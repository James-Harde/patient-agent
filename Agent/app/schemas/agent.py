

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class AgentImageInput(BaseModel):
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    mime_type: str = "image/png"

    @model_validator(mode="after")
    def validate_source(self) -> "AgentImageInput":
        if not self.image_url and not self.image_base64:
            raise ValueError("image_url or image_base64 is required")
        return self


class AgentQueryRequest(BaseModel):
    query: str
    images: List[AgentImageInput] = Field(default_factory=list)
    debug_planner: bool = False
    enable_speech: bool = False
    speech_voice: str = "longanyang"
    speech_format: str = "mp3"


class AgentToolOutput(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]


class AgentQueryResponse(BaseModel):
    answer: str
    tool_outputs: List[AgentToolOutput]
    planner_debug: Optional[Dict[str, Any]] = None
    speech_mime_type: Optional[str] = None
    speech_model: Optional[str] = None
    speech_voice: Optional[str] = None
    speech_file_path: Optional[str] = None
    speech_download_url: Optional[str] = None
