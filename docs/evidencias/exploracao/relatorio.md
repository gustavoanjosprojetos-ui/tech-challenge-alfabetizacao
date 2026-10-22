# Exploração basedosdados.br_inep_avaliacao_alfabetizacao

Execução 20261021T010745Z

## Tabelas

| tabela | linhas | MB | partição | colunas |
| --- | --- | --- | --- | --- |
| alunos | 3867999 | 268.5 | - | ano (INTEGER), id_municipio (STRING), id_escola (STRING), id_aluno (STRING), caderno (STRING), serie (STRING), rede (STRING), presenca (STRING), preenchimento_caderno (STRING), alfabetizado (STRING), proficiencia (FLOAT), peso_aluno (FLOAT) |
| dicionario | 27 | 0.0 | - | id_tabela (STRING), nome_coluna (STRING), chave (STRING), cobertura_temporal (STRING), valor (STRING) |
| meta_alfabetizacao_brasil | 3 | 0.0 | - | ano (INTEGER), rede (STRING), taxa_alfabetizacao (FLOAT), meta_alfabetizacao_2024 (FLOAT), meta_alfabetizacao_2025 (FLOAT), meta_alfabetizacao_2026 (FLOAT), meta_alfabetizacao_2027 (FLOAT), meta_alfabetizacao_2028 (FLOAT), meta_alfabetizacao_2029 (FLOAT), meta_alfabetizacao_2030 (FLOAT), percentual_participacao (FLOAT) |
| meta_alfabetizacao_municipio | 10704 | 1.2 | - | ano (INTEGER), id_municipio (STRING), rede (STRING), taxa_alfabetizacao (FLOAT), meta_alfabetizacao_2024 (FLOAT), meta_alfabetizacao_2025 (FLOAT), meta_alfabetizacao_2026 (FLOAT), meta_alfabetizacao_2027 (FLOAT), meta_alfabetizacao_2028 (FLOAT), meta_alfabetizacao_2029 (FLOAT), meta_alfabetizacao_2030 (FLOAT), nivel_alfabetizacao (INTEGER), percentual_participacao (FLOAT) |
| meta_alfabetizacao_uf | 81 | 0.0 | - | ano (INTEGER), sigla_uf (STRING), rede (STRING), taxa_alfabetizacao (FLOAT), meta_alfabetizacao_2024 (FLOAT), meta_alfabetizacao_2025 (FLOAT), meta_alfabetizacao_2026 (FLOAT), meta_alfabetizacao_2027 (FLOAT), meta_alfabetizacao_2028 (FLOAT), meta_alfabetizacao_2029 (FLOAT), meta_alfabetizacao_2030 (FLOAT), percentual_participacao (FLOAT) |
| municipio | 23995 | 1.8 | - | ano (INTEGER), id_municipio (STRING), serie (STRING), rede (STRING), taxa_alfabetizacao (FLOAT), media_portugues (FLOAT), proporcao_aluno_nivel_0 (FLOAT), proporcao_aluno_nivel_1 (FLOAT), proporcao_aluno_nivel_2 (FLOAT), proporcao_aluno_nivel_3 (FLOAT), proporcao_aluno_nivel_4 (FLOAT), proporcao_aluno_nivel_5 (FLOAT), proporcao_aluno_nivel_6 (FLOAT), proporcao_aluno_nivel_7 (FLOAT), proporcao_aluno_nivel_8 (FLOAT) |
| uf | 145 | 0.0 | - | ano (INTEGER), sigla_uf (STRING), serie (STRING), rede (STRING), taxa_alfabetizacao (FLOAT), media_portugues (FLOAT), proporcao_aluno_nivel_0 (FLOAT), proporcao_aluno_nivel_1 (FLOAT), proporcao_aluno_nivel_2 (FLOAT), proporcao_aluno_nivel_3 (FLOAT), proporcao_aluno_nivel_4 (FLOAT), proporcao_aluno_nivel_5 (FLOAT), proporcao_aluno_nivel_6 (FLOAT), proporcao_aluno_nivel_7 (FLOAT), proporcao_aluno_nivel_8 (FLOAT) |

## Colunas com nulos

