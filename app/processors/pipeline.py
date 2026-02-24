from typing import List, Optional
from loguru import logger

from app.processors.base import BaseContext, BaseProcessor


class ProcessingPipeline(BaseProcessor):
    """
    Main pipeline for processing Claude requests.
    """

    def __init__(self, processors: Optional[List[BaseProcessor]] = None):
        """
        Initialize the pipeline with processors.

        Args:
            processors: List of processors to use. If None, default processors are used.
        """
        self.processors = processors

        logger.debug(f"Initialized pipeline with {len(self.processors)} processors")
        for processor in self.processors:
            logger.debug(f"  - {processor.name}")

    async def process(self, context: BaseContext) -> BaseContext:
        """
        Process a request through the pipeline.

        Args:
            context: The processing context

        Returns:
            Updated context.
        """

        logger.debug("Starting pipeline processing")

        # Process through each processor
        for i, processor in enumerate(self.processors):
            if processor.name in context.metadata.get("skip_processors", []):
                logger.debug(
                    f"Skipping processor {processor.name} due to being in skip_processors list"
                )
                continue

            logger.debug(
                f"Running processor {i + 1}/{len(self.processors)}: {processor.name}"
            )

            context = await processor.process(context)

            if context.metadata.get("stop_pipeline", False):
                logger.debug(f"Pipeline stopped by {processor.name}")
                break

        logger.debug("Pipeline processing completed successfully")
        return context
