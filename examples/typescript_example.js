/**
 * Basic Node.js example using the TypeScript SDK
 * 
 * This demonstrates how to use the Analyst Agent from JavaScript/TypeScript
 */

const fs = require('fs');
const path = require('path');

// Simple client implementation (since we haven't built the SDK yet)
class SimpleAnalystClient {
  constructor(config) {
    this.baseUrl = config.baseUrl;
    this.apiKey = config.apiKey;
  }

  async healthCheck() {
    const response = await fetch(`${this.baseUrl}/v1/health`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
  }

  async ask(request) {
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

  async getJobStatus(jobId) {
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

  async waitForCompletion(jobId, options = {}) {
    const { interval = 2000, timeout = 300000, onProgress } = options;
    const startTime = Date.now();

    while (true) {
      const status = await this.getJobStatus(jobId);
      
      if (onProgress) {
        onProgress(status);
      }

      switch (status.status) {
        case 'completed':
          if (!status.result) {
            throw new Error('Job completed but no result available');
          }
          return status.result;

        case 'failed':
          throw new Error(status.result?.error_message || 'Analysis job failed');

        case 'cancelled':
          throw new Error('Analysis job was cancelled');

        case 'pending':
        case 'running':
          if (Date.now() - startTime > timeout) {
            throw new Error(`Job did not complete within ${timeout}ms timeout`);
          }
          
          await new Promise(resolve => setTimeout(resolve, interval));
          break;

        default:
          throw new Error(`Unknown job status: ${status.status}`);
      }
    }
  }
}

async function main() {
  console.log('🚀 Testing Analyst Agent TypeScript SDK');
  
  const client = new SimpleAnalystClient({
    baseUrl: 'http://localhost:8000'
  });

  try {
    // Test health check
    console.log('\n📋 Checking service health...');
    const health = await client.healthCheck();
    console.log('✅ Service is healthy:', health.status);

    // Create sample CSV data
    const sampleData = [
      'product,sales,month,region',
      'A,100,Jan,North',
      'B,150,Jan,South',
      'C,200,Jan,East',
      'A,110,Feb,North',
      'B,160,Feb,South',
      'C,210,Feb,East'
    ].join('\n');

    const csvPath = path.join(__dirname, 'sample_data.csv');
    fs.writeFileSync(csvPath, sampleData);
    console.log(`📊 Created sample data: ${csvPath}`);

    // Submit analysis request
    console.log('\n🔍 Submitting analysis request...');
    const request = {
      question: 'What are the sales trends by product and region?',
      data_source: {
        type: 'csv',
        file_path: path.resolve(csvPath)
      },
      preferences: {
        analysis_types: ['descriptive'],
        chart_types: ['bar', 'line'],
        include_code: false
      }
    };

    const response = await client.ask(request);
    console.log(`📝 Job submitted: ${response.job_id}`);

    // Wait for completion with progress updates
    console.log('\n⏳ Waiting for analysis...');
    const result = await client.waitForCompletion(response.job_id, {
      onProgress: (status) => {
        console.log(`   ${status.status}: ${status.current_step || 'Processing...'}`);
      }
    });

    // Display results
    console.log('\n✅ Analysis completed!');
    console.log(`📋 Summary: ${result.summary}`);
    console.log(`🔍 Insights: ${result.insights.length}`);
    console.log(`📊 Charts: ${result.charts.length}`);
    
    if (result.insights.length > 0) {
      console.log('\n💡 Key Insights:');
      result.insights.forEach((insight, i) => {
        console.log(`   ${i + 1}. ${insight.title}: ${insight.description}`);
      });
    }

  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

// Only run if this file is executed directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { SimpleAnalystClient }; 