"""
Self-contained demo database for running agent/client.py directly.

databases/schema.sql is written for SQL Server and databases/db.py has no
live connection configured -- by design, tests monkeypatch it. This module
builds an equivalent SQLite database in memory purely so the agent has
something real to talk to for the demo. It is NOT the production schema;
once a real SQL Server connection is configured in databases/db.py, the
agent should be pointed at that instead (see agent/client.py).
"""

import sqlite3

SCHEMA = """
CREATE TABLE Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('technician', 'manager'))
);

CREATE TABLE Categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE Suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE SpareParts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_name TEXT NOT NULL,
    part_number TEXT NOT NULL UNIQUE,
    category_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    price REAL NOT NULL CHECK (price >= 0),
    location TEXT NOT NULL,
    minimum_stock INTEGER NOT NULL DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'discontinued')),
    FOREIGN KEY (category_id) REFERENCES Categories(id),
    FOREIGN KEY (supplier_id) REFERENCES Suppliers(id)
);

CREATE TABLE AlternativeParts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER NOT NULL,
    alternative_part_id INTEGER NOT NULL,
    FOREIGN KEY (part_id) REFERENCES SpareParts(id),
    FOREIGN KEY (alternative_part_id) REFERENCES SpareParts(id)
);

CREATE TABLE InventoryLogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    old_quantity INTEGER NOT NULL,
    new_quantity INTEGER NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    FOREIGN KEY (part_id) REFERENCES SpareParts(id),
    FOREIGN KEY (user_id) REFERENCES Users(id)
);
"""

SEED = """
INSERT INTO Users (name, email, role) VALUES
    ('Sam Tech', 'sam@autofix.example', 'technician'),
    ('Priya Manager', 'priya@autofix.example', 'manager');

INSERT INTO Categories (name) VALUES ('Brakes'), ('Engine');

INSERT INTO Suppliers (name) VALUES ('NAPA Distribution');

INSERT INTO SpareParts
    (part_name, part_number, category_id, supplier_id, quantity, price, location, minimum_stock, status)
VALUES
    ('Front Brake Pad Set', 'BRK-001', 1, 1, 8, 42.50, 'A1-03', 5, 'active'),
    ('Rear Brake Pad Set',  'BRK-002', 1, 1, 2, 39.00, 'A1-04', 5, 'active'),
    ('Timing Belt',         'ENG-010', 2, 1, 0, 65.00, 'B2-01', 3, 'discontinued');

INSERT INTO AlternativeParts (part_id, alternative_part_id) VALUES (1, 2);
"""


def build_demo_connection() -> sqlite3.Connection:
    """Fresh in-memory SQLite connection, seeded, ready for the agent demo."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.executescript(SEED)
    conn.commit()
    return conn