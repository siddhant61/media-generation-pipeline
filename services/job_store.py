"""
Job Store Service for persisting job data in Redis.
Provides a clean interface for storing and retrieving job information.
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import redis


class JobStoreService:
    """
    Service for storing and retrieving job data using Redis.
    
    Attributes:
        redis_client: Redis client instance
        key_prefix: Prefix for all Redis keys to namespace job data
    """
    
    def __init__(self, redis_url: Optional[str] = None, key_prefix: str = "job:"):
        """
        Initialize the job store with Redis connection.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
                      If None, defaults to localhost:6379
            key_prefix: Prefix for Redis keys (default: "job:")
        """
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = key_prefix
    
    def _get_key(self, job_id: str) -> str:
        """Generate Redis key for a job ID."""
        return f"{self.key_prefix}{job_id}"
    
    def _get_index_key(self) -> str:
        """Get Redis key for the job index (set of all job IDs)."""
        return f"{self.key_prefix}index"
    
    def create_job(self, job_id: str, job_data: Dict) -> None:
        """
        Create a new job in Redis.
        
        Args:
            job_id: Unique job identifier
            job_data: Job data dictionary to store
        """
        key = self._get_key(job_id)
        # Store job data as JSON
        self.redis_client.set(key, json.dumps(job_data))
        # Add job ID to index
        self.redis_client.sadd(self._get_index_key(), job_id)
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """
        Retrieve a job from Redis.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job data dictionary or None if not found
        """
        key = self._get_key(job_id)
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def update_job(self, job_id: str, job_data: Dict) -> None:
        """
        Update an existing job in Redis.
        
        Args:
            job_id: Job identifier
            job_data: Updated job data dictionary
        """
        key = self._get_key(job_id)
        self.redis_client.set(key, json.dumps(job_data))
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from Redis.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job was deleted, False if it didn't exist
        """
        key = self._get_key(job_id)
        result = self.redis_client.delete(key)
        if result:
            # Remove from index
            self.redis_client.srem(self._get_index_key(), job_id)
        return bool(result)
    
    def list_all_jobs(self) -> List[Dict]:
        """
        List all jobs from Redis.
        
        Returns:
            List of job data dictionaries
        """
        index_key = self._get_index_key()
        job_ids = self.redis_client.smembers(index_key)
        
        jobs = []
        for job_id in job_ids:
            job_data = self.get_job(job_id)
            if job_data:
                jobs.append(job_data)
        
        return jobs
    
    def exists(self, job_id: str) -> bool:
        """
        Check if a job exists in Redis.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job exists, False otherwise
        """
        key = self._get_key(job_id)
        return bool(self.redis_client.exists(key))
    
    def clear_all_jobs(self) -> int:
        """
        Clear all jobs from Redis (useful for testing).
        
        Returns:
            Number of jobs deleted
        """
        index_key = self._get_index_key()
        job_ids = self.redis_client.smembers(index_key)
        
        count = 0
        for job_id in job_ids:
            if self.delete_job(job_id):
                count += 1
        
        return count
    
    def ping(self) -> bool:
        """
        Check if Redis connection is alive.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            return self.redis_client.ping()
        except Exception:
            return False
