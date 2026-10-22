# FinOps: custo medido e projeção

Todas as quantidades abaixo foram **medidas** no projeto `tech-challenge-alfab` em 21/10/2026, com
`scripts/medir_custos.cmd`. A saída bruta está em `docs/evidencias/finops/medicoes.txt`. Os preços
são os de lista do Google Cloud consultados na mesma data (USD; região `us-central1` para Cloud Run,
Build e Artifact Registry; multirregião `US` para BigQuery e Cloud Storage).

**Ambiente usado:** conta de avaliação (trial, crédito de US$ 300 = R$ 1.779,29) e cotas gratuitas.
A fatura do projeto estava em R$ 0,00. Por isso, a coluna "preço de lista" mostra quanto o mesmo
desenho custaria sem cota gratuita, e a coluna "após cota gratuita" mostra quanto custaria numa
conta paga comum.

Câmbio usado: **R$ 5,931 por US$**, a mesma conversão que o próprio Google aplicou ao crédito do trial.

## 1. O que foi medido

| Medição | Valor medido | Fonte |
|---|---|---|
| Bytes faturados por execução completa do batch (Bronze → Silver → Gold, na nuvem) | 2.017.460.224 B (1,88 GiB) | `ops.pipeline_execucoes`, run `20261021T211337Z` |
| Bytes faturados por micro-lote do streaming com mensagens | 220.200.960 B (210 MiB) | `ops.pipeline_execucoes`, média de 3 lotes |
| Bytes faturados por micro-lote sem mensagens | 52.428.800 B (50 MiB) | `ops.pipeline_execucoes`, 4 lotes |
| Duração do job `pipeline-batch` no Cloud Run | 332,0 s | `gcloud run jobs executions list` |
| Duração do job `pipeline-streaming` no Cloud Run (lote sem mensagens) | 60,3 s | idem |
| Duração da orquestração completa (Workflows) | 495,6 s | `gcloud workflows executions list` |
| Bronze no Cloud Storage | 149.211.574 B para 2 execuções = **74,6 MB por execução** | `gcloud storage du` |
| Armazenamento no BigQuery (todas as tabelas) | 1.135.830.949 B (1,058 GiB) | `__TABLES__` |
| ... dos quais `silver_stage` + `gold_stage` | 567.183.358 B (49,9%) | `__TABLES__` |
| Imagem do pipeline | 67.252.563 B (64 MiB) | `gcloud artifacts docker images list` |
| Build da imagem | 45 s | `gcloud builds list` |
| Mensagens do streaming | 360 mensagens, média de 261,6 B de payload | `bronze.eventos_stream` |

## 2. Tabela de custo: arquitetura implantada (cadência semanal)

O Cloud Scheduler dispara o workflow toda segunda-feira: um batch completo e um micro-lote
(52 ÷ 12 = **4,33 execuções por mês**).

| Serviço | Unidade | Quantidade medida | Preço unitário (USD) | Uso mensal projetado | Custo mensal (preço de lista) | Custo mensal após cota gratuita |
|---|---|---|---|---|---|---|
| BigQuery: consultas on-demand | TiB processado | 1,88 GiB por batch + 50 MiB por micro-lote | 6,25 / TiB (1 TiB grátis/mês) | 0,0080 TiB | US$ 0,050 | US$ 0,00 |
| BigQuery: armazenamento lógico ativo | GiB-mês | 1,058 GiB | 0,023 / GiB-mês (10 GiB grátis) | 1,058 GiB | US$ 0,024 | US$ 0,00 |
| Cloud Storage Standard (US), Bronze | GiB-mês | 74,6 MB por execução | 0,026 / GiB-mês | 0,30 GiB no 1º mês; 3,6 GiB no 12º mês | US$ 0,008 → 0,094 | US$ 0,008 → 0,094 |
| Cloud Run Jobs (1 vCPU, 1 GiB) | vCPU-s e GiB-s | 332 s (batch) + 60 s (streaming) por semana | 0,000018 / vCPU-s + 0,000002 / GiB-s (240 mil vCPU-s e 450 mil GiB-s grátis) | 1.700 vCPU-s | US$ 0,034 | US$ 0,00 |
| Cloud Workflows | passos internos | ~37 por execução¹ | 0,01 / 1.000 (5.000 grátis) | 160 passos | US$ 0,002 | US$ 0,00 |
| Cloud Scheduler | job-mês | 1 job | 0,10 / job (3 grátis por conta) | 1 job | US$ 0,100 | US$ 0,00 |
| Cloud Build | build-minuto | 45 s por build | 0,0061 / min (2.500 grátis) | 3 min (4 deploys) | US$ 0,018 | US$ 0,00 |
| Artifact Registry | GiB-mês | 64 MiB | 0,10 / GiB-mês (0,5 GiB grátis) | 0,063 GiB | US$ 0,006 | US$ 0,00 |
| **Total** | | | | | **US$ 0,24 (R$ 1,44)** no 1º mês; **US$ 0,33 (R$ 1,95)** no 12º | **US$ 0,01 (R$ 0,05)** no 1º mês; **US$ 0,09 (R$ 0,56)** no 12º |

¹ Único valor não medido diretamente: 4 passos do workflow mais os polls dos conectores do Cloud
Run, calculados pela política de polling padrão para os 332 s e 60 s medidos. Mesmo 10 vezes maior,
continuaria dentro da cota gratuita.

Por execução, o batch custa **US$ 0,0115** em BigQuery mais **US$ 0,0066** em Cloud Run, a preço de lista.

## 3. Projeção para produção com streaming de verdade

Neste cenário, o micro-lote passa a rodar **a cada 15 minutos** (2.920 lotes por mês), disparado por um
segundo job do Scheduler, e o batch continua semanal.

