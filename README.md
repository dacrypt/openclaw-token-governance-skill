# OpenClaw Token Governance Skill

Observabilidad histórica de consumo de tokens/costo para OpenClaw, con granularidad por evento (casi en tiempo real), lista para Power BI / Grafana / SQL.

## Qué resuelve

- Registro histórico por **agente**, **sesión**, **modelo**, **canal** y **proveedor**
- Tokens por evento: `input`, `output`, `cacheRead`, `cacheWrite`, `total`
- Costos por evento (cuando OpenClaw los expone en `usage.cost`)
- Snapshots de cuota/plan via `openclaw status --json --usage`
- Exportación CSV para BI

> Nota importante: con plan ChatGPT Plus (USD$20), OpenClaw suele mostrar ventanas de uso/cuota (ej. 5h/día) y puede mostrar `plan: plus ($0.00)`. Eso **no** equivale a facturación API por token.

---

## Arquitectura

El colector lee:

1. `~/.openclaw/agents/*/sessions/sessions.json` (metadatos de sesión/canal)
2. `~/.openclaw/agents/*/sessions/*.jsonl` (eventos por turno, incluyendo `message.usage`)
3. `openclaw status --json --usage` (snapshots de cuota del proveedor)

Persistencia en SQLite:

- `usage_events` (evento por respuesta del modelo)
- `provider_usage_snapshots` (ventanas de cuota)
- `collector_state` (offsets por archivo)

---

## Requisitos

- Python 3.9+
- OpenClaw CLI accesible en PATH

## Instalación rápida

```bash
cd token-governance-skill
python3 src/collector.py init --db ./data/token_usage.db
```

## Modo daemon (1s)

```bash
python3 src/collector.py collect \
  --db ./data/token_usage.db \
  --openclaw-home ~/.openclaw \
  --interval-sec 1 \
  --status-every 30
```

- `--interval-sec 1` = polling por segundo
- `--status-every 30` = snapshot de cuota cada 30 ciclos

## Exportación CSV (Power BI)

```bash
python3 src/collector.py export-csv --db ./data/token_usage.db --out-dir ./exports
```

Importa en Power BI:

- `exports/usage_events.csv`
- `exports/provider_usage_snapshots.csv`

---

## Campos clave para gobernanza

`usage_events` incluye:

- `event_ts`, `agent_id`, `session_id`, `session_key`
- `channel`, `chat_type`, `origin_provider`
- `model_provider`, `model`, `api`, `stop_reason`
- `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `total_tokens`
- `cost_input`, `cost_output`, `cost_cache_read`, `cost_cache_write`, `cost_total`

Esto te permite segmentar por:

- Agente vs canal
- Modelo y proveedor
- Horario/día/semana
- Coste medio por respuesta
- Tokens de caché vs tokens nuevos

---

## Publicarlo como skill

Este repo incluye `skill/SKILL.md` para usarlo como habilidad reutilizable de operación/observabilidad.

---

## Estado actual GitHub

No puedo crear el repo remoto desde aquí hasta que `gh` esté autenticado en tu cuenta.

Cuando hagas login:

```bash
gh auth login
gh repo create <TU_USUARIO>/openclaw-token-governance-skill --public --source=. --remote=origin --push
```

También puedo hacerlo yo inmediatamente después del login.
