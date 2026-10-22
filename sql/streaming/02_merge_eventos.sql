-- Insere na Silver do streaming so os eventos novos e validos. MERGE por event_id:
-- reprocessar o mesmo lote nunca duplica. processado_em = momento real da gravacao,
-- usado para medir a latencia ponta a ponta (processado_em - event_time).
MERGE `${projeto}.${silver}.eventos_resultado_municipio` t
USING (
  SELECT * FROM `${projeto}.${stage}.stream_lote` WHERE resultado = 'inserido'
) s
ON t.event_id = s.event_id
WHEN NOT MATCHED THEN INSERT (
  event_id, message_id, lote_id, event_time, publish_time, processado_em,
  ano, id_municipio, sigla_uf, rede_codigo, serie, n_avaliados, n_alfabetizados,
  taxa_alfabetizacao, origem
) VALUES (
  s.event_id, s.message_id, s.lote_id, s.event_time, s.publish_time, CURRENT_TIMESTAMP(),
  s.ano, s.id_municipio, s.sigla_uf, s.rede_codigo, s.serie, s.n_avaliados, s.n_alfabetizados,
  100 * s.n_alfabetizados / s.n_avaliados, 'simulado'
);
