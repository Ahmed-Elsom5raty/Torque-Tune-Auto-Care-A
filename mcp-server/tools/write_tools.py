try:
    from mcp.server.fastmcp import Context
except ImportError:
    from fastmcp import Context

from app import mcp
from databases.db import get_connection
from auth.authorization import require_manager

from notifications import (
    inventory_updated,
    spare_part_added,
    spare_part_deleted,
)

from progress import report_inventory_progress


# -----------------------------
# Helper Functions
# -----------------------------

def _ensure_non_negative(quantity: int):
    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")


def _part_exists(cursor, part_id: int) -> bool:
    cursor.execute(
        "SELECT 1 FROM SpareParts WHERE id = ?",
        (part_id,)
    )
    return cursor.fetchone() is not None


# -----------------------------
# Write Tools
# -----------------------------

@mcp.tool()
def update_inventory(
    part_id: int,
    new_quantity: int,
    user_role: str
):
    """
    Update the quantity of a spare part.
    Only managers and admins are allowed.
    """

    require_manager(user_role)
    _ensure_non_negative(new_quantity)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if not _part_exists(cursor, part_id):
            raise ValueError("Spare part not found.")

        cursor.execute(
            """
            UPDATE SpareParts
            SET quantity = ?
            WHERE id = ?
            """,
            (new_quantity, part_id)
        )

        conn.commit()

        return inventory_updated(
            part_id,
            new_quantity
        )

    finally:
        conn.close()


@mcp.tool()
def add_spare_part(
    part_id: int | None,
    part_name: str,
    quantity: int,
    user_role: str
):
    """
    Add a new spare part to the inventory.
    """

    require_manager(user_role)
    _ensure_non_negative(quantity)

    if not part_name.strip():
        raise ValueError("Part name cannot be empty.")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if part_id is not None:

            if _part_exists(cursor, part_id):
                raise ValueError("Spare part already exists.")

            cursor.execute(
                """
                INSERT INTO SpareParts
                (id, part_name, quantity)
                VALUES (?, ?, ?)
                """,
                (part_id, part_name, quantity)
            )

        else:

            cursor.execute(
                """
                INSERT INTO SpareParts
                (part_name, quantity)
                VALUES (?, ?)
                """,
                (part_name, quantity)
            )

            part_id = cursor.lastrowid

        conn.commit()

        return spare_part_added(
            part_id,
            part_name
        )

    finally:
        conn.close()


@mcp.tool()
def delete_spare_part(
    part_id: int,
    user_role: str
):
    """
    Delete a spare part from the inventory.
    """

    require_manager(user_role)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if not _part_exists(cursor, part_id):
            raise ValueError("Spare part not found.")

        cursor.execute(
            "DELETE FROM SpareParts WHERE id = ?",
            (part_id,)
        )

        conn.commit()

        return spare_part_deleted(part_id)

    finally:
        conn.close()


@mcp.tool()
async def generate_inventory_report(ctx: Context):
    """
    Generate a summary report for the spare parts inventory
    while reporting progress to the client.
    """

    await report_inventory_progress(ctx, 0)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Read inventory
        await report_inventory_progress(ctx, 25)

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_parts,
                COALESCE(SUM(quantity), 0) AS total_quantity,
                COALESCE(AVG(price), 0) AS average_price
            FROM SpareParts
            """
        )

        report = cursor.fetchone()

        # Step 2: Calculate report
        await report_inventory_progress(ctx, 50)

        total_parts = report[0]
        total_quantity = report[1]
        average_price = round(report[2], 2)

        # Step 3: Prepare report
        await report_inventory_progress(ctx, 75)

        result = {
            "success": True,
            "total_parts": total_parts,
            "total_quantity": total_quantity,
            "average_price": average_price
        }

        # Completed
        await report_inventory_progress(ctx, 100)

        return result

    finally:
        conn.close()