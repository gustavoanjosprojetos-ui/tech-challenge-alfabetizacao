"""Fase 1 do Tech Challenge: exploracao das tabelas br_inep_avaliacao_alfabetizacao.

Descobre o esquema sozinho (nenhum nome de coluna fixo no codigo) e gera em
saida_exploracao/:
  - relatorio.md              resumo legivel (cole aqui no chat)
  - perfil_colunas.csv        nulos, cardinalidade, min/max por coluna
  - valores_categoricos.csv   valores e contagens das colunas categoricas
  - dicionario.csv            conteudo da tabela dicionario
  - custos_consultas.csv      bytes de cada query (acumula entre execucoes; insumo do FinOps)

Uso:
    pip install -r requirements.txt
    gcloud auth application-default login
    export GCP_PROJECT=seu-projeto-gcp      # projeto que paga as queries
    python explorar.py
"""
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery

FONTE = os.environ.get("FONTE_DATASET", "basedosdados.br_inep_avaliacao_alfabetizacao")
PROJETO = os.environ.get("GCP_PROJECT")
MAX_GB_POR_QUERY = float(os.environ.get("MAX_GB_POR_QUERY", "5"))
LIMITE_CATEGORICA = int(os.environ.get("LIMITE_CATEGORICA", "60"))
SAIDA = Path(os.environ.get("SAIDA_DIR", "saida_exploracao"))

TIPOS_ESCALARES = {
    "STRING", "INT64", "INTEGER", "FLOAT64", "FLOAT", "NUMERIC", "BIGNUMERIC",
    "BOOL", "BOOLEAN", "DATE", "DATETIME", "TIMESTAMP", "TIME",
}
TIPOS_ORDENAVEIS = TIPOS_ESCALARES - {"BOOL", "BOOLEAN"}
TIPOS_DECIMAIS = {"FLOAT64", "FLOAT", "NUMERIC", "BIGNUMERIC"}

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
custos = []


def consultar(client, sql, etapa, tabela):
    """Dry run para medir bytes, recusa se passar do limite, depois executa."""
    seco = client.query(
        sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    )
    bytes_previstos = seco.total_bytes_processed
    gb = bytes_previstos / 1e9
    print(f"  [{etapa}] {tabela}: dry run = {gb:.3f} GB")
    if gb > MAX_GB_POR_QUERY:
        raise RuntimeError(
            f"Query de {etapa} em {tabela} escanearia {gb:.2f} GB, acima do limite "
            f"MAX_GB_POR_QUERY={MAX_GB_POR_QUERY}. Aumente o limite conscientemente."
        )
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            maximum_bytes_billed=max(int(MAX_GB_POR_QUERY * 1e9), 10 * 1024**2)
        ),
    )
    linhas = list(job.result())
    custos.append({
        "run_id": RUN_ID,
        "etapa": etapa,
        "tabela": tabela,
        "bytes_dry_run": bytes_previstos,
        "bytes_processados": job.total_bytes_processed,
        "bytes_faturados": job.total_bytes_billed,
        "job_id": job.job_id,
        "duracao_s": round((job.ended - job.started).total_seconds(), 2),
    })
    return linhas


def ident(nome):
    return f"`{nome}`"


def perfilar(client, tabela_id, nome, campos):
    escalares = [c for c in campos if c.field_type in TIPOS_ESCALARES]
    partes = ["COUNT(*) AS n_linhas"]
    for c in escalares:
        col = ident(c.name)
        partes.append(f"COUNTIF({col} IS NULL) AS {ident('nulos__' + c.name)}")
        partes.append(f"APPROX_COUNT_DISTINCT({col}) AS {ident('distintos__' + c.name)}")
        if c.field_type in TIPOS_ORDENAVEIS:
            partes.append(f"CAST(MIN({col}) AS STRING) AS {ident('min__' + c.name)}")
            partes.append(f"CAST(MAX({col}) AS STRING) AS {ident('max__' + c.name)}")
    sql = f"SELECT {', '.join(partes)} FROM {ident(tabela_id)}"
    r = consultar(client, sql, "perfil", nome)[0]
    n = r["n_linhas"]
    perfil = []
    for c in escalares:
        nulos = r["nulos__" + c.name]
        perfil.append({
            "tabela": nome,
            "coluna": c.name,
            "tipo": c.field_type,
            "n_linhas": n,
            "nulos": nulos,
            "pct_nulos": round(100 * nulos / n, 2) if n else None,
            "distintos_aprox": r["distintos__" + c.name],
            "min": r.get("min__" + c.name),
            "max": r.get("max__" + c.name),
        })
    nao_escalares = [c.name for c in campos if c.field_type not in TIPOS_ESCALARES]
    if nao_escalares:
        print(f"  aviso: {nome} tem colunas nao escalares ignoradas: {nao_escalares}")
    return perfil


def valores_categoricos(client, tabela_id, nome, perfil):
    cats = [
        p for p in perfil
        if p["distintos_aprox"] <= LIMITE_CATEGORICA and p["tipo"] not in TIPOS_DECIMAIS
    ]
    if not cats:
        return []
    blocos = [
        f"SELECT '{p['coluna']}' AS coluna, CAST({ident(p['coluna'])} AS STRING) AS valor, "
        f"COUNT(*) AS n FROM {ident(tabela_id)} GROUP BY 2"
        for p in cats
    ]
    sql = " UNION ALL ".join(blocos) + " ORDER BY coluna, valor"
    return [
        {"tabela": nome, "coluna": r["coluna"], "valor": r["valor"], "n": r["n"]}
        for r in consultar(client, sql, "valores", nome)
    ]


