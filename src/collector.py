#!/usr/bin/env python3
import argparse
import csv
import glob
import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS usage_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_ts TEXT,
  ingest_ts TEXT NOT NULL,
  agent_id TEXT,
  session_id TEXT,
  session_key TEXT,
  channel TEXT,
  chat_type TEXT,
  origin_provider TEXT,
  model_provider TEXT,
  model TEXT,
  api TEXT,
  stop_reason TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  cache_read_tokens INTEGER,
  cache_write_tokens INTEGER,
  total_tokens INTEGER,
  cost_input REAL,
  cost_output REAL,
  cost_cache_read REAL,
  cost_cache_write REAL,
  cost_total REAL,
  source_file TEXT,
  source_line_no INTEGER,
  UNIQUE(source_file, source_line_no)
);

CREATE TABLE IF NOT EXISTS provider_usage_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  snapshot_ts TEXT NOT NULL,
  provider TEXT,
  display_name TEXT,
  plan TEXT,
  window_label TEXT,
  used_percent REAL,
  reset_at_ms INTEGER
);

CREATE TABLE IF NOT EXISTS collector_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_ts TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_events_ts ON usage_events(event_ts);
CREATE INDEX IF NOT EXISTS idx_usage_events_agent ON usage_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_model ON usage_events(model);
CREATE INDEX IF NOT EXISTS idx_usage_events_channel ON usage_events(channel);
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_db(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def db_connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_state(conn: sqlite3.Connection, key: str, default: Optional[str] = None) -> Optional[str]:
    row = conn.execute("SELECT value FROM collector_state WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_state(conn: sqlite3.Connection, key: str, value: str):
    conn.execute(
        """
        INSERT INTO collector_state(key, value, updated_ts)
        VALUES(?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_ts=excluded.updated_ts
        """,
        (key, value, utc_now_iso()),
    )


def load_session_index(openclaw_home: str) -> Dict[str, Dict[str, Any]]:
    """Return map sessionId -> metadata."""
    by_session_id: Dict[str, Dict[str, Any]] = {}
    for path in glob.glob(os.path.join(openclaw_home, "agents", "*", "sessions", "sessions.json")):
        agent_id = path.split(os.sep)[-3]
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        for session_key, meta in data.items():
            session_id = meta.get("sessionId")
            if not session_id:
                continue
            delivery = meta.get("deliveryContext", {}) or {}
            origin = meta.get("origin", {}) or {}
            by_session_id[session_id] = {
                "agent_id": agent_id,
                "session_key": session_key,
                "channel": meta.get("lastChannel") or delivery.get("channel"),
                "chat_type": meta.get("chatType") or origin.get("chatType"),
                "origin_provider": origin.get("provider"),
            }
    return by_session_id


def parse_event_usage(line_obj: Dict[str, Any], session_meta: Dict[str, Any], source_file: str, line_no: int) -> Optional[Dict[str, Any]]:
    if line_obj.get("type") != "message":
        return None
    msg = line_obj.get("message", {}) or {}
    if msg.get("role") != "assistant":
        return None
    usage = msg.get("usage")
    if not usage:
        return None

    cost = usage.get("cost") or {}
    return {
        "event_ts": line_obj.get("timestamp") or msg.get("timestamp"),
        "ingest_ts": utc_now_iso(),
        "agent_id": session_meta.get("agent_id"),
        "session_id": _basename_without_ext(source_file),
        "session_key": session_meta.get("session_key"),
        "channel": session_meta.get("channel"),
        "chat_type": session_meta.get("chat_type"),
        "origin_provider": session_meta.get("origin_provider"),
        "model_provider": msg.get("provider"),
        "model": msg.get("model"),
        "api": msg.get("api"),
        "stop_reason": msg.get("stopReason"),
        "input_tokens": usage.get("input"),
        "output_tokens": usage.get("output"),
        "cache_read_tokens": usage.get("cacheRead"),
        "cache_write_tokens": usage.get("cacheWrite"),
        "total_tokens": usage.get("totalTokens"),
        "cost_input": cost.get("input"),
        "cost_output": cost.get("output"),
        "cost_cache_read": cost.get("cacheRead"),
        "cost_cache_write": cost.get("cacheWrite"),
        "cost_total": cost.get("total"),
        "source_file": source_file,
        "source_line_no": line_no,
    }


def _basename_without_ext(path: str) -> str:
    return os.path.basename(path).replace(".jsonl", "")


def ingest_jsonl_files(conn: sqlite3.Connection, openclaw_home: str):
    session_idx = load_session_index(openclaw_home)
    session_files = glob.glob(os.path.join(openclaw_home, "agents", "*", "sessions", "*.jsonl"))

    for sf in session_files:
        state_key = f"offset:{sf}"
        try:
            fsize = os.path.getsize(sf)
        except OSError:
            continue

        offset = int(get_state(conn, state_key, "0") or "0")
        if offset > fsize:
            offset = 0

        session_id = _basename_without_ext(sf)
        smeta = session_idx.get(session_id, {})

        with open(sf, "r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            line_no = int(get_state(conn, f"line:{sf}", "0") or "0")
            while True:
                line = f.readline()
                if not line:
                    break
                line_no += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                rec = parse_event_usage(obj, smeta, sf, line_no)
                if rec:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO usage_events (
                          event_ts, ingest_ts, agent_id, session_id, session_key, channel, chat_type, origin_provider,
                          model_provider, model, api, stop_reason,
                          input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, total_tokens,
                          cost_input, cost_output, cost_cache_read, cost_cache_write, cost_total,
                          source_file, source_line_no
                        ) VALUES (
                          :event_ts, :ingest_ts, :agent_id, :session_id, :session_key, :channel, :chat_type, :origin_provider,
                          :model_provider, :model, :api, :stop_reason,
                          :input_tokens, :output_tokens, :cache_read_tokens, :cache_write_tokens, :total_tokens,
                          :cost_input, :cost_output, :cost_cache_read, :cost_cache_write, :cost_total,
                          :source_file, :source_line_no
                        )
                        """,
                        rec,
                    )

            new_offset = f.tell()

        set_state(conn, state_key, str(new_offset))
        set_state(conn, f"line:{sf}", str(line_no))


def ingest_provider_usage_snapshot(conn: sqlite3.Connection):
    try:
        out = subprocess.check_output(
            ["openclaw", "status", "--json", "--usage"],
            stderr=subprocess.STDOUT,
            text=True,
        )
        data = json.loads(out)
    except Exception:
        return

    usage = data.get("usage", {}) or {}
    providers = usage.get("providers", []) or []
    snapshot_ts = utc_now_iso()

    for p in providers:
        for w in p.get("windows", []) or []:
            conn.execute(
                """
                INSERT INTO provider_usage_snapshots (
                  snapshot_ts, provider, display_name, plan, window_label, used_percent, reset_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_ts,
                    p.get("provider"),
                    p.get("displayName"),
                    p.get("plan"),
                    w.get("label"),
                    w.get("usedPercent"),
                    w.get("resetAt"),
                ),
            )


def export_csv(conn: sqlite3.Connection, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    def dump(query: str, filename: str):
        rows = conn.execute(query).fetchall()
        if not rows:
            return
        path = os.path.join(out_dir, filename)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys())
            for r in rows:
                writer.writerow([r[k] for k in r.keys()])

    dump("SELECT * FROM usage_events ORDER BY id", "usage_events.csv")
    dump("SELECT * FROM provider_usage_snapshots ORDER BY id", "provider_usage_snapshots.csv")


def run_collect(db: str, openclaw_home: str, interval_sec: float, status_every: int, once: bool):
    ensure_db(db)
    conn = db_connect(db)
    try:
        i = 0
        while True:
            ingest_jsonl_files(conn, openclaw_home)
            if i % max(1, status_every) == 0:
                ingest_provider_usage_snapshot(conn)
            conn.commit()
            i += 1
            if once:
                break
            time.sleep(interval_sec)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="OpenClaw token governance collector")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--db", required=True)

    p_collect = sub.add_parser("collect")
    p_collect.add_argument("--db", required=True)
    p_collect.add_argument("--openclaw-home", default=os.path.expanduser("~/.openclaw"))
    p_collect.add_argument("--interval-sec", type=float, default=1.0)
    p_collect.add_argument("--status-every", type=int, default=30)
    p_collect.add_argument("--once", action="store_true")

    p_export = sub.add_parser("export-csv")
    p_export.add_argument("--db", required=True)
    p_export.add_argument("--out-dir", required=True)

    args = parser.parse_args()

    if args.cmd == "init":
        ensure_db(args.db)
        print(f"initialized: {args.db}")
    elif args.cmd == "collect":
        run_collect(args.db, args.openclaw_home, args.interval_sec, args.status_every, args.once)
    elif args.cmd == "export-csv":
        conn = db_connect(args.db)
        try:
            export_csv(conn, args.out_dir)
            print(f"exported to: {args.out_dir}")
        finally:
            conn.close()


if __name__ == "__main__":
    main()
