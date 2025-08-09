// Main entry point for the Analyst Agent TypeScript frontend
import './styles/main.css'
import { 
  AnalystClient, 
  AnalystApiError,
  type QuerySpec, 
  type DataSource, 
  type RunResult,
  type SupportedDialect,
  type ValidationProfile 
} from 'analyst-agent-sdk'

const API_BASE = 'http://localhost:8000';

// Initialize the SDK client
const client = new AnalystClient({
  baseUrl: API_BASE,
  timeout: 60000,
  retries: 3,
  defaultDialect: 'postgres'
});

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
let progressLog: HTMLElement;

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
  progressLog = document.getElementById('progressLog') as HTMLElement;
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

function addProgressEntry(
  message: string, 
  type: 'info' | 'step' | 'sql' | 'success' | 'error' = 'info',
  metadata?: { sql?: string; rowCount?: number; duration?: number }
): void {
  if (!progressLog) return;

  const timestamp = new Date().toLocaleTimeString();
  const entry = document.createElement('div');
  entry.className = `progress-entry ${type}`;
  
  let emoji = '';
  switch (type) {
    case 'step': emoji = getStepEmoji(message); break;
    case 'sql': emoji = '📝'; break;
    case 'success': emoji = '✅'; break;
    case 'error': emoji = '❌'; break;
    default: emoji = 'ℹ️';
  }
  
  let content = `<div class="progress-header">
    <span class="progress-time">[${timestamp}]</span>
    <span class="progress-message">${emoji} ${message}</span>
  </div>`;
  
  if (metadata) {
    if (metadata.sql) {
      content += `<div class="progress-sql">
        <details>
          <summary>📝 SQL Query (${metadata.duration ? `${metadata.duration}ms` : 'N/A'})</summary>
          <pre>${metadata.sql}</pre>
        </details>
      </div>`;
    }
    
    if (metadata.rowCount !== undefined) {
      content += `<div class="progress-metadata">📊 Rows: ${metadata.rowCount}</div>`;
    }
  }
  
  entry.innerHTML = content;
  progressLog.appendChild(entry);
  progressLog.scrollTop = progressLog.scrollHeight;
}

function clearProgressLog(): void {
  if (progressLog) {
    progressLog.innerHTML = '';
  }
}

