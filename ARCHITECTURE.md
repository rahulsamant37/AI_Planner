# 🚀 AI Travel Planner - Modern Microservices Architecture

A production-ready, cloud-native AI Travel Planner built with modern microservices architecture, featuring comprehensive observability, security, and scalability.

## 🏗️ Architecture Overview

### Core Services
- **API Gateway** - Nginx-based reverse proxy with rate limiting, load balancing, and security headers
- **Planner Service** - FastAPI microservice for travel itinerary generation using LangChain and Groq
- **Frontend Service** - Streamlit web interface for user interaction
- **Authentication Service** - JWT-based authentication and authorization
- **Configuration Service** - Centralized configuration management with feature flags
- **Monitoring Service** - Health checks and metrics collection
- **Notification Service** - Email, SMS, and webhook notifications

### Infrastructure Services
- **Redis** - Caching, session management, and pub/sub messaging
- **Elasticsearch** - Centralized logging and search
- **Kibana** - Log visualization and analysis
- **Prometheus** - Metrics collection and alerting
- **Grafana** - Metrics visualization and dashboards
- **Filebeat** - Log shipping and processing

## 🎯 Key Features

### 🔐 Security
- JWT-based authentication with session management
- Rate limiting and DDoS protection
- Security headers and CORS policies
- Network policies in Kubernetes
- Secret management with encrypted storage

### 📊 Observability
- Structured JSON logging with ELK stack
- Metrics collection with Prometheus
- Distributed tracing capabilities
- Health checks and monitoring
- Real-time dashboards with Grafana

### ⚡ Performance & Reliability
- Redis caching with configurable TTL
- Circuit breaker pattern implementation
- Horizontal pod autoscaling
- Load balancing with failover
- Graceful degradation

### 🔧 DevOps & Deployment
- Docker containerization
- Kubernetes-native deployment
- CI/CD pipeline with GitHub Actions
- Infrastructure as Code
- Multi-environment support

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Kubernetes cluster (optional)
- Python 3.10+ (for local development)

### 1. Environment Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd ai_planner

# Create environment file
cp .env.example .env
# Edit .env with your API keys and configuration
```

### 2. Local Development with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access services
# Frontend: http://localhost:8501
# API Gateway: http://localhost:80
# Monitoring: http://localhost:8002
# Grafana: http://localhost:3000
# Kibana: http://localhost:5601
```

### 3. Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n ai-planner

# Access via ingress or port-forward
kubectl port-forward svc/api-gateway-service 8080:80 -n ai-planner
```

## 📋 Service Details

### Planner Service (Port 8000)
**Purpose**: Core travel itinerary generation
**Features**:
- RESTful API with FastAPI
- LangChain integration for AI processing
- Redis caching for performance
- Comprehensive error handling

**Endpoints**:
- `GET /health` - Health check
- `POST /generate-itinerary` - Generate travel itinerary
- `GET /cache/stats` - Cache statistics
- `DELETE /cache/clear` - Clear cache

### Frontend Service (Port 8501)
**Purpose**: User interface for travel planning
**Features**:
- Modern Streamlit interface
- Real-time service status monitoring
- Cache management UI
- Responsive design

### Monitoring Service (Port 8002)
**Purpose**: System health monitoring and metrics
**Features**:
- Service discovery and health checks
- System metrics collection
- Service availability monitoring
- Performance analytics

**Endpoints**:
- `GET /system/health` - Overall system health
- `GET /system/metrics` - System metrics
- `GET /services/{service}/health` - Specific service health

### Authentication Service (Port 8003)
**Purpose**: User authentication and authorization
**Features**:
- JWT token-based authentication
- User session management
- Role-based access control
- Token blacklisting

**Endpoints**:
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `GET /auth/me` - Current user info
- `POST /auth/verify` - Token verification

### Configuration Service (Port 8004)
**Purpose**: Centralized configuration management
**Features**:
- Dynamic configuration updates
- Feature flag management
- Environment-specific configurations
- Configuration versioning

**Endpoints**:
- `GET /config` - All configurations
- `GET /config/{key}` - Specific configuration
- `POST /config/{key}` - Update configuration
- `GET /feature-flags` - Feature flags

### Notification Service (Port 8005)
**Purpose**: Multi-channel notification delivery
**Features**:
- Email notifications
- SMS notifications (configurable)
- Webhook notifications
- Notification tracking and status

**Endpoints**:
- `POST /notifications/email` - Send email
- `POST /notifications/sms` - Send SMS
- `POST /notifications/webhook` - Send webhook
- `GET /notifications/{id}/status` - Notification status

## 🏗️ Infrastructure Components

### Redis Configuration
```yaml
# High-performance caching with persistence
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Elasticsearch & Kibana
```yaml
# Centralized logging with Elasticsearch
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
```

