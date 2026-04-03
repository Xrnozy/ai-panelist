# Technical Architecture & API Reference

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Website)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • HTML/CSS/JavaScript (index.html)                     │  │
│  │  • Responsive design, modern UI                         │  │
│  │  • Local storage for API config                         │  │
│  │  • Real-time status updates                             │  │
│  └────────────────┬─────────────────────────────────────────┘  │
│                   │                                             │
│              HTTPS REST API Calls                                │
│                   │   (via Cloudflare Tunnel or Ngrok)         │
│                   ▼                                             │
│  ┌────────────────────────────────────────────────────────┐   │
│  │            FASTAPI SERVER (main.py)                    │   │
│  │  Runs on: Home PC with GPU                             │   │
│  │  Port: 8000                                            │   │
│  │  Features:                                              │   │
│  │  • API key authentication                              │   │
│  │  • CORS enabled                                        │   │
│  │  • Request validation (Pydantic)                       │   │
│  │  • Error handling w/ HTTP status codes                 │   │
│  │  • Startup/shutdown events for model loading           │   │
│  └─────┬──────────────────────┬──────────────────────────┘   │
│        │                      │                               │
│   ┌────▼────────────┐  ┌──────▼──────────────────┐            │
│   │ Paper Analyzer  │  │ Panel Simulator        │            │
│   │ (paper_analyzer │  │ (panel_simulator.py)   │            │
│   │  .py)           │  │                         │            │
│   │                 │  │ • Question generation  │            │
│   │ • Structure     │  │ • Answer evaluation    │            │
│   │   analysis      │  │ • Assessment creation  │            │
│   │ • Vague stmt    │  │ • Prof rotation        │            │
│   │ • Relevance     │  │ • History tracking     │            │
│   │ • Citations     │  │                        │            │
│   │ • Grammar       │  └──────┬─────────────────┘            │
│   └────┬────────────┘         │                               │
│        └───────────┬──────────┘                               │
│                    │                                          │
│        ┌───────────▼──────────────────────┐                  │
│        │  Model Loader & GPU Manager      │                  │
│        │  (model_loader.py)               │                  │
│        │                                  │                  │
│        │ • Load main LLM (Mistral/Llama)  │                  │
│        │ • Load embeddings (MiniLM)       │                  │
│        │ • GPU memory management          │                  │
│        │ • Model caching                  │                  │
│        └───────────┬──────────────────────┘                  │
│                    │                                          │
│        ┌───────────▼──────────────────────┐                  │
│        │        GPU (NVIDIA RTX)           │                  │
│        │   • PyTorch inference             │                  │
│        │   • Transformers library          │                  │
│        │   • CUDA acceleration             │                  │
│        └──────────────────────────────────┘                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints Reference

### 1. Health Check
**Endpoint:** `GET /health`

**Authentication:** API Key (header)

**Purpose:** Verify server and GPU status

**Response:**
```json
{
  "status": "healthy",
  "cuda_available": true,
  "models_loaded": ["main", "embedding"],
  "gpu_memory_allocated": "12.5 GB"
}
```

**HTTP Status:** 200 (Healthy) | 500 (Server Error)

---

### 2. Model Information
**Endpoint:** `GET /info`

**Authentication:** API Key (header)

**Purpose:** Get detailed model and system info

**Response:**
```json
{
  "active_model": "mistral_7b",
  "device": "cuda",
  "cuda_available": true,
  "loaded_models": ["main", "embedding"],
  "gpu_memory_allocated": "12.3 GB",
  "gpu_memory_reserved": "14.0 GB"
}
```

---

### 3. Analyze Research Paper
**Endpoint:** `POST /analyze`

**Authentication:** Required (API Key in header)

**Purpose:** Comprehensive paper analysis for issues

**Request Body:**
```json
{
  "text": "Full research paper text...",
  "max_length": null
}
```

**Response:**
```json
{
  "structure_issues": [
    {
      "severity": "high",
      "type": "missing_sections",
      "description": "Missing sections: literature_review, methodology",
      "recommendation": "Add required sections for a complete research paper"
    }
  ],
  "vague_sentences": [
    {
      "type": "weak_language",
      "text": "I think",
      "context": "...our method I think performs well...",
      "severity": "medium",
      "recommendation": "Replace with specific evidence or clear statement"
    }
  ],
  "irrelevant_parts": [
    {
      "paragraph_index": 5,
      "preview": "The history of computing is fascinating...",
      "similarity_score": 0.25,
      "recommendation": "Consider if this paragraph supports your main argument"
    }
  ],
  "citation_flags": [
    {
      "citation": "[Smith 2010]",
      "year": 2010,
      "age_years": 14,
      "severity": "medium",
      "recommendation": "Consider adding more recent sources (14 years old)"
    }
  ],
  "grammar_issues": [
    {
      "type": "Article error",
      "match": "a elephant",
      "suggestion": "Use 'an' before vowels"
    }
  ],
  "summary": "Analysis of 2500 characters (450 words, 8 paragraphs)",
  "processing_time_ms": 2345.6
}
```

