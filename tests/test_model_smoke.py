import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER_ROOT = ROOT / "mcp-server"
if str(MCP_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_SERVER_ROOT))

import tools.read_tools as read_tools
import tools.write_tools as write_tools


class DummyCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    @property
    def lastrowid(self):
        return 42


class DummyConnection:
    def __init__(self, cursor):
        self.cursor_obj = cursor
        self.commit_calls = 0
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commit_calls += 1

    def close(self):
        self.closed = True


def test_search_spare_part_returns_matching_rows(monkeypatch):
    cursor = DummyCursor([("Brake Pad",)])
    conn = DummyConnection(cursor)
    monkeypatch.setattr(read_tools, "get_connection", lambda: conn)

    result = read_tools.search_spare_part("Brake")

    assert result == [("Brake Pad",)]
    assert cursor.executed


def test_update_inventory_commits_and_returns_notification(monkeypatch):
    cursor = DummyCursor([(10,)])
    conn = DummyConnection(cursor)
    monkeypatch.setattr(write_tools, "get_connection", lambda: conn)
    monkeypatch.setattr(write_tools, "require_manager", lambda role: None)
    monkeypatch.setattr(
        write_tools,
        "inventory_updated",
        lambda part_id, new_quantity: {
            "part_id": part_id,
            "new_quantity": new_quantity,
            "event": "inventory.updated",
        },
    )

    result = write_tools.update_inventory(1, 12, "manager")

    assert result["event"] == "inventory.updated"
    assert result["part_id"] == 1
    assert result["new_quantity"] == 12
    assert conn.commit_calls == 1
    assert conn.closed is True
