# 作者：小红书@人间清醒的李某人

import base64
import json
import logging
import re
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from openai import BadRequestError
from sqlalchemy.orm import Session

from app.db.session import DATA_DIR
from app.db.session import get_db
from app.llm.qwen_client import QwenClient
from app.llm.qwen_mcp_agent import QwenMCPAgent
from app.llm.qwen_speech_client import QwenSpeechClient
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse
from app.schemas.memory import (
    BusinessMemoryExtractRequest,
    BusinessMemoryExtractResponse,
    ConversationMemoryCreate,
    ConversationMemoryRead,
    ConversationMemoryExtractRequest,
    ConversationMemoryExtractResponse,
    MemoryEventRead,
    MemoryEventSearchRequest,
    MemoryEventSearchResponse,
    MemoryEventSearchItem,
    UserProfileRead,
)
from app.schemas.memory_preference import MemoryPreferenceRead, MemoryPreferenceUpsert
from app.schemas.medical_case import MedicalCaseCreate, MedicalCaseRead, MedicalCaseUpdate
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.schemas.visit_record import (
    VisitRecordCreate,
    VisitRecordRead,
    VisitRecordUpdate,
)
from app.services import (
    memory_preference_service,
    memory_service,
    medical_case_service,
    patient_service,
    visit_record_service,
    conversation_memory_service,
)

router = APIRouter()
logger = logging.getLogger("uvicorn.error")
GENERATED_AUDIO_DIR = DATA_DIR / "generated_audio"
GENERATED_AUDIO_DIR.mkdir(exist_ok=True)
SHORT_TERM_ROUND_TRIGGER = 5
MESSAGES_PER_ROUND = 2
SHORT_TERM_TRIGGER_MESSAGE_COUNT = SHORT_TERM_ROUND_TRIGGER * MESSAGES_PER_ROUND


def _save_speech_audio(audio_base64: str, mime_type: str) -> tuple[str, str]:
    suffix = ".mp3" if mime_type == "audio/mp3" else ".bin"
    filename = f"speech_{uuid4().hex}{suffix}"
    output_path = GENERATED_AUDIO_DIR / filename
    output_path.write_bytes(base64.b64decode(audio_base64))
    return str(output_path), f"/media/generated_audio/{filename}"


def _extract_patient_code_from_query(query: str) -> Optional[str]:
    match = re.search(r"P\d{4,}", query, flags=re.IGNORECASE)
    if match is None:
        return None
    return match.group(0).upper()


def _extract_phone_from_query(query: str) -> Optional[str]:
    match = re.search(r"1\d{10}", query)
    if match is None:
        return None
    return match.group(0)


def _build_user_multimodal_payload(payload: AgentQueryRequest) -> Optional[str]:
    if not payload.images:
        return None
    image_items = []
    for image in payload.images:
        image_items.append(
            {
                "mime_type": image.mime_type,
                "image_url": image.image_url,
                "has_base64": bool(image.image_base64),
            }
        )
    return json.dumps({"images": image_items}, ensure_ascii=False)


def _build_assistant_multimodal_payload(result: dict) -> Optional[str]:
    if not result.get("speech_download_url") and not result.get("speech_file_path"):
        return None
    return json.dumps(
        {
            "speech": {
                "speech_mime_type": result.get("speech_mime_type"),
                "speech_model": result.get("speech_model"),
                "speech_voice": result.get("speech_voice"),
                "speech_file_path": result.get("speech_file_path"),
                "speech_download_url": result.get("speech_download_url"),
            }
        },
        ensure_ascii=False,
    )


def _build_retrieval_label(retrieval_sources: list[str]) -> str:
    sources = set(retrieval_sources)
    if {"keyword", "vector"}.issubset(sources):
        return "hybrid"
    if "keyword" in sources:
        return "keyword"
    if "vector" in sources:
        return "vector"
    return "recent"


