from typing import List, Any, Literal
from dataclasses import dataclass
from .short_term_memory import Message

@dataclass
class RouterDecision:
    """
    Data structure representing the router's decision for a specific piece of information.
    """
    decision: Literal["promote", "drop"]
    reason: str
    content: Any

class PromoteOrDropRouter:
    """
    Evaluates messages from the Short-Term Memory when it reaches capacity.
    Decides whether to promote information to Episodic Memory or drop it entirely.
    Strict Rule: This router NEVER writes directly to Semantic Memory.
    """
    def __init__(self, llm_client=None):
        # The llm_client is used to call the AI model to make intelligent routing decisions
        self.llm_client = llm_client

    def evaluate_context(self, messages: List[Message]) -> List[RouterDecision]:
        """
        Analyzes a batch of messages from STM and outputs routing decisions.
        """
        decisions: List[RouterDecision] = []
        
        # Format messages for the LLM prompt
        formatted_context = self._format_for_llm(messages)
        
        # In a real implementation, you will pass 'formatted_context' to the LLM here.
        # The LLM should be instructed to return a JSON array of decisions.
        # Example prompt instruction: 
        # "Analyze this conversation. For each significant event or preference, decide to 'promote'. 
        # For routine chatter, decide to 'drop'. Always provide a 'reason'."
        
        # ---------------------------------------------------------
        # Placeholder for LLM invocation and JSON parsing:
        # parsed_llm_response = self.llm_client.generate(prompt=...)
        # ---------------------------------------------------------
        
        # Mocking the process to demonstrate the expected logic flow:
        for msg in messages:
            if self._contains_valuable_info(msg):
                decisions.append(
                    RouterDecision(
                        decision="promote",
                        reason="Contains user preference or significant action.",
                        content=msg.content
                    )
                )
            else:
                decisions.append(
                    RouterDecision(
                        decision="drop",
                        reason="Routine conversational filler, lacks long-term value.",
                        content=msg.content
                    )
                )
                
        return decisions

    def _format_for_llm(self, messages: List[Message]) -> str:
        """Helper method to format messages into a readable string for the LLM."""
        return "\n".join([f"[{msg.role}] {msg.content}" for msg in messages])

    def _contains_valuable_info(self, msg: Message) -> bool:
        """
        Mock helper method. 
        In production, the LLM handles this evaluation natively via the prompt.
        """
        # Example naive check
        content_str = str(msg.content).lower()
        keywords = ["prefer", "change", "failed", "dispatched", "update_inventory"]
        return any(keyword in content_str for keyword in keywords)