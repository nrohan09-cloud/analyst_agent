/**
 * TypeScript client for the Analyst Agent API.
 * 
 * Provides a comprehensive interface for interacting with the analysis service
 * with support for multiple database dialects and async workflow execution.
 */

import {
  QuerySpec,
  DataSource,
  RunResult,
  JobStatusResponse,
  AnalysisRequest,
  AnalysisResponse,
  DialectCapabilities,
  ConnectorInfo,
  ApiError,
  SupportedDialect,
  ValidationProfile
} from './types';

export interface AnalystClientConfig {
  baseUrl: string;                 // Base URL of the API service
  apiKey?: string | undefined;     // Optional API key for authentication
  timeout?: number | undefined;    // Request timeout in milliseconds
  defaultDialect?: SupportedDialect | undefined; // Default SQL dialect to use
  retries?: number | undefined;    // Number of retry attempts for failed requests
}

export class AnalystClient {
  private baseUrl: string;
  private apiKey?: string | undefined;
  private timeout: number;
  private defaultDialect: SupportedDialect;
  private retries: number;

  constructor(config: AnalystClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.apiKey = config.apiKey;
    this.timeout = config.timeout ?? 30000; // 30 second default
    this.defaultDialect = config.defaultDialect ?? 'postgres';
    this.retries = config.retries ?? 3;
  }

