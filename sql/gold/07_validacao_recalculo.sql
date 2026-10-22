-- Validacao cruzada: taxa recalculada dos microdados x taxa oficial, por nivel, ano e rede.
-- Mostra tambem o erro da versao SEM peso amostral, para evidenciar o efeito do peso.
CREATE OR REPLACE TABLE `${projeto}.${stage}.validacao_recalculo` AS
WITH pares AS (
  SELECT 'municipio' AS nivel, ano, rede_codigo, taxa_oficial, taxa_recalculada, taxa_recalculada_sem_peso
  FROM `${projeto}.${stage}.indicador_municipio`
  WHERE taxa_oficial IS NOT NULL AND taxa_recalculada IS NOT NULL
  UNION ALL
  SELECT 'uf', ano, rede_codigo, taxa_oficial, taxa_recalculada, taxa_recalculada_sem_peso
  FROM `${projeto}.${stage}.indicador_uf`
  WHERE taxa_oficial IS NOT NULL AND taxa_recalculada IS NOT NULL
  UNION ALL
  SELECT 'brasil', ano, rede_codigo, taxa_publicada, taxa_recalculada, taxa_recalculada_sem_peso
  FROM `${projeto}.${stage}.indicador_brasil`
  WHERE taxa_publicada IS NOT NULL AND taxa_recalculada IS NOT NULL
)
SELECT
  nivel,
  ano,
  rede_codigo,
  COUNT(*) AS pares,
  ROUND(AVG(ABS(taxa_recalculada - taxa_oficial)), 3) AS erro_medio_abs_pp,
  ROUND(APPROX_QUANTILES(ABS(taxa_recalculada - taxa_oficial), 100)[OFFSET(50)], 3) AS erro_mediano_abs_pp,
  ROUND(APPROX_QUANTILES(ABS(taxa_recalculada - taxa_oficial), 100)[OFFSET(95)], 3) AS erro_p95_abs_pp,
  ROUND(MAX(ABS(taxa_recalculada - taxa_oficial)), 3) AS erro_max_abs_pp,
  ROUND(100 * COUNTIF(ABS(taxa_recalculada - taxa_oficial) <= 1) / COUNT(*), 1) AS pct_ate_1pp,
  ROUND(AVG(ABS(taxa_recalculada_sem_peso - taxa_oficial)), 3) AS erro_medio_abs_sem_peso_pp
FROM pares
GROUP BY nivel, ano, rede_codigo;
