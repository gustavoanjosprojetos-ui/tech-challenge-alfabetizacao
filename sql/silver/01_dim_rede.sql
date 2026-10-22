-- Codigos de rede traduzidos pela tabela oficial dicionario (nao inventamos a correspondencia).
-- O mesmo codigo tem a mesma descricao em alunos, municipio e uf (conferido na exploracao);
-- a regra de qualidade dim_rede_codigo_duplicado bloqueia se isso deixar de valer.
CREATE OR REPLACE TABLE `${projeto}.${stage}.dim_rede` AS
SELECT DISTINCT
  TRIM(chave) AS rede_codigo,
  TRIM(valor) AS rede_descricao
FROM `${projeto}.${bronze}.dicionario`
WHERE run_id = '${run_id}'
  AND nome_coluna = 'rede';
