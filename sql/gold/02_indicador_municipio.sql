-- Indicador Crianca Alfabetizada por municipio, ano e rede: taxa oficial (INEP) lado a lado
-- com a taxa recalculada dos microdados. FULL OUTER JOIN para nao perder linha de nenhum lado;
-- ausencia fica NULL (nunca zero).
CREATE OR REPLACE TABLE `${projeto}.${stage}.indicador_municipio`
CLUSTER BY sigla_uf, id_municipio
AS
WITH o AS (SELECT * FROM `${projeto}.${silver}.resultado_municipio`),
r AS (SELECT * FROM `${projeto}.${stage}.recalculo_microdados` WHERE nivel = 'municipio'),
j AS (
  SELECT
    COALESCE(o.ano, r.ano) AS ano,
    COALESCE(o.id_municipio, r.id_municipio) AS id_municipio,
    COALESCE(o.sigla_uf, r.sigla_uf) AS sigla_uf,
    COALESCE(o.rede_codigo, r.rede_codigo) AS rede_codigo,
    o.taxa_alfabetizacao AS taxa_oficial,
    r.taxa_recalculada,
    r.taxa_recalculada_sem_peso,
    r.n_avaliados,
    r.soma_pesos,
    r.proficiencia_media_ponderada,
    o.media_portugues,
    o.proporcao_aluno_nivel_0, o.proporcao_aluno_nivel_1, o.proporcao_aluno_nivel_2,
    o.proporcao_aluno_nivel_3, o.proporcao_aluno_nivel_4, o.proporcao_aluno_nivel_5,
    o.proporcao_aluno_nivel_6, o.proporcao_aluno_nivel_7, o.proporcao_aluno_nivel_8,
    o.taxa_alfabetizacao IS NOT NULL AS tem_resultado_oficial,
    r.taxa_recalculada IS NOT NULL AS tem_microdado
  FROM o
  FULL OUTER JOIN r
    ON o.ano = r.ano AND o.id_municipio = r.id_municipio AND o.rede_codigo = r.rede_codigo
)
SELECT
  j.*,
  u.regiao,
  d.rede_descricao,
  j.taxa_recalculada - j.taxa_oficial AS dif_recalculo_pp,
  -- variacao so quando o ano anterior imediato existe (nao compara 2023 com 2021, por exemplo)
  IF(LAG(j.ano) OVER w = j.ano - 1, j.taxa_oficial - LAG(j.taxa_oficial) OVER w, NULL) AS variacao_ano_anterior_pp,
  'oficial' AS origem
FROM j
LEFT JOIN `${projeto}.${silver}.dim_uf` u ON u.sigla_uf = j.sigla_uf
LEFT JOIN `${projeto}.${silver}.dim_rede` d ON d.rede_codigo = j.rede_codigo
WINDOW w AS (PARTITION BY j.id_municipio, j.rede_codigo ORDER BY j.ano);
