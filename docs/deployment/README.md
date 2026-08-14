# Deployment Guide

## Option A: Docker Compose (Easiest)

### Prerequisites
- Docker and Docker Compose installed

### Steps

```bash
# Clone the repository
git clone <repo-url>
cd nexus

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Start services
docker compose up --build

# Open browser
open http://localhost:5173
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| frontend | 5173 | React application |
| api | 8000 | FastAPI backend |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache |

## Option B: AWS (Production)

### Infrastructure

```
ALB → ECS Fargate (API) → RDS PostgreSQL
                       → ElastiCache Redis
    → CloudFront → S3 (Frontend)
```

### Step 1: VPC and Networking

```bash
# Create VPC with public and private subnets
# Configure NAT Gateway for private subnet internet access
```

### Step 2: RDS PostgreSQL

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier nexus-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 16 \
  --master-username nexus \
  --master-user-password <secure-password> \
  --allocated-storage 20 \
  --vpc-security-group-ids <sg-id> \
  --db-subnet-group-name <subnet-group>
```

### Step 3: ElastiCache Redis

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id nexus-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1
```

### Step 4: ECS Cluster

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name nexus

# Create task definitions for API and frontend
# Configure service with load balancer
```

### Step 5: Secrets Manager

```bash
# Store sensitive configuration
aws secretsmanager create-secret \
  --name nexus/prod \
  --secret-string '{
    "DATABASE_URL": "...",
    "JWT_SECRET": "...",
    "ENCRYPTION_KEY": "...",
    "OPENAI_API_KEY": "..."
  }'
```

### Step 6: Build and Push Docker Images

```bash
# Build API image
docker build -t nexus-api ./apps/api
docker tag nexus-api:latest <account>.dkr.ecr.<region>.amazonaws.com/nexus-api:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/nexus-api:latest

# Build frontend image
docker build -t nexus-web ./apps/web
docker tag nexus-web:latest <account>.dkr.ecr.<region>.amazonaws.com/nexus-web:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/nexus-web:latest
```

### Step 7: Deploy

```bash
# Update ECS services
aws ecs update-service \
  --cluster nexus \
  --service nexus-api \
  --force-new-deployment

aws ecs update-service \
  --cluster nexus \
  --service nexus-web \
  --force-new-deployment
```

### Step 8: HTTPS

```bash
# Request ACM certificate
aws acm request-certificate \
  --domain-name nexus.yourdomain.com \
  --validation-method DNS

# Configure ALB listener with certificate
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string |
| REDIS_URL | Redis connection string |
| JWT_SECRET | Session signing key |
| ENCRYPTION_KEY | Fernet encryption key |

### LLM

| Variable | Description |
|----------|-------------|
| LLM_PROVIDER | `openai` or `anthropic` |
| LLM_MODEL | Model name |
| OPENAI_API_KEY | OpenAI API key |
| ANTHROPIC_API_KEY | Anthropic API key |

### Integrations

| Variable | Description |
|----------|-------------|
| GITHUB_CLIENT_ID | GitHub OAuth client ID |
| GITHUB_CLIENT_SECRET | GitHub OAuth client secret |
| SLACK_CLIENT_ID | Slack OAuth client ID |
| SLACK_CLIENT_SECRET | Slack OAuth client secret |
| HUBSPOT_CLIENT_ID | HubSpot OAuth client ID |
| HUBSPOT_CLIENT_SECRET | HubSpot OAuth client secret |

### Security

| Variable | Description |
|----------|-------------|
| CORS_ORIGINS | Allowed CORS origins (JSON array) |
| RATE_LIMIT_PER_MINUTE | Per-user rate limit |
| RATE_LIMIT_PER_HOUR | Per-organization rate limit |

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# API readiness
curl http://localhost:8000/ready

# Metrics
curl http://localhost:8000/metrics
```

### Logging

All logs are structured JSON with:
- `timestamp`
- `level`
- `logger`
- `message`
- `request_id` (where applicable)
- `user_id` (where applicable)

### Sentry

Set `SENTRY_DSN` environment variable to enable error tracking.

## Rollback

```bash
# Rollback ECS service to previous task definition
aws ecs update-service \
  --cluster nexus \
  --service nexus-api \
  --task-definition <previous-task-def>
```