def _resolve_patient_from_agent_result(
    db: Session,
    query: str,
    result: dict,
):
    for tool_output in result.get("tool_outputs", []):
        tool_name = tool_output.get("tool_name")
        tool_result = tool_output.get("result", {})

        if tool_name == "verify_patient_identity" and tool_result.get("verified"):
            patient_data = tool_result.get("patient", {})
            patient_id = patient_data.get("id")
            if patient_id is not None:
                patient = patient_service.get_patient_by_id(db, patient_id)
                if patient is not None:
                    return patient
            patient_code = patient_data.get("patient_code")
            if patient_code:
                patient = patient_service.get_patient_by_code(db, patient_code)
                if patient is not None:
                    return patient

        patient_data = tool_result.get("patient")
        if isinstance(patient_data, dict):
            patient_id = patient_data.get("id")
            if patient_id is not None:
                patient = patient_service.get_patient_by_id(db, patient_id)
                if patient is not None:
                    return patient
            patient_code = patient_data.get("patient_code")
            if patient_code:
                patient = patient_service.get_patient_by_code(db, patient_code)
                if patient is not None:
                    return patient

    patient_code = _extract_patient_code_from_query(query)
    if patient_code is not None:
        patient = patient_service.get_patient_by_code(db, patient_code)
        if patient is not None:
            return patient

    phone = _extract_phone_from_query(query)
    if phone is not None:
        return patient_service.get_patient_by_phone(db, phone)
    return None


def _build_memory_context(db: Session, patient, query: str) -> dict:
    short_term_memories = conversation_memory_service.list_recent_conversation_memories(
        db,
        patient_id=patient.id,
        limit=6,
    )
    user_profile = memory_service.get_user_profile(db, patient.id)
    relevant_events = memory_service.get_relevant_memory_events(
        db,
        patient_id=patient.id,
        query=query,
        limit=5,
    )
    return {
        "short_term_memories": [
            {
                "role": memory.role,
                "content": memory.content,
                "multimodal_payload": memory.multimodal_payload,
            }
            for memory in short_term_memories
        ],
        "user_profile": (
            {
                "profile_summary": user_profile.profile_summary,
                "stable_preferences": user_profile.stable_preferences,
                "preferred_topics": user_profile.preferred_topics,
            }
            if user_profile is not None
            else None
        ),
        "relevant_events": [
            {
                "event_time": event.event_time.isoformat(),
                "title": event.title,
                "summary": event.summary,
            }
            for event in relevant_events
        ],
    }


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/agent/query",
    response_model=AgentQueryResponse,
    tags=["Agent"],
    summary="调用 Qwen + 工具查询患者信息",
    description=(
        "主问答接口。把用户的问题发送给 Agent，由 Agent 结合历史短期记忆、长期用户画像、"
        "长期关键事件、内部工具和可选图片一起生成答案。"
        "如果开启语音播报，还会额外生成音频文件路径和下载链接。"
    ),
)
def agent_query(
    request: Request,
    payload: AgentQueryRequest,
    db: Session = Depends(get_db),
) -> AgentQueryResponse:
    try:
        llm_client = QwenClient()
        speech_client = QwenSpeechClient() if payload.enable_speech else None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    agent = QwenMCPAgent(db=db, llm_client=llm_client)
    try:
        pre_resolved_patient = _resolve_patient_from_agent_result(
            db,
            payload.query,
            {"tool_outputs": []},
        )
        memory_context = None
        if pre_resolved_patient is not None:
            memory_context = _build_memory_context(db, pre_resolved_patient, payload.query)
        result = agent.run(
            payload.query,
            images=[image.model_dump() for image in payload.images],
            debug_planner=payload.debug_planner,
            memory_context=memory_context,
        )
    except BadRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if payload.enable_speech and speech_client is not None:
        try:
            speech_result = speech_client.synthesize(
                result["answer"],
                voice=payload.speech_voice,
                audio_format=payload.speech_format,
            )
        except (BadRequestError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )
        speech_file_path, speech_download_url = _save_speech_audio(
            speech_result["audio_base64"],
            speech_result["mime_type"],
        )
        result.update(
            {
                "speech_mime_type": speech_result["mime_type"],
                "speech_model": speech_result["model"],
                "speech_voice": speech_result["voice"],
                "speech_file_path": speech_file_path,
                "speech_download_url": str(request.base_url).rstrip("/") + speech_download_url,
            }
        )

    patient = _resolve_patient_from_agent_result(db, payload.query, result)
    if patient is not None:
        memory_session_id = f"agent-{uuid4().hex}"
        conversation_memory_service.create_conversation_memory(
            db,
            ConversationMemoryCreate(
                patient_id=patient.id,
                session_id=memory_session_id,
                role="user",
                content=payload.query,
                multimodal_payload=_build_user_multimodal_payload(payload),
            ),
        )
        conversation_memory_service.create_conversation_memory(
            db,
            ConversationMemoryCreate(
                patient_id=patient.id,
                session_id=memory_session_id,
                role="assistant",
                content=result["answer"],
                multimodal_payload=_build_assistant_multimodal_payload(result),
            ),
        )
        short_term_count = conversation_memory_service.count_conversation_memories(
            db,
            patient_id=patient.id,
        )
        if (
            short_term_count >= SHORT_TERM_TRIGGER_MESSAGE_COUNT
            and short_term_count % SHORT_TERM_TRIGGER_MESSAGE_COUNT == 0
        ):
            conversation_texts = memory_service.get_conversation_texts_for_extraction(
                db=db,
                patient_id=patient.id,
                limit=SHORT_TERM_TRIGGER_MESSAGE_COUNT,
            )
            memory_events, user_profile = memory_service.refresh_conversation_memory(
                db=db,
                patient=patient,
                conversation_texts=conversation_texts,
            )
            logger.info(
                "Auto extracted long-term conversation memory for patient_id=%s short_term_count=%s event_count=%s profile_updated=%s",
                patient.id,
                short_term_count,
                len(memory_events),
                user_profile is not None,
            )
    return AgentQueryResponse(**result)


