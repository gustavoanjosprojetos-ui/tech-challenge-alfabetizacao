-- Taxa de alfabetizacao recalculada a partir do microdado de alunos (Silver publicada).
-- Denominador: alunos AVALIADOS (presentes, prova preenchida, com proficiencia e peso).
-- Ponderada pelo peso amostral (peso_aluno), como o indicador oficial.
-- Tambem calculamos a versao SEM peso, so para mostrar quanto o peso muda o resultado.
-- Redes agregadas seguem o dicionario: 5 = publica (2 estadual + 3 municipal), 0 = total.
CREATE OR REPLACE TABLE `${projeto}.${stage}.recalculo_microdados` AS
WITH a AS (
  SELECT
    ano, sigla_uf, id_municipio, rede_agregada AS rede_codigo,
    alfabetizado, peso_aluno, proficiencia
  FROM `${projeto}.${silver}.alunos`,
  UNNEST(ARRAY_CONCAT(
    [rede_codigo],
    IF(rede_codigo IN ('2', '3'), ['5'], CAST([] AS ARRAY<STRING>)),
    ['0']
  )) AS rede_agregada
  WHERE avaliado
)
SELECT 'municipio' AS nivel, ano, sigla_uf, id_municipio, rede_codigo,
  COUNT(*) AS n_avaliados,
  SUM(peso_aluno) AS soma_pesos,
  100 * SAFE_DIVIDE(SUM(IF(alfabetizado, peso_aluno, 0)), SUM(peso_aluno)) AS taxa_recalculada,
  100 * AVG(IF(alfabetizado, 1, 0)) AS taxa_recalculada_sem_peso,
  SAFE_DIVIDE(SUM(proficiencia * peso_aluno), SUM(peso_aluno)) AS proficiencia_media_ponderada
FROM a GROUP BY ano, sigla_uf, id_municipio, rede_codigo
UNION ALL
SELECT 'uf', ano, sigla_uf, CAST(NULL AS STRING), rede_codigo,
  COUNT(*), SUM(peso_aluno),
  100 * SAFE_DIVIDE(SUM(IF(alfabetizado, peso_aluno, 0)), SUM(peso_aluno)),
  100 * AVG(IF(alfabetizado, 1, 0)),
  SAFE_DIVIDE(SUM(proficiencia * peso_aluno), SUM(peso_aluno))
FROM a GROUP BY ano, sigla_uf, rede_codigo
UNION ALL
SELECT 'brasil', ano, CAST(NULL AS STRING), CAST(NULL AS STRING), rede_codigo,
  COUNT(*), SUM(peso_aluno),
  100 * SAFE_DIVIDE(SUM(IF(alfabetizado, peso_aluno, 0)), SUM(peso_aluno)),
  100 * AVG(IF(alfabetizado, 1, 0)),
  SAFE_DIVIDE(SUM(proficiencia * peso_aluno), SUM(peso_aluno))
FROM a GROUP BY ano, rede_codigo;
