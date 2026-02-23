from typing import Optional, List, Union, Literal, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator
from enum import Enum


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ImageType(str, Enum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    WEBP = "image/webp"


# Image sources
class Base64ImageSource(BaseModel):
    type: Literal["base64"] = "base64"
    media_type: ImageType = Field(..., description="MIME type of the image")
    data: str = Field(..., description="Base64 encoded image data")


class URLImageSource(BaseModel):
    type: Literal["url"] = "url"
    url: str = Field(..., description="URL of the image")


class FileImageSource(BaseModel):
    type: Literal["file"] = "file"
    file_uuid: str = Field(..., description="UUID of the uploaded file")


# Web search result
class WebSearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["web_search_result"]
    title: str
    url: str
    encrypted_content: str
    page_age: Optional[str] = None


# Cache control
class CacheControl(BaseModel):
    type: Literal["ephemeral"]


# Content types
class TextContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["text"]
    text: str
    cache_control: Optional[CacheControl] = None


class ImageContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["image"]
    source: Base64ImageSource | URLImageSource | FileImageSource
    cache_control: Optional[CacheControl] = None


class ThinkingContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["thinking"]
    thinking: str


# redacted_thinking 块：API 可能返回被审查的思考内容
class RedactedThinkingContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["redacted_thinking"]
    data: str


class ToolUseContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Any]
    cache_control: Optional[CacheControl] = None


class ToolResultContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["tool_result"]
    tool_use_id: str
    content: str | List[TextContent | ImageContent]
    is_error: Optional[bool] = False
    cache_control: Optional[CacheControl] = None


class ServerToolUseContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["server_tool_use"]
    id: str
    name: str
    input: Dict[str, Any]
    cache_control: Optional[CacheControl] = None


class WebSearchToolResultContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["web_search_tool_result"]
    tool_use_id: str
    content: List[WebSearchResult]
    cache_control: Optional[CacheControl] = None


ContentBlock = Union[
    TextContent,
    ImageContent,
    ThinkingContent,
    RedactedThinkingContent,
    ToolUseContent,
    ToolResultContent,
    ServerToolUseContent,
    WebSearchToolResultContent,
]


class InputMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: Role
    content: Union[str, List[ContentBlock]]


class ThinkingOptions(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["enabled", "disabled", "adaptive"] = "disabled"
    budget_tokens: Optional[int] = None


class ToolChoice(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["auto", "any", "tool", "none"] = "auto"
    name: Optional[str] = None
    disable_parallel_tool_use: Optional[bool] = None


class Tool(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    input_schema: Any
    description: Optional[str] = None


class OutputConfig(BaseModel):
    """Output configuration (effort, format, etc). effort and structured outputs are now GA."""

    model_config = ConfigDict(extra="allow")
    effort: Optional[Literal["low", "medium", "high", "max"]] = None


class OutputFormat(BaseModel):
    """Output format for structured outputs (deprecated, use output_config.format instead)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True, serialize_by_alias=True)
    type: Literal["json_schema"]
    schema_: Optional[Dict[str, Any]] = Field(default=None, alias="schema")


class ServerToolUsage(BaseModel):
    model_config = ConfigDict(extra="allow")
    web_search_requests: Optional[int] = None


class Usage(BaseModel):
    model_config = ConfigDict(extra="allow")
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: Optional[int] = 0
    cache_read_input_tokens: Optional[int] = 0
    server_tool_use: Optional[ServerToolUsage] = None


class MessagesAPIRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str = Field(default="claude-opus-4-20250514")
    messages: List[InputMessage]
    max_tokens: int = Field(default=8192, ge=1)
    system: Optional[str | List[TextContent]] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=1)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    top_k: Optional[int] = Field(default=None, ge=0)
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None
    thinking: Optional[ThinkingOptions] = None
    tool_choice: Optional[ToolChoice] = None
    tools: Optional[List[Tool]] = None
    output_config: Optional[OutputConfig] = None
    output_format: Optional[OutputFormat] = None

    @model_validator(mode="after")
    def validate_thinking_tokens(self) -> "MessagesAPIRequest":
        """Ensure max_tokens > thinking.budget_tokens when thinking is enabled."""
        if (
            self.thinking
            and self.thinking.type == "enabled"
            and self.thinking.budget_tokens is not None
            and self.max_tokens <= self.thinking.budget_tokens
        ):
            self.max_tokens = self.thinking.budget_tokens + 1
        return self


class Message(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    type: Literal["message"]
    role: Literal["assistant"]
    content: List[ContentBlock]
    model: str
    stop_reason: Optional[
        Literal[
            "end_turn",
            "max_tokens",
            "stop_sequence",
            "tool_use",
            "pause_turn",
            "refusal",
        ]
    ] = None
    stop_sequence: Optional[str] = None
    usage: Optional[Usage] = None
