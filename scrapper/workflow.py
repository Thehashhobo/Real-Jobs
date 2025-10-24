"""
LangGraph workflow for intelligent job scraping.
"""

from typing import Dict, List, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import httpx
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse
from app.config import settings

class CrawlState(BaseModel):
    """State for the crawling workflow."""
    company_name: str
    company_domain: Optional[str] = None
    careers_url: Optional[str] = None
    html_content: Optional[str] = None
    job_listings: List[Dict[str, Any]] = Field(default_factory=list)
    extraction_rules: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    confidence_score: float = 0.0
    step: str = "start"

class JobScrapingWorkflow:
    """LangGraph workflow for intelligent job scraping."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.1
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(CrawlState)
        
        # Add nodes
        workflow.add_node("discover_careers_page", self.discover_careers_page)
        workflow.add_node("fetch_content", self.fetch_content)
        workflow.add_node("analyze_structure", self.analyze_structure)
        workflow.add_node("generate_extraction_rules", self.generate_extraction_rules)
        workflow.add_node("extract_jobs", self.extract_jobs)
        workflow.add_node("validate_extraction", self.validate_extraction)
        
        # Set entry point
        workflow.set_entry_point("discover_careers_page")
        
        # Add edges
        workflow.add_edge("discover_careers_page", "fetch_content")
        workflow.add_edge("fetch_content", "analyze_structure")
        workflow.add_edge("analyze_structure", "generate_extraction_rules")
        workflow.add_edge("generate_extraction_rules", "extract_jobs")
        workflow.add_edge("extract_jobs", "validate_extraction")
        workflow.add_edge("validate_extraction", END)
        
        return workflow.compile()
    
    def discover_careers_page(self, state: CrawlState) -> CrawlState:
        """Discover the careers page for a company."""
        try:
            if state.careers_url:
                return state
            
            # Try common patterns
            if state.company_domain:
                common_paths = [
                    "/careers",
                    "/jobs",
                    "/work-with-us",
                    "/join-us",
                    "/opportunities"
                ]
                
                for path in common_paths:
                    potential_url = f"https://{state.company_domain}{path}"
                    
                    try:
                        response = httpx.get(potential_url, timeout=10)
                        if response.status_code == 200:
                            state.careers_url = potential_url
                            break
                    except:
                        continue
            
            # If still no URL found, use LLM to help discover
            if not state.careers_url:
                state = self._llm_discover_careers_url(state)
            
            state.step = "discover_complete"
            return state
            
        except Exception as e:
            state.error_message = f"Discovery failed: {str(e)}"
            return state
    
    def fetch_content(self, state: CrawlState) -> CrawlState:
        """Fetch HTML content from the careers page."""
        try:
            if not state.careers_url:
                state.error_message = "No careers URL found"
                return state
            
            headers = {
                "User-Agent": settings.default_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
            
            response = httpx.get(
                state.careers_url,
                headers=headers,
                timeout=settings.request_timeout,
                follow_redirects=True
            )
            response.raise_for_status()
            
            state.html_content = response.text
            state.step = "fetch_complete"
            return state
            
        except Exception as e:
            state.error_message = f"Fetch failed: {str(e)}"
            return state
    
    def analyze_structure(self, state: CrawlState) -> CrawlState:
        """Analyze the HTML structure to understand the site layout."""
        try:
            if not state.html_content:
                state.error_message = "No HTML content to analyze"
                return state
            
            soup = BeautifulSoup(state.html_content, 'html.parser')
            
            # Look for common job listing patterns
            job_containers = []
            
            # Common selectors for job listings
            selectors = [
                "[class*='job']",
                "[class*='position']",
                "[class*='opening']",
                "[data-testid*='job']",
                ".career-listing",
                ".job-listing",
                ".position-listing"
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    job_containers.extend(elements)
            
            # Store analysis results
            state.extraction_rules = {
                "potential_job_containers": len(job_containers),
                "page_structure": {
                    "has_pagination": bool(soup.find(text=re.compile(r'next|more|page', re.I))),
                    "has_filters": bool(soup.select("[class*='filter'], [class*='search']")),
                    "total_links": len(soup.find_all('a'))
                }
            }
            
            state.step = "analyze_complete"
            return state
            
        except Exception as e:
            state.error_message = f"Analysis failed: {str(e)}"
            return state
    
    def generate_extraction_rules(self, state: CrawlState) -> CrawlState:
        """Use LLM to generate CSS/XPath selectors for job extraction."""
        try:
            # Prepare a clean sample of the HTML for the LLM
            soup = BeautifulSoup(state.html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get a manageable sample of the HTML
            html_sample = str(soup)[:8000]  # Limit to avoid token limits
            
            prompt = ChatPromptTemplate.from_template("""
            You are an expert web scraper. Analyze the following HTML from a company careers page and generate CSS selectors to extract job listings.

            Company: {company_name}
            URL: {careers_url}

            HTML Sample:
            {html_sample}

            Please provide a JSON response with the following structure:
            {{
                "job_list_selector": "CSS selector for the container holding all jobs",
                "job_item_selector": "CSS selector for individual job items",
                "title_selector": "CSS selector for job title (relative to job item)",
                "location_selector": "CSS selector for job location (relative to job item)",
                "department_selector": "CSS selector for department (relative to job item)",
                "link_selector": "CSS selector for job detail link (relative to job item)",
                "confidence_score": 0.8,
                "notes": "Any additional observations"
            }}

            Focus on finding reliable, specific selectors that uniquely identify job-related elements.
            """)
            
            response = self.llm.invoke(prompt.format_messages(
                company_name=state.company_name,
                careers_url=state.careers_url,
                html_sample=html_sample
            ))
            
            try:
                # Extract JSON from response
                content = response.content
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    rules = json.loads(json_match.group())
                    state.extraction_rules = rules
                    state.confidence_score = rules.get('confidence_score', 0.5)
            except json.JSONDecodeError:
                state.error_message = "Failed to parse LLM response as JSON"
                return state
            
            state.step = "rules_generated"
            return state
            
        except Exception as e:
            state.error_message = f"Rule generation failed: {str(e)}"
            return state
    
    def extract_jobs(self, state: CrawlState) -> CrawlState:
        """Extract job listings using the generated rules."""
        try:
            if not state.extraction_rules or not state.html_content:
                state.error_message = "Missing extraction rules or content"
                return state
            
            soup = BeautifulSoup(state.html_content, 'html.parser')
            rules = state.extraction_rules
            
            jobs = []
            
            # Find job containers
            if 'job_item_selector' in rules:
                job_elements = soup.select(rules['job_item_selector'])
                
                for job_element in job_elements:
                    job_data = {}
                    
                    # Extract title
                    if 'title_selector' in rules:
                        title_elem = job_element.select_one(rules['title_selector'])
                        if title_elem:
                            job_data['title'] = title_elem.get_text(strip=True)
                    
                    # Extract location
                    if 'location_selector' in rules:
                        location_elem = job_element.select_one(rules['location_selector'])
                        if location_elem:
                            job_data['location'] = location_elem.get_text(strip=True)
                    
                    # Extract department
                    if 'department_selector' in rules:
                        dept_elem = job_element.select_one(rules['department_selector'])
                        if dept_elem:
                            job_data['department'] = dept_elem.get_text(strip=True)
                    
                    # Extract link
                    if 'link_selector' in rules:
                        link_elem = job_element.select_one(rules['link_selector'])
                        if link_elem and link_elem.get('href'):
                            job_data['url'] = urljoin(state.careers_url, link_elem['href'])
                    
                    if job_data.get('title'):  # Only add if we found a title
                        jobs.append(job_data)
            
            state.job_listings = jobs
            state.step = "extraction_complete"
            return state
            
        except Exception as e:
            state.error_message = f"Extraction failed: {str(e)}"
            return state
    
    def validate_extraction(self, state: CrawlState) -> CrawlState:
        """Validate the extracted job data and adjust confidence score."""
        try:
            jobs = state.job_listings
            
            if not jobs:
                state.confidence_score = 0.0
                state.error_message = "No jobs extracted"
                return state
            
            # Calculate quality metrics
            has_title = sum(1 for job in jobs if job.get('title'))
            has_location = sum(1 for job in jobs if job.get('location'))
            has_url = sum(1 for job in jobs if job.get('url'))
            
            total_jobs = len(jobs)
            
            # Adjust confidence based on extraction quality
            quality_score = (
                (has_title / total_jobs) * 0.5 +  # Titles are essential
                (has_location / total_jobs) * 0.3 +  # Locations are important
                (has_url / total_jobs) * 0.2  # URLs are nice to have
            )
            
            state.confidence_score = min(state.confidence_score * quality_score, 1.0)
            
            # Filter out jobs with no title (likely false positives)
            state.job_listings = [job for job in jobs if job.get('title')]
            
            state.step = "validation_complete"
            return state
            
        except Exception as e:
            state.error_message = f"Validation failed: {str(e)}"
            return state
    
    def _llm_discover_careers_url(self, state: CrawlState) -> CrawlState:
        """Use LLM to help discover careers page URL."""
        prompt = ChatPromptTemplate.from_template("""
        Given the company name "{company_name}" and domain "{company_domain}", 
        what are the most likely URLs for their careers page?
        
        Provide 3-5 potential URLs in order of likelihood.
        Format as a simple list, one URL per line.
        """)
        
        try:
            response = self.llm.invoke(prompt.format_messages(
                company_name=state.company_name,
                company_domain=state.company_domain or "unknown"
            ))
            
            # Extract URLs from response and test them
            urls = [line.strip() for line in response.content.split('\n') if line.strip().startswith('http')]
            
            for url in urls[:3]:  # Test top 3 suggestions
                try:
                    test_response = httpx.head(url, timeout=5)
                    if test_response.status_code == 200:
                        state.careers_url = url
                        break
                except:
                    continue
                    
        except Exception:
            pass  # If LLM discovery fails, we'll handle it gracefully
        
        return state
    
    def run_crawl(self, company_name: str, company_domain: str = None, careers_url: str = None) -> CrawlState:
        """Run the complete crawling workflow."""
        initial_state = CrawlState(
            company_name=company_name,
            company_domain=company_domain,
            careers_url=careers_url
        )
        
        result = self.graph.invoke(initial_state)
        return result