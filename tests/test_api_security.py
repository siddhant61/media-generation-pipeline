"""
Tests for API key authentication.
Tests security features for protected endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app, jobs
from config import config


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear jobs dictionary before each test."""
    jobs.clear()
    yield
    jobs.clear()


class TestAPIKeyAuthenticationDisabled:
    """Test API behavior when API key is not configured."""
    
    @patch('main.MediaGenerationPipeline')
    def test_generate_without_api_key_when_disabled(self, mock_pipeline_class, client):
        """Test that /generate works without API key when not configured."""
        # Ensure API key is not configured
        original_api_key = config.api_key
        config.api_key = None
        
        try:
            request_data = {
                "topic": "Test Topic",
                "num_scenes": 5
            }
            
            response = client.post("/generate", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
        finally:
            config.api_key = original_api_key
    
    def test_list_jobs_without_api_key_when_disabled(self, client):
        """Test that /jobs works without API key when not configured."""
        # Ensure API key is not configured
        original_api_key = config.api_key
        config.api_key = None
        
        try:
            response = client.get("/jobs")
            
            assert response.status_code == 200
            data = response.json()
            assert "jobs" in data
        finally:
            config.api_key = original_api_key


class TestAPIKeyAuthenticationEnabled:
    """Test API behavior when API key is configured."""
    
    @patch('main.MediaGenerationPipeline')
    def test_generate_without_api_key_when_enabled(self, mock_pipeline_class, client):
        """Test that /generate rejects requests without API key when configured."""
        # Configure API key
        original_api_key = config.api_key
        config.api_key = "test-api-key-12345"
        
        try:
            request_data = {
                "topic": "Test Topic",
                "num_scenes": 5
            }
            
            response = client.post("/generate", json=request_data)
            
            assert response.status_code == 401
            assert "API key is required" in response.json()["detail"]
        finally:
            config.api_key = original_api_key
    
    @patch('main.MediaGenerationPipeline')
    def test_generate_with_invalid_api_key(self, mock_pipeline_class, client):
        """Test that /generate rejects requests with invalid API key."""
        # Configure API key
        original_api_key = config.api_key
        config.api_key = "test-api-key-12345"
        
        try:
            request_data = {
                "topic": "Test Topic",
                "num_scenes": 5
            }
            headers = {"X-API-Key": "wrong-key"}
            
            response = client.post("/generate", json=request_data, headers=headers)
            
            assert response.status_code == 403
            assert "Invalid API key" in response.json()["detail"]
        finally:
            config.api_key = original_api_key
    
    @patch('main.MediaGenerationPipeline')
    def test_generate_with_valid_api_key(self, mock_pipeline_class, client):
        """Test that /generate accepts requests with valid API key."""
        # Configure API key
        original_api_key = config.api_key
        config.api_key = "test-api-key-12345"
        
        try:
            request_data = {
                "topic": "Test Topic",
                "num_scenes": 5
            }
            headers = {"X-API-Key": "test-api-key-12345"}
            
            response = client.post("/generate", json=request_data, headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
        finally:
            config.api_key = original_api_key
    
    def test_list_jobs_without_api_key_when_enabled(self, client):
        """Test that /jobs rejects requests without API key when configured."""
        # Configure API key
        original_api_key = config.api_key
        config.api_key = "test-api-key-12345"
        
        try:
            response = client.get("/jobs")
            
            assert response.status_code == 401
            assert "API key is required" in response.json()["detail"]
        finally:
            config.api_key = original_api_key
    
    def test_list_jobs_with_invalid_api_key(self, client):
        """Test that /jobs rejects requests with invalid API key."""
        # Configure API key
        original_api_key = config.api_key
        config.api_key = "test-api-key-12345"
        
        try:
            headers = {"X-API-Key": "wrong-key"}
            response = client.get("/jobs", headers=headers)
            
            assert response.status_code == 403
            assert "Invalid API key" in response.json()["detail"]
        finally:
            config.api_key = original_api_key
    
    def test_list_jobs_with_valid_api_key(self, client):
        """Test that /jobs accepts requests with valid API key."""
        # Configure API key
        original_api_key = config.api_key
        config.api_key = "test-api-key-12345"
        
        try:
            headers = {"X-API-Key": "test-api-key-12345"}
            response = client.get("/jobs", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "jobs" in data
        finally:
            config.api_key = original_api_key


class TestUnprotectedEndpoints:
    """Test that public endpoints remain accessible."""
    
    def test_health_check_always_accessible(self, client):
        """Test that /health is always accessible without API key."""
        # Configure API key to ensure health check is still public
        original_api_key = config.api_key
        config.api_key = "test-api-key-12345"
        
        try:
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        finally:
            config.api_key = original_api_key
    
    def test_status_endpoint_always_accessible(self, client):
        """Test that /status/{job_id} is accessible without API key."""
        # Create a test job
        jobs["test-job-id"] = {
            "job_id": "test-job-id",
            "status": "queued",
            "progress": "Queued",
            "created_at": "2024-01-01T00:00:00"
        }
        
        # Configure API key
        original_api_key = config.api_key
        config.api_key = "test-api-key-12345"
        
        try:
            response = client.get("/status/test-job-id")
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "test-job-id"
        finally:
            config.api_key = original_api_key
