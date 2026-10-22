-- Nos caminhos JSON, o cifrao aparece dobrado: e o escape do template (vira um so ao renderizar).
-- Micro-lote incremental: so mensagens que ainda NAO estao no livro-razao ops.stream_mensagens.
-- Cada mensagem recebe exatamente um resultado:
--   invalido  -> vai para a quarentena (ops.eventos_invalidos), com o motivo
--   duplicado -> event_id ja processado antes (ou repetido dentro do lote): descartado
--   inserido  -> entra na Silver do streaming
-- O Pub/Sub entrega "pelo menos uma vez" e o simulador reenvia eventos de proposito,
-- entao a deduplicacao e por event_id (chave do evento), nao por message_id.
CREATE OR REPLACE TABLE `${projeto}.${stage}.stream_lote` AS
WITH ja_processadas AS (
  SELECT message_id FROM `${projeto}.${ops}.stream_mensagens`
),
novas AS (
  SELECT b.message_id, b.publish_time, b.data
  FROM `${projeto}.${bronze}.eventos_stream` b
  LEFT JOIN ja_processadas p ON p.message_id = b.message_id
  WHERE b.publish_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL ${janela_horas} HOUR)
    AND p.message_id IS NULL
  -- a propria assinatura pode gravar a mesma mensagem duas vezes (entrega pelo menos uma vez)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY b.message_id ORDER BY b.publish_time) = 1
),
campos AS (
  SELECT
    message_id,
    publish_time,
    data,
    SAFE.PARSE_JSON(data) AS j
  FROM novas
),
extraidos AS (
  SELECT
    message_id,
    publish_time,
    data,
    j IS NOT NULL AS json_ok,
    JSON_VALUE(j, '$$.event_id') AS event_id,
    SAFE.TIMESTAMP(JSON_VALUE(j, '$$.event_time')) AS event_time,
    SAFE_CAST(JSON_VALUE(j, '$$.ano') AS INT64) AS ano,
    JSON_VALUE(j, '$$.id_municipio') AS id_municipio,
    JSON_VALUE(j, '$$.rede_codigo') AS rede_codigo,
    JSON_VALUE(j, '$$.serie') AS serie,
    SAFE_CAST(JSON_VALUE(j, '$$.n_avaliados') AS INT64) AS n_avaliados,
    SAFE_CAST(JSON_VALUE(j, '$$.n_alfabetizados') AS INT64) AS n_alfabetizados,
    JSON_VALUE(j, '$$.origem') AS origem
  FROM campos
),
municipios AS (
  SELECT DISTINCT id_municipio, sigla_uf FROM `${projeto}.${silver}.resultado_municipio`
),
redes AS (
  SELECT rede_codigo FROM `${projeto}.${silver}.dim_rede`
),
validados AS (
  SELECT
    e.*,
    mu.sigla_uf,
    CASE
      WHEN NOT e.json_ok THEN 'json_invalido'
      WHEN e.event_id IS NULL OR e.event_time IS NULL OR e.ano IS NULL OR e.id_municipio IS NULL
        OR e.rede_codigo IS NULL OR e.n_avaliados IS NULL OR e.n_alfabetizados IS NULL
        THEN 'campo_obrigatorio_ausente'
      WHEN e.origem IS NULL OR e.origem != 'simulado' THEN 'origem_invalida'
      WHEN e.ano NOT BETWEEN 2023 AND 2030 THEN 'ano_fora_da_faixa'
      WHEN e.event_time > TIMESTAMP_ADD(e.publish_time, INTERVAL 5 MINUTE) THEN 'event_time_no_futuro'
      WHEN mu.id_municipio IS NULL THEN 'municipio_inexistente'
      WHEN r.rede_codigo IS NULL THEN 'rede_desconhecida'
      WHEN e.n_avaliados <= 0 OR e.n_alfabetizados < 0 THEN 'contagem_invalida'
      WHEN e.n_alfabetizados > e.n_avaliados THEN 'alfabetizados_maior_que_avaliados'
    END AS motivo_invalido
  FROM extraidos e
  LEFT JOIN municipios mu ON mu.id_municipio = e.id_municipio
  LEFT JOIN redes r ON r.rede_codigo = e.rede_codigo
),
eventos_existentes AS (
  SELECT DISTINCT event_id, TRUE AS existe FROM `${projeto}.${silver}.eventos_resultado_municipio`
)
SELECT
  v.*,
  CASE
    WHEN v.motivo_invalido IS NOT NULL THEN 'invalido'
    WHEN x.existe THEN 'duplicado'
    WHEN ROW_NUMBER() OVER (
      PARTITION BY IF(v.motivo_invalido IS NULL, v.event_id, v.message_id)
      ORDER BY v.publish_time, v.message_id) > 1 THEN 'duplicado'
    ELSE 'inserido'
  END AS resultado,
  '${lote_id}' AS lote_id
FROM validados v
LEFT JOIN eventos_existentes x ON x.event_id = v.event_id;
