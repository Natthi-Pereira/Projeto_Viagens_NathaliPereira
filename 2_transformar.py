import pandas as pd
from psycopg2.extras import execute_values
from config import TAMANHO_BLOCO
from banco import conectar

# ============================================================================
# FUNÇÕES ESPECÍFICAS DE CONVERSÃO E LIMPEZA
# ============================================================================

def texto_para_decimal(coluna):
    """Converte '1272,97' para 1272.97. Valores vazios viram NaN."""
    if coluna is None:
        return None
    coluna_limpa = coluna.astype(str).str.strip().str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(coluna_limpa, errors="coerce")

def texto_para_data(coluna):
    """Converte datas em formato DD/MM/AAAA para datetime. Texto vazio vira NaT."""
    if coluna is None:
        return None
    return pd.to_datetime(coluna.astype(str).str.strip(), format="%d/%m/%Y", errors="coerce")

def limpar_texto(coluna):
    """Remove espaços em branco nas pontas e normaliza textos vazios."""
    if coluna is None:
        return None
    return coluna.astype(str).str.strip()

# ============================================================================
# TRANSFORMAÇÃO E CARGA DE CADA TABELA
# ============================================================================

def transformar_viagem(conexao):
    """Transforma dados de raw_viagem para silver_viagem (Tabela Mãe)."""
    print("\n-> Transformando e carregando silver_viagem...")
    cursor = conexao.cursor()

    # Busca registros da raw_viagem
    query = """
        SELECT
            identificador_processo_viagem,
            numero_proposta_rede,
            situacao,
            viagem_urgente,
            codigo_orgao_superior,
            nome_orgao_superior,
            nome_viajante,
            cargo,
            periodo_data_inicio,
            periodo_data_fim,
            destinos,
            motivo,
            valor_diarias,
            valor_passagens,
            valor_devolucao,
            valor_outros_gastos
        FROM raw_viagem
    """
    df = pd.read_sql(query, conexao)

    # Limpeza de texto
    for col in ["identificador_processo_viagem", "numero_proposta_rede", "situacao", 
                "viagem_urgente", "codigo_orgao_superior", "nome_orgao_superior", 
                "nome_viajante", "cargo", "destinos", "motivo"]:
        df[col] = limpar_texto(df[col])

    # Conversões de Datas
    df["data_inicio"] = texto_para_data(df["periodo_data_inicio"])
    df["data_fim"] = texto_para_data(df["periodo_data_fim"])

    # Conversões Financeiras
    df["v_diarias"] = texto_para_decimal(df["valor_diarias"]).fillna(0.0)
    df["v_passagens"] = texto_para_decimal(df["valor_passagens"]).fillna(0.0)
    df["v_devolucao"] = texto_para_decimal(df["valor_devolucao"]).fillna(0.0)
    df["v_outros"] = texto_para_decimal(df["valor_outros_gastos"]).fillna(0.0)

    # Colunas Calculadas
    df["valor_total"] = df["v_diarias"] + df["v_passagens"] + df["v_outros"] - df["v_devolucao"]
    df["duracao_dias"] = (df["data_fim"] - df["data_inicio"]).dt.days + 1
    # Caso data_fim ou data_inicio sejam nulas, duracao_dias fica nula
    df["duracao_dias"] = df["duracao_dias"].where(df["data_inicio"].notna() & df["data_fim"].notna(), None)

    # Garante que campos obrigatórios atendam às constraints
    df["nome_orgao_superior"] = df["nome_orgao_superior"].replace("", "ÓRGÃO NÃO INFORMADO").fillna("ÓRGÃO NÃO INFORMADO")
    df["v_diarias"] = df["v_diarias"].apply(lambda x: max(x, 0.0))

    df_silver = pd.DataFrame({
        "id_viagem": df["identificador_processo_viagem"],
        "num_proposta": df["numero_proposta_rede"],
        "situacao": df["situacao"],
        "viagem_urgente": df["viagem_urgente"],
        "cod_orgao_superior": df["codigo_orgao_superior"],
        "nome_orgao_superior": df["nome_orgao_superior"],
        "nome_viajante": df["nome_viajante"],
        "cargo": df["cargo"],
        "data_inicio": df["data_inicio"].dt.strftime("%Y-%m-%d").where(df["data_inicio"].notna(), None),
        "data_fim": df["data_fim"].dt.strftime("%Y-%m-%d").where(df["data_fim"].notna(), None),
        "destinos": df["destinos"],
        "motivo": df["motivo"],
        "valor_diarias": df["v_diarias"],
        "valor_passagens": df["v_passagens"],
        "valor_devolucao": df["v_devolucao"],
        "valor_outros_gastos": df["v_outros"],
        "valor_total": df["valor_total"],
        "duracao_dias": df["duracao_dias"]
    })

    # Tratamento para None em valores nulos
    df_silver = df_silver.astype(object).where(pd.notna(df_silver), None)

    # Inserção em blocos na Silver
    sql_insert = """
        INSERT INTO silver_viagem (
            id_viagem, num_proposta, situacao, viagem_urgente, cod_orgao_superior,
            nome_orgao_superior, nome_viajante, cargo, data_inicio, data_fim,
            destinos, motivo, valor_diarias, valor_passagens, valor_devolucao,
            valor_outros_gastos, valor_total, duracao_dias
        ) VALUES %s
    """
    total = len(df_silver)
    for i in range(0, total, TAMANHO_BLOCO):
        lote = df_silver.iloc[i:i + TAMANHO_BLOCO]
        linhas = list(lote.itertuples(index=False, name=None))
        execute_values(cursor, sql_insert, linhas)

    conexao.commit()
    cursor.close()
    print(f"-> silver_viagem finalizada com {total:,} registros.")
    return total