**HTTP Status:** 
- 200: Success
- 400: Invalid input (text too short)
- 403: Invalid API key
- 500: Server error

---

### 4. Get Panel Question
**Endpoint:** `POST /panel/question`

**Authentication:** Required (API Key in header)

**Purpose:** Generate next question from rotating panel professors

**Request Body:**
```json
{
  "text": "Research paper text...",
  "history": [
    {
      "professor": "Dr. Johnson",
      "question": "Why did you choose this methodology?",
      "answer": "Because it is efficient...",
      "feedback": "Good answer..."
    }
  ]
}
```

**Response:**
```json
{
  "professor": "Dr. Chen",
  "expertise": "Literature Expert",
  "question": "How does your work address the gap in the existing literature that you mentioned in the introduction?",
  "focus_areas": ["literature review", "citation coverage", "research gap"],
  "timestamp": "2026-02-19T14:30:45.123456"
}
```

**Behavior:**
- Rotates between 3 professors (methodology, literature, statistics)
- Uses paper and history context to generate relevant questions
- Asks follow-up questions if history provided
- Each professor focuses on their expertise

**HTTP Status:**
- 200: Success
- 400: Invalid input
- 403: Invalid API key
- 500: Generation failed

---

### 5. Evaluate Student Answer
**Endpoint:** `POST /panel/answer_feedback`

**Authentication:** Required (API Key in header)

**Purpose:** Evaluate student's answer to panel question

**Request Body:**
```json
{
  "paper_text": "Research paper text...",
  "question": "How does your work address...",
  "answer": "Our work addresses this by using a novel approach that leverages..."
}
```

**Response:**
```json
{
  "feedback": "Excellent answer! You clearly explained your approach and its novelty. However, you might strengthen it by referencing the specific papers that preceded your work. Overall, this shows good understanding of your research.",
  "timestamp": "2026-02-19T14:31:20.456789"
}
```

**HTTP Status:**
- 200: Success
- 403: Invalid API key
- 500: Evaluation failed

---

### 6. Get Panel Assessment
**Endpoint:** `POST /panel/assessment`

**Authentication:** Required (API Key in header)

**Purpose:** Generate overall panel assessment after questions

**Request Body:**
```json
{
  "text": "Research paper text...",
  "history": [
    {
      "professor": "Dr. Johnson",
      "question": "Why...?",
      "answer": "Because...",
      "feedback": "Good..."
    }
  ]
}
```

**Response:**
```json
{
  "assessment": "The research demonstrates strong understanding of the methodology and clear recognition of the literature gap. The experimental design is sound, though more statistical rigor in the analysis would strengthen the findings. The work makes a solid contribution to the field with good potential for publication with revisions. Key areas for improvement: expand statistical analysis, add more recent citations, and clarify the practical implications of your findings.",
  "overall_recommendation": "Minor revisions needed",
  "timestamp": "2026-02-19T14:32:10.789012"
}
```

**Overall Recommendations:**
- "Accept" - Exceptional work
- "Minor revisions needed" - Good work, small improvements
- "Major revisions needed" - Solid work, significant improvements
- "Reject" - Fundamental issues

**HTTP Status:**
- 200: Success
- 403: Invalid API key
- 500: Assessment generation failed

---

## Error Handling

### Authentication Error (403)
```json
{
  "detail": "Invalid API Key"
}
```

### Validation Error (400)
```json
{
  "detail": "Paper text is too short (min 50 characters)"
}
```

### Server Error (500)
```json
{
  "detail": "Analysis failed: CUDA out of memory"
}
```

---

## Performance Specs

| Operation | Latency | VRAM | Max Input |
|-----------|---------|------|-----------|
| Health Check | <1ms | - | - |
| Paper Analysis (2k words) | 2-5s | 14GB | 4096 tokens |
| Panel Question | 3-8s | 14GB | 2000 tokens |
| Answer Evaluation | 2-4s | 14GB | 2000 tokens |
| Assessment | 4-6s | 14GB | 4096 tokens |

---

## Configuration

### config.py

