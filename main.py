#!/usr/bin/env python3
"""
FastAPI server for the Media Generation Pipeline.
Provides REST API endpoints for video generation with job tracking.
"""

import os
import uuid
import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import config
from cli import MediaGenerationPipeline
from services.job_store import JobStoreService


# Job status enum
class JobStatus(str, Enum):
    QUEUED = "queued"
    GENERATING_SCENES = "generating_scenes"
    GENERATING_CONTENT = "generating_content"
    GENERATING_AUDIO = "generating_audio"
    ASSEMBLING_VIDEO = "assembling_video"
    COMPLETE = "complete"
    FAILED = "failed"


# Request/Response models
class GenerateRequest(BaseModel):
    """Request model for video generation."""
    topic: str = Field(
        ..., 
        description="Topic to generate video about",
        examples=["The History of Space Exploration", "Climate Change Solutions", "Ancient Egyptian Civilization"]
    )
    num_scenes: int = Field(
        8, 
        ge=1, 
        le=20, 
        description="Number of scenes to generate (1-20)"
    )
    use_static_scenes: bool = Field(
        False, 
        description="Use predefined static scenes instead of generating from topic"
    )
    scene_ids: Optional[list[str]] = Field(
        None, 
        description="Specific scene IDs to process (only applicable with use_static_scenes=true)"
    )
    openai_api_key: Optional[str] = Field(
        None,
        description="Optional OpenAI API key (for UI-provided keys). If not provided, uses server configuration."
    )
    stability_api_key: Optional[str] = Field(
        None,
        description="Optional Stability AI API key (for UI-provided keys). If not provided, uses server configuration."
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "topic": "The Solar System",
                    "num_scenes": 8
                },
                {
                    "topic": "The Industrial Revolution",
                    "num_scenes": 5
                },
                {
                    "use_static_scenes": True
                }
            ]
        }
    }


class GenerateResponse(BaseModel):
    """Response model for video generation request."""
    job_id: str = Field(
        ..., 
        description="Unique identifier for the video generation job"
    )
    status: JobStatus = Field(
        ..., 
        description="Current status of the job"
    )
    message: str = Field(
        ..., 
        description="Human-readable message about the job"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "queued",
                    "message": "Video generation job queued. Use /status/{job_id} to check progress."
                }
            ]
        }
    }


class JobStatusResponse(BaseModel):
    """Response model for job status query."""
    job_id: str = Field(
        ..., 
        description="Unique identifier for the job"
    )
    status: JobStatus = Field(
        ..., 
        description="Current status of the job"
    )
    progress: str = Field(
        ..., 
        description="Human-readable progress message"
    )
    created_at: str = Field(
        ..., 
        description="ISO 8601 timestamp when the job was created"
    )
    completed_at: Optional[str] = Field(
        None, 
        description="ISO 8601 timestamp when the job completed or failed"
    )
    video_url: Optional[str] = Field(
        None, 
        description="URL to download the generated video (available when status is 'complete')"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message if the job failed"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "complete",
                    "progress": "Video generation complete!",
                    "created_at": "2024-01-01T12:00:00",
                    "completed_at": "2024-01-01T12:05:30",
                    "video_url": "/outputs/final_video.mp4",
                    "error": None
                },
                {
                    "job_id": "660e8400-e29b-41d4-a716-446655440001",
                    "status": "generating_content",
                    "progress": "Generating images and narration...",
                    "created_at": "2024-01-01T12:00:00",
                    "completed_at": None,
                    "video_url": None,
                    "error": None
                }
            ]
        }
    }


# Job storage (Redis-based for production, with in-memory fallback)
job_store: Optional[JobStoreService] = None

# Legacy in-memory storage (used as fallback if Redis unavailable)
jobs: Dict[str, dict] = {}


