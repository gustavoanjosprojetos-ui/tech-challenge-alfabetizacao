-- Linha de base publicada junto com as metas (Brasil, UF e municipio), em formato unico.
-- ano_publicacao = coluna ano da tabela de meta.
CREATE OR REPLACE TABLE `${projeto}.${stage}.meta_base` AS
WITH unidas AS (
  SELECT 'brasil' AS nivel, CAST(NULL AS STRING) AS sigla_uf, CAST(NULL AS STRING) AS id_municipio,
         TRIM(rede) AS rotulo_rede_meta, ano AS ano_publicacao, taxa_alfabetizacao,
         percentual_participacao, CAST(NULL AS INT64) AS nivel_alfabetizacao
  FROM `${projeto}.${bronze}.meta_alfabetizacao_brasil` WHERE run_id = '${run_id}'
  UNION ALL
  SELECT 'uf', TRIM(sigla_uf), NULL, TRIM(rede), ano, taxa_alfabetizacao,
         percentual_participacao, NULL
  FROM `${projeto}.${bronze}.meta_alfabetizacao_uf` WHERE run_id = '${run_id}'
  UNION ALL
  SELECT 'municipio', NULL, TRIM(id_municipio), TRIM(rede), ano, taxa_alfabetizacao,
         percentual_participacao, nivel_alfabetizacao
  FROM `${projeto}.${bronze}.meta_alfabetizacao_municipio` WHERE run_id = '${run_id}'
)
SELECT
  x.nivel,
  COALESCE(x.sigla_uf, u.sigla_uf) AS sigla_uf,
  x.id_municipio,
  x.rotulo_rede_meta,
  m.rede_codigo,
  x.ano_publicacao,
  x.taxa_alfabetizacao AS taxa_alfabetizacao_publicada,
  x.percentual_participacao,
  x.nivel_alfabetizacao,
  'oficial' AS origem
FROM unidas x
LEFT JOIN `${projeto}.${stage}.map_rede_meta` m ON m.rotulo_meta = x.rotulo_rede_meta
LEFT JOIN `${projeto}.${stage}.dim_uf` u ON u.codigo_uf = SUBSTR(x.id_municipio, 1, 2);
