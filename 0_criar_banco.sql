-- ============================================================================
-- PROJETO AVALIATIVO: PIPELINE ETL - VIAGENS A SERVIÇO
-- FASE 0: MODELAGEM RELACIONAL E CRIAÇÃO DAS TABELAS (RAW E SILVER)
-- ============================================================================

-- ============================================================================
-- PARTE 1: Criação do Banco de Dados
-- (Executar conectado ao banco padrão 'postgres' se a base ainda não existir)
-- CREATE DATABASE transparencia;
-- ============================================================================

-- ============================================================================
-- PARTE 2: Conectado ao banco 'transparencia'
-- Exclui tabelas anteriores para permitir reexecução limpa (idempotência)
-- ============================================================================
DROP TABLE IF EXISTS silver_pagamento CASCADE;
DROP TABLE IF EXISTS silver_passagem CASCADE;
DROP TABLE IF EXISTS silver_trecho CASCADE;
DROP TABLE IF EXISTS silver_viagem CASCADE;

DROP TABLE IF EXISTS raw_pagamento CASCADE;
DROP TABLE IF EXISTS raw_passagem CASCADE;
DROP TABLE IF EXISTS raw_trecho CASCADE;
DROP TABLE IF EXISTS raw_viagem CASCADE;

-- ============================================================================
-- CAMADA RAW (Cópia fiel dos CSVs: todas as colunas VARCHAR, sem constraints)
-- ============================================================================

-- 1. Raw Viagem (22 colunas originais do CSV 2025_Viagem.csv)
CREATE TABLE raw_viagem (
    identificador_processo_viagem VARCHAR(50),
    numero_proposta_rede VARCHAR(50),
    situacao VARCHAR(100),
    viagem_urgente VARCHAR(20),
    justificativa_urgencia_viagem TEXT,
    codigo_orgao_superior VARCHAR(50),
    nome_orgao_superior VARCHAR(255),
    codigo_orgao_solicitante VARCHAR(50),
    nome_orgao_solicitante VARCHAR(255),
    cpf_viajante VARCHAR(50),
    nome_viajante VARCHAR(255),
    cargo VARCHAR(255),
    funcao VARCHAR(255),
    descricao_funcao VARCHAR(255),
    periodo_data_inicio VARCHAR(50),
    periodo_data_fim VARCHAR(50),
    destinos VARCHAR(4000),
    motivo VARCHAR(4000),
    valor_diarias VARCHAR(50),
    valor_passagens VARCHAR(50),
    valor_devolucao VARCHAR(50),
    valor_outros_gastos VARCHAR(50)
);

-- 2. Raw Pagamento (10 colunas originais do CSV 2025_Pagamento.csv)
CREATE TABLE raw_pagamento (
    identificador_processo_viagem VARCHAR(50),
    numero_proposta_rede VARCHAR(50),
    codigo_orgao_superior VARCHAR(50),
    nome_orgao_superior VARCHAR(255),
    codigo_orgao_pagador VARCHAR(50),
    nome_orgao_pagador VARCHAR(255),
    codigo_unidade_gestora_pagadora VARCHAR(50),
    nome_unidade_gestora_pagadora VARCHAR(255),
    tipo_pagamento VARCHAR(100),
    valor VARCHAR(50)
);

-- 3. Raw Passagem (19 colunas originais do CSV 2025_Passagem.csv)
CREATE TABLE raw_passagem (
    identificador_processo_viagem VARCHAR(50),
    numero_proposta_rede VARCHAR(50),
    meio_transporte VARCHAR(100),
    pais_origem_ida VARCHAR(100),
    uf_origem_ida VARCHAR(50),
    cidade_origem_ida VARCHAR(100),
    pais_destino_ida VARCHAR(100),
    uf_destino_ida VARCHAR(50),
    cidade_destino_ida VARCHAR(100),
    pais_origem_volta VARCHAR(100),
    uf_origem_volta VARCHAR(50),
    cidade_origem_volta VARCHAR(100),
    pais_destino_volta VARCHAR(100),
    uf_destino_volta VARCHAR(50),
    cidade_destino_volta VARCHAR(100),
    valor_passagem VARCHAR(50),
    taxa_servico VARCHAR(50),
    data_emissao_bilhete VARCHAR(50),
    hora_emissao_bilhete VARCHAR(50)
);

-- 4. Raw Trecho (14 colunas originais do CSV 2025_Trecho.csv)
CREATE TABLE raw_trecho (
    identificador_processo_viagem VARCHAR(50),
    numero_proposta_rede VARCHAR(50),
    sequencia_trecho VARCHAR(50),
    origem_data VARCHAR(50),
    origem_pais VARCHAR(100),
    origem_uf VARCHAR(50),
    origem_cidade VARCHAR(100),
    destino_data VARCHAR(50),
    destino_pais VARCHAR(100),
    destino_uf VARCHAR(50),
    destino_cidade VARCHAR(100),
    meio_transporte VARCHAR(100),
    numero_diarias VARCHAR(50),
    missao VARCHAR(255)
);

