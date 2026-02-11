# OpenClaw Token Governance Skill

Historical token and cost observability for OpenClaw, with event-level granularity (near real-time), ready for Power BI / Grafana / SQL.

## What it solves

- Historical tracking by **agent**, **session**, **model**, **channel**, and **provider**
- Event-level tokens: `input`, `output`, `cacheRead`, `cacheWrite`, `total`
- Event-level costs (when OpenClaw exposes `usage.cost`)
- Provider quota/plan snapshots via `openclaw status --json --usage`
- CSV export for BI workflows

> Important note: with ChatGPT Plus (USD $20), OpenClaw may show quota windows (e.g., 5h/day) and `plan: plus ($0.00)`. This is **not the same** as per-token API billing.

---

## Architecture

The collector reads:

1. `~/.openclaw/agents/*/sessions/sessions.json` (session/channel metadata)
2. `~/.openclaw/agents/*/sessions/*.jsonl` (turn-level events, including `message.usage`)
3. `openclaw status --json --usage` (provider quota snapshots)

SQLite persistence:

- `usage_events` (one row per model response event)
- `provider_usage_snapshots` (quota window snapshots)
- `collector_state` (file offsets/checkpointing)

---

## Requirements

- Python 3.9+
- OpenClaw CLI available in PATH

## Quick start

```bash
cd token-governance-skill
python3 src/collector.py init --db ./data/token_usage.db
```

## Daemon mode (1s)

```bash
python3 src/collector.py collect \
  --db ./data/token_usage.db \
  --openclaw-home ~/.openclaw \
  --interval-sec 1 \
  --status-every 30
```

- `--interval-sec 1` = poll every second
- `--status-every 30` = quota snapshot every 30 loops

## CSV export (Power BI)

```bash
python3 src/collector.py export-csv --db ./data/token_usage.db --out-dir ./exports
```

Import into Power BI:

- `exports/usage_events.csv`
- `exports/provider_usage_snapshots.csv`

---

## Governance-ready fields

`usage_events` includes:

- `event_ts`, `agent_id`, `session_id`, `session_key`
- `channel`, `chat_type`, `origin_provider`
- `model_provider`, `model`, `api`, `stop_reason`
- `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `total_tokens`
- `cost_input`, `cost_output`, `cost_cache_read`, `cost_cache_write`, `cost_total`

This enables segmentation by:

- Agent vs channel
- Model and provider
- Time window (hour/day/week)
- Average cost per response
- Cached tokens vs new tokens

---

## Skill packaging

This repository includes `skill/SKILL.md` so it can be reused as an operational/observability skill.

---

## Publish to GitHub

If needed on a fresh environment:

```bash
gh auth login
gh repo create <YOUR_USER>/openclaw-token-governance-skill --public --source=. --remote=origin --push
```
