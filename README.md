# Pipeline ETL — Gastos com Viagens a Serviço (Governo Federal)

Projeto prático desenvolvido para consolidar, tratar e analisar os microdados públicos de viagens a serviço do Governo Federal (janeiro a junho de 2025), transformando dados brutos em inteligência acionável por meio da **Arquitetura Medallion** (Raw, Silver e Gold).

---

## 1. Contextualização e Problema de Negócio

Os dados de viagens a serviço disponibilizados pelo Portal da Transparência totalizam mais de 1,8 milhão de registros brutos distribuídos em 4 arquivos CSV. Esses dados apresentam formatos complexos:
- Separador por ponto e vírgula (`;`);
- Codificação `latin-1`;
- Valores monetários com vírgula como separador decimal;
- Datas em formato textual `DD/MM/AAAA`;
- Espaços em branco ocultos nos nomes de colunas e registros nulos implícitos.

O objetivo deste projeto foi estruturar um pipeline de engenharia de dados ponta a ponta com Python e PostgreSQL, garantindo rastreabilidade, integridade referencial, idempotência e visualização analítica para responder a 7 perguntas de negócio essenciais.

---

## 2. Arquitetura da Solução (Medallion)

O pipeline foi estruturado em três camadas de qualidade progressiva:

```text
[ Portal da Transparência / Google Drive (.zip) ]
                       │
                       ▼
┌────────────────────────────────────────────────────────┐
│ CAMADA RAW (Bronze) — Cópia Fiel                       │
│ • Tabelas: raw_viagem, raw_pagamento,                  │
│            raw_passagem, raw_trecho                    │
│ • Todas as colunas armazenadas como VARCHAR            │
│ • Preservação histórica sem filtros ou transformações  │
│ • Carga idempotente via TRUNCATE e execute_values      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ CAMADA SILVER (Prata) — Limpeza e Modelagem            │
│ • Tabelas: silver_viagem, silver_pagamento,            │
│            silver_passagem, silver_trecho              │
│ • Tipagem forte (DATE, DECIMAL(10,2), INT)             │
│ • Integridade referencial (PKs e FKs 1:N)              │
│ • 8 Constraints declaradas (NOT NULL, CHECK, UNIQUE)   │
│ • Métricas calculadas: valor_total e duracao_dias      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ CAMADA GOLD (Ouro) — Agregação e Dataviz               │
│ • Tabelas Físicas e Views: gold_pagamento_resumo e     │
│                            gold_trecho_resumo          │
│ • Consultas analíticas respondendo a 7 perguntas       │
│ • Gráficos padronizados com Matplotlib e Seaborn       │
└────────────────────────────────────────────────────────┘