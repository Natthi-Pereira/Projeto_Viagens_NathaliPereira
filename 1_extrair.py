import os
import zipfile
import requests
import pandas as pd
from pathlib import Path
from psycopg2.extras import execute_values
from config import (
    PASTA_DADOS,
    CSV_SEPARADOR,
    CSV_ENCODING,
    TAMANHO_BLOCO,
    DRIVE_FILE_ID
)
from banco import conectar

# Mapeamento: Nome do arquivo CSV -> Nome da tabela Raw
TABELAS_RAW = {
    "2025_Viagem.csv": "raw_viagem",
    "2025_Pagamento.csv": "raw_pagamento",
    "2025_Passagem.csv": "raw_passagem",
    "2025_Trecho.csv": "raw_trecho"
}

def baixar_dados_drive():
    """Baixa e extrai os arquivos CSV se ainda não existirem na pasta data/."""
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    
    # Verifica se os 4 arquivos já estão presentes
    arquivos_existentes = [f.name for f in PASTA_DADOS.glob("*.csv")]
    if all(nome in arquivos_existentes for nome in TABELAS_RAW.keys()):
        print("-> Arquivos CSV já encontrados na pasta data/.")
        return

    if not DRIVE_FILE_ID:
        print("-> AVISO: DRIVE_FILE_ID não configurado no .env.")
        print("   Coloque os 4 arquivos CSV manualmente dentro da pasta 'data/'.")
        return

    print("-> Baixando arquivo compactado do Google Drive...")
    url = f"https://drive.google.com/uc?export=download&id={DRIVE_FILE_ID}"
    caminho_zip = PASTA_DADOS / "dados_viagens.zip"

    session = requests.Session()
    response = session.get(url, stream=True)
    
    # Lida com token de confirmação de arquivos grandes do Drive
    for k, v in response.cookies.items():
        if k.startswith("download_warning"):
            url = f"{url}&confirm={v}"
            response = session.get(url, stream=True)
            break

    with open(caminho_zip, "wb") as f:
        for chunk in response.iter_content(chunk_size=32768):
            if chunk:
                f.write(chunk)

    print("-> Extraindo arquivos...")
    with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
        zip_ref.extractall(PASTA_DADOS)
    
    if caminho_zip.exists():
        caminho_zip.unlink()
    print("-> Extração concluída com sucesso.")

def carregar_raw(conexao, nome_csv, tabela):
    """
    Lê o CSV em blocos e insere na tabela Raw correspondente.
    Aplica TRUNCATE antes para assegurar idempotência.
    """
    caminho_csv = PASTA_DADOS / nome_csv
    if not caminho_csv.exists():
        raise FileNotFoundError(f"Arquivo {nome_csv} não encontrado na pasta {PASTA_DADOS}")

    cursor = conexao.cursor()
    print(f"\n-> Processando {nome_csv} para {tabela}...")
    cursor.execute(f"TRUNCATE {tabela}")

    blocos = pd.read_csv(
        caminho_csv,
        sep=CSV_SEPARADOR,
        encoding=CSV_ENCODING,
        dtype=str,
        keep_default_na=False,
        chunksize=TAMANHO_BLOCO
    )

    total_linhas = 0
    for i, bloco in enumerate(blocos, start=1):
        linhas = list(bloco.itertuples(index=False, name=None))
        execute_values(cursor, f"INSERT INTO {tabela} VALUES %s", linhas)
        total_linhas += len(linhas)
        print(f"   Bloco {i} carregado: {total_linhas:,} linhas inseridas...")

    conexao.commit()
    cursor.close()
    print(f"-> Carga da tabela {tabela} finalizada com sucesso! Total: {total_linhas:,} linhas.")
    return total_linhas

def main():
    print("==================================================")
    print("FASE 1: EXTRAÇÃO E CARGA NA CAMADA RAW")
    print("==================================================")
    
    try:
        baixar_dados_drive()
    except Exception as e:
        print(f"Erro no download/extração: {e}")
        print("Certifique-se de que os CSVs estão na pasta data/.")

    try:
        conexao = conectar()
        print("-> Conectado ao banco de dados com sucesso.")
    except Exception as e:
        print(f"ERRO DE CONEXÃO COM O BANCO: {e}")
        return

    try:
        total_geral = 0
        for csv_nome, tabela in TABELAS_RAW.items():
            total_geral += carregar_raw(conexao, csv_nome, tabela)
        
        print("\n==================================================")
        print(f"CARGA RAW CONCLUÍDA: {total_geral:,} registros inseridos.")
        print("==================================================")
    except Exception as e:
        print(f"\nERRO DURANTE A CARGA: {e}")
        conexao.rollback()
        print("Operação revertida (rollback executado).")
    finally:
        conexao.close()

if __name__ == "__main__":
    main()