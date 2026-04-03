"""
Paper Analysis Module
Analyzes research papers for vague statements, weak arguments, structure issues, etc.
"""
import re
import json
import logging
import torch
from datetime import datetime
from typing import Dict, List
from model_loader import load_main_model, load_embedding_model, clear_cache
from config import MAX_INPUT_TOKENS, CITATION_AGE_THRESHOLD, DEVICE

logger = logging.getLogger(__name__)


class PaperAnalyzer:
    def __init__(self):
        # LAZY LOAD - don't load models until needed (matches old app)
        self.main_model = None
        self.embedding_model = None
        self.current_year = datetime.now().year
    
    def _ensure_models_loaded(self):
        """Load models only when first needed (lazy loading)"""
        if self.main_model is None:
            logger.info("🎮 Loading main model on first request...")
            self.main_model = load_main_model()
        if self.embedding_model is None:
            logger.info("🎮 Loading embedding model on first request...")
            self.embedding_model = load_embedding_model()
    
    def analyze_paper(self, text: str) -> Dict:
        """
        Comprehensive paper analysis
        """
        # LAZY LOAD models on first use (matches old app pattern)
        self._ensure_models_loaded()
        
        # Limit input size
        if len(text) > MAX_INPUT_TOKENS * 4:
            text = text[:MAX_INPUT_TOKENS * 4]
            logger.warning("Input text truncated to token limit")
        
        logger.info(f"Analyzing paper ({len(text)} characters)")
        
        results = {
            "structure_issues": self._analyze_structure(text),
            "vague_sentences": self._identify_vague_statements(text),
            "irrelevant_parts": self._identify_irrelevant_paragraphs(text),
            "citation_flags": self._check_citations(text),
            "grammar_issues": self._check_grammar(text),
            "summary": self._generate_summary(text)
        }
        
        clear_cache()
        return results
    
    def _analyze_structure(self, text: str) -> List[Dict]:
        """Analyze paper structure and organization"""
        issues = []
        
        # Check for common sections
        sections = {
            "abstract": r"(?i)(abstract)",
            "introduction": r"(?i)(introduction|background)",
            "literature_review": r"(?i)(literature|review|related work)",
            "methodology": r"(?i)(methodology|methods|approach)",
            "results": r"(?i)(results|findings)",
            "conclusion": r"(?i)(conclusion|discussion)"
        }
        
        found_sections = {name: bool(re.search(pattern, text)) 
                         for name, pattern in sections.items()}
        
        missing = [s for s, found in found_sections.items() if not found]
        if missing:
            issues.append({
                "severity": "high",
                "type": "missing_sections",
                "description": f"Missing sections: {', '.join(missing)}",
                "recommendation": "Add required sections for a complete research paper"
            })
        
        # Check for paragraph length (too short or too long)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        short_paragraphs = sum(1 for p in paragraphs if len(p) < 100)
        if short_paragraphs > len(paragraphs) * 0.3:
            issues.append({
                "severity": "medium",
                "type": "short_paragraphs",
                "description": f"{short_paragraphs} paragraphs are very short",
                "recommendation": "Expand brief paragraphs with more detail"
            })
        
        return issues
    
    def _identify_vague_statements(self, text: str) -> List[Dict]:
        """Identify vague or weak statements"""
        vague_patterns = [
            (r"(?i)\b(i think|i believe|it seems|it appears|might be|could be|maybe|perhaps)\b", "weak_language"),
            (r"(?i)\b(very|really|quite|fairly|somewhat|sort of|kind of)\b", "imprecise_modifiers"),
            (r"(?i)\b(this shows|it proves|it demonstrates)\b [^.]{0,20}[.?!]", "unsupported_claim"),
            (r"(?i)\b(obvious|clear|evident|well-known)\b", "assumption_without_support"),
        ]
        
        results = []
        for pattern, issue_type in vague_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Get context (sentence)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ').strip()
                
                results.append({
                    "type": issue_type,
                    "text": match.group(0),
                    "context": f"...{context}...",
                    "severity": "medium",
                    "recommendation": "Replace with specific evidence or clear statement"
                })
        
        # Limit to top 10
        return results[:10]
    
    def _identify_irrelevant_paragraphs(self, text: str) -> List[Dict]:
        """Identify paragraphs that might not fit the research topic"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p) > 100]
        
        # Get embeddings for first paragraph (assumed to be intro/abstract)
        if not paragraphs:
            return []
        
        try:
            # Encode on GPU using DEVICE string (proven pattern)
            intro_embedding = self.embedding_model.encode(
                paragraphs[0], 
                convert_to_tensor=True,
                device=DEVICE
            )
            
            irrelevant = []
            for i, para in enumerate(paragraphs[1:], 1):
                if len(para) < 50:  # Skip very short paragraphs
                    continue
                    
                para_embedding = self.embedding_model.encode(
                    para, 
                    convert_to_tensor=True,
                    device=DEVICE
                )
                
                # Calculate similarity
                from torch.nn.functional import cosine_similarity
                similarity = cosine_similarity(intro_embedding, para_embedding, dim=0).item()
                
                if similarity < 0.3:  # Low relevance threshold
                    irrelevant.append({
                        "paragraph_index": i,
                        "preview": para[:150] + "...",
                        "similarity_score": float(similarity),
                        "recommendation": "Consider if this paragraph supports your main argument"
                    })
            
            return irrelevant[:5]
        except Exception as e:
            logger.warning(f"Error in relevance check: {str(e)}")
            return []
    
    def _check_citations(self, text: str) -> List[Dict]:
        """Check citations format and age"""
        citations = []
        
        # Look for reference patterns
        # Pattern: [Author Year], Author (Year), etc.
        citation_patterns = [
            r"\[([^]]+?)(\d{4})\]",  # [Author 2020]
            r"([A-Z][a-z]+)\s*(?:et al\.)?\s*\((\d{4})\)",  # Author et al. (2020)
        ]
        
        found_citations = []
        for pattern in citation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                year_str = match.group(2) if len(match.groups()) > 1 else None
                if year_str:
                    try:
                        year = int(year_str)
                        if year >= 1900 and year <= self.current_year:
                            found_citations.append({
                                "text": match.group(0),
                                "year": year
                            })
                    except ValueError:
                        pass
        
        # Check for outdated citations
        if found_citations:
            for cit in found_citations:
                age = self.current_year - cit["year"]
                if age > CITATION_AGE_THRESHOLD:
                    citations.append({
                        "citation": cit["text"],
                        "year": cit["year"],
                        "age_years": age,
                        "severity": "medium",
                        "recommendation": f"Consider adding more recent sources ({age} years old)"
                    })
        
        return citations
    
    def _check_grammar(self, text: str) -> List[Dict]:
        """Check for common grammar issues"""
        issues = []
        
        # Define patterns for common grammar errors
        grammar_patterns = [
            (r"\b(a)\s+([aeiou])", "Article error", "Use 'an' before vowels"),
            (r"\b(the)\s+(a|an)\b", "Double article", "Remove redundant article"),
            (r"\b(their|there|they're)\b(?![\w])", "Homophone check", "Verify it's the correct form"),
            (r"\b(\w+)\s+(\1)\b", "Repeated word", "Remove duplicate word"),
            (r"([.!?])\s+([a-z])", "Capitalization", "Capitalize first letter after punctuation"),
        ]
        
        for pattern, error_type, suggestion in grammar_patterns:
            matches = list(re.finditer(pattern, text))
            for match in matches[:3]:  # Limit to 3 per type
                issues.append({
                    "type": error_type,
                    "match": match.group(0),
                    "suggestion": suggestion
                })
        
        return issues
    
    def _generate_summary(self, text: str) -> str:
        """Generate brief analysis summary"""
        num_chars = len(text)
        num_words = len(text.split())
        num_paragraphs = len([p for p in text.split('\n\n') if p.strip()])
        
        return f"Analysis of {num_chars} characters ({num_words} words, {num_paragraphs} paragraphs)"
