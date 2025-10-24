"""
Celery configuration and task definitions for the Real-Jobs scraper.
"""

from celery import Celery
from celery.schedules import crontab
from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "real_jobs_scraper",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "scrapper.tasks.discovery",
        "scrapper.tasks.extraction",
        "scrapper.tasks.verification",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "scrapper.tasks.discovery.*": {"queue": "discovery"},
        "scrapper.tasks.extraction.*": {"queue": "extraction"},
        "scrapper.tasks.verification.*": {"queue": "verification"},
    },
    beat_schedule={
        "discover-companies": {
            "task": "scrapper.tasks.discovery.discover_company_careers_pages",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        },
        "crawl-jobs": {
            "task": "scrapper.tasks.extraction.crawl_all_companies",
            "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
        },
        "verify-rules": {
            "task": "scrapper.tasks.verification.verify_extraction_rules",
            "schedule": crontab(hour=22, minute=0),  # Daily at 10 PM
        },
    },
)