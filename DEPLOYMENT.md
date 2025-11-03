# Deployment Guide

This guide explains how to deploy the Media Generation Pipeline API using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Running with Docker Compose](#running-with-docker-compose)
- [Accessing the API](#accessing-the-api)
- [Monitoring and Logs](#monitoring-and-logs)
- [Troubleshooting](#troubleshooting)
- [Production Considerations](#production-considerations)

## Prerequisites

### Required Software

- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 2.0 or later

Install Docker Desktop (includes Docker Compose):
- **macOS**: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Windows**: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- **Linux**: [Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/)

Verify installation:
```bash
docker --version
docker-compose --version
```

### Required API Keys

You will need API keys from:

1. **OpenAI**: For scene generation (LLM) and text-to-speech
   - Sign up at [https://platform.openai.com](https://platform.openai.com)
   - Generate API key at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

2. **Stability AI**: For AI image generation
   - Sign up at [https://platform.stability.ai](https://platform.stability.ai)
   - Generate API key at [https://platform.stability.ai/account/keys](https://platform.stability.ai/account/keys)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/siddhant61/media-generation-pipeline.git
cd media-generation-pipeline
```

### 2. Configure Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required API Keys
OPENAI_API_KEY=sk-your-openai-api-key-here
STABILITY_API_KEY=sk-your-stability-api-key-here
```

### 3. Start the Services

```bash
docker-compose up -d
```

This command will:
- Build the API Docker image
- Pull the Redis image
- Start both services in the background

### 4. Verify Services are Running

```bash
docker-compose ps
```

You should see both `media-pipeline-api` and `media-pipeline-redis` with status `Up (healthy)`.

### 5. Test the API

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Media Generation Pipeline API",
  "version": "2.0.0"
}
```

## Configuration

### Environment Variables

Edit the `.env` file to configure the application:

#### Required Variables

```bash
# OpenAI API Key (Required)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Stability AI API Key (Required)
STABILITY_API_KEY=sk-your-stability-api-key-here
```

#### Optional Variables

```bash
# API Security (Optional)
# Generate a secure key: python -c "import secrets; print(secrets.token_urlsafe(32))"
API_KEY=your-secure-api-key-here

# LLM Configuration (Optional)
LLM_MODEL=gpt-4o-mini              # Scene generation model

# TTS Configuration (Optional)
TTS_MODEL=tts-1                    # Text-to-speech model
TTS_VOICE=alloy                    # Voice: alloy, echo, fable, onyx, nova, shimmer

# Video Configuration (Optional)
VIDEO_FPS=24                       # Video frame rate

# Background Music (Optional)
BACKGROUND_MUSIC_FILE=/path/to/background_music.mp3

# Output Directory (Optional)
OUTPUT_DIR=generated_content       # Directory for generated videos
```

### Redis Configuration

Redis is automatically configured via Docker Compose. The API connects to Redis at `redis://redis:6379/0`.

To use an external Redis instance, set in `.env`:

```bash
REDIS_URL=redis://your-redis-host:6379/0
```

## Running with Docker Compose

### Start Services

Start services in the background:
```bash
docker-compose up -d
```

Start services with live logs:
```bash
docker-compose up
```

### Stop Services

Stop services:
```bash
docker-compose stop
```

Stop and remove containers:
```bash
docker-compose down
```

Stop and remove containers with volumes (removes all data):
```bash
docker-compose down -v
```

### Rebuild Services

After code changes:
```bash
docker-compose up -d --build
```

### View Logs

View logs from all services:
```bash
docker-compose logs
```

View logs from a specific service:
```bash
docker-compose logs api
docker-compose logs redis
```

Follow logs in real-time:
```bash
docker-compose logs -f api
```

### Restart Services

Restart all services:
```bash
docker-compose restart
```

Restart a specific service:
```bash
docker-compose restart api
```

## Accessing the API

### API Base URL

Once services are running, the API is available at:

```
http://localhost:8000
```

### Interactive API Documentation (Swagger UI)

Open your browser and navigate to:

```
http://localhost:8000/docs
```

The Swagger UI provides:
- Complete API documentation
- Interactive request/response examples
- Ability to test endpoints directly in the browser
- Request/response schemas

### Alternative API Documentation (ReDoc)

For a cleaner documentation view:

```
http://localhost:8000/redoc
```

### OpenAPI Schema

Download the OpenAPI schema:

```
http://localhost:8000/openapi.json
```

## Using the API

### Example: Generate a Video

#### 1. Submit a Generation Request

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "The Solar System",
    "num_scenes": 8
  }'
```

If API key authentication is enabled:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "topic": "The Solar System",
    "num_scenes": 8
  }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Video generation job queued. Use /status/{job_id} to check progress."
}
```

#### 2. Check Job Status

```bash
curl http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "generating_content",
  "progress": "Generating images and narration...",
  "created_at": "2024-01-01T12:00:00",
  "completed_at": null,
  "video_url": null,
  "error": null
}
```

#### 3. Download Completed Video

Once status is `complete`, download the video:

```bash
curl -o video.mp4 http://localhost:8000/outputs/final_video.mp4
```

### Example: Using Python

```python
import requests
import time

# Submit job
response = requests.post(
    "http://localhost:8000/generate",
    json={
        "topic": "The History of Space Exploration",
        "num_scenes": 6
    }
)
job = response.json()
job_id = job["job_id"]
print(f"Job submitted: {job_id}")

# Poll status
while True:
    status_response = requests.get(f"http://localhost:8000/status/{job_id}")
    status = status_response.json()
    
    print(f"Status: {status['status']} - {status['progress']}")
    
    if status["status"] == "complete":
        print(f"Video ready: http://localhost:8000{status['video_url']}")
        break
    elif status["status"] == "failed":
        print(f"Job failed: {status['error']}")
        break
    
    time.sleep(10)
```

## Monitoring and Logs

### Health Checks

Check API health:
```bash
curl http://localhost:8000/health
```

Check Redis health:
```bash
docker-compose exec redis redis-cli ping
```

### Container Status

View running containers:
```bash
docker-compose ps
```

View resource usage:
```bash
docker stats media-pipeline-api media-pipeline-redis
```

### Persistent Data

Generated videos are stored in:
```
./generated_content/
```

This directory is mounted as a volume and persists between container restarts.

Redis data is stored in a Docker volume and persists between restarts.

## Troubleshooting

### Services Won't Start

**Check Docker is running:**
```bash
docker info
```

**Check logs for errors:**
```bash
docker-compose logs
```

**Check port conflicts:**
```bash
# Check if ports 8000 or 6379 are already in use
netstat -an | grep 8000
netstat -an | grep 6379
```

To use different ports, edit `docker-compose.yml`:
```yaml
services:
  api:
    ports:
      - "8080:8000"  # Use port 8080 instead
  redis:
    ports:
      - "6380:6379"  # Use port 6380 instead
```

### API Keys Not Working

**Verify environment variables are set:**
```bash
docker-compose exec api env | grep API_KEY
```

**Restart services after changing .env:**
```bash
docker-compose down
docker-compose up -d
```

### Redis Connection Issues

**Check Redis is healthy:**
```bash
docker-compose ps redis
```

**Check Redis logs:**
```bash
docker-compose logs redis
```

**Test Redis connection from API container:**
```bash
docker-compose exec api python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"
```

### Out of Disk Space

**Check disk usage:**
```bash
docker system df
```

**Clean up unused Docker resources:**
```bash
docker system prune -a
```

**Remove old generated videos:**
```bash
rm -rf ./generated_content/*
```

### Job Failures

**Check API logs:**
```bash
docker-compose logs -f api
```

Common issues:
- Invalid API keys
- Rate limits exceeded
- Insufficient disk space
- Network connectivity issues

## Production Considerations

### Security

1. **Use API Key Authentication**
   - Generate a strong API key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - Set `API_KEY` in `.env`
   - All protected endpoints will require `X-API-Key` header

2. **Use HTTPS**
   - Deploy behind a reverse proxy (Nginx, Traefik, Caddy)
   - Enable SSL/TLS certificates

3. **Secure Environment Variables**
   - Never commit `.env` file to version control
   - Use secrets management in production (AWS Secrets Manager, HashiCorp Vault)

### Scaling

1. **Horizontal Scaling**
   - Run multiple API instances behind a load balancer
   - Use external Redis (AWS ElastiCache, Redis Cloud)

2. **Resource Limits**
   - Add resource limits to `docker-compose.yml`:
   ```yaml
   services:
     api:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 4G
           reservations:
             cpus: '1'
             memory: 2G
   ```

### Monitoring

1. **Add Logging**
   - Configure structured logging
   - Use centralized logging (ELK Stack, Splunk)

2. **Add Metrics**
   - Use Prometheus for metrics collection
   - Set up Grafana dashboards

3. **Set Up Alerts**
   - Monitor health check endpoints
   - Alert on service failures

### Backup

1. **Redis Data**
   - Configure Redis persistence
   - Regular backups of Redis data volume

2. **Generated Content**
   - Backup `./generated_content/` directory
   - Consider object storage (S3, GCS, Azure Blob)

### Performance

1. **Caching**
   - Redis is already configured for job storage
   - Consider caching frequent requests

2. **Background Processing**
   - Job processing is already asynchronous
   - Consider dedicated worker services for heavy tasks

## Support

For issues and questions:
- Check the [troubleshooting](#troubleshooting) section
- Review logs with `docker-compose logs`
- Open an issue on [GitHub](https://github.com/siddhant61/media-generation-pipeline/issues)

## License

This project is licensed under the MIT License. See LICENSE file for details.
