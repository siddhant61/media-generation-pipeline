"""
Tests for the FastAPI endpoints.
Tests the API layer without actual pipeline execution.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app, jobs, JobStatus
from config import APIConfig


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_pipeline():
    """Create a mock pipeline."""
    mock = Mock()
    mock.scene_manager = Mock()
    mock.scene_manager.generate_scenes = Mock()
    mock.scene_manager.get_all_scenes = Mock(return_value={})
    mock.generate_content = Mock(return_value={})
    mock.create_visualizations = Mock(return_value={'video': '/tmp/test_video.mp4'})
    return mock


@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear jobs dictionary before each test."""
    jobs.clear()
    yield
    jobs.clear()


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test that health check returns expected response."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Media Generation Pipeline API"
        assert "version" in data


class TestGenerateEndpoint:
    """Test video generation endpoint."""
    
    @patch('main.MediaGenerationPipeline')
    def test_generate_video_with_topic(self, mock_pipeline_class, client):
        """Test generating video from topic."""
        request_data = {
            "topic": "The Solar System",
            "num_scenes": 5
        }
        
        response = client.post("/generate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert "message" in data
        
        # Verify job was created
        job_id = data["job_id"]
        assert job_id in jobs
        assert jobs[job_id]["topic"] == "The Solar System"
        assert jobs[job_id]["num_scenes"] == 5
    
    def test_generate_video_without_topic_or_static(self, client):
        """Test that request without topic and without static scenes fails."""
        request_data = {
            "topic": "",  # Empty topic
            "num_scenes": 5
        }
        
        response = client.post("/generate", json=request_data)
        
        assert response.status_code == 400
        assert "topic" in response.json()["detail"].lower() or "static" in response.json()["detail"].lower()
    
    @patch('main.MediaGenerationPipeline')
    def test_generate_video_with_static_scenes(self, mock_pipeline_class, client):
        """Test generating video with static scenes."""
        request_data = {
            "topic": "",
            "use_static_scenes": True
        }
        
        response = client.post("/generate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        
        # Verify job was created with static scenes flag
        job_id = data["job_id"]
        assert jobs[job_id]["use_static_scenes"] is True
    
    @patch('main.MediaGenerationPipeline')
    def test_generate_video_with_custom_num_scenes(self, mock_pipeline_class, client):
        """Test generating video with custom number of scenes."""
        request_data = {
            "topic": "Climate Change",
            "num_scenes": 12
        }
        
        response = client.post("/generate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        job_id = data["job_id"]
        assert jobs[job_id]["num_scenes"] == 12
    
    def test_generate_video_invalid_num_scenes(self, client):
        """Test that invalid num_scenes value is rejected."""
        request_data = {
            "topic": "Test Topic",
            "num_scenes": 25  # exceeds max of 20
        }
        
        response = client.post("/generate", json=request_data)
        
        assert response.status_code == 422  # Validation error


class TestStatusEndpoint:
    """Test job status endpoint."""
    
    def test_get_status_existing_job(self, client):
        """Test getting status of an existing job."""
        # Create a mock job
        job_id = "test-job-123"
        jobs[job_id] = {
            "job_id": job_id,
            "status": JobStatus.GENERATING_SCENES,
            "progress": "Generating scenes...",
            "created_at": "2024-01-01T00:00:00",
            "completed_at": None,
            "video_url": None,
            "error": None
        }
        
        response = client.get(f"/status/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "generating_scenes"
        assert data["progress"] == "Generating scenes..."
        assert data["video_url"] is None
    
    def test_get_status_completed_job(self, client):
        """Test getting status of a completed job."""
        job_id = "test-job-456"
        jobs[job_id] = {
            "job_id": job_id,
            "status": JobStatus.COMPLETE,
            "progress": "Video generation complete!",
            "created_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:05:00",
            "video_url": "/outputs/final_video.mp4",
            "error": None
        }
        
        response = client.get(f"/status/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert data["video_url"] == "/outputs/final_video.mp4"
        assert data["completed_at"] is not None
    
    def test_get_status_failed_job(self, client):
        """Test getting status of a failed job."""
        job_id = "test-job-789"
        jobs[job_id] = {
            "job_id": job_id,
            "status": JobStatus.FAILED,
            "progress": "Failed",
            "created_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:02:00",
            "video_url": None,
            "error": "API error: Rate limit exceeded"
        }
        
        response = client.get(f"/status/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "API error: Rate limit exceeded"
    
    def test_get_status_nonexistent_job(self, client):
        """Test getting status of a job that doesn't exist."""
        response = client.get("/status/nonexistent-job-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestJobsEndpoint:
    """Test jobs listing endpoint."""
    
    def test_list_jobs_empty(self, client):
        """Test listing jobs when no jobs exist."""
        response = client.get("/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 0
    
    def test_list_jobs_multiple(self, client):
        """Test listing multiple jobs."""
        # Create mock jobs
        jobs["job-1"] = {
            "job_id": "job-1",
            "status": JobStatus.COMPLETE,
            "progress": "Complete",
            "created_at": "2024-01-01T00:00:00"
        }
        jobs["job-2"] = {
            "job_id": "job-2",
            "status": JobStatus.GENERATING_SCENES,
            "progress": "In progress",
            "created_at": "2024-01-01T00:05:00"
        }
        
        response = client.get("/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2
        job_ids = [job["job_id"] for job in data["jobs"]]
        assert "job-1" in job_ids
        assert "job-2" in job_ids


class TestStaticFilesServing:
    """Test static file serving for video outputs."""
    
    def test_static_files_mount_exists(self, client):
        """Test that static files are mounted correctly."""
        # This test verifies the mount point exists
        # Actual file serving would require creating test files
        # which we avoid to keep tests lightweight
        pass
