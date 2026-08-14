# Nexus Runbook

## Common Operations

### Starting the Application

```bash
# Start all services
docker compose up --build

# Start in background
docker compose up --build -d

# View logs
docker compose logs -f api
docker compose logs -f frontend
```

### Stopping the Application

```bash
# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

### Database Operations

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Create new migration
docker compose exec api alembic revision --autogenerate -m "description"
```

### Viewing Logs

```bash
# API logs
docker compose logs api

# All logs
docker compose logs

# Follow logs
docker compose logs -f
```

## Troubleshooting

### API Won't Start

1. Check database connection:
   ```bash
   docker compose exec postgres pg_isready -U nexus
   ```

2. Check Redis connection:
   ```bash
   docker compose exec redis redis-cli ping
   ```

3. View API logs:
   ```bash
   docker compose logs api
   ```

### Frontend Won't Connect to API

1. Check API is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check CORS configuration in `.env`

3. Check nginx proxy configuration

### Database Connection Issues

1. Check PostgreSQL is running:
   ```bash
   docker compose ps postgres
   ```

2. Check connection:
   ```bash
   docker compose exec postgres psql -U nexus -d nexus -c "SELECT 1"
   ```

3. Reset database:
   ```bash
   docker compose down -v
   docker compose up -d postgres
   docker compose exec api alembic upgrade head
   ```

### Redis Connection Issues

1. Check Redis is running:
   ```bash
   docker compose ps redis
   ```

2. Test connection:
   ```bash
   docker compose exec redis redis-cli ping
   ```

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

### Performance

```bash
# View container resource usage
docker stats

# View API response times
docker compose logs api | grep "duration_ms"
```

## Security

### Rotating Secrets

1. Generate new JWT secret:
   ```bash
   openssl rand -base64 32
   ```

2. Generate new encryption key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

3. Update `.env` and restart services

### Reviewing Audit Logs

```bash
# Query audit logs
docker compose exec postgres psql -U nexus -d nexus -c \
  "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100"
```

## Backup and Recovery

### Database Backup

```bash
# Backup
docker compose exec postgres pg_dump -U nexus nexus > backup.sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U nexus -d nexus
```

### Full Backup

```bash
# Backup volume
docker run --rm -v nexus_pgdata:/data -v $(pwd):/backup alpine \
  tar czf /backup/pgdata.tar.gz /data
```

## Scaling

### Horizontal Scaling

```bash
# Scale API instances
docker compose up -d --scale api=3
```

### Database Scaling

For production, consider:
- Read replicas for read-heavy workloads
- Connection pooling with PgBouncer
- RDS Multi-AZ for high availability
