# News AI - Advanced RSS Feed Processing & Analysis

A high-performance, scalable news aggregation and analysis system with machine learning-powered topic classification, event extraction, and semantic search.

## 🏗️ Architecture

```
news-ai/
├── services/
│   ├── api_go/          # Public Gateway (Go + Gin/Fiber)
│   ├── ingester_go/     # RSS Feed Ingester (Go + Cron)
│   └── nlp_py/          # ML Pipeline (Python + FastAPI)
├── frontend/            # Next.js Dashboard
├── shared/              # gRPC Proto & Schemas
├── infra/               # K8s & Terraform
└── data/                # Configuration Files
```

## 🚀 Features

- **High-Performance API**: Go-based REST API with gRPC communication
- **Concurrent RSS Ingestion**: Ultra-fast feed fetching and processing
- **ML Pipeline**: Topic classification, event extraction, and grouping
- **Vector Search**: Semantic search with Qdrant vector database
- **Real-time Dashboard**: Next.js frontend with live updates
- **Scalable Infrastructure**: Docker, Kubernetes, and cloud-ready

## 🛠️ Tech Stack

### Services
- **API Gateway**: Go + Gin/Fiber + gRPC
- **RSS Ingester**: Go + gofeed + Redis streams
- **ML Pipeline**: Python + FastAPI + Transformers + spaCy
- **Vector DB**: Qdrant for semantic search
- **Cache/Queue**: Redis for caching and job queues
- **Database**: PostgreSQL for persistent storage

### Frontend
- **Framework**: Next.js 15 + TypeScript
- **Styling**: Tailwind CSS
- **State**: React Query for API state management

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Orchestration**: Kubernetes (optional)
- **Cloud**: Terraform for IaC (optional)

## 🚀 Quick Start

1. **Clone and setup**:
```bash
git clone <repo-url>
cd news-ai
cp .env.example .env
```

2. **Start with Docker Compose**:
```bash
make build
docker-compose up -d
```

3. **Initialize database**:
```bash
make migrate
make seed
```

4. **Access the dashboard**:
- Frontend: http://localhost:3000
- API: http://localhost:8080
- Qdrant: http://localhost:6333

## 📊 Pipeline Flow

```
RSS Feeds → Ingester → Redis Queue → NLP Pipeline → Database/Vector Store → API → Frontend
```

### 5-Step ML Pipeline
1. **Gather**: Fetch and normalize RSS feeds
2. **Translate**: Multi-language support with MarianMT
3. **Classify**: Zero-shot topic classification with BART-MNLI
4. **Extract**: Event extraction with spaCy + SRL
5. **Group**: Event clustering with HDBSCAN
6. **Embed**: Generate vectors with sentence-transformers

## 🔧 Development

### Build Commands
```bash
make build      # Build all services
make test       # Run tests
make lint       # Code linting
make proto-gen  # Generate gRPC stubs
```

### Service Development
```bash
# API Gateway (Go)
cd services/api_go
go run cmd/api/main.go

# RSS Ingester (Go)
cd services/ingester_go
go run cmd/ingester/main.go

# ML Pipeline (Python)
cd services/nlp_py
pip install -r requirements.txt
python app/server.py

# Frontend (Next.js)
cd frontend
npm install
npm run dev
```

## 📈 Performance

- **RSS Ingestion**: 1000+ feeds/minute
- **Classification**: 1.6 requests/second with concurrent processing
- **Search**: Sub-100ms vector similarity search
- **API**: <50ms response times with caching

## 🌐 API Endpoints

### Headlines
- `GET /api/headlines` - List all headlines
- `GET /api/headlines/search` - Hybrid search
- `GET /api/headlines/topics` - Topic statistics

### Events
- `GET /api/events` - Event groups
- `GET /api/events/{id}` - Event details

### Analytics
- `GET /api/metrics` - System metrics
- `GET /api/topics/underrepresentation` - Topic analysis

## 🔒 Security

- Rate limiting with Redis
- Input validation and sanitization
- CORS protection
- Environment-based configuration
- Health checks and monitoring

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📚 Documentation

- [API Documentation](./docs/api.md)
- [Deployment Guide](./docs/deployment.md)
- [Development Setup](./docs/development.md)
