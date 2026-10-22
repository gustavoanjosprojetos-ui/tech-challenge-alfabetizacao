-- Livro-razao: registra cada mensagem do lote com o resultado. E o que torna o
-- processamento incremental: o proximo lote ignora tudo o que ja esta aqui.
MERGE `${projeto}.${ops}.stream_mensagens` t
USING (SELECT * FROM `${projeto}.${stage}.stream_lote`) s
ON t.message_id = s.message_id
WHEN NOT MATCHED THEN INSERT (message_id, event_id, lote_id, resultado, publish_time, processado_em)
VALUES (s.message_id, s.event_id, s.lote_id, s.resultado, s.publish_time, CURRENT_TIMESTAMP());
