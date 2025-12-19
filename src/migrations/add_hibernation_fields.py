"""
Database migration script to add new columns for hibernation tracking.

This adds:
- idle_timeout_seconds to instance_status
- last_snapshot_id to instance_status  
- dph_total, idle_hours, savings_usd to hibernation_events

Run with: python -m src.migrations.add_hibernation_fields
"""
import logging
from sqlalchemy import text, inspect
from src.config.database import engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Execute database migration to add new hibernation fields."""
    
    conn = engine.connect()
    inspector = inspect(engine)
    
    try:
        # Check if tables exist
        tables = inspector.get_table_names()
        
        if 'instance_status' in tables:
            columns = [c['name'] for c in inspector.get_columns('instance_status')]
            
            # Add idle_timeout_seconds if not exists
            if 'idle_timeout_seconds' not in columns:
                logger.info("Adding idle_timeout_seconds to instance_status...")
                conn.execute(text(
                    "ALTER TABLE instance_status ADD COLUMN idle_timeout_seconds INTEGER DEFAULT 180"
                ))
                conn.commit()
                logger.info("✓ Added idle_timeout_seconds")
            
            # Add last_snapshot_id if not exists
            if 'last_snapshot_id' not in columns:
                logger.info("Adding last_snapshot_id to instance_status...")
                conn.execute(text(
                    "ALTER TABLE instance_status ADD COLUMN last_snapshot_id VARCHAR(200)"
                ))
                conn.commit()
                logger.info("✓ Added last_snapshot_id")
        
        if 'hibernation_events' in tables:
            columns = [c['name'] for c in inspector.get_columns('hibernation_events')]
            
            # Add dph_total if not exists
            if 'dph_total' not in columns:
                logger.info("Adding dph_total to hibernation_events...")
                conn.execute(text(
                    "ALTER TABLE hibernation_events ADD COLUMN dph_total FLOAT"
                ))
                conn.commit()
                logger.info("✓ Added dph_total")
            
            # Add idle_hours if not exists
            if 'idle_hours' not in columns:
                logger.info("Adding idle_hours to hibernation_events...")
                conn.execute(text(
                    "ALTER TABLE hibernation_events ADD COLUMN idle_hours FLOAT"
                ))
                conn.commit()
                logger.info("✓ Added idle_hours")
            
            # Add savings_usd if not exists
            if 'savings_usd' not in columns:
                logger.info("Adding savings_usd to hibernation_events...")
                conn.execute(text(
                    "ALTER TABLE hibernation_events ADD COLUMN savings_usd FLOAT"
                ))
                conn.commit()
                logger.info("✓ Added savings_usd")
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
