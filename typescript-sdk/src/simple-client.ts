/**
 * Simplified client for the Analyst Agent API.
 * This version avoids complex typing to focus on core functionality.
 */

export interface SimpleDataSource {
  type: string;
  connection_string?: string;
  file_path?: string;
  [key: string]: any;
}

export interface SimpleAnalysisRequest {
  question: string;
  data_source: SimpleDataSource;
  preferences?: {
    analysis_types?: string[];
    chart_types?: string[];
    include_code?: boolean;
  };
}

export interface SimpleAnalysisResponse {
  job_id: string;
  status: string;
  message: string;
}

export class SimpleAnalystClient {
  private baseUrl: string;
  private apiKey?: string;

  constructor(config: { baseUrl: string; apiKey?: string }) {
    this.baseUrl = config.baseUrl;
    this.apiKey = config.apiKey;
  }

  async ask(request: SimpleAnalysisRequest): Promise<SimpleAnalysisResponse> {
    const response = await fetch(`${this.baseUrl}/v1/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` }),
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async getJobStatus(jobId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/v1/jobs/${jobId}`, {
      headers: {
        ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` }),
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async healthCheck(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/v1/health`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }
} 