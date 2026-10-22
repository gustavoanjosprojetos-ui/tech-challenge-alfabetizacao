@echo off
REM ============================================================================
REM Mede as quantidades reais usadas no FinOps e salva em
REM docs\evidencias\finops\medicoes.txt (evidencia versionada).
REM Rodar da raiz do projeto:  scripts\medir_custos.cmd
REM Todas as consultas sao de leitura ou dry run (custo desprezivel).
REM ============================================================================
setlocal
REM Projeto e bucket vem das variaveis de ambiente (mesmas usadas pelo pipeline):
REM     set GCP_PROJECT=seu-projeto
REM     set GCS_BUCKET=seu-bucket
if "%GCP_PROJECT%"=="" (
  echo Defina GCP_PROJECT antes de rodar. Ex.: set GCP_PROJECT=seu-projeto
  exit /b 1
)
if "%GCS_BUCKET%"=="" (
  echo Defina GCS_BUCKET antes de rodar. Ex.: set GCS_BUCKET=seu-bucket
  exit /b 1
)
set PROJETO=%GCP_PROJECT%
set BUCKET=%GCS_BUCKET%
if "%GCP_REGION%"=="" (set REGIAO=us-central1) else (set REGIAO=%GCP_REGION%)
set SAIDA=docs\evidencias\finops
if not exist %SAIDA% mkdir %SAIDA%
set ARQ=%SAIDA%\medicoes.txt

echo Medicoes FinOps - %date% %time% > %ARQ%

echo. >> %ARQ%
echo === 1. Cloud Storage: tamanho total do bucket (Bronze em Parquet/Snappy) >> %ARQ%
call gcloud storage du -s gs://%BUCKET% --project=%PROJETO% >> %ARQ% 2>&1
echo --- por tabela da Bronze (todas as execucoes) >> %ARQ%
call gcloud storage du -s gs://%BUCKET%/bronze/* --project=%PROJETO% >> %ARQ% 2>&1
echo --- quantidade de execucoes (run_id) da Bronze de alunos >> %ARQ%
call gcloud storage ls gs://%BUCKET%/bronze/alunos/*/ --project=%PROJETO% >> %ARQ% 2>&1

echo. >> %ARQ%
echo === 2. Artifact Registry: tamanho da imagem >> %ARQ%
call gcloud artifacts docker images list %REGIAO%-docker.pkg.dev/%PROJETO%/pipeline --include-tags --format="table(package,tags,createTime,metadata.imageSizeBytes)" --project=%PROJETO% >> %ARQ% 2>&1

echo. >> %ARQ%
echo === 3. Cloud Run Jobs: duracao real de cada execucao >> %ARQ%
call gcloud run jobs executions list --region=%REGIAO% --project=%PROJETO% --format="table(name,job,status.startTime,status.completionTime,status.succeededCount,status.failedCount)" >> %ARQ% 2>&1

echo. >> %ARQ%
echo === 4. Cloud Build: duracao dos builds >> %ARQ%
call gcloud builds list --region=%REGIAO% --project=%PROJETO% --limit=10 >> %ARQ% 2>&1

echo. >> %ARQ%
echo === 5. Workflows: execucoes >> %ARQ%
call gcloud workflows executions list pipeline-alfabetizacao --location=%REGIAO% --project=%PROJETO% --format="table(name.basename(),state,startTime,endTime)" >> %ARQ% 2>&1

echo. >> %ARQ%
echo === 6. BigQuery dry run: efeito de selecionar colunas e filtrar particao >> %ARQ%
echo --- fonte inteira (o que a Bronze le a cada execucao) >> %ARQ%
call bq query --project_id=%PROJETO% --dry_run --nouse_legacy_sql "SELECT * FROM `basedosdados.br_inep_avaliacao_alfabetizacao.alunos`" >> %ARQ% 2>&1
echo --- silver.alunos, todas as colunas >> %ARQ%
call bq query --project_id=%PROJETO% --dry_run --nouse_legacy_sql "SELECT * FROM silver.alunos" >> %ARQ% 2>&1
echo --- silver.alunos, so as 3 colunas do indicador >> %ARQ%
call bq query --project_id=%PROJETO% --dry_run --nouse_legacy_sql "SELECT id_municipio, alfabetizado, peso_aluno FROM silver.alunos" >> %ARQ% 2>&1
echo --- silver.alunos, 3 colunas + filtro de particao (ano = 2024) >> %ARQ%
call bq query --project_id=%PROJETO% --dry_run --nouse_legacy_sql "SELECT id_municipio, alfabetizado, peso_aluno FROM silver.alunos WHERE ano = 2024" >> %ARQ% 2>&1
echo --- consulta analitica tipica na Gold >> %ARQ%
call bq query --project_id=%PROJETO% --dry_run --nouse_legacy_sql "SELECT * FROM gold.meta_vs_resultado" >> %ARQ% 2>&1

echo. >> %ARQ%
echo === 7. BigQuery: bytes por execucao, armazenamento e volume do streaming >> %ARQ%
call bq query --project_id=%PROJETO% --nouse_legacy_sql --format=prettyjson --max_rows=200 < scripts\finops_medicoes.sql >> %ARQ% 2>&1

echo.
echo Medicoes salvas em %ARQ%
type %ARQ%
endlocal
