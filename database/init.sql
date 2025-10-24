-- Database initialization script for Real-Jobs
-- This script runs automatically when PostgreSQL container starts

-- Enable UUID extension for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Note: Table schemas are created by SQLAlchemy in the application
-- This script only handles database-level optimizations

-- Create indexes for better performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_domain ON companies(domain);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_name ON companies(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_company_id ON jobs(company_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_title ON jobs(title);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_location ON jobs(location);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_posted_date ON jobs(posted_date);

-- Create full-text search indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_title_fts ON jobs USING gin(to_tsvector('english', title));
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_description_fts ON jobs USING gin(to_tsvector('english', description));

-- Create composite indexes for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_active_posted ON jobs(is_active, posted_date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_crawl_logs_company_status ON crawl_logs(company_id, status, started_at DESC);