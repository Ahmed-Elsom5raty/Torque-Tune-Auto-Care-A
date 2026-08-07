"""
agent/client.py

A minimal MCP client for the Auto Care spare-parts inventory server.

Run directly for an end-to-end walkthrough against a seeded demo
database, exercising every protocol concern in one pass:

    python agent/client.py

What it does, in order:
  1. capability negotiation -- a real initialize/initialized exchange,
     and checks the server's declared capabilities before relying on them
  2. tools/list -- discovers only the tools a technician session can see
  3. tools/call -- a read-only call (search_spare_part)
  4. a role change (technician -> manager) that genuinely grows the tool
     set, pushing notifications/tools/list_changed
  5. resources/read -- reads the static warehouse policy instead of
     calling a tool for it
  6. tools/call -- update_inventory on a change that trips the
     elicitation trigger (decreasing a part to zero), pausing for
     confirmation via elicitation/create
  7. tools/call -- generate_inventory_report, a long-running call that
     reports real progress instead of blocking silently

Swap wire_demo_database() for a real connection once databases/db.py has
one configured -- see the comment at the bottom of this file.
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER_ROOT = ROOT / "mcp-server"
AGENT_ROOT = Path(__file__).resolve().parent

for path in (str(ROOT), str(MCP_SERVER_ROOT), str(AGENT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)


def wire_demo_database() -> None:
    """
    Point databases.db.get_connection at the seeded in-memory SQLite demo
    DB. Must run before anything imports `from databases.db import
    get_connection`, since that binds the function at import time.
    """
    import databases.db as db
    from demo_db import build_demo_connection

    db.get_connection = build_demo_connection


wire_demo_database()

import server  # noqa: E402  (registers tools + resources, wires negotiation onto mcp)
from negotiation import negotiation  # noqa: E402
from notifications import notifier  # noqa: E402
from fastmcp import ElicitationResult  # noqa: E402


class CLIContext:
    """
    The Context this client hands to tools. Where the test-suite's stub
    context silently auto-accepts, this one actually surfaces
    elicitation/create and progress updates to whoever is running the
    demo -- prompting on the terminal instead of proceeding silently.
    """

    def __init__(self, auto_confirm: bool | None = None):
        # auto_confirm=None -> prompt interactively (real demo use).
        # auto_confirm=True/False -> skip the prompt (used by the test suite).
        self.auto_confirm = auto_confirm

    async def elicit(self, message: str, schema: dict | None = None) -> ElicitationResult:
        print(f"\n  [elicitation/create] {message}")
        if self.auto_confirm is not None:
            confirmed = self.auto_confirm
        else:
            confirmed = input("  Confirm? [y/N]: ").strip().lower() == "y"
        return ElicitationResult("accept" if confirmed else "decline", confirmed)

    async def report_progress(self, progress: float, total: float = 100) -> None:
        print(f"  [progress] {progress:.0f}/{total:.0f}")


def run_handshake(session_id: str) -> dict:
    """A real initialize/initialized exchange, not assumed."""
    response = negotiation.handle_initialize(
        {"id": 1, "params": {"clientInfo": {"name": "auto-care-cli-agent"}}}
    )
    capabilities = response["result"]["capabilities"]
    print(f"[initialize] server declares: {capabilities}")

    negotiation.handle_initialized_notification(session_id)
    assert negotiation.is_session_initialized(session_id)
    print(f"[initialized] session '{session_id}' ready")

    return capabilities


def list_visible_tools(role: str) -> list:
    """tools/list, filtered to what this session's role is allowed to see."""
    registered = set(server.mcp._tools.keys())
    return sorted(notifier.visible_tools_for_role(role) & registered)


async def main(auto_confirm: bool | None = None) -> dict:
    session_id = "demo-session-1"
    capabilities = run_handshake(session_id)

    # A client that skipped this check could offer the risky write tool
    # even if the server had no way to actually pause for confirmation.
    supports_elicitation = "elicitation" in capabilities
    print(f"[capability check] elicitation supported: {supports_elicitation}")
    if not supports_elicitation:
        print("  -> would fall back to read-only tools only; continuing for the demo")

    role = "technician"
    print(f"\n[session] starting as '{role}'")
    print(f"[tools/list] visible tools: {list_visible_tools(role)}")

    search_result = server.mcp._tools["search_spare_part"]("Brake")
    print(f"[tools/call] search_spare_part('Brake') -> {search_result}")

    # --- role change: manager authenticates, tool set genuinely changes ---
    print(f"\n[session] '{session_id}' authenticates as 'manager'")
    notification = notifier.authenticate_session(session_id, "manager")
    if notification:
        print(f"[notification] {notification} -- refreshing tool list")
    role = "manager"
    print(f"[tools/list] visible tools: {list_visible_tools(role)}")

    # --- resource: static policy, read once rather than called ---
    policy_text = server.mcp._resources["warehouse://policy/inventory"]()
    print(f"\n[resources/read] warehouse://policy/inventory ({len(policy_text)} chars)")
    print(f"  first line: {policy_text.splitlines()[0]}")

    # --- write tool that trips the elicitation trigger ---
    # Rear Brake Pad Set (part_id=2) starts at quantity=2; decreasing by 2
    # brings it to zero, which company_policy.md requires confirming.
    print("\n[tools/call] update_inventory(part_id=2, action='decrease', quantity=2, ...)")
    ctx = CLIContext(auto_confirm=auto_confirm)
    update_result = await server.mcp._tools["update_inventory"](
        part_id=2,
        action="decrease",
        quantity=2,
        reason="Sold to customer #4471",
        user_id=2,  # Priya Manager
        ctx=ctx,
    )
    print(f"[tools/call result] {update_result}")

    # --- long-running call with real progress reporting ---
    print("\n[tools/call] generate_inventory_report()")
    report_result = await server.mcp._tools["generate_inventory_report"](ctx=ctx)
    print(f"[tools/call result] {report_result}")

    return {
        "search_result": search_result,
        "notification": notification,
        "update_result": update_result,
        "report_result": report_result,
    }


if __name__ == "__main__":
    asyncio.run(main())

# To point this agent at a real database instead of the seeded SQLite demo:
# delete the wire_demo_database() call above, and make sure
# databases/db.py's get_connection() returns a live connection for
# whichever engine the README documents (see the note left on that file).