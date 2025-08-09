# 🚀 Quick Start Guide - New LangGraph Analysis System

Welcome to the new **direct-dialect SQL generation** system! This implementation features:

- **🔄 LangGraph Workflow**: Intelligent analysis pipeline with controlled loops
- **🗃️ Multi-Database Support**: PostgreSQL, MySQL, SQLite, Snowflake, BigQuery, and more
- **🎯 Direct SQL Generation**: Dialect-specific SQL without cross-compilation
- **⚡ Quality-Driven Iteration**: Automatic refinement based on validation gates
- **📊 Rich Artifacts**: Tables, charts, SQL queries, and execution traces

## 🏃‍♂️ Quick Start

### 1. Install Dependencies

```bash
# Install the Python package and dependencies
pip install -e .

# Verify installation
python test_setup.py
```

### 2. Set Environment Variables

```bash
# Required: LLM API key
export OPENAI_API_KEY="your-openai-api-key"

# Optional: Other settings
export DEBUG=true
export LOG_LEVEL=INFO
```

### 3. Start the Service

```bash
# Start the FastAPI server
python main.py

# Server will start at http://localhost:8000
```

### 4. Test the New System

```bash
# Run comprehensive integration tests
python examples/new_system_test.py

# Test TypeScript SDK (requires Node.js)
node examples/typescript_example.js
```

## 🔍 Key Features Demonstrated

### ✅ What's Working

1. **🏗️ Complete Architecture**: FastAPI + LangGraph + Connectors + TypeScript SDK
2. **🔄 Intelligent Workflow**: plan → profile → mvq → diagnose → refine → produce → validate → present
3. **🗃️ Database Agnostic**: Same workflow works across PostgreSQL, MySQL, SQLite, etc.
4. **📊 Quality Gates**: Automatic validation with quality scoring (0.0-1.0)
5. **🎯 Artifact Generation**: Structured output with tables, charts, and SQL
6. **⚡ Background Processing**: Async job execution with status tracking
7. **🔧 Extensible Design**: Easy to add new dialects, connectors, and analysis types

### 🆕 New API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/query` | POST | Run analysis with new QuerySpec format |
| `/v1/jobs/{job_id}` | GET | Check job status |
| `/v1/jobs/{job_id}` | DELETE | Cancel running job |
| `/v1/dialects` | GET | List supported SQL dialects |
| `/v1/connectors` | GET | List available data connectors |
| `/v1/ask` | POST | Legacy endpoint (backward compatible) |

### 📊 Example Usage

#### Python (Direct Workflow)

```python
from analyst_agent.models.contracts import QuerySpec, DataSource, SupportedDialect
from analyst_agent.adapters import make_connector
from analyst_agent.core.graph import run_analysis_async

# Create data source
data_source = DataSource(
    kind="sqlite",
    config={"url": "sqlite:///example.db"},
    business_tz="UTC"
)

# Create query specification
spec = QuerySpec(
    question="What are the top selling products?",
    dialect=SupportedDialect.SQLITE,
    validation_profile="balanced"
)

# Run analysis
connector = make_connector(data_source.kind, **data_source.config)
ctx = {"connector": connector, "dialect": spec.dialect}

result = await run_analysis_async("job123", spec.model_dump(), ctx)
print(f"Answer: {result['answer']}")
print(f"Quality Score: {result['quality']['score']}")
```

#### TypeScript/JavaScript (SDK)

```typescript
import { AnalystClient } from 'analyst-agent-sdk';

const client = new AnalystClient({
  baseUrl: 'http://localhost:8000',
  defaultDialect: 'postgres'
});

const result = await client.quickAnalysis(
  "What are the monthly sales trends?",
  {
    kind: "postgres",
    config: {
      url: "postgresql://user:pass@localhost:5432/db"
    }
  },
  {
    dialect: "postgres",
    validationProfile: "balanced"
  }
);

console.log(`Answer: ${result.answer}`);
console.log(`Quality: ${result.quality.score}`);
```

#### cURL (REST API)

