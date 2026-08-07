from typing import Dict, Any
from .short_term_memory import ShortTermMemory
from .scratchpad import Scratchpad
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory
from .router import PromoteOrDropRouter

class MemoryManager:
    """
    Orchestrates all memory modules.
    Handles the ingestion of new messages, triggers the routing/consolidation pipeline, 
    and retrieves relevant information when a new request arrives.
    """
    def __init__(self, llm_client=None):
        self.stm = ShortTermMemory(max_capacity=10)
        self.scratchpad = Scratchpad()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory(llm_client=llm_client)
        self.router = PromoteOrDropRouter(llm_client=llm_client)

    def add_interaction(self, role: str, content: Any) -> None:
        """
        Adds a new message to Short-Term Memory. 
        If STM becomes full, it automatically triggers the Promote/Drop routing pipeline.
        """
        self.stm.add_message(role=role, content=content)
        
        if self.stm.is_full():
            # 1. Extract and clear STM
            old_messages = self.stm.clear()
            
            # 2. Route messages (Promote or Drop)
            decisions = self.router.evaluate_context(old_messages)
            
            new_episodes_for_consolidation = []
            
            # 3. Save promoted items to Episodic Memory
            for decision in decisions:
                if decision.decision == "promote":
                    self.episodic.add_episode(
                        event_type="interaction_event",
                        content=decision.content,
                        promotion_reason=decision.reason
                    )
                    # Prepare for Semantic Consolidation
                    new_episodes_for_consolidation.append({
                        "event_type": "interaction_event",
                        "content": decision.content,
                        "promotion_reason": decision.reason
                    })
            
            # 4. Trigger Semantic Consolidation to update long-term facts
            if new_episodes_for_consolidation:
                self.semantic.consolidate_episodes(new_episodes_for_consolidation)

    def retrieve_for_llm(self) -> Dict[str, Any]:
        """
        Retrieves relevant information from all memory layers.
        The output of this method is exactly what should be injected into the LLM prompt.
        """
        return {
            "semantic_memory": self.semantic.get_active_facts(),
            "episodic_memory": self.episodic.get_recent_episodes(limit=3),
            "short_term_memory": self.stm.get_context(),
            "scratchpad": self.scratchpad.get_state()
        }