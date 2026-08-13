
"""LangGraph-backed Agent orchestration.

The public API (``PatientAgent.run()`` / ``PatientAgent.run_stream()``) is
stable.  The internal ReAct-style tool loop is implemented as a LangGraph
``StateGraph`` with the nodes ``planner``, ``agent_decision``, ``tools`` and
``finalizer``.  Status events (planning / tool) and final answer deltas are
emitted as custom stream events, then converted back to the existing SSE event
shape by ``run_stream()``.
"""

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.llm.llm import LLMClient
from app.mcp_client import MCPToolClient


ToolHandler = Callable[..., Dict[str, Any]]


SYSTEM_PROMPT = """
你是医院患者智能辅助 Agent。
你可以调用内部工具完成身份验证、病例查询、就诊记录调取。
涉及患者隐私数据时，优先完成身份验证。
回答必须基于工具结果，不要编造病例或就诊信息。
当用户要求"最近一次""最新一次"就诊记录时，使用 get_patient_visit_records，并传入 limit=1。
不要臆造不存在的工具名称。
采用"先规划、再行动、最后校验"的工作方式：
1. 先根据问题形成简短内部计划。
2. 每一步只执行当前最必要的工具。
3. 工具结果不足时继续补查，足够时停止。
4. 最终答案只保留结论和证据，不暴露冗长内部思维。
如果提供了"短期记忆、用户画像、关键事件"上下文，回答前优先参考这些信息，并在与用户当前问题相关时加以利用。
""".strip()

PLANNER_PROMPT = """
你是 Agent 的内部 Planner，需要为当前问题生成简洁计划。
要求结合以下策略：
1. CoT：先拆分目标、约束、所需证据。
2. ReAct：明确下一步最合适的动作和工具顺序。
3. Self-Consistency：你会被多次采样，输出要稳定、可执行、短。

仅输出 JSON，不要输出 markdown，不要解释：
{
  "objective": "一句话目标",
  "need_identity_verification": true,
  "image_reasoning": false,
  "tool_sequence": ["verify_patient_identity", "get_patient_visit_records"],
  "steps": ["步骤1", "步骤2"],
  "final_answer_focus": ["回答应覆盖的重点1", "重点2"]
}
""".strip()

FINALIZER_PROMPT = """
你是最终答案整理器。
请基于用户问题、执行计划和工具结果给出最终回答。
要求：
1. 只能使用已有工具结果和已知图片内容。
2. 如果证据不足，明确指出不足。
3. 直接给结论、依据和必要提醒，不暴露内部思维链。
""".strip()

MAX_TOOL_STEPS = 6
PLAN_TEMPERATURES = [0.1, 0.4, 0.7]
TOOL_DISPLAY_NAMES = {
    "verify_patient_identity": "验证患者身份",
    "get_patient_profile": "查询患者资料",
    "get_patient_medical_cases": "查询病例信息",
    "get_patient_visit_records": "查询就诊记录",
}
UNKNOWN_TOOL_DISPLAY_NAME = "调用业务工具"

# Tools the Agent may expose and execute via the MCP layer.  Anything outside
# this allowlist is rejected and never reaches the MCP server.
MCP_ALLOWED_TOOLS = frozenset(TOOL_DISPLAY_NAMES)


class AgentState(TypedDict):
    """State shared across LangGraph nodes.

    Deliberately excludes the database ``Session``, ``LLMClient`` and API keys
    — those live on the ``PatientAgent`` instance and are never placed in this
    state.  No LangGraph checkpointer is enabled, so this state never leaves
    memory and is never surfaced through the SSE endpoint.
    """

    # Request inputs
    user_query: str
    images: List[Dict[str, Any]]
    memory_context: Optional[Dict[str, Any]]
    has_images: bool
    debug_planner: bool
    streaming: bool

    # Planner outputs
    execution_plan: Dict[str, Any]
    planner_debug: Dict[str, Any]

    # Agent tool loop
    messages: List[Dict[str, Any]]
    pending_tool_calls: List[Dict[str, Any]]
    tool_outputs: List[Dict[str, Any]]
    tool_steps: int

    # Finalizer
    draft_answer: str
    answer: str


