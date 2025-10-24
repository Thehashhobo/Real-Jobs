"""
Task for discovering company careers pages.
"""

from celery import current_task
from sqlalchemy.orm import sessionmaker
from scrapper.celery_app import celery_app
from scrapper.workflow import JobScrapingWorkflow
from app.models import Company, CrawlLog, create_db_engine
from app.config import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def discover_company_careers_page(self, company_name: str, company_domain: str = None):
    """
    Discover careers page for a given company.
    """
    # Database setup
    engine = create_db_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if company already exists
        company = db.query(Company).filter(Company.name == company_name).first()
        if not company:
            company = Company(
                name=company_name,
                domain=company_domain
            )
            db.add(company)
            db.commit()
            db.refresh(company)
        
        # Create crawl log
        crawl_log = CrawlLog(
            company_id=company.id,
            crawl_type='discovery',
            status='running',
            started_at=datetime.utcnow()
        )
        db.add(crawl_log)
        db.commit()
        
        # Run discovery workflow
        workflow = JobScrapingWorkflow()
        
        # Update task progress
        current_task.update_state(
            state='PROGRESS',
            meta={'step': 'discovering', 'company': company_name}
        )
        
        result = workflow.run_crawl(company_name, company_domain)
        
        # Update company with discovered information
        if result.careers_url:
            company.careers_url = result.careers_url
            company.last_crawled = datetime.utcnow()
        
        if result.extraction_rules:
            company.extraction_rules = result.extraction_rules
        
        # Update crawl log
        crawl_log.status = 'success' if not result.error_message else 'failed'
        crawl_log.completed_at = datetime.utcnow()
        crawl_log.error_message = result.error_message
        crawl_log.metadata = {
            'careers_url': result.careers_url,
            'confidence_score': result.confidence_score,
            'jobs_found': len(result.job_listings)
        }
        
        db.commit()
        
        return {
            'company_id': str(company.id),
            'careers_url': result.careers_url,
            'jobs_found': len(result.job_listings),
            'confidence_score': result.confidence_score,
            'error_message': result.error_message
        }
        
    except Exception as e:
        logger.error(f"Discovery failed for {company_name}: {str(e)}")
        
        # Update crawl log with error
        if 'crawl_log' in locals():
            crawl_log.status = 'failed'
            crawl_log.completed_at = datetime.utcnow()
            crawl_log.error_message = str(e)
            db.commit()
        
        raise
        
    finally:
        db.close()

@celery_app.task
def discover_company_careers_pages():
    """
    Batch task to discover careers pages for multiple companies.
    """
    # This would be called from a list of target companies
    companies_to_discover = [
        {"name": "Google", "domain": "google.com"},
        {"name": "Microsoft", "domain": "microsoft.com"},
        {"name": "Apple", "domain": "apple.com"},
        # Add more companies as needed
    ]
    
    results = []
    for company in companies_to_discover:
        try:
            result = discover_company_careers_page.delay(
                company["name"], 
                company.get("domain")
            )
            results.append({
                'company': company["name"],
                'task_id': result.id
            })
        except Exception as e:
            logger.error(f"Failed to queue discovery for {company['name']}: {str(e)}")
            results.append({
                'company': company["name"],
                'error': str(e)
            })
    
    return results