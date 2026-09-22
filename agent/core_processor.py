from agent.models import ProcessingContext, UnifiedProcessingResult
from agent.economy import add_credit
import logging

logger = logging.getLogger("core_processor")

class MaterialProcessor:
    def __init__(self):
        pass

    def process(self, context: ProcessingContext) -> UnifiedProcessingResult:
        # Stub implementation to be expanded in later tasks
        result = UnifiedProcessingResult(
            success=False,
            decision="NOT_IMPLEMENTED",
            reason="Core processor stub"
        )
        
        # --- Give-to-Get Gamification Hook ---
        # When processing is fully implemented, this block will execute
        # if the LLM quality score is >= 65.
        quality_score = context.metadata.get("quality_score", 0) # Placeholder
        user_id = context.metadata.get("user_id")
        
        if result.success and result.decision == "ACCEPT" and quality_score >= 65 and user_id:
            add_credit(user_id)
            logger.info(f"Rewarded Magnum Credit to {user_id}")
            
        return result
