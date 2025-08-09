/**
 * TypeScript types for the Analyst Agent API.
 * 
 * These types match the Pydantic models from the Python API and provide
 * full type safety for the TypeScript SDK.
 */

export type SupportedDialect = 
  | "postgres"
  | "mysql" 
  | "mssql"
  | "sqlite"
  | "snowflake"
  | "bigquery"
  | "duckdb"
  | "trino"
  | "clickhouse";

export type ValidationProfile = 
  | "fast"           // Basic checks only
  | "balanced"       // Standard validation suite  
  | "strict";        // Full validation with stability checks

export interface DataSource {
  kind: string;                    // Database type (postgres, mysql, snowflake, etc.)
  config: Record<string, any>;     // Connection configuration (DSN, credentials, etc.)
  business_tz?: string;            // Business timezone for date operations
}

export interface QuerySpec {
  question: string;                // Natural language question
  dialect: SupportedDialect;       // Target SQL dialect for query generation
  time_window?: string;            // Time window filter (e.g., 'last_6_months')
  grain?: string;                  // Time granularity (month, day, hour)
  filters?: Record<string, any>;   // Additional filters
  budget?: {                       // Resource limits for execution
    queries?: number;
    seconds?: number;
  };
  validation_profile?: ValidationProfile; // Validation strictness level
}

export type ArtifactType = "table" | "chart" | "log" | "sql";

export interface Artifact {
  id: string;                      // Unique artifact identifier
  kind: ArtifactType;              // Type of artifact
  title: string;                   // Human-readable title
  meta?: Record<string, any>;      // Artifact metadata
  content?: Record<string, any>;   // Artifact content/data
  file_path?: string;              // Path to artifact file if stored separately
}

export interface QualityGate {
  name: string;                    // Gate name
  passed: boolean;                 // Whether gate passed
  score: number;                   // Gate score (0.0-1.0)
  message?: string;                // Gate result message
}

export interface QualityReport {
  passed: boolean;                 // Overall quality check passed
  score: number;                   // Overall quality score (0.0-1.0)
  gates: QualityGate[];            // Individual gate results
  notes?: string[];                // Quality assessment notes
  reconciliation?: Record<string, number>; // Reconciliation deltas across validation paths
  plateau?: boolean;               // Whether improvement has plateaued
}

export interface ExecutionStep {
  step_name: string;               // Name of the execution step
  status: string;                  // Step execution status
  start_time?: string;             // Step start timestamp (ISO string)
  end_time?: string;               // Step completion timestamp (ISO string)
  duration_ms?: number;            // Step duration in milliseconds
  sql?: string;                    // SQL executed in this step
  row_count?: number;              // Number of rows processed
  error?: string;                  // Error message if step failed
  metadata?: Record<string, any>;  // Step-specific metadata
}

export interface RunResult {
  job_id: string;                  // Unique job identifier
  answer: string;                  // Natural language answer to the question
  tables: Artifact[];              // Table artifacts
  charts: Artifact[];              // Chart artifacts
  quality: QualityReport;          // Quality assessment
  lineage: Record<string, any>;    // Data lineage and execution metadata
  execution_steps: ExecutionStep[]; // Detailed execution trace
  created_at: string;              // Result creation timestamp (ISO string)
  completed_at?: string;           // Completion timestamp (ISO string)
}

export interface JobStatusResponse {
  job_id: string;                  // Unique job identifier
  status: string;                  // Current job status
  progress?: number;               // Completion progress (0.0-1.0)
  current_step?: string;           // Currently executing step
  estimated_completion?: string;   // Estimated completion time (ISO string)
  result?: RunResult;              // Final result if completed
  error?: string;                  // Error message if failed
}

// Legacy compatibility types
export interface AnalysisRequest {
  question: string;                // Natural language question
  data_source: DataSource;         // Data source configuration
  preferences?: Record<string, any>; // Analysis preferences
  context?: Record<string, any>;   // Additional context
}

export interface AnalysisResponse {
  job_id: string;                  // Unique job identifier
  status: string;                  // Job status
  result?: RunResult;              // Analysis result if completed
  message?: string;                // Status message
}

// API Error types
export interface ApiError {
  detail: string;                  // Error message
  type?: string;                   // Error type
  status_code: number;             // HTTP status code
}

// Configuration types for common data sources
export interface PostgresConfig {
  host: string;
  port?: number;
  database: string;
  username: string;
  password: string;
  schema?: string;
  ssl?: boolean;
}

export interface MySQLConfig {
  host: string;
  port?: number;
  database: string;
  username: string;
  password: string;
  charset?: string;
}

export interface SQLiteConfig {
  database_path: string;           // Path to SQLite database file
}

export interface SnowflakeConfig {
  account: string;                 // Snowflake account identifier
  username: string;
  password: string;
  database: string;
  schema?: string;
  warehouse?: string;
  role?: string;
}

export interface BigQueryConfig {
  project_id: string;              // Google Cloud Project ID
  dataset_id?: string;             // Default dataset
  credentials_path?: string;       // Path to service account JSON
  credentials_json?: string;       // Service account JSON content
}

export interface CSVConfig {
  file_path: string | string[];    // Path(s) to CSV file(s)
  delimiter?: string;              // CSV delimiter (default: ',')
  encoding?: string;               // File encoding (default: 'utf-8')
  has_header?: boolean;            // Whether first row is header
}

// Helper type for creating data sources
export type DataSourceConfig = 
  | { kind: "postgres"; config: PostgresConfig }
  | { kind: "mysql"; config: MySQLConfig }
  | { kind: "sqlite"; config: SQLiteConfig }
  | { kind: "snowflake"; config: SnowflakeConfig }
  | { kind: "bigquery"; config: BigQueryConfig }
  | { kind: "csv"; config: CSVConfig }
  | { kind: string; config: Record<string, any> }; // Generic fallback

// Response type for dialect capabilities
export interface DialectCapabilities {
  supported_dialects: SupportedDialect[];
  capabilities: Record<string, {
    functions: string[];
    features: {
      window_functions: boolean;
      cte: boolean;
      json_support: boolean;
      ilike: boolean;
    };
  }>;
}

// Response type for available connectors
export interface ConnectorInfo {
  available_connectors: Record<string, string>;
  total_count: number;
} 