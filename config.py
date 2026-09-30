import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do ficheiro .env
load_dotenv()

# Caminhos do projeto
PASTA_PROJETO = Path(__file__).parent
PASTA_DADOS = PASTA_PROJETO / "data"

# Parâmetros de leitura dos CSVs
CSV_SEPARADOR = ";"
CSV_ENCODING = "latin-1"
TAMANHO_BLOCO = 50_000

# Parâmetros da Base de Dados PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "transparencia")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")

# ID do ficheiro do Drive para download automático
DRIVE_FILE_ID = os.getenv("DRIVE_FILE_ID", "")