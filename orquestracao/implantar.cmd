@echo off
REM ============================================================================
REM Implanta a orquestracao na nuvem (Windows, Prompt de Comando).
REM Rodar da pasta raiz do projeto, com o .venv ativo:
REM     orquestracao\implantar.cmd SEU-EMAIL@exemplo.com
REM Pode rodar de novo: passos que ja existem so avisam e seguem.
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
set EMAIL=%~1

if "%EMAIL%"=="" (
  echo Informe o e-mail que recebe os alertas: orquestracao\implantar.cmd seu-email@exemplo.com
  exit /b 1
)

set REPO=pipeline
set IMAGEM=%REGIAO%-docker.pkg.dev/%PROJETO%/%REPO%/pipeline:latest
set SA_BUILD=pipeline-build@%PROJETO%.iam.gserviceaccount.com
set SA_RUN=pipeline-runner@%PROJETO%.iam.gserviceaccount.com
set SA_ORQ=pipeline-orquestrador@%PROJETO%.iam.gserviceaccount.com

echo.
echo === 1/8 Ativando as APIs (pode levar 1-2 minutos)
call gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com workflows.googleapis.com workflowexecutions.googleapis.com cloudscheduler.googleapis.com monitoring.googleapis.com logging.googleapis.com iam.googleapis.com --project=%PROJETO%

echo.
echo === 2/8 Criando as contas de servico (uma por papel, permissao minima)
call gcloud iam service-accounts create pipeline-build --display-name="Pipeline - build da imagem" --project=%PROJETO%
call gcloud iam service-accounts create pipeline-runner --display-name="Pipeline - execucao (BigQuery e GCS)" --project=%PROJETO%
call gcloud iam service-accounts create pipeline-orquestrador --display-name="Pipeline - Workflows e Scheduler" --project=%PROJETO%

echo.
echo === 3/8 Concedendo permissoes
REM build: ler o codigo enviado, publicar a imagem e escrever logs
call gcloud projects add-iam-policy-binding %PROJETO% --member=serviceAccount:%SA_BUILD% --role=roles/storage.objectViewer --condition=None --quiet >nul
call gcloud projects add-iam-policy-binding %PROJETO% --member=serviceAccount:%SA_BUILD% --role=roles/artifactregistry.writer --condition=None --quiet >nul
call gcloud projects add-iam-policy-binding %PROJETO% --member=serviceAccount:%SA_BUILD% --role=roles/logging.logWriter --condition=None --quiet >nul
REM execucao: consultas e tabelas no BigQuery, arquivos so no bucket do projeto
call gcloud projects add-iam-policy-binding %PROJETO% --member=serviceAccount:%SA_RUN% --role=roles/bigquery.jobUser --condition=None --quiet >nul
call gcloud projects add-iam-policy-binding %PROJETO% --member=serviceAccount:%SA_RUN% --role=roles/bigquery.dataEditor --condition=None --quiet >nul
call gcloud storage buckets add-iam-policy-binding gs://%BUCKET% --member=serviceAccount:%SA_RUN% --role=roles/storage.objectAdmin --quiet >nul
REM orquestrador: executar os jobs, disparar o workflow e escrever logs
call gcloud projects add-iam-policy-binding %PROJETO% --member=serviceAccount:%SA_ORQ% --role=roles/run.developer --condition=None --quiet >nul
call gcloud projects add-iam-policy-binding %PROJETO% --member=serviceAccount:%SA_ORQ% --role=roles/workflows.invoker --condition=None --quiet >nul
call gcloud projects add-iam-policy-binding %PROJETO% --member=serviceAccount:%SA_ORQ% --role=roles/logging.logWriter --condition=None --quiet >nul
call gcloud iam service-accounts add-iam-policy-binding %SA_RUN% --member=serviceAccount:%SA_ORQ% --role=roles/iam.serviceAccountUser --project=%PROJETO% --quiet >nul
echo Permissoes concedidas. Aguardando 60 s para que passem a valer...
timeout /t 60 /nobreak >nul

echo.
echo === 4/8 Construindo a imagem do pipeline (Cloud Build, 2-4 minutos)
call gcloud artifacts repositories create %REPO% --repository-format=docker --location=%REGIAO% --project=%PROJETO%
call gcloud builds submit --project=%PROJETO% --region=%REGIAO% --config=orquestracao/cloudbuild.yaml --substitutions=_IMAGEM=%IMAGEM% --service-account=projects/%PROJETO%/serviceAccounts/%SA_BUILD% .
if errorlevel 1 (
  echo ERRO: o build da imagem falhou. Envie o print desta tela.
  exit /b 1
)

echo.
echo === 5/8 Criando os Cloud Run Jobs
call gcloud run jobs deploy pipeline-batch --image=%IMAGEM% --region=%REGIAO% --project=%PROJETO% --service-account=%SA_RUN% --set-env-vars=GCP_PROJECT=%PROJETO%,GCS_BUCKET=%BUCKET% --args=pipeline.run --task-timeout=3600 --max-retries=0 --memory=1Gi --quiet
call gcloud run jobs deploy pipeline-streaming --image=%IMAGEM% --region=%REGIAO% --project=%PROJETO% --service-account=%SA_RUN% --set-env-vars=GCP_PROJECT=%PROJETO%,GCS_BUCKET=%BUCKET% --args=pipeline.streaming,processar --task-timeout=1800 --max-retries=0 --memory=1Gi --quiet

echo.
echo === 6/8 Implantando o workflow
call gcloud workflows deploy pipeline-alfabetizacao --source=orquestracao/workflow.yaml --location=%REGIAO% --service-account=%SA_ORQ% --project=%PROJETO%

echo.
echo === 7/8 Agendando: toda segunda-feira as 06:00 (horario de Brasilia)
call gcloud scheduler jobs create http pipeline-semanal --location=%REGIAO% --project=%PROJETO% --schedule="0 6 * * 1" --time-zone="America/Sao_Paulo" --uri="https://workflowexecutions.googleapis.com/v1/projects/%PROJETO%/locations/%REGIAO%/workflows/pipeline-alfabetizacao/executions" --http-method=POST --message-body="{}" --oauth-service-account-email=%SA_ORQ%

echo.
echo === 8/8 Configurando o alerta de falha por e-mail
python -m pipeline.setup_alerta --email %EMAIL%

echo.
echo Pronto. Para testar agora:
echo   gcloud workflows run pipeline-alfabetizacao --location=%REGIAO% --project=%PROJETO%
endlocal
