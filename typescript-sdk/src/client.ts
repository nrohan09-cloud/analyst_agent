/**
 * Main client for the Analyst Agent API.
 * Provides a simple, type-safe interface for interacting with the service.
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';
import {
  ClientConfig,
  AnalysisRequest,
  AnalysisResponse,
  JobStatusResponse,
  HealthCheck,
  ErrorResponse,
  PollOptions,
  AnalysisResult
} from './types';

export class AnalystAgentError extends Error {
  public readonly status?: number;
  public readonly details?: Record<string, any>;

  constructor(message: string, status?: number, details?: Record<string, any>) {
    super(message);
    this.name = 'AnalystAgentError';
    this.status = status;
    this.details = details;
  }
}

export class AnalystClient {
  private readonly http: AxiosInstance;
  private readonly config: ClientConfig;

  constructor(config: ClientConfig) {
    this.config = {
      timeout: 30000,
      retries: 3,
      retryDelay: 1000,
      ...config,
    };

    this.http = axios.create({
      baseURL: this.config.baseUrl,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` }),
      },
    });

    // Response interceptor for error handling
    this.http.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ErrorResponse>) => {
        if (error.response?.data) {
          throw new AnalystAgentError(
            error.response.data.message || error.message,
            error.response.status,
            error.response.data.details
          );
        }
        throw new AnalystAgentError(error.message, error.response?.status);
      }
    );

    // Request interceptor for retry logic
    this.http.interceptors.request.use(async (config) => {
      if (!config.metadata) {
        config.metadata = {};
      }
      config.metadata.retryCount = config.metadata.retryCount || 0;
      return config;
    });
  }

  /**
   * Check the health status of the service.
   */
  async healthCheck(): Promise<HealthCheck> {
    const response = await this.http.get<HealthCheck>('/v1/health');
    return response.data;
  }

  /**
   * Submit a natural language question for data analysis.
   * 
   * @param request - Analysis request containing question and data source
   * @returns Promise resolving to analysis response with job ID
   */
  async ask(request: AnalysisRequest): Promise<AnalysisResponse> {
    const response = await this.http.post<AnalysisResponse>('/v1/ask', request);
    return response.data;
  }

  /**
   * Get the status of an analysis job.
   * 
   * @param jobId - Unique job identifier
   * @returns Promise resolving to job status response
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const response = await this.http.get<JobStatusResponse>(`/v1/jobs/${jobId}`);
    return response.data;
  }

  /**
   * Cancel a running analysis job.
   * 
   * @param jobId - Unique job identifier
   * @returns Promise resolving to cancellation confirmation
   */
  async cancelJob(jobId: string): Promise<{ message: string }> {
    const response = await this.http.delete<{ message: string }>(`/v1/jobs/${jobId}`);
    return response.data;
  }

  /**
   * Submit a question and wait for the analysis to complete.
   * This is a convenience method that combines ask() and polling.
   * 
   * @param request - Analysis request
   * @param options - Polling options
   * @returns Promise resolving to the completed analysis result
   */
  async askAndWait(
    request: AnalysisRequest,
    options: PollOptions = {}
  ): Promise<AnalysisResult> {
    const response = await this.ask(request);
    return this.waitForCompletion(response.job_id, options);
  }

  /**
   * Poll for job completion and return the final result.
   * 
   * @param jobId - Job ID to poll
   * @param options - Polling options
   * @returns Promise resolving to the completed analysis result
   */
  async waitForCompletion(
    jobId: string,
    options: PollOptions = {}
  ): Promise<AnalysisResult> {
    const {
      interval = 2000,
      timeout = 300000, // 5 minutes
      onProgress
    } = options;

    const startTime = Date.now();

    while (true) {
      const status = await this.getJobStatus(jobId);
      
      if (onProgress) {
        onProgress(status);
      }

      switch (status.status) {
        case 'completed':
          if (!status.result) {
            throw new AnalystAgentError('Job completed but no result available');
          }
          return status.result;

        case 'failed':
          throw new AnalystAgentError(
            status.result?.error_message || 'Analysis job failed'
          );

        case 'cancelled':
          throw new AnalystAgentError('Analysis job was cancelled');

        case 'pending':
        case 'running':
          // Check timeout
          if (Date.now() - startTime > timeout) {
            throw new AnalystAgentError(
              `Job did not complete within ${timeout}ms timeout`
            );
          }
          
          // Wait before next poll
          await this.sleep(interval);
          break;

        default:
          throw new AnalystAgentError(`Unknown job status: ${status.status}`);
      }
    }
  }

  /**
   * Create a quick analysis for simple questions with automatic data source detection.
   * This is a convenience method for common use cases.
   * 
   * @param question - Natural language question
   * @param dataSource - Data source configuration
   * @param options - Polling options
   * @returns Promise resolving to the completed analysis result
   */
  async quickAnalysis(
    question: string,
    dataSource: { type: 'csv' | 'json'; file_path: string } | 
                { type: 'postgres' | 'mysql' | 'sqlite'; connection_string: string },
    options: PollOptions = {}
  ): Promise<AnalysisResult> {
    const request: AnalysisRequest = {
      question,
      data_source: dataSource as any,
      preferences: {
        analysis_types: ['descriptive', 'inferential'],
        chart_types: ['bar', 'line', 'scatter'],
        include_code: false,
        confidence_threshold: 0.8
      }
    };

    return this.askAndWait(request, options);
  }

  /**
   * Get insights summary from an analysis result.
   * Helper method to extract key insights in a readable format.
   */
  static getInsightsSummary(result: AnalysisResult): string {
    const insights = result.insights
      .filter(insight => insight.confidence >= 0.7)
      .map(insight => `• ${insight.title}: ${insight.description}`)
      .join('\n');
    
    return `${result.summary}\n\nKey Insights:\n${insights}`;
  }

  /**
   * Extract chart data for use with charting libraries.
   */
  static extractChartData(result: AnalysisResult) {
    return result.charts.map(chart => ({
      title: chart.title,
      type: chart.type,
      data: chart.data,
      config: chart.config
    }));
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
} 