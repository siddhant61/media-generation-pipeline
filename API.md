# Media Generation Pipeline API

A FastAPI-based REST API for generating dynamic videos from topics using AI.

## Features

- **Asynchronous Job Processing**: Submit video generation requests and track progress
- **Job Status Tracking**: Real-time status updates for video generation
- **Static File Serving**: Direct access to generated videos
- **REST API**: Standard HTTP endpoints for easy integration

## Quick Start

### Starting the API Server

```bash
# Using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000

# Or using the console script (after pip install)
media-pipeline-api
```

The API will be available at `http://localhost:8000`

### API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## API Endpoints

### Health Check

**GET** `/health`

Check if the API is running.

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "Media Generation Pipeline API",
  "version": "2.0.0"
}
```

### Generate Video

**POST** `/generate`

Submit a video generation job.

**Request Body:**
```json
{
  "topic": "The Industrial Revolution",
  "num_scenes": 8,
  "use_static_scenes": false,
  "scene_ids": null
}
```

**Parameters:**
- `topic` (string, required unless using static scenes): Topic to generate video about
- `num_scenes` (integer, 1-20, default: 8): Number of scenes to generate
- `use_static_scenes` (boolean, default: false): Use predefined static scenes
- `scene_ids` (array, optional): Specific scene IDs to process (only with static scenes)

**Example:**
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "The Industrial Revolution",
    "num_scenes": 6
  }'
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Video generation job queued. Use /status/{job_id} to check progress."
}
```

### Get Job Status

**GET** `/status/{job_id}`

Get the current status of a video generation job.

**Example:**
```bash
curl http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000
```

**Response (In Progress):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "generating_content",
  "progress": "Generating images and narration...",
  "created_at": "2024-01-15T10:30:00",
  "completed_at": null,
  "video_url": null,
  "error": null
}
```

**Response (Complete):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "progress": "Video generation complete!",
  "created_at": "2024-01-15T10:30:00",
  "completed_at": "2024-01-15T10:35:00",
  "video_url": "/outputs/final_video.mp4",
  "error": null
}
```

**Job Status Values:**
- `queued`: Job is waiting to start
- `generating_scenes`: Generating scene descriptions from topic
- `generating_content`: Creating images and narration
- `generating_audio`: Processing audio for scenes
- `assembling_video`: Assembling final video with effects
- `complete`: Video generation complete
- `failed`: Job failed (check error field)

### List All Jobs

**GET** `/jobs`

Get a list of all jobs (for monitoring/debugging).

**Example:**
```bash
curl http://localhost:8000/jobs
```

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "complete",
      "progress": "Video generation complete!",
      "created_at": "2024-01-15T10:30:00",
      "topic": "The Industrial Revolution",
      "num_scenes": 6
    }
  ]
}
```

### Access Generated Video

**GET** `/outputs/{filename}`

Static file endpoint to download generated videos.

**Example:**
```bash
# Download the video
curl -O http://localhost:8000/outputs/final_video.mp4

# Or open in browser
open http://localhost:8000/outputs/final_video.mp4
```

## Usage Examples

### Python Client Example

```python
import requests
import time

# API base URL
BASE_URL = "http://localhost:8000"

# 1. Submit generation job
response = requests.post(
    f"{BASE_URL}/generate",
    json={
        "topic": "Climate Change",
        "num_scenes": 5
    }
)
job_data = response.json()
job_id = job_data["job_id"]
print(f"Job submitted: {job_id}")

# 2. Poll for completion
while True:
    status_response = requests.get(f"{BASE_URL}/status/{job_id}")
    status_data = status_response.json()
    
    print(f"Status: {status_data['status']} - {status_data['progress']}")
    
    if status_data["status"] in ["complete", "failed"]:
        break
    
    time.sleep(5)  # Wait 5 seconds before checking again

# 3. Download video if successful
if status_data["status"] == "complete":
    video_url = f"{BASE_URL}{status_data['video_url']}"
    print(f"Video available at: {video_url}")
    
    # Download the video
    video_response = requests.get(video_url)
    with open("my_video.mp4", "wb") as f:
        f.write(video_response.content)
    print("Video downloaded!")
else:
    print(f"Job failed: {status_data['error']}")
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';

