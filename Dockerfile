# Imagem do pipeline para os Cloud Run Jobs (batch e micro-lote do streaming).
# A configuracao vem do config.example.toml + variaveis de ambiente GCP_PROJECT e GCS_BUCKET,
# definidas no job: nenhuma credencial vai para a imagem (o job usa a propria conta de servico).
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIPELINE_CONFIG=/app/config.example.toml

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pipeline/ pipeline/
COPY sql/ sql/
COPY config.example.toml .

# O job escolhe o modulo pelos argumentos: "pipeline.run" (padrao) ou "pipeline.streaming processar".
ENTRYPOINT ["python", "-m"]
CMD ["pipeline.run"]
