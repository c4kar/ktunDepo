from agent.models import ProcessingContext, UnifiedProcessingResult

class MaterialProcessor:
    def __init__(self):
        pass

    def process(self, context: ProcessingContext) -> UnifiedProcessingResult:
        # Stub implementation to be expanded in later tasks
        return UnifiedProcessingResult(
            success=False,
            decision="NOT_IMPLEMENTED",
            reason="Core processor stub"
        )
