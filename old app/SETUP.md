# Tab Audio Transcriber - Setup Guide

## Quick Start

### 1. Initial Setup (First Time Only)

**Windows:**
```bash
start.bat
```

That's it! The batch file will:
- ✅ Check Python installation
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Verify FFmpeg (optional)
- ✅ Detect CUDA/GPU support
- ✅ Start FastAPI backend
- ✅ Start frontend server
- ✅ Open browser automatically

### 2. Using the Application

1. **Open the app** at `http://localhost:8000`

2. **Click "📊 Share Tab & Start"**
   - Select the browser tab you want to capture audio from
   - Grant microphone permission when prompted
   - Audio capture begins automatically

3. **Watch live captions** appear in real-time

4. **View transcript history** on the right panel

5. **Export results:**
   - Click "📄 Export TXT" for plain text
   - Click "🎬 Export SRT" for subtitle format

6. **Stop recording** with "⏹️ Stop" button

---

## Verify GPU is Active

### Check Status in UI
- Look at the **Status Bar** (top of app)
- **GPU indicator** shows:
  - ✅ CUDA Ready → GPU is active
  - 💻 CPU Mode → Running on CPU (slower)

### Verify from Terminal
```bash
python -c "import torch; print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

### If GPU Not Detected
1. **For RTX 5060 Ti or newer GPUs:**
   - Ensure CUDA 12.4+ is installed (NVIDIA CUDA Toolkit 12.4+)
   - Install PyTorch with CUDA 12.4 support:
   ```bash
   pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```

2. **For older NVIDIA GPUs (RTX 3000/4000 series):**
   - Use CUDA 12.1 instead:
   ```bash
   pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

3. **Install NVIDIA CUDA Toolkit** (matching your PyTorch CUDA version)
   - Download: https://developer.nvidia.com/cuda-downloads

4. **Install cuDNN** (NVIDIA Deep Neural Network library)
   - Download: https://developer.nvidia.com/cudnn

5. **Restart the application**
   ```bash
   start.bat
   ```

6. **Verify GPU is working:**
   ```bash
   python -c "import torch; print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
   ```

---

## Replace Model

The application uses `whisper-small-tagalog` model from Hugging Face.

### Replace with Different Model

1. **Download model from Hugging Face:**
   - Browse: https://huggingface.co/models
   - Look for Whisper variants or speech-to-text models
   - Download model files (safetensors format preferred)

2. **Copy model files:**
   ```
   Model/
   └── whisper-small-tagalog/
       ├── config.json
       ├── model.safetensors
       ├── processor_config.json
       ├── tokenizer_config.json
       └── [other model files]
   ```

3. **Update model path in backend** (`app/backend/main.py`):
   ```python
   MODEL_DIR = Path(__file__).parent.parent.parent / "Model" / "your-model-name"
   ```

4. **Restart application:**
   ```bash
   start.bat
   ```

### Supported Models
- `openai/whisper-small` - Faster, smaller
- `openai/whisper-base` - Balanced
- `openai/whisper-medium` - Slower, more accurate
- `filippo-ferroni/whisper-tagalog` - Tagalog specialized

---

## Features

### Audio Capture
- ✅ Share specific browser tab (Google Meet style)
- ✅ 16kHz mono audio capture
- ✅ No audio playback in app (hear original tab audio)
- ✅ Real-time waveform visualization

### Transcription
- ✅ Real-time speech-to-text
- ✅ English & Tagalog support
- ✅ Mixed language detection
- ✅ Automatic language detection
- ✅ Live confidence scores

### GPU Support
- ✅ Auto-detect CUDA
- ✅ GPU fallback to CPU
- ✅ Compatible with RTX 2050, 3060 Ti, 4090, etc.
- ✅ Optimized inference with PyTorch

### Export Options
- ✅ TXT (plain text transcript)
- ✅ SRT (SubRip subtitle format)
- ✅ Timestamps
- ✅ Language and confidence metadata

---

## Troubleshooting

### Issue: "Python not found"
**Solution:**
- Install Python 3.10 or higher
- Download: https://www.python.org/downloads/
- Make sure to check "Add Python to PATH" during installation
- Restart your computer

### Issue: Backend fails to start
**Solution:**
```bash
cd app/backend
python -m pip install -r ../../requirements.txt
python main.py
```

### Issue: Model loading fails
**Solution:**
- Ensure model files exist in `Model/whisper-small-tagalog/`
- Run: `python -c "from transformers import AutoProcessor; AutoProcessor.from_pretrained('Model/whisper-small-tagalog', local_files_only=True)"`
- Check for download interruptions, redownload if needed

### Issue: No audio detected
**Solution:**
1. Check browser tab has audio playing
2. Grant microphone permissions
3. Check Windows audio settings
4. Disable browser audio mixing if needed
5. Try a different tab