# Initialize FastAPI app with enhanced OpenAPI documentation
app = FastAPI(
    title="Media Generation Pipeline API",
    description="""
    ## AI-Powered Video Generation Pipeline
    
    Transform any topic into a complete video narrative with synchronized audio, 
    automated text overlays, and professional MP4 output.
    
    ### Features
    
    * **Dynamic Scene Generation**: LLM-powered scene creation from any topic
    * **Text-to-Speech Audio**: OpenAI TTS integration for professional narration
    * **AI Image Generation**: Stability AI for stunning visual content
    * **MP4 Video Assembly**: MoviePy-based video creation with audio synchronization
    * **Job Tracking**: Real-time status updates for video generation
    * **Production Features**: Ken Burns effect, background music, subtitles
    
    ### Authentication
    
    API key authentication can be enabled by setting the `API_KEY` environment variable.
    When enabled, protected endpoints require the `X-API-Key` header.
    
    ### Workflow
    
    1. Submit a video generation job via `/generate`
    2. Receive a job ID in the response
    3. Poll `/status/{job_id}` to check progress
    4. Download the completed video from the URL in the status response
    """,
    version="2.0.0",
    contact={
        "name": "Media Generation Pipeline",
        "url": "https://github.com/siddhant61/media-generation-pipeline",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "jobs",
            "description": "Operations for managing video generation jobs. **Protected by API key** if configured.",
        },
        {
            "name": "status",
            "description": "Check the status and progress of video generation jobs. **Public endpoint**.",
        },
        {
            "name": "health",
            "description": "Health check and monitoring. **Public endpoint**.",
        },
    ]
)

# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key from request header.
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        The API key if valid
        
    Raises:
        HTTPException: If API key is required but missing or invalid
    """
    # If no API key is configured, allow all requests
    if not config.api_key:
        return None
    
    # If API key is configured, require it
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is required. Provide it in the X-API-Key header."
        )
    
    if api_key != config.api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return api_key


# Validate configuration on startup
@app.on_event("startup")
async def startup_event():
    """Validate configuration and create output directory."""
    global job_store
    try:
        config.validate()
        os.makedirs(config.output_dir, exist_ok=True)
        
        # Initialize Redis job store with retry logic
        try:
            job_store = JobStoreService()
            if job_store.ping():
                print(f"Media Generation Pipeline API started with Redis job store")
            else:
                raise Exception("Redis ping failed")
        except Exception as redis_error:
            print(f"Warning: Could not connect to Redis: {redis_error}")
            print(f"Using in-memory job storage as fallback")
            job_store = None
        
        print(f"Output directory: {config.output_dir}")
    except Exception as e:
        print(f"Configuration error: {e}")
        print("Please set the required environment variables:")
        print("  export OPENAI_API_KEY='your-openai-key'")
        print("  export STABILITY_API_KEY='your-stability-key'")


def get_job(job_id: str) -> Optional[dict]:
    """Get a job from storage (Redis or in-memory)."""
    if job_store:
        try:
            return job_store.get_job(job_id)
        except Exception:
            pass
    return jobs.get(job_id)


def store_job(job_id: str, job_data: dict) -> None:
    """Store a job in storage (Redis or in-memory)."""
    if job_store:
        try:
            job_store.create_job(job_id, job_data)
            return
        except Exception:
            pass
    jobs[job_id] = job_data


def update_job_data(job_id: str, job_data: dict) -> None:
    """Update a job in storage (Redis or in-memory)."""
    if job_store:
        try:
            job_store.update_job(job_id, job_data)
            return
        except Exception:
            pass
    jobs[job_id] = job_data


def list_jobs() -> List[dict]:
    """List all jobs from storage (Redis or in-memory)."""
    if job_store:
        try:
            return job_store.list_all_jobs()
        except Exception:
            pass
    return list(jobs.values())


def job_exists(job_id: str) -> bool:
    """Check if a job exists in storage (Redis or in-memory)."""
    if job_store:
        try:
            return job_store.exists(job_id)
        except Exception:
            pass
    return job_id in jobs


def update_job_status(job_id: str, status: JobStatus, progress: str = "", error: str = None):
    """Update job status in storage."""
    job_data = get_job(job_id)
    if job_data:
        job_data["status"] = status
        job_data["progress"] = progress
        if error:
            job_data["error"] = error
        if status == JobStatus.COMPLETE or status == JobStatus.FAILED:
            job_data["completed_at"] = datetime.utcnow().isoformat()
        update_job_data(job_id, job_data)


async def run_pipeline_job(job_id: str, topic: str, num_scenes: int, use_static_scenes: bool, scene_ids: Optional[list[str]], 
                          openai_api_key: Optional[str] = None, stability_api_key: Optional[str] = None):
    """
    Background task to run the video generation pipeline.
    
    Args:
        job_id: Unique job identifier
        topic: Topic to generate video about
        num_scenes: Number of scenes to generate
        use_static_scenes: Whether to use static scenes
        scene_ids: Specific scene IDs to process
        openai_api_key: Optional OpenAI API key from UI
        stability_api_key: Optional Stability AI API key from UI
    """
    try:
        # Initialize pipeline with custom config if API keys are provided
        pipeline_config = config
        if openai_api_key or stability_api_key:
            # Create a custom config with UI-provided keys
            from config import APIConfig
            pipeline_config = APIConfig(
                openai_api_key=openai_api_key or config.openai_api_key,
                stability_api_key=stability_api_key or config.stability_api_key,
                api_key=config.api_key,
                openai_model=config.openai_model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                stability_seed=config.stability_seed,
                stability_steps=config.stability_steps,
                stability_cfg_scale=config.stability_cfg_scale,
                stability_width=config.stability_width,
                stability_height=config.stability_height,
                stability_samples=config.stability_samples,
                output_dir=config.output_dir,
                font_size=config.font_size,
                llm_config=config.llm_config,
                tts_config=config.tts_config,
                video_config=config.video_config
            )
        
        # Initialize pipeline
        update_job_status(job_id, JobStatus.GENERATING_SCENES, "Initializing pipeline...")
        pipeline = MediaGenerationPipeline(pipeline_config, use_static_scenes=use_static_scenes)
        
        # Generate scenes if using topic
        if topic and not use_static_scenes:
            update_job_status(job_id, JobStatus.GENERATING_SCENES, f"Generating {num_scenes} scenes...")
            pipeline.scene_manager.generate_scenes(topic, num_scenes)
        
        # Generate content
        update_job_status(job_id, JobStatus.GENERATING_CONTENT, "Generating images and narration...")
        content_results = pipeline.generate_content(scene_ids)
        
        # Update progress for audio generation
        scenes = pipeline.scene_manager.get_all_scenes()
        total_scenes = len(scenes)
        for idx, (scene_id, scene) in enumerate(scenes.items(), 1):
            if scene.narration and scene.audio_file:
                update_job_status(
                    job_id, 
                    JobStatus.GENERATING_AUDIO,
                    f"Processing audio {idx}/{total_scenes}"
                )
        
        # Create video
        update_job_status(job_id, JobStatus.ASSEMBLING_VIDEO, "Assembling final video...")
        visualization_results = pipeline.create_visualizations(content_results)
        
        # Job complete
        video_path = visualization_results.get('video')
        if video_path:
            video_filename = os.path.basename(video_path)
            video_url = f"/outputs/{video_filename}"
            job_data = get_job(job_id)
            if job_data:
                job_data["video_url"] = video_url
                update_job_data(job_id, job_data)
            update_job_status(job_id, JobStatus.COMPLETE, "Video generation complete!")
        else:
            update_job_status(job_id, JobStatus.FAILED, error="Failed to create video")
        
    except Exception as e:
        error_msg = f"Pipeline error: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        update_job_status(job_id, JobStatus.FAILED, error=error_msg)


@app.post(
    "/generate", 
    response_model=GenerateResponse,
    tags=["jobs"],
    summary="Generate a video from a topic",
    response_description="Job created successfully with unique job ID"
)
async def generate_video(
    request: GenerateRequest, 
    background_tasks: BackgroundTasks,
    api_key: str = Security(verify_api_key)
):
    """
    ## Generate a Video from a Topic
    
    Submit a video generation job that creates a complete video with:
    - AI-generated scenes based on your topic
    - Professional narration using text-to-speech
    - AI-generated images for each scene
    - Synchronized audio and video assembly
    
    ### Workflow
    
    1. Submit this request with your topic
    2. Receive a job ID immediately
    3. Poll `/status/{job_id}` to track progress
    4. Download the video when complete
    
    ### Authentication
    
    **Protected endpoint**: Requires API key if configured (X-API-Key header)
    
    ### Example Request
    
    ```json
    {
        "topic": "The History of Space Exploration",
        "num_scenes": 8
    }
    ```
    """
    # Validate request
    if not request.use_static_scenes and not request.topic:
        raise HTTPException(
            status_code=400,
            detail="Please provide a topic or use static scenes"
        )
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job in storage
    job_data = {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "progress": "Job queued",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "video_url": None,
        "error": None,
        "topic": request.topic if not request.use_static_scenes else None,
        "num_scenes": request.num_scenes,
        "use_static_scenes": request.use_static_scenes
    }
    store_job(job_id, job_data)
    
    # Add background task
    background_tasks.add_task(
        run_pipeline_job,
        job_id,
        request.topic,
        request.num_scenes,
        request.use_static_scenes,
        request.scene_ids,
        request.openai_api_key,
        request.stability_api_key
    )
    
    return GenerateResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="Video generation job queued. Use /status/{job_id} to check progress."
    )


@app.get(
    "/status/{job_id}", 
    response_model=JobStatusResponse,
    tags=["status"],
    summary="Get job status and progress",
    response_description="Current job status with progress information"
)
async def get_job_status(job_id: str):
    """
    ## Get Job Status and Progress
    
    Retrieve the current status, progress, and results of a video generation job.
    
    ### Job Statuses
    
    - **queued**: Job is queued for processing
    - **generating_scenes**: Generating scenes from topic
    - **generating_content**: Creating images and narration
    - **generating_audio**: Synthesizing audio narration
    - **assembling_video**: Assembling final video
    - **complete**: Video generation complete (video_url available)
    - **failed**: Job failed (error message available)
    
    ### Public Endpoint
    
    This endpoint is **always accessible** without authentication.
    
    ### Example Response
    
    ```json
    {
        "job_id": "abc123",
        "status": "complete",
        "progress": "Video generation complete!",
        "created_at": "2024-01-01T12:00:00",
        "completed_at": "2024-01-01T12:05:30",
        "video_url": "/outputs/final_video.mp4"
    }
    ```
    """
    if not job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = get_job(job_id)
    
    return JobStatusResponse(
        job_id=job_data["job_id"],
        status=job_data["status"],
        progress=job_data["progress"],
        created_at=job_data["created_at"],
        completed_at=job_data.get("completed_at"),
        video_url=job_data.get("video_url"),
        error=job_data.get("error")
    )


@app.get(
    "/jobs",
    tags=["jobs"],
    summary="List all jobs",
    response_description="List of all video generation jobs"
)
async def list_all_jobs(api_key: str = Security(verify_api_key)):
    """
    ## List All Video Generation Jobs
    
    Retrieve a list of all video generation jobs with their current status.
    
    ### Authentication
    
    **Protected endpoint**: Requires API key if configured (X-API-Key header)
    
    ### Response
    
    Returns an array of job objects, each containing:
    - Job ID
    - Current status
    - Progress information
    - Creation and completion timestamps
    - Video URL (if complete)
    - Error message (if failed)
    """
    return {"jobs": list_jobs()}


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    response_description="API health status"
)
async def health_check():
    """
    ## Health Check
    
    Check if the API is running and healthy.
    
    ### Public Endpoint
    
    This endpoint is **always accessible** without authentication.
    
    ### Response
    
    Returns the service name, version, and health status.
    """
    return {
        "status": "healthy",
        "service": "Media Generation Pipeline API",
        "version": "2.0.0"
    }


# Mount static files directory for serving generated videos
# Create the output directory if it doesn't exist
os.makedirs(config.output_dir, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=config.output_dir), name="outputs")

# Mount UI directory for serving the frontend application
# This should be mounted last to avoid conflicts with API routes
ui_dir = os.path.join(os.path.dirname(__file__), "ui")
if os.path.exists(ui_dir):
    app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")
    print(f"UI mounted at / from {ui_dir}")
else:
    print(f"Warning: UI directory not found at {ui_dir}")


# Main entry point for running with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
