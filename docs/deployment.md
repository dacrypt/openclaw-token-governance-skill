# Deployment Guide

## 1) Long-running daemon

```bash
python3 src/collector.py collect \
  --db /var/lib/openclaw-token-governance/token_usage.db \
  --openclaw-home ~/.openclaw \
  --interval-sec 1 \
  --status-every 30
```

## 2) systemd example (Linux)

Copy `deploy/systemd/openclaw-token-governance.service` to `/etc/systemd/system/`.

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-token-governance.service
sudo systemctl status openclaw-token-governance.service
```

## 3) launchd example (macOS)

Copy `deploy/launchd/com.openclaw.token-governance.plist` to `~/Library/LaunchAgents/`.

Then:

```bash
launchctl load ~/Library/LaunchAgents/com.openclaw.token-governance.plist
launchctl start com.openclaw.token-governance
launchctl list | grep token-governance
```

## 4) Backup and retention

- Back up SQLite daily
- Rotate monthly if DB grows quickly
- Keep exports immutable per month (`exports/YYYY-MM/`)
