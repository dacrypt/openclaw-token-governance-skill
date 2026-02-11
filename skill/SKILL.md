---
name: token-governance
description: "Capture, store, and export OpenClaw token/cost usage for governance and BI (Power BI/Grafana)."
---

# Token Governance Skill

Use this skill to:

- Monitor token consumption near real-time (1-second polling)
- Track per-event cost when OpenClaw provides it
- Audit usage by agent/session/model/channel/provider
- Export CSV for dashboards and analytics

## Commands

Initialize DB:

```bash
python3 src/collector.py init --db ./data/token_usage.db
```

Run continuous collector:

```bash
python3 src/collector.py collect --db ./data/token_usage.db --interval-sec 1 --status-every 30
```

Export CSV:

```bash
python3 src/collector.py export-csv --db ./data/token_usage.db --out-dir ./exports
```

## Operational recommendation

- Servers: run as a service (launchd/systemd)
- Laptops: run via cron every minute with `--once`, or daemon mode while online
- Retention: rotate DB monthly for long-term scale
