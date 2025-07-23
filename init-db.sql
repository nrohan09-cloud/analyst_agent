-- Initialize the Analyst Agent database
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS analyst_agent;

-- Create tables for job tracking and results storage
CREATE TABLE IF NOT EXISTS analyst_agent.analysis_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    question TEXT NOT NULL,
    data_source JSONB NOT NULL,
    preferences JSONB,
    context JSONB,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create index for faster job lookups
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_job_id ON analyst_agent.analysis_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_status ON analyst_agent.analysis_jobs(status);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_created_at ON analyst_agent.analysis_jobs(created_at);

-- Create table for data source connections (encrypted)
CREATE TABLE IF NOT EXISTS analyst_agent.data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL, -- Encrypted connection details
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create table for analysis insights and results caching
CREATE TABLE IF NOT EXISTS analyst_agent.analysis_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key VARCHAR(500) NOT NULL UNIQUE,
    data_hash VARCHAR(64) NOT NULL,
    question_hash VARCHAR(64) NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Create index for cache lookups
CREATE INDEX IF NOT EXISTS idx_analysis_cache_key ON analyst_agent.analysis_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_analysis_cache_expires ON analyst_agent.analysis_cache(expires_at);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION analyst_agent.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_analysis_jobs_updated_at 
    BEFORE UPDATE ON analyst_agent.analysis_jobs
    FOR EACH ROW EXECUTE FUNCTION analyst_agent.update_updated_at_column();

CREATE TRIGGER update_data_sources_updated_at 
    BEFORE UPDATE ON analyst_agent.data_sources
    FOR EACH ROW EXECUTE FUNCTION analyst_agent.update_updated_at_column();

-- Insert sample data source configurations (for testing)
INSERT INTO analyst_agent.data_sources (name, type, config) VALUES 
('Sample CSV Data', 'csv', '{"description": "Sample sales data for testing"}'),
('Local SQLite', 'sqlite', '{"description": "Local SQLite database for development"}');

-- Grant permissions to the analyst user
GRANT USAGE ON SCHEMA analyst_agent TO analyst;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analyst_agent TO analyst;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analyst_agent TO analyst; 