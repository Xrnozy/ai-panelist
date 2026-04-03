"""
FastAPI Server for AI Panel Review System
Runs on home PC with GPU support
"""
import logging
import json
import os
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import torch

from model_loader import load_main_model, load_embedding_model, get_model_info, clear_cache
from paper_analyzer import PaperAnalyzer
from panel_simulator import PanelSimulator
from config import API_KEY, ALLOWED_ORIGINS, HOST, PORT

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Panel Review System",
    description="Research paper analysis and panel simulation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
analyzer = None
panel = None


# On-demand model loading (lazy initialization)
def get_analyzer():
    """Load analyzer only when needed"""
    global analyzer
    if analyzer is None:
        logger.info("📦 Loading paper analyzer...")
        analyzer = PaperAnalyzer()
    return analyzer


def get_panel():
    """Load panel simulator only when needed"""
    global panel
    if panel is None:
        logger.info("📦 Loading panel simulator...")
        panel = PanelSimulator()
    return panel


# Request/Response Models
class AnalyzeRequest(BaseModel):
    text: str
    max_length: Optional[int] = None


class AnalyzeResponse(BaseModel):
    structure_issues: List[dict]
    vague_sentences: List[dict]
    irrelevant_parts: List[dict]
    citation_flags: List[dict]
    grammar_issues: List[dict]
    summary: str
    processing_time_ms: float


class PanelQuestionRequest(BaseModel):
    text: str
    history: Optional[List[dict]] = None


class PanelQuestionResponse(BaseModel):
    professor: str
    expertise: str
    question: str
    focus_areas: List[str]
    timestamp: str


class PanelAnswerRequest(BaseModel):
    paper_text: str
    question: str
    answer: str


class PanelAnswerResponse(BaseModel):
    feedback: str
    timestamp: str


class AssessmentResponse(BaseModel):
    assessment: str
    overall_recommendation: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    cuda_available: bool
    models_loaded: List[str]
    gpu_memory_allocated: Optional[str] = None


# Authentication
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key


# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting AI Panel Review System (Lazy Loading Mode)...")
    logger.info(f"✓ GPU available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"✓ GPU: {torch.cuda.get_device_name(0)}")
    logger.info("✓ Models will be loaded on-demand (no startup overhead)")
    logger.info(f"✓ Available endpoints: /docs")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Shutting down...")
    clear_cache()


# ==================== ENDPOINTS ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        cuda_available=torch.cuda.is_available(),
        models_loaded=get_model_info()["loaded_models"],
        gpu_memory_allocated=get_model_info().get("gpu_memory_allocated")
    )


@app.get("/info")
async def model_info():
    """Get detailed model information"""
    return get_model_info()


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_paper(
    request: AnalyzeRequest,
    x_api_key: str = Header(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Analyze a research paper for:
    - Structure issues
    - Vague statements
    - Irrelevant paragraphs
    - Citation problems
    - Grammar issues
    """
    # Verify API key
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    if not request.text or len(request.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Paper text is too short (min 50 characters)")
    
    logger.info(f"📄 Analyze request received ({len(request.text)} chars)")
    
    try:
        start_time = datetime.now()
        
        # Load analyzer on-demand
        analyzer_instance = get_analyzer()
        
        # Analyze the paper
        analysis_results = analyzer_instance.analyze_paper(request.text)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Schedule GPU cache clear after response
        background_tasks.add_task(clear_cache)
        
        logger.info(f"✓ Analysis complete in {processing_time:.1f}ms")
        
        return AnalyzeResponse(
            structure_issues=analysis_results["structure_issues"],
            vague_sentences=analysis_results["vague_sentences"],
            irrelevant_parts=analysis_results["irrelevant_parts"],
            citation_flags=analysis_results["citation_flags"],
            grammar_issues=analysis_results["grammar_issues"],
            summary=analysis_results["summary"],
            processing_time_ms=processing_time
        )
    
    except Exception as e:
        logger.error(f"❌ Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/panel/question", response_model=PanelQuestionResponse)
async def get_panel_question(
    request: PanelQuestionRequest,
    x_api_key: str = Header(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Get next question from a panel professor
    Simulates real thesis defense panel
    """
    # Verify API key
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    if not request.text or len(request.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Paper text is too short")
    
    logger.info("❓ Panel question request")
    
    try:
        history = request.history or []
        
        # Load panel simulator on-demand
        panel_instance = get_panel()
        
        question_data = panel_instance.get_next_question(request.text, history)
        
        # Schedule GPU cache clear after response
        background_tasks.add_task(clear_cache)
        
        logger.info(f"✓ Question from {question_data['professor']}")
        
        return PanelQuestionResponse(**question_data)
    
    except Exception as e:
        logger.error(f"❌ Question generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(e)}")


@app.post("/panel/answer_feedback", response_model=PanelAnswerResponse)
async def evaluate_answer(
    request: PanelAnswerRequest,
    x_api_key: str = Header(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Evaluate student's answer and provide feedback
    """
    # Verify API key
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    logger.info("📝 Answer evaluation request")
    
    try:
        # Load panel simulator on-demand
        panel_instance = get_panel()
        
        feedback = panel_instance.evaluate_answer(request.paper_text, request.question, request.answer)
        
        # Schedule GPU cache clear after response
        background_tasks.add_task(clear_cache)
        
        logger.info("✓ Feedback generated")
        
        return PanelAnswerResponse(**feedback)
    
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.post("/panel/assessment", response_model=AssessmentResponse)
async def get_assessment(
    request: PanelQuestionRequest,
    x_api_key: str = Header(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Get overall panel assessment after questions
    """
    # Verify API key
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    logger.info("📊 Assessment request")
    
    try:
        history = request.history or []
        
        # Load panel simulator on-demand
        panel_instance = get_panel()
        
        assessment = panel_instance.get_overall_assessment(request.text, history)
        
        # Schedule GPU cache clear after response
        background_tasks.add_task(clear_cache)
        
        logger.info("✓ Assessment generated")
        
        return AssessmentResponse(**assessment)
    
    except Exception as e:
        logger.error(f"❌ Assessment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


# Root endpoint
@app.get("/")
async def root():
    """Welcome endpoint"""
    return {
        "name": "AI Panel Review System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "info": "/info"
    }


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "detail": "Internal server error",
        "error": str(exc)
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {HOST}:{PORT}")
    logger.info(f"CUDA Available: {torch.cuda.is_available()}")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