def transformar_pagamento(conexao):
    """Transforma dados de raw_pagamento para silver_pagamento (Tabela Filha)."""
    print("\n-> Transformando e carregando silver_pagamento...")
    cursor = conexao.cursor()

    query = """
        SELECT
            p.identificador_processo_viagem,
            p.numero_proposta_rede,
            p.nome_orgao_pagador,
            p.nome_unidade_gestora_pagadora,
            p.tipo_pagamento,
            p.valor
        FROM raw_pagamento p
        INNER JOIN silver_viagem v ON v.id_viagem = p.identificador_processo_viagem
    """
    df = pd.read_sql(query, conexao)

    df["id_viagem"] = limpar_texto(df["identificador_processo_viagem"])
    df["num_proposta"] = limpar_texto(df["numero_proposta_rede"])
    df["nome_orgao_pagador"] = limpar_texto(df["nome_orgao_pagador"])
    df["nome_ug_pagadora"] = limpar_texto(df["nome_unidade_gestora_pagadora"])
    df["tipo_pagamento"] = limpar_texto(df["tipo_pagamento"]).replace("", "Outros").fillna("Outros")
    df["valor"] = texto_para_decimal(df["valor"]).fillna(0.0)
    df["valor"] = df["valor"].apply(lambda x: max(x, 0.0))

    df_silver = pd.DataFrame({
        "id_viagem": df["id_viagem"],
        "num_proposta": df["num_proposta"],
        "nome_orgao_pagador": df["nome_orgao_pagador"],
        "nome_ug_pagadora": df["nome_ug_pagadora"],
        "tipo_pagamento": df["tipo_pagamento"],
        "valor": df["valor"]
    })

    df_silver = df_silver.astype(object).where(pd.notna(df_silver), None)

    sql_insert = """
        INSERT INTO silver_pagamento (
            id_viagem, num_proposta, nome_orgao_pagador,
            nome_ug_pagadora, tipo_pagamento, valor
        ) VALUES %s
    """
    total = len(df_silver)
    for i in range(0, total, TAMANHO_BLOCO):
        lote = df_silver.iloc[i:i + TAMANHO_BLOCO]
        linhas = list(lote.itertuples(index=False, name=None))
        execute_values(cursor, sql_insert, linhas)

    conexao.commit()
    cursor.close()
    print(f"-> silver_pagamento finalizada com {total:,} registros.")
    return total

