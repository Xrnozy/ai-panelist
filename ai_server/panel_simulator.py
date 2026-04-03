"""
Panel Simulation Module
Simulates professor panel asking questions about the research paper
"""
import json
import logging
import random
import os
import torch
from typing import Dict, List, Optional
from datetime import datetime
from model_loader import load_main_model, clear_cache
from config import PANEL_PROFESSORS, MAX_TOKENS, DEVICE, INFERENCE_MAX_NEW_TOKENS, INFERENCE_TEMPERATURE, INFERENCE_TOP_P, COMPUTE_DTYPE

logger = logging.getLogger(__name__)


class PanelSimulator:
    def __init__(self):
        # LAZY LOAD - don't load models until needed (matches old app)
        self.model_data = None
        self.model = None
        self.tokenizer = None
        self.professors = PANEL_PROFESSORS
        self.current_professor_idx = 0
        
    def _ensure_models_loaded(self):
        """Load models only when first needed (lazy loading)"""
        if self.model is None:
            logger.info("🎮 Loading Mistral model on first request...")
            self.model_data = load_main_model()
            self.model = self.model_data["model"]
            self.tokenizer = self.model_data["tokenizer"]
            
            # Ensure model is on GPU
            self.model.eval()
            assert self.model.device.type == "cuda", "❌ MODEL NOT ON GPU!"
            logger.info(f"✓ Model on GPU: {self.model.device}")
    
    def get_next_question(self, paper_text: str, history: List[Dict]) -> Dict:
        """
        Generate next panel question based on paper and conversation history
        """
        # LAZY LOAD models on first use (matches old app pattern)
        self._ensure_models_loaded()
        
        # Rotate through professors
        professor = self.professors[self.current_professor_idx]
        self.current_professor_idx = (self.current_professor_idx + 1) % len(self.professors)
        
        logger.info(f"Generating question from {professor['name']} ({professor['expertise']})")
        
        # Build context
        context = f"""You are {professor['name']}, a {professor['expertise']} on a PhD thesis panel.

Your expertise focus areas: {', '.join(professor['focus_areas'])}

RESEARCH PAPER ABSTRACT:
{self._truncate_text(paper_text, 1000)}

Your job is to ask ONE CRITICAL, FOCUSED question about the research.
Make it sound natural, challenging but fair.
Focus on: {', '.join(random.sample(professor['focus_areas'], min(2, len(professor['focus_areas']))))}"""
        
        if history:
            context += "\n\nPREVIOUS QUESTIONS & ANSWERS:"
            for i, item in enumerate(history[-3:], 1):  # Show last 3
                context += f"\nQ{i}: {item.get('question', '')}\nA{i}: {item.get('answer', '')}"
            context += "\n\nNow ask a FOLLOW-UP question that builds on previous discussion."
        else:
            context += "\n\nThis is the first question of the panel."
        
        context += "\n\nAsk your question. Keep it to 1-2 sentences."
        
        try:
            question = self._generate_response(context, max_new_tokens=100)
            
            return {
                "professor": professor["name"],
                "expertise": professor["expertise"],
                "question": question.strip(),
                "focus_areas": professor["focus_areas"],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")
            # Fallback
            return {
                "professor": professor["name"],
                "expertise": professor["expertise"],
                "question": self._get_fallback_question(professor),
                "focus_areas": professor["focus_areas"],
                "timestamp": datetime.now().isoformat()
            }
    
    def evaluate_answer(self, paper_text: str, question: str, answer: str) -> Dict:
        """
        Evaluate student's answer and provide feedback
        """
        # LAZY LOAD models on first use
        self._ensure_models_loaded()
        
        logger.info("Evaluating student answer")
        
        prompt = f"""Given this research paper excerpt:
{self._truncate_text(paper_text, 800)}

Panel Question: {question}

Student's Answer: {answer}

Please evaluate the answer in 2-3 sentences. Consider:
1. Does it address the question clearly?
2. Is there evidence from the paper?
3. Are there gaps or inconsistencies?

Format: Evaluation with constructive feedback."""
        
        try:
            feedback = self._generate_response(prompt, max_new_tokens=150)
            
            return {
                "feedback": feedback.strip(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error evaluating answer: {str(e)}")
            return {"feedback": "Please provide a more detailed answer.", "timestamp": datetime.now().isoformat()}
    
    def get_overall_assessment(self, paper_text: str, history: List[Dict]) -> Dict:
        """
        Generate overall assessment after panel questions
        """
        # LAZY LOAD models on first use
        self._ensure_models_loaded()
        
        logger.info("Generating overall assessment")
        
        if not history:
            return {"assessment": "No questions asked yet."}
        
        questions_asked = [h.get('question', '') for h in history]
        assessment_prompt = f"""After reviewing the research paper and asking questions, provide a brief panel assessment (4-5 sentences).

Paper Focus: {self._truncate_text(paper_text, 300)}

Questions Asked:
{chr(10).join(f'- {q}' for q in questions_asked[:5])}

Assessment should cover:
1. Paper strengths
2. Main areas for improvement
3. Likelihood of acceptance
4. Key recommendations"""
        
        try:
            assessment = self._generate_response(assessment_prompt, max_new_tokens=200)
            
            return {
                "assessment": assessment.strip(),
                "timestamp": datetime.now().isoformat(),
                "overall_recommendation": random.choice(["Accept", "Minor revisions needed", "Major revisions needed", "Reject"])
            }
        except Exception as e:
            logger.error(f"Error generating assessment: {str(e)}")
            return {
                "assessment": "Unable to generate assessment.",
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_response(self, prompt: str, max_new_tokens: int = 100) -> str:
        """Generate response using PROVEN GPU-ONLY pattern from audio transcription system"""
        try:
            actual_max_tokens = min(max_new_tokens, INFERENCE_MAX_NEW_TOKENS)
            
            # PROVEN GPU-ONLY PATTERN: torch.no_grad() + simple .to(DEVICE)
            with torch.no_grad():
                # Tokenize
                inputs = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=2048,
                    padding=False
                )
                
                # Move inputs to DEVICE (proven method - not device_map)
                inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
                
                # Generate on GPU (model is already on DEVICE from __init__)
                generated_tokens = self.model.generate(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs.get("attention_mask"),
                    max_new_tokens=actual_max_tokens,
                    temperature=INFERENCE_TEMPERATURE,
                    top_p=INFERENCE_TOP_P,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    use_cache=True
                )
                
                # Decode
                response = self.tokenizer.decode(
                    generated_tokens[0][inputs["input_ids"].shape[1]:],
                    skip_special_tokens=True
                ).strip()
            
            return response if response else "Unable to generate response."
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return "Unable to generate response at this time."
    
    def _get_fallback_question(self, professor: Dict) -> str:
        """Fallback questions if generation fails"""
        fallback_questions = {
            "Methodology Expert": [
                "Can you explain your experimental design and why you chose this approach?",
                "How did you validate your methodology against existing standards?",
                "What limitations does your approach have?",
            ],
            "Literature Expert": [
                "How does your work address the gap in the existing literature?",
                "Which recent papers do you see as most relevant to your research?",
                "How does your contribution differ from prior work?",
            ],
            "Statistician": [
                "Can you walk us through your statistical analysis pipeline?",
                "How did you handle potential confounding variables?",
                "What is the statistical power of your findings?",
            ]
        }
        
        expertise = professor["expertise"]
        return random.choice(fallback_questions.get(expertise, ["Can you elaborate on your main findings?"]))
    
    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncate text to max characters"""
        if len(text) > max_chars:
            return text[:max_chars] + "..."
        return text
