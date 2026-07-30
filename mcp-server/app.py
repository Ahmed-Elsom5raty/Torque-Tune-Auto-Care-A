try:
    from .fastmcp import FastMCP
except Exception:
    # Fallback for direct execution / older layouts
    from fastmcp import FastMCP


mcp = FastMCP("Spare Parts Inventory Management System")