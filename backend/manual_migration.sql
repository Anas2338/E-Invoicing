-- Manual migration script for user approval fields
-- Run this against your PostgreSQL database if alembic is not available

-- Add account_status column with default 'pending'
ALTER TABLE users ADD COLUMN IF NOT EXISTS account_status VARCHAR NOT NULL DEFAULT 'pending';

-- Add approved_by column (UUID of admin who approved)
ALTER TABLE users ADD COLUMN IF NOT EXISTS approved_by UUID;

-- Add approved_at timestamp
ALTER TABLE users ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP;

-- Add rejection_reason column
ALTER TABLE users ADD COLUMN IF NOT EXISTS rejection_reason VARCHAR;

-- Create index on account_status for faster queries
CREATE INDEX IF NOT EXISTS ix_users_account_status ON users(account_status);

-- Update existing users to 'approved' status so they can continue using the system
UPDATE users SET account_status = 'approved' WHERE account_status = 'pending';

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('account_status', 'approved_by', 'approved_at', 'rejection_reason')
ORDER BY column_name;
