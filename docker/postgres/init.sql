-- PostgreSQL initialization script
-- Runs once when the Docker container is first created

-- Enable UUID generation extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create database if not exists (already created by POSTGRES_DB env var)
-- This script runs in the context of the dentist_db database
