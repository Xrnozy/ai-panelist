"""
Quick test script to verify AI Panel Review System
Run this to check everything is working before hackathon
"""

import sys
import subprocess
import json
import time
from pathlib import Path

def print_header(msg):
    print("\n" + "="*60)
    print(f"  {msg}")
    print("="*60)

def print_success(msg):
    print(f"  ✓ {msg}")

def print_error(msg):
    print(f"  ✗ {msg}")

def print_warning(msg):
    print(f"  ⚠ {msg}")

def test_python():
    print_header("Testing Python Installation")
    try:
        version = subprocess.check_output([sys.executable, "--version"], text=True).strip()
        print_success(f"Python: {version}")
        
        major, minor = sys.version_info[:2]
        if major >= 3 and minor >= 8:
            print_success("Python version is 3.8+")
            return True
        else:
            print_error(f"Python {major}.{minor} is older than 3.8")
            return False
    except Exception as e:
        print_error(f"Python check failed: {e}")
        return False

def test_pytorch():
    print_header("Testing PyTorch Installation")
    try:
        import torch
        print_success(f"PyTorch: {torch.__version__}")
        
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
            memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            print_success(f"CUDA Available: YES")
            print_success(f"GPU: {device_name}")
            print_success(f"VRAM: {memory:.1f} GB")
            return True
        else:
            print_warning("CUDA not available (CPU only mode)")
            return True
    except ImportError:
        print_error("PyTorch not installed. Run: pip install torch")
        return False

def test_transformers():
    print_header("Testing Transformers Library")
    try:
        import transformers
        print_success(f"Transformers: {transformers.__version__}")
        return True
    except ImportError:
        print_error("Transformers not installed. Run: pip install transformers")
        return False

def test_fastapi():
    print_header("Testing FastAPI")
    try:
        import fastapi
        print_success(f"FastAPI: {fastapi.__version__}")
        return True
    except ImportError:
        print_error("FastAPI not installed. Run: pip install fastapi uvicorn")
        return False

def test_model_folder():
    print_header("Testing Model Folder Structure")
    
    models_path = Path("ai_server/models")
    
    if not models_path.exists():
        print_error(f"Models folder not found: {models_path}")
        return False
    
    print_success(f"Models folder exists: {models_path.absolute()}")
    
    models_found = []
    for model_dir in models_path.iterdir():
        if model_dir.is_dir():
            has_model = False
            has_config = False
            has_tokenizer = False
            
            # Check for model files
            for file in model_dir.glob("*"):
                if file.suffix in ['.bin', '.safetensors']:
                    has_model = True
                if file.name == 'config.json':
                    has_config = True
                if file.name in ['tokenizer.json', 'tokenizer_config.json']:
                    has_tokenizer = True
            
            status = "✓"
            if not has_model:
                status = "⚠ (no model file)"
            
            models_found.append({
                "name": model_dir.name,
                "has_model": has_model,
                "has_config": has_config,
                "has_tokenizer": has_tokenizer
            })
    
    if models_found:
        for model in models_found:
            status = "✓" if (model['has_model'] and model['has_config']) else "⚠"
            print(f"  {status} {model['name']}")
            if not model['has_model']:
                print_warning(f"    Missing model file (.bin or .safetensors)")
            if not model['has_config']:
                print_warning(f"    Missing config.json")
        return len(models_found) > 0
    else:
        print_warning("No models found in models/ folder")
        print("  Download a model first. See MODELS_SETUP.md")
        return False

def test_config():
    print_header("Testing Configuration Files")
    
    required_files = [
        "ai_server/config.py",
        "ai_server/model_loader.py",
        "ai_server/main.py",
        "ai_server/paper_analyzer.py",
        "ai_server/panel_simulator.py",
        "website/index.html",
    ]
    
    all_exist = True
    for file in required_files:
        path = Path(file)
        if path.exists():
            print_success(f"Found: {file}")
        else:
            print_error(f"Missing: {file}")
            all_exist = False
    
    return all_exist

def test_requirements():
    print_header("Checking requirements.txt")
    
    req_path = Path("ai_server/requirements.txt")
    if req_path.exists():
        print_success("requirements.txt exists")
        
        # Check key packages
        with open(req_path) as f:
            content = f.read()
        
        packages = ['fastapi', 'torch', 'transformers', 'sentence-transformers']
        for pkg in packages:
            if pkg in content.lower():
                print_success(f"  {pkg} in requirements")
            else:
                print_warning(f"  {pkg} not in requirements")
        
        return True
    else:
        print_error("requirements.txt not found")
        return False

def test_model_loading():
    print_header("Testing Model Loading")
    
    print("  This requires models to be downloaded first...")
    print("  Skipping dynamic load test (run after downloading models)")
    print("  To test: python -c \"from model_loader import load_main_model; load_main_model()\"")
    return True

def run_all_tests():
    print("\n")
    print("█" * 60)
    print("█  AI Panel Review System - Pre-Hackathon Test Suite")
    print("█" * 60)
    
    results = {
        "Python": test_python(),
        "PyTorch": test_pytorch(),
        "Transformers": test_transformers(),
        "FastAPI": test_fastapi(),
        "Config Files": test_config(),
        "Requirements": test_requirements(),
        "Model Folder": test_model_folder(),
        "Model Loading": test_model_loading(),
    }
    
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status:8} - {test_name}")
    
    print(f"\n  Passed: {passed}/{total}")
    
    if passed == total:
        print_success("All tests passed! System is ready for hackathon.")
        return True
    else:
        print_warning(f"{total - passed} test(s) failed. See details above.")
        return False

def print_next_steps():
    print_header("Next Steps")
    print("""
  1. Download a model:
     huggingface-cli download mistralai/Mistral-7B-Instruct-v0.1 --local-dir ai_server/models/mistral_7b

  2. Start the AI server:
     cd ai_server
     python start_server.bat

  3. In another terminal, start the website:
     cd website
     python -m http.server 3000

  4. Open website:
     http://127.0.0.1:3000

  5. For remote access:
     Install Cloudflare Tunnel and follow REMOTE_ACCESS_SETUP.md

  See README.md for detailed setup instructions.
    """)

if __name__ == "__main__":
    success = run_all_tests()
    print_next_steps()
    
    sys.exit(0 if success else 1)
