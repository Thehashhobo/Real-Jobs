"""
Tasks for verifying and improving extraction rules.
"""

from celery import current_task
from sqlalchemy.orm import sessionmaker
from scrapper.celery_app import celery_app
from scrapper.workflow import JobScrapingWorkflow
from app.models import Company, ExtractionRule, create_db_engine
from app.config import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def verify_extraction_rules(self, company_id: str = None):
    """
    Verify and update extraction rules for companies.
    """
    engine = create_db_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get companies to verify
        if company_id:
            companies = db.query(Company).filter(Company.id == company_id).all()
        else:
            # Verify companies that haven't been checked in the last 7 days
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            companies = db.query(Company).filter(
                Company.is_active == True,
                Company.careers_url.isnot(None),
                (Company.last_crawled.is_(None) | (Company.last_crawled < cutoff_date))
            ).limit(10).all()  # Limit to avoid overloading
        
        results = []
        
        for company in companies:
            try:
                # Update task progress
                current_task.update_state(
                    state='PROGRESS',
                    meta={'step': 'verifying', 'company': company.name}
                )
                
                # Run verification workflow
                workflow = JobScrapingWorkflow()
                result = workflow.run_crawl(
                    company_name=company.name,
                    company_domain=company.domain,
                    careers_url=company.careers_url
                )
                
                # Calculate success metrics
                jobs_extracted = len(result.job_listings)
                confidence_score = result.confidence_score
                
                # Update or create extraction rule
                if result.extraction_rules:
                    existing_rule = db.query(ExtractionRule).filter(
                        ExtractionRule.company_id == company.id,
                        ExtractionRule.rule_type == 'job_list'
                    ).first()
                    
                    if existing_rule:
                        # Update existing rule
                        existing_rule.selectors = result.extraction_rules
                        existing_rule.confidence_score = confidence_score
                        existing_rule.last_verified = datetime.utcnow()
                        
                        # Update success rate based on extraction results
                        if jobs_extracted > 0:
                            # Weighted average with previous success rate
                            old_rate = existing_rule.success_rate or 0.0
                            new_rate = min(confidence_score, 1.0)
                            existing_rule.success_rate = (old_rate * 0.7) + (new_rate * 0.3)
                        
                    else:
                        # Create new rule
                        new_rule = ExtractionRule(
                            company_id=company.id,
                            site_pattern=company.careers_url,
                            rule_type='job_list',
                            selectors=result.extraction_rules,
                            confidence_score=confidence_score,
                            success_rate=min(confidence_score, 1.0),
                            last_verified=datetime.utcnow()
                        )
                        db.add(new_rule)
                
                # Update company extraction rules cache
                company.extraction_rules = result.extraction_rules
                company.last_crawled = datetime.utcnow()
                
                results.append({
                    'company_id': str(company.id),
                    'company_name': company.name,
                    'jobs_extracted': jobs_extracted,
                    'confidence_score': confidence_score,
                    'status': 'success' if not result.error_message else 'failed',
                    'error_message': result.error_message
                })
                
            except Exception as e:
                logger.error(f"Verification failed for {company.name}: {str(e)}")
                results.append({
                    'company_id': str(company.id),
                    'company_name': company.name,
                    'status': 'error',
                    'error_message': str(e)
                })
        
        db.commit()
        
        return {
            'companies_verified': len(results),
            'successful_verifications': len([r for r in results if r['status'] == 'success']),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Batch verification failed: {str(e)}")
        raise
        
    finally:
        db.close()

@celery_app.task(bind=True)
def improve_extraction_rules(self, company_id: str):
    """
    Use LLM to improve extraction rules based on recent performance.
    """
    engine = create_db_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")
        
        # Get current extraction rules
        current_rules = db.query(ExtractionRule).filter(
            ExtractionRule.company_id == company.id,
            ExtractionRule.is_active == True
        ).all()
        
        if not current_rules:
            logger.info(f"No existing rules to improve for {company.name}")
            return {'status': 'no_rules_to_improve'}
        
        # Update task progress
        current_task.update_state(
            state='PROGRESS',
            meta={'step': 'improving_rules', 'company': company.name}
        )
        
        # Run workflow to generate new rules
        workflow = JobScrapingWorkflow()
        result = workflow.run_crawl(
            company_name=company.name,
            company_domain=company.domain,
            careers_url=company.careers_url
        )
        
        # Compare performance with existing rules
        new_confidence = result.confidence_score
        best_existing_confidence = max(rule.confidence_score for rule in current_rules)
        
        if new_confidence > best_existing_confidence * 1.1:  # 10% improvement threshold
            # Deactivate old rules
            for rule in current_rules:
                rule.is_active = False
            
            # Create new improved rule
            improved_rule = ExtractionRule(
                company_id=company.id,
                site_pattern=company.careers_url,
                rule_type='job_list',
                selectors=result.extraction_rules,
                confidence_score=new_confidence,
                success_rate=new_confidence,
                last_verified=datetime.utcnow()
            )
            db.add(improved_rule)
            
            # Update company cache
            company.extraction_rules = result.extraction_rules
            
            db.commit()
            
            return {
                'company_id': str(company.id),
                'company_name': company.name,
                'status': 'improved',
                'old_confidence': best_existing_confidence,
                'new_confidence': new_confidence,
                'jobs_extracted': len(result.job_listings)
            }
        else:
            return {
                'company_id': str(company.id),
                'company_name': company.name,
                'status': 'no_improvement',
                'current_confidence': best_existing_confidence,
                'new_confidence': new_confidence
            }
        
    except Exception as e:
        logger.error(f"Rule improvement failed for company {company_id}: {str(e)}")
        raise
        
    finally:
        db.close()

@celery_app.task
def cleanup_old_extraction_rules():
    """
    Clean up old, unused extraction rules to keep the database tidy.
    """
    engine = create_db_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Delete rules older than 90 days that are inactive
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        old_rules = db.query(ExtractionRule).filter(
            ExtractionRule.is_active == False,
            ExtractionRule.last_verified < cutoff_date
        ).all()
        
        deleted_count = len(old_rules)
        
        for rule in old_rules:
            db.delete(rule)
        
        db.commit()
        
        return {
            'status': 'completed',
            'rules_deleted': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise
        
    finally:
        db.close()