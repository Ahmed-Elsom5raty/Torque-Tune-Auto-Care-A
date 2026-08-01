
"""
mcp-server/rag/search_policy_tool.py

Option A (Search Over Your Data): one new tool, search_policy, giving the
model keyword search over the warehouse & inventory policy instead of
requiring it to read the whole ~1,800-character document on every turn.

The policy is already exposed as a Resource (warehouse://policy/inventory,
see resources/resources.py) for the case where the model should read it
once in full. search_policy is for the more common case: the model has
one specific question (a threshold, a rule, who's authorized) and just
needs the relevant section back.
"""

from app import mcp
from .policy_index import policy_store


@mcp.tool()
def search_policy(query: str, top_k: int = 3):
    """
    Search the Auto Care warehouse & inventory policy by keyword and
    return the most relevant section(s) instead of the full document.

    Use this for specific questions about: stock thresholds (low/out of
    stock rules), who is authorized to change inventory, when a stock
    change requires human confirmation (elicitation triggers), what
    counts as a valid alternative part, or audit-trail requirements.
    """
    matches = policy_store.query(query_text=query, top_k=top_k)

    if not matches:
        return "No relevant policy section found for this query."

    return "\n\n---\n\n".join(m["text"] for m in matches)
