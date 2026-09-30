import psycopg2
from psycopg2.extras import execute_values
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

def conectar(nome_banco=None):
    """Estabelece a ligação com o PostgreSQL."""
    banco = nome_banco if nome_banco else DB_NAME
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=banco,
        user=DB_USER,
        password=DB_PASS
    )

def executar(conexao, sql, parametros=None):
    """Executa um comando SQL (DDL ou DML)."""
    with conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
    conexao.commit()

def inserir_em_lote(conexao, sql, dados):
    """Insere dados em massa de forma eficiente."""
    with conexao.cursor() as cursor:
        execute_values(cursor, sql, dados)
    conexao.commit()