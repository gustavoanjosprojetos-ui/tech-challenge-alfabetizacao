-- Medicoes de FinOps no BigQuery (somente leitura; custo minimo).
-- 1) bytes faturados e duracao por execucao do pipeline (registrados pelo proprio pipeline)
-- 2) armazenamento logico por dataset
-- 3) volume do streaming (mensagens e bytes que passaram pelo Pub/Sub)
SELECT 'execucao' AS medida, TO_JSON_STRING(t) AS valor FROM (
  SELECT run_id, pipeline, MIN(inicio) AS inicio, ROUND(SUM(duracao_s), 1) AS duracao_etapas_s,
         SUM(bytes_faturados) AS bytes_faturados, COUNT(*) AS etapas,
         LOGICAL_OR(status = 'falha') AS falhou
  FROM ops.pipeline_execucoes
  GROUP BY run_id, pipeline
) t
UNION ALL
SELECT 'armazenamento', TO_JSON_STRING(s) FROM (
  SELECT dataset_id, COUNT(*) AS tabelas, SUM(size_bytes) AS bytes, SUM(row_count) AS linhas
  FROM (
    SELECT * FROM bronze.__TABLES__ UNION ALL SELECT * FROM silver.__TABLES__
    UNION ALL SELECT * FROM silver_stage.__TABLES__ UNION ALL SELECT * FROM gold.__TABLES__
    UNION ALL SELECT * FROM gold_stage.__TABLES__ UNION ALL SELECT * FROM ops.__TABLES__
  )
  GROUP BY dataset_id
) s
UNION ALL
SELECT 'pubsub', TO_JSON_STRING(p) FROM (
  SELECT COUNT(*) AS mensagens, SUM(BYTE_LENGTH(data)) AS bytes_payload,
         ROUND(AVG(BYTE_LENGTH(data)), 1) AS media_bytes
  FROM bronze.eventos_stream
) p
ORDER BY medida, valor;
