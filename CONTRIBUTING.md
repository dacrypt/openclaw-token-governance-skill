# Contributing

Thanks for your interest in contributing.

## How to contribute

1. Fork the repository
2. Create a feature branch (`feat/...` or `fix/...`)
3. Make focused, well-documented changes
4. Open a Pull Request with:
   - Problem statement
   - What changed
   - How to test

## Development setup

```bash
python3 src/collector.py init --db ./data/token_usage.db
python3 src/collector.py collect --db ./data/token_usage.db --once
python3 src/collector.py export-csv --db ./data/token_usage.db --out-dir ./exports
```

## Pull request guidelines

- Keep PRs small and focused
- Preserve backward compatibility in CSV/SQLite schema when possible
- Update README and examples if behavior changes
- Add migration notes for schema changes

## Code style

- Prefer simple, explicit Python
- Avoid adding heavy dependencies unless clearly justified
- Keep observability fields stable (agent/session/channel/model/provider/tokens/cost)
