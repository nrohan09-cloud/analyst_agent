# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Python Development

**Always activate virtual environment first:**
```bash
source .venv/bin/activate
```

**Development Commands (run after activating .venv):**
```bash
# Install in development mode
source .venv/bin/activate && pip install -e ".[dev]"

# Run the service
source .venv/bin/activate && python main.py

# Development with auto-reload  
source .venv/bin/activate && uvicorn analyst_agent.api.app:app --reload --host 0.0.0.0 --port 8000

# Alternative CLI entry point
source .venv/bin/activate && analyst-agent
```

### Code Quality
```bash
# Code formatting
source .venv/bin/activate && black analyst_agent/

# Linting
source .venv/bin/activate && ruff analyst_agent/

# Type checking
source .venv/bin/activate && mypy analyst_agent/
```

### Testing
```bash
# Run all tests
source .venv/bin/activate && pytest

# Basic setup validation
source .venv/bin/activate && python test_setup.py

# Multi-provider LLM test
source .venv/bin/activate && python examples/multi_provider_test.py

# Full system test
source .venv/bin/activate && python examples/new_system_test.py
```

### TypeScript SDK Development
```bash
cd typescript-sdk

# Install dependencies
npm install

# Build SDK
npm run build

# Watch mode
npm run build:watch

# Run tests
npm test

# Type checking
npm run type-check

# Test the SDK
node examples/basic_example.js
```

### Frontend Development

**IMPORTANT: Always use the TypeScript SDK for frontend-backend integration**

The project includes a modern TypeScript frontend that demonstrates best practices for integrating with the Analyst Agent API. **Never build frontends that directly call the API endpoints** - always use the provided TypeScript SDK.

```bash
cd frontend

# Install dependencies
npm install

# Development server (with hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run type-check
```

**Key Frontend Features:**
- **TypeScript + Vite** for modern development experience
- **SDK Integration** with `analyst-agent-sdk` package
- **Real-time Progress Logging** with step-by-step execution details
- **Streaming Support** for long-running queries
- **Type-safe Error Handling** with proper error messages
- **Database URL Field** for Supabase and other hosted databases
- **Automatic Field Management** (URL vs individual connection fields)

**Frontend Architecture:**
- `frontend/src/main.ts` - Main TypeScript entry point using the SDK
- `frontend/src/styles/main.css` - Modern CSS with responsive design
- `frontend/index.html` - HTML structure
- `frontend/vite.config.ts` - Vite configuration
- `frontend/tsconfig.json` - TypeScript configuration

## Architecture Overview

### Core Workflow (LangGraph)
The system implements an iterative analysis workflow: **Plan → Profile → MVQ → Diagnose → Refine → Transform → Validate → Present**

Key workflow nodes in `analyst_agent/core/nodes.py`:
- **plan**: Analyzes the question and sets up analysis context
- **profile**: Examines database schema and identifies relevant tables
- **mvq**: Generates and executes the minimum viable query
- **diagnose**: Detects issues with query execution or results
- **refine**: Improves the SQL based on diagnostics
- **transform**: Converts raw results into business insights
- **validate**: Quality checks and iteration decisions
- **present**: Formats the final answer

### Key Components

**LangGraph Engine** (`analyst_agent/core/graph.py`):
- State management with `AnalystState`
- Conditional routing between workflow nodes
- Iterative refinement with budget constraints

**Multi-Provider LLM Support** (`analyst_agent/core/llm_factory.py`):
- OpenAI, Anthropic Claude, Local (Ollama) providers
- Automatic fallback and model mapping
- Provider caching and error handling

**Database Adapters** (`analyst_agent/adapters/`):
- Protocol-based connector interface in `base.py`
- SQLAlchemy connector implementation
- Support for PostgreSQL, MySQL, SQLite, Snowflake, BigQuery, SQL Server, DuckDB

**API Layer** (`analyst_agent/api/`):
- FastAPI with async support
- RESTful endpoints for analysis queries
- Type-safe contracts with Pydantic models

### Environment Setup

Required `.env` file:
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

### SQL Generation Strategy

The system generates SQL **directly in target dialects** without transpilation:
- Dialect-specific capabilities in `analyst_agent/core/dialect_caps.py`
- Schema introspection and query validation
- Iterative refinement based on execution feedback
- Support for complex time-series analysis and business logic

### Data Flow

1. **Question Input** → Natural language query
2. **Planning** → Analyze question requirements  
3. **Schema Profiling** → Identify relevant tables/columns
4. **SQL Generation** → Create dialect-specific query
5. **Execution & Diagnosis** → Run query, detect issues
6. **Iterative Refinement** → Improve SQL based on feedback
7. **Result Processing** → Transform to business insights
8. **Quality Validation** → Check completeness and accuracy
9. **Response Formatting** → Present final answer

### TypeScript SDK Integration

**MANDATORY SDK USAGE FOR ALL FRONTEND INTEGRATIONS**

Located in `typescript-sdk/`, provides:
- Type-safe client for the REST API
- Full TypeScript definitions
- Promise-based async operations
- Built with tsup and distributed as both ESM and CommonJS

The SDK maps directly to the Python API contracts defined in `analyst_agent/models/contracts.py`.

**SDK Integration Examples:**

```typescript
// Always use the SDK - NEVER call API endpoints directly
import { AnalystClient } from 'analyst-agent-sdk'

// Initialize client
const client = new AnalystClient({
  baseUrl: 'http://localhost:8000',
  timeout: 60000,
  retries: 3
})

// Create data sources (Supabase example)
const dataSource = AnalystClient.createPostgresDataSource({
  host: 'your-project.supabase.co',
  database: 'postgres',
  username: 'postgres',
  password: 'your-password'
})

// Or use connection URL directly
const dataSource = AnalystClient.createDataSource('postgres', {
  url: 'postgresql://user:pass@host:port/database'
})

// Query with streaming (recommended for production)
const result = await client.queryWithStreaming(querySpec, dataSource, {
  onStatus: (data) => console.log('Status:', data.status),
  onStep: (data) => console.log('Step:', data.step_name, data.status),
  onProgress: (data) => console.log('Progress:', data.progress + '%')
})

// Simple query (for fast operations)
const result = await client.query(querySpec, dataSource)
```

**Integration Rules:**
1. **NEVER** use `fetch()` or other HTTP clients to call `/v1/query` directly
2. **ALWAYS** use the `AnalystClient` class from the SDK
3. **ALWAYS** use SDK helper methods for data source creation
4. **ALWAYS** use TypeScript for better type safety and developer experience
5. **PREFER** streaming queries for better user experience with progress updates

**Supported Data Source Helpers:**
- `AnalystClient.createPostgresDataSource()` - PostgreSQL/Supabase
- `AnalystClient.createSQLiteDataSource()` - Local SQLite files
- `AnalystClient.createDataSource()` - Generic with connection URL
- `AnalystClient.createCSVDataSource()` - CSV files
