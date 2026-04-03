"""
FastAPI backend for real-time audio transcription
Handles audio streaming, Whisper model inference, WebSocket communication, and file uploads
"""

import asyncio
import logging
import numpy as np
import torch
import torchaudio
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq, WhisperProcessor, WhisperForConditionalGeneration
from safetensors.torch import load_file
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from pathlib import Path
import json
from datetime import datetime
import queue
import threading
import subprocess
import tempfile
import shutil
from typing import Optional

# Optional NeMo support
try:
    from nemo.collections.asr.models import ASRModel as NeMoASRModel
    NEMO_AVAILABLE = True
except ImportError as e:
    NEMO_AVAILABLE = False
    NEMO_IMPORT_ERROR = str(e)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check GPU availability with more detailed information
import warnings
# Suppress the sm_120 compatibility warning since PyTorch still works with fallback kernels
warnings.filterwarnings("ignore", message=".*sm_120.*is not compatible.*")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"🎮 Using device: {DEVICE}")
if DEVICE == "cuda":
    logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
    logger.info(f"   CUDA Version: {torch.version.cuda}")
    logger.info(f"   CUDA Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    try:
        free_memory, total_memory = torch.cuda.mem_get_info(0)
        logger.info(f"   CUDA Memory Available: {free_memory / 1e9:.1f} GB free, {total_memory / 1e9:.1f} GB total")
    except Exception as e:
        logger.warning(f"   Could not get memory info: {e}")
else:
    logger.warning(f"⚠️ CUDA not available, using CPU. Transcription may be slow.")
    logger.warning(f"   To use GPU, ensure NVIDIA CUDA toolkit and torch GPU version are installed.")

# Model paths - auto-detect from common locations and recursive search
def find_model_dir():
    """Auto-detect model directory from candidates list"""
    root = Path(__file__).parent.parent.parent
    
    # Explicit list of model candidates to try in order
    # Edit this list to use a different model (first matching candidate will be used)
    candidates = [
        root / "app" / "model" / "whisper-small-tagalog"
    ]
    
    # Try each candidate in order - use first one that exists with model files
    for candidate in candidates:
        if candidate.exists():
            # Check for .nemo file (NeMo model)
            nemo_files = list(candidate.glob('*.nemo'))
            if nemo_files:
                logger.info(f"   Found NeMo model at: {candidate}")
                return candidate, "nemo"
            
            # Check for single safetensors file
            if (candidate / "model.safetensors").exists():
                logger.info(f"   Found safetensors model at: {candidate}")
                return candidate, "safetensors"
            
            # Check for split safetensors files (model-00001-of-00002.safetensors, etc.)
            split_files = list(candidate.glob('model-*-of-*.safetensors'))
            if split_files:
                logger.info(f"   Found split safetensors model at: {candidate}")
                logger.info(f"   Split files: {[f.name for f in split_files]}")
                return candidate, "safetensors"
            
            # Check for pytorch format
            if (candidate / "pytorch_model.bin").exists():
                logger.info(f"   Found PyTorch model at: {candidate}")
                return candidate, "pytorch"
            
            # Check for split pytorch files
            split_bin_files = list(candidate.glob('pytorch_model-*-of-*.bin'))
            if split_bin_files:
                logger.info(f"   Found split PyTorch model at: {candidate}")
                logger.info(f"   Split files: {[f.name for f in split_bin_files]}")
                return candidate, "pytorch"
    
    # If none of the candidates found, raise an error instead of searching recursively
    logger.error(f"❌ No model found in any candidate location:")
    for candidate in candidates:
        logger.error(f"   - {candidate}")
    raise FileNotFoundError(f"Model not found in candidates. Please add your model to one of the candidate paths or edit the candidates list in find_model_dir()")

MODEL_DIR, MODEL_TYPE = find_model_dir()
SAMPLE_RATE = 16000
CHUNK_DURATION = 4.0  # seconds - 4 second chunks for optimized transcription
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

# Global model and processor
model = None
processor = None
model_loaded = False
model_type = MODEL_TYPE  # Track which model type we're using
language_cache = {}


def load_model():
    """Load model from local path - supports .nemo, safetensors, and pytorch formats"""
    global model, processor, model_loaded, model_type
    
    try:
        logger.info(f"📦 Loading {model_type.upper()} model from: {MODEL_DIR}")
        
        # Verify model directory exists
        if not MODEL_DIR.exists():
            raise FileNotFoundError(f"Model directory not found: {MODEL_DIR}")
        
        # Load based on model type
        if model_type == "nemo":
            return _load_nemo_model()
        elif model_type == "safetensors":
            return _load_huggingface_model()
        elif model_type == "pytorch":
            return _load_huggingface_model()
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        logger.error(f"   Model path: {MODEL_DIR}")
        logger.error(f"   Model type: {model_type}")
        logger.error(f"   Path exists: {MODEL_DIR.exists()}")
        if MODEL_DIR.exists():
            files = list(MODEL_DIR.glob('*'))
            logger.error(f"   Files in directory ({len(files)}): {[f.name for f in files[:10]]}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        model_loaded = False
        return False


def _load_nemo_model():
    """Load NeMo ASR model"""
    global model, model_loaded
    
    if not NEMO_AVAILABLE:
        logger.error("❌ NeMo toolkit not installed. Install with: pip install nemo_toolkit")
        logger.error(f"   Import error: {NEMO_IMPORT_ERROR}")
        return False
    
    try:
        logger.info("   Loading NeMo model...")
        
        # Find .nemo file
        nemo_files = list(MODEL_DIR.glob('*.nemo'))
        if not nemo_files:
            raise FileNotFoundError(f"No .nemo files found in {MODEL_DIR}")
        
        nemo_path = str(nemo_files[0])
        logger.info(f"   Using .nemo file: {nemo_files[0].name}")
        
        # Load the NeMo model
        model = NeMoASRModel.restore_from(nemo_path)
        model.eval()
        
        if DEVICE == "cuda":
            model = model.cuda()
        
        logger.info(f"   ✓ NeMo model loaded and moved to {DEVICE}")
        model_loaded = True
        logger.info("✅ NeMo model loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load NeMo model: {e}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        model_loaded = False
        return False


def _load_huggingface_model():
    """Load HuggingFace model (safetensors or pytorch format)"""
    global model, processor, model_loaded
    
    try:
        # Check for model files
        safetensors_file = MODEL_DIR / "model.safetensors"
        bin_file = MODEL_DIR / "pytorch_model.bin"
        split_safetensors = list(MODEL_DIR.glob('model-*-of-*.safetensors'))
        split_bin = list(MODEL_DIR.glob('pytorch_model-*-of-*.bin'))
        
        if not safetensors_file.exists() and not bin_file.exists() and not split_safetensors and not split_bin:
            raise FileNotFoundError(f"model.safetensors, pytorch_model.bin, or split model files not found in: {MODEL_DIR}")
        
        if safetensors_file.exists():
            logger.info(f"   Using single safetensors model format")
        elif split_safetensors:
            logger.info(f"   Using split safetensors model format ({len(split_safetensors)} files)")
        elif bin_file.exists():
            logger.info(f"   Using single pytorch_model.bin format")
        else:
            logger.info(f"   Using split pytorch model format ({len(split_bin)} files)")
        
        # Convert Path to string for transformers library
        model_path = str(MODEL_DIR)
        
        logger.info(f"   Loading processor...")
        # Load processor - bypass transformers validation by using absolute path normalization
        import tempfile
        import shutil
        
        # Create a temporary directory with no spaces for the model
        temp_model_dir = Path(tempfile.gettempdir()) / "whisper_model_temp"
        if temp_model_dir.exists():
            logger.info(f"   Using existing temp model directory")
        else:
            logger.info(f"   Creating temporary model directory: {temp_model_dir}")
            # Copy model files to temp location
            shutil.copytree(MODEL_DIR, temp_model_dir)
            logger.info(f"   ✓ Model copied to temp location")
        
        # Now load from temp path (no spaces)
        temp_model_path = str(temp_model_dir)
        
        try:
            processor = AutoProcessor.from_pretrained(
                temp_model_path,
                local_files_only=True,
                trust_remote_code=True
            )
        except (ValueError, RuntimeError) as e:
            logger.warning(f"   AutoProcessor failed, trying WhisperProcessor: {e}")
            processor = WhisperProcessor.from_pretrained(
                temp_model_path,
                local_files_only=True,
                trust_remote_code=True
            )
        logger.info(f"   ✓ Processor loaded")
        
        logger.info(f"   Loading model weights...")
        try:
            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                temp_model_path,
                local_files_only=True,
                trust_remote_code=True,
                torch_dtype=torch.float32  # Use float32 for stability
            )
        except (ValueError, RuntimeError) as e:
            logger.warning(f"   AutoModel failed, trying WhisperForConditionalGeneration: {e}")
            model = WhisperForConditionalGeneration.from_pretrained(
                temp_model_path,
                local_files_only=True,
                trust_remote_code=True,
                torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32
            )
        logger.info(f"   ✓ Model weights loaded")
        
        logger.info(f"   Moving to device: {DEVICE}")
        model = model.to(DEVICE)
        model.eval()
        
        # Enable GPU optimizations if CUDA is available
        if DEVICE == "cuda":
            logger.info(f"   Enabling CUDA optimizations...")
            # Enable CUDA benchmarking for optimal performance
            torch.backends.cudnn.benchmark = True
            logger.info(f"   CUDA optimizations enabled")
        
        model_loaded = True
        logger.info("✅ HuggingFace model loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load HuggingFace model: {e}")
        logger.error(f"\n   Expected structure:")
        logger.error(f"   model/")
        logger.error(f"   ├── model.safetensors (or split model-00001-of-00002.safetensors, etc.)")
        logger.error(f"   ├── config.json")
        logger.error(f"   ├── processor_config.json")
        logger.error(f"   └── tokenizer_config.json")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        model_loaded = False
        return False


def detect_language(audio_np: np.ndarray) -> str:
    """
    Detect language from audio - limited to English and Tagalog
    Returns: 'en', 'tl', or 'other'
    """
    global model, processor, model_type
    
    if not model_loaded or model is None:
        return "unknown"
    
    try:
        # Detect using Whisper if applicable
        if "Whisper" in type(model).__name__:
            inputs = processor(audio_np, sampling_rate=SAMPLE_RATE, return_tensors="pt")
            input_features = inputs.input_features.to(DEVICE)
            if hasattr(model, 'dtype'):
                input_features = input_features.to(model.dtype)
                
            with torch.no_grad():
                # Whisper generation to get language token
                generated_ids = model.generate(input_features, max_new_tokens=2)
                if generated_ids.shape[1] > 1:
                    lang_token_id = generated_ids[0][1].item()
                    lang_code = processor.tokenizer.decode(lang_token_id).strip("<|>")
                    
                    if lang_code in ["en", "english"]:
                        return "en"
                    elif lang_code in ["tl", "tagalog"]:
                        return "tl"
                    else:
                        logger.info(f"🌐 Detected other language: {lang_code}")
                        return "other"
        
        # Default for single-language models
        return "tl"
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        return "tl"


def transcribe_audio_file(audio_np: np.ndarray) -> dict:
    """
    Transcribe full audio file in chunks
    Chunks the audio into CHUNK_SIZE segments and transcribes each one
    Returns concatenated results
    """
    if not model_loaded or model is None:
        return {"text": "", "language": "unknown", "confidence": 0.0, "error": "Model not loaded"}
    
    try:
        logger.info(f"🎤 Starting full file transcription - Audio length: {len(audio_np) / SAMPLE_RATE:.1f}s")
        
        # Ensure audio is in float32 for processing
        if audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)
            logger.debug("✏️ Converted audio to float32")
        
        # Split into chunks
        num_chunks = (len(audio_np) + CHUNK_SIZE - 1) // CHUNK_SIZE
        logger.info(f"📊 Splitting into {num_chunks} chunks of {CHUNK_SIZE} samples ({CHUNK_DURATION}s each)")
        
        all_text = []
        
        for chunk_idx in range(num_chunks):
            start_idx = chunk_idx * CHUNK_SIZE
            end_idx = min((chunk_idx + 1) * CHUNK_SIZE, len(audio_np))
            chunk = audio_np[start_idx:end_idx]
            
            chunk_duration = (end_idx - start_idx) / SAMPLE_RATE
            logger.info(f"  📝 Chunk {chunk_idx + 1}/{num_chunks} ({chunk_duration:.1f}s)...")
            
            # Skip silent chunks
            chunk_rms = np.sqrt(np.mean(chunk ** 2))
            if chunk_rms < 0.001:
                logger.debug(f"    🔇 Skipping silent chunk (RMS: {chunk_rms:.6f})")
                continue
            
            # Apply audio boost pipeline
            alpha = 0.98
            chunk = np.append(chunk[0], chunk[1:] - alpha * chunk[:-1])
            
            current_rms = np.sqrt(np.mean(chunk ** 2))
            target_rms = 0.75
            
            if current_rms > 1e-7:
                gain_multiplier = min(250.0, target_rms / current_rms)
                chunk = chunk * gain_multiplier
                
                peak = np.max(np.abs(chunk))
                if peak > 0.98:
                    chunk = chunk / (peak / 0.98)
            
            # Transcribe chunk
            try:
                if model_type == "nemo":
                    result = _transcribe_nemo(chunk)
                else:
                    result = _transcribe_huggingface(chunk)
                
                text = result.get("text", "").strip()
                if text:
                    all_text.append(text)
                    logger.info(f"    ✅ Got {len(text)} chars")
                else:
                    logger.debug(f"    ⚠️ Empty result")
            except Exception as e:
                logger.error(f"    ❌ Chunk transcription failed: {e}")
                continue
        
        # Concatenate results
        full_text = " ".join(all_text)
        logger.info(f"✅ Full transcription complete: {len(full_text)} characters from {num_chunks} chunks")
        
        return {
            "text": full_text,
            "language": "en",  # Detected earlier
            "confidence": 0.95,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Full file transcription error: {e}", exc_info=True)
        return {
            "text": "",
            "language": "unknown",
            "confidence": 0.0,
            "error": str(e)
        }


def transcribe_audio(audio_np: np.ndarray) -> dict:
    """
    Transcribe audio using loaded model (NeMo or HuggingFace)
    Returns: {'text': str, 'language': str, 'confidence': float}
    """
    if not model_loaded or model is None:
        return {"text": "", "language": "unknown", "confidence": 0.0, "error": "Model not loaded"}
    
    try:
        logger.debug(f"🎤 Starting transcription - Audio shape: {audio_np.shape}, dtype: {audio_np.dtype}")
        
        # Ensure audio is in float32 for processing
        if audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)
            logger.debug("✏️ Converted audio to float32")
        
        # --- ULTRA-CLARITY & LOUDNESS PIPELINE ---
        # 1. PRE-EMPHASIS FILTER (CLARITY BOOST)
        # Boosts high frequencies (consonants) which helps ASR clarity
        alpha = 0.98
        audio_np = np.append(audio_np[0], audio_np[1:] - alpha * audio_np[:-1])
        
        # 2. AGGRESSIVE GAIN (LOUDNESS BOOST)
        # We target a much higher RMS level for "loud and clear" audio
        current_rms = np.sqrt(np.mean(audio_np ** 2))
        target_rms = 0.75  # Target a very hot signal
        
        if current_rms > 1e-7:
            # Multiplier can be up to 250x if audio is extremely quiet
            gain_multiplier = min(250.0, target_rms / current_rms)
            audio_np = audio_np * gain_multiplier
            
            # 3. PEAK LIMITING (SAFETY)
            # Ensure we don't clip hard after the massive gain
            peak = np.max(np.abs(audio_np))
            if peak > 0.98:
                audio_np = audio_np / (peak / 0.98)
                
            logger.info(f"🔊 Audio Boost: {gain_multiplier:.1f}x (RMS: {current_rms:.4f} -> {target_rms:.2f})")
        else:
            logger.warning(f"⚠️ Audio is silent (RMS: {current_rms:.6f})")

        # Use appropriate transcription method based on model type
        if model_type == "nemo":
            return _transcribe_nemo(audio_np)
        else:
            return _transcribe_huggingface(audio_np)
        
    except Exception as e:
        logger.error(f"❌ Transcription error: {e}", exc_info=True)
        return {
            "text": "",
            "language": "unknown",
            "confidence": 0.0,
            "error": str(e)
        }


def _transcribe_nemo(audio_np: np.ndarray) -> dict:
    """Transcribe using NeMo model"""
    try:
        logger.debug("🤖 Running NeMo model inference...")
        
        # NeMo expects audio at 16kHz
        with torch.no_grad():
            # Convert numpy array to tensor
            audio_tensor = torch.from_numpy(audio_np).to(DEVICE)
            
            # Get transcription from NeMo model
            # The exact method depends on the NeMo model type
            # For ASR models, typically use transcribe() method
            try:
                # Method 1: Try transcribe method
                if hasattr(model, 'transcribe'):
                    # NeMo 2.0+ can take list of tensors
                    res = model.transcribe([audio_tensor])
                    
                    # Handle various return formats (Hybrid models return tuples/nested lists)
                    if isinstance(res, tuple):
                        # Hybrid models often return (rnn_transcripts, ctc_transcripts)
                        res = res[0]
                    
                    if isinstance(res, list) and len(res) > 0:
                        transcription = res[0]
                    else:
                        transcription = res
                
                # Method 2: Try forward pass as fallback
                elif hasattr(model, 'forward'):
                    with torch.no_grad():
                        outputs = model(processed_signal=audio_tensor.unsqueeze(0), processed_signal_length=torch.tensor([len(audio_np)]))
                    transcription = model.tokenizer.decode(outputs[0].cpu().numpy())
                else:
                    raise ValueError("NeMo model has no transcribe or forward method")
                    
            except Exception as e:
                logger.warning(f"NeMo transcription method failed, trying generic approach: {e}")
                # Fallback: use the model's default inference
                transcription = str(model(processed_signal=torch.from_numpy(audio_np).to(DEVICE).unsqueeze(0)))
        
        logger.info(f"✅ NeMo Transcription complete: '{transcription}'")
        
        return {
            "text": transcription,
            "language": "unknown",
            "confidence": 0.95,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ NeMo transcription failed: {e}", exc_info=True)
        return {
            "text": "",
            "language": "unknown",
            "confidence": 0.0,
            "error": str(e)
        }


def _transcribe_huggingface(audio_np: np.ndarray) -> dict:
    """Transcribe using HuggingFace model (Whisper, etc)"""
    try:
        # Detect language first
        lang = detect_language(audio_np)
        
        if lang == "other":
            return {
                "text": "[Other Language]",
                "language": "other",
                "confidence": 0.9,
                "timestamp": datetime.now().isoformat()
            }
            
        # For Taglish support, we use "tl" as the base language but add a prompt
        # Whisper's Tagalog mode handles English loanwords better than English mode handles Tagalog
        forced_lang = "tl" if lang in ["en", "tl"] else "tl"
        
        # Taglish prompt to guide the model
        taglish_prompt = "English and Tagalog, Taglish conversation."

        # Process audio
        logger.debug("🔧 Processing with processor...")
        inputs = processor(
            audio_np,
            sampling_rate=SAMPLE_RATE,
            return_tensors="pt"
        )
        
        input_features = inputs.input_features.to(DEVICE).to(torch.float32)
        logger.debug(f"✅ Features shape: {input_features.shape}, dtype: {input_features.dtype}")
        
        # Prepare prompt IDs if it's a Whisper model
        prompt_ids = None
        if "Whisper" in type(model).__name__:
            try:
                # Use the processor to get prompt IDs for Taglish bias
                prompt_ids = processor.get_prompt_ids(taglish_prompt).to(DEVICE)
            except Exception as e:
                logger.debug(f"Could not set prompt_ids: {e}")

        # Generate transcription with improved parameters
        logger.debug("🤖 Running model.generate()...")
        try:
            with torch.no_grad():
                # Use beam search with detected language for better quality
                generate_kwargs = {
                    "input_features": input_features,
                    "max_length": 448,
                    "num_beams": 5,
                    "return_timestamps": False,
                    "task": "transcribe",
                    "language": forced_lang,
                    "no_repeat_ngram_size": 2,
                    "repetition_penalty": 1.5,
                    "length_penalty": 0.6
                }
                
                # Add prompt if available
                if prompt_ids is not None:
                    generate_kwargs["prompt_ids"] = prompt_ids
                    
                generated_ids = model.generate(**generate_kwargs)
        except RuntimeError as e:
            if "no kernel image is available" in str(e) or "cuda" in str(e).lower():
                logger.warning(f"⚠️ CUDA kernel error, trying CPU fallback: {str(e)[:100]}")
                # Move model and inputs to CPU and retry
                model.to("cpu")
                input_features = input_features.to("cpu")
                with torch.no_grad():
                    generate_kwargs["input_features"] = input_features
                    if prompt_ids is not None:
                        generate_kwargs["prompt_ids"] = prompt_ids.to("cpu")
                    generated_ids = model.generate(**generate_kwargs)
            else:
                raise
        
        logger.debug(f"✅ Generated IDs: {generated_ids.shape}")
        
        # Decode
        transcription = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0].strip()
        
        # Check if output looks like junk (repeated same character)
        if transcription and len(set(transcription.strip())) == 1:
            logger.warning(f"⚠️ Detected junk output (repeated character): {transcription[:50]}...")
            return {
                "text": "[Inaudible/Noise]",
                "language": "unknown",
                "confidence": 0.1,
                "timestamp": datetime.now().isoformat()
            }
        
        # Check if output has excessive word repetition (stuttering artifact)
        words = transcription.split()
        if len(words) > 5:  # Only check if enough words
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # If any word appears too many times (>50% of total words), it's likely hallucination
            max_count = max(word_counts.values())
            if max_count > len(words) * 0.5:
                logger.warning(f"⚠️ Detected excessive repetition - word '{max(word_counts, key=word_counts.get)}' appears {max_count}/{len(words)} times")
                # Clean up by removing repeated consecutive words
                cleaned_words = []
                prev_word = None
                for word in words:
                    if word != prev_word or word_counts[word] < 3:  # Allow some repetition if not excessive
                        cleaned_words.append(word)
                        prev_word = word
                transcription = " ".join(cleaned_words)
        
        logger.info(f"✅ Transcription complete: '{transcription}'")
        
        # Language detection (simple heuristic)
        language = detect_language(audio_np)
        
        return {
            "text": transcription,
            "language": language,
            "confidence": 0.95,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ HuggingFace transcription error: {e}", exc_info=True)
        return {
            "text": "",
            "language": "unknown",
            "confidence": 0.0,
            "error": str(e)
        }


def resample_audio(audio_np: np.ndarray, original_sr: int) -> np.ndarray:
    """Resample audio to 16kHz if needed"""
    if original_sr == SAMPLE_RATE:
        return audio_np
    
    # Simple linear resampling
    num_samples = int(len(audio_np) * SAMPLE_RATE / original_sr)
    return np.interp(
        np.linspace(0, len(audio_np) - 1, num_samples),
        np.arange(len(audio_np)),
        audio_np
    )


# Audio file handling functions
def validate_audio_format(file_path: Path) -> bool:
    """Validate if file is a supported audio format"""
    supported_formats = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus'}
    return file_path.suffix.lower() in supported_formats


def convert_to_wav(input_path: Path, output_path: Path) -> bool:
    """
    Convert audio file to WAV format using FFmpeg
    Returns True if successful, False otherwise
    """
    try:
        logger.info(f"   Converting {input_path.suffix} to WAV...")
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite output
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300  # 5 minutes max
        )
        
        if result.returncode == 0:
            logger.info(f"   ✓ Conversion successful")
            return True
        else:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            logger.error(f"   FFmpeg error: {error_msg[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"   Conversion timeout (file too large)")
        return False
    except Exception as e:
        logger.error(f"   Conversion failed: {e}")
        return False


def load_audio_file(file_path: Path) -> Optional[tuple[np.ndarray, int]]:
    """
    Load audio file and return (audio_array, sample_rate)
    Automatically converts to WAV if needed
    """
    try:
        file_ext = file_path.suffix.lower()
        logger.info(f"📂 Attempting to load file: {file_path.name} (ext: {file_ext})")
        
        # Handle WAV files directly
        if file_ext == '.wav':
            logger.info(f"   Loading WAV file directly...")
            try:
                # Try soundfile first (most reliable)
                import soundfile as sf
                audio_np, sr = sf.read(str(file_path))
                logger.info(f"   ✓ Loaded with soundfile: {audio_np.shape[0]/sr:.1f}s @ {sr}Hz")
                if audio_np.ndim > 1:
                    audio_np = np.mean(audio_np, axis=1)
                return audio_np.astype(np.float32), sr
            except ImportError:
                logger.info(f"   soundfile not available, trying torchaudio...")
                audio_tensor, sr = torchaudio.load(str(file_path))
                audio_np = audio_tensor.numpy()
                
                # Handle stereo/mono
                if audio_np.shape[0] > 1:
                    logger.info(f"   Converting stereo to mono...")
                    audio_np = np.mean(audio_np, axis=0)
                else:
                    audio_np = audio_np[0]
                
                logger.info(f"   ✓ Loaded: {audio_np.shape[0]/sr:.1f}s @ {sr}Hz")
                return audio_np.astype(np.float32), sr
        
        # Convert other formats to WAV first
        logger.info(f"   {file_ext.upper()} file detected, need to convert to WAV...")
        
        # Check if FFmpeg is available
        try:
            result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            if result.returncode != 0:
                logger.error(f"   ❌ FFmpeg check failed with return code {result.returncode}")
                return None
        except FileNotFoundError:
            logger.error(f"   ❌ FFmpeg not found! Install with: pip install ffmpeg-python or download from ffmpeg.org")
            return None
        except Exception as e:
            logger.error(f"   ❌ FFmpeg check error: {e}")
            return None
        
        temp_wav = file_path.parent / f"temp_{file_path.stem}.wav"
        
        if not convert_to_wav(file_path, temp_wav):
            logger.error(f"   ❌ Conversion failed for {file_ext}")
            return None
        
        # Load the converted WAV
        logger.info(f"   Loading converted WAV...")
        try:
            # Try soundfile first
            import soundfile as sf
            audio_np, sr = sf.read(str(temp_wav))
            logger.info(f"   ✓ Loaded with soundfile: {audio_np.shape[0]/sr:.1f}s @ {sr}Hz")
            if audio_np.ndim > 1:
                audio_np = np.mean(audio_np, axis=1)
        except ImportError:
            logger.info(f"   soundfile not available, trying torchaudio...")
            audio_tensor, sr = torchaudio.load(str(temp_wav))
            audio_np = audio_tensor.numpy()
            
            if audio_np.shape[0] > 1:
                logger.info(f"   Converting stereo to mono...")
                audio_np = np.mean(audio_np, axis=0)
            else:
                audio_np = audio_np[0]
        
        # Clean up temp file
        try:
            temp_wav.unlink()
            logger.debug(f"   ✓ Cleaned up temp file")
        except:
            pass
        
        logger.info(f"   ✓ Loaded: {audio_np.shape[0]/sr:.1f}s @ {sr}Hz")
        return audio_np.astype(np.float32), sr
        
    except Exception as e:
        logger.error(f"   ❌ Failed to load audio: {e}", exc_info=True)
        return None


def resample_audio(audio_np: np.ndarray, sr_from: int, sr_to: int = SAMPLE_RATE) -> np.ndarray:
    """Resample audio to target sample rate"""
    if sr_from == sr_to:
        return audio_np
    
    try:
        logger.info(f"   Resampling from {sr_from}Hz to {sr_to}Hz...")
        audio_tensor = torch.from_numpy(audio_np).unsqueeze(0)
        resampler = torchaudio.transforms.Resample(sr_from, sr_to)
        resampled = resampler(audio_tensor).squeeze(0).numpy()
        logger.info(f"   ✓ Resampled")
        return resampled.astype(np.float32)
    except Exception as e:
        logger.error(f"   Resample failed: {e}")
        return audio_np


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass  # WebSocket already disconnected
        logger.info(f"🔌 Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await asyncio.wait_for(connection.send_json(message), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Broadcast timeout - client may be slow")
                disconnected.append(connection)
            except Exception as e:
                logger.warning(f"Broadcast error: {e}")
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup and shutdown"""
    # Startup
    logger.info("🚀 Starting up...")
    load_model()
    await manager.broadcast({
        "type": "status",
        "model_loaded": model_loaded,
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available()
    })
    yield
    # Shutdown
    logger.info("⏹️ Shutting down...")


# Initialize FastAPI app with lifespan
app = FastAPI(title="Tab Audio Transcriber", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = __import__('time').time()
    response = await call_next(request)
    process_time = __import__('time').time() - start_time
    logger.info(f"📡 {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}s")
    return response


@app.get("/")
async def get_index():
    """Serve index.html with no-cache headers"""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    index_file = frontend_dir / "index.html"
    
    if not index_file.exists():
        return {"error": f"index.html not found at {index_file}"}
    
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "model_loaded": model_loaded,
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available()
    }


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio transcription
    Expects audio chunks as binary messages
    """
    await manager.connect(websocket)
    logger.info("🔗 WebSocket connected")
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "status",
            "model_loaded": model_loaded,
            "model_name": MODEL_DIR.name if MODEL_DIR else "None",
            "device": DEVICE,
            "cuda_available": torch.cuda.is_available()
        })
        
        # Buffer for accumulating audio chunks
        audio_buffer = np.array([], dtype=np.float32)
        chunk_count = 0
        
        while True:
            # Receive audio data
            data = await websocket.receive_bytes()
            
            # Convert bytes to numpy array
            audio_chunk = np.frombuffer(data, dtype=np.float32).copy()
            
            # Immediate Boost for level calculation and processing
            if len(audio_chunk) > 0:
                max_chunk = np.max(np.abs(audio_chunk))
                if max_chunk > 1e-7:
                    # Apply 5x multiplier to the already boosted frontend signal
                    audio_chunk = audio_chunk * 5.0
                    # Peak limiter
                    peak = np.max(np.abs(audio_chunk))
                    if peak > 0.95:
                        audio_chunk = audio_chunk / peak
            
            # Add to buffer
            audio_buffer = np.concatenate([audio_buffer, audio_chunk])
            
            # Calculate audio level for visualization (using the boosted chunk)
            if len(audio_chunk) > 0:
                rms = np.sqrt(np.mean(audio_chunk ** 2))
                # Scale level more aggressively to fill the UI indicator
                level = min(100, int(rms * 250)) 
            else:
                level = 0
            
            # Send audio level update
            await manager.broadcast({
                "type": "audio_level",
                "level": level
            })
            
            # When buffer reaches chunk size (4 seconds), transcribe
            if len(audio_buffer) >= CHUNK_SIZE:
                # Take one chunk
                chunk = audio_buffer[:CHUNK_SIZE]
                audio_buffer = audio_buffer[CHUNK_SIZE:]
                
                chunk_count += 1
                
                # Only transcribe if there's significant audio (avoid transcribing silence)
                audio_rms = np.sqrt(np.mean(chunk ** 2))
                # Threshold lowered significantly to catch quiet speech
                logger.info(f"📊 Chunk {chunk_count} RMS: {audio_rms:.4f} (threshold: 0.005)")
                
                if audio_rms > 0.005:  # Sensitive threshold
                    logger.info(f"📝 Transcribing chunk {chunk_count}...")
                    result = transcribe_audio(chunk)
                    
                    
                    if result.get("text") and result.get("text").strip():  # Only send non-empty text
                        logger.info(f"✅ Broadcasting caption: {result['text']}")
                        await manager.broadcast({
                            "type": "caption",
                            "text": result["text"],
                            "language": result.get("language", "unknown"),
                            "confidence": result.get("confidence", 0.0),
                            "chunk_id": chunk_count,
                            "timestamp": result.get("timestamp")
                        })
                    else:
                        logger.warning(f"⚠️ Empty transcription result for chunk {chunk_count}")
                else:
                    logger.debug(f"🔇 Skipping chunk {chunk_count} - insufficient audio (RMS: {audio_rms:.4f})")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


