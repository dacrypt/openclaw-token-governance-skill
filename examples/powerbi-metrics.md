# Suggested Power BI Metrics

## Dimensions
- Timestamp (`event_ts`)
- Agent (`agent_id`)
- Channel (`channel`)
- Model (`model`)
- Provider (`model_provider`)

## KPIs
- Total tokens = `SUM(total_tokens)`
- Total cost = `SUM(cost_total)`
- Cost per 1K tokens = `DIVIDE(SUM(cost_total), SUM(total_tokens)) * 1000`
- Cache-read ratio = `DIVIDE(SUM(cache_read_tokens), SUM(total_tokens))`

## Visuals
- Time series: tokens/second or tokens/minute
- Bar charts by agent/model/channel
- Hour vs day heatmap
- Daily and weekly cumulative cost
