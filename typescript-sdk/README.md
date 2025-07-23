# Analyst Agent TypeScript SDK

TypeScript/JavaScript client for the Analyst Agent AI data analysis service.

## Installation

```bash
npm install @analyst-agent/typescript-sdk
```

## Quick Start

```typescript
import { AnalystClient } from '@analyst-agent/typescript-sdk';

const client = new AnalystClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key' // Optional
});

// Submit a question for analysis
const response = await client.ask({
  question: 'What are the sales trends over the last quarter?',
  data_source: {
    type: 'postgres',
    connection_string: 'postgresql://user:pass@localhost:5432/sales_db'
  },
  preferences: {
    analysis_types: ['descriptive', 'predictive'],
    chart_types: ['line', 'bar']
  }
});

console.log('Job ID:', response.job_id);

// Check job status
const status = await client.getJobStatus(response.job_id);
console.log('Status:', status.status);

// Wait for completion and get results
const result = await client.waitForCompletion(response.job_id);
console.log('Analysis completed:', result.summary);
```

## Convenience Methods

### Quick Analysis

For simple use cases, use the `quickAnalysis` method:

```typescript
const result = await client.quickAnalysis(
  'What are the top selling products?',
  { type: 'csv', file_path: './sales.csv' }
);

console.log(AnalystClient.getInsightsSummary(result));
```

### Ask and Wait

Submit a question and automatically wait for completion:

```typescript
const result = await client.askAndWait({
  question: 'Analyze customer churn patterns',
  data_source: { type: 'postgres', connection_string: 'postgresql://...' }
}, {
  onProgress: (status) => console.log(`Progress: ${status.progress}`)
});
```

## Data Source Types

The SDK supports multiple data source types:

### PostgreSQL
```typescript
{
  type: 'postgres',
  connection_string: 'postgresql://user:pass@host:port/db'
}
```

### CSV Files
```typescript
{
  type: 'csv',
  file_path: './data.csv'
}
```

### MySQL
```typescript
{
  type: 'mysql',
  connection_string: 'mysql://user:pass@host:port/db'
}
```

### SQLite
```typescript
{
  type: 'sqlite',
  file_path: './database.db'
}
```

## Error Handling

```typescript
import { AnalystAgentError } from '@analyst-agent/typescript-sdk';

try {
  const result = await client.ask(request);
} catch (error) {
  if (error instanceof AnalystAgentError) {
    console.error('API Error:', error.message);
    console.error('Status:', error.status);
    console.error('Details:', error.details);
  } else {
    console.error('Unexpected error:', error);
  }
}
```

## Configuration Options

```typescript
const client = new AnalystClient({
  baseUrl: 'http://localhost:8000',  // Required: API base URL
  apiKey: 'your-api-key',            // Optional: API key for authentication
  timeout: 30000,                    // Optional: Request timeout in ms
  retries: 3,                        // Optional: Number of retries
  retryDelay: 1000                   // Optional: Delay between retries in ms
});
```

## Analysis Preferences

Customize analysis behavior:

```typescript
{
  analysis_types: ['descriptive', 'inferential', 'predictive'],
  chart_types: ['bar', 'line', 'scatter', 'histogram'],
  include_code: true,           // Include generated Python code
  confidence_threshold: 0.8,    // Minimum confidence for insights
  max_execution_time: 300       // Max execution time in seconds
}
```

## Helper Methods

### Extract Insights Summary
```typescript
const summary = AnalystClient.getInsightsSummary(result);
console.log(summary);
```

### Extract Chart Data
```typescript
const chartData = AnalystClient.extractChartData(result);
chartData.forEach(chart => {
  console.log(`Chart: ${chart.title} (${chart.type})`);
  console.log('Data:', chart.data);
});
```

## TypeScript Support

The SDK is written in TypeScript and includes full type definitions:

```typescript
import type { 
  AnalysisRequest, 
  AnalysisResult, 
  DataSourceConfig 
} from '@analyst-agent/typescript-sdk';

const request: AnalysisRequest = {
  question: 'Analyze sales data',
  data_source: {
    type: 'postgres',
    connection_string: 'postgresql://...'
  }
};
```

## Browser Support

The SDK works in both Node.js and modern browsers. For browser usage, ensure your bundler handles the dependencies correctly.

## Examples

See the `/examples` directory for complete usage examples:

- `examples/node-example.js` - Node.js usage
- `examples/react-example.tsx` - React integration
- `examples/csv-analysis.js` - CSV file analysis

## Contributing

1. Clone the repository
2. Install dependencies: `npm install`
3. Build: `npm run build`
4. Test: `npm run test`
5. Lint: `npm run lint`

## License

MIT License - see LICENSE file for details. 