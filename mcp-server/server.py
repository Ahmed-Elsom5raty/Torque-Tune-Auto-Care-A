from app import mcp

# Import tools so they are registered with the MCP server
from tools import read_tools
from tools import write_tools

# Import resources so they are registered with the MCP server
from resources import resources  # noqa: F401

# Import notifications
from notifications import notifier

# Import progress
from progress import progress

# Capability negotiation: declare exactly what this server supports so a
# client checks these before relying on elicitation, a resource, or a
# runtime-changing tool set -- rather than assuming everything works.
from negotiation import negotiation

mcp.server_info = negotiation.SERVER_INFO
mcp.capabilities = negotiation.SERVER_CAPABILITIES


if __name__ == "__main__":
    mcp.run()