@app.post("/api/transcribe-file")
async def transcribe_file(file: UploadFile = File(...)):
    """
    Transcribe uploaded audio file with progress tracking
    Supports: MP3, WAV, M4A, FLAC, OGG, AAC, WMA, OPUS
    """
    if not model_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded. Please wait for startup to complete.")
    
    temp_file_path = None
    
    try:
        # Validate file size (max 2GB for large podcasts)
        max_size = 2 * 1024 * 1024 * 1024
        contents = await file.read()
        
        if len(contents) > max_size:
            raise HTTPException(status_code=413, detail="File too large (max 2GB)")
        
        # Create temp directory for processing
        temp_dir = Path(tempfile.gettempdir()) / "audio_transcribe"
        temp_dir.mkdir(exist_ok=True)
        
        # Save uploaded file temporarily
        temp_file_path = temp_dir / file.filename
        with open(temp_file_path, 'wb') as f:
            f.write(contents)
        
        logger.info(f"📥 Processing: {file.filename} ({len(contents) / 1024 / 1024:.1f}MB)")
        
        # Validate and load audio
        if not validate_audio_format(temp_file_path):
            raise HTTPException(status_code=400, detail=f"Unsupported format: {temp_file_path.suffix}")
        
        logger.info(f"🎵 Loading audio file...")
        audio_result = load_audio_file(temp_file_path)
        if audio_result is None:
            logger.error(f"❌ load_audio_file returned None")
            raise HTTPException(status_code=400, detail="Failed to load audio file. Check backend logs for details.")
        
        audio_np, sr = audio_result
        logger.info(f"✅ Audio loaded successfully: {len(audio_np)/sr:.1f}s @ {sr}Hz")
        
        # Resample if needed
        if sr != SAMPLE_RATE:
            audio_np = resample_audio(audio_np, sr, SAMPLE_RATE)
        
        logger.info(f"🎵 Audio loaded: {len(audio_np)/SAMPLE_RATE:.1f}s")
        
        # Detect language
        detected_lang = detect_language(audio_np)
        logger.info(f"🌐 Detected language: {detected_lang}")
        
        # Transcribe
        logger.info(f"🤖 Starting full file transcription...")
        result = transcribe_audio_file(audio_np)
        
        # Ensure language is set
        if result.get("language") == "unknown":
            result["language"] = detected_lang
        
        logger.info(f"✅ Transcription complete: {len(result.get('text', ''))} characters")
        
        return {
            "status": "success",
            "filename": file.filename,
            "file_size": len(contents),
            "duration_seconds": len(audio_np) / SAMPLE_RATE,
            "text": result.get("text", ""),
            "language": result.get("language", detected_lang),
            "confidence": result.get("confidence", 0.0),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ File transcription error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    finally:
        # Cleanup temp file
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
                logger.debug(f"🧹 Cleaned up temp file: {temp_file_path}")
            except:
                pass


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model_loaded,
        "device": DEVICE,
        "gpu_available": DEVICE == "cuda"
    }
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="static")
    logger.info(f"📁 Mounted frontend from: {FRONTEND_DIR}")
else:
    logger.warning(f"⚠️ Frontend directory not found: {FRONTEND_DIR}")


if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
