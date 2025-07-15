#!/usr/bin/env python3
"""
Setup script for the Media Generation Pipeline.
Helps users configure the project and check dependencies.
"""

import os
import sys
import subprocess
import pkg_resources
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def install_dependencies():
    """Install required dependencies."""
    print("\n📦 Installing dependencies...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        "openai>=1.0.0",
        "stability-sdk>=0.8.0",
        "pillow>=9.0.0",
        "numpy>=1.21.0",
        "torch>=1.12.0",
        "opencv-python>=4.5.0",
        "matplotlib>=3.5.0",
        "IPython>=8.0.0",
        "requests>=2.28.0"
    ]
    
    missing_packages = []
    
    for requirement in required_packages:
        try:
            pkg_resources.require(requirement)
            print(f"✅ {requirement.split('>=')[0]}")
        except pkg_resources.DistributionNotFound:
            print(f"❌ {requirement.split('>=')[0]} - Not installed")
            missing_packages.append(requirement)
        except pkg_resources.VersionConflict:
            print(f"⚠️  {requirement.split('>=')[0]} - Version conflict")
            missing_packages.append(requirement)
    
    return len(missing_packages) == 0

def setup_environment():
    """Help user set up environment variables."""
    print("\n🔧 Environment Setup")
    print("="*50)
    
    # Check for API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    stability_key = os.getenv('STABILITY_API_KEY')
    
    if openai_key:
        print(f"✅ OPENAI_API_KEY: {'*' * (len(openai_key) - 4)}{openai_key[-4:]}")
    else:
        print("❌ OPENAI_API_KEY: Not set")
        print("   Get your key from: https://platform.openai.com/api-keys")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
    
    if stability_key:
        print(f"✅ STABILITY_API_KEY: {'*' * (len(stability_key) - 4)}{stability_key[-4:]}")
    else:
        print("❌ STABILITY_API_KEY: Not set")
        print("   Get your key from: https://platform.stability.ai/account/keys")
        print("   Set it with: export STABILITY_API_KEY='your-key-here'")
    
    return openai_key and stability_key

def create_directories():
    """Create necessary output directories."""
    print("\n📁 Creating output directories...")
    
    directories = [
        "generated_content",
        "generated_content/transitions",
        "generated_content/overlays",
        "generated_content/storyboards"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")

def test_basic_functionality():
    """Test basic functionality without API calls."""
    print("\n🧪 Testing basic functionality...")
    
    try:
        # Test imports
        from config import config
        from scene_manager import SceneManager
        print("✅ Core modules import successfully")
        
        # Test scene manager
        scene_manager = SceneManager()
        scenes = scene_manager.get_all_scenes()
        print(f"✅ Scene manager loaded {len(scenes)} scenes")
        
        # Test configuration
        print(f"✅ Configuration loaded, output dir: {config.output_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Media Generation Pipeline Setup")
    print("="*50)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Install or check dependencies
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        if not install_dependencies():
            return 1
    else:
        if not check_dependencies():
            print("\n💡 Run 'python setup.py --install' to install missing dependencies")
            return 1
    
    # Create directories
    create_directories()
    
    # Test basic functionality
    if not test_basic_functionality():
        return 1
    
    # Setup environment
    env_ready = setup_environment()
    
    # Final status
    print("\n" + "="*50)
    if env_ready:
        print("🎉 Setup complete! You're ready to run the pipeline.")
        print("\nQuick start:")
        print("  python main.py --single 'Scene 1'")
        print("  python example_usage.py")
        print("  python main.py  # Run complete pipeline")
    else:
        print("⚠️  Setup incomplete - please configure your API keys")
        print("\nAfter setting API keys, test with:")
        print("  python example_usage.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 