```bash
# Submit analysis query
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "spec": {
      "question": "How many orders were placed last month?",
      "dialect": "sqlite",
      "validation_profile": "fast"
    },
    "data_source": {
      "kind": "sqlite",
      "config": {"url": "sqlite:///orders.db"}
    }
  }'

# Check job status
curl http://localhost:8000/v1/jobs/{job_id}
```

## 🧪 Testing Different Scenarios

The new system includes comprehensive tests for:

### 1. **Simple Queries** (Fast validation)
```python
QuerySpec(
    question="How many customers do we have?",
    dialect=SupportedDialect.SQLITE,
    validation_profile=ValidationProfile.FAST
)
```

### 2. **Complex Analysis** (Balanced validation)
```python
QuerySpec(
    question="What are the total sales by month and top customers?", 
    dialect=SupportedDialect.POSTGRES,
    time_window="last_6_months",
    validation_profile=ValidationProfile.BALANCED
)
```

### 3. **High-Quality Analysis** (Strict validation)
```python
QuerySpec(
    question="Show order distribution and statistical analysis",
    dialect=SupportedDialect.SNOWFLAKE,
    filters={"min_amount": 100},
    validation_profile=ValidationProfile.STRICT
)
```

## 🔧 Configuration

### Environment Variables

```bash
# Core Settings
DEBUG=true
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# LLM Configuration
OPENAI_API_KEY=your-key
DEFAULT_LLM_MODEL=gpt-4
DEFAULT_LLM_PROVIDER=openai

# Analysis Settings
MAX_EXECUTION_TIME=300
ENABLE_CODE_EXECUTION=true

# Security
SECRET_KEY=your-secret-key
```

### Supported Dialects

- **PostgreSQL**: Full-featured with CTEs, window functions, JSON
- **MySQL**: Complete support with proper date/time handling
- **SQLite**: Great for testing and small datasets
- **Snowflake**: Advanced analytics with QUALIFY support
- **BigQuery**: Google Cloud native with backtick identifiers
- **SQL Server**: Enterprise features with TOP clause support
- **DuckDB**: Fast analytics with PostgreSQL compatibility
- **Trino/Presto**: Distributed query engine support
- **ClickHouse**: High-performance analytics database

## 📈 Quality Gates

The system validates results using multiple quality gates:

| Gate | Weight | Description |
|------|--------|-------------|
| **Data Coverage** | 25% | Query returns meaningful data |
| **Reconciliation** | 35% | Cross-validation across data paths |
| **Unique Keys** | 20% | Data integrity checks |
| **Stability** | 10% | Consistent results across time windows |
| **Units/Types** | 10% | Proper data types and units |

**Overall Score**: 0.85+ for high quality, 0.70+ for acceptable quality.

## 🐳 Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# Services include:
# - analyst-agent: Main Python service
# - postgres: PostgreSQL database  
# - redis: Cache and job queue
# - pgadmin: Database management UI
```

## 🔍 Troubleshooting

### Common Issues

1. **ImportError**: Run `pip install -e .` to install dependencies
2. **LLM API Error**: Set `OPENAI_API_KEY` environment variable  
3. **Database Connection**: Check connection strings and credentials
4. **Port Conflicts**: Change `API_PORT` if 8000 is in use

### Debug Mode

```bash
# Enable detailed logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Check service health
curl http://localhost:8000/v1/health

# View real-time logs
tail -f logs/analyst-agent.log
```

## 🚀 Next Steps

1. **Try the Examples**: Run `python examples/new_system_test.py`
2. **Test Your Database**: Update connection configs for your data
3. **Explore Dialects**: Try different SQL dialects for the same question
4. **Custom Connectors**: Add support for new database types
5. **Production Deploy**: Use Docker Compose for full deployment

## 📚 API Documentation

- **Interactive Docs**: http://localhost:8000/docs (when `DEBUG=true`)
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/v1/health

---

🎉 **You now have a powerful, database-agnostic AI analysis system!**

The new architecture provides intelligent SQL generation, quality validation, and extensible connector support across multiple database platforms. 