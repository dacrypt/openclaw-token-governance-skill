---
name: token-governance
description: "Captura, historiza y exporta uso de tokens/costos de OpenClaw para gobernanza y BI (Power BI/Grafana)."
---

# Token Governance Skill

Usa este skill para:

- Monitorear consumo de tokens casi en tiempo real (polling por segundo)
- Registrar costo por evento cuando OpenClaw lo entrega
- Auditar por agente/sesión/modelo/canal/proveedor
- Exportar CSV para tableros

## Comandos

Inicializar DB:

```bash
python3 src/collector.py init --db ./data/token_usage.db
```

Correr colector continuo:

```bash
python3 src/collector.py collect --db ./data/token_usage.db --interval-sec 1 --status-every 30
```

Exportar CSV:

```bash
python3 src/collector.py export-csv --db ./data/token_usage.db --out-dir ./exports
```

## Recomendación operacional

- En servidores: correr como servicio (launchd/systemd)
- En laptops: cron cada minuto con `--once` o daemon cuando esté encendido
- Retención: mover DB por mes si crece mucho
