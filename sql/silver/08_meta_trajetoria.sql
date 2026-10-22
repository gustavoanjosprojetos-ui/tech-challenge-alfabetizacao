-- Trajetoria pactuada de metas (2024 a 2030) em formato longo: uma linha por ano de meta.
-- UNPIVOT descarta metas nulas: ausencia de linha = "sem meta", nunca meta zero.
-- Esta e a META PACTUADA da fonte (2030 = 80 para a rede publica). A universalizacao (100%)
-- e tratada na Gold como cenario aspiracional, em coluna separada.
CREATE OR REPLACE TABLE `${projeto}.${stage}.meta_trajetoria` AS
WITH unidas AS (
  SELECT 'brasil' AS nivel, CAST(NULL AS STRING) AS sigla_uf, CAST(NULL AS STRING) AS id_municipio,
         TRIM(rede) AS rotulo_rede_meta, ano AS ano_publicacao,
         meta_alfabetizacao_2024, meta_alfabetizacao_2025, meta_alfabetizacao_2026,
         meta_alfabetizacao_2027, meta_alfabetizacao_2028, meta_alfabetizacao_2029,
         meta_alfabetizacao_2030
  FROM `${projeto}.${bronze}.meta_alfabetizacao_brasil` WHERE run_id = '${run_id}'
  UNION ALL
  SELECT 'uf', TRIM(sigla_uf), NULL, TRIM(rede), ano,
         meta_alfabetizacao_2024, meta_alfabetizacao_2025, meta_alfabetizacao_2026,
         meta_alfabetizacao_2027, meta_alfabetizacao_2028, meta_alfabetizacao_2029,
         meta_alfabetizacao_2030
  FROM `${projeto}.${bronze}.meta_alfabetizacao_uf` WHERE run_id = '${run_id}'
  UNION ALL
  SELECT 'municipio', NULL, TRIM(id_municipio), TRIM(rede), ano,
         meta_alfabetizacao_2024, meta_alfabetizacao_2025, meta_alfabetizacao_2026,
         meta_alfabetizacao_2027, meta_alfabetizacao_2028, meta_alfabetizacao_2029,
         meta_alfabetizacao_2030
  FROM `${projeto}.${bronze}.meta_alfabetizacao_municipio` WHERE run_id = '${run_id}'
),
longa AS (
  SELECT *
  FROM unidas
  UNPIVOT (meta_pct FOR coluna_meta IN (
    meta_alfabetizacao_2024, meta_alfabetizacao_2025, meta_alfabetizacao_2026,
    meta_alfabetizacao_2027, meta_alfabetizacao_2028, meta_alfabetizacao_2029,
    meta_alfabetizacao_2030
  ))
)
SELECT
  l.nivel,
  COALESCE(l.sigla_uf, u.sigla_uf) AS sigla_uf,
  l.id_municipio,
  l.rotulo_rede_meta,
  m.rede_codigo,
  l.ano_publicacao,
  CAST(SUBSTR(l.coluna_meta, -4) AS INT64) AS ano_meta,
  l.meta_pct,
  'pactuada' AS tipo_meta,
  'oficial' AS origem
FROM longa l
LEFT JOIN `${projeto}.${stage}.map_rede_meta` m ON m.rotulo_meta = l.rotulo_rede_meta
LEFT JOIN `${projeto}.${stage}.dim_uf` u ON u.codigo_uf = SUBSTR(l.id_municipio, 1, 2);