def gravar_csv(caminho, linhas, modo="w"):
    if not linhas:
        return
    novo = modo == "w" or not caminho.exists()
    with caminho.open(modo, newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        if novo:
            w.writeheader()
        w.writerows(linhas)


def comparar_chaves(perfis, valores):
    """Colunas com o mesmo nome em 2+ tabelas: tipos e conjuntos de valores."""
    tipos = {}
    for p in perfis:
        tipos.setdefault(p["coluna"], {})[p["tabela"]] = p["tipo"]
    conjuntos = {}
    for v in valores:
        conjuntos.setdefault(v["coluna"], {}).setdefault(v["tabela"], set()).add(v["valor"])

    secoes = []
    for coluna, por_tabela in sorted(tipos.items()):
        if len(por_tabela) < 2:
            continue
        linhas = [f"### `{coluna}`", ""]
        tipos_distintos = set(por_tabela.values())
        alerta = " **(tipos diferentes!)**" if len(tipos_distintos) > 1 else ""
        linhas.append("Tipos: " + ", ".join(f"{t}={tp}" for t, tp in sorted(por_tabela.items())) + alerta)
        vals = conjuntos.get(coluna, {})
        if len(vals) >= 2:
            todos = set().union(*vals.values())
            for t, s in sorted(vals.items()):
                faltam = sorted(todos - s, key=str)
                extra = f" | ausentes aqui: {faltam}" if faltam else ""
                linhas.append(f"- {t}: {sorted(s, key=str)}{extra}")
        elif vals:
            linhas.append("- (categórica em só uma tabela; nas outras tem cardinalidade alta)")
        else:
            linhas.append("- (alta cardinalidade em todas; ex.: id de município — conferir match no join)")
        secoes.append("\n".join(linhas))
    return secoes


def main():
    if not PROJETO:
        sys.exit("Defina a variavel de ambiente GCP_PROJECT com o projeto que paga as queries.")
    SAIDA.mkdir(parents=True, exist_ok=True)
    client = bigquery.Client(project=PROJETO)

    print(f"Listando tabelas de {FONTE} (metadado, sem custo)...")
    tabelas = sorted(client.list_tables(FONTE), key=lambda t: t.table_id)

    perfis, valores, resumo = [], [], []
    for t in tabelas:
        tabela_id = f"{t.project}.{t.dataset_id}.{t.table_id}"
        meta = client.get_table(tabela_id)
        print(f"\n{t.table_id}: {meta.num_rows} linhas, {meta.num_bytes / 1e6:.1f} MB")
        resumo.append({
            "tabela": t.table_id,
            "linhas": meta.num_rows,
            "mb": round(meta.num_bytes / 1e6, 1),
            "particionada_por": getattr(meta.time_partitioning, "field", None)
                or (meta.range_partitioning.field if meta.range_partitioning else None),
            "colunas": ", ".join(f"{c.name} ({c.field_type})" for c in meta.schema),
        })
        p = perfilar(client, tabela_id, t.table_id, meta.schema)
        perfis.extend(p)
        valores.extend(valores_categoricos(client, tabela_id, t.table_id, p))

    dicionario = []
    if any(t.table_id == "dicionario" for t in tabelas):
        linhas = consultar(client, f"SELECT * FROM {ident(FONTE + '.dicionario')}", "dicionario", "dicionario")
        dicionario = [dict(r.items()) for r in linhas]

    gravar_csv(SAIDA / "perfil_colunas.csv", perfis)
    gravar_csv(SAIDA / "valores_categoricos.csv", valores)
    gravar_csv(SAIDA / "dicionario.csv", dicionario)
    gravar_csv(SAIDA / "custos_consultas.csv", custos, modo="a")

    md = [f"# Exploração {FONTE}", "", f"Execução {RUN_ID}", "", "## Tabelas", ""]
    md.append("| tabela | linhas | MB | partição | colunas |")
    md.append("| --- | --- | --- | --- | --- |")
    for r in resumo:
        md.append(f"| {r['tabela']} | {r['linhas']} | {r['mb']} | {r['particionada_por'] or '-'} | {r['colunas']} |")
    md += ["", "## Colunas com nulos", ""]
    com_nulos = [p for p in perfis if p["nulos"]]
    md += [f"- {p['tabela']}.{p['coluna']}: {p['pct_nulos']}% nulos" for p in com_nulos] or ["- nenhuma"]
    md += ["", "## Faixa das colunas numéricas", ""]
    md += [
        f"- {p['tabela']}.{p['coluna']} ({p['tipo']}): min={p['min']}, max={p['max']}, distintos≈{p['distintos_aprox']}"
        for p in perfis if p["tipo"] in TIPOS_ORDENAVEIS - {"STRING"}
    ]
    md += ["", "## Colunas compartilhadas entre tabelas (candidatas a chave)", ""]
    md += comparar_chaves(perfis, valores)
    total_gb = sum(c["bytes_faturados"] or 0 for c in custos) / 1e9
    md += ["", "## Custo desta execução", "", f"{len(custos)} queries, {total_gb:.3f} GB faturados."]
    (SAIDA / "relatorio.md").write_text("\n".join(md), encoding="utf-8")

    print(f"\nPronto. Relatorio em {SAIDA / 'relatorio.md'} ({total_gb:.3f} GB faturados).")


if __name__ == "__main__":
    main()
