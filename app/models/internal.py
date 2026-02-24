from typing import List, Optional
from pydantic import BaseModel, Field
from .claude import Tool


class Attachment(BaseModel):
    extracted_content: str
    file_name: str
    file_type: str
    file_size: int

    @classmethod
    def from_text(cls, content: str) -> "Attachment":
        """Create text attachment."""
        return cls(
            extracted_content=content,
            file_name="paste.txt",
            file_type="txt",
            file_size=len(content),
        )


class ClaudeWebRequest(BaseModel):
    max_tokens_to_sample: int
    attachments: List[Attachment]
    files: List[str] = Field(default_factory=list)
    model: Optional[str] = None
    rendering_mode: str = "messages"
    prompt: str = ""
    timezone: str
    tools: List[Tool] = Field(default_factory=list)


class UploadResponse(BaseModel):
    file_uuid: str
