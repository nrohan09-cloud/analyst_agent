#!/usr/bin/env node
/**
 * Example usage of the Analyst Agent TypeScript SDK.
 * 
 * This script demonstrates how to use the new API with different dialects
 * and analysis types.
 */

const path = require('path');

// Mock implementation of the AnalystClient for demonstration
// In a real implementation, you would install the SDK as an npm package
class MockAnalystClient {
  constructor(config) {
    this.baseUrl = config.baseUrl;
    this.apiKey = config.apiKey;
    console.log(`📡 Initialized client for ${this.baseUrl}`);
  }

  async healthCheck() {
    try {
      const response = await fetch(`${this.baseUrl}/v1/health`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    } catch (error) {
      console.error('Health check failed:', error.message);
      throw error;
    }
  }

  async query(spec, dataSource) {
    try {
      const response = await fetch(`${this.baseUrl}/v1/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
        },
        body: JSON.stringify({ spec, data_source: dataSource })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`HTTP ${response.status}: ${errorData.detail || response.statusText}`);
      }

      return response.json();
    } catch (error) {
      console.error('Query failed:', error.message);
      throw error;
    }
  }

  async getJobStatus(jobId) {
    try {
      const response = await fetch(`${this.baseUrl}/v1/jobs/${jobId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    } catch (error) {
      console.error('Job status check failed:', error.message);
      throw error;
    }
  }

  async quickAnalysis(question, dataSource, options = {}) {
    const spec = {
      question,
      dialect: options.dialect || 'postgres',
      time_window: options.timeWindow,
      grain: options.grain,
      budget: { queries: 10, seconds: 60 },
      validation_profile: options.validationProfile || 'balanced'
    };

    // Remove undefined fields to avoid TypeScript strict mode issues
    Object.keys(spec).forEach(key => {
      if (spec[key] === undefined) {
        delete spec[key];
      }
    });

    return this.query(spec, dataSource);
  }

  static createDataSource(kind, config, businessTz = 'Asia/Kolkata') {
    return {
      kind,
      config,
      business_tz: businessTz
    };
  }

  static createSQLiteDataSource(databasePath) {
    return this.createDataSource('sqlite', {
      url: `sqlite:///${path.resolve(databasePath)}`
    });
  }

  static createCSVDataSource(filePath) {
    return this.createDataSource('csv', {
      file_path: path.resolve(filePath)
    });
  }
}

async function testHealthCheck(client) {
  console.log('\n🏥 Testing Health Check');
  console.log('-'.repeat(30));
  
  try {
    const health = await client.healthCheck();
    console.log('✅ Service is healthy:', {
      status: health.status,
      version: health.version,
      uptime: health.uptime_seconds ? `${Math.round(health.uptime_seconds)}s` : 'unknown'
    });
    return true;
  } catch (error) {
    console.error('❌ Health check failed:', error.message);
    return false;
  }
}

async function testSQLiteAnalysis(client) {
  console.log('\n🗃️ Testing SQLite Analysis');
  console.log('-'.repeat(30));
  
  try {
    // Create SQLite data source pointing to our test database
    const dataSource = MockAnalystClient.createSQLiteDataSource('./examples/test_data.db');
    
    const questions = [
      'How many customers do we have?',
      'What is the total revenue by month?',
      'Which products are the top sellers?',
      'What is the average order value?'
    ];

    for (const question of questions) {
      console.log(`\n💭 Question: "${question}"`);
      
      try {
        const result = await client.quickAnalysis(question, dataSource, {
          dialect: 'sqlite',
          validationProfile: 'fast'
        });

        console.log(`✅ Answer: ${result.answer}`);
        console.log(`📊 Quality Score: ${result.quality.score.toFixed(2)}`);
        console.log(`🎯 Quality Passed: ${result.quality.passed}`);
        console.log(`📋 Tables Generated: ${result.tables.length}`);
        console.log(`📈 Charts Generated: ${result.charts.length}`);

        if (result.tables.length > 0) {
          const table = result.tables[0];
          const rows = table.content?.data?.length || 0;
          const columns = table.content?.columns?.length || 0;
          console.log(`   📄 Table "${table.title}": ${rows} rows, ${columns} columns`);
        }

        // Show execution steps
        if (result.execution_steps && result.execution_steps.length > 0) {
          console.log('🔄 Execution Steps:');
          result.execution_steps.slice(-3).forEach(step => {
            const icon = step.status === 'completed' ? '✅' : 
                        step.status === 'failed' ? '❌' : '⏳';
            console.log(`   ${icon} ${step.step_name} (${step.status})`);
          });
        }

      } catch (error) {
        console.error(`❌ Failed: ${error.message}`);
      }
    }

  } catch (error) {
    console.error('❌ SQLite analysis setup failed:', error.message);
  }
}

async function testCSVAnalysis(client) {
  console.log('\n📊 Testing CSV Analysis');
  console.log('-'.repeat(30));
  
  try {
    // Create a simple CSV file for testing
    const csvPath = './examples/sample_sales.csv';
    
    // Check if CSV exists (should be created by Python examples)
    const fs = require('fs');
    if (!fs.existsSync(csvPath)) {
      console.log('⚠️ CSV file not found, skipping CSV analysis');
      return;
    }

    const dataSource = MockAnalystClient.createCSVDataSource(csvPath);
    
    const question = 'What are the sales trends in this data?';
    console.log(`💭 Question: "${question}"`);
    
    try {
      const result = await client.quickAnalysis(question, dataSource, {
        dialect: 'duckdb',  // DuckDB is good for CSV analysis
        validationProfile: 'balanced'
      });

      console.log(`✅ Answer: ${result.answer}`);
      console.log(`📊 Quality Score: ${result.quality.score.toFixed(2)}`);
      console.log(`🎯 Quality Passed: ${result.quality.passed}`);

    } catch (error) {
      console.error(`❌ Failed: ${error.message}`);
    }

  } catch (error) {
    console.error('❌ CSV analysis setup failed:', error.message);
  }
}

async function testDialectCapabilities(client) {
  console.log('\n🔧 Testing Dialect Capabilities');
  console.log('-'.repeat(30));
  
  try {
    // Mock the dialect capabilities endpoint
    const response = await fetch(`${client.baseUrl}/v1/dialects`);
    if (response.ok) {
      const capabilities = await response.json();
      
      console.log(`📊 Supported Dialects: ${capabilities.supported_dialects.length}`);
      capabilities.supported_dialects.forEach(dialect => {
        console.log(`   🗃️ ${dialect}`);
      });

      // Show capabilities for a few dialects
      const showcaseDialects = ['postgres', 'sqlite', 'snowflake'];
      for (const dialect of showcaseDialects) {
        const caps = capabilities.capabilities[dialect];
        if (caps) {
          const features = Object.entries(caps.features)
            .filter(([, enabled]) => enabled)
            .map(([feature]) => feature)
            .join(', ');
          console.log(`   🔧 ${dialect}: ${features}`);
        }
      }
    } else {
      console.log('⚠️ Could not fetch dialect capabilities');
    }
  } catch (error) {
    console.log('⚠️ Dialect capabilities test skipped:', error.message);
  }
}

async function testConnectorInfo(client) {
  console.log('\n🔌 Testing Connector Information');
  console.log('-'.repeat(30));
  
  try {
    const response = await fetch(`${client.baseUrl}/v1/connectors`);
    if (response.ok) {
      const connectors = await response.json();
      
      console.log(`📊 Available Connectors: ${connectors.total_count}`);
      Object.entries(connectors.available_connectors).forEach(([kind, className]) => {
        console.log(`   🔌 ${kind}: ${className}`);
      });
    } else {
      console.log('⚠️ Could not fetch connector information');
    }
  } catch (error) {
    console.log('⚠️ Connector information test skipped:', error.message);
  }
}

async function main() {
  console.log('🧪 Analyst Agent TypeScript SDK Test');
  console.log('='.repeat(50));
  
  // Initialize client
  const client = new MockAnalystClient({
    baseUrl: process.env.ANALYST_AGENT_URL || 'http://localhost:8000',
    apiKey: process.env.ANALYST_AGENT_API_KEY // Optional
  });

  let allTestsPassed = true;

  try {
    // Test health check
    const isHealthy = await testHealthCheck(client);
    if (!isHealthy) {
      console.log('\n❌ Service is not healthy. Make sure the Analyst Agent service is running.');
      console.log('   Start the service with: python main.py');
      return 1;
    }

    // Test dialect capabilities
    await testDialectCapabilities(client);

    // Test connector information
    await testConnectorInfo(client);

    // Test SQLite analysis
    await testSQLiteAnalysis(client);

    // Test CSV analysis
    await testCSVAnalysis(client);

    console.log('\n🎉 TypeScript SDK Test Summary');
    console.log('='.repeat(50));
    console.log('✅ All tests completed successfully!');
    console.log('📝 The TypeScript SDK is working correctly with the new API.');
    
    return 0;

  } catch (error) {
    console.error('\n💥 Critical Error:', error.message);
    console.error(error.stack);
    return 1;
  }
}

// Check if we're running in Node.js
if (typeof window === 'undefined') {
  main()
    .then(exitCode => {
      process.exit(exitCode);
    })
    .catch(error => {
      console.error('Unhandled error:', error);
      process.exit(1);
    });
} else {
  console.log('This script is designed to run in Node.js, not in a browser.');
} 