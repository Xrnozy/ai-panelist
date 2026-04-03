"""
Configuration for AI Panel Review System
GPU-Only Mode - Matches proven audio transcription pattern
"""
import os
import torch

# DISABLE CPU THREADING - MATCHES OLD APP
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TORCH_NUM_THREADS"] = "1"

# SIMPLE DEVICE SELECTION - IDENTICAL TO OLD APP
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Print GPU info (matches old app)
if DEVICE == "cuda":
    print("=" * 70)
    print(f"🎮 GPU MODE: {torch.cuda.get_device_name(0)}")
    print(f"   CUDA: {torch.version.cuda}")
    print(f"   PyTorch: {torch.__version__}")
    print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print("=" * 70)
    # Enable GPU optimizations - CRITICAL for GPU-only (matches old app)
    torch.backends.cudnn.benchmark = True
else:
    print("⚠️ CPU MODE (slow)")

# Model Configuration
ACTIVE_MODEL = "mistral_7b"
MAX_TOKENS = 2048
MAX_INPUT_TOKENS = 4096

# Compute dtype (matches old app)
COMPUTE_DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

# Inference Parameters
INFERENCE_MAX_NEW_TOKENS = 100
INFERENCE_TEMPERATURE = 0.7
INFERENCE_TOP_P = 0.9

# API Configuration
API_KEY = "aipanelist_secret_key_2026"
ALLOWED_ORIGINS = ["*"]

# Server Configuration
HOST = "0.0.0.0"
PORT = 8000

# Model paths
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

# Embedding model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Panel Professors
PANEL_PROFESSORS = [
    {
        "name": "Dr. Johnson",
        "expertise": "Methodology Expert",
        "focus_areas": ["research design", "experimental setup", "methodology validity"]
    },
    {
        "name": "Dr. Chen",
        "expertise": "Literature Expert",
        "focus_areas": ["literature review", "citation coverage", "research gap"]
    },
    {
        "name": "Dr. Williams",
        "expertise": "Statistician",
        "focus_areas": ["data analysis", "statistical significance", "results interpretation"]
    }
]

CITATION_AGE_THRESHOLD = 10
RELEVANCE_THRESHOLD = 0.5