-- ============================================================================
-- CAMADA SILVER (Tipada, PKs, FKs e as 8 CONSTRAINTS obrigatórias)
-- ============================================================================

-- 1. Silver Viagem (Tabela Mãe)
-- Constraint 1: NOT NULL em nome_orgao_superior
-- Constraint 2: CHECK em valor_diarias >= 0
CREATE TABLE silver_viagem (
    id_viagem VARCHAR(20) NOT NULL,
    num_proposta VARCHAR(20),
    situacao VARCHAR(50),
    viagem_urgente VARCHAR(5),
    cod_orgao_superior VARCHAR(20),
    nome_orgao_superior VARCHAR(255) NOT NULL,
    nome_viajante VARCHAR(255),
    cargo VARCHAR(255),
    data_inicio DATE,
    data_fim DATE,
    destinos VARCHAR(4000),
    motivo VARCHAR(4000),
    valor_diarias DECIMAL(10,2),
    valor_passagens DECIMAL(10,2),
    valor_devolucao DECIMAL(10,2),
    valor_outros_gastos DECIMAL(10,2),
    valor_total DECIMAL(12,2),
    duracao_dias INT,
    CONSTRAINT pk_silver_viagem PRIMARY KEY (id_viagem),
    CONSTRAINT ck_viagem_valor_diarias CHECK (valor_diarias >= 0)
);

-- 2. Silver Pagamento (Tabela Filha)
-- Constraint 1: CHECK em valor >= 0
-- Constraint 2: NOT NULL em tipo_pagamento
CREATE TABLE silver_pagamento (
    id_pagamento SERIAL,
    id_viagem VARCHAR(20) NOT NULL,
    num_proposta VARCHAR(20),
    nome_orgao_pagador VARCHAR(255),
    nome_ug_pagadora VARCHAR(255),
    tipo_pagamento VARCHAR(50) NOT NULL,
    valor DECIMAL(10,2),
    CONSTRAINT pk_silver_pagamento PRIMARY KEY (id_pagamento),
    CONSTRAINT fk_pagamento_viagem FOREIGN KEY (id_viagem) REFERENCES silver_viagem(id_viagem),
    CONSTRAINT ck_pagamento_valor CHECK (valor >= 0)
);

-- 3. Silver Passagem (Tabela Filha)
-- Constraint 1: CHECK em valor_passagem >= 0
-- Constraint 2: CHECK em taxa_servico >= 0
CREATE TABLE silver_passagem (
    id_passagem SERIAL,
    id_viagem VARCHAR(20) NOT NULL,
    meio_transporte VARCHAR(50),
    pais_origem_ida VARCHAR(60),
    uf_origem_ida VARCHAR(40),
    cidade_origem_ida VARCHAR(80),
    pais_destino_ida VARCHAR(60),
    uf_destino_ida VARCHAR(40),
    cidade_destino_ida VARCHAR(80),
    valor_passagem DECIMAL(10,2),
    taxa_servico DECIMAL(10,2),
    data_emissao DATE,
    CONSTRAINT pk_silver_passagem PRIMARY KEY (id_passagem),
    CONSTRAINT fk_passagem_viagem FOREIGN KEY (id_viagem) REFERENCES silver_viagem(id_viagem),
    CONSTRAINT ck_passagem_valor CHECK (valor_passagem >= 0),
    CONSTRAINT ck_passagem_taxa CHECK (taxa_servico >= 0)
);

-- 4. Silver Trecho (Tabela Filha)
-- Constraint 1: CHECK em numero_diarias >= 0
-- Constraint 2: UNIQUE em (id_viagem, sequencia_trecho)
CREATE TABLE silver_trecho (
    id_trecho SERIAL,
    id_viagem VARCHAR(20) NOT NULL,
    sequencia_trecho INT,
    origem_data DATE,
    origem_uf VARCHAR(40),
    origem_cidade VARCHAR(80),
    destino_data DATE,
    destino_uf VARCHAR(40),
    destino_cidade VARCHAR(80),
    meio_transporte VARCHAR(50),
    numero_diarias DECIMAL(10,2),
    CONSTRAINT pk_silver_trecho PRIMARY KEY (id_trecho),
    CONSTRAINT fk_trecho_viagem FOREIGN KEY (id_viagem) REFERENCES silver_viagem(id_viagem),
    CONSTRAINT ck_trecho_diarias CHECK (numero_diarias >= 0),
    CONSTRAINT uq_trecho_viagem_sequencia UNIQUE (id_viagem, sequencia_trecho)
);