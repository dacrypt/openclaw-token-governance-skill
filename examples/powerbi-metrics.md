# Métricas sugeridas para Power BI

## Dimensiones
- Fecha/hora (`event_ts`)
- Agente (`agent_id`)
- Canal (`channel`)
- Modelo (`model`)
- Proveedor (`model_provider`)

## KPIs
- Tokens totales = `SUM(total_tokens)`
- Costo total = `SUM(cost_total)`
- Costo por 1K tokens = `DIVIDE(SUM(cost_total), SUM(total_tokens)) * 1000`
- % cache read = `DIVIDE(SUM(cache_read_tokens), SUM(total_tokens))`

## Gráficos
- Serie temporal de tokens/segundo o tokens/minuto
- Barras por agente/modelo/canal
- Heatmap hora vs día
- Costo acumulado diario y semanal
