-- Metricas do micro-lote (consulta de leitura, uma linha).
-- Latencia de ingestao   = publish_time (Pub/Sub recebeu) - event_time (evento criado)
-- Latencia ponta a ponta = processado_em (gravado na Silver) - event_time
-- Todos os carimbos sao gerados em pontos diferentes do caminho: nada e estimado.
WITH lote AS (
  SELECT resultado FROM `${projeto}.${stage}.stream_lote`
),
inseridos AS (
  SELECT
    TIMESTAMP_DIFF(publish_time, event_time, MILLISECOND) / 1000 AS lat_ingestao_s,
    TIMESTAMP_DIFF(processado_em, event_time, MILLISECOND) / 1000 AS lat_ponta_s
  FROM `${projeto}.${silver}.eventos_resultado_municipio`
  WHERE lote_id = '${lote_id}'
)
SELECT
  (SELECT COUNT(*) FROM lote) AS mensagens_novas,
  (SELECT COUNTIF(resultado = 'inserido') FROM lote) AS inseridos,
  (SELECT COUNTIF(resultado = 'duplicado') FROM lote) AS duplicados,
  (SELECT COUNTIF(resultado = 'invalido') FROM lote) AS invalidos,
  (SELECT AVG(lat_ingestao_s) FROM inseridos) AS latencia_ingestao_media_s,
  (SELECT AVG(lat_ponta_s) FROM inseridos) AS latencia_ponta_media_s,
  (SELECT APPROX_QUANTILES(lat_ponta_s, 100)[OFFSET(50)] FROM inseridos) AS latencia_ponta_p50_s,
  (SELECT APPROX_QUANTILES(lat_ponta_s, 100)[OFFSET(95)] FROM inseridos) AS latencia_ponta_p95_s,
  (SELECT MAX(lat_ponta_s) FROM inseridos) AS latencia_ponta_max_s;
