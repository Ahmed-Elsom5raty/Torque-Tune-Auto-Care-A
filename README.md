# Torque-Tune-Auto-Care-A

Temp name

## Database (databases/)

**Engine:** SQL Server (SSMS)

**Company:** AutoFix Repair Chain — technicians need to check spare parts
availability, find alternatives, and adjust stock without touching the
database directly. An MCP server sits between the LLM and this database.

**Tables (6):**
- `Users` — technician/manager roles (drives authorization)
- `Categories` — part categories (Brakes, Engine, Electrical, Suspension)
- `Suppliers` — supplier contact info
- `SpareParts` — core inventory table, includes `minimum_stock` and `status`
- `AlternativeParts` — interchangeable parts (self-referencing)
- `InventoryLogs` — full audit trail of every stock change (who, when, old→new, why)

**Edge cases in seed data:**
- A part at 0 quantity (out of stock)
- A part below `minimum_stock` (low stock)
- A discontinued part (never restocked, never suggested as an alternative)
- Two parts linked as valid alternatives

**Files:** `databases/shcema.sql` (table definitions), `databases/seed.sql` (sample data)