### Monitoring Stack
```yaml
# Prometheus + Grafana for metrics
prometheus:
  image: prom/prometheus:latest
grafana:
  image: grafana/grafana:latest
```

## 🔧 Configuration

### Environment Variables
```bash
# Core Configuration
GROQ_API_KEY=your_groq_api_key
JWT_SECRET_KEY=your_secret_key
ENVIRONMENT=production

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# Notification Configuration
SMTP_HOST=your_smtp_host
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
```

### Feature Flags
The system supports runtime feature flags:
- `enable_caching` - Enable/disable Redis caching
- `enable_auth` - Enable/disable authentication
- `enable_rate_limiting` - Enable/disable API rate limiting
- `enable_metrics` - Enable/disable metrics collection

## 📊 Monitoring & Observability

### Metrics Available
- Request/response metrics
- Cache hit/miss ratios
- Service availability
- Resource utilization
- Custom business metrics

### Logging
- Structured JSON logging
- Request/response logging
- Error tracking and alerting
- Performance monitoring
- Security event logging

### Health Checks
All services implement comprehensive health checks:
- Database connectivity
- External service dependencies
- Resource availability
- Cache status

## 🧪 Testing

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio

# Run unit tests
pytest tests/test_core.py -v

# Run service tests
pytest tests/test_planner_service.py -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Test Coverage
- Unit tests for core business logic
- Integration tests for API endpoints
- Mocked external dependencies
- Health check testing

## 🚀 Deployment Strategies

### Development
```bash
docker-compose -f docker-compose.dev.yml up
```

### Staging
```bash
docker-compose -f docker-compose.staging.yml up
```

### Production
```bash
# Kubernetes deployment
kubectl apply -f k8s/
```

### Scaling
```bash
# Scale specific services
kubectl scale deployment planner-service --replicas=5 -n ai-planner

# Auto-scaling is configured via HPA
kubectl get hpa -n ai-planner
```

## 🔒 Security Considerations

### Authentication
- JWT tokens with configurable expiration
- Secure session management
- Password hashing with bcrypt
- Token blacklisting for logout

### Network Security
- API Gateway with rate limiting
- Network policies in Kubernetes
- TLS/SSL termination
- CORS configuration

### Data Protection
- Secrets encrypted at rest
- Environment-based configuration
- No hardcoded credentials
- Audit logging

## 📈 Performance Optimization

### Caching Strategy
- Multi-level caching (Redis, application)
- Cache invalidation strategies
- TTL-based cache expiration
- Cache warming procedures

### Database Optimization
- Connection pooling
- Query optimization
- Index strategies
- Read replicas (when applicable)

### Resource Management
- CPU and memory limits
- Horizontal pod autoscaling
- Resource requests and limits
- Efficient container images

## 🔄 CI/CD Pipeline

The project includes a comprehensive CI/CD pipeline:

### GitHub Actions Workflow
- Automated testing on multiple Python versions
- Code quality checks (flake8, black, isort)
- Docker image building and pushing
- Automated deployment to staging
- Production deployment with approval gates

### Build Process
1. Code checkout and environment setup
2. Dependency installation and caching
3. Linting and code formatting checks
4. Unit and integration tests
5. Docker image building
6. Container registry push
7. Kubernetes deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards
- Follow PEP 8 for Python code
- Use type hints where applicable
- Write comprehensive tests
- Update documentation
- Follow semantic versioning

## 📚 Additional Resources

### Documentation
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Architecture Decision Records](docs/adr/)
- [Troubleshooting Guide](docs/troubleshooting.md)

### Monitoring Dashboards
- **System Overview**: `http://localhost:3000/d/system`
- **Service Metrics**: `http://localhost:3000/d/services`
- **Log Analysis**: `http://localhost:5601`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the troubleshooting guide

---

**Built with ❤️ using modern microservices architecture patterns**
