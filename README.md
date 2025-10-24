# Real-Jobs: AI-Assisted Job Scraper Platform

A scalable job aggregation system that automatically collects and normalizes job postings directly from company career pages using AI-powered extraction and modern workflow orchestration.

## 🏗️ Architecture Overview

This system combines **agentic automation**, **modern workflow orchestration**, and **robust data storage** to create a continuously updating dataset of job opportunities.

### Key Components

- **LangGraph Workflow**: Intelligent, LLM-driven decision-making for detecting site structures and generating extraction rules
- **Celery Task Queue**: Distributed task management with automatic retries and parallel processing  
- **PostgreSQL**: Main transactional database for structured job and company data
- **OpenSearch**: Full-text search index for fast querying and filtering
- **Redis**: Caching, rate limiting, and task queuing
- **MinIO/S3**: Object storage for raw HTML snapshots and artifacts

## 🚀 Tech Stack

- **Backend**: Python + FastAPI
- **Task Queue**: Celery + Redis
- **AI/ML**: LangGraph + OpenAI
- **Database**: PostgreSQL + OpenSearch  
- **Storage**: MinIO (dev) / S3 (prod)
- **Containerization**: Docker + Docker Compose

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API Key

## 🛠️ Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd Real-Jobs
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file and add your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Check service status  
docker-compose ps
```

### 4. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install requirements
pip install -r requirements.txt
```

### 5. Initialize Database

```bash
# The database will be automatically initialized via Docker
# Tables are created using SQLAlchemy models
```

## 🔄 Data Flow

1. **Discovery**: Identify company career pages using AI-assisted discovery
2. **Crawl**: Fetch HTML content with intelligent retry mechanisms  
3. **LLM Extraction**: Generate CSS/XPath rules automatically via LangGraph
4. **Verification**: Validate rules against live data and store for reuse
5. **Normalization**: Clean and structure job data into PostgreSQL
6. **Indexing**: Push jobs to OpenSearch for fast search capabilities

## 📊 Monitoring & Management

### Celery Flower (Task Monitoring)
```bash
# Access at http://localhost:5555
```

### OpenSearch Dashboard
```bash
# Access at http://localhost:9200
```

### MinIO Console  
```bash
# Access at http://localhost:9090
# Default credentials: minioadmin/minioadmin
```

## 🎯 Usage Examples

### Discover Company Jobs
```python
from scrapper.tasks.discovery import discover_company_careers_page

# Queue discovery task
result = discover_company_careers_page.delay("Google", "google.com")
```

### Extract Jobs from All Companies
```python  
from scrapper.tasks.extraction import crawl_all_companies

# Run daily job extraction
result = crawl_all_companies.delay()
```

### Verify Extraction Rules
```python
from scrapper.tasks.verification import verify_extraction_rules

# Verify and improve extraction rules
result = verify_extraction_rules.delay()
```

## 📁 Project Structure

```
Real-Jobs/
├── app/                    # Core application logic
│   ├── models.py          # SQLAlchemy database models
│   └── config.py          # Configuration management
├── scrapper/              # Scraping workflow and tasks  
│   ├── workflow.py        # LangGraph intelligent workflow
│   ├── celery_app.py      # Celery configuration
│   └── tasks/             # Distributed task definitions
├── database/              # Database initialization
├── docker-compose.yml     # Infrastructure orchestration
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔧 Configuration

Key settings in `.env`:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection for caching and queues
- `OPENAI_API_KEY`: Required for LLM-powered extraction
- `OPENSEARCH_HOST`: Search engine endpoint
- `S3_ENDPOINT_URL`: Object storage endpoint

## 🚦 Development Roadmap

### Phase 1: Core Infrastructure ✅
- [x] Database models and relationships
- [x] Celery task queue setup  
- [x] LangGraph workflow implementation
- [x] Docker containerization

### Phase 2: Enhanced Extraction 🔄
- [ ] ATS provider detection (Workday, Greenhouse, Lever)
- [ ] Job detail page extraction
- [ ] Salary and benefits parsing
- [ ] Multi-page crawling support

### Phase 3: Search & API 📋
- [ ] OpenSearch integration
- [ ] FastAPI REST endpoints
- [ ] Job deduplication algorithms
- [ ] Rate limiting and caching

### Phase 4: Frontend & Analytics 🎨
- [ ] Next.js search interface
- [ ] Real-time job alerts
- [ ] Market analytics dashboard
- [ ] Company insights

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`  
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

For questions or support, please open an issue on GitHub or reach out to the maintainers.

---

**Built with ❤️ using Python, LangGraph, and modern data infrastructure**