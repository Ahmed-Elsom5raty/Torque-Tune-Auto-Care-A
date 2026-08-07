# Torque Tune Auto Care

An MCP-based **Spare Parts Inventory Management System** designed for automotive repair businesses.

## Overview

Torque Tune Auto Care uses the **Model Context Protocol (MCP)** to expose inventory-management tools through an MCP server. The system is designed around a spare-parts database and supports both read and write operations, with authorization, validation, notifications, progress reporting, and human confirmation for sensitive inventory changes.

The project also includes automated tests covering the core tools, validation, authorization, notifications, negotiation, and tool visibility behavior.

## Features

- 🔍 Search for spare parts by name
- 📦 Check spare-part stock levels
- 🔄 Suggest alternative spare parts
- ➕ Add new spare parts
- ✏️ Update inventory quantities using increase/decrease actions
- 🗑️ Delete spare parts
- 📊 Generate inventory reports
- 🔐 Role-based authorization for inventory changes
- 🛡️ Server-side user-role lookup for inventory updates
- ✅ Inventory input validation
- 💬 MCP Elicitation for sensitive stock changes
- 🔔 Inventory notifications
- 📈 Progress tracking for inventory reports
- 🤝 MCP capability negotiation
- 👁️ Role-based tool visibility
- 🧪 Automated test suite

## MCP Tools

### Read Tools

| Tool | Description |
|---|---|
| `search_spare_part` | Search for spare parts by name. |
| `check_stock` | Return the current quantity for a spare part. |
| `suggest_alternative` | Return alternative parts for a given part ID. |

### Write Tools

| Tool | Description |
|---|---|
| `update_inventory` | Increase or decrease stock with authorization, validation, logging, and confirmation rules. |
| `add_spare_part` | Add a new spare part. |
| `delete_spare_part` | Delete an existing spare part. |
| `generate_inventory_report` | Generate an inventory summary while reporting progress to the client. |

## Update Inventory Flow

The `update_inventory` tool follows a controlled flow:

1. Look up the user's role from the `Users` table using `user_id`.
2. Authorize the operation based on the stored role.
3. Read the current part quantity and status.
4. Validate the requested action, quantity, status, and reason.
5. If the change is sensitive, request human confirmation through MCP Elicitation.
6. Apply the inventory update.
7. Insert an `InventoryLogs` record containing the old and new quantities, action, reason, part ID, and user ID.
8. Commit the transaction and return an inventory notification payload.

This keeps authorization and business validation on the server side rather than relying on values supplied by the client.

## Architecture

```text
Client
  │
  ▼
MCP Server
  │
  ├── Authentication & Authorization
  ├── Read Tools
  ├── Write Tools
  ├── Validation
  ├── Elicitation
  ├── Notifications
  ├── Progress Tracking
  ├── Resources
  └── Capability Negotiation
  │
  ▼
SQLite Database
