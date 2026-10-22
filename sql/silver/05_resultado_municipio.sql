-- Indicador oficial por municipio, ano, serie e rede. Nulos preservados (nao viram zero).
CREATE OR REPLACE TABLE `${projeto}.${stage}.resultado_municipio`
CLUSTER BY sigla_uf, id_municipio
AS
SELECT
  m.ano,
  TRIM(m.id_municipio) AS id_municipio,
  u.sigla_uf,
  u.regiao,
  m.serie,
  TRIM(m.rede) AS rede_codigo,
  COALESCE(r.rede_descricao, 'desconhecido') AS rede_descricao,
  m.taxa_alfabetizacao,
  m.media_portugues,
  m.proporcao_aluno_nivel_0, m.proporcao_aluno_nivel_1, m.proporcao_aluno_nivel_2,
  m.proporcao_aluno_nivel_3, m.proporcao_aluno_nivel_4, m.proporcao_aluno_nivel_5,
  m.proporcao_aluno_nivel_6, m.proporcao_aluno_nivel_7, m.proporcao_aluno_nivel_8,
  'oficial' AS origem,
  m.run_id AS bronze_run_id
FROM `${projeto}.${bronze}.municipio` m
LEFT JOIN `${projeto}.${stage}.dim_uf` u
  ON u.codigo_uf = SUBSTR(TRIM(m.id_municipio), 1, 2)
LEFT JOIN `${projeto}.${stage}.dim_rede` r
  ON r.rede_codigo = TRIM(m.rede)
WHERE m.run_id = '${run_id}';
