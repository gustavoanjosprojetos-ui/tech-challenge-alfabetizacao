-- Microdado de alunos tratado.
-- Achado da exploracao: a coluna alfabetizado da fonte marca os AUSENTES como 0 (nao alfabetizado).
-- Por isso a Silver define o universo de alunos avaliados e recalcula alfabetizado so para eles;
-- para os demais a coluna fica NULL (nao avaliado), nunca 0.
CREATE OR REPLACE TABLE `${projeto}.${stage}.alunos`
PARTITION BY RANGE_BUCKET(ano, GENERATE_ARRAY(2020, 2036, 1))
CLUSTER BY sigla_uf, id_municipio
AS
WITH base AS (
  SELECT
    a.*,
    (a.presenca = '1'
      AND a.preenchimento_caderno = '1'
      AND a.proficiencia IS NOT NULL
      AND a.peso_aluno IS NOT NULL) AS avaliado
  FROM `${projeto}.${bronze}.alunos` a
  WHERE a.run_id = '${run_id}'
)
SELECT
  b.ano,
  TRIM(b.id_municipio) AS id_municipio,
  u.sigla_uf,
  u.regiao,
  b.id_escola,
  b.id_aluno,
  SAFE_CAST(b.caderno AS INT64) AS caderno,
  b.serie,
  TRIM(b.rede) AS rede_codigo,
  COALESCE(r.rede_descricao, 'desconhecido') AS rede_descricao,
  b.presenca AS presenca_codigo,
  b.preenchimento_caderno AS preenchimento_codigo,
  b.presenca = '1' AS presente,
  b.preenchimento_caderno = '1' AS prova_preenchida,
  SAFE_CAST(b.alfabetizado AS INT64) AS alfabetizado_fonte,
  b.proficiencia,
  b.peso_aluno,
  b.avaliado,
  IF(b.avaliado, b.proficiencia >= ${corte}, NULL) AS alfabetizado,
  'oficial' AS origem,
  b._ingerido_em,
  b.run_id AS bronze_run_id
FROM base b
LEFT JOIN `${projeto}.${stage}.dim_uf` u
  ON u.codigo_uf = SUBSTR(TRIM(b.id_municipio), 1, 2)
LEFT JOIN `${projeto}.${stage}.dim_rede` r
  ON r.rede_codigo = TRIM(b.rede);
