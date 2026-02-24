import base64
from typing import List, Optional, Tuple
from loguru import logger

from app.core.http_client import download_image
from app.core.config import settings
from app.core.exceptions import ExternalImageDownloadError, ExternalImageNotAllowedError
from app.models.claude import (
    ImageType,
    InputMessage,
    Role,
    ServerToolUseContent,
    TextContent,
    ImageContent,
    ThinkingContent,
    ToolResultContent,
    ToolUseContent,
    URLImageSource,
    Base64ImageSource,
)


async def process_messages(
    messages: List[InputMessage], system: Optional[str | List[TextContent]] = None
) -> Tuple[str, List[Base64ImageSource]]:
    if isinstance(system, str):
        merged_text = system
    elif system:
        merged_text = "\n".join(item.text for item in system)
    else:
        merged_text = ""

    if settings.use_real_roles:
        human_prefix = f"\x08{settings.human_name}: "
        assistant_prefix = f"\x08{settings.assistant_name}: "
    else:
        human_prefix = f"{settings.human_name}: "
        assistant_prefix = f"{settings.assistant_name}: "

    images: List[Base64ImageSource] = []
    current_role = Role.USER

    for message in messages:
        if message.role != current_role:
            if merged_text.endswith("\n"):
                merged_text = merged_text[:-1]

            if message.role == Role.USER:
                merged_text += f"\n\n{human_prefix}"
            elif message.role == Role.ASSISTANT:
                merged_text += f"\n\n{assistant_prefix}"

        current_role = message.role

        if isinstance(message.content, str):
            merged_text += f"{message.content}\n"
        else:
            for block in message.content:
                if isinstance(block, TextContent):
                    merged_text += f"{block.text}\n"
                elif isinstance(block, ThinkingContent):
                    merged_text += f"<\x08antml:thinking>\n{block.thinking}\n</\x08antml:thinking>\n"
                elif isinstance(block, ToolUseContent) or isinstance(
                    block, ServerToolUseContent
                ):
                    merged_text += f'<\x08antml:function_calls>\n<\x08antml:invoke name="{block.name}">\n'
                    for key, value in block.input.items():
                        merged_text += f'<\x08antml:parameter name="{key}">{value}</\x08antml:parameter>\n'
                    merged_text += "</\x08antml:invoke>\n</\x08antml:function_calls>\n"
                elif isinstance(block, ToolResultContent):
                    text_content = ""
                    if isinstance(block.content, str):
                        text_content = f"{block.content}"
                    else:
                        for content_block in block.content:
                            if isinstance(content_block, TextContent):
                                text_content += f"{content_block.text}\n"
                            elif isinstance(content_block, ImageContent):
                                if isinstance(content_block.source, Base64ImageSource):
                                    images.append(content_block.source)
                                elif isinstance(content_block.source, URLImageSource):
                                    image_source = await extract_image_from_url(
                                        content_block.source.url
                                    )
                                    if image_source:
                                        images.append(image_source)
                                        text_content += "(image attached)\n"
                            if text_content.endswith("\n"):
                                text_content = text_content[:-1]
                    merged_text += (
                        f"<function_results>{text_content}</function_results>"
                    )
                elif isinstance(block, ImageContent):
                    if isinstance(block.source, Base64ImageSource):
                        images.append(block.source)
                    elif isinstance(block.source, URLImageSource):
                        image_source = await extract_image_from_url(block.source.url)
                        if image_source:
                            images.append(image_source)

        if merged_text.endswith("\n"):
            merged_text = merged_text[:-1]

    return (merged_text, images)


async def extract_image_from_url(url: str) -> Optional[Base64ImageSource]:
    """Extract base64 image from data URL or download from external URL."""

    if url.startswith("data:"):
        try:
            metadata, base64_data = url.split(",", 1)
            media_info = metadata[5:]
            media_type, encoding = media_info.split(";", 1)

            return Base64ImageSource(
                type=encoding, media_type=media_type, data=base64_data
            )
        except Exception:
            logger.warning("Failed to extract image from data URL. Skipping image.")
            return None

    elif settings.allow_external_images and (
        url.startswith("http://") or url.startswith("https://")
    ):
        try:
            logger.debug(f"Downloading external image: {url}")

            content, content_type = await download_image(
                url, timeout=settings.request_timeout
            )
            base64_data = base64.b64encode(content).decode("utf-8")

            return Base64ImageSource(
                type="base64", media_type=ImageType(content_type), data=base64_data
            )
        except Exception:
            raise ExternalImageDownloadError(url)

    elif not settings.allow_external_images and (
        url.startswith("http://") or url.startswith("https://")
    ):
        raise ExternalImageNotAllowedError(url)
    else:
        logger.warning(f"Unsupported URL format: {url}, Skipping image.")
        return None