```python
# Active model to load
ACTIVE_MODEL = "mistral_7b"

# Device selection
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Token limits
MAX_TOKENS = 2048          # Max output length
MAX_INPUT_TOKENS = 4096    # Max input length

# API Security
API_KEY = "aipanelist_secret_key_2026"
ALLOWED_ORIGINS = ["*"]    # Restrict in production

# Server
HOST = "0.0.0.0"
PORT = 8000

# Models directory
MODELS_DIR = "./models"

# Embedding model for relevance
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Citation age threshold
CITATION_AGE_THRESHOLD = 10  # Flag citations >10 years old

# Panel professors
PANEL_PROFESSORS = [...]
```

### main.py Environment

```bash
# Python 3.8+
python --version

# Set GPU
# Windows: No special config needed (uses CUDA_VISIBLE_DEVICES by default)
# Linux: export CUDA_VISIBLE_DEVICES=0

# Run server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Data Flow Examples

### Example 1: Paper Analysis Flow

```
1. User selects paper file
2. Website reads file (TXT, PDF via text extraction)
3. POST /analyze with paper text + API key
4. Server receives request
5. model_loader checks if models loaded
6. If not: load_main_model() + load_embedding_model()
7. paper_analyzer.analyze_paper(text)
   - Extract structure (regex patterns)
   - Find vague statements
   - Semantic similarity check (embeddings)
   - Citation extraction and age check
   - Grammar pattern matching
8. Return JSON results
9. Website displays formatted results
10. User sees issues with recommendations
```

### Example 2: Panel Simulation Flow

```
1. User clicks "Get Next Question"
2. Website POST /panel/question with paper + history
3. Server receives request
4. panel_simulator.get_next_question(paper, history)
5. Rotate to next professor
6. Build context prompt with:
   - Professor name, expertise, focus areas
   - Paper abstract/content
   - Previous Q&A history if exists
7. Send prompt to LLM via model.generate()
8. LLM generates question (3-8 seconds)
9. Return question + professor info
10. Website displays question
11. User types answer
12. Website POST /panel/answer_feedback
13. LLM evaluates answer against paper
14. Return feedback to user
15. Add to history for next question context
```

---

## Model Architecture Details

### Main LLM (Mistral 7B)

- **Architecture**: Mistral variant of Transformer
- **Parameters**: 7.3 billion
- **Context Window**: 8192 tokens
- **Quantization**: float16 (14 GB) or int4 (7 GB)
- **Inference Speed**: ~50 tokens/second on RTX 5060 Ti

### Embedding Model (MiniLM)

- **Architecture**: DistilBERT variant
- **Parameters**: 22 million
- **Output Dimensions**: 384
- **Speed**: Real-time (<100ms)
- **Purpose**: Semantic similarity for relevance checking

---

## Scaling & Optimization

### For Higher Throughput

1. **Model Quantization** (4-bit)
   - Reduces VRAM: 14GB → 7GB
   - Speed: -10-15%
   - Code: See model_loader.py quantization example

2. **Batch Processing**
   - Process multiple papers concurrently
   - Requires queue system (Redis/Celery)

3. **Larger GPU**
   - RTX 4090: Can run 13B models
   - Multiple GPUs: Model parallelism

### For Lower Latency

1. **Smaller Models**
   - Phi-2 (3B): 2-3 second responses
   - DistilGPT: 1-2 second responses

2. **Token Reduction**
   - MAX_TOKENS = 512 (from 2048)
   - MAX_INPUT_TOKENS = 1024 (from 4096)

3. **Model Compilation**
   - torch.compile() (PyTorch 2.0+)
   - 20-30% speedup

---

## Deployment Checklist

- [ ] Models downloaded to ai_server/models/
- [ ] Python 3.8+ installed
- [ ] PyTorch with CUDA installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] config.py updated with API key
- [ ] FastAPI server can start: `python main.py`
- [ ] Website loads: http://127.0.0.1:3000
- [ ] Test /health endpoint returns HTTP 200
- [ ] Test /analyze with sample paper
- [ ] Test /panel/question
- [ ] Cloudflare Tunnel configured (if remote)
- [ ] API key matches in website + config.py
- [ ] HTTPS only (Cloudflare/Ngrok provides this)

---

## Security Considerations

1. **API Key**: Change from default
   - Generate random 32-char string
   - Update in config.py
   - Share only with authorized users

2. **HTTPS**: Always use (provided by Cloudflare/Ngrok)

3. **Input Validation**: 
   - Max token limits prevent model abuse
   - Text length checks prevent OOM

4. **Rate Limiting** (optional):
   - Add slowapi middleware to prevent DDoS
   - Limit requests per user/IP

5. **Model Security**:
   - Models are open-source, no secret information
   - Local execution only (no cloud upload)

---

**Questions?** Review code comments or check FastAPI docs at /docs endpoint.