@router.get(
    "/memory/preferences",
    response_model=MemoryPreferenceRead,
    tags=["Memory"],
    summary="查询长期记忆偏好配置",
    description=(
        "读取某个患者已经保存的长期偏好配置，例如偏好称呼、回答风格、回答长度、"
        "常关注主题等。这些内容会影响后续 Agent 的个性化回答。"
    ),
)
def get_memory_preference(
    patient_id: Optional[int] = Query(default=None),
    patient_code: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> MemoryPreferenceRead:
    if patient_id is None and patient_code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="patient_id or patient_code is required",
        )

    memory_preference = None
    if patient_id is not None:
        memory_preference = memory_preference_service.get_memory_preference_by_patient_id(
            db, patient_id
        )
    elif patient_code is not None:
        memory_preference = memory_preference_service.get_memory_preference_by_patient_code(
            db, patient_code
        )

    if memory_preference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="memory preference not found",
        )
    return memory_preference


@router.put(
    "/memory/preferences",
    response_model=MemoryPreferenceRead,
    tags=["Memory"],
    summary="创建或更新长期记忆偏好配置",
    description=(
        "创建或更新某个患者的长期偏好。这个接口适合保存用户主动设置的内容，"
        "例如希望回答更简短、希望使用通俗语言、关注心内科等。"
    ),
)
def upsert_memory_preference(
    payload: MemoryPreferenceUpsert,
    db: Session = Depends(get_db),
) -> MemoryPreferenceRead:
    patient = patient_service.get_patient_by_id(db, payload.patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient not found",
        )
    return memory_preference_service.upsert_memory_preference(db, payload)


