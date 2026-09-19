-- Database initialization script for PostgreSQL
-- This runs automatically when the postgres container starts for the first time

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The tables will be created by SQLAlchemy via the backend on startup
-- This script just ensures the database exists and is ready
-- Additional initialization can be added here if needed