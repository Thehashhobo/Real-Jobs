"""
Tasks for job extraction and processing.
"""

from celery import current_task
from sqlalchemy.orm import sessionmaker
from scrapper.celery_app import celery_app
from scrapper.workflow import JobScrapingWorkflow
from app.models import Company, Job, CrawlLog, create_db_engine
from app.config import settings
from datetime import datetime
import logging
import hashlib

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def extract_company_jobs(self, company_id: str):
    """
    Extract jobs for a specific company using stored extraction rules.
    """
    engine = create_db_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")
        
        if not company.careers_url:
            raise ValueError(f"No careers URL for company {company.name}")
        
        # Create crawl log
        crawl_log = CrawlLog(
            company_id=company.id,
            crawl_type='extraction',
            status='running',
            started_at=datetime.utcnow()
        )
        db.add(crawl_log)
        db.commit()
        
        # Update task progress
        current_task.update_state(
            state='PROGRESS',
            meta={'step': 'extracting', 'company': company.name}
        )
        
        # Run extraction workflow
        workflow = JobScrapingWorkflow()
        result = workflow.run_crawl(
            company_name=company.name,
            company_domain=company.domain,
            careers_url=company.careers_url
        )
        
        jobs_new = 0
        jobs_updated = 0
        
        # Process extracted jobs
        for job_data in result.job_listings:
            # Create a hash for deduplication
            job_hash = hashlib.md5(
                f"{company.id}:{job_data.get('title', '')}:{job_data.get('location', '')}".encode()
            ).hexdigest()
            
            # Check if job already exists
            existing_job = db.query(Job).filter(
                Job.company_id == company.id,
                Job.external_id == job_hash
            ).first()
            
            if existing_job:
                # Update existing job
                existing_job.title = job_data.get('title', existing_job.title)
                existing_job.location = job_data.get('location', existing_job.location)
                existing_job.department = job_data.get('department', existing_job.department)
                existing_job.url = job_data.get('url', existing_job.url)
                existing_job.updated_at = datetime.utcnow()
                existing_job.raw_data = job_data
                jobs_updated += 1
            else:
                # Create new job
                new_job = Job(
                    company_id=company.id,
                    external_id=job_hash,
                    title=job_data.get('title', ''),
                    location=job_data.get('location', ''),
                    department=job_data.get('department', ''),
                    url=job_data.get('url', ''),
                    posted_date=datetime.utcnow(),
                    raw_data=job_data
                )
                db.add(new_job)
                jobs_new += 1
        
        # Update company last crawled
        company.last_crawled = datetime.utcnow()
        
        # Update crawl log
        crawl_log.status = 'success' if not result.error_message else 'failed'
        crawl_log.completed_at = datetime.utcnow()
        crawl_log.jobs_found = len(result.job_listings)
        crawl_log.jobs_new = jobs_new
        crawl_log.jobs_updated = jobs_updated
        crawl_log.error_message = result.error_message
        crawl_log.metadata = {
            'confidence_score': result.confidence_score,
            'extraction_rules': result.extraction_rules
        }
        
        db.commit()
        
        return {
            'company_id': str(company.id),
            'company_name': company.name,
            'jobs_found': len(result.job_listings),
            'jobs_new': jobs_new,
            'jobs_updated': jobs_updated,
            'confidence_score': result.confidence_score,
            'error_message': result.error_message
        }
        
    except Exception as e:
        logger.error(f"Job extraction failed for company {company_id}: {str(e)}")
        
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
def crawl_all_companies():
    """
    Crawl jobs from all active companies.
    """
    engine = create_db_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get all active companies with careers URLs
        companies = db.query(Company).filter(
            Company.is_active == True,
            Company.careers_url.isnot(None)
        ).all()
        
        results = []
        
        for company in companies:
            try:
                # Queue job extraction task
                result = extract_company_jobs.delay(str(company.id))
                results.append({
                    'company_id': str(company.id),
                    'company_name': company.name,
                    'task_id': result.id
                })
            except Exception as e:
                logger.error(f"Failed to queue extraction for {company.name}: {str(e)}")
                results.append({
                    'company_id': str(company.id),
                    'company_name': company.name,
                    'error': str(e)
                })
        
        return {
            'total_companies': len(companies),
            'queued_tasks': len([r for r in results if 'task_id' in r]),
            'results': results
        }
        
    finally:
        db.close()

@celery_app.task(bind=True)
def extract_job_details(self, job_id: str):
    """
    Extract detailed information for a specific job posting.
    """
    engine = create_db_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if not job.url:
            raise ValueError(f"No URL available for job {job.title}")
        
        # Update task progress
        current_task.update_state(
            state='PROGRESS',
            meta={'step': 'fetching_details', 'job_title': job.title}
        )
        
        # Here you would implement detailed job extraction
        # This could involve fetching the job detail page and extracting:
        # - Full job description
        # - Requirements
        # - Benefits
        # - Salary information
        # - Application deadline
        
        # For now, this is a placeholder
        logger.info(f"Job detail extraction for {job.title} - placeholder")
        
        return {
            'job_id': str(job.id),
            'job_title': job.title,
            'status': 'completed'
        }
        
    except Exception as e:
        logger.error(f"Job detail extraction failed for job {job_id}: {str(e)}")
        raise
        
    finally:
        db.close()