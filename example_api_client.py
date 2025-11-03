#!/usr/bin/env python3
"""
Example API client for the Media Generation Pipeline.
Demonstrates how to use the REST API to generate videos programmatically.
"""

import requests
import time
import sys


def generate_video(topic: str, num_scenes: int = 8, base_url: str = "http://localhost:8000"):
    """
    Generate a video using the API.
    
    Args:
        topic: Topic to generate video about
        num_scenes: Number of scenes to generate
        base_url: Base URL of the API server
        
    Returns:
        Path to the generated video or None if failed
    """
    print(f"🎬 Generating video about: {topic}")
    print(f"📊 Number of scenes: {num_scenes}")
    print()
    
    # 1. Submit generation job
    print("📤 Submitting job...")
    try:
        response = requests.post(
            f"{base_url}/generate",
            json={
                "topic": topic,
                "num_scenes": num_scenes
            }
        )
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ Job submitted: {job_id}")
        print()
    except Exception as e:
        print(f"❌ Failed to submit job: {e}")
        return None
    
    # 2. Poll for completion
    print("⏳ Waiting for completion...")
    last_status = None
    
    while True:
        try:
            status_response = requests.get(f"{base_url}/status/{job_id}")
            status_response.raise_for_status()
            status_data = status_response.json()
            
            current_status = status_data['status']
            progress = status_data['progress']
            
            # Only print if status changed
            if current_status != last_status:
                status_emoji = {
                    'queued': '📋',
                    'generating_scenes': '🎬',
                    'generating_content': '🎨',
                    'generating_audio': '🎙️',
                    'assembling_video': '🎥',
                    'complete': '✅',
                    'failed': '❌'
                }.get(current_status, '⏳')
                
                print(f"{status_emoji} {current_status}: {progress}")
                last_status = current_status
            
            if current_status == "complete":
                video_url = status_data.get("video_url")
                if video_url:
                    full_url = f"{base_url}{video_url}"
                    print()
                    print(f"🎉 Video generation complete!")
                    print(f"📹 Video URL: {full_url}")
                    print(f"⏱️  Duration: {status_data.get('completed_at', 'N/A')}")
                    return full_url
                else:
                    print("❌ Video URL not found")
                    return None
                    
            elif current_status == "failed":
                error = status_data.get("error", "Unknown error")
                print(f"❌ Job failed: {error}")
                return None
            
            # Wait before next poll
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
            print(f"Job ID: {job_id} (still running in background)")
            return None
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            time.sleep(5)
            continue


def main():
    """Main entry point."""
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python example_api_client.py <topic> [num_scenes] [base_url]")
        print()
        print("Examples:")
        print("  python example_api_client.py 'The Solar System'")
        print("  python example_api_client.py 'Climate Change' 6")
        print("  python example_api_client.py 'Ancient Egypt' 8 http://api.example.com:8000")
        sys.exit(1)
    
    topic = sys.argv[1]
    num_scenes = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    base_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"
    
    # Check if API is running
    try:
        health_response = requests.get(f"{base_url}/health", timeout=2)
        health_response.raise_for_status()
        print(f"✅ API server is running at {base_url}")
        print()
    except Exception as e:
        print(f"❌ Cannot connect to API server at {base_url}")
        print(f"   Error: {e}")
        print()
        print("Make sure the API server is running:")
        print("  uvicorn main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    # Generate video
    video_url = generate_video(topic, num_scenes, base_url)
    
    if video_url:
        print()
        print("🎊 Success! You can now:")
        print(f"  • View in browser: {video_url}")
        print(f"  • Download: curl -O {video_url}")
        sys.exit(0)
    else:
        print()
        print("❌ Video generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