class PatientAgent:
    """Orchestrates tool calls via an LLM using a LangGraph ``StateGraph``.

    ``run()`` (non-streaming) and ``run_stream()`` (streaming) keep their
    original signatures and return values; only the internal execution loop
    changed from a hand-written ``while`` loop to graph nodes.
    """

    def __init__(self, db: Session, llm_client: LLMClient) -> None:
        self.db = db
        self.llm_client = llm_client
        self.mcp_client = MCPToolClient()
        self.tools = self._build_tool_registry()
        self.graph = self._build_graph()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        user_query: str,
        images: Optional[List[Dict[str, Any]]] = None,
        debug_planner: bool = False,
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        final_state = self.graph.invoke(
            self._build_input_state(
                user_query=user_query,
                images=images,
                memory_context=memory_context,
                debug_planner=debug_planner,
                streaming=False,
            )
        )
        return self._build_result(
            answer=final_state["answer"],
            execution=self._execution_from_state(final_state),
            debug_planner=debug_planner,
        )

    def run_stream(
        self,
        user_query: str,
        images: Optional[List[Dict[str, Any]]] = None,
        debug_planner: bool = False,
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
        """Yield public execution events and return the completed Agent result.

        The graph emits custom events — either status data (``{"stage": ...}``)
        or answer deltas (``{"text": ...}``) — which are converted here into the
        existing ``{"event": ..., "data": ...}`` SSE shape.  LangGraph node
        updates and raw state are never surfaced to the caller.
        """
        final_state: Dict[str, Any] = {}
        for mode, chunk in self.graph.stream(
            self._build_input_state(
                user_query=user_query,
                images=images,
                memory_context=memory_context,
                debug_planner=debug_planner,
                streaming=True,
            ),
            stream_mode=["custom", "values"],
        ):
            if mode == "custom":
                if "stage" in chunk:
                    yield {"event": "status", "data": chunk}
                elif "text" in chunk:
                    yield {"event": "delta", "data": chunk}
            elif mode == "values":
                final_state = chunk

        return self._build_result(
            answer=final_state["answer"],
            execution=self._execution_from_state(final_state),
            debug_planner=debug_planner,
        )

    # ------------------------------------------------------------------
    # LangGraph graph: state helpers, nodes, and routing
    # ------------------------------------------------------------------

    def _build_input_state(
        self,
        user_query: str,
        images: Optional[List[Dict[str, Any]]],
        memory_context: Optional[Dict[str, Any]],
        debug_planner: bool,
        streaming: bool,
    ) -> AgentState:
        return {
            "user_query": user_query,
            "images": images or [],
            "memory_context": memory_context,
            "has_images": bool(images),
            "debug_planner": debug_planner,
            "streaming": streaming,
            "execution_plan": {},
            "planner_debug": {},
            "messages": [],
            "pending_tool_calls": [],
            "tool_outputs": [],
            "tool_steps": 0,
            "draft_answer": "",
            "answer": "",
        }

    def _execution_from_state(self, state: AgentState) -> Dict[str, Any]:
        return {
            "execution_plan": state["execution_plan"],
            "draft_answer": state["draft_answer"],
            "tool_outputs": state["tool_outputs"],
            "planner_debug": state["planner_debug"],
            "has_images": state["has_images"],
        }

    def _emit_status(self, status: Dict[str, Any]) -> None:
        get_stream_writer()(status)

    def _emit_delta(self, text: str) -> None:
        get_stream_writer()({"text": text})

    def _build_graph(self) -> Any:
        graph = StateGraph(AgentState)
        graph.add_node("planner", self._planner_node)
        graph.add_node("agent_decision", self._agent_decision_node)
        graph.add_node("tools", self._tools_node)
        graph.add_node("finalizer", self._finalizer_node)

        graph.add_edge(START, "planner")
        graph.add_edge("planner", "agent_decision")
        graph.add_conditional_edges(
            "agent_decision",
            self._route_after_decision,
            ["tools", "finalizer"],
        )
        graph.add_conditional_edges(
            "tools",
            self._route_after_tools,
            ["agent_decision", "finalizer"],
        )
        graph.add_edge("finalizer", END)
        return graph.compile()

    def _planner_node(self, state: AgentState) -> Dict[str, Any]:
        if state["streaming"]:
            self._emit_status({"stage": "planning"})
        execution_plan, planner_debug = self._build_execution_plan(
            user_query=state["user_query"],
            has_images=state["has_images"],
        )
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self._build_memory_messages(state["memory_context"]),
            {
                "role": "system",
                "content": self._format_execution_plan(execution_plan),
            },
            {
                "role": "user",
                "content": self._build_user_content(state["user_query"], state["images"]),
            },
        ]
        return {
            "execution_plan": execution_plan,
            "planner_debug": planner_debug,
            "messages": messages,
        }

    def _agent_decision_node(self, state: AgentState) -> Dict[str, Any]:
        response = self.llm_client.complete_with_tools(
            messages=state["messages"],
            tools=self._tool_specs(),
            temperature=0,
        )
        if response["tool_calls"]:
            return {
                "messages": state["messages"] + [response["assistant_message"]],
                "pending_tool_calls": response["tool_calls"],
            }
        return {
            "pending_tool_calls": [],
            "draft_answer": response["content"] or "",
        }

    def _tools_node(self, state: AgentState) -> Dict[str, Any]:
        messages = state["messages"]
        tool_outputs = list(state["tool_outputs"])
        tool_steps = state["tool_steps"]
        streaming = state["streaming"]

        for tool_call in state["pending_tool_calls"]:
            handler = self.tools.get(tool_call["name"])
            if handler is None:
                continue
            display_name = self._tool_display_name(tool_call["name"])
            if streaming:
                self._emit_status({"stage": "tool", "status": "started", "name": display_name})
            try:
                result = handler(**tool_call["arguments"])
                tool_outputs.append(
                    {
                        "tool_name": tool_call["name"],
                        "arguments": tool_call["arguments"],
                        "result": result,
                    }
                )
                tool_steps += 1
                messages = messages + [
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": tool_call["name"],
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                ]
            except Exception:
                if streaming:
                    self._emit_status({"stage": "tool", "status": "failed", "name": display_name})
                raise
            if streaming:
                self._emit_status({"stage": "tool", "status": "completed", "name": display_name})

        return {
            "messages": messages,
            "tool_outputs": tool_outputs,
            "tool_steps": tool_steps,
            "pending_tool_calls": [],
        }

    def _finalizer_node(self, state: AgentState) -> Dict[str, Any]:
        if state["streaming"]:
            self._emit_status({"stage": "generating"})
            parts: List[str] = []
            for text in self._stream_finalize_answer(
                user_query=state["user_query"],
                execution_plan=state["execution_plan"],
                draft_answer=state["draft_answer"],
                tool_outputs=state["tool_outputs"],
                has_images=state["has_images"],
            ):
                parts.append(text)
                self._emit_delta(text)
            answer = "".join(parts) or state["draft_answer"]
        else:
            answer = self._finalize_answer(
                user_query=state["user_query"],
                execution_plan=state["execution_plan"],
                draft_answer=state["draft_answer"],
                tool_outputs=state["tool_outputs"],
                has_images=state["has_images"],
            )
        return {"answer": answer}

    def _route_after_decision(self, state: AgentState) -> str:
        if state["pending_tool_calls"] and state["tool_steps"] < MAX_TOOL_STEPS:
            return "tools"
        return "finalizer"

    def _route_after_tools(self, state: AgentState) -> str:
        if state["tool_steps"] < MAX_TOOL_STEPS:
            return "agent_decision"
        return "finalizer"

    def _tool_display_name(self, tool_name: str) -> str:
        return TOOL_DISPLAY_NAMES.get(tool_name, UNKNOWN_TOOL_DISPLAY_NAME)

    def _build_result(
        self,
        answer: str,
        execution: Dict[str, Any],
        debug_planner: bool,
    ) -> Dict[str, Any]:
        return {
            "answer": answer,
            "tool_outputs": execution["tool_outputs"],
            "planner_debug": (
                self._build_runtime_planner_debug(
                    planner_debug=execution["planner_debug"],
                    execution_plan=execution["execution_plan"],
                    tool_outputs=execution["tool_outputs"],
                )
                if debug_planner
                else None
            ),
        }

    # ------------------------------------------------------------------
    # Planner
    # ------------------------------------------------------------------

    def _build_execution_plan(
        self, user_query: str, has_images: bool
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        raw_candidates: List[Dict[str, Any]] = []
        planner_user_prompt = (
            f"用户问题：{user_query}\n"
            f"是否包含图片：{'是' if has_images else '否'}\n"
            "请输出最小可执行计划。"
        )
        for temperature in PLAN_TEMPERATURES:
            response = self.llm_client.complete(
                messages=[
                    {"role": "system", "content": PLANNER_PROMPT},
                    {"role": "user", "content": planner_user_prompt},
                ],
                temperature=temperature,
            )
            parsed_candidate = self._parse_plan_candidate(response["content"])
            raw_candidates.append(
                {
                    "temperature": temperature,
                    "raw_content": response["content"],
                    "parsed_plan": parsed_candidate,
                }
            )
            candidates.append(parsed_candidate)
        merged_plan = self._merge_plan_candidates(candidates, has_images=has_images)
        return merged_plan, {
            "planner_prompt": PLANNER_PROMPT,
            "temperatures": PLAN_TEMPERATURES,
            "candidates": raw_candidates,
            "merged_plan": merged_plan,
        }

    def _parse_plan_candidate(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    pass
        return {
            "objective": "基于用户问题规划查询与回答",
            "need_identity_verification": False,
            "image_reasoning": False,
            "tool_sequence": [],
            "steps": ["解析问题", "按需调用工具", "整理结论"],
            "final_answer_focus": ["直接回答问题", "标注依据和限制"],
        }

    def _merge_plan_candidates(
        self,
        candidates: List[Dict[str, Any]],
        has_images: bool,
    ) -> Dict[str, Any]:
        verification_votes = sum(
            1 for candidate in candidates if candidate.get("need_identity_verification")
        )
        image_votes = sum(1 for candidate in candidates if candidate.get("image_reasoning"))
        tool_scores: Dict[str, int] = {}
        merged_steps: List[str] = []
        merged_focus: List[str] = []

        for candidate in candidates:
            for tool_name in candidate.get("tool_sequence", []):
                if tool_name not in self.tools:
                    continue
                tool_scores[tool_name] = tool_scores.get(tool_name, 0) + 1
            for step in candidate.get("steps", []):
                if step not in merged_steps:
                    merged_steps.append(step)
            for focus in candidate.get("final_answer_focus", []):
                if focus not in merged_focus:
                    merged_focus.append(focus)

        ranked_tools = [
            tool_name
            for tool_name, _ in sorted(
                tool_scores.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]
        return {
            "objective": candidates[0].get("objective", "完成患者问题回答"),
            "need_identity_verification": verification_votes >= 2,
            "image_reasoning": has_images or image_votes >= 2,
            "tool_sequence": ranked_tools,
            "steps": merged_steps[:5] or ["解析问题", "按需调用工具", "整理结论"],
            "final_answer_focus": merged_focus[:5] or ["直接回答问题", "说明依据与限制"],
        }

    def _format_execution_plan(self, execution_plan: Dict[str, Any]) -> str:
        return (
            "内部执行计划（已做多候选一致性筛选）：\n"
            f"- 目标：{execution_plan['objective']}\n"
            f"- 是否优先验权：{'是' if execution_plan['need_identity_verification'] else '否'}\n"
            f"- 是否结合图片：{'是' if execution_plan['image_reasoning'] else '否'}\n"
            f"- 推荐工具顺序：{', '.join(execution_plan['tool_sequence']) or '按需决定'}\n"
            f"- 关键步骤：{'；'.join(execution_plan['steps'])}\n"
            f"- 回答重点：{'；'.join(execution_plan['final_answer_focus'])}"
        )

    # ------------------------------------------------------------------
    # Answer finalisation
    # ------------------------------------------------------------------

    def _build_finalizer_messages(
        self,
        user_query: str,
        execution_plan: Dict[str, Any],
        draft_answer: str,
        tool_outputs: List[Dict[str, Any]],
        has_images: bool,
    ) -> List[Dict[str, Any]]:
        return [
            {"role": "system", "content": FINALIZER_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "user_query": user_query,
                        "has_images": has_images,
                        "execution_plan": execution_plan,
                        "draft_answer": draft_answer,
                        "tool_outputs": tool_outputs,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def _finalize_answer(
        self,
        user_query: str,
        execution_plan: Dict[str, Any],
        draft_answer: str,
        tool_outputs: List[Dict[str, Any]],
        has_images: bool,
    ) -> str:
        response = self.llm_client.complete(
            messages=self._build_finalizer_messages(
                user_query=user_query,
                execution_plan=execution_plan,
                draft_answer=draft_answer,
                tool_outputs=tool_outputs,
                has_images=has_images,
            ),
            temperature=0,
        )
        return response["content"] or draft_answer

    def _stream_finalize_answer(
        self,
        user_query: str,
        execution_plan: Dict[str, Any],
        draft_answer: str,
        tool_outputs: List[Dict[str, Any]],
        has_images: bool,
    ) -> Generator[str, None, None]:
        yield from self.llm_client.stream_complete(
            messages=self._build_finalizer_messages(
                user_query=user_query,
                execution_plan=execution_plan,
                draft_answer=draft_answer,
                tool_outputs=tool_outputs,
                has_images=has_images,
            ),
            temperature=0,
        )

    # ------------------------------------------------------------------
    # Memory context helpers
    # ------------------------------------------------------------------

    def _build_memory_messages(
        self,
        memory_context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        if not memory_context:
            return []

        memory_lines: List[str] = []
        short_term_memories = memory_context.get("short_term_memories", [])
        if short_term_memories:
            formatted_memories = []
            for item in short_term_memories:
                role = item.get("role", "unknown")
                content = item.get("content", "")
                multimodal_payload = item.get("multimodal_payload")
                suffix = f" [多模态摘要: {multimodal_payload}]" if multimodal_payload else ""
                formatted_memories.append(f"{role}: {content}{suffix}")
            memory_lines.append("短期记忆：\n" + "\n".join(formatted_memories))

        user_profile = memory_context.get("user_profile")
        if user_profile:
            profile_summary = user_profile.get("profile_summary")
            stable_preferences = user_profile.get("stable_preferences")
            preferred_topics = user_profile.get("preferred_topics")
            memory_lines.append(
                "长期用户画像：\n"
                f"- 用户画像摘要：{profile_summary or '无'}\n"
                f"- 稳定偏好：{stable_preferences or '无'}\n"
                f"- 关注主题：{preferred_topics or '无'}"
            )

        relevant_events = memory_context.get("relevant_events", [])
        if relevant_events:
            formatted_events = []
            for event in relevant_events:
                formatted_events.append(
                    f"{event.get('event_time')}: {event.get('title')} - {event.get('summary') or ''}"
                )
            memory_lines.append("相关关键事件：\n" + "\n".join(formatted_events))

        if not memory_lines:
            return []
        return [{"role": "system", "content": "\n\n".join(memory_lines)}]

    def _build_runtime_planner_debug(
        self,
        planner_debug: Dict[str, Any],
        execution_plan: Dict[str, Any],
        tool_outputs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            **planner_debug,
            "execution_plan_prompt": self._format_execution_plan(execution_plan),
            "executed_tools": [
                {
                    "tool_name": item["tool_name"],
                    "arguments": item["arguments"],
                }
                for item in tool_outputs
            ],
        }

    # ------------------------------------------------------------------
    # Multimodal user content
    # ------------------------------------------------------------------

    def _build_user_content(
        self,
        user_query: str,
        images: List[Dict[str, Any]],
    ) -> Any:
        if not images:
            return user_query

        content: List[Dict[str, Any]] = [{"type": "text", "text": user_query}]
        for image in images:
            image_url = image.get("image_url")
            image_base64 = image.get("image_base64")
            mime_type = image.get("mime_type", "image/png")
            if image_url and not image_base64:
                image_base64, mime_type = self._try_load_local_image(image_url, mime_type)
            if image_base64:
                image_url = f"data:{mime_type};base64,{image_base64}"
            if image_url:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                        },
                    }
                )
        return content

    def _try_load_local_image(
        self,
        image_url: str,
        mime_type: str,
    ) -> tuple[Optional[str], str]:
        image_path = Path(image_url).expanduser()
        if not image_path.is_file():
            return None, mime_type

        detected_mime_type, _ = mimetypes.guess_type(image_path.name)
        with image_path.open("rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded, detected_mime_type or mime_type

    # ------------------------------------------------------------------
    # Tool registry
    # ------------------------------------------------------------------

    def _build_tool_registry(self) -> Dict[str, ToolHandler]:
        def make_handler(name: str) -> ToolHandler:
            def handler(**kwargs: Any) -> Dict[str, Any]:
                # The MCP server opens its own database Session, so the tool
                # result is obtained end-to-end over the MCP protocol.
                return self.mcp_client.call_tool(name, kwargs)

            return handler

        return {name: make_handler(name) for name in MCP_ALLOWED_TOOLS}

    def _tool_specs(self) -> List[Dict[str, Any]]:
        specs: List[Dict[str, Any]] = []
        for tool in self.mcp_client.list_tools():
            if tool["name"] not in MCP_ALLOWED_TOOLS:
                continue
            specs.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": self._openai_parameters(tool["inputSchema"]),
                    },
                }
            )
        return specs

    @staticmethod
    def _openai_parameters(input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Build an OpenAI-compatible ``parameters`` object from an MCP schema.

        FastMCP marks optional parameters as ``anyOf: [{...}, {type: null}]``
        plus ``default``/``title``.  Providers may reject those JSON-Schema
        extras, so this collapses each property to its non-null type and drops
        the decorative keys while preserving ``required``.
        """
        parameters: Dict[str, Any] = {
            "type": input_schema.get("type", "object"),
            "properties": {},
        }
        for name, prop in (input_schema.get("properties") or {}).items():
            parameters["properties"][name] = PatientAgent._openai_property(prop)
        required = input_schema.get("required")
        if required:
            parameters["required"] = required
        return parameters

    @staticmethod
    def _openai_property(prop: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(prop, dict):
            return {"type": "string"}
        candidates = prop.get("anyOf")
        if isinstance(candidates, list):
            for candidate in candidates:
                if isinstance(candidate, dict) and candidate.get("type") != "null":
                    return {
                        key: value
                        for key, value in candidate.items()
                        if key not in ("default", "title")
                    }
            return {"type": "string"}
        return {
            key: value
            for key, value in prop.items()
            if key not in ("default", "title")
        }
