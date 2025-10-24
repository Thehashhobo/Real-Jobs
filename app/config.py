"""
Configuration management for the Real-Jobs application.
"""

from typing import Optional
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/real_jobs",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_RESULT_BACKEND"
    )
    
    # OpenSearch
    opensearch_host: str = Field(
        default="localhost",
        env="OPENSEARCH_HOST"
    )
    opensearch_port: int = Field(
        default=9200,
        env="OPENSEARCH_PORT"
    )
    opensearch_use_ssl: bool = Field(
        default=False,
        env="OPENSEARCH_USE_SSL"
    )
    opensearch_verify_certs: bool = Field(
        default=False,
        env="OPENSEARCH_VERIFY_CERTS"
    )
    
    # Object Storage (S3/MinIO)
    s3_endpoint_url: Optional[str] = Field(
        default="http://localhost:9000",
        env="S3_ENDPOINT_URL"
    )
    s3_access_key: str = Field(
        default="minioadmin",
        env="S3_ACCESS_KEY"
    )
    s3_secret_key: str = Field(
        default="minioadmin",
        env="S3_SECRET_KEY"
    )
    s3_bucket_name: str = Field(
        default="real-jobs-storage",
        env="S3_BUCKET_NAME"
    )
    
    # OpenAI
    openai_api_key: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY"
    )
    openai_model: str = Field(
        default="gpt-4",
        env="OPENAI_MODEL"
    )
    
    # Scraping
    default_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        env="USER_AGENT"
    )
    request_timeout: int = Field(
        default=30,
        env="REQUEST_TIMEOUT"
    )
    max_retries: int = Field(
        default=3,
        env="MAX_RETRIES"
    )
    concurrent_crawls: int = Field(
        default=5,
        env="CONCURRENT_CRAWLS"
    )
    
    # Rate limiting
    requests_per_second: float = Field(
        default=1.0,
        env="REQUESTS_PER_SECOND"
    )
    
    # Application
    debug: bool = Field(
        default=False,
        env="DEBUG"
    )
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()