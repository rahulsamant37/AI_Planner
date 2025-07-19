# AI Travel Planner - Modern Microservices Makefile
# Comprehensive development and deployment automation

.PHONY: help install dev test build deploy clean docs

# Configuration
PROJECT_NAME := ai-planner
DOCKER_COMPOSE := docker-compose
KUBECTL := kubectl
NAMESPACE := ai-planner

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
NC := \033[0m # No Color

# Default target
help: ## Show this help message
	@echo "$(CYAN)🚀 AI Travel Planner - Modern Microservices$(NC)"
	@echo "$(YELLOW)Available commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development Setup
install: ## Install development dependencies
	@echo "$(BLUE)📦 Installing development dependencies...$(NC)"
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-asyncio black isort flake8
	@echo "$(GREEN)✅ Dependencies installed successfully$(NC)"

install-services: ## Install dependencies for all services
	@echo "$(BLUE)📦 Installing service dependencies...$(NC)"
	cd services/planner-service && pip install -r requirements.txt
	cd services/frontend-service && pip install -r requirements.txt
	cd services/monitoring-service && pip install -r requirements.txt
	cd services/auth-service && pip install -r requirements.txt
	cd services/config-service && pip install -r requirements.txt
	cd services/notification-service && pip install -r requirements.txt
	@echo "$(GREEN)✅ All service dependencies installed$(NC)"

# Development
dev: ## Start development environment with Docker Compose
	@echo "$(BLUE)🔧 Starting development environment...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ Development environment started$(NC)"
	@echo "$(YELLOW)Services available at:$(NC)"
	@echo "  Frontend: http://localhost:8501"
	@echo "  API Gateway: http://localhost:80"
	@echo "  Monitoring: http://localhost:8002"
	@echo "  Grafana: http://localhost:3000"
	@echo "  Kibana: http://localhost:5601"

dev-logs: ## Show development logs
	@echo "$(BLUE)📋 Showing development logs...$(NC)"
	$(DOCKER_COMPOSE) logs -f

dev-stop: ## Stop development environment
	@echo "$(YELLOW)⏹️  Stopping development environment...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✅ Development environment stopped$(NC)"

dev-rebuild: ## Rebuild and restart development environment
	@echo "$(BLUE)🔄 Rebuilding development environment...$(NC)"
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) build --no-cache
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ Development environment rebuilt$(NC)"

# Testing
test: ## Run all tests
	@echo "$(BLUE)🧪 Running all tests...$(NC)"
	pytest tests/ -v --cov=src --cov-report=term-missing
	@echo "$(GREEN)✅ Tests completed$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)🧪 Running unit tests...$(NC)"
	pytest tests/test_core.py -v
	@echo "$(GREEN)✅ Unit tests completed$(NC)"

test-integration: ## Run integration tests
	@echo "$(BLUE)🧪 Running integration tests...$(NC)"
	pytest tests/test_planner_service.py -v
	@echo "$(GREEN)✅ Integration tests completed$(NC)"

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)👀 Running tests in watch mode...$(NC)"
	pytest-watch tests/ -- -v

# Code Quality
lint: ## Run code linting
	@echo "$(BLUE)🔍 Running code linting...$(NC)"
	flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	@echo "$(GREEN)✅ Linting completed$(NC)"

format: ## Format code with black and isort
	@echo "$(BLUE)🎨 Formatting code...$(NC)"
	black src/ services/
	isort src/ services/
	@echo "$(GREEN)✅ Code formatting completed$(NC)"

format-check: ## Check code formatting without making changes
	@echo "$(BLUE)🎨 Checking code formatting...$(NC)"
	black --check src/ services/
	isort --check-only src/ services/
	@echo "$(GREEN)✅ Code formatting check completed$(NC)"

# Building
build: ## Build all Docker images
	@echo "$(BLUE)🏗️  Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✅ Docker images built successfully$(NC)"

build-service: ## Build specific service (usage: make build-service SERVICE=planner-service)
	@echo "$(BLUE)🏗️  Building $(SERVICE) image...$(NC)"
	cd services/$(SERVICE) && docker build -t $(PROJECT_NAME)/$(SERVICE):latest .
	@echo "$(GREEN)✅ $(SERVICE) image built successfully$(NC)"

build-prod: ## Build production images with optimization
	@echo "$(BLUE)🏗️  Building production Docker images...$(NC)"
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml build
	@echo "$(GREEN)✅ Production images built successfully$(NC)"

# Kubernetes Deployment
k8s-create-namespace: ## Create Kubernetes namespace
	@echo "$(BLUE)🏗️  Creating Kubernetes namespace...$(NC)"
	$(KUBECTL) create namespace $(NAMESPACE) --dry-run=client -o yaml | $(KUBECTL) apply -f -
	@echo "$(GREEN)✅ Namespace created$(NC)"

k8s-deploy: ## Deploy to Kubernetes
	@echo "$(BLUE)🚀 Deploying to Kubernetes...$(NC)"
	$(KUBECTL) apply -f k8s/
	@echo "$(GREEN)✅ Deployed to Kubernetes$(NC)"

k8s-status: ## Check Kubernetes deployment status
	@echo "$(BLUE)📊 Checking Kubernetes status...$(NC)"
	$(KUBECTL) get pods -n $(NAMESPACE)
	$(KUBECTL) get services -n $(NAMESPACE)
	$(KUBECTL) get ingress -n $(NAMESPACE)

k8s-logs: ## Show Kubernetes logs (usage: make k8s-logs SERVICE=planner-service)
	@echo "$(BLUE)📋 Showing $(SERVICE) logs...$(NC)"
	$(KUBECTL) logs -f deployment/$(SERVICE) -n $(NAMESPACE)

