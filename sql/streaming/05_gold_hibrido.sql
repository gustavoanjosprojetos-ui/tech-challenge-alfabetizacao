-- Visao hibrida na Gold: resultado OFICIAL (batch) e SIMULADO (streaming) na mesma tabela,
-- separados pela coluna origem. Do streaming entra o evento mais recente de cada
-- municipio/ano/rede. Nunca misture as duas origens num mesmo calculo sem filtrar.
CREATE OR REPLACE TABLE `${projeto}.${gold}.indicador_municipio_hibrido`
CLUSTER BY origem, sigla_uf
AS
WITH stream AS (
  SELECT *
  FROM `${projeto}.${silver}.eventos_resultado_municipio`
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ano, id_municipio, rede_codigo ORDER BY event_time DESC, event_id DESC) = 1
)
SELECT
  ano, id_municipio, sigla_uf, rede_codigo,
  taxa_oficial AS taxa_alfabetizacao,
  n_avaliados,
  'oficial' AS origem,
  CAST(NULL AS TIMESTAMP) AS atualizado_em
FROM `${projeto}.${gold}.indicador_municipio`
WHERE tem_resultado_oficial
UNION ALL
SELECT
  ano, id_municipio, sigla_uf, rede_codigo,
  taxa_alfabetizacao,
  n_avaliados,
  'simulado' AS origem,
  event_time AS atualizado_em
FROM stream;
