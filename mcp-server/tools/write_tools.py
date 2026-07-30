try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP
from databases.db import get_connection
from app import mcp
from server import mcp

ALLOWED_ROLES = {'admin', 'manager'}

def _check_permission(user_role: str, action: str):
    if user_role.lower() not in ALLOWED_ROLES:
        raise PermissionError(f"You do not have permission to {action} the inventory.")


def _ensure_non_negative(quantity: int):
    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")


def _part_exists(cursor, part_id: int) -> bool:
    cursor.execute("SELECT 1 FROM SpareParts WHERE id = ?", (part_id,))
    return cursor.fetchone() is not None


@mcp.tool()
def update_inventory(part_id: int, new_quantity: int, user_role: str):
    """
    Update the inventory quantity of a spare part by its ID and user role.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        _ensure_non_negative(new_quantity)
        _check_permission(user_role, "update")

        cursor.execute(
            "UPDATE SpareParts SET quantity = ? WHERE id = ?",
            (new_quantity, part_id)
        )

        if cursor.rowcount == 0:
            raise ValueError("Spare part not found.")

        conn.commit()
        return {"part_id": part_id, "new_quantity": new_quantity, "user_role": user_role}
    finally:
        conn.close()
        


@mcp.tool()
def add_spare_part(part_id: int | None, part_name: str, quantity: int, user_role: str):
    """
    Add a new spare part to the inventory.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        _ensure_non_negative(quantity)
        _check_permission(user_role, "add")
        if not part_name:
            raise ValueError("Part name cannot be empty.")

        if part_id is not None:
            if _part_exists(cursor, part_id):
                raise ValueError("Spare part already exists.")
            cursor.execute(
                "INSERT INTO SpareParts (id, part_name, quantity) VALUES (?, ?, ?)",
                (part_id, part_name, quantity)
            )
        else:
            cursor.execute(
                "INSERT INTO SpareParts (part_name, quantity) VALUES (?, ?)",
                (part_name, quantity)
            )
            part_id = cursor.lastrowid

        conn.commit()
        return {"part_id": part_id, "part_name": part_name, "quantity": quantity}
    finally:
        conn.close()
        


@mcp.tool()
def delete_spare_part(part_id: int, user_role: str):
    """
    Delete a spare part from the inventory by its ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        _check_permission(user_role, "delete")

        if not _part_exists(cursor, part_id):
            raise ValueError("Spare part not found.")

        cursor.execute("DELETE FROM SpareParts WHERE id = ?", (part_id,))
        conn.commit()
        return {
            "success": True,
            "message": "Spare part deleted successfully.",
            "part_id": part_id
        }
    finally:
        conn.close()
        
        
@mcp.tool()
def generate_inventory_report():
        """
        Generate a summary report for the inventory.
        """
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    COUNT(*) AS total_parts,
                    SUM(quantity) AS total_quantity,
                    AVG(price) AS average_price
                FROM SpareParts
            """)

            report = cursor.fetchone()

            return {
                "total_parts": report[0],
                "total_quantity": report[1],
                "average_price": round(report[2], 2) if report[2] else 0
            }

        finally:
            conn.close()