/**
 * TypeScript types for the Analyst Agent API.
 * These types match the Pydantic schemas from the Python service.
 */

export type DataSourceType = 
  | 'postgres' 
  | 'mysql' 
  | 'sqlite' 
  | 'csv' 
  | 'parquet' 
  | 'json';

export type AnalysisType = 
  | 'descriptive' 
  | 'inferential' 
  | 'predictive' 
  | 'exploratory' 
  | 'diagnostic';

export type ChartType = 
  | 'bar' 
  | 'line' 
  | 'scatter' 
  | 'histogram' 
  | 'box' 
  | 'heatmap' 
  | 'pie';

export type JobStatus = 
  | 'pending' 
  | 'running' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

export interface DataSourceConfig {
  type: DataSourceType;
  connection_string?: string;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  file_path?: string;
  table_name?: string;
  [key: string]: any; // Allow additional fields for extensibility
}

export interface AnalysisPreferences {
  analysis_types?: AnalysisType[];
  max_execution_time?: number;
  chart_types?: ChartType[];
  include_code?: boolean;
  confidence_threshold?: number;
}

export interface AnalysisRequest {
  question: string;
  data_source: DataSourceConfig;
  preferences?: AnalysisPreferences;
  context?: Record<string, any>;
}

export interface Chart {
  title: string;
  type: ChartType;
  data: Record<string, any>;
  config?: Record<string, any>;
  base64_image?: string;
  html?: string;
}

export interface Insight {
  title: string;
  description: string;
  confidence: number;
  type: AnalysisType;
  supporting_data?: Record<string, any>;
  recommendations?: string[];
}

export interface ExecutionStep {
  step_name: string;
  description: string;
  status: JobStatus;
  start_time?: string;
  end_time?: string;
  duration_seconds?: number;
  output?: any;
  error?: string;
}

export interface AnalysisResult {
  job_id: string;
  status: JobStatus;
  question: string;
  summary: string;
  insights: Insight[];
  charts: Chart[];
  tables: Record<string, any>[];
  generated_code?: string;
  execution_steps: ExecutionStep[];
  metadata: Record<string, any>;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface AnalysisResponse {
  job_id: string;
  status: JobStatus;
  result?: AnalysisResult;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress?: number;
  current_step?: string;
  estimated_completion?: string;
  result?: AnalysisResult;
}

export interface HealthCheck {
  status: string;
  timestamp: string;
  version: string;
  uptime_seconds: number;
  dependencies: Record<string, string>;
}

export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

export interface ClientConfig {
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

export interface PollOptions {
  interval?: number;
  timeout?: number;
  onProgress?: (response: JobStatusResponse) => void;
} 