Premissas, declaradas:
- os eventos chegam em horário comercial (dias úteis, das 8h às 18h): 880 lotes com mensagens e
  2.040 lotes vazios por mês;
- volume de 10 mil eventos por mês (cerca de 2 por município).

Os custos por lote são os **medidos** (210 MiB e cerca de 97 s com mensagens; 50 MiB e 60 s sem
mensagens).

| Serviço | Uso mensal projetado | Custo mensal (preço de lista) | Custo mensal após cota gratuita |
|---|---|---|---|
| BigQuery: consultas | 0,28 TiB | US$ 1,76 | US$ 0,00 |
| Cloud Run Jobs | 209,7 mil vCPU-s e GiB-s | US$ 4,19 | US$ 0,00 |
| Pub/Sub (publicação + assinatura BigQuery) | 0,012 GiB | US$ 0,0005 | US$ 0,0001 |
| Cloud Scheduler | 2 jobs | US$ 0,20 | US$ 0,00 |
| Demais (armazenamento, Workflows, Build, Artifact Registry) | igual à seção 2 | US$ 0,06 | US$ 0,01 |
| **Total** | | **US$ 6,21 (R$ 36,84)** | **US$ 0,01 (R$ 0,05)** |

**Pior caso** (todos os 2.920 lotes com mensagens): US$ 9,64 (R$ 57,18) a preço de lista, e
US$ 0,80 (R$ 4,73) após a cota gratuita, porque o Cloud Run passa da cota de 240 mil vCPU-s.

**Leitura:** com streaming contínuo, o custo deixa de ser dado e passa a ser **custo fixo por lote**.
Os 50 MiB de um lote vazio vêm do mínimo de 10 MB que o BigQuery cobra por tabela consultada, e o
Cloud Run cobra no mínimo 1 minuto por execução. Os dois crescem com a frequência, e não com o volume.

## 4. Práticas aplicadas, com o efeito medido

| Prática | Onde | Efeito medido |
|---|---|---|
| Parquet + Snappy na Bronze | `pipeline/bronze.py` | Cerca de 272 MB lógicos na fonte viram **74,6 MB** por execução: **3,6x menor** |
| Seleção de colunas | consultas da Gold sobre `silver.alunos` | Dry run com todas as colunas: 547,1 MB. Com as 3 colunas do indicador: 65,0 MB (**−88,1%**) |
| Particionamento por `ano` + filtro | `silver.alunos` (`RANGE_BUCKET(ano)`) | Com o filtro `ano = 2024`: 52,7 MB (**−90,4%** em relação a todas as colunas) |
| Clusterização por UF e município | `silver.alunos`, `silver.resultado_municipio`, `gold.indicador_municipio` | Reduz a leitura em filtros por UF e município (o dry run mostra só o limite superior) |
| Trava de custo por consulta | `pipeline/bq.py`: dry run antes de cada consulta + `maximum_bytes_billed` | Nenhuma consulta roda acima de 5 GB; a maior medida foi a leitura da fonte (268,5 MB) |
| Publicação por cópia | `pipeline/camadas.py` | Cópia de tabela na mesma região não é cobrada: publicar a Silver e a Gold custa US$ 0 em consulta |
| Gravações gratuitas | load jobs para `ops`; assinatura BigQuery do Pub/Sub | Sem streaming insert pago; as métricas entram por load job (gratuito) |
| Micro-lote não reprocessa | livro-razão `ops.stream_mensagens` | Um lote sem mensagens faz 1 consulta (50 MiB) e para |
| Cadência compatível com a fonte | Scheduler semanal | A fonte muda no máximo uma vez por ano; rodar diariamente multiplicaria o custo por 7 sem ganho |
| Mesma localização para tudo | US / us-central1 | Nenhum custo de transferência entre regiões |

## 5. Otimizações identificadas (ainda não aplicadas)

1. **Expiração automática dos datasets de stage.** `silver_stage` e `gold_stage` somam 49,9% do
   armazenamento do BigQuery (567 MB) e só servem durante a validação. Uma expiração padrão de 1 dia
   reduz o armazenamento para 0,53 GiB.
2. **Só exportar a Bronze quando a fonte mudar.** O `lastModifiedTime` das tabelas da fonte é um
   metadado gratuito. Pular a exportação quando ele não mudou evita os 74,6 MB por semana na Bronze
   (3,6 GiB no 12º mês) e a leitura de 268,5 MB da fonte.
3. **Ciclo de vida no bucket.** Mover execuções da Bronze com mais de 30 dias para Nearline
   (US$ 0,015 contra 0,026 por GiB-mês).
4. **Menos consultas nas regras de qualidade.** Cada regra é uma consulta, e cada consulta paga no
   mínimo 10 MB por tabela. Agrupar as regras da mesma tabela numa só consulta reduz o piso do batch.
5. **Streaming sem contêiner.** No cenário de 15 minutos, o Cloud Run representa 67% do custo de
   lista, por causa do mínimo de 1 minuto por execução. O micro-lote é puro SQL; rodá-lo como consulta
   agendada do BigQuery eliminaria esse custo.

## Preços consultados (21/10/2026)

- [BigQuery](https://cloud.google.com/bigquery/pricing)
- [Cloud Storage](https://cloud.google.com/storage/pricing)
- [Cloud Run](https://cloud.google.com/run/pricing)
- [Workflows](https://cloud.google.com/workflows/pricing)
- [Pub/Sub](https://cloud.google.com/pubsub/pricing)
- [Cloud Scheduler](https://cloud.google.com/scheduler/pricing)
- [Cloud Build](https://cloud.google.com/build/pricing)
- [Artifact Registry](https://cloud.google.com/artifact-registry/pricing)