- alunos.proficiencia: 13.27% nulos
- alunos.peso_aluno: 13.27% nulos
- meta_alfabetizacao_municipio.taxa_alfabetizacao: 1.12% nulos
- meta_alfabetizacao_municipio.meta_alfabetizacao_2024: 2.24% nulos
- meta_alfabetizacao_municipio.nivel_alfabetizacao: 1.12% nulos
- meta_alfabetizacao_municipio.percentual_participacao: 1.12% nulos
- meta_alfabetizacao_uf.taxa_alfabetizacao: 4.94% nulos
- meta_alfabetizacao_uf.meta_alfabetizacao_2024: 11.11% nulos
- meta_alfabetizacao_uf.meta_alfabetizacao_2025: 3.7% nulos
- meta_alfabetizacao_uf.meta_alfabetizacao_2026: 2.47% nulos
- meta_alfabetizacao_uf.meta_alfabetizacao_2027: 2.47% nulos
- meta_alfabetizacao_uf.meta_alfabetizacao_2028: 2.47% nulos
- meta_alfabetizacao_uf.meta_alfabetizacao_2029: 2.47% nulos
- meta_alfabetizacao_uf.meta_alfabetizacao_2030: 2.47% nulos
- meta_alfabetizacao_uf.percentual_participacao: 4.94% nulos
- municipio.proporcao_aluno_nivel_0: 48.12% nulos
- municipio.proporcao_aluno_nivel_1: 48.12% nulos
- municipio.proporcao_aluno_nivel_2: 48.12% nulos
- municipio.proporcao_aluno_nivel_3: 48.12% nulos
- municipio.proporcao_aluno_nivel_4: 48.12% nulos
- municipio.proporcao_aluno_nivel_5: 48.12% nulos
- municipio.proporcao_aluno_nivel_6: 48.12% nulos
- municipio.proporcao_aluno_nivel_7: 48.12% nulos
- municipio.proporcao_aluno_nivel_8: 48.12% nulos
- uf.proporcao_aluno_nivel_0: 48.28% nulos
- uf.proporcao_aluno_nivel_1: 48.28% nulos
- uf.proporcao_aluno_nivel_2: 48.28% nulos
- uf.proporcao_aluno_nivel_3: 48.28% nulos
- uf.proporcao_aluno_nivel_4: 48.28% nulos
- uf.proporcao_aluno_nivel_5: 48.28% nulos
- uf.proporcao_aluno_nivel_6: 48.28% nulos
- uf.proporcao_aluno_nivel_7: 48.28% nulos
- uf.proporcao_aluno_nivel_8: 48.28% nulos

## Faixa das colunas numéricas

