"""
Notification helpers for the Spare Parts Inventory Management System.
"""

def inventory_updated(part_id:int,quantity:int):
    return{
        "event":"inventory.updated",
        "message":"inventory updated successfully",
        "part_id":part_id,
        "new_quantity":quantity,
    }

def spare_part_deleted(part_id:int):
    return{
        "event":"inventory.part_deleted",
        "message":"Spare part deleted successfully",
        "part_id":part_id,
    }