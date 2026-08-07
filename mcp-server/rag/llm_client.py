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

    if not want_json:
        text = _mock_answer(user)
    elif "retrieve_again" in user:
        text = _mock_decision(user)
    elif "Is the passage below relevant" in user:
        text = _mock_relevance(user)
    elif "Is the answer below fully supported" in user:
        text = _mock_support(user)
    else:
        text = _mock_decision(user)  # generic JSON fallback

    out_tokens = _approx_tokens(text)
    return text, in_tokens, out_tokens


def _mock_answer(user_prompt: str) -> str:
    """Extractive stand-in for 'generate': pulls the context block out of
    the prompt and returns its most query-relevant sentences. A real LLM
    call would paraphrase/synthesize instead of extracting verbatim.

    Sentences are scored with a mini-IDF: a query term that appears in
    only one retrieved section (like an exact identifier "wt-317") counts
    for more than a term that appears in every section (like "warranty"),
    otherwise generic words drown out the one section that actually
    matches the identifier being asked about."""
    context_match = re.search(r"Context:\n(.*?)\n\nQuestion:", user_prompt, re.S)
    question_match = re.search(r"Question:\n(.*)", user_prompt, re.S)
    context = context_match.group(1) if context_match else user_prompt
    question = question_match.group(1).strip() if question_match else ""

    sections = context.split("\n\n---\n\n")
    q_tokens = set(re.findall(r"[a-z0-9-]+", question.lower()))

    # term -> number of distinct sections it appears in (mini document freq)
    doc_freq: dict[str, int] = {}
    for section in sections:
        for tok in set(re.findall(r"[a-z0-9-]+", section.lower())):
            doc_freq[tok] = doc_freq.get(tok, 0) + 1
    n_sections = max(len(sections), 1)

    def term_weight(tok: str) -> float:
        return n_sections / doc_freq.get(tok, n_sections)

    scored = []
    for section in sections:
        for sentence in re.split(r"(?<=[.!?])\s+", section):
            s_tokens = set(re.findall(r"[a-z0-9-]+", sentence.lower()))
            hit = q_tokens & s_tokens
            score = sum(term_weight(t) for t in hit)
            if sentence.strip():
                scored.append((score, sentence.strip()))

    scored.sort(key=lambda x: x[0], reverse=True)
    best = [s for score, s in scored[:3] if score > 0]
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


_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "does", "do", "did", "say", "says", "said", "to", "of", "in", "on",
    "for", "and", "or", "but", "with", "about", "it", "its", "as", "at",
}


def _kw_tokens(text: str) -> set[str]:
    raw = set(re.findall(r"[a-z0-9-]+", text.lower()))
    return raw - _STOPWORDS


def _mock_relevance(user_prompt: str) -> str:
    """Mock for self_rag_check's post-retrieval relevance check."""
    q_match = re.search(r"Question:\s*(.*?)\n", user_prompt)
    p_match = re.search(r"Passage:\n(.*)", user_prompt, re.S)
    question = q_match.group(1) if q_match else ""
    passage = p_match.group(1) if p_match else user_prompt

    overlap = _kw_tokens(question) & _kw_tokens(passage)
    relevant = len(overlap) >= 1
    return json.dumps({
        "relevant": relevant,
        "reasoning": f"mock heuristic: shared terms {sorted(overlap)}" if overlap else "mock heuristic: no shared terms",
    })


def _mock_support(user_prompt: str) -> str:
    """Mock for self_rag_check's post-generation support check."""
    c_match = re.search(r"Context:\n(.*?)\n\nAnswer:", user_prompt, re.S)
    a_match = re.search(r"Answer:\n(.*)", user_prompt, re.S)
    context = c_match.group(1) if c_match else ""
    answer = a_match.group(1) if a_match else ""

    a_tokens = _kw_tokens(answer)
    c_tokens = _kw_tokens(context)
    ratio = len(a_tokens & c_tokens) / len(a_tokens) if a_tokens else 0.0
    supported = ratio >= 0.5
    return json.dumps({
        "supported": supported,
        "reasoning": f"mock heuristic: {ratio:.0%} of answer terms found in context",
    })
