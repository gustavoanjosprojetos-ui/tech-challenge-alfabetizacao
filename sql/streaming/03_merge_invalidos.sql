-- Quarentena: eventos invalidos guardados com o payload bruto e o motivo, para analise.
MERGE `${projeto}.${ops}.eventos_invalidos` t
USING (
  SELECT * FROM `${projeto}.${stage}.stream_lote` WHERE resultado = 'invalido'
) s
ON t.message_id = s.message_id
WHEN NOT MATCHED THEN INSERT (message_id, lote_id, publish_time, motivo, data, registrado_em)
VALUES (s.message_id, s.lote_id, s.publish_time, s.motivo_invalido, s.data, CURRENT_TIMESTAMP());
