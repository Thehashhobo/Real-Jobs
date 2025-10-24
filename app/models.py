"""
Core models for the Real-Jobs application using SQLAlchemy ORM.
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

Base = declarative_base()

class Company(Base):
    """Model for company information."""
    __tablename__ = 'companies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    domain = Column(String(255), unique=True)
    careers_url = Column(String(500))
    ats_provider = Column(String(100))  # e.g., 'workday', 'greenhouse', 'lever'
    extraction_rules = Column(JSONB)  # Cached extraction rules for this company
    last_crawled = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    jobs = relationship("Job", back_populates="company")
    crawl_logs = relationship("CrawlLog", back_populates="company")
    
    # Indexes
    __table_args__ = (
        Index('idx_company_domain', domain),
        Index('idx_company_name', name),
    )

class Job(Base):
    """Model for job postings."""
    __tablename__ = 'jobs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    external_id = Column(String(255))  # Company's internal job ID
    title = Column(String(255), nullable=False)
    department = Column(String(255))
    location = Column(String(255))
    remote_type = Column(String(50))  # 'remote', 'hybrid', 'onsite'
    employment_type = Column(String(50))  # 'full-time', 'part-time', 'contract'
    experience_level = Column(String(50))  # 'entry', 'mid', 'senior', 'executive'
    description = Column(Text)
    requirements = Column(Text)
    benefits = Column(Text)
    salary_min = Column(Float)
    salary_max = Column(Float)
    currency = Column(String(3))  # ISO currency code
    url = Column(String(500))
    posted_date = Column(DateTime)
    expires_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    raw_data = Column(JSONB)  # Store original scraped data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="jobs")
    
    # Indexes
    __table_args__ = (
        Index('idx_job_company_id', company_id),
        Index('idx_job_title', title),
        Index('idx_job_location', location),
        Index('idx_job_posted_date', posted_date),
        Index('idx_job_external_id', external_id),
    )

class CrawlLog(Base):
    """Model for tracking crawl activities and results."""
    __tablename__ = 'crawl_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    crawl_type = Column(String(50), nullable=False)  # 'discovery', 'extraction', 'verification'
    status = Column(String(20), nullable=False)  # 'pending', 'running', 'success', 'failed'
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    jobs_found = Column(Integer, default=0)
    jobs_new = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    error_message = Column(Text)
    metadata = Column(JSONB)  # Store additional crawl information
    
    # Relationships
    company = relationship("Company", back_populates="crawl_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_crawl_log_company_id', company_id),
        Index('idx_crawl_log_status', status),
        Index('idx_crawl_log_started_at', started_at),
    )

class ExtractionRule(Base):
    """Model for storing LLM-generated extraction rules."""
    __tablename__ = 'extraction_rules'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'))
    site_pattern = Column(String(255))  # URL pattern this rule applies to
    rule_type = Column(String(50), nullable=False)  # 'job_list', 'job_detail', 'pagination'
    selectors = Column(JSONB, nullable=False)  # CSS/XPath selectors
    confidence_score = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)  # Track how often this rule works
    last_verified = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_extraction_rule_company_id', company_id),
        Index('idx_extraction_rule_pattern', site_pattern),
    )

# Database connection and session management
def create_db_engine(database_url: str):
    """Create database engine."""
    return create_engine(database_url, echo=False)

def create_session_factory(engine):
    """Create session factory."""
    return sessionmaker(bind=engine)

def init_database(engine):
    """Initialize database tables."""
    Base.metadata.create_all(engine)