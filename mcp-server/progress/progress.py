"""
Progress tracking helpers for the MCP server.
"""

from mcp.server.fastmcp import Context


async def report_progress(
    ctx: Context,
    progress: float,
    total: float = 100
):
    """
    Report the current progress of a long-running operation.
    """

    await ctx.report_progress(
        progress=progress,
        total=total
    )


async def report_inventory_progress(
    ctx: Context,
    progress: float
):
    """
    Report progress specifically for inventory operations.
    """

    await report_progress(
        ctx=ctx,
        progress=progress,
        total=100
    )