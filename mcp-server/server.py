from app import mcp

# Import tools so they are registered with the MCP server
from tools import read_tools
from tools import write_tools

# Import resources when available
try:
    from resources import resources  # type: ignore
except ImportError:
    resources = None

# Import notifications
from notifications import notifier

# Import progress
from progress import progress


if __name__ == "__main__":
    mcp.run()
