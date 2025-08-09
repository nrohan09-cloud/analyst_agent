// Main entry point for the Analyst Agent TypeScript frontend
import './styles/main.css'

interface QuerySpec {
  question: string;
  dialect: string;
  time_window?: string | null;
  filters: Record<string, any>;
  budget: {
    queries: number;
    seconds: number;
  };
  validation_profile: string;
}

interface DataSource {
  kind: string;
  config: Record<string, any>;
  business_tz: string;
}

interface AnalysisResult {
  job_id: string;
  answer: string;
  artifacts?: Array<{
    id: string;
    kind: string;
    title: string;
    content?: string;
    data?: any;
  }>;
}

const API_BASE = 'http://localhost:8000';

// UI Elements
let questionInput: HTMLTextAreaElement;
let dialectSelect: HTMLSelectElement;
let timeWindowSelect: HTMLSelectElement;
let dbUrlInput: HTMLInputElement;
let dbHostInput: HTMLInputElement;
let dbNameInput: HTMLInputElement;
let dbUserInput: HTMLInputElement;
let dbPasswordInput: HTMLInputElement;
let submitBtn: HTMLButtonElement;
let statusDiv: HTMLElement;
let resultsDiv: HTMLElement;
let answerDiv: HTMLElement;
let sqlCard: HTMLElement;
let generatedSqlPre: HTMLElement;
let dataCard: HTMLElement;
let dataPreviewDiv: HTMLElement;
let connectionDetails: HTMLElement;

function initializeElements(): void {
  questionInput = document.getElementById('question') as HTMLTextAreaElement;
  dialectSelect = document.getElementById('dialect') as HTMLSelectElement;
  timeWindowSelect = document.getElementById('timeWindow') as HTMLSelectElement;
  dbUrlInput = document.getElementById('dbUrl') as HTMLInputElement;
  dbHostInput = document.getElementById('dbHost') as HTMLInputElement;
  dbNameInput = document.getElementById('dbName') as HTMLInputElement;
  dbUserInput = document.getElementById('dbUser') as HTMLInputElement;
  dbPasswordInput = document.getElementById('dbPassword') as HTMLInputElement;
  submitBtn = document.getElementById('submitBtn') as HTMLButtonElement;
  statusDiv = document.getElementById('status') as HTMLElement;
  resultsDiv = document.getElementById('results') as HTMLElement;
  answerDiv = document.getElementById('answer') as HTMLElement;
  sqlCard = document.getElementById('sqlCard') as HTMLElement;
  generatedSqlPre = document.getElementById('generatedSql') as HTMLElement;
  dataCard = document.getElementById('dataCard') as HTMLElement;
  dataPreviewDiv = document.getElementById('dataPreview') as HTMLElement;
  connectionDetails = document.getElementById('connectionDetails') as HTMLElement;
}

function fillExample(text: string): void {
  if (questionInput) {
    questionInput.value = text;
  }
}

function showStatus(message: string, type: 'loading' | 'success' | 'error'): void {
  if (!statusDiv) return;
  
  statusDiv.className = `status ${type}`;
  statusDiv.style.display = 'block';
  
  if (type === 'loading') {
    statusDiv.innerHTML = `<span class="spinner"></span>${message}`;
  } else {
    statusDiv.innerHTML = message;
  }
}

function hideStatus(): void {
  if (statusDiv) {
    statusDiv.style.display = 'none';
  }
}

function showResults(data: AnalysisResult): void {
  if (!resultsDiv || !answerDiv) return;
  
  // Show answer
  answerDiv.innerHTML = `<p style="font-size: 16px; line-height: 1.6;">${data.answer || 'Analysis completed successfully!'}</p>`;
  
  // Show SQL if available
  if (data.artifacts && data.artifacts.length > 0) {
    const sqlArtifact = data.artifacts.find(a => a.kind === 'sql' || a.content);
    if (sqlArtifact && generatedSqlPre && sqlCard) {
      generatedSqlPre.textContent = sqlArtifact.content || 'SQL query executed';
      sqlCard.style.display = 'block';
    }
    
    // Show data preview if available
    const dataArtifact = data.artifacts.find(a => a.kind === 'table');
    if (dataArtifact && dataArtifact.data && dataPreviewDiv && dataCard) {
      try {
        const tableData = typeof dataArtifact.data === 'string' ? 
          JSON.parse(dataArtifact.data) : dataArtifact.data;
        
        if (Array.isArray(tableData) && tableData.length > 0) {
          const table = createTable(tableData);
          dataPreviewDiv.innerHTML = table;
          dataCard.style.display = 'block';
        }
      } catch (e) {
        dataPreviewDiv.innerHTML = `<pre>${JSON.stringify(dataArtifact.data, null, 2)}</pre>`;
        dataCard.style.display = 'block';
      }
    }
  }
  
  resultsDiv.classList.add('show');
}

