from typing import Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, RootModel, ConfigDict

from .claude import ContentBlock, Message, Usage


# Base event types
class BaseEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str


# Delta types
class TextDelta(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["text_delta"]
    text: str


class InputJsonDelta(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["input_json_delta"]
    partial_json: str


class ThinkingDelta(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["thinking_delta"]
    thinking: str


class SignatureDelta(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["signature_delta"]
    signature: str


Delta = Union[TextDelta, InputJsonDelta, ThinkingDelta, SignatureDelta]


class MessageDeltaData(BaseModel):
    model_config = ConfigDict(extra="allow")
    stop_reason: Optional[
        Literal["end_turn", "max_tokens", "stop_sequence", "tool_use", "pause_turn", "refusal"]
    ] = None
    stop_sequence: Optional[str] = None


# Error model
class ErrorInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    message: str


# Event models
class MessageStartEvent(BaseEvent):
    type: Literal["message_start"]
    message: Message


class ContentBlockStartEvent(BaseEvent):
    type: Literal["content_block_start"]
    index: int
    content_block: ContentBlock


class ContentBlockDeltaEvent(BaseEvent):
    type: Literal["content_block_delta"]
    index: int
    delta: Delta


class ContentBlockStopEvent(BaseEvent):
    type: Literal["content_block_stop"]
    index: int


class MessageDeltaEvent(BaseEvent):
    type: Literal["message_delta"]
    delta: MessageDeltaData
    usage: Optional[Usage] = None


class MessageStopEvent(BaseEvent):
    type: Literal["message_stop"]


class PingEvent(BaseEvent):
    type: Literal["ping"]


class ErrorEvent(BaseEvent):
    type: Literal["error"]
    error: ErrorInfo


class UnknownEvent(BaseEvent):
    type: str
    data: Dict[str, Any]


# Union of all streaming event types
class StreamingEvent(RootModel):
    root: Union[
        MessageStartEvent,
        ContentBlockStartEvent,
        ContentBlockDeltaEvent,
        ContentBlockStopEvent,
        MessageDeltaEvent,
        MessageStopEvent,
        PingEvent,
        ErrorEvent,
        UnknownEvent,
    ]
