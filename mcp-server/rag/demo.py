"""
mcp-server/rag/demo.py

Demo query that only search_policy can answer correctly: the exact
elicitation thresholds (bring-to-zero, or a decrease of more than 20
units) live only inside company_policy.md. No other tool in this
project (search_spare_part, check_stock, suggest_alternative,
update_inventory) can answer "does this specific decrease need
confirmation?" -- that logic is applied at runtime inside
update_inventory, but nothing surfaces the *rule itself* in words
except this tool (or reading the whole resource by hand).

Run:
    python rag/demo.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import mcp          # noqa: E402
from rag import search_policy_tool  # noqa: E402,F401  (registers the tool)


def ask(query: str, top_k: int = 1) -> str:
    return mcp._tools["search_policy"](query=query, top_k=top_k)


if __name__ == "__main__":
    print("--- Query 1: a decrease that stays above zero ---")
    q1 = "If I decrease a part by 15 units, does it need human confirmation?"
    print(f"Q: {q1}\n")
    print(ask(q1))

    print("\n\n--- Query 2: who is allowed to change inventory ---")
    q2 = "Can a technician call update_inventory?"
    print(f"Q: {q2}\n")
    print(ask(q2))

    print("\n\n--- Query 3: alternative part validity ---")
    q3 = "Can a discontinued part be suggested as an alternative?"
    print(f"Q: {q3}\n")
    print(ask(q3))
