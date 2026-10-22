-- Indicador nacional por ano e rede.
-- taxa_publicada: taxa nacional que o INEP publica junto com as metas (tabela meta_alfabetizacao_brasil).
-- taxa_recalculada: agregacao de TODOS os alunos avaliados do pais, ponderada pelo peso amostral.
-- Nao existe tabela de resultado nacional na fonte, e o nacional NAO e media simples de UFs ou municipios.
CREATE OR REPLACE TABLE `${projeto}.${stage}.indicador_brasil` AS
WITH p AS (
  SELECT ano_publicacao AS ano, rede_codigo, taxa_alfabetizacao_publicada AS taxa_publicada,
         percentual_participacao
  FROM `${projeto}.${silver}.meta_base`
  WHERE nivel = 'brasil'
),
r AS (SELECT * FROM `${projeto}.${stage}.recalculo_microdados` WHERE nivel = 'brasil')
SELECT
  COALESCE(p.ano, r.ano) AS ano,
  COALESCE(p.rede_codigo, r.rede_codigo) AS rede_codigo,
  d.rede_descricao,
  p.taxa_publicada,
  r.taxa_recalculada,
  r.taxa_recalculada_sem_peso,
  r.taxa_recalculada - p.taxa_publicada AS dif_recalculo_pp,
  r.n_avaliados,
  r.soma_pesos,
  r.proficiencia_media_ponderada,
  p.percentual_participacao,
  'oficial' AS origem
FROM p
FULL OUTER JOIN r ON p.ano = r.ano AND p.rede_codigo = r.rede_codigo
LEFT JOIN `${projeto}.${silver}.dim_rede` d ON d.rede_codigo = COALESCE(p.rede_codigo, r.rede_codigo);