@router.post(
    "/memory/conversations",
    response_model=ConversationMemoryRead,
    tags=["Memory"],
    summary="写入短期记忆对话",
    description=(
        "手动写入一条短期记忆。通常系统会在 /api/agent/query 完成后自动写入，"
        "这个接口更适合测试、补数据或联调。"
    ),
)
def create_conversation_memory(
    payload: ConversationMemoryCreate,
    db: Session = Depends(get_db),
) -> ConversationMemoryRead:
    patient = patient_service.get_patient_by_id(db, payload.patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient not found",
        )
    return conversation_memory_service.create_conversation_memory(db, payload)


@router.get(
    "/memory/conversations",
    response_model=list[ConversationMemoryRead],
    tags=["Memory"],
    summary="查询短期记忆对话",
    description=(
        "查询某个患者已经保存的短期记忆内容。可以按 session_id 过滤，也可以限制返回条数，"
        "适合查看最近几轮对话是否已经正确写入。"
    ),
)
def list_conversation_memories(
    patient_id: int,
    session_id: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=10),
    db: Session = Depends(get_db),
) -> list[ConversationMemoryRead]:
    patient = patient_service.get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient not found",
        )
    return conversation_memory_service.list_conversation_memories(
        db,
        patient_id=patient_id,
        session_id=session_id,
        limit=limit,
    )


@router.post(
    "/memory/extract/business",
    response_model=BusinessMemoryExtractResponse,
    tags=["Memory"],
    summary="从业务数据提炼长期记忆关键事件",
    description=(
        "从病例和就诊记录中提炼长期关键事件。提炼后的结果会写入 memory_events，"
        "并在向量检索可用时同步写入向量索引。适合在业务数据新增或更新后触发。"
    ),
)
def extract_business_memory(
    payload: BusinessMemoryExtractRequest,
    db: Session = Depends(get_db),
) -> BusinessMemoryExtractResponse:
    patient = memory_service.get_patient(db, payload.patient_id, payload.patient_code)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient not found",
        )

    memory_events = memory_service.refresh_business_memory(
        db=db,
        patient=patient,
    )
    return BusinessMemoryExtractResponse(
        patient_id=patient.id,
        event_count=len(memory_events),
        memory_events=memory_events,
    )


@router.post(
    "/memory/extract/conversation",
    response_model=ConversationMemoryExtractResponse,
    tags=["Memory"],
    summary="从短期对话提炼长期记忆画像与对话事件",
    description=(
        "从某个患者最近 N 条短期对话中提炼长期用户画像和对话类关键事件。"
        "这个接口不需要手工传对话文本，而是直接从 conversation_memories 里读取。"
    ),
)
def extract_conversation_memory(
    payload: ConversationMemoryExtractRequest,
    db: Session = Depends(get_db),
) -> ConversationMemoryExtractResponse:
    patient = patient_service.get_patient_by_id(db, payload.patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient not found",
        )

    conversation_texts = memory_service.get_conversation_texts_for_extraction(
        db=db,
        patient_id=patient.id,
        limit=payload.recent_limit,
    )

    memory_events, user_profile = memory_service.refresh_conversation_memory(
        db=db,
        patient=patient,
        conversation_texts=conversation_texts,
    )
    return ConversationMemoryExtractResponse(
        patient_id=patient.id,
        event_count=len(memory_events),
        profile_updated=True,
        memory_events=memory_events,
        user_profile=user_profile,
    )


@router.get(
    "/memory/events",
    response_model=list[MemoryEventRead],
    tags=["Memory"],
    summary="查询长期记忆中的关键事件",
    description=(
        "查询某个患者当前已经沉淀的长期关键事件，包括业务数据提炼出的事件和"
        "短期对话提炼出的事件。"
    ),
)
def list_memory_events(
    patient_id: int,
    db: Session = Depends(get_db),
) -> list[MemoryEventRead]:
    patient = patient_service.get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient not found",
        )
    return memory_service.list_memory_events(db, patient_id)


