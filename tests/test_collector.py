import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

from src import collector


def _db_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_parse_event_usage_happy_path(tmp_path: Path):
    source_file = str(tmp_path / "abc.jsonl")
    line_obj = {
        "type": "message",
        "timestamp": "2026-01-01T00:00:00Z",
        "message": {
            "role": "assistant",
            "provider": "openai-codex",
            "model": "gpt-5.3-codex",
            "api": "openai-codex-responses",
            "stopReason": "stop",
            "usage": {
                "input": 10,
                "output": 5,
                "cacheRead": 3,
                "cacheWrite": 1,
                "totalTokens": 19,
                "cost": {"input": 0.1, "output": 0.2, "total": 0.3},
            },
        },
    }
    meta = {
        "agent_id": "agent1",
        "session_key": "agent:agent1:direct:x",
        "channel": "webchat",
        "chat_type": "direct",
        "origin_provider": "webchat",
    }

    rec = collector.parse_event_usage(line_obj, meta, source_file, 7)

    assert rec is not None
    assert rec["agent_id"] == "agent1"
    assert rec["session_id"] == "abc"
    assert rec["input_tokens"] == 10
    assert rec["total_tokens"] == 19
    assert rec["cost_total"] == 0.3


def test_ingest_jsonl_files_and_deduplicate(tmp_path: Path):
    openclaw_home = tmp_path / ".openclaw"
    sessions_dir = openclaw_home / "agents" / "alpha" / "sessions"
    sessions_dir.mkdir(parents=True)

    session_id = "1111-2222"
    session_key = "agent:alpha:openresponses-user:webchat"

    (sessions_dir / "sessions.json").write_text(
        json.dumps(
            {
                session_key: {
                    "sessionId": session_id,
                    "lastChannel": "webchat",
                    "chatType": "direct",
                    "origin": {"provider": "webchat", "chatType": "direct"},
                }
            }
        ),
        encoding="utf-8",
    )

    evt = {
        "type": "message",
        "timestamp": "2026-01-01T00:00:00Z",
        "message": {
            "role": "assistant",
            "provider": "openai-codex",
            "model": "gpt-5.3-codex",
            "api": "openai-codex-responses",
            "stopReason": "stop",
            "usage": {"input": 20, "output": 2, "cacheRead": 0, "cacheWrite": 0, "totalTokens": 22},
        },
    }
    (sessions_dir / f"{session_id}.jsonl").write_text(json.dumps(evt) + "\n", encoding="utf-8")

    db = tmp_path / "token_usage.db"
    collector.ensure_db(str(db))
    conn = collector.db_connect(str(db))
    try:
        collector.ingest_jsonl_files(conn, str(openclaw_home))
        conn.commit()
        assert _db_count(conn, "usage_events") == 1

        # Run again, should not duplicate because of UNIQUE(source_file, source_line_no)
        collector.ingest_jsonl_files(conn, str(openclaw_home))
        conn.commit()
        assert _db_count(conn, "usage_events") == 1
    finally:
        conn.close()


def test_ingest_provider_usage_snapshot(tmp_path: Path):
    db = tmp_path / "token_usage.db"
    collector.ensure_db(str(db))
    conn = collector.db_connect(str(db))

    fake = {
        "usage": {
            "providers": [
                {
                    "provider": "openai-codex",
                    "displayName": "Codex",
                    "plan": "plus ($0.00)",
                    "windows": [{"label": "Day", "usedPercent": 12, "resetAt": 123}],
                }
            ]
        }
    }

    with patch("subprocess.check_output", return_value=json.dumps(fake)):
        collector.ingest_provider_usage_snapshot(conn)
        conn.commit()

    try:
        assert _db_count(conn, "provider_usage_snapshots") == 1
    finally:
        conn.close()


def test_export_csv(tmp_path: Path):
    db = tmp_path / "token_usage.db"
    out = tmp_path / "exports"
    collector.ensure_db(str(db))
    conn = collector.db_connect(str(db))
    try:
        conn.execute(
            """
            INSERT INTO usage_events(
                event_ts, ingest_ts, agent_id, session_id, source_file, source_line_no
            ) VALUES('2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'a', 's', 'f', 1)
            """
        )
        conn.execute(
            """
            INSERT INTO provider_usage_snapshots(
                snapshot_ts, provider, window_label, used_percent
            ) VALUES('2026-01-01T00:00:00Z', 'p', 'Day', 12)
            """
        )
        conn.commit()

        collector.export_csv(conn, str(out))
        assert (out / "usage_events.csv").exists()
        assert (out / "provider_usage_snapshots.csv").exists()
    finally:
        conn.close()
