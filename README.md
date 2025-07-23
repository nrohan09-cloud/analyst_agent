# Analyst Agent

Autonomous AI data analyst/scientist service that provides AI-powered data analysis capabilities through natural language queries.

## Features

- 🤖 **Natural Language Queries**: Ask questions about your data in plain English
- 📊 **Multiple Data Sources**: Support for PostgreSQL, MySQL, SQLite, CSV, Parquet, and JSON
- 🔍 **Comprehensive Analysis**: Descriptive, inferential, predictive, exploratory, and diagnostic analytics
- 📈 **Visualizations**: Automatic chart generation with multiple chart types
- 🛡️ **Secure Code Execution**: Safe execution of LLM-generated Python code
- 🔌 **Extensible Architecture**: Easy to add new data sources and analysis types
- 🚀 **Async API**: High-performance FastAPI backend with background job processing
- 🐳 **Docker Ready**: Containerized deployment with Docker Compose

## Quick Start

### Prerequisites

- Python 3.10 or higher
- PostgreSQL (optional, for database features)
- OpenAI API key (for LLM capabilities)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/analyst-agent.git
   cd analyst-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -e .
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the service**
   ```bash
   python main.py
   ```

   Or with uvicorn directly:
   ```bash
   uvicorn analyst_agent.api.app:app --reload
   ```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## API Usage

### Submit an Analysis Request

```bash
curl -X POST "http://localhost:8000/v1/ask" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What are the key trends in sales data over the last quarter?",
       "data_source": {
         "type": "postgres",
         "connection_string": "postgresql://user:pass@localhost:5432/mydb"
       },
       "preferences": {
         "analysis_types": ["descriptive", "predictive"],
         "chart_types": ["line", "bar"]
       }
     }'
```

Response:
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "pending",
  "message": "Analysis request received and queued for processing"
}
```

### Check Job Status

```bash
curl "http://localhost:8000/v1/jobs/abc123-def456-ghi789"
```

Response:
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "completed",
  "progress": 1.0,
  "current_step": "Completed",
  "result": {
    "summary": "Analysis revealed declining sales in Q3 with recovery in Q4...",
    "insights": [
      {
        "title": "Seasonal Sales Pattern",
        "description": "Sales show a clear seasonal pattern with peaks in Q4",
        "confidence": 0.92,
        "type": "descriptive"
      }
    ],
    "charts": [...],
    "tables": [...],
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:35:00Z"
  }
}
```

## Development

### Development Setup

1. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

3. **Run tests**
   ```bash
   pytest
   ```

4. **Format code**
   ```bash
   black analyst_agent/
   ruff check analyst_agent/
   ```

5. **Type checking**
   ```bash
   mypy analyst_agent/
   ```

### Project Structure

```
analyst_agent/
├── analyst_agent/
│   ├── __init__.py
│   ├── settings.py          # Configuration management
│   ├── schemas.py           # Pydantic models
│   ├── api/                 # FastAPI routes and middleware
│   │   ├── app.py          # Main FastAPI application
│   │   └── routes/         # API route handlers
│   ├── agents/             # LangGraph/LangChain agents
│   ├── data_sources/       # Data source connectors
│   ├── analysis/           # Analysis and ML utilities
│   └── sandbox/            # Safe code execution
├── tests/                  # Test suite
├── main.py                 # Application entry point
├── pyproject.toml         # Project configuration
└── README.md
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

### Key Settings

- `OPENAI_API_KEY`: Your OpenAI API key for LLM capabilities
- `DATABASE_URL`: Default database connection string
- `DEBUG`: Enable debug mode and API documentation
- `MAX_EXECUTION_TIME`: Maximum time for analysis execution (seconds)
- `ENABLE_CODE_EXECUTION`: Enable/disable code execution features

## Docker Deployment

### Using Docker Compose

```bash
# Start the full stack (app + database)
docker-compose up -d

# View logs
docker-compose logs -f analyst-agent

# Stop services
docker-compose down
```

### Build and Run Manually

```bash
# Build the image
docker build -t analyst-agent .

# Run the container
docker run -p 8000:8000 \
           -e OPENAI_API_KEY=your-key \
           -e DEBUG=false \
           analyst-agent
```

## Extending the System

### Adding a New Data Source

1. Create a new connector in `analyst_agent/data_sources/`
2. Implement the `BaseConnector` interface
3. Register the connector in the data source factory
4. Update schemas to include the new data source type

### Adding a New LLM Provider

1. Create a provider class in `analyst_agent/agents/providers/`
2. Implement the LangChain ChatLLM interface
3. Update settings and configuration
4. Register in the provider factory

### Adding New Analysis Types

1. Implement analysis functions in `analyst_agent/analysis/`
2. Create LangChain tools for the new analysis types
3. Update the agent workflow to include new capabilities
4. Add corresponding schemas and API documentation

## Security Considerations

- **API Keys**: Store LLM API keys securely using environment variables
- **Code Execution**: Code execution is sandboxed with time and memory limits
- **Database Access**: Use connection pooling and prepared statements
- **CORS**: Configure allowed origins for production deployments
- **Rate Limiting**: Implement rate limiting for production use

## Performance Tuning

- **Database**: Use connection pooling and async database drivers
- **Caching**: Implement caching for frequently accessed data and analysis results
- **Background Jobs**: Use proper task queues (Celery/Redis) for production
- **Resource Limits**: Configure appropriate memory and CPU limits

## Monitoring and Observability

- **Health Checks**: `/v1/health` and `/v1/ready` endpoints
- **Structured Logging**: JSON structured logs with correlation IDs
- **Metrics**: Integration ready for Prometheus/Grafana
- **Tracing**: OpenTelemetry support for distributed tracing

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: your.email@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/analyst-agent/issues)
- 📚 Documentation: [GitHub Wiki](https://github.com/yourusername/analyst-agent/wiki) 