@router.post(
    "/memory/search/events",
    response_model=MemoryEventSearchResponse,
    tags=["Memory"],
    summary="混合检索长期记忆关键事件",
    description=(
        "根据用户问题在长期关键事件里做混合检索。系统会同时做关键词匹配和向量检索，"
        "返回最相关的 topN 条事件，并标明每条结果是关键词命中、向量命中还是混合命中。"
    ),
)
def search_memory_events(
    payload: MemoryEventSearchRequest,
    db: Session = Depends(get_db),
) -> MemoryEventSearchResponse:
    patient = memory_service.get_patient(db, payload.patient_id, payload.patient_code)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient not found",
        )

    results = memory_service.search_memory_events(
        db=db,
        patient_id=patient.id,
        query=payload.query,
        top_n=payload.top_n,
    )
    return MemoryEventSearchResponse(
        patient_id=patient.id,
        query=payload.query,
        top_n=payload.top_n,
        results=[
            MemoryEventSearchItem(
                **MemoryEventRead.model_validate(item["event"]).model_dump(),
                retrieval_score=item["retrieval_score"],
                retrieval_sources=item["retrieval_sources"],
                retrieval_label=_build_retrieval_label(item["retrieval_sources"]),
                matched_by_keyword="keyword" in item["retrieval_sources"],
                matched_by_vector="vector" in item["retrieval_sources"],
                keyword_score=item.get("keyword_score", 0.0),
                vector_score=item.get("vector_score", 0.0),
            )
            for item in results
        ],
    )


@router.get(
    "/memory/profile",
    response_model=UserProfileRead,
    tags=["Memory"],
    summary="查询长期记忆中的用户画像",
    description=(
        "读取某个患者已经沉淀的长期用户画像，包括画像摘要、沟通风格、偏好主题、"
        "稳定偏好和画像来源。"
    ),
)
def get_user_profile(
    patient_id: int,
    db: Session = Depends(get_db),
) -> UserProfileRead:
    patient = patient_service.get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient not found",
        )
    user_profile = memory_service.get_user_profile(db, patient_id)
    if user_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user profile not found",
        )
    return user_profile


@router.post(
    "/patients",
    response_model=PatientRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Patients"],
    summary="创建患者",
    description=(
        "创建一条新的患者基础信息。适合录入新患者时使用，内容包括患者编号、姓名、"
        "联系方式、身份证号等基础资料。"
    ),
)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)) -> PatientRead:
    existing = patient_service.get_patient_by_code(db, payload.patient_code)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="patient_code already exists",
        )
    return patient_service.create_patient(db, payload)


@router.get(
    "/patients",
    response_model=list[PatientRead],
    tags=["Patients"],
    summary="查询患者列表",
    description="查询当前系统里的患者列表，适合做后台管理、调试和测试数据检查。",
)
def list_patients(db: Session = Depends(get_db)) -> list[PatientRead]:
    return patient_service.list_patients(db)


@router.get(
    "/patients/{patient_id}",
    response_model=PatientRead,
    tags=["Patients"],
    summary="按 ID 查询患者",
    description="按数据库中的 patient_id 查询一位患者的基础资料。",
)
def get_patient(patient_id: int, db: Session = Depends(get_db)) -> PatientRead:
    patient = patient_service.get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="patient not found")
    return patient


@router.put(
    "/patients/{patient_id}",
    response_model=PatientRead,
    tags=["Patients"],
    summary="更新患者信息",
    description="更新某位患者的基础信息，例如手机号、地址、紧急联系人等。",
)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
) -> PatientRead:
    patient = patient_service.get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="patient not found")
    return patient_service.update_patient(db, patient, payload)


