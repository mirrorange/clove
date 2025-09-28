import time
import base64
import random
import string
from typing import List
from loguru import logger

from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.services.session import session_manager
from app.models.internal import ClaudeWebRequest, Attachment
from app.core.exceptions import NoValidMessagesError
from app.core.config import settings
from app.utils.messages import process_messages


class ClaudeWebProcessor(BaseProcessor):
    """Claude AI processor that handles session management, request building, and sending to Claude AI."""

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Claude AI processor that:
        1. Gets or creates a Claude session
        2. Builds ClaudeWebRequest from messages_api_request
        3. Sends the request to Claude.ai

        Requires:
            - messages_api_request in context

        Produces:
            - claude_session in context
            - claude_web_request in context
            - original_stream in context
        """
        if context.original_stream:
            logger.debug("Skipping ClaudeWebProcessor due to existing original_stream")
            return context

        if not context.messages_api_request:
            logger.warning(
                "Skipping ClaudeWebProcessor due to missing messages_api_request"
            )
            return context

        # Step 1: Get or create Claude session
        if not context.claude_session:
            session_id = context.metadata.get("session_id")
            if not session_id:
                session_id = f"session_{int(time.time() * 1000)}"
                context.metadata["session_id"] = session_id

            logger.debug(f"Creating new session: {session_id}")
            context.claude_session = await session_manager.get_or_create_session(
                session_id
            )

        # Step 2: Build ClaudeWebRequest
        if not context.claude_web_request:
            request = context.messages_api_request

            if not request.messages:
                raise NoValidMessagesError()

            merged_text, images, documents = await process_messages(
                request.messages, request.system
            )
            if not merged_text:
                raise NoValidMessagesError()

            if settings.padtxt_length > 0:
                pad_tokens = settings.pad_tokens or (
                    string.ascii_letters + string.digits
                )
                pad_text = "".join(random.choices(pad_tokens, k=settings.padtxt_length))
                merged_text = pad_text + merged_text
                logger.debug(
                    f"Added {settings.padtxt_length} padding tokens to the beginning of the message"
                )

            image_file_ids: List[str] = []
            if images:
                for i, image_source in enumerate(images):
                    try:
                        # Convert base64 to bytes
                        image_data = base64.b64decode(image_source.data)

                        # Upload to Claude
                        file_id = await context.claude_session.upload_file(
                            file_data=image_data,
                            filename=f"image_{i}.png",  # Default filename
                            content_type=image_source.media_type,
                        )
                        image_file_ids.append(file_id)
                        logger.debug(f"Uploaded image {i}: {file_id}")
                    except Exception as e:
                        logger.error(f"Failed to upload image {i}: {e}")

            await context.claude_session._ensure_conversation_initialized()

            paprika_mode = (
                "extended"
                if (
                    context.claude_session.account.is_pro
                    and request.thinking
                    and request.thinking.type == "enabled"
                )
                else None
            )

            await context.claude_session.set_paprika_mode(paprika_mode)

            web_request = ClaudeWebRequest(
                max_tokens_to_sample=request.max_tokens,
                attachments=[Attachment.from_text(merged_text)],
                files=image_file_ids,
                model=request.model,
                rendering_mode="messages",
                prompt=settings.custom_prompt or "",
                timezone="UTC",
                tools=request.tools or [],
            )

            context.claude_web_request = web_request
            logger.debug(f"Built web request with {len(image_file_ids)} images")

        # Step 3: Send to Claude
        logger.debug(
            f"Sending request to Claude.ai for session {context.claude_session.session_id}"
        )

        request_dict = context.claude_web_request.model_dump(exclude_none=True)
        context.original_stream = await context.claude_session.send_message(
            request_dict
        )

        return context
