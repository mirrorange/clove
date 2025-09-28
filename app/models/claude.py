from typing import Optional, List, Union, Literal, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ImageType(str, Enum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    WEBP = "image/webp"


class DocumentType(str, Enum):
    PDF = "application/pdf"


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


# Document sources
class Base64DocumentSource(BaseModel):
    type: Literal["base64"] = "base64"
    media_type: DocumentType = Field(..., description="MIME type of the document")
    data: str = Field(..., description="Base64 encoded document data")


class URLDocumentSource(BaseModel):
    type: Literal["url"] = "url"
    url: str = Field(..., description="URL of the document")


class FileDocumentSource(BaseModel):
    type: Literal["file"] = "file"
    file_uuid: str = Field(..., description="UUID of the uploaded document")


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


class DocumentContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["document"]
    source: Base64DocumentSource | URLDocumentSource | FileDocumentSource
    cache_control: Optional[CacheControl] = None


class ThinkingContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["thinking"]
    thinking: str


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
    DocumentContent,
    ThinkingContent,
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
    type: Literal["enabled", "disabled"] = "disabled"
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
    temperature: Optional[float] = Field(default=1.0, ge=0, le=1)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    top_k: Optional[int] = Field(default=None, ge=0)
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None
    thinking: Optional[ThinkingOptions] = None
    tool_choice: Optional[ToolChoice] = None
    tools: Optional[List[Tool]] = None


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