def transformar_passagem(conexao):
    """Transforma dados de raw_passagem para silver_passagem (Tabela Filha)."""
    print("\n-> Transformando e carregando silver_passagem...")
    cursor = conexao.cursor()

    query = """
        SELECT
            p.identificador_processo_viagem,
            p.meio_transporte,
            p.pais_origem_ida,
            p.uf_origem_ida,
            p.cidade_origem_ida,
            p.pais_destino_ida,
            p.uf_destino_ida,
            p.cidade_destino_ida,
            p.valor_passagem,
            p.taxa_servico,
            p.data_emissao_bilhete
        FROM raw_passagem p
        INNER JOIN silver_viagem v ON v.id_viagem = p.identificador_processo_viagem
    """
    df = pd.read_sql(query, conexao)

    for col in ["meio_transporte", "pais_origem_ida", "uf_origem_ida", "cidade_origem_ida",
                "pais_destino_ida", "uf_destino_ida", "cidade_destino_ida"]:
        df[col] = limpar_texto(df[col])

    df["id_viagem"] = limpar_texto(df["identificador_processo_viagem"])
    df["v_passagem"] = texto_para_decimal(df["valor_passagem"]).fillna(0.0).apply(lambda x: max(x, 0.0))
    df["v_taxa"] = texto_para_decimal(df["taxa_servico"]).fillna(0.0).apply(lambda x: max(x, 0.0))
    df["dt_emissao"] = texto_para_data(df["data_emissao_bilhete"])

    df_silver = pd.DataFrame({
        "id_viagem": df["id_viagem"],
        "meio_transporte": df["meio_transporte"],
        "pais_origem_ida": df["pais_origem_ida"],
        "uf_origem_ida": df["uf_origem_ida"],
        "cidade_origem_ida": df["cidade_origem_ida"],
        "pais_destino_ida": df["pais_destino_ida"],
        "uf_destino_ida": df["uf_destino_ida"],
        "cidade_destino_ida": df["cidade_destino_ida"],
        "valor_passagem": df["v_passagem"],
        "taxa_servico": df["v_taxa"],
        "data_emissao": df["dt_emissao"].dt.strftime("%Y-%m-%d").where(df["dt_emissao"].notna(), None)
    })

    df_silver = df_silver.astype(object).where(pd.notna(df_silver), None)

    sql_insert = """
        INSERT INTO silver_passagem (
            id_viagem, meio_transporte, pais_origem_ida, uf_origem_ida, cidade_origem_ida,
            pais_destino_ida, uf_destino_ida, cidade_destino_ida, valor_passagem,
            taxa_servico, data_emissao
        ) VALUES %s
    """
    total = len(df_silver)
    for i in range(0, total, TAMANHO_BLOCO):
        lote = df_silver.iloc[i:i + TAMANHO_BLOCO]
        linhas = list(lote.itertuples(index=False, name=None))
        execute_values(cursor, sql_insert, linhas)

    conexao.commit()
    cursor.close()
    print(f"-> silver_passagem finalizada com {total:,} registros.")
    return total

