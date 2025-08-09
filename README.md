# Analyst Agent 🤖📊

**Autonomous AI Data Analyst & SQL Generation Service**

A production-ready system that generates and executes SQL queries directly in target database dialects, with multi-provider LLM support and comprehensive database connectivity.

## 🎯 Features

- **🔄 Direct SQL Generation**: No transpilation - generates SQL directly in target dialects
- **🏢 Multi-Database Support**: PostgreSQL, MySQL, SQLite, Snowflake, BigQuery, SQL Server, DuckDB
- **🤖 Multi-LLM Providers**: OpenAI, Anthropic Claude, Local models with automatic fallback
- **🛡️ Iterative Refinement**: Automatic error detection, diagnostics, and SQL repair
- **⚡ Production Ready**: FastAPI, async workflows, comprehensive error handling
- **🧪 TypeScript SDK**: Full type safety for frontend integration

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/analyst-agent.git
cd analyst-agent

# Install dependencies
pip install -e .

# Or install from PyPI (when published)
pip install analyst-agent
```

### 2. Environment Setup

Create a `.env` file:

```bash
# LLM Provider (choose one or more)
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# LLM Configuration
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Security
SECRET_KEY=your-secret-key-change-in-production
```

### 3. Run the Service

```bash
# Method 1: Direct Python
python main.py

# Method 2: Using the CLI
analyst-agent

# Method 3: Development with auto-reload
uvicorn analyst_agent.api.app:app --reload --host 0.0.0.0 --port 8000

# Method 4: Docker
docker-compose up
```

### 4. Test the Setup

```bash
# Basic setup validation
python test_setup.py

# Multi-provider LLM test
python examples/multi_provider_test.py

# Full system test with real database
python examples/new_system_test.py
```

## 💻 Usage Examples

### API Usage

```bash
# Health check
curl http://localhost:8000/health

# SQL Query Generation
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the top 5 products by sales this month?",
    "dialect": "postgres",
    "time_window": "last_month",
    "filters": {},
    "budget": {"queries": 30, "seconds": 90}
  }'
```

### TypeScript SDK

```bash
cd typescript-sdk
npm install
npm run build

# Test the SDK
node examples/basic_example.js
```

```typescript
import { AnalystClient } from './src/client';

const client = new AnalystClient('http://localhost:8000');

const result = await client.query({
  question: "Show me monthly revenue trends",
  dialect: "postgres",
  dataSource: {
    kind: "postgres",
    config: {
      host: "localhost",
      database: "mydb",
      user: "user",
      password: "pass"
    }
  }
});

console.log(result.answer);
```

### Python SDK

```python
import asyncio
from analyst_agent.core.graph import run_analysis_async
from analyst_agent.models.contracts import QuerySpec, DataSource

async def analyze_data():
    spec = QuerySpec(
        question="What are our best performing products?",
        dialect="postgres"
    )
    
    data_source = DataSource(
        kind="postgres",
        config={
            "host": "localhost",
            "database": "sales_db",
            "user": "analyst",
            "password": "password"
        }
    )
    
    result = await run_analysis_async("job123", spec.model_dump(), {
        "connector": make_connector(data_source.kind, **data_source.config),
        "dialect": spec.dialect
    })
    
    print(result["answer"])

asyncio.run(analyze_data())
```

## 🏗️ Architecture

### Core Components

```
📁 analyst_agent/
├── 🎛️ api/              # FastAPI routes and app
├── 🔌 adapters/         # Database connectors
├── 🧠 core/             # Analysis engine
│   ├── graph.py         # LangGraph workflow
│   ├── nodes.py         # Analysis nodes
│   ├── sql_executor.py  # SQL generation & execution
│   └── llm_factory.py   # Multi-provider LLM support
├── 📋 models/           # Pydantic contracts
└── ⚙️ settings.py       # Configuration
```

### Workflow

```
Question → Plan → Profile → MVQ → Diagnose → Refine → Transform → Validate → Present
           ↑                     ↓         ↑
           └─ Iteration Loop ────┘         │
                                          ↓
                                    Final Answer
```

## 🗄️ Supported Databases

| Database | Connector | Status | Notes |
|----------|-----------|--------|-------|
| PostgreSQL | `asyncpg` | ✅ | Full support with async |
| MySQL | `mysql-connector` | ✅ | Full support |
| SQLite | `sqlite3` | ✅ | Built-in support |
| Snowflake | `snowflake-connector` | ✅ | Cloud data warehouse |
| BigQuery | `google-cloud-bigquery` | ✅ | Google Cloud |
| SQL Server | `pyodbc` | ✅ | Microsoft SQL Server |
| DuckDB | `duckdb` | ✅ | Analytics database |

## 🤖 LLM Providers

| Provider | Models | Setup | Status |
|----------|--------|-------|--------|
| OpenAI | GPT-4, GPT-3.5-turbo, GPT-4o | `OPENAI_API_KEY` | ✅ |
| Anthropic | Claude 3 Opus/Sonnet/Haiku | `ANTHROPIC_API_KEY` | ✅ |
| Local | Llama, Mistral via Ollama | Install Ollama | ✅ |

See [Multi-Provider Guide](MULTI_PROVIDER_GUIDE.md) for detailed setup.

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run specific test suites
python examples/new_system_test.py      # Core system
python examples/multi_provider_test.py  # LLM providers
python examples/typescript_example.js   # TypeScript SDK

# Manual testing
python test_setup.py                    # Basic setup
```

## 📚 Documentation

- [Multi-Provider LLM Guide](MULTI_PROVIDER_GUIDE.md) - LLM setup and configuration
- [Quick Start Guide](QUICK_START_NEW_SYSTEM.md) - Detailed setup instructions
- [TypeScript SDK](typescript-sdk/README.md) - Frontend integration
- [Examples](examples/) - Working code examples

## 🐳 Docker Deployment

```bash
# Development
docker-compose up

# Production
docker-compose -f docker-compose.prod.yml up

# With custom environment
OPENAI_API_KEY=sk-... docker-compose up
```

## 🔧 Configuration

Key environment variables:

```bash
# LLM Settings
DEFAULT_LLM_PROVIDER=openai|anthropic|local
DEFAULT_LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Database Settings
DATABASE_URL=postgresql://user:pass@host:port/db

# Security
SECRET_KEY=your-secret-key
```

## 🚀 Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run with auto-reload
uvicorn analyst_agent.api.app:app --reload

# Code formatting
black analyst_agent/
ruff analyst_agent/

# Type checking
mypy analyst_agent/
```

## 📈 Production Considerations

- **Security**: Set strong `SECRET_KEY`, use HTTPS, implement authentication
- **Scaling**: Use Redis for caching, PostgreSQL for persistence
- **Monitoring**: Structured logging with `structlog`, error tracking
- **LLM Costs**: Monitor usage, implement rate limiting, use cost-effective models
- **Database**: Connection pooling, read replicas, query optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangChain/LangGraph** for the agentic workflow framework
- **FastAPI** for the robust API framework
- **SQLAlchemy** for database abstraction
- **PyArrow** for efficient data processing 