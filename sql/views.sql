-- View enfocada en BI
CREATE VIEW IF NOT EXISTS v_usage_events_enriched AS
SELECT
  event_ts,
  date(event_ts) AS event_date,
  strftime('%H', event_ts) AS event_hour,
  agent_id,
  session_id,
  session_key,
  channel,
  chat_type,
  origin_provider,
  model_provider,
  model,
  api,
  stop_reason,
  input_tokens,
  output_tokens,
  cache_read_tokens,
  cache_write_tokens,
  total_tokens,
  cost_total,
  CASE WHEN total_tokens > 0 THEN (cost_total / total_tokens) ELSE NULL END AS cost_per_token
FROM usage_events;