def transformar_trecho(conexao):
    """Transforma dados de raw_trecho para silver_trecho (Tabela Filha)."""
    print("\n-> Transformando e carregando silver_trecho...")
    cursor = conexao.cursor()

    query = """
        SELECT
            t.identificador_processo_viagem,
            t.sequencia_trecho,
            t.origem_data,
            t.origem_uf,
            t.origem_cidade,
            t.destino_data,
            t.destino_uf,
            t.destino_cidade,
            t.meio_transporte,
            t.numero_diarias
        FROM raw_trecho t
        INNER JOIN silver_viagem v ON v.id_viagem = t.identificador_processo_viagem
    """
    df = pd.read_sql(query, conexao)

    for col in ["origem_uf", "origem_cidade", "destino_uf", "destino_cidade", "meio_transporte"]:
        df[col] = limpar_texto(df[col])

    df["id_viagem"] = limpar_texto(df["identificador_processo_viagem"])
    df["seq"] = pd.to_numeric(df["sequencia_trecho"].astype(str).str.strip(), errors="coerce").fillna(1).astype(int)
    
    # Tratamento da constraint UNIQUE (id_viagem, sequencia_trecho)
    df = df.drop_duplicates(subset=["id_viagem", "seq"])

    df["dt_origem"] = texto_para_data(df["origem_data"])
    df["dt_destino"] = texto_para_data(df["destino_data"])
    df["diarias"] = texto_para_decimal(df["numero_diarias"]).fillna(0.0).apply(lambda x: max(x, 0.0))

    df_silver = pd.DataFrame({
        "id_viagem": df["id_viagem"],
        "sequencia_trecho": df["seq"],
        "origem_data": df["dt_origem"].dt.strftime("%Y-%m-%d").where(df["dt_origem"].notna(), None),
        "origem_uf": df["origem_uf"],
        "origem_cidade": df["origem_cidade"],
        "destino_data": df["dt_destino"].dt.strftime("%Y-%m-%d").where(df["dt_destino"].notna(), None),
        "destino_uf": df["destino_uf"],
        "destino_cidade": df["destino_cidade"],
        "meio_transporte": df["meio_transporte"],
        "numero_diarias": df["diarias"]
    })

    df_silver = df_silver.astype(object).where(pd.notna(df_silver), None)

    sql_insert = """
        INSERT INTO silver_trecho (
            id_viagem, sequencia_trecho, origem_data, origem_uf, origem_cidade,
            destino_data, destino_uf, destino_cidade, meio_transporte, numero_diarias
        ) VALUES %s
    """
    total = len(df_silver)
    for i in range(0, total, TAMANHO_BLOCO):
        lote = df_silver.iloc[i:i + TAMANHO_BLOCO]
        linhas = list(lote.itertuples(index=False, name=None))
        execute_values(cursor, sql_insert, linhas)

    conexao.commit()
    cursor.close()
    print(f"-> silver_trecho finalizada com {total:,} registros.")
    return total

def conferir_integridade(conexao):
    """Executa a conferência de integridade Raw x Silver conforme a rubrica."""
    print("\n==================================================")
    print("CONFERÊNCIA DE INTEGRIDADE: RAW x SILVER")
    print("==================================================")
    tabelas = [
        ("raw_viagem", "silver_viagem"),
        ("raw_pagamento", "silver_pagamento"),
        ("raw_passagem", "silver_passagem"),
        ("raw_trecho", "silver_trecho")
    ]
    cursor = conexao.cursor()
    for raw, silver in tabelas:
        cursor.execute(f"SELECT COUNT(*) FROM {raw}")
        qtd_raw = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM {silver}")
        qtd_silver = cursor.fetchone()[0]
        status = "OK" if qtd_raw == qtd_silver else "FILTRADO/AJUSTADO"
        print(f"-> Linhas: {raw} ({qtd_raw:,}) x {silver} ({qtd_silver:,}) -> {status}")

    # Checagem de soma financeira de pagamentos
    cursor.execute("SELECT SUM(valor) FROM silver_pagamento")
    soma_silver = cursor.fetchone()[0] or 0.0
    print(f"-> Soma total de pagamentos na Silver: R$ {soma_silver:,.2f}")
    print("==================================================")
    cursor.close()

def main():
    print("==================================================")
    print("FASE 2: TRANSFORMAÇÃO E CARGA NA CAMADA SILVER")
    print("==================================================")
    conexao = conectar()

    try:
        cursor = conexao.cursor()
        print("-> Esvaziando tabelas da camada Silver (Mãe e Filhas)...")
        # Esvazia na ordem: filhas primeiro, depois a mãe (respeita Foreign Keys)
        cursor.execute("TRUNCATE silver_pagamento, silver_passagem, silver_trecho, silver_viagem CASCADE")
        conexao.commit()
        cursor.close()

        # Ordem obrigatória de inserção: Mãe antes das Filhas
        transformar_viagem(conexao)
        transformar_pagamento(conexao)
        transformar_passagem(conexao)
        transformar_trecho(conexao)

        # Conferência final
        conferir_integridade(conexao)

    except Exception as e:
        print(f"\nERRO NA TRANSFORMAÇÃO: {e}")
        conexao.rollback()
    finally:
        conexao.close()

if __name__ == "__main__":
    main()