@router.post(
    "/medical-cases",
    response_model=MedicalCaseRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Medical Cases"],
    summary="创建病例",
    description=(
        "创建一条病例记录。病例主要用于保存诊断、主诉、现病史、既往史、治疗方案和"
        "主治医生等信息。"
    ),
)
def create_medical_case(
    payload: MedicalCaseCreate, db: Session = Depends(get_db)
) -> MedicalCaseRead:
    if not medical_case_service.patient_exists(db, payload.patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="patient not found")
    return medical_case_service.create_medical_case(db, payload)


@router.get(
    "/medical-cases",
    response_model=list[MedicalCaseRead],
    tags=["Medical Cases"],
    summary="查询病例列表",
    description="查询病例列表。可以按 patient_id 过滤，只看某个患者的病例。",
)
def list_medical_cases(
    patient_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[MedicalCaseRead]:
    return medical_case_service.list_medical_cases(db, patient_id=patient_id)


@router.get(
    "/medical-cases/{case_id}",
    response_model=MedicalCaseRead,
    tags=["Medical Cases"],
    summary="按 ID 查询病例",
    description="按病例主键 case_id 查询单条病例详情。",
)
def get_medical_case(case_id: int, db: Session = Depends(get_db)) -> MedicalCaseRead:
    medical_case = medical_case_service.get_medical_case_by_id(db, case_id)
    if medical_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="medical case not found")
    return medical_case


@router.put(
    "/medical-cases/{case_id}",
    response_model=MedicalCaseRead,
    tags=["Medical Cases"],
    summary="更新病例",
    description="更新某条病例记录，例如修改诊断、补充主诉或调整治疗方案。",
)
def update_medical_case(
    case_id: int,
    payload: MedicalCaseUpdate,
    db: Session = Depends(get_db),
) -> MedicalCaseRead:
    medical_case = medical_case_service.get_medical_case_by_id(db, case_id)
    if medical_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="medical case not found")
    return medical_case_service.update_medical_case(db, medical_case, payload)


@router.post(
    "/visit-records",
    response_model=VisitRecordRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Visit Records"],
    summary="创建就诊记录",
    description=(
        "创建一条就诊记录。就诊记录主要保存就诊时间、科室、医生、摘要和备注等，"
        "适合记录一次门诊或住院过程。"
    ),
)
def create_visit_record(
    payload: VisitRecordCreate, db: Session = Depends(get_db)
) -> VisitRecordRead:
    if not visit_record_service.patient_exists(db, payload.patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="patient not found")
    return visit_record_service.create_visit_record(db, payload)


@router.get(
    "/visit-records",
    response_model=list[VisitRecordRead],
    tags=["Visit Records"],
    summary="查询就诊记录列表",
    description="查询就诊记录列表。可以按 patient_id 过滤，只看某个患者的记录。",
)
def list_visit_records(
    patient_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[VisitRecordRead]:
    return visit_record_service.list_visit_records(db, patient_id=patient_id)


@router.get(
    "/visit-records/{visit_record_id}",
    response_model=VisitRecordRead,
    tags=["Visit Records"],
    summary="按 ID 查询就诊记录",
    description="按就诊记录主键查询单条就诊详情。",
)
def get_visit_record(
    visit_record_id: int,
    db: Session = Depends(get_db),
) -> VisitRecordRead:
    visit_record = visit_record_service.get_visit_record_by_id(db, visit_record_id)
    if visit_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="visit record not found",
        )
    return visit_record


@router.put(
    "/visit-records/{visit_record_id}",
    response_model=VisitRecordRead,
    tags=["Visit Records"],
    summary="更新就诊记录",
    description="更新某条就诊记录，例如修改医生、补充备注或调整就诊摘要。",
)
def update_visit_record(
    visit_record_id: int,
    payload: VisitRecordUpdate,
    db: Session = Depends(get_db),
) -> VisitRecordRead:
    visit_record = visit_record_service.get_visit_record_by_id(db, visit_record_id)
    if visit_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="visit record not found",
        )
    return visit_record_service.update_visit_record(db, visit_record, payload)