function showResults(data: RunResult): void {
  if (!resultsDiv || !answerDiv) return;
  
  // Show answer
  answerDiv.innerHTML = `<p style="font-size: 16px; line-height: 1.6;">${data.answer || 'Analysis completed successfully!'}</p>`;
  
  // Show execution steps in progress log
  if (data.execution_steps && data.execution_steps.length > 0) {
    data.execution_steps.forEach(step => {
      addProgressEntry(
        `${step.step_name.toUpperCase()} ${step.status.toUpperCase()}`,
        'step',
        {
          ...(step.sql && { sql: step.sql }),
          ...(step.row_count !== undefined && { rowCount: step.row_count }),
          ...(step.duration_ms !== undefined && { duration: step.duration_ms })
        }
      );
    });
  }
  
  // Show SQL artifacts
  const sqlArtifacts = data.tables?.filter(a => a.kind === 'sql') || [];
  if (sqlArtifacts.length > 0 && generatedSqlPre && sqlCard) {
    const sqlArtifact = sqlArtifacts[0];
    const mainSql = sqlArtifact?.content || sqlArtifact?.title || 'SQL executed';
    generatedSqlPre.textContent = typeof mainSql === 'string' ? mainSql : JSON.stringify(mainSql, null, 2);
    sqlCard.style.display = 'block';
  }
  
  // Show data preview
  const dataArtifacts = data.tables?.filter(a => a.kind === 'table') || [];
  if (dataArtifacts.length > 0 && dataPreviewDiv && dataCard) {
    const dataArtifact = dataArtifacts[0];
    if (dataArtifact?.content) {
      try {
        const tableData = typeof dataArtifact.content === 'string' ? 
          JSON.parse(dataArtifact.content) : dataArtifact.content;
        
        if (Array.isArray(tableData) && tableData.length > 0) {
          const table = createTable(tableData);
          dataPreviewDiv.innerHTML = table;
          dataCard.style.display = 'block';
        }
      } catch (e) {
        dataPreviewDiv.innerHTML = `<pre>${JSON.stringify(dataArtifact.content, null, 2)}</pre>`;
        dataCard.style.display = 'block';
      }
    }
  }
  
  // Show quality information
  if (data.quality) {
    addProgressEntry(
      `Quality Score: ${(data.quality.score * 100).toFixed(1)}% (${data.quality.passed ? 'PASSED' : 'FAILED'})`,
      data.quality.passed ? 'success' : 'error'
    );
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

function buildDataSource(): DataSource {
  const dialect = dialectSelect?.value as SupportedDialect || 'sqlite';
  
  // If URL is provided, use it directly
  if (dbUrlInput && dbUrlInput.value.trim()) {
    return AnalystClient.createDataSource(dialect, {
      url: dbUrlInput.value.trim()
    });
  }
  
  // Use SDK helper methods for common databases
  const host = dbHostInput?.value.trim() || 'localhost';
  const database = dbNameInput?.value.trim() || '';
  const username = dbUserInput?.value.trim() || '';
  const password = dbPasswordInput?.value.trim() || '';
  
  switch (dialect) {
    case 'postgres':
      return AnalystClient.createPostgresDataSource({
        host,
        database,
        username,
        password
      });
      
    case 'sqlite':
      const dbPath = database || 'data/test_ecommerce.db';
      return AnalystClient.createSQLiteDataSource(dbPath);
      
    default:
      // Handle CSV and other generic data sources
      if (dialect === 'csv' as any) {
        return AnalystClient.createCSVDataSource(database.split(',').map(f => f.trim()));
      }
      
      // Generic data source for other dialects
      return AnalystClient.createDataSource(dialect, {
        host,
        database,
        user: username,
        password
      });
  }
}

async function handleFormSubmit(e: Event): Promise<void> {
  e.preventDefault();
  
  if (!submitBtn || !resultsDiv) return;
  
  // Get form values
  const question = questionInput?.value || '';
  const dialect = dialectSelect?.value as SupportedDialect || 'sqlite';
  const timeWindow = timeWindowSelect?.value || null;
  
  // Build query spec using SDK types
  const spec: QuerySpec = {
    question: question,
    dialect: dialect,
    filters: {},
    budget: { queries: 30, seconds: 90 },
    validation_profile: (dialect === 'sqlite' ? 'fast' : 'balanced') as ValidationProfile,
    ...(timeWindow && { time_window: timeWindow })
  };
  
  const dataSource = buildDataSource();
  
  // Update UI
  submitBtn.disabled = true;
  resultsDiv.classList.remove('show');
  clearProgressLog();
  showStatus('🚀 Starting analysis...', 'loading');
  addProgressEntry('Analysis job started', 'info');
  
  try {
    if (spec.validation_profile === 'fast') {
      // For fast queries (like SQLite), use direct query
      addProgressEntry('Running fast query (synchronous)', 'info');
      const result = await client.query(spec, dataSource);
      
      hideStatus();
      showResults(result);
      showStatus('✅ Analysis completed successfully!', 'success');
      addProgressEntry('Analysis completed successfully', 'success');
      
    } else {
      // For other profiles, use streaming
      addProgressEntry('Starting streaming analysis', 'info');
      
      const result = await client.queryWithStreaming(spec, dataSource, {
        onStatus: (data) => {
          showStatus(`📡 ${data.status}`, 'loading');
          addProgressEntry(data.status, 'info');
        },
        
        onStep: (data) => {
          const stepEmoji = getStepEmoji(data.step_name);
          showStatus(`${stepEmoji} ${data.step_name.toUpperCase()} (${data.status})`, 'loading');
          
          const metadata: { sql?: string; rowCount?: number; duration?: number } = {};
          if (data.sql) metadata.sql = data.sql;
          if (data.row_count !== undefined) metadata.rowCount = data.row_count;
          if (data.duration_ms !== undefined) metadata.duration = data.duration_ms;
          
          addProgressEntry(
            `${data.step_name.toUpperCase()} ${data.status.toUpperCase()}`,
            'step',
            Object.keys(metadata).length > 0 ? metadata : undefined
          );
          
          // Update SQL display if available
          if (data.sql && generatedSqlPre && sqlCard) {
            generatedSqlPre.textContent = data.sql;
            sqlCard.style.display = 'block';
          }
        },
        
        onProgress: (data) => {
          const progressPercent = Math.round(data.progress);
          showStatus(`⏳ Progress: ${progressPercent}% - ${data.current_step || 'processing...'}`, 'loading');
        },
        
        onError: (error) => {
          addProgressEntry(`Error: ${error}`, 'error');
        }
      });
      
      hideStatus();
      showResults(result);
      showStatus('✅ Analysis completed successfully!', 'success');
      addProgressEntry('Analysis completed successfully', 'success');
    }
    
  } catch (error) {
    console.error('Analysis error:', error);
    
    let message = 'Unknown error';
    if (error instanceof AnalystApiError) {
      message = error.message;
      addProgressEntry(`API Error: ${error.message} (${error.statusCode})`, 'error');
    } else if (error instanceof Error) {
      message = error.message;
      addProgressEntry(`Error: ${error.message}`, 'error');
    }
    
    showStatus(`❌ Error: ${message}`, 'error');
  } finally {
    submitBtn.disabled = false;
  }
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
  
  return emojis[stepName.toLowerCase()] || '⚙️';
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
    const health = await client.healthCheck();
    console.log('✅ API connection successful:', health);
    addProgressEntry(`API connected: ${health.status}`, 'success');
  } catch (error) {
    console.warn('⚠️ API connection failed:', error);
    addProgressEntry('API connection failed', 'error');
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  console.log('🤖 Analyst Agent TypeScript frontend starting (SDK-powered)...');
  
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
      const text = example.getAttribute('data-example') || example.textContent;
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
  
  // Set up dialect change handler
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
  
  // Test API connection using SDK
  testApiConnection();
  
  console.log('Frontend initialized successfully with TypeScript SDK');
});

// Make fillExample available globally for onclick handlers
(window as any).fillExample = fillExample;
