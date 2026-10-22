-- Indicador por UF, ano e rede: oficial x recalculado dos microdados.
-- O recalculado por UF agrega ALUNOS (ponderado por peso), nunca media simples de municipios.
CREATE OR REPLACE TABLE `${projeto}.${stage}.indicador_uf` AS
WITH o AS (SELECT * FROM `${projeto}.${silver}.resultado_uf`),
r AS (SELECT * FROM `${projeto}.${stage}.recalculo_microdados` WHERE nivel = 'uf'),
j AS (
  SELECT
    COALESCE(o.ano, r.ano) AS ano,
    COALESCE(o.sigla_uf, r.sigla_uf) AS sigla_uf,
    COALESCE(o.rede_codigo, r.rede_codigo) AS rede_codigo,
    o.taxa_alfabetizacao AS taxa_oficial,
    r.taxa_recalculada,
    r.taxa_recalculada_sem_peso,
    r.n_avaliados,
    r.soma_pesos,
    r.proficiencia_media_ponderada,
    o.media_portugues,
    o.taxa_alfabetizacao IS NOT NULL AS tem_resultado_oficial,
    r.taxa_recalculada IS NOT NULL AS tem_microdado
  FROM o
  FULL OUTER JOIN r
    ON o.ano = r.ano AND o.sigla_uf = r.sigla_uf AND o.rede_codigo = r.rede_codigo
)
SELECT
  j.*,
  u.regiao,
  d.rede_descricao,
  j.taxa_recalculada - j.taxa_oficial AS dif_recalculo_pp,
  IF(LAG(j.ano) OVER w = j.ano - 1, j.taxa_oficial - LAG(j.taxa_oficial) OVER w, NULL) AS variacao_ano_anterior_pp,
  'oficial' AS origem
FROM j
LEFT JOIN `${projeto}.${silver}.dim_uf` u ON u.sigla_uf = j.sigla_uf
LEFT JOIN `${projeto}.${silver}.dim_rede` d ON d.rede_codigo = j.rede_codigo
WINDOW w AS (PARTITION BY j.sigla_uf, j.rede_codigo ORDER BY j.ano);