### Issue: Transcription is slow (using CPU)
**Solution:**
- Install NVIDIA CUDA and cuDNN (see "Verify GPU" section)
- Check GPU detection: `python -c "import torch; print(torch.cuda.is_available())"`
- Reduce audio chunk size in backend for faster processing

### Issue: "ModuleNotFoundError" for transformers/torch
**Solution:**
```bash
cd venv\Scripts
activate.bat
pip install --upgrade torch torchaudio transformers
```

### Issue: WebSocket connection fails
**Solution:**
1. Check backend is running on port 8000
2. Check no firewall blocking localhost
3. Check port 8000 not in use: `netstat -ano | findstr :8000`
4. Kill process on port 8000 if needed

### Issue: "Permission denied" or "Access denied"
**Solution:**
- Run Command Prompt as Administrator
- Run `start.bat` again

---

## Performance Tips

### For Better Transcription
1. **Use GPU** - See "Verify GPU is Active" section
2. **Reduce background noise** - Mute other tabs/programs
3. **Use clear audio** - Speak clearly and avoid mumbling
4. **Use consistent volume** - Too quiet or too loud affects accuracy

### For Faster Processing
1. **Reduce chunk duration** - Edit `CHUNK_DURATION` in `app/backend/main.py`
2. **Use smaller model** - Replace with `whisper-base` or `whisper-tiny`
3. **Reduce CUDA memory usage** - Lower `torch_dtype` to float16

### For Stable Long Sessions
1. **Keep browser tab focused** - Prevents audio dropouts
2. **Monitor GPU memory** - Check with `nvidia-smi`
3. **Restart periodically** - Every 2-3 hours for very long sessions
4. **Close other applications** - Free up system memory

---

## System Requirements

### Minimum
- Windows 10/11
- Python 3.10+
- 4GB RAM
- 2GB disk space
- Internet (first setup only)

### Recommended
- Windows 10/11
- Python 3.10 or 3.11
- 8GB+ RAM
- 4GB disk space (2GB model + temp)
- **NVIDIA GPU** (RTX 2060+, RTX 3060+, RTX 4060+)
- NVIDIA CUDA 11.8+
- NVIDIA cuDNN 8.6+

### GPU Compatibility
✅ **Supported:**
- NVIDIA RTX 2050, 2060, 2070, 2080
- NVIDIA RTX 3060, 3070, 3080, 3090
- NVIDIA RTX 4060, 4070, 4080, 4090
- NVIDIA A100, A40 (data center)
- NVIDIA Jetson devices

❌ **Not Supported:**
- AMD Radeon (different architecture)
- Intel Arc (limited support)
- Apple Silicon (use different setup)
- Older NVIDIA cards (pre-Maxwell)

---

## Project Structure

```
Share tab transcription/
├── start.bat                    # Main startup script
├── requirements.txt             # Python dependencies
├── SETUP.md                     # This file
│
├── Model/
│   └── whisper-small-tagalog/   # Pre-downloaded model
│       ├── config.json
│       ├── model.safetensors
│       ├── tokenizer_config.json
│       └── ...
│
└── app/
    ├── backend/
    │   └── main.py              # FastAPI server & Whisper inference
    │
    └── frontend/
        ├── index.html           # Main UI
        ├── styles.css           # Styling
        ├── app.js               # Main logic
        ├── audio-capture.js     # Web Audio API wrapper
        └── visualization.js     # Waveform & transcript management
```

---

## Advanced Configuration

### Change Backend Port
Edit `app/backend/main.py`, line ~250:
```python
uvicorn.run(
    app,
    host="127.0.0.1",
    port=8000,  # Change to different port
)
```

### Change Chunk Duration
Edit `app/backend/main.py`, line ~36:
```python
CHUNK_DURATION = 0.5  # seconds - increase for fewer updates, decrease for faster response
```

### Change Model
Edit `app/backend/main.py`, line ~41:
```python
MODEL_DIR = Path(__file__).parent.parent.parent / "Model" / "your-model-name"
```

### Enable Remote Access
Edit `app/backend/main.py`, line ~250:
```python
host="0.0.0.0"  # Allow external connections (security risk!)
```

---

## Support & Documentation

### Additional Resources
- **Whisper Models:** https://huggingface.co/openai/whisper-small
- **FastAPI:** https://fastapi.tiangolo.com/
- **PyTorch:** https://pytorch.org/
- **Transformers:** https://huggingface.co/docs/transformers/

### Issues?
1. Check troubleshooting section above
2. Review logs in terminal windows
3. Verify all dependencies installed: `pip list`
4. Try fresh startup: Close all terminals and run `start.bat` again

---

**Version:** 1.0.0  
**Last Updated:** January 2025  
**Status:** Production Ready