async function generateVideo(topic, numScenes = 8) {
  try {
    // 1. Submit job
    const generateResponse = await axios.post(`${BASE_URL}/generate`, {
      topic: topic,
      num_scenes: numScenes
    });
    
    const jobId = generateResponse.data.job_id;
    console.log(`Job submitted: ${jobId}`);
    
    // 2. Poll for completion
    let status = 'queued';
    while (status !== 'complete' && status !== 'failed') {
      await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5s
      
      const statusResponse = await axios.get(`${BASE_URL}/status/${jobId}`);
      const statusData = statusResponse.data;
      
      status = statusData.status;
      console.log(`${status}: ${statusData.progress}`);
      
      if (status === 'complete') {
        console.log(`Video URL: ${BASE_URL}${statusData.video_url}`);
        return statusData.video_url;
      } else if (status === 'failed') {
        throw new Error(statusData.error);
      }
    }
  } catch (error) {
    console.error('Error:', error.message);
    throw error;
  }
}

// Use the function
generateVideo('The Solar System', 6)
  .then(videoUrl => console.log('Success!', videoUrl))
  .catch(err => console.error('Failed:', err));
```

### cURL Example

```bash
#!/bin/bash

# Submit job
RESPONSE=$(curl -s -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "Space Exploration", "num_scenes": 5}')

JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"

# Poll for completion
while true; do
  STATUS=$(curl -s http://localhost:8000/status/$JOB_ID)
  STATE=$(echo $STATUS | jq -r '.status')
  PROGRESS=$(echo $STATUS | jq -r '.progress')
  
  echo "$STATE: $PROGRESS"
  
  if [ "$STATE" = "complete" ]; then
    VIDEO_URL=$(echo $STATUS | jq -r '.video_url')
    echo "Video ready: http://localhost:8000$VIDEO_URL"
    break
  elif [ "$STATE" = "failed" ]; then
    ERROR=$(echo $STATUS | jq -r '.error')
    echo "Failed: $ERROR"
    break
  fi
  
  sleep 5
done
```

## Configuration

The API uses the same configuration as the CLI:

### Environment Variables

```bash
# Required
export OPENAI_API_KEY='your-openai-api-key'
export STABILITY_API_KEY='your-stability-api-key'

# Optional - Video Production Features
export BACKGROUND_MUSIC_FILE='/path/to/music.mp3'

# Optional - Model Configuration
export LLM_MODEL='gpt-4o-mini'
export TTS_MODEL='tts-1'
export TTS_VOICE='alloy'
export VIDEO_FPS='24'
export OUTPUT_DIR='generated_content'
```

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t media-pipeline-api .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY='your-key' \
  -e STABILITY_API_KEY='your-key' \
  media-pipeline-api
```

### Using Gunicorn + Uvicorn Workers

```bash
pip install gunicorn

gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Systemd Service

Create `/etc/systemd/system/media-pipeline-api.service`:

```ini
[Unit]
Description=Media Generation Pipeline API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/media-generation-pipeline
Environment="OPENAI_API_KEY=your-key"
Environment="STABILITY_API_KEY=your-key"
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable media-pipeline-api
sudo systemctl start media-pipeline-api
```

## Scaling Considerations

### Job Storage

The current implementation uses in-memory job storage. For production:

1. **Use Redis**: Store jobs in Redis for persistence
2. **Use Database**: PostgreSQL or MongoDB for job history
3. **Use Message Queue**: RabbitMQ or Redis Queue for job processing

### File Storage

For production deployments:

1. **Cloud Storage**: S3, Google Cloud Storage, or Azure Blob Storage
2. **CDN**: CloudFront or similar for video delivery
3. **Cleanup**: Implement automatic cleanup of old files

### Rate Limiting

Implement rate limiting to prevent API abuse:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/generate")
@limiter.limit("10/hour")
async def generate_video(...):
    ...
```

## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Job not found
- `422`: Validation error
- `500`: Internal server error

All error responses include a detail message:
```json
{
  "detail": "Error message here"
}
```

## Troubleshooting

### API Won't Start

1. Check that required API keys are set
2. Verify port 8000 is available
3. Check Python version (requires 3.8+)

### Jobs Stay in "queued" State

1. Check background task execution
2. Verify API keys are valid
3. Check server logs for errors

### Videos Not Accessible

1. Verify output directory exists and is readable
2. Check static file mount configuration
3. Ensure video generation completed successfully

## Support

For issues and questions:
- Check the [main README](README.md)
- Review server logs
- Open an issue on GitHub