- alunos.ano (INTEGER): min=2023, max=2024, distintos≈2
- alunos.proficiencia (FLOAT): min=578.46, max=904.382031, distintos≈1298984
- alunos.peso_aluno (FLOAT): min=0.0952381, max=142.5454, distintos≈70315
- meta_alfabetizacao_brasil.ano (INTEGER): min=2023, max=2025, distintos≈3
- meta_alfabetizacao_brasil.taxa_alfabetizacao (FLOAT): min=55.9, max=66, distintos≈3
- meta_alfabetizacao_brasil.meta_alfabetizacao_2024 (FLOAT): min=59.9, max=60, distintos≈2
- meta_alfabetizacao_brasil.meta_alfabetizacao_2025 (FLOAT): min=63.77, max=64, distintos≈2
- meta_alfabetizacao_brasil.meta_alfabetizacao_2026 (FLOAT): min=67, max=67.47, distintos≈2
- meta_alfabetizacao_brasil.meta_alfabetizacao_2027 (FLOAT): min=70.97, max=71, distintos≈2
- meta_alfabetizacao_brasil.meta_alfabetizacao_2028 (FLOAT): min=74, max=74.23, distintos≈2
- meta_alfabetizacao_brasil.meta_alfabetizacao_2029 (FLOAT): min=77, max=77.24, distintos≈2
- meta_alfabetizacao_brasil.meta_alfabetizacao_2030 (FLOAT): min=80, max=80, distintos≈1
- meta_alfabetizacao_brasil.percentual_participacao (FLOAT): min=86, max=88, distintos≈3
- meta_alfabetizacao_municipio.ano (INTEGER): min=2023, max=2024, distintos≈2
- meta_alfabetizacao_municipio.taxa_alfabetizacao (FLOAT): min=4.4, max=100, distintos≈3873
- meta_alfabetizacao_municipio.meta_alfabetizacao_2024 (FLOAT): min=7.94, max=80, distintos≈2748
- meta_alfabetizacao_municipio.meta_alfabetizacao_2025 (FLOAT): min=14.05, max=80, distintos≈2502
- meta_alfabetizacao_municipio.meta_alfabetizacao_2026 (FLOAT): min=23.65, max=80, distintos≈2284
- meta_alfabetizacao_municipio.meta_alfabetizacao_2027 (FLOAT): min=37, max=80, distintos≈1887
- meta_alfabetizacao_municipio.meta_alfabetizacao_2028 (FLOAT): min=52.68, max=80, distintos≈1387
- meta_alfabetizacao_municipio.meta_alfabetizacao_2029 (FLOAT): min=67.85, max=80, distintos≈755
- meta_alfabetizacao_municipio.meta_alfabetizacao_2030 (FLOAT): min=80, max=80, distintos≈1
- meta_alfabetizacao_municipio.nivel_alfabetizacao (INTEGER): min=0, max=5, distintos≈6
- meta_alfabetizacao_municipio.percentual_participacao (FLOAT): min=70, max=100, distintos≈2152
- meta_alfabetizacao_uf.ano (INTEGER): min=2023, max=2025, distintos≈3
- meta_alfabetizacao_uf.taxa_alfabetizacao (FLOAT): min=31.3, max=85.31, distintos≈69
- meta_alfabetizacao_uf.meta_alfabetizacao_2024 (FLOAT): min=38, max=80, distintos≈42
- meta_alfabetizacao_uf.meta_alfabetizacao_2025 (FLOAT): min=45.9, max=80, distintos≈44
- meta_alfabetizacao_uf.meta_alfabetizacao_2026 (FLOAT): min=53.6, max=80, distintos≈39
- meta_alfabetizacao_uf.meta_alfabetizacao_2027 (FLOAT): min=61, max=80, distintos≈38
- meta_alfabetizacao_uf.meta_alfabetizacao_2028 (FLOAT): min=68, max=80, distintos≈32
- meta_alfabetizacao_uf.meta_alfabetizacao_2029 (FLOAT): min=74.6, max=80, distintos≈25
- meta_alfabetizacao_uf.meta_alfabetizacao_2030 (FLOAT): min=80, max=80, distintos≈1
- meta_alfabetizacao_uf.percentual_participacao (FLOAT): min=70.05, max=98.13, distintos≈62
- municipio.ano (INTEGER): min=2023, max=2024, distintos≈2
- municipio.taxa_alfabetizacao (FLOAT): min=2.12, max=100, distintos≈6161
- municipio.media_portugues (FLOAT): min=673.2983, max=868.4554, distintos≈13328
- municipio.proporcao_aluno_nivel_0 (FLOAT): min=0, max=30, distintos≈941
- municipio.proporcao_aluno_nivel_1 (FLOAT): min=0, max=50, distintos≈1372
- municipio.proporcao_aluno_nivel_2 (FLOAT): min=0, max=47.06, distintos≈1919
- municipio.proporcao_aluno_nivel_3 (FLOAT): min=0, max=59.73, distintos≈2286
- municipio.proporcao_aluno_nivel_4 (FLOAT): min=0, max=64.71, distintos≈2619
- municipio.proporcao_aluno_nivel_5 (FLOAT): min=0, max=70, distintos≈2965
- municipio.proporcao_aluno_nivel_6 (FLOAT): min=0, max=68.75, distintos≈2893
- municipio.proporcao_aluno_nivel_7 (FLOAT): min=0, max=61.54, distintos≈2149
- municipio.proporcao_aluno_nivel_8 (FLOAT): min=0, max=89.71, distintos≈1401
- uf.ano (INTEGER): min=2023, max=2024, distintos≈2
- uf.taxa_alfabetizacao (FLOAT): min=30.57, max=86.21, distintos≈139
- uf.media_portugues (FLOAT): min=712.562, max=797.34, distintos≈140
- uf.proporcao_aluno_nivel_0 (FLOAT): min=0, max=8.16, distintos≈60
- uf.proporcao_aluno_nivel_1 (FLOAT): min=1.41, max=11.74, distintos≈65
- uf.proporcao_aluno_nivel_2 (FLOAT): min=2.44, max=20.6, distintos≈68
- uf.proporcao_aluno_nivel_3 (FLOAT): min=1.52, max=20.07, distintos≈65
- uf.proporcao_aluno_nivel_4 (FLOAT): min=6.11, max=27.77, distintos≈69
- uf.proporcao_aluno_nivel_5 (FLOAT): min=10.14, max=40.41, distintos≈67
- uf.proporcao_aluno_nivel_6 (FLOAT): min=8.24, max=35.66, distintos≈69
- uf.proporcao_aluno_nivel_7 (FLOAT): min=2.1, max=23.76, distintos≈67
- uf.proporcao_aluno_nivel_8 (FLOAT): min=0, max=31.24, distintos≈64

## Colunas compartilhadas entre tabelas (candidatas a chave)

### `ano`

