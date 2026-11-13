# 🧊 FDE Cold-Chain Supply Chain Dispatch Project

**Fleet Dispatch Enterprise (FDE)** cold-chain monitoring platform — an AI-powered "chat with your data" system for logistics stakeholders to investigate cold-chain anomalies, route disruptions, and compliance thresholds across an active fleet.

The project combines a **LangGraph reasoning agent**, a **Streamlit dispatch console**, a **legacy MSSQL telemetry database**, and a **Pinecone vector index** of Standard Operating Procedures (SOPs) into a single decision-support workflow.

---

## ✨ Features

| Capability | Description |
|---|---|
| 🤖 **LangGraph Agent** | Reasoning loop (`orchestrator.py`) that chains tool use: telemetry → corridor conditions → SOP compliance. |
| 🧊 **Streamlit Dispatch Console** | Chat UI to query fleet telemetry, corridor weather, and compliance rules, with full tool-call traces. |
| 🛡️ **Security & Audit Logs** | Admin-authenticated viewer for `FDE_VIEWS.AgentAuditLog` (agent execution traces stored in MSSQL). |
| 🗄️ **Semantic SQL Layer** | Read-only view (`FDE_VIEWS.VW_ACTIVE_FLEET`) over a messy legacy schema, protecting raw tables from LLM access. |
| 🌐 **Live Corridor API** | Real-time weather and corridor conditions via Open-Meteo for any GPS coordinate. |
| 📚 **Pinecone SOP Index** | Incremental ingestion of compliance documents (`.md`, `.txt`, `.pdf`, `.csv`, `.xlsx`) into Pinecone with hash-based change detection. |
| 🔄 **Legacy Data Ingestion** | Pipeline to load raw CSV telemetry into the enterprise MSSQL schema. |

---

## 🏗️ Architecture

```
cold_chain_FDE_project/
├── main.py                        # Package entry point
├── pyproject.toml                 # Project metadata & dependencies (uv)
├── requirements.txt               # Pip-compatible dependency list
├── docker-compose.yml             # MSSQL Server 2022 container
├── .env                           # API keys, database credentials, model settings
├── .gitignore
├── README.md
├── uv.lock
├── data/
│   ├── raw/                       # Raw source datasets (e.g. dynamic_supply_chain_logistics_dataset.csv)
│   └── source/                    # Source metadata (e.g. data.txt)
├── cache/                         # Ingestion hash cache (Pinecone incremental sync)
├── scripts/
│   ├── ingest_legacy_data.py      # Load CSV into legacy MSSQL table
│   ├── ingest_sop_pinecone.py     # Ingest policy docs into Pinecone vector index
│   └── setup_security_view.sql    # MSSQL schema, view, and read-only agent login
└── src/
    ├── orchestrator.py            # LangGraph agent graph + CLI chat loop
    ├── ui.py                      # Streamlit dispatch console & audit viewer
    ├── agent_tools.py             # Three agent tools (telemetry, corridor, SOP)
    └── prompts/system_prompt.txt  # System instructions & response format
```

### Data Flow

1. **Operator** asks a question in the Streamlit Dispatch Console (e.g., *"Any temperature breaches on route to Rotterdam?"*).
2. **LangGraph agent** (`orchestrator.py`) receives the query and decides which tool to call:
   - `query_telemetry_db` → reads `FDE_VIEWS.VW_ACTIVE_FLEET` in MSSQL
   - `fetch_corridor_conditions` → calls Open-Meteo weather API for GPS coordinates
   - `search_compliance_sop` → semantic search over the Pinecone SOP index
3. **Agent** formats findings into an executive summary, telemetry table, and action plan (per `system_prompt.txt`).
4. **Audit trail** of every session, node, tool, and payload is silently written to `FDE_VIEWS.AgentAuditLog` for admin review.

---

## 📋 Tech Stack

- **Python 3.13** (managed with `uv`)
- **LangGraph** + **LangChain** agent orchestration
- **NVIDIA NIM** (`ChatNVIDIA`) LLM backend
- **Streamlit** web UI
- **Microsoft SQL Server 2022** (via Docker)
- **Pinecone** vector database (SOPs)
- **Open-Meteo** live weather API
- **Pandas / SQLAlchemy / pyodbc** data access

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd cold_chain_FDE_project
```

### 2. Set up the Python environment

This project uses `uv` (Python 3.13+):

```bash
uv sync
```

Or with pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env` and adjust the values for your environment:

```ini
# Vector DB
PINECONE_API_KEY=your-pinecone-key
NVIDIA_API_KEY=your-nvidia-api-key

# Embedding Model
EMBEDDING_MODEL=LOCAL
LOCAL_EMBEDDING_MODEL_PATH=BAAI/bge-m3

# SQL DB admin credentials
SQL_ADMIN_USER=sa
SQL_ADMIN_PASSWORD=your-strong-password

# SQL DB Agent Credentials
SQL_AGENT_USER=USR_FDE_RO
SQL_AGENT_PASSWORD=your-agent-password

# SQL Database configuration
SQL_SERVER_HOST=localhost
SQL_SERVER_PORT=1433
```

### 4. Start the database (Docker)

```bash
docker-compose up -d
```

This launches **MSSQL Server 2022** on `localhost:1433`.

### 5. Initialize the database security layer

Run the security setup script against your MSSQL instance to create the `FDE_VIEWS` schema, the `VW_ACTIVE_FLEET` semantic view, and the read-only agent login:

```bash
# Example using sqlcmd (adjust auth as needed)
sqlcmd -S localhost,1433 -U sa -P '<admin-password>' -i scripts/setup_security_view.sql
```

### 6. Ingest legacy fleet telemetry

Load the sample dataset into the legacy MSSQL table:

```bash
python scripts/ingest_legacy_data.py
```

This reads `data/raw/dynamic_supply_chain_logistics_dataset.csv`, maps it to the legacy schema, and writes it to `dbo.TBL_SC_FLEET_HIST_RAW`.

### 7. Ingest SOPs into Pinecone

Place compliance documents in `data/policy/` (or update the target directory in `scripts/ingest_sop_pinecone.py`), then run:

```bash
python scripts/ingest_sop_pinecone.py
```

This creates/updates the Pinecone index (`fde-sop-index-local` or `fde-sop-index-openai`) and maintains a hash cache in `cache/ingestion_hash_cache.json` for incremental syncs.

---

## ▶️ Running the Application

### Option A — LangGraph Agent (CLI)

Run the orchestrator directly for a terminal-based chat loop:

```bash
python -m src.orchestrator
```

Type your question at the `Dispatcher >` prompt. Type `exit` or `quit` to leave.

### Option B — Streamlit Dispatch Console (Web UI)

Launch the full web interface:

```bash
streamlit run src/ui.py
```

The console opens two modes:

- **🧊 Dispatch Console** — chat with the FDE agent; view tool-call inputs/outputs in real time.
- **🛡️ Security & Audit Logs** — authenticate with admin credentials to inspect `FDE_VIEWS.AgentAuditLog`.

---

## 🔐 Security Model

- The AI agent connects to MSSQL using a **read-only login** (`USR_FDE_RO`) granted `SELECT` **only** on `FDE_VIEWS.VW_ACTIVE_FLEET`.
- Direct access to `dbo.TBL_SC_FLEET_HIST_RAW` and all DDL/DML operations are explicitly denied to the agent.
- The `query_telemetry_db` tool rejects any statement that does not begin with `SELECT`.
- Audit logs capture every agent session, node execution, tool name, and payload for accountability.

---

