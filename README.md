# AI Panelist - Research Paper Review System

> ⚠️ **PROJECT STATUS**: This project is incomplete and has been dropped. Use at your own discretion.

An AI-powered system for analyzing research papers and simulating expert panel reviews using state-of-the-art language models.

## Features

- **Research Paper Analysis**: Analyze and extract key insights from research papers
- **AI Panel Simulation**: Generate expert panel reviews using large language models
- **GPU Acceleration**: Optimized for NVIDIA GPUs with CUDA support
- **FastAPI Backend**: High-performance REST API for easy integration
- **Model Management**: Efficient model loading and caching

## System Requirements

- **GPU**: NVIDIA GPU with CUDA support (tested on RTX 5060 Ti with CUDA 12.8)
- **RAM**: 16GB+ recommended
- **Python**: 3.8+
- **OS**: Windows, Linux, or macOS

## Models Used

- **Main Model**: Mistral 7B (LLM for analysis and reviews)
- **Embedding Model**: Sentence Transformers (all-MiniLM-L6-v2)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Xrnozy/ai-panelist.git
   cd ai-panelist
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   cd ai_server
   pip install -r requirements.txt
   ```

4. **Download models** (optional - models are loaded on-demand):
   - Mistral 7B is automatically downloaded to `ai_server/models/mistral_7b/`
   - Sentence Transformers model is downloaded to `ai_server/models/sentence-transformers/`

## Quick Start

### Start the AI Server

```bash
# From the project root
python ai_server/main.py
```

Or use the provided batch script:
```bash
start_server.bat
```

The API will be available at `http://localhost:8000`

### Quick Links

- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## Project Structure

```
├── ai_server/               # Main FastAPI application
│   ├── main.py             # FastAPI app and endpoints
│   ├── model_loader.py     # Model loading and caching
│   ├── paper_analyzer.py   # Paper analysis logic
│   ├── panel_simulator.py  # Panel review simulation
│   ├── config.py           # Configuration settings
│   ├── requirements.txt    # Python dependencies
│   └── models/             # Downloaded models (git ignored)
├── website/                # Frontend web interface
├── old app/                # Legacy implementation
├── test_system.py          # System testing script
└── README.md               # This file
```

## Configuration

Edit `ai_server/config.py` to customize:

- `API_KEY`: Authentication key for API endpoints
- `ALLOWED_ORIGINS`: CORS settings for frontend
- `HOST`: Server host (default: localhost)
- `PORT`: Server port (default: 8000)

## Usage Examples

### Analyze a Research Paper

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -d {
    "title": "Paper Title",
    "abstract": "Paper abstract...",
    "content": "Full paper content..."
  }
```

### Generate Panel Review

```bash
curl -X POST "http://localhost:8000/api/review" \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -d {
    "paper_id": "paper_123",
    "num_reviewers": 3
  }
```

## Environment Variables

Optionally set environment variables in `.env` or in the terminal:

```bash
API_KEY=your-secret-key
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Troubleshooting

### Models not loading
- Ensure you have sufficient disk space (~20GB for all models)
- Check GPU memory availability
- Verify CUDA is properly installed: `nvidia-smi`

### CORS errors
- Update `ALLOWED_ORIGINS` in `ai_server/config.py`

### Out of Memory
- The system automatically manages VRAM
- Clear cache if needed: `GET /api/cache/clear`

## Development

### Run Tests

```bash
python test_system.py
```

### Batch Scripts

- `start_server.bat` - Start AI server
- `start_website.bat` - Start web interface
- `start_system.bat` - Start complete system

## Performance Notes

- First request may take longer due to model loading
- Subsequent requests are faster with cached models
- GPU memory is managed automatically

## Contributing

Contributions are welcome! Please ensure:
- Models are git-ignored (already configured)
- Dependencies are documented in `requirements.txt`
- Code follows PEP 8 guidelines

## License

[Add your license here]

## Support

For issues or questions, please open an issue on the GitHub repository.

---

**Version**: 1.0.0  
**Last Updated**: April 2026
