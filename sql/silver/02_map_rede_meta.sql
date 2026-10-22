-- As tabelas de meta usam rotulos em texto ('Municipal', 'Pública') e o dicionario oficial
-- nao cobre essas tabelas. Esta e a unica correspondencia definida pela equipe, explicita e justificada.
-- Rotulo novo na fonte fica sem codigo e a regra meta_rede_sem_mapeamento bloqueia o pipeline.
CREATE OR REPLACE TABLE `${projeto}.${stage}.map_rede_meta` AS
SELECT * FROM UNNEST([
  STRUCT(
    'Municipal' AS rotulo_meta,
    '3' AS rede_codigo,
    'Metas municipais: rede municipal (dicionario: 3 = Municipal).' AS justificativa
  ),
  (
    'Pública',
    '5',
    'Metas de UF e Brasil: rede publica estadual e municipal (dicionario: 5). O codigo 6 (com federal) nao aparece em nenhuma tabela de resultado, e alunos nao tem rede federal.'
  )
]);
