"""
Database initialization and management utilities.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, init_database
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def initialize_database():
    """
    Initialize the database with all tables and initial data.
    This should be run once when setting up the application.
    """
    try:
        # Create database engine
        engine = create_engine(settings.database_url, echo=settings.debug)
        
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        
        # Run any additional initialization
        init_database(engine)
        
        logger.info("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False

def get_database_session():
    """
    Get a database session for use in the application.
    """
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

if __name__ == "__main__":
    # Allow running this script directly to initialize the database
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Initializing Real-Jobs database...")
    success = initialize_database()
    
    if success:
        print("✅ Database initialization completed successfully!")
        sys.exit(0)
    else:
        print("❌ Database initialization failed!")
        sys.exit(1)