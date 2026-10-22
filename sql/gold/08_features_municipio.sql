-- Base para o modelo da Fase 3: uma linha por municipio (rede municipal) e ano_base.
-- REGRA ANTI-VAZAMENTO: colunas f_* usam so informacao disponivel ao fim do ano_base
-- (resultado do ano_base, participacao e nivel publicados no ano_base, e a meta para o
-- ano_alvo, que foi publicada antes). Colunas alvo_* sao do ano_alvo e NUNCA devem
-- entrar como variavel de entrada. A tabela meta_base do ano_alvo traz a taxa do proprio
-- ano_alvo (= alvo), por isso ela nao e usada aqui.
CREATE OR REPLACE TABLE `${projeto}.${stage}.features_municipio` AS
WITH base AS (
  SELECT * FROM `${projeto}.${stage}.indicador_municipio`
  WHERE rede_codigo = '3' AND tem_resultado_oficial
),
publicado_no_ano_base AS (
  SELECT id_municipio, ano_publicacao, percentual_participacao, nivel_alfabetizacao
  FROM `${projeto}.${silver}.meta_base`
  WHERE nivel = 'municipio'
),
meta_alvo AS (
  SELECT chave AS id_municipio, ano, meta_ano, status_meta
  FROM `${projeto}.${stage}.meta_vs_resultado`
  WHERE nivel = 'municipio'
)
SELECT
  t.id_municipio,
  t.sigla_uf,
  t.regiao,
  t.ano AS ano_base,
  t.ano + 1 AS ano_alvo,
  -- variaveis de entrada (conhecidas ao fim do ano_base)
  t.taxa_oficial AS f_taxa_ano_base,
  t.media_portugues AS f_media_portugues,
  t.proficiencia_media_ponderada AS f_proficiencia_media_microdado,
  t.n_avaliados AS f_n_avaliados,
  t.soma_pesos AS f_soma_pesos,
  t.proporcao_aluno_nivel_0 AS f_prop_nivel_0, t.proporcao_aluno_nivel_1 AS f_prop_nivel_1,
  t.proporcao_aluno_nivel_2 AS f_prop_nivel_2, t.proporcao_aluno_nivel_3 AS f_prop_nivel_3,
  t.proporcao_aluno_nivel_4 AS f_prop_nivel_4, t.proporcao_aluno_nivel_5 AS f_prop_nivel_5,
  t.proporcao_aluno_nivel_6 AS f_prop_nivel_6, t.proporcao_aluno_nivel_7 AS f_prop_nivel_7,
  t.proporcao_aluno_nivel_8 AS f_prop_nivel_8,
  p.percentual_participacao AS f_percentual_participacao,
  p.nivel_alfabetizacao AS f_nivel_alfabetizacao,
  m.meta_ano AS f_meta_ano_alvo,
  m.meta_ano - t.taxa_oficial AS f_esforco_necessario_pp,
  -- alvos (ano_alvo): o que o modelo deve prever
  nxt.taxa_oficial AS alvo_taxa,
  CASE m.status_meta WHEN 'atingiu' THEN TRUE WHEN 'nao_atingiu' THEN FALSE END AS alvo_atingiu_meta
FROM base t
JOIN base nxt ON nxt.id_municipio = t.id_municipio AND nxt.ano = t.ano + 1
LEFT JOIN publicado_no_ano_base p ON p.id_municipio = t.id_municipio AND p.ano_publicacao = t.ano
LEFT JOIN meta_alvo m ON m.id_municipio = t.id_municipio AND m.ano = t.ano + 1;
