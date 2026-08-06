"""
mcp-server/rag/llm_client.py

One seam for every LLM call the RAG layer needs:
  - the final "generate" step (naive / hybrid / agentic RAG)
  - the "should I retrieve again?" decision inside agentic RAG
  - the Self-RAG-style relevance/support checks (self_rag_check.py)

Production: set ANTHROPIC_API_KEY (in your .env, never committed --
see the project's existing .gitignore). Then `llm_call()` calls the real
Claude API.

This lab sandbox has no API key configured, so `llm_call()` falls back to
a clearly-labeled MOCK responder. The mock is heuristic, not a language
model -- it exists so retrieval_eval/ can run end-to-end and produce real
token/latency numbers for the *retrieval* side (which is what this lab
grades) without requiring secrets. Swap point is this file only; nothing
in naive_rag.py / hybrid_rag.py / agentic_rag.py / self_rag_check.py needs
to change once a real key is set.
"""

import json
import os
import re

MODEL = "claude-sonnet-4-6"
_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def llm_call(system: str, user: str, want_json: bool = False) -> tuple[str, int, int]:
    """Returns (response_text, input_tokens, output_tokens)."""
    if _API_KEY:
        return _real_call(system, user)
    return _mock_call(system, user, want_json)


def _real_call(system: str, user: str) -> tuple[str, int, int]:
    import anthropic

    client = anthropic.Anthropic(api_key=_API_KEY)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, resp.usage.input_tokens, resp.usage.output_tokens


# ---------------------------------------------------------------------
# MOCK responder -- offline stand-in, used only when no API key is set.
# ---------------------------------------------------------------------
def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # rough chars/4 estimate, fine for eval comparisons


def _mock_call(system: str, user: str, want_json: bool) -> tuple[str, int, int]:
    in_tokens = _approx_tokens(system) + _approx_tokens(user)

    if want_json:
        text = _mock_decision(user)
    else:
        text = _mock_answer(user)

    out_tokens = _approx_tokens(text)
    return text, in_tokens, out_tokens


def _mock_answer(user_prompt: str) -> str:
    """Extractive stand-in for 'generate': pulls the context block out of
    the prompt and returns its most query-relevant sentences. A real LLM
    call would paraphrase/synthesize instead of extracting verbatim."""
    context_match = re.search(r"Context:\n(.*?)\n\nQuestion:", user_prompt, re.S)
    question_match = re.search(r"Question:\n(.*)", user_prompt, re.S)
    context = context_match.group(1) if context_match else user_prompt
    question = question_match.group(1).strip() if question_match else ""

    q_tokens = set(re.findall(r"[a-z0-9]+", question.lower()))
    sentences = re.split(r"(?<=[.!?])\s+", context)
    scored = sorted(
        sentences,
        key=lambda s: len(q_tokens & set(re.findall(r"[a-z0-9]+", s.lower()))),
        reverse=True,
    )
    best = [s.strip() for s in scored[:3] if s.strip()]
    return " ".join(best) if best else "No answer could be derived from the retrieved context."


def _mock_decision(user_prompt: str) -> str:
    """Heuristic stand-in for agentic RAG's 'do I need to retrieve again?'
    decision. Looks for multi-hop signals (multiple clauses / 'and' /
    'before') to decide whether a second retrieval round is warranted."""
    multi_hop_signals = len(re.findall(r"\band\b|\bbefore\b|\bthen\b", user_prompt.lower()))
    needs_more = multi_hop_signals >= 2
    decision = {
        "reasoning": (
            "Question references multiple conditions that likely span more "
            "than one document section." if needs_more else
            "Question looks like a single, direct lookup."
        ),
        "retrieve_again": needs_more,
        "next_query": None,
    }
    return json.dumps(decision)
