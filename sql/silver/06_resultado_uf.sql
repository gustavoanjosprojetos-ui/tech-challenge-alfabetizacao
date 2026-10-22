-- Indicador oficial por UF, ano, serie e rede.
CREATE OR REPLACE TABLE `${projeto}.${stage}.resultado_uf` AS
SELECT
  x.ano,
  TRIM(x.sigla_uf) AS sigla_uf,
  u.regiao,
  x.serie,
  TRIM(x.rede) AS rede_codigo,
  COALESCE(r.rede_descricao, 'desconhecido') AS rede_descricao,
  x.taxa_alfabetizacao,
  x.media_portugues,
  x.proporcao_aluno_nivel_0, x.proporcao_aluno_nivel_1, x.proporcao_aluno_nivel_2,
  x.proporcao_aluno_nivel_3, x.proporcao_aluno_nivel_4, x.proporcao_aluno_nivel_5,
  x.proporcao_aluno_nivel_6, x.proporcao_aluno_nivel_7, x.proporcao_aluno_nivel_8,
  'oficial' AS origem,
  x.run_id AS bronze_run_id
FROM `${projeto}.${bronze}.uf` x
LEFT JOIN `${projeto}.${stage}.dim_uf` u
  ON u.sigla_uf = TRIM(x.sigla_uf)
LEFT JOIN `${projeto}.${stage}.dim_rede` r
  ON r.rede_codigo = TRIM(x.rede)
WHERE x.run_id = '${run_id}';