k8s-delete: ## Delete Kubernetes deployment
	@echo "$(RED)⚠️  Deleting Kubernetes deployment...$(NC)"
	$(KUBECTL) delete -f k8s/
	@echo "$(GREEN)✅ Kubernetes deployment deleted$(NC)"

k8s-port-forward: ## Port forward to frontend service
	@echo "$(BLUE)🔗 Port forwarding to frontend service...$(NC)"
	$(KUBECTL) port-forward svc/frontend-service 8501:8501 -n $(NAMESPACE)

# Monitoring
monitor-health: ## Check health of all services
	@echo "$(BLUE)🩺 Checking service health...$(NC)"
	@curl -s http://localhost:8000/health | jq '.' || echo "Planner service not available"
	@curl -s http://localhost:8002/system/health | jq '.' || echo "Monitoring service not available"
	@curl -s http://localhost:8003/health | jq '.' || echo "Auth service not available"
	@curl -s http://localhost:8004/health | jq '.' || echo "Config service not available"
	@curl -s http://localhost:8005/health | jq '.' || echo "Notification service not available"

monitor-metrics: ## Show service metrics
	@echo "$(BLUE)📊 Showing service metrics...$(NC)"
	@curl -s http://localhost:8002/system/metrics | jq '.'

monitor-cache: ## Show cache statistics
	@echo "$(BLUE)💾 Showing cache statistics...$(NC)"
	@curl -s http://localhost:8000/cache/stats | jq '.'

# Database Management
redis-cli: ## Connect to Redis CLI
	@echo "$(BLUE)🔧 Connecting to Redis CLI...$(NC)"
	docker exec -it $(shell docker-compose ps -q redis) redis-cli

redis-flush: ## Flush all Redis data
	@echo "$(RED)⚠️  Flushing all Redis data...$(NC)"
	docker exec -it $(shell docker-compose ps -q redis) redis-cli FLUSHALL

# Logs and Debugging
logs: ## Show all service logs
	@echo "$(BLUE)📋 Showing all service logs...$(NC)"
	$(DOCKER_COMPOSE) logs -f

logs-planner: ## Show planner service logs
	$(DOCKER_COMPOSE) logs -f planner-service

logs-frontend: ## Show frontend service logs
	$(DOCKER_COMPOSE) logs -f frontend-service

logs-monitoring: ## Show monitoring service logs
	$(DOCKER_COMPOSE) logs -f monitoring-service

debug-planner: ## Debug planner service
	@echo "$(BLUE)🐛 Debugging planner service...$(NC)"
	docker exec -it $(shell docker-compose ps -q planner-service) /bin/bash

debug-redis: ## Debug Redis
	@echo "$(BLUE)🐛 Debugging Redis...$(NC)"
	docker exec -it $(shell docker-compose ps -q redis) /bin/bash

# Performance Testing
load-test: ## Run simple load test
	@echo "$(BLUE)⚡ Running load test...$(NC)"
	@for i in {1..50}; do \
		curl -s -X POST http://localhost:8000/generate-itinerary \
		-H "Content-Type: application/json" \
		-d '{"city": "Test City", "interests": "testing, performance"}' > /dev/null & \
	done
	wait
	@echo "$(GREEN)✅ Load test completed$(NC)"

benchmark: ## Run benchmark tests
	@echo "$(BLUE)🏃 Running benchmark tests...$(NC)"
	ab -n 100 -c 10 http://localhost:8000/health
	@echo "$(GREEN)✅ Benchmark completed$(NC)"

# Security
security-scan: ## Run security scan on Docker images
	@echo "$(BLUE)🔒 Running security scan...$(NC)"
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy image $(PROJECT_NAME)/planner-service:latest
	@echo "$(GREEN)✅ Security scan completed$(NC)"

# Cleanup
clean: ## Clean up Docker resources
	@echo "$(YELLOW)🧹 Cleaning up Docker resources...$(NC)"
	$(DOCKER_COMPOSE) down -v
	docker system prune -f
	docker volume prune -f
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

clean-all: ## Clean up everything including images
	@echo "$(RED)⚠️  Cleaning up all Docker resources...$(NC)"
	$(DOCKER_COMPOSE) down -v --rmi all
	docker system prune -af
	docker volume prune -f
	@echo "$(GREEN)✅ Complete cleanup finished$(NC)"

# Documentation
docs: ## Generate documentation
	@echo "$(BLUE)📚 Generating documentation...$(NC)"
	@echo "$(GREEN)✅ Documentation available in ARCHITECTURE.md$(NC)"

docs-api: ## Generate API documentation
	@echo "$(BLUE)📚 Generating API documentation...$(NC)"
	cd services/planner-service && python -c "from main import app; import json; print(json.dumps(app.openapi(), indent=2))" > ../../docs/api-spec.json
	@echo "$(GREEN)✅ API documentation generated$(NC)"

# Quick Actions
quick-start: install dev ## Quick start for new developers
	@echo "$(CYAN)🎉 Welcome to AI Travel Planner!$(NC)"
	@echo "$(GREEN)✅ Environment is ready for development$(NC)"

quick-test: format-check lint test ## Quick test pipeline
	@echo "$(CYAN)🎉 All checks passed!$(NC)"

# Production shortcuts
prod-deploy: build-prod k8s-deploy ## Build and deploy to production
	@echo "$(CYAN)🚀 Production deployment completed!$(NC)"

prod-rollback: ## Rollback production deployment
	@echo "$(YELLOW)🔄 Rolling back production deployment...$(NC)"
	$(KUBECTL) rollout undo deployment/planner-service -n $(NAMESPACE)
	$(KUBECTL) rollout undo deployment/frontend-service -n $(NAMESPACE)
	@echo "$(GREEN)✅ Production rollback completed$(NC)"
