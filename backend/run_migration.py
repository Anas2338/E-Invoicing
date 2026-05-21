"""One-off migration: add reset_pin_hash and reset_pin_expires_at to users table."""
from src.database.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_pin_hash VARCHAR'))
    conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_pin_expires_at TIMESTAMPTZ'))
    conn.commit()
    print('Columns added successfully')
