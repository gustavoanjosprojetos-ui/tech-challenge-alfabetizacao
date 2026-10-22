-- Meta x resultado no MESMO recorte de rede e serie (2o ano):
--   municipio -> rede 3 (Municipal), UF e Brasil -> rede 5 (Publica estadual e municipal).
-- Meta vigente no ano Y = a meta para Y da publicacao MAIS RECENTE feita ANTES de Y
-- (ex.: resultado 2024 x meta 2024 publicada em 2023). Assim a meta nunca e definida
-- depois de conhecido o resultado que ela avalia.
-- status_meta tem estados distintos: atingiu | nao_atingiu | sem_meta | sem_resultado.
-- "sem_meta" NUNCA vira "nao_atingiu", e resultado ausente NUNCA vira zero.
CREATE OR REPLACE TABLE `${projeto}.${stage}.meta_vs_resultado` AS
WITH resultado AS (
  SELECT 'municipio' AS nivel, id_municipio AS chave, sigla_uf, rede_codigo, ano,
         taxa_oficial AS taxa_resultado, 'resultado_municipio' AS fonte_resultado
  FROM `${projeto}.${stage}.indicador_municipio`
  WHERE rede_codigo = '3' AND tem_resultado_oficial
  UNION ALL
  SELECT 'uf', sigla_uf, sigla_uf, rede_codigo, ano, taxa_oficial, 'resultado_uf'
  FROM `${projeto}.${stage}.indicador_uf`
  WHERE rede_codigo = '5' AND tem_resultado_oficial
  UNION ALL
  SELECT 'brasil', 'BR', CAST(NULL AS STRING), rede_codigo, ano, taxa_publicada, 'meta_alfabetizacao_brasil'
  FROM `${projeto}.${stage}.indicador_brasil`
  WHERE rede_codigo = '5' AND taxa_publicada IS NOT NULL
),
anos_por_nivel AS (SELECT DISTINCT nivel, ano FROM resultado),
meta AS (
  SELECT
    nivel,
    CASE nivel WHEN 'municipio' THEN id_municipio WHEN 'uf' THEN sigla_uf ELSE 'BR' END AS chave,
    sigla_uf, rede_codigo, ano_publicacao, ano_meta, meta_pct
  FROM `${projeto}.${silver}.meta_trajetoria`
),
meta_vigente AS (
  SELECT m.nivel, m.chave, m.sigla_uf, m.rede_codigo, m.ano_meta AS ano, m.meta_pct, m.ano_publicacao
  FROM meta m
  JOIN anos_por_nivel a ON a.nivel = m.nivel AND a.ano = m.ano_meta
  WHERE m.ano_publicacao < m.ano_meta
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY m.nivel, m.chave, m.rede_codigo, m.ano_meta ORDER BY m.ano_publicacao DESC) = 1
),
meta_2030 AS (
  SELECT nivel, chave, rede_codigo, meta_pct AS meta_2030_pactuada
  FROM meta
  WHERE ano_meta = 2030
  QUALIFY ROW_NUMBER() OVER (PARTITION BY nivel, chave, rede_codigo ORDER BY ano_publicacao DESC) = 1
),
base AS (
  SELECT
    COALESCE(r.nivel, v.nivel) AS nivel,
    COALESCE(r.chave, v.chave) AS chave,
    COALESCE(r.sigla_uf, v.sigla_uf) AS sigla_uf,
    COALESCE(r.rede_codigo, v.rede_codigo) AS rede_codigo,
    COALESCE(r.ano, v.ano) AS ano,
    r.taxa_resultado,
    r.fonte_resultado,
    v.meta_pct AS meta_ano,
    v.ano_publicacao AS ano_publicacao_meta
  FROM resultado r
  FULL OUTER JOIN meta_vigente v
    ON r.nivel = v.nivel AND r.chave = v.chave AND r.rede_codigo = v.rede_codigo AND r.ano = v.ano
)
SELECT
  b.*,
  m.meta_2030_pactuada,
  100.0 AS meta_2030_aspiracional,
  CASE
    WHEN b.taxa_resultado IS NULL THEN 'sem_resultado'
    WHEN b.meta_ano IS NULL THEN 'sem_meta'
    WHEN b.taxa_resultado >= b.meta_ano THEN 'atingiu'
    ELSE 'nao_atingiu'
  END AS status_meta,
  b.taxa_resultado - b.meta_ano AS gap_meta_pp,
  b.taxa_resultado - m.meta_2030_pactuada AS gap_2030_pactuada_pp,
  b.taxa_resultado - 100.0 AS gap_2030_aspiracional_pp,
  'oficial' AS origem
FROM base b
LEFT JOIN meta_2030 m ON m.nivel = b.nivel AND m.chave = b.chave AND m.rede_codigo = b.rede_codigo;
