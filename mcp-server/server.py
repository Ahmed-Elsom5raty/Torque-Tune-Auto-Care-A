mcp-server/server.py

CAPABILITY NEGOTIATION (Protocol Concern #1)
=============================================
This file implements the real initialize / initialized handshake described
in the MCP spec (modelcontextprotocol.io). Nothing here is assumed by the
client -- the server declares exactly what it supports, and the client
(agent/client.py) reads that declaration before relying on any capability.

Transport: stdio (line-delimited JSON-RPC 2.0 messages), per the task's
requirement to start local/stdio during development. The transport will
move to Streamable HTTP later in the project; this module only concerns
itself with the negotiation logic, which stays the same either way.

Why this matters for our problem (Auto Care spare parts inventory):
- The server only supports `elicitation` and `resources` right now (this
  part of the project). A client that does NOT check for `elicitation`
  support and blindly calls a risky write tool could get stuck waiting for
  a confirmation prompt that will never come from a non-interactive client.
- Declaring capabilities up front, and having the client check them, is
  what lets a client safely decide: "this server can pause for human
  confirmation, so it is safe to expose update_inventory" vs. "this
  server/client pairing can't do that, so fall back to read-only tools."
"""

import json
import sys


SERVER_INFO = {
    "name": "auto-care-inventory-mcp-server",
    "version": "0.1.0",
}

# What this server ACTUALLY supports right now. This is the single source
# of truth -- nothing downstream should assume support beyond this dict.
SERVER_CAPABILITIES = {
    "resources": {
        "listChanged": False,  # resources here are static (warehouse policy doc)
    },
    "elicitation": {},  # server can call elicitation/create mid-tool-call
    # NOTE: "tools" and "notifications" capabilities are declared by the
    # teammate's tool-serving code once tools/list_changed is wired in --
    # this module only owns the negotiation contract itself.
}


def send_message(message: dict) -> None:
    """Write one JSON-RPC message as a single line to stdout."""
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def log(message: str) -> None:
    """Server-side logging goes to stderr so it never corrupts the
    stdout JSON-RPC stream."""
    sys.stderr.write(f"[server] {message}\n")
    sys.stderr.flush()


def handle_initialize(request: dict) -> dict:
    client_info = request.get("params", {}).get("clientInfo", {})
    log(f"Received initialize from client: {client_info.get('name', 'unknown')}")

    return {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": SERVER_INFO,
            "capabilities": SERVER_CAPABILITIES,
        },
    }


def main() -> None:
    initialized = False
    log("Server started, waiting for initialize request...")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            log(f"Ignoring malformed message: {line!r}")
            continue

        method = message.get("method")

        if method == "initialize":
            response = handle_initialize(message)
            send_message(response)
            log(f"Declared capabilities: {list(SERVER_CAPABILITIES.keys())}")

        elif method == "notifications/initialized":
            # This is a notification (no "id", no response expected).
            # Only after this arrives is the session considered ready.
            initialized = True
            log("Received initialized notification. Handshake complete.")

        elif not initialized:
            # Defensive: refuse to do anything else until the handshake
            # is actually done, instead of silently assuming it happened.
            log(f"Rejecting '{method}' -- session not initialized yet.")
            if "id" in message:
                send_message({
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "error": {
                        "code": -32002,
                        "message": "Server not initialized. Send 'initialize' first.",
                    },
                })

        else:
            log(f"Received '{method}' after successful handshake (not yet implemented in this module).")


if __name__ == "__main__":
    main()
