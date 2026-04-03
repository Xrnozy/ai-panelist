"""
Dynamic Model Loader for AI Panel Review System
Handles loading from /models folder with support for .bin and .safetensors
"""
import os
import torch
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer
from config import ACTIVE_MODEL, DEVICE, MODELS_DIR, EMBEDDING_MODEL, COMPUTE_DTYPE

logger = logging.getLogger(__name__)

# Global model cache
loaded_models = {}


def load_main_model():
    """
    Load the main LLM model from the models folder
    Supports both .bin and .safetensors formats
    On-demand loading only when needed
    """
    global loaded_models
    
    if "main" in loaded_models:
        logger.debug("Main model already loaded, using cached version")
        return loaded_models["main"]
    
    model_path = os.path.join(MODELS_DIR, ACTIVE_MODEL)
    hf_model = "mistralai/Mistral-7B-Instruct-v0.1"
    
    # Check if local model has weight files
    has_model = False
    if os.path.exists(model_path):
        has_model = any(f.endswith((".bin", ".safetensors")) for f in os.listdir(model_path) if os.path.isfile(os.path.join(model_path, f)))
    
    logger.info(f"📦 Loading main model: {ACTIVE_MODEL}")
    logger.info(f"   Device: {DEVICE}")
    logger.info(f"   Has local weights: {has_model}")
    
    try:
        # Check for existing tokenizer files in local model path to avoid re-downloading
        tokenizer_exists = False
        if os.path.exists(model_path):
            tokenizer_files = ["tokenizer.json", "tokenizer.model", "tokenizer_config.json"]
            tokenizer_exists = any(
                os.path.exists(os.path.join(model_path, f)) 
                for f in tokenizer_files
            )
        
        # Load tokenizer - use local-only if files exist, otherwise download
        logger.info(f"🔤 Loading tokenizer...")
        try:
            if tokenizer_exists:
                logger.info(f"   Using cached tokenizer from {model_path}")
                tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                    use_fast=False,
                    local_files_only=True
                )
            else:
                logger.info(f"   Downloading tokenizer from HuggingFace (first time only)...")
                tokenizer = AutoTokenizer.from_pretrained(
                    hf_model, 
                    trust_remote_code=True,
                    use_fast=False
                )
        except Exception as e:
            logger.warning(f"Tokenizer load failed: {e}, trying with legacy_processing=False")
            tokenizer = AutoTokenizer.from_pretrained(
                hf_model if not tokenizer_exists else model_path,
                trust_remote_code=True,
                use_fast=False,
                legacy_processing=False,
                local_files_only=tokenizer_exists
            )
        
        # Try to load model from local path if available, otherwise from HuggingFace
        if has_model:
            logger.info(f"📦 Loading model from cache: {model_path}")
            
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=COMPUTE_DTYPE,
                trust_remote_code=True,
                local_files_only=True
            )
        else:
            logger.info(f"📥 Downloading model from HuggingFace: {hf_model}")
            
            model = AutoModelForCausalLM.from_pretrained(
                hf_model,
                torch_dtype=COMPUTE_DTYPE,
                trust_remote_code=True,
                cache_dir=model_path
            )
        
        # PROVEN GPU-ONLY PATTERN: Simple .to(DEVICE) call
        logger.info(f"   Moving to {DEVICE}...")
        model = model.to(DEVICE)
        model.eval()  # Critical for inference
        
        logger.info(f"✓ Model {ACTIVE_MODEL} loaded and moved to {DEVICE}")
        logger.info(f"  Type: {type(model).__name__}")
        logger.info(f"  Size: {sum(p.numel() for p in model.parameters()) / 1e9:.2f}B")
        
        loaded_models["main"] = {"model": model, "tokenizer": tokenizer}
        return loaded_models["main"]
    
    except Exception as e:
        logger.error(f"Error loading main model: {str(e)}")
        raise


def load_embedding_model():
    """
    Load embedding model for semantic similarity checks
    Uses HuggingFace cache to avoid re-downloading same version
    FORCES GPU EXECUTION
    """
    global loaded_models
    
    if "embedding" in loaded_models:
        logger.debug("Embedding model already loaded, using cached version")
        return loaded_models["embedding"]
    
    logger.info(f"📦 Loading embedding model: {EMBEDDING_MODEL}")
    
    try:
        # Load to GPU using DEVICE string (proven pattern)
        embedding_model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)
        logger.info(f"✓ Embedding model loaded on {DEVICE}")
        
        loaded_models["embedding"] = embedding_model
        return loaded_models["embedding"]
    
    except Exception as e:
        logger.error(f"Error loading embedding model: {str(e)}")
        raise


def clear_cache():
    """Clear GPU cache aggressively to maximize available VRAM"""
    import gc
    if DEVICE == "cuda":
        # Clear GPU cache completely
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.reset_accumulated_memory_stats()
        
        # Force Python garbage collection aggressively
        gc.collect()
        
        # Synchronize GPU to ensure cache clear completes
        torch.cuda.synchronize()
        
        # Log memory info
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        logger.debug(f"GPU cache cleared. Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB")


def get_model_info():
    """Return information about loaded models"""
    info = {
        "active_model": ACTIVE_MODEL,
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available(),
        "loaded_models": list(loaded_models.keys())
    }
    
    if torch.cuda.is_available():
        info["gpu_memory_allocated"] = f"{torch.cuda.memory_allocated() / 1e9:.2f} GB"
        info["gpu_memory_reserved"] = f"{torch.cuda.memory_reserved() / 1e9:.2f} GB"
    
    return info
