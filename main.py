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

from fastapi import FastAPI, HTTPException, BackgroundTasks
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
    topic: str = Field(..., description="Topic to generate video about")
    num_scenes: int = Field(8, ge=1, le=20, description="Number of scenes to generate")
    use_static_scenes: bool = Field(False, description="Use predefined static scenes")
    scene_ids: Optional[list[str]] = Field(None, description="Specific scene IDs to process (only with static scenes)")


class GenerateResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: str
    created_at: str
    completed_at: Optional[str] = None
    video_url: Optional[str] = None
    error: Optional[str] = None


# Job storage (Redis-based for production, with in-memory fallback)
job_store: Optional[JobStoreService] = None

# Legacy in-memory storage (used as fallback if Redis unavailable)
jobs: Dict[str, dict] = {}


# Initialize FastAPI app
app = FastAPI(
    title="Media Generation Pipeline API",
    description="AI-powered video generation from topics using LLM, TTS, and image generation",
    version="2.0.0"
)


# Validate configuration on startup
@app.on_event("startup")
async def startup_event():
    """Validate configuration and create output directory."""
    global job_store
    try:
        config.validate()
        os.makedirs(config.output_dir, exist_ok=True)
        
        # Initialize Redis job store
        try:
            job_store = JobStoreService()
            if job_store.ping():
                print(f"Media Generation Pipeline API started with Redis job store")
            else:
                print(f"Warning: Redis connection failed, using in-memory job storage")
                job_store = None
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
    if job_store and job_store.ping():
        return job_store.get_job(job_id)
    return jobs.get(job_id)


def store_job(job_id: str, job_data: dict) -> None:
    """Store a job in storage (Redis or in-memory)."""
    if job_store and job_store.ping():
        job_store.create_job(job_id, job_data)
    else:
        jobs[job_id] = job_data


def update_job_data(job_id: str, job_data: dict) -> None:
    """Update a job in storage (Redis or in-memory)."""
    if job_store and job_store.ping():
        job_store.update_job(job_id, job_data)
    else:
        jobs[job_id] = job_data


def list_jobs() -> List[dict]:
    """List all jobs from storage (Redis or in-memory)."""
    if job_store and job_store.ping():
        return job_store.list_all_jobs()
    return list(jobs.values())


def job_exists(job_id: str) -> bool:
    """Check if a job exists in storage (Redis or in-memory)."""
    if job_store and job_store.ping():
        return job_store.exists(job_id)
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


async def run_pipeline_job(job_id: str, topic: str, num_scenes: int, use_static_scenes: bool, scene_ids: Optional[list[str]]):
    """
    Background task to run the video generation pipeline.
    
    Args:
        job_id: Unique job identifier
        topic: Topic to generate video about
        num_scenes: Number of scenes to generate
        use_static_scenes: Whether to use static scenes
        scene_ids: Specific scene IDs to process
    """
    try:
        # Initialize pipeline
        update_job_status(job_id, JobStatus.GENERATING_SCENES, "Initializing pipeline...")
        pipeline = MediaGenerationPipeline(config, use_static_scenes=use_static_scenes)
        
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


@app.post("/generate", response_model=GenerateResponse)
async def generate_video(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate a video from a topic or using static scenes.
    
    This endpoint queues a video generation job and returns immediately with a job ID.
    Use the /status/{job_id} endpoint to check the job status.
    
    Args:
        request: Generation request parameters
        background_tasks: FastAPI background tasks
        
    Returns:
        Job ID and initial status
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
        request.scene_ids
    )
    
    return GenerateResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="Video generation job queued. Use /status/{job_id} to check progress."
    )


@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a video generation job.
    
    Args:
        job_id: The job ID returned from the /generate endpoint
        
    Returns:
        Current job status, progress, and video URL if complete
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


@app.get("/jobs")
async def list_all_jobs():
    """
    List all jobs.
    
    Returns:
        List of all jobs with their current status
    """
    return {"jobs": list_jobs()}


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        API health status
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


# Main entry point for running with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