  /**
   * Make an HTTP request with error handling and retries.
   */
  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}/v1${endpoint}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {})
    };

    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const requestOptions: RequestInit = {
      ...options,
      headers,
      signal: AbortSignal.timeout(this.timeout)
    };

    let lastError: Error;

    for (let attempt = 1; attempt <= this.retries; attempt++) {
      try {
        const response = await fetch(url, requestOptions);

        if (!response.ok) {
          const errorData: ApiError = await response.json().catch(() => ({
            detail: response.statusText || 'Unknown error',
            status_code: response.status
          }));
          
          throw new AnalystApiError(
            errorData.detail || `HTTP ${response.status}`,
            response.status,
            errorData
          );
        }

        return await response.json();
      } catch (error) {
        lastError = error as Error;
        
        // Don't retry on client errors (4xx) or if it's the last attempt
        if (error instanceof AnalystApiError && error.statusCode < 500) {
          throw error;
        }
        
        if (attempt === this.retries) {
          throw lastError;
        }

        // Wait before retrying (exponential backoff)
        await this.delay(Math.pow(2, attempt - 1) * 1000);
      }
    }

    throw lastError!;
  }

  /**
   * Delay helper for retries.
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Run a data analysis query.
   */
     async query(spec: QuerySpec, dataSource: DataSource): Promise<RunResult> {
     // Ensure spec has required fields with defaults
     const finalSpec: QuerySpec = {
       ...spec,
       dialect: spec.dialect || this.defaultDialect
     };

     return this.makeRequest<RunResult>('/query', {
       method: 'POST',
       body: JSON.stringify({ spec: finalSpec, data_source: dataSource })
     });
   }

  /**
   * Get the status of an analysis job.
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    return this.makeRequest<JobStatusResponse>(`/jobs/${jobId}`, {
      method: 'GET'
    });
  }

  /**
   * Cancel a running analysis job.
   */
  async cancelJob(jobId: string): Promise<{ message: string }> {
    return this.makeRequest<{ message: string }>(`/jobs/${jobId}`, {
      method: 'DELETE'
    });
  }

  /**
   * Legacy compatibility method for the old ask endpoint.
   */
  async ask(request: AnalysisRequest): Promise<AnalysisResponse> {
    return this.makeRequest<AnalysisResponse>('/ask', {
      method: 'POST',
      body: JSON.stringify(request)
    });
  }

  /**
   * Wait for a job to complete and return the final result.
   */
  async waitForCompletion(
    jobId: string,
    options: {
      pollInterval?: number;     // Polling interval in milliseconds
      maxWaitTime?: number;      // Maximum wait time in milliseconds
      onProgress?: (status: JobStatusResponse) => void; // Progress callback
    } = {}
  ): Promise<RunResult> {
    const pollInterval = options.pollInterval || 2000; // 2 seconds default
    const maxWaitTime = options.maxWaitTime || 300000; // 5 minutes default
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitTime) {
      const status = await this.getJobStatus(jobId);

      if (options.onProgress) {
        options.onProgress(status);
      }

      if (status.status === 'completed' && status.result) {
        return status.result;
      }

      if (status.status === 'failed') {
        throw new AnalystApiError(
          status.error || 'Analysis job failed',
          500,
          { detail: status.error || 'Job failed', status_code: 500 }
        );
      }

      if (status.status === 'cancelled') {
        throw new AnalystApiError(
          'Analysis job was cancelled',
          400,
          { detail: 'Job cancelled', status_code: 400 }
        );
      }

      await this.delay(pollInterval);
    }

    throw new AnalystApiError(
      `Job ${jobId} did not complete within ${maxWaitTime}ms`,
      408,
      { detail: 'Request timeout', status_code: 408 }
    );
  }

  /**
   * Convenience method to run a query and wait for completion.
   */
  async queryAndWait(
    spec: QuerySpec,
    dataSource: DataSource,
    options?: {
      pollInterval?: number;
      maxWaitTime?: number;
      onProgress?: (status: JobStatusResponse) => void;
    }
  ): Promise<RunResult> {
    // For fast validation, the query should complete synchronously
    if (spec.validation_profile === 'fast') {
      return this.query(spec, dataSource);
    }

    // For other profiles, start the job and wait for completion
    const result = await this.query(spec, dataSource);
    
    // If we got a complete result immediately, return it
    if (result.quality.passed || result.completed_at) {
      return result;
    }

    // Otherwise, wait for completion
    return this.waitForCompletion(result.job_id, options);
  }

  /**
   * Quick analysis method with sensible defaults.
   */
  async quickAnalysis(
    question: string,
    dataSource: DataSource,
    options: {
      dialect?: SupportedDialect;
      timeWindow?: string;
      grain?: string;
      validationProfile?: ValidationProfile;
    } = {}
  ): Promise<RunResult> {
         const spec: QuerySpec = {
       question,
       dialect: options.dialect || this.defaultDialect,
       ...(options.timeWindow && { time_window: options.timeWindow }),
       ...(options.grain && { grain: options.grain }),
       budget: { queries: 10, seconds: 60 }, // Conservative defaults
       validation_profile: options.validationProfile || 'balanced'
     };

    return this.queryAndWait(spec, dataSource);
  }

  /**
   * List supported SQL dialects and their capabilities.
   */
  async getSupportedDialects(): Promise<DialectCapabilities> {
    return this.makeRequest<DialectCapabilities>('/dialects', {
      method: 'GET'
    });
  }

  /**
   * List available data source connectors.
   */
  async getAvailableConnectors(): Promise<ConnectorInfo> {
    return this.makeRequest<ConnectorInfo>('/connectors', {
      method: 'GET'
    });
  }

  /**
   * Health check endpoint.
   */
  async healthCheck(): Promise<{ status: string; timestamp: string; version: string }> {
    return this.makeRequest<{ status: string; timestamp: string; version: string }>('/health', {
      method: 'GET'
    });
  }

  /**
   * Stream analysis progress for a job.
   * Returns an EventSource for real-time updates.
   */
  streamJobProgress(
    jobId: string,
    callbacks: {
      onStatus?: (data: { type: 'status'; status: string }) => void;
      onStep?: (data: { type: 'step'; step_name: string; status: string; sql?: string; row_count?: number; duration_ms?: number }) => void;
      onProgress?: (data: { type: 'progress'; progress: number; current_step?: string }) => void;
      onCompletion?: (data: { type: 'completion'; status: string; result?: RunResult; error?: string }) => void;
      onError?: (data: { type: 'error'; error: string }) => void;
      onOpen?: () => void;
    } = {}
  ): EventSource {
    const streamUrl = `${this.baseUrl}/v1/stream/${jobId}`;
    const eventSource = new EventSource(streamUrl);
    
    eventSource.onopen = () => {
      if (callbacks.onOpen) {
        callbacks.onOpen();
      }
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'status':
            if (callbacks.onStatus) {
              callbacks.onStatus(data);
            }
            break;
            
          case 'step':
            if (callbacks.onStep) {
              callbacks.onStep(data);
            }
            break;
            
          case 'progress':
            if (callbacks.onProgress) {
              callbacks.onProgress(data);
            }
            break;
            
          case 'completion':
            if (callbacks.onCompletion) {
              callbacks.onCompletion(data);
            }
            eventSource.close();
            break;
            
          case 'error':
            if (callbacks.onError) {
              callbacks.onError(data);
            }
            eventSource.close();
            break;
        }
      } catch (parseError) {
        if (callbacks.onError) {
          callbacks.onError({ type: 'error', error: `Failed to parse streaming data: ${parseError}` });
        }
        eventSource.close();
      }
    };

    eventSource.onerror = (error) => {
      if (callbacks.onError) {
        callbacks.onError({ type: 'error', error: 'EventSource connection error' });
      }
    };

    return eventSource;
  }

  /**
   * Run a query with streaming support.
   * Automatically handles both synchronous and asynchronous results.
   */
  async queryWithStreaming(
    spec: QuerySpec,
    dataSource: DataSource,
    callbacks: {
      onStatus?: (data: { type: 'status'; status: string }) => void;
      onStep?: (data: { type: 'step'; step_name: string; status: string; sql?: string; row_count?: number; duration_ms?: number }) => void;
      onProgress?: (data: { type: 'progress'; progress: number; current_step?: string }) => void;
      onError?: (error: string) => void;
    } = {}
  ): Promise<RunResult> {
    // Start the query
    const initialResult = await this.query(spec, dataSource);
    
    // If completed synchronously, return immediately
    if (initialResult.completed_at || initialResult.quality.passed) {
      return initialResult;
    }
    
    // For async jobs, set up streaming and wait for completion
    return new Promise((resolve, reject) => {
      let hasReceivedData = false;
      
      const eventSource = this.streamJobProgress(initialResult.job_id, {
        onOpen: () => {
          hasReceivedData = true;
          if (callbacks.onStatus) {
            callbacks.onStatus({ type: 'status', status: 'Connected to analysis stream' });
          }
        },
        
        ...(callbacks.onStatus && { onStatus: callbacks.onStatus }),
        ...(callbacks.onStep && { onStep: callbacks.onStep }),
        ...(callbacks.onProgress && { onProgress: callbacks.onProgress }),
        
        onCompletion: (data) => {
          if (data.status === 'completed' && data.result) {
            resolve(data.result);
          } else {
            reject(new AnalystApiError(
              data.error || 'Analysis failed',
              500,
              { detail: data.error || 'Job failed', status_code: 500 }
            ));
          }
        },
        
        onError: (data) => {
          if (callbacks.onError) {
            callbacks.onError(data.error);
          }
          reject(new AnalystApiError(
            data.error,
            500,
            { detail: data.error, status_code: 500 }
          ));
        }
      });
      
      // Fallback to polling if streaming doesn't work
      setTimeout(() => {
        if (!hasReceivedData) {
          eventSource.close();
          if (callbacks.onStatus) {
            callbacks.onStatus({ type: 'status', status: 'Falling back to polling...' });
          }
          
          this.waitForCompletion(initialResult.job_id, {
            onProgress: (status) => {
              if (callbacks.onProgress) {
                callbacks.onProgress({
                  type: 'progress',
                  progress: status.progress || 0,
                  ...(status.current_step && { current_step: status.current_step })
                });
              }
            }
          }).then(resolve).catch(reject);
        }
      }, 3000);
    });
  }

  /**
   * Create a data source configuration helper.
   */
  static createDataSource(
    kind: string,
    config: Record<string, any>,
    businessTz: string = 'Asia/Kolkata'
  ): DataSource {
    return {
      kind,
      config,
      business_tz: businessTz
    };
  }

  /**
   * Create a PostgreSQL data source.
   */
  static createPostgresDataSource(config: {
    host: string;
    port?: number;
    database: string;
    username: string;
    password: string;
    schema?: string;
    ssl?: boolean;
  }): DataSource {
    return this.createDataSource('postgres', {
      url: `postgresql://${config.username}:${config.password}@${config.host}:${config.port || 5432}/${config.database}`,
      schema: config.schema,
      ...config
    });
  }

  /**
   * Create a SQLite data source.
   */
  static createSQLiteDataSource(databasePath: string): DataSource {
    return this.createDataSource('sqlite', {
      url: `sqlite:///${databasePath}`
    });
  }

  /**
   * Create a CSV data source.
   */
  static createCSVDataSource(filePath: string | string[]): DataSource {
    return this.createDataSource('csv', {
      file_path: filePath
    });
  }
}

/**
 * Custom error class for API errors.
 */
export class AnalystApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public apiError?: ApiError
  ) {
    super(message);
    this.name = 'AnalystApiError';
  }
}

/**
 * Simple client with minimal dependencies for basic use cases.
 */
export class SimpleAnalystClient {
  private baseUrl: string;
  private apiKey?: string | undefined;

  constructor(config: { baseUrl: string; apiKey?: string }) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.apiKey = config.apiKey;
  }

  async query(
    question: string,
    dataSource: DataSource,
    dialect: SupportedDialect = 'postgres'
  ): Promise<RunResult> {
    const spec: QuerySpec = {
      question,
      dialect,
      validation_profile: 'fast'
    };

    const response = await fetch(`${this.baseUrl}/v1/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
      },
      body: JSON.stringify({ spec, data_source: dataSource })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async healthCheck(): Promise<{ status: string }> {
    const response = await fetch(`${this.baseUrl}/v1/health`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
  }
}