function createTable(data: any[]): string {
  if (!data || data.length === 0) return '<p>No data returned</p>';
  
  const headers = Object.keys(data[0]);
  const rows = data.slice(0, 10); // Show first 10 rows
  
  let html = '<table style="width: 100%; border-collapse: collapse;">';
  
  // Headers
  html += '<thead><tr>';
  headers.forEach(header => {
    html += `<th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: left;">${header}</th>`;
  });
  html += '</tr></thead>';
  
  // Rows
  html += '<tbody>';
  rows.forEach(row => {
    html += '<tr>';
    headers.forEach(header => {
      const value = row[header] ?? '';
      html += `<td style="border: 1px solid #ddd; padding: 8px;">${value}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  
  if (data.length > 10) {
    html += `<p style="margin-top: 10px; color: #666;"><em>Showing first 10 of ${data.length} rows</em></p>`;
  }
  
  return html;
}

function buildDataSourceConfig(): Record<string, any> {
  // If URL is provided, use it directly
  if (dbUrlInput && dbUrlInput.value.trim()) {
    return {
      url: dbUrlInput.value.trim()
    };
  }
  
  // Otherwise, use individual parameters
  const config: Record<string, any> = {};
  
  if (dbHostInput && dbHostInput.value.trim()) {
    config.host = dbHostInput.value.trim();
  }
  
  if (dbNameInput && dbNameInput.value.trim()) {
    config.database = dbNameInput.value.trim();
  }
  
  if (dbUserInput && dbUserInput.value.trim()) {
    config.user = dbUserInput.value.trim();
  }
  
  if (dbPasswordInput && dbPasswordInput.value.trim()) {
    config.password = dbPasswordInput.value.trim();
  }
  
  return config;
}

async function handleFormSubmit(e: Event): Promise<void> {
  e.preventDefault();
  
  if (!submitBtn || !resultsDiv) return;
  
  // Get form values
  const question = questionInput?.value || '';
  const dialect = dialectSelect?.value || 'sqlite';
  const timeWindow = timeWindowSelect?.value || null;
  
  // Build configuration
  const config = buildDataSourceConfig();
  
  // Prepare request - use "fast" for SQLite to avoid async jobs, "balanced" for others to enable streaming
  const spec: QuerySpec = {
    question: question,
    dialect: dialect,
    time_window: timeWindow || null,
    filters: {},
    budget: { queries: 30, seconds: 90 },
    validation_profile: dialect === 'sqlite' ? "fast" : "balanced"
  };
  
  const dataSource: DataSource = {
    kind: dialect,
    config: config,
    business_tz: "America/New_York"
  };
  
  // Update UI
  submitBtn.disabled = true;
  resultsDiv.classList.remove('show');
  showStatus('🚀 Starting analysis...', 'loading');
  
  try {
    // Start the analysis job
    const response = await fetch(`${API_BASE}/v1/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        spec: spec,
        data_source: dataSource
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const initialResult: AnalysisResult = await response.json();
    
    // Check if job is running asynchronously or completed synchronously
    console.log('Initial result:', initialResult);
    
    if (initialResult.answer && initialResult.answer.includes('Analysis is running')) {
      // Start streaming for async job
      showStatus('🔄 Analysis running - streaming updates...', 'loading');
      await streamJobProgress(initialResult.job_id);
    } else {
      // Job completed synchronously - most SQLite queries will end up here
      console.log('Job completed synchronously');
      hideStatus();
      showResults(initialResult);
      showStatus('✅ Analysis completed successfully!', 'success');
    }
    
  } catch (error) {
    console.error('Error:', error);
    const message = error instanceof Error ? error.message : String(error);
    showStatus(`❌ Error: ${message}`, 'error');
  } finally {
    submitBtn.disabled = false;
  }
}

async function streamJobProgress(jobId: string): Promise<void> {
  console.log('Starting streaming for job:', jobId);
  
  try {
    // First check if the job exists
    const jobStatusResponse = await fetch(`${API_BASE}/v1/jobs/${jobId}`);
    if (!jobStatusResponse.ok) {
      throw new Error(`Job ${jobId} not found or error fetching status`);
    }
    
    const jobStatus = await jobStatusResponse.json();
    console.log('Job status before streaming:', jobStatus);
    
    // If job is already completed, don't stream
    if (jobStatus.status === 'completed') {
      console.log('Job already completed, showing results directly');
      if (jobStatus.result) {
        hideStatus();
        showResults(jobStatus.result);
        showStatus('✅ Analysis completed successfully!', 'success');
      }
      return;
    }
    
    const streamUrl = `${API_BASE}/v1/stream/${jobId}`;
    console.log('Connecting to stream:', streamUrl);
    
    const eventSource = new EventSource(streamUrl);
    let stepCount = 0;
    let hasReceivedData = false;
    
    // Set up a timeout to detect if streaming actually starts
    const timeout = setTimeout(() => {
      if (!hasReceivedData) {
        console.log('No streaming data received, checking job status...');
        eventSource.close();
        checkJobStatusFallback(jobId);
      }
    }, 3000);
    
    eventSource.onopen = () => {
      console.log('EventSource connection opened');
      showStatus('🔗 Connected to analysis stream...', 'loading');
    };
    
    eventSource.onmessage = (event) => {
      hasReceivedData = true;
      clearTimeout(timeout);
      
      try {
        const data = JSON.parse(event.data);
        console.log('Streaming event:', data);
        
        switch (data.type) {
          case 'status':
            showStatus(`📊 Status: ${data.status}`, 'loading');
            break;
            
          case 'step':
            stepCount++;
            const stepEmoji = getStepEmoji(data.step_name);
            showStatus(`${stepEmoji} Step ${stepCount}: ${data.step_name} (${data.status})`, 'loading');
            
            // Show SQL if available
            if (data.sql && generatedSqlPre && sqlCard) {
              generatedSqlPre.textContent = data.sql;
              sqlCard.style.display = 'block';
            }
            break;
            
          case 'progress':
            const progressPercent = Math.round(data.progress);
            showStatus(`⏳ Progress: ${progressPercent}% - ${data.current_step || 'processing...'}`, 'loading');
            break;
            
          case 'completion':
            console.log('Received completion event:', data);
            eventSource.close();
            
            if (data.status === 'completed' && data.result) {
              hideStatus();
              showResults(data.result);
              showStatus('✅ Analysis completed successfully!', 'success');
            } else {
              const errorMsg = data.error || 'Analysis failed';
              showStatus(`❌ Error: ${errorMsg}`, 'error');
            }
            break;
            
          case 'error':
            console.log('Received error event:', data);
            eventSource.close();
            showStatus(`❌ Streaming Error: ${data.error}`, 'error');
            break;
        }
      } catch (parseError) {
        console.error('Error parsing streaming data:', parseError, 'Raw data:', event.data);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('EventSource error:', error);
      clearTimeout(timeout);
      eventSource.close();
      
      // Try fallback to polling
      console.log('Streaming failed, trying fallback polling...');
      checkJobStatusFallback(jobId);
    };
    
  } catch (error) {
    console.error('Error setting up streaming:', error);
    showStatus(`❌ Streaming Setup Error: ${error}`, 'error');
  }
}

async function checkJobStatusFallback(jobId: string): Promise<void> {
  console.log('Using fallback polling for job:', jobId);
  showStatus('🔄 Using fallback polling...', 'loading');
  
  const maxAttempts = 30; // 30 seconds
  let attempts = 0;
  
  const pollInterval = setInterval(async () => {
    try {
      attempts++;
      const response = await fetch(`${API_BASE}/v1/jobs/${jobId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch job status: ${response.status}`);
      }
      
      const jobStatus = await response.json();
      console.log(`Polling attempt ${attempts}:`, jobStatus);
      
      if (jobStatus.status === 'completed') {
        clearInterval(pollInterval);
        if (jobStatus.result) {
          hideStatus();
          showResults(jobStatus.result);
          showStatus('✅ Analysis completed successfully!', 'success');
        } else {
          showStatus('❌ Analysis completed but no result available', 'error');
        }
      } else if (jobStatus.status === 'failed') {
        clearInterval(pollInterval);
        showStatus(`❌ Analysis failed: ${jobStatus.error || 'Unknown error'}`, 'error');
      } else if (attempts >= maxAttempts) {
        clearInterval(pollInterval);
        showStatus('❌ Analysis timed out', 'error');
      } else {
        // Still running
        const progress = jobStatus.progress || 0;
        showStatus(`⏳ Polling: ${Math.round(progress)}% - ${jobStatus.current_step || 'processing...'}`, 'loading');
      }
    } catch (error) {
      console.error('Polling error:', error);
      attempts++;
      if (attempts >= maxAttempts) {
        clearInterval(pollInterval);
        showStatus(`❌ Polling failed: ${error}`, 'error');
      }
    }
  }, 1000);
}

function getStepEmoji(stepName: string): string {
  const emojis: Record<string, string> = {
    'plan': '📋',
    'profile': '🔍',
    'mvq': '⚡',
    'diagnose': '🩺',
    'refine': '✨',
    'transform': '🔄',
    'produce': '🏭',
    'validate': '✅',
    'present': '📊'
  };
  
  return emojis[stepName] || '⚙️';
}

function toggleConnectionDetails(): void {
  if (!dbUrlInput || !connectionDetails) return;
  
  // Show/hide individual connection fields based on URL field
  const hasUrl = dbUrlInput.value.trim().length > 0;
  connectionDetails.style.opacity = hasUrl ? '0.5' : '1.0';
  
  // Disable/enable individual fields when URL is provided
  [dbHostInput, dbNameInput, dbUserInput, dbPasswordInput].forEach(input => {
    if (input) {
      input.disabled = hasUrl;
    }
  });
}

async function testApiConnection(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (response.ok) {
      console.log('✅ API connection successful');
    } else {
      console.warn('⚠️ API connection failed');
    }
  } catch (error) {
    console.warn('⚠️ Could not connect to API:', error);
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  console.log('🤖 Analyst Agent TypeScript frontend starting...');
  
  initializeElements();
  
  // Set up event listeners
  if (submitBtn) {
    const form = document.getElementById('queryForm');
    if (form) {
      form.addEventListener('submit', handleFormSubmit);
    }
  }
  
  // Set up example click handlers
  const examples = document.querySelectorAll('.example');
  examples.forEach(example => {
    example.addEventListener('click', () => {
      const text = example.getAttribute('data-example');
      if (text) {
        fillExample(text);
      }
    });
  });
  
  // Set up URL field change handler
  if (dbUrlInput) {
    dbUrlInput.addEventListener('input', toggleConnectionDetails);
    dbUrlInput.addEventListener('change', toggleConnectionDetails);
  }
  
  // Set up dialect change handler for SQLite special case
  if (dialectSelect) {
    dialectSelect.addEventListener('change', () => {
      const dialect = dialectSelect.value;
      if (dialect === 'sqlite' && dbNameInput) {
        // Set default SQLite database path
        if (!dbNameInput.value || dbNameInput.value === 'my_database') {
          dbNameInput.value = 'data/test_ecommerce.db';
        }
        // Clear host for SQLite
        if (dbHostInput) {
          dbHostInput.value = '';
        }
      } else if (dbHostInput && !dbHostInput.value) {
        dbHostInput.value = 'localhost';
      }
    });
  }
  
  // Test API connection
  testApiConnection();
  
  console.log('Frontend initialized successfully');
});

// Make fillExample available globally for onclick handlers
(window as any).fillExample = fillExample;