Tipos: alunos=INTEGER, meta_alfabetizacao_brasil=INTEGER, meta_alfabetizacao_municipio=INTEGER, meta_alfabetizacao_uf=INTEGER, municipio=INTEGER, uf=INTEGER
- alunos: ['2023', '2024'] | ausentes aqui: ['2025']
- meta_alfabetizacao_brasil: ['2023', '2024', '2025']
- meta_alfabetizacao_municipio: ['2023', '2024'] | ausentes aqui: ['2025']
- meta_alfabetizacao_uf: ['2023', '2024', '2025']
- municipio: ['2023', '2024'] | ausentes aqui: ['2025']
- uf: ['2023', '2024'] | ausentes aqui: ['2025']
### `id_municipio`

Tipos: alunos=STRING, meta_alfabetizacao_municipio=STRING, municipio=STRING
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `media_portugues`

Tipos: municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `meta_alfabetizacao_2024`

Tipos: meta_alfabetizacao_brasil=FLOAT, meta_alfabetizacao_municipio=FLOAT, meta_alfabetizacao_uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `meta_alfabetizacao_2025`

Tipos: meta_alfabetizacao_brasil=FLOAT, meta_alfabetizacao_municipio=FLOAT, meta_alfabetizacao_uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `meta_alfabetizacao_2026`

Tipos: meta_alfabetizacao_brasil=FLOAT, meta_alfabetizacao_municipio=FLOAT, meta_alfabetizacao_uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `meta_alfabetizacao_2027`

Tipos: meta_alfabetizacao_brasil=FLOAT, meta_alfabetizacao_municipio=FLOAT, meta_alfabetizacao_uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `meta_alfabetizacao_2028`

Tipos: meta_alfabetizacao_brasil=FLOAT, meta_alfabetizacao_municipio=FLOAT, meta_alfabetizacao_uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `meta_alfabetizacao_2029`

Tipos: meta_alfabetizacao_brasil=FLOAT, meta_alfabetizacao_municipio=FLOAT, meta_alfabetizacao_uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `meta_alfabetizacao_2030`

Tipos: meta_alfabetizacao_brasil=FLOAT, meta_alfabetizacao_municipio=FLOAT, meta_alfabetizacao_uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `percentual_participacao`

Tipos: meta_alfabetizacao_brasil=FLOAT, meta_alfabetizacao_municipio=FLOAT, meta_alfabetizacao_uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `proporcao_aluno_nivel_0`

Tipos: municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `proporcao_aluno_nivel_1`

Tipos: municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `proporcao_aluno_nivel_2`

Tipos: municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `proporcao_aluno_nivel_3`

Tipos: municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `proporcao_aluno_nivel_4`

Tipos: municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `proporcao_aluno_nivel_5`

Tipos: municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `proporcao_aluno_nivel_6`

Tipos: municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `proporcao_aluno_nivel_7`

Tipos: municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `proporcao_aluno_nivel_8`

Tipos: municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)
### `rede`

Tipos: alunos=STRING, meta_alfabetizacao_brasil=STRING, meta_alfabetizacao_municipio=STRING, meta_alfabetizacao_uf=STRING, municipio=STRING, uf=STRING
- alunos: ['2', '3', '4'] | ausentes aqui: ['0', '5', 'Municipal', 'Pública']
- meta_alfabetizacao_brasil: ['Pública'] | ausentes aqui: ['0', '2', '3', '4', '5', 'Municipal']
- meta_alfabetizacao_municipio: ['Municipal'] | ausentes aqui: ['0', '2', '3', '4', '5', 'Pública']
- meta_alfabetizacao_uf: ['Pública'] | ausentes aqui: ['0', '2', '3', '4', '5', 'Municipal']
- municipio: ['0', '2', '3', '5'] | ausentes aqui: ['4', 'Municipal', 'Pública']
- uf: ['0', '2', '3', '5'] | ausentes aqui: ['4', 'Municipal', 'Pública']
### `serie`

Tipos: alunos=STRING, municipio=STRING, uf=STRING
- alunos: ['2']
- municipio: ['2']
- uf: ['2']
### `sigla_uf`

Tipos: meta_alfabetizacao_uf=STRING, uf=STRING
- meta_alfabetizacao_uf: ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']
- uf: ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RS', 'SC', 'SE', 'SP', 'TO'] | ausentes aqui: ['DF', 'RR']
### `taxa_alfabetizacao`

Tipos: meta_alfabetizacao_brasil=FLOAT, meta_alfabetizacao_municipio=FLOAT, meta_alfabetizacao_uf=FLOAT, municipio=FLOAT, uf=FLOAT
- (alta cardinalidade em todas; ex.: id de município — conferir match no join)

## Custo desta execução

15 queries, 0.509 GB faturados.