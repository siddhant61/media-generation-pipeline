"""
Tests for the JobStoreService.
Tests Redis job storage functionality with mocked Redis client.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.job_store import JobStoreService


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.ping.return_value = True
    return mock


@pytest.fixture
def job_store(mock_redis):
    """Create a JobStoreService with mocked Redis."""
    with patch('services.job_store.redis.from_url', return_value=mock_redis):
        store = JobStoreService(redis_url='redis://localhost:6379/0')
        return store


class TestJobStoreService:
    """Test JobStoreService functionality."""
    
    def test_create_job(self, job_store, mock_redis):
        """Test creating a new job."""
        job_id = "test-job-123"
        job_data = {
            "job_id": job_id,
            "status": "queued",
            "progress": "Job queued"
        }
        
        job_store.create_job(job_id, job_data)
        
        # Verify Redis set was called
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == f"job:{job_id}"
        assert json.loads(call_args[0][1]) == job_data
        
        # Verify job was added to index
        mock_redis.sadd.assert_called_once_with("job:index", job_id)
    
    def test_get_job_exists(self, job_store, mock_redis):
        """Test retrieving an existing job."""
        job_id = "test-job-456"
        job_data = {
            "job_id": job_id,
            "status": "complete",
            "video_url": "/outputs/video.mp4"
        }
        
        mock_redis.get.return_value = json.dumps(job_data)
        
        result = job_store.get_job(job_id)
        
        assert result == job_data
        mock_redis.get.assert_called_once_with(f"job:{job_id}")
    
    def test_get_job_not_exists(self, job_store, mock_redis):
        """Test retrieving a non-existent job."""
        mock_redis.get.return_value = None
        
        result = job_store.get_job("nonexistent-job")
        
        assert result is None
    
    def test_update_job(self, job_store, mock_redis):
        """Test updating an existing job."""
        job_id = "test-job-789"
        updated_data = {
            "job_id": job_id,
            "status": "complete",
            "progress": "Done!"
        }
        
        job_store.update_job(job_id, updated_data)
        
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == f"job:{job_id}"
        assert json.loads(call_args[0][1]) == updated_data
    
    def test_delete_job(self, job_store, mock_redis):
        """Test deleting a job."""
        job_id = "test-job-delete"
        mock_redis.delete.return_value = 1  # 1 key deleted
        
        result = job_store.delete_job(job_id)
        
        assert result is True
        mock_redis.delete.assert_called_once_with(f"job:{job_id}")
        mock_redis.srem.assert_called_once_with("job:index", job_id)
    
    def test_delete_nonexistent_job(self, job_store, mock_redis):
        """Test deleting a non-existent job."""
        mock_redis.delete.return_value = 0  # 0 keys deleted
        
        result = job_store.delete_job("nonexistent")
        
        assert result is False
    
    def test_list_all_jobs(self, job_store, mock_redis):
        """Test listing all jobs."""
        job_ids = ["job-1", "job-2", "job-3"]
        mock_redis.smembers.return_value = job_ids
        
        # Mock get_job to return data for each job
        def mock_get_side_effect(key):
            job_id = key.replace("job:", "")
            return json.dumps({"job_id": job_id, "status": "queued"})
        
        mock_redis.get.side_effect = mock_get_side_effect
        
        result = job_store.list_all_jobs()
        
        assert len(result) == 3
        assert all(job["job_id"] in job_ids for job in result)
        mock_redis.smembers.assert_called_once_with("job:index")
    
    def test_exists_true(self, job_store, mock_redis):
        """Test checking if a job exists (positive case)."""
        mock_redis.exists.return_value = 1
        
        result = job_store.exists("existing-job")
        
        assert result is True
        mock_redis.exists.assert_called_once_with("job:existing-job")
    
    def test_exists_false(self, job_store, mock_redis):
        """Test checking if a job exists (negative case)."""
        mock_redis.exists.return_value = 0
        
        result = job_store.exists("nonexistent-job")
        
        assert result is False
    
    def test_ping_success(self, job_store, mock_redis):
        """Test Redis ping success."""
        mock_redis.ping.return_value = True
        
        result = job_store.ping()
        
        assert result is True
    
    def test_ping_failure(self, job_store, mock_redis):
        """Test Redis ping failure."""
        mock_redis.ping.side_effect = Exception("Connection failed")
        
        result = job_store.ping()
        
        assert result is False
    
    def test_clear_all_jobs(self, job_store, mock_redis):
        """Test clearing all jobs."""
        job_ids = ["job-1", "job-2"]
        mock_redis.smembers.return_value = job_ids
        mock_redis.delete.return_value = 1  # Each delete succeeds
        
        count = job_store.clear_all_jobs()
        
        assert count == 2
        assert mock_redis.delete.call_count == 2
    
    def test_custom_key_prefix(self, mock_redis):
        """Test using a custom key prefix."""
        with patch('services.job_store.redis.from_url', return_value=mock_redis):
            store = JobStoreService(key_prefix="custom:")
            
            job_id = "test-job"
            job_data = {"job_id": job_id}
            
            store.create_job(job_id, job_data)
            
            # Check that custom prefix was used
            call_args = mock_redis.set.call_args
            assert call_args[0][0] == f"custom:{job_id}"
    
    def test_redis_url_from_env(self, mock_redis):
        """Test that Redis URL can be loaded from environment."""
        with patch('services.job_store.redis.from_url', return_value=mock_redis) as mock_from_url:
            with patch.dict(os.environ, {'REDIS_URL': 'redis://custom-host:6379/1'}):
                store = JobStoreService()
                
                # Verify correct URL was used
                mock_from_url.assert_called_once()
                assert 'redis://custom-host:6379/1' in str(mock_from_url.call_args)
