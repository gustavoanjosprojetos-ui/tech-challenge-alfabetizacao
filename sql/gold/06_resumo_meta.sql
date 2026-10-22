-- Resumo executivo de meta x resultado: quantos entes em cada estado, por nivel e ano.
CREATE OR REPLACE TABLE `${projeto}.${stage}.resumo_meta` AS
SELECT
  nivel,
  ano,
  status_meta,
  COUNT(*) AS quantidade,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY nivel, ano), 1) AS pct_do_nivel_ano,
  ROUND(AVG(gap_meta_pp), 2) AS gap_medio_meta_pp
FROM `${projeto}.${stage}.meta_vs_resultado`
GROUP BY nivel, ano, status_meta;
