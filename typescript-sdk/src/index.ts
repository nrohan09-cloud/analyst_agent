/**
 * Analyst Agent TypeScript SDK
 * 
 * A simple, type-safe client for the Analyst Agent AI data analysis service.
 * 
 * @example
 * ```typescript
 * import { AnalystClient } from '@analyst-agent/typescript-sdk';
 * 
 * const client = new AnalystClient({
 *   baseUrl: 'http://localhost:8000',
 *   apiKey: 'your-api-key'
 * });
 * 
 * const result = await client.quickAnalysis(
 *   'What are the sales trends?',
 *   { type: 'csv', file_path: './sales.csv' }
 * );
 * 
 * console.log(AnalystClient.getInsightsSummary(result));
 * ```
 */

// Export the main client class
export { AnalystClient, AnalystApiError } from './client';
export type { SupabaseDataSourceOptions } from './client';

// Export all types
export type {
  ValidationProfile,
  SupportedDialect,
  QuerySpec,
  DataSource,
  SupabaseRLSAuth,
  RunResult
} from './types';
