-- Migration: Add comprehensive metrics to failover_test_events table
-- Date: 2025-12-20
-- Description: Adds fields for tracking snapshot type (full/incremental),
--              original GPU SSH info, and incremental snapshot metrics

-- Add snapshot metrics
ALTER TABLE failover_test_events
ADD COLUMN IF NOT EXISTS snapshot_type VARCHAR(20),
ADD COLUMN IF NOT EXISTS base_snapshot_id VARCHAR(200),
ADD COLUMN IF NOT EXISTS files_changed INTEGER;

-- Add original GPU SSH info
ALTER TABLE failover_test_events
ADD COLUMN IF NOT EXISTS original_ssh_host VARCHAR(100),
ADD COLUMN IF NOT EXISTS original_ssh_port INTEGER;

-- Add comments for documentation
COMMENT ON COLUMN failover_test_events.snapshot_type IS 'Type of snapshot: "full" or "incremental"';
COMMENT ON COLUMN failover_test_events.base_snapshot_id IS 'Base snapshot ID for incremental snapshots';
COMMENT ON COLUMN failover_test_events.files_changed IS 'Number of files changed in incremental snapshot';
COMMENT ON COLUMN failover_test_events.original_ssh_host IS 'SSH host of the original GPU before failover';
COMMENT ON COLUMN failover_test_events.original_ssh_port IS 'SSH port of the original GPU before failover';
