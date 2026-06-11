"""
Enhanced Rule Engine with LangChain Structured Outputs
Production-ready manufacturing rule extraction with 98%+ accuracy target
"""

import asyncio
import json
import logging
import re
import hashlib
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

# Core LangChain imports
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_groq import ChatGroq

# Pydantic for config only
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

# Analytics and monitoring
import structlog
import tiktoken
from textstat import flesch_reading_ease, automated_readability_index
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np
import pandas as pd

# Local imports
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from .enhanced_vector_utils import EnhancedVectorManager
from .rule_extraction import DocumentLoader
from .chunk_cache import ChunkCache, FileChunkCache
from .prompts import PromptLibrary
logger = logging.getLogger(__name__)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Structured logger
enhanced_logger = structlog.get_logger()

class ManufacturingCategory(str, Enum):
    """Manufacturing categories enum for validation."""
    SHEET_METAL = "Sheet Metal"
    INJECTION_MOLDING = "Injection Molding"
    MACHINING = "Machining"
    ASSEMBLY = "Assembly"
    WELDING = "Welding"
    CASTING = "Casting"
    QUALITY_CONTROL = "Quality Control"
    ELECTRONICS = "Electronics"
    MATERIAL_SPECIFICATION = "Material Specification"
    SAFETY_REQUIREMENT = "Safety Requirement"
    DESIGN_GUIDELINE = "Design Guideline"
    GENERAL = "General"

class RuleType(str, Enum):
    """Rule type classification."""
    DIMENSIONAL = "dimensional"
    MATERIAL = "material"
    PROCESS = "process"
    QUALITY = "quality"
    SAFETY = "safety"
    ASSEMBLY = "assembly"
    TOLERANCE = "tolerance"
    GENERAL = "general"

class CorrectnessTag(str, Enum):
    """Correctness tagging for rule validation."""
    CORRECT = "correct"
    OUT_OF_SCOPE = "out_of_scope"
    LOW_CONFIDENCE = "low_confidence"
    NEEDS_REVIEW = "needs_review"
    INCOMPLETE = "incomplete"

class ConfidenceLevel(str, Enum):
    """Confidence level categories."""
    HIGH = "high"      # 0.8-1.0
    MEDIUM = "medium"  # 0.6-0.8
    LOW = "low"        # 0.4-0.6
    VERY_LOW = "very_low"  # 0.0-0.4

class ManufacturingRule(BaseModel):
    """Enhanced Pydantic model for manufacturing rules with validation."""
    
    # Core fields
    rule_text: str = Field(..., description="Original rule text", max_length=500)
    rule_category: ManufacturingCategory = Field(default=ManufacturingCategory.GENERAL, description="Manufacturing category")
    rule_type: RuleType = Field(default=RuleType.GENERAL, description="Type of rule")
    
    # Extracted entities
    primary_feature: Optional[str] = Field(default="", description="Primary manufacturing feature")
    secondary_feature: Optional[str] = Field(default="", description="Secondary feature if applicable")
    primary_object: Optional[str] = Field(default="", description="Primary object/component (may be empty if not specified)")
    secondary_object: Optional[str] = Field(default="", description="Secondary object if applicable")
    
    # Constraints and specifications
    operator: Optional[str] = Field(default="", description="Comparison operator (>=, <=, ==, between, etc.)")
    value: Optional[Union[float, List[float], str]] = Field(default=None, description="Numeric value or range")
    unit: Optional[str] = Field(default="", description="Unit of measurement")
    tolerance: Optional[Union[float, List[float]]] = Field(default=None, description="Tolerance value (single number or range)")
    
    # Metadata
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    confidence_level: ConfidenceLevel = Field(default=ConfidenceLevel.LOW, description="Confidence category")
    correctness_tag: CorrectnessTag = Field(default=CorrectnessTag.NEEDS_REVIEW, description="Correctness validation tag")
    manufacturing_relevance: float = Field(default=0.5, ge=0.0, le=1.0, description="Manufacturing relevance score")
    
    # Context
    source_document: str = Field(default="", description="Source document filename")
    document_section: Optional[str] = Field(default="", description="Document section/page")
    extraction_method: str = Field(default="unknown", description="Method used for extraction")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Quality indicators
    readability_score: Optional[float] = Field(default=None, description="Text readability score")
    complexity_score: Optional[float] = Field(default=None, description="Rule complexity score")
    
    # Advanced features
    implicit_requirements: List[str] = Field(default_factory=list, description="Implicit requirements")
    related_standards: List[str] = Field(default_factory=list, description="Related industry standards")
    cross_references: List[str] = Field(default_factory=list, description="Cross-referenced rules")
    
    @validator('rule_type', pre=True, always=True)
    def normalize_rule_type(cls, value):
        """Normalize rule type to enum values."""
        if value is None:
            return RuleType.GENERAL
        if isinstance(value, RuleType):
            return value
            
        normalized = str(value).strip().lower()
        # Map common variations
        type_map = {
            'dimensional specification': RuleType.DIMENSIONAL,
            'material specification': RuleType.MATERIAL,
            'process specification': RuleType.PROCESS,
            'quality specification': RuleType.QUALITY,
            'safety requirement': RuleType.SAFETY,
            'design specification': RuleType.GENERAL,
            'design requirement': RuleType.GENERAL,
            'proportional specification': RuleType.DIMENSIONAL,
        }
        
        if normalized in type_map:
            return type_map[normalized]
            
        try:
            return RuleType(normalized)
        except ValueError:
            # Fallback for unknown types
            return RuleType.GENERAL

    @validator('confidence_level', pre=True, always=True)
    def set_confidence_level(cls, v, values):
        if 'confidence_score' in values:
            score = values['confidence_score']
            if score >= 0.8:
                return ConfidenceLevel.HIGH
            elif score >= 0.6:
                return ConfidenceLevel.MEDIUM
            elif score >= 0.4:
                return ConfidenceLevel.LOW
            else:
                return ConfidenceLevel.VERY_LOW
        return v
    
    @validator('correctness_tag', pre=True, always=True)
    def set_correctness_tag(cls, v, values):
        """Auto-assign correctness tag based on rule characteristics."""
        if 'confidence_score' in values and 'manufacturing_relevance' in values:
            confidence = values['confidence_score']
            relevance = values['manufacturing_relevance']
            
            # Out of scope if very low relevance
            if relevance < 0.2:
                return CorrectnessTag.OUT_OF_SCOPE
            
            # Low confidence needs review
            if confidence < 0.4:
                return CorrectnessTag.LOW_CONFIDENCE
            
            # Incomplete if missing key fields
            rule_text = values.get('rule_text', '')
            if len(rule_text.strip()) < 20 or not any(char.isdigit() for char in rule_text):
                return CorrectnessTag.INCOMPLETE
            
            # Needs review if medium confidence
            if confidence < 0.7:
                return CorrectnessTag.NEEDS_REVIEW
            
            # High confidence and relevance = correct
            return CorrectnessTag.CORRECT
        
        return CorrectnessTag.NEEDS_REVIEW

    @validator('value', pre=True)
    def parse_value(cls, value):
        """Normalize numeric value field."""
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, list):
            cleaned = []
            for item in value:
                if item in (None, ""):
                    continue
                try:
                    cleaned.append(float(item))
                except (TypeError, ValueError):
                    continue
            if not cleaned:
                return None
            if len(cleaned) == 1:
                return cleaned[0]
            return cleaned
        if isinstance(value, str):
            normalized = value.replace(',', ' ')
            numbers = re.findall(r'-?\d*\.?\d+', normalized)
            if not numbers:
                return value
            floats = [float(num) for num in numbers]
            if len(floats) == 1:
                return floats[0]
            return floats
        return value

    @validator('tolerance', pre=True)
    def parse_tolerance(cls, value):
        """Normalize tolerance values into floats or ranges."""
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, list):
            cleaned = []
            for item in value:
                if item in (None, ""):
                    continue
                try:
                    cleaned.append(float(item))
                except (TypeError, ValueError):
                    continue
            if not cleaned:
                return None
            if len(cleaned) == 1:
                return cleaned[0]
            return cleaned
        if isinstance(value, str):
            normalized = value.replace(',', ' ')
            numbers = re.findall(r'-?\d*\.?\d+', normalized)
            if not numbers:
                return None
            floats = [float(num) for num in numbers]
            if len(floats) == 1:
                return floats[0]
            return floats
        return None

    @validator('extracted_at', pre=True, always=True)
    def normalize_extracted_at(cls, value):
        """Ensure ``extracted_at`` is always a valid timestamp."""

        if not value:
            return datetime.utcnow()
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return datetime.utcnow()
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(cleaned, fmt)
                except ValueError:
                    continue
        return datetime.utcnow()

    @validator('rule_category', pre=True, always=True)
    def normalize_rule_category(cls, value):
        """Map freeform categories into the enumerated set."""

        if value is None:
            return ManufacturingCategory.GENERAL
        if isinstance(value, ManufacturingCategory):
            return value

        normalized = str(value).strip().lower()
        category_map = {
            'pharmaceutical': ManufacturingCategory.QUALITY_CONTROL,
            'pharma': ManufacturingCategory.QUALITY_CONTROL,
            'quality control': ManufacturingCategory.QUALITY_CONTROL,
            'occupational health and safety': ManufacturingCategory.SAFETY_REQUIREMENT,
            'occupational health & safety': ManufacturingCategory.SAFETY_REQUIREMENT,
            'occupational safety': ManufacturingCategory.SAFETY_REQUIREMENT,
            'safety': ManufacturingCategory.SAFETY_REQUIREMENT,
            'health and safety': ManufacturingCategory.SAFETY_REQUIREMENT,
            'material': ManufacturingCategory.MATERIAL_SPECIFICATION,
            'materials': ManufacturingCategory.MATERIAL_SPECIFICATION,
            'assembly': ManufacturingCategory.ASSEMBLY,
            'machining': ManufacturingCategory.MACHINING,
            'process': ManufacturingCategory.GENERAL,
        }
        try:
            return ManufacturingCategory[normalized.replace(" ", "_").upper()]
        except KeyError:
            pass

        for key, mapped in category_map.items():
            if key in normalized:
                return mapped

        return ManufacturingCategory.GENERAL


class ManufacturingRuleList(BaseModel):
    """Container model for multiple manufacturing rules per chunk.

    This allows the enhanced engine to extract more than one rule from a
    given text segment while still leveraging LangChain's structured
    output parsing.
    """

    rules: List[ManufacturingRule] = Field(
        default_factory=list,
        description="List of extracted manufacturing rules for a chunk",
    )


class ManufacturingRuleCandidate(BaseModel):
    """Minimal, tolerant model used to accept partial rule outputs from the LLM.

    Only `rule_text` is required — other fields are optional and will be
    reconciled later into a full `ManufacturingRule` with sensible defaults.
    """

    rule_text: str = Field(..., description="Original rule text")
    confidence_score: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)
    rule_category: Optional[str] = Field(default=None)
    rule_type: Optional[str] = Field(default=None)
    primary_feature: Optional[str] = Field(default=None)
    primary_object: Optional[str] = Field(default=None)
    operator: Optional[str] = Field(default=None)
    value: Optional[Any] = Field(default=None)
    unit: Optional[Any] = Field(default=None)


class ManufacturingRuleCandidateList(BaseModel):
    rules: List[ManufacturingRuleCandidate] = Field(
        default_factory=list,
        description="List of candidate rules (tolerant schema)",
    )

class RawRuleItem(BaseModel):
    """Lightweight representation for raw rule text returned by bulk extraction."""

    text: str = Field(..., description="Raw rule text")
    confidence_score: Optional[float] = Field(default=0.6, ge=0.0, le=1.0, description="Optional confidence")

class RawRuleList(BaseModel):
    """Container model for bulk/raw extraction responses."""

    rules: List[RawRuleItem] = Field(default_factory=list, description="List of raw rule items")

class RuleExtractionResult(BaseModel):
    """Complete result from enhanced rule extraction."""
    rules: List[ManufacturingRule] = Field(description="Extracted manufacturing rules")
    document_metadata: Dict[str, Any] = Field(description="Document analysis metadata")
    extraction_stats: Dict[str, Any] = Field(description="Extraction statistics")
    processing_time: float = Field(description="Processing time in seconds")
    token_usage: Dict[str, int] = Field(description="Token usage statistics")

class DocumentContext(BaseModel):
    """Enhanced document context analysis."""
    industry_sector: str = Field(default="Unknown", description="Identified industry sector")
    technical_domain: str = Field(default="General", description="Technical domain")
    document_type: str = Field(default="Unspecified", description="Document type")
    document_purpose: str = Field(default="General", description="Document purpose")
    
    # Content analysis
    key_concepts: List[str] = Field(default_factory=list, description="Key technical concepts")
    manufacturing_density: float = Field(default=0.0, description="Manufacturing content density")
    technical_complexity: float = Field(default=0.0, description="Technical complexity score")
    
    # Language metrics
    readability_index: float = Field(default=0.0, description="Document readability")
    avg_sentence_length: float = Field(default=0.0, description="Average sentence length")
    
    # Manufacturing specifics
    process_types: List[str] = Field(default_factory=list, description="Manufacturing processes identified")
    material_types: List[str] = Field(default_factory=list, description="Materials mentioned")
    quality_standards: List[str] = Field(default_factory=list, description="Quality standards referenced")

class EnhancedConfig(BaseSettings):
    """Production configuration with validation.

    Level 1 (rule extraction) always takes its Groq model from the
    GROQ_MODEL environment variable when available. If that variable is
    not set, we default to the GPT‑OSS‑20B family identifier so that
    all callers (CLI, Streamlit, batch) converge on the same model.
    """

    # LLM Configuration
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    groq_api_key: str = ""
    max_tokens: int = 3000
    temperature: float = 0.05

    # Processing Configuration
    chunk_size: int = 400  # Token-aware chunking (keep low for 8k TPM models)
    chunk_overlap: int = 100
    max_chunks_per_document: int = 60
    recall_mode: bool = False
    
    # Quality thresholds
    min_confidence_threshold: float = 0.3
    min_manufacturing_relevance: float = 0.2
    max_rules_per_document: int = 250

    # Lightweight rate limiting / retry controls (enhanced engine only)
    throttle_seconds: float = 60.0  # ~60s between calls to stay under 8k TPM
    max_retries: int = 2
    retry_backoff_seconds: float = 2.0
    
    # RAG Configuration
    rag_top_k: int = 5
    rag_score_threshold: float = 0.7
    enable_rag_enhancement: bool = False
    api_request_delay: float = 0.0  # handled by throttle_seconds now
    
    # Advanced features
    enable_semantic_chunking: bool = True
    enable_cross_validation: bool = True
    enable_rule_clustering: bool = False
    enable_quality_scoring: bool = True
    
    # Extraction mode: 'structured', 'raw', or 'auto'
    extraction_mode: str = "structured"
    allow_bulk_extraction: bool = False
    # If Groq is unavailable or you need quick local recall, enable the
    # heuristic keyword extractor that does not rely on LLM calls.
    enable_local_heuristic: bool = True

    # Monitoring
    log_level: str = "INFO"
    enable_metrics: bool = True

    # Resumable extraction (chunk cache)
    enable_chunk_cache: bool = False
    resume_from_cache: bool = False
    chunk_cache_dir: str = "output/chunk_cache"
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Allow extra fields in .env file

class EnhancedRuleEngine:
    """Production-ready rule extraction engine with LangChain integration."""
    
    def __init__(
        self,
        config: Optional[EnhancedConfig] = None,
        vector_manager: Optional[Any] = None,
        *,
        chunk_cache: Optional[ChunkCache] = None,
    ):
        """Initialize enhanced rule engine."""
        
        self.config = config or EnhancedConfig()

        # Enable high-recall defaults when requested
        self._recall_mode = bool(self.config.recall_mode)
        if self._recall_mode:
            self.config.allow_bulk_extraction = True
            self.config.extraction_mode = "raw"
            self.config.min_confidence_threshold = min(self.config.min_confidence_threshold, 0.1)
            self.config.min_manufacturing_relevance = min(self.config.min_manufacturing_relevance, 0.05)
            # Allow larger document coverage in recall mode
            if self.config.max_chunks_per_document < 80:
                self.config.max_chunks_per_document = 80
        
        # Validate API key (no hardcoded or placeholder keys allowed)
        if not self.config.groq_api_key or self.config.groq_api_key == "":
            raise ValueError(
                "GROQ_API_KEY is required but not set. "
                "Please set the GROQ_API_KEY environment variable or create a .env file. "
                "Get your API key from https://console.groq.com/"
            )
        # No hardcoded or placeholder keys allowed in code
        if self.config.groq_api_key.lower().startswith("sk-groq") or self.config.groq_api_key == "your_actual_groq_api_key_here":
            raise ValueError("GROQ_API_KEY appears to be a placeholder or hardcoded key. Please use a secure environment variable.")
        
        self.vector_manager = vector_manager
        self.loader = DocumentLoader()

        # Optional per-chunk cache for resumable extraction.
        self._chunk_cache: Optional[ChunkCache] = chunk_cache
        if self._chunk_cache is None and (self.config.enable_chunk_cache or self.config.resume_from_cache):
            self._chunk_cache = FileChunkCache(Path(self.config.chunk_cache_dir))
        
        # Initialize tokenizer for token-aware processing
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Load mega-prompt from single source of truth
        self.prompt_library = PromptLibrary()
        
        # Initialize LLM with structured output
        self._preferred_model = self.config.groq_model
        self._fallback_model = "llama-3.1-8b-instant"
        self._last_llm_error: Optional[Exception] = None

        # Simple per-process rate limiting state for the enhanced engine.
        self._last_call_time: float = 0.0
        self._tpd_blocked_until: Optional[float] = None

        if not self._try_configure_llm(self._preferred_model):
            if (
                self._preferred_model != self._fallback_model
                and self._try_configure_llm(self._fallback_model)
            ):
                enhanced_logger.warning(
                    "groq_model_fallback_startup",
                    requested_model=self._preferred_model,
                    fallback_model=self._fallback_model,
                )
            else:
                raise ValueError(
                    f"Failed to initialize Groq LLM: {self._last_llm_error}. Please check your GROQ_API_KEY."
                )
        
        # Setup JSON output parser (NO PYDANTIC VALIDATION)
        self.rule_parser = JsonOutputParser()
        
        # Setup LangChain chains
        self._setup_extraction_chains()
        
        # Initialize quality assessors
        self._initialize_quality_assessors()
        
        enhanced_logger.info("Enhanced rule engine initialized", 
                           model=self.config.groq_model,
                           has_vector_manager=self.vector_manager is not None)

    # ------------------------------------------------------------------
    # Internal rate limiting helpers
    # ------------------------------------------------------------------

    def _respect_tpd_limit(self) -> bool:
        """Return False if we know the daily token limit is exhausted.

        When Groq reports a tokens‑per‑day (TPD) exhaustion, we record a
        timestamp until which further calls are very likely to fail.  All
        subsequent LLM invocations short‑circuit until that window expires.
        """

        if self._tpd_blocked_until is None:
            return True

        now = time.time()
        if now >= self._tpd_blocked_until:
            self._tpd_blocked_until = None
            return True

        enhanced_logger.error(
            "groq_daily_limit_exhausted",
            blocked_until=self._tpd_blocked_until,
        )
        return False

    def _update_tpd_from_error(self, error: Exception) -> None:
        """Inspect an error message and update daily limit window if needed."""

        message = str(error)
        if "429" not in message or "tokens per day (TPD)" not in message:
            return

        # Try to parse "Please try again in XmYs" or "in Xs" style hints.
        retry_seconds: float = 300.0  # sensible fallback ~5 minutes
        try:
            match = re.search(r"Please try again in (\d+)m([0-9.]+)s", message)
            if match:
                minutes = float(match.group(1))
                seconds = float(match.group(2))
                retry_seconds = max(retry_seconds, minutes * 60.0 + seconds)
            else:
                match = re.search(r"Please try again in ([0-9.]+)s", message)
                if match:
                    retry_seconds = max(retry_seconds, float(match.group(1)))
        except Exception:  # pragma: no cover - defensive parsing
            pass

        self._tpd_blocked_until = time.time() + retry_seconds
        enhanced_logger.error(
            "groq_daily_limit_window_set",
            retry_after_seconds=retry_seconds,
        )

    def _sleep_for_throttle(self) -> None:
        """Coarse, blocking throttle between enhanced-engine calls."""

        interval = max(0.0, float(self.config.throttle_seconds or 0.0))
        if interval <= 0.0:
            return

        now = time.time()
        delta = now - self._last_call_time
        if delta < interval:
            wait = interval - delta
            enhanced_logger.info("Rate-limit throttle", wait_seconds=round(wait, 1))
            time.sleep(wait)
        self._last_call_time = time.time()

    def _canonicalize_rule_text(self, text: str) -> str:
        """Clean and normalize rule text returned by the LLM or heuristic.

        Actions:
        - Remove common page headers/footers and markers
        - Strip leading bullets/prefixes (Note:, Tip:, •, -)
        - Collapse whitespace, remove excessive newlines
        - Ensure sentence ends with punctuation and is concise
        """

        if not text:
            return ""

        s = text
        # Remove page markers like '--- Page 1 ---' or 'Page 1 of 10'
        s = re.sub(r"-+\s*Page\s*\d+\s*-+", "", s, flags=re.IGNORECASE)
        s = re.sub(r"Page\s*\d+(\s*of\s*\d+)?", "", s, flags=re.IGNORECASE)

        # Remove common boilerplate / recycle lines
        s = re.sub(r"Please recycle\.|Please recycle.*", "", s, flags=re.IGNORECASE)

        # Remove leading prefixes (case-insensitive)
        s = re.sub(r"(?i)^\s*(note:|tip:|•|\*|-\s+|o\s+)\s*", "", s)
        # Remove multiple internal newlines and collapse whitespace
        s = re.sub(r"\s+", " ", s).strip()

        # Remove page number patterns like '1 / 10' or '1. '
        s = re.sub(r"^\d+\s*/\s*\d+", "", s)
        s = re.sub(r"^\d+\.\s*", "", s)

        # Trim to reasonable length
        s = s.strip()
        if len(s) > 240:
            s = s[:240].rsplit(' ', 1)[0] + '...'

        # Ensure final punctuation
        if not re.search(r"[.!?]$", s):
            s = s + "."

        return s

    def _document_cache_id(self, *, filename: str, text: str) -> str:
        """Stable identifier for chunk caching.

        Uses a content hash so resume remains correct across runs.
        """

        name = Path(filename).name if filename else "document"
        digest = hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()[:16]
        return f"{name}__{digest}"

    def _chunk_text_hash(self, chunk_text: str) -> str:
        return hashlib.md5(chunk_text.encode("utf-8", errors="ignore")).hexdigest()

    def _try_configure_llm(self, model_name: str) -> bool:
        try:
            self.llm = ChatGroq(
                model=model_name,
                api_key=self.config.groq_api_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            self.config.groq_model = model_name
            self._last_llm_error = None
            return True
        except Exception as error:  # pragma: no cover - network / access errors
            self._last_llm_error = error
            return False

    def _ensure_llm_available(self, error: Exception) -> bool:
        message = str(error).lower()
        if "model_not_found" not in message and "does not exist" not in message:
            return False
        if self.config.groq_model == self._fallback_model:
            return False
        if self._try_configure_llm(self._fallback_model):
            self._setup_extraction_chains()
            enhanced_logger.warning(
                "groq_model_fallback_runtime",
                requested_model=self._preferred_model,
                fallback_model=self._fallback_model,
            )
            return True
        enhanced_logger.error(
            "groq_model_fallback_failed",
            requested_model=self._preferred_model,
            fallback_model=self._fallback_model,
            error=str(self._last_llm_error),
        )
        return False
    
    async def extract_rules_from_text(
        self,
        text: str,
        filename: str = "ad_hoc.txt",
    ) -> Dict[str, Any]:
        """Public async helper that mirrors the legacy interface."""

        result = await self.extract_rules_parallel(text, filename)
        # result is already a dict, return as-is
        return result

    def _setup_extraction_chains(self):
        """Setup LangChain chains using mega-prompt from prompts.py."""
        
        # Use mega-prompt from prompts.py as single source of truth
        # Escape curly braces in the prompt to avoid template variable issues
        rule_system_prompt = self.prompt_library.compiler_prompt.replace("{", "{{").replace("}", "}}")
        
        rule_human_prompt = """Text Chunk:
{text_chunk}

Return ONLY the JSON object with format: {{"rules": [...]}}. No markdown, no explanations."""
        
        # Single extraction chain - LLM output flows verbatim to JSON
        self.rule_extraction_chain = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(rule_system_prompt),
            HumanMessagePromptTemplate.from_template(rule_human_prompt)
        ]) | self.llm | self.rule_parser
    
    def _initialize_quality_assessors(self):
        """Initialize quality assessment tools."""
        self.manufacturing_keywords = {
            'high_priority': [
                'minimum', 'maximum', 'thickness', 'diameter', 'radius', 'tolerance',
                'clearance', 'specification', 'requirement', 'standard', 'shall',
                'must', 'required', 'not less than', 'not exceed', 'between'
            ],
            'manufacturing': [
                'machining', 'molding', 'assembly', 'welding', 'casting',
                'sheet metal', 'injection', 'drilling', 'milling', 'turning'
            ],
            'materials': [
                'steel', 'aluminum', 'plastic', 'carbon', 'titanium', 'copper',
                'stainless', 'alloy', 'composite', 'polymer'
            ],
            'dimensions': [
                'length', 'width', 'height', 'depth', 'angle', 'surface finish',
                'roughness', 'flatness', 'roundness', 'concentricity'
            ]
        }
        
        # Initialize TF-IDF for content analysis
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 3)
        )

    def _rerank_rag_context(
        self,
        query: str,
        contexts: List[Dict[str, Any]],
        *,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Lightweight local reranker for retrieved context.

        Keeps dependencies minimal by using TF-IDF cosine similarity.
        This improves relevance ordering when the vector store returns noisy hits.
        """

        if not contexts or top_k <= 0:
            return []

        texts = [str(c.get("text", "")) for c in contexts]
        query_text = str(query or "")
        if not query_text.strip():
            return contexts[:top_k]

        try:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=3000)
            matrix = vectorizer.fit_transform([query_text] + texts)
            query_vec = matrix[0]
            ctx_vecs = matrix[1:]
            # Cosine similarity since TF-IDF vectors are L2 normalized by default in sklearn.
            sims = (ctx_vecs @ query_vec.T).toarray().reshape(-1)
            ranked = [c for _, c in sorted(zip(sims, contexts), key=lambda x: x[0], reverse=True)]
            return ranked[:top_k]
        except Exception:
            return contexts[:top_k]
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.tokenizer.encode(text))
    
    def semantic_chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Advanced semantic chunking with manufacturing context awareness."""
        
        # Split into sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        current_sentences: List[str] = []
        current_tokens = 0
        manufacturing_score = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            # Calculate manufacturing relevance for this sentence
            sentence_lower = sentence.lower()
            mfg_score = sum(1 for kw in self.manufacturing_keywords['high_priority'] 
                           if kw in sentence_lower)
            
            # Check if adding this sentence would exceed token limit
            if current_tokens + sentence_tokens > self.config.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'text': current_chunk.strip(),
                    'token_count': current_tokens,
                    'manufacturing_score': manufacturing_score,
                    'sentence_count': len(re.split(r'[.!?]', current_chunk))
                })
                
                # Start new chunk with overlap
                if self.config.chunk_overlap > 0:
                    # IMPORTANT: overlap must come from the *current* chunk, not the full document.
                    overlap_sentences = current_sentences[-2:] if len(current_sentences) > 2 else current_sentences
                    current_sentences = list(overlap_sentences) + [sentence]
                    current_chunk = " ".join(current_sentences)
                    current_tokens = self.count_tokens(current_chunk)
                else:
                    current_chunk = sentence
                    current_tokens = sentence_tokens
                    current_sentences = [sentence]
                
                manufacturing_score = mfg_score
            else:
                current_chunk += " " + sentence
                current_tokens += sentence_tokens
                manufacturing_score += mfg_score
                current_sentences.append(sentence)
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'token_count': current_tokens,
                'manufacturing_score': manufacturing_score,
                'sentence_count': len(re.split(r'[.!?]', current_chunk))
            })
        
        if not chunks:
            return []

        # Preserve chronological coverage; downsample evenly only if we exceed the cap
        max_chunks = max(1, int(self.config.max_chunks_per_document)) if self.config.max_chunks_per_document else len(chunks)
        if len(chunks) > max_chunks:
            # Evenly sample across the document so we do not lose coverage
            if max_chunks == 1:
                return [chunks[0]]

            positions = [
                round(i * (len(chunks) - 1) / (max_chunks - 1))
                for i in range(max_chunks)
            ]
            # Preserve order and drop any accidental duplicates from rounding
            seen = set()
            selected = []
            for pos in positions:
                if pos in seen:
                    continue
                seen.add(pos)
                selected.append(chunks[pos])
            return selected

        return chunks
    
    def analyze_document_context(self, text: str, *, _retry: bool = True) -> DocumentContext:
        """Analyze document context using LangChain structured output."""
        
        try:
            if not self._respect_tpd_limit():
                return DocumentContext()

            # Prepare text for analysis (first 2000 characters)
            analysis_text = text[:2000] if len(text) > 2000 else text
            
            # Run context analysis chain
            self._sleep_for_throttle()
            context = self.context_chain.invoke({
                'document_text': analysis_text,
                'format_instructions': self.context_parser.get_format_instructions()
            })

            if self.config.api_request_delay:
                time.sleep(self.config.api_request_delay)
            
            # Calculate additional metrics
            context.readability_index = flesch_reading_ease(analysis_text)
            context.avg_sentence_length = len(analysis_text.split()) / len(re.split(r'[.!?]', analysis_text))
            
            # Calculate manufacturing density
            total_words = len(analysis_text.split())
            mfg_words = sum(1 for word in analysis_text.lower().split() 
                           if any(kw in word for kw_list in self.manufacturing_keywords.values() 
                                 for kw in kw_list))
            context.manufacturing_density = mfg_words / total_words if total_words > 0 else 0.0
            
            return context
            
        except Exception as e:
            self._update_tpd_from_error(e)
            if _retry and self._ensure_llm_available(e):
                return self.analyze_document_context(text, _retry=False)
            enhanced_logger.error("Context analysis failed", error=str(e))
            return DocumentContext()
    
    def extract_single_rule(self, text_chunk: str, document_context: DocumentContext,
                           rag_context: List[Dict] = None, *, _retry: bool = True) -> Optional[ManufacturingRule]:
        """Extract single rule using LangChain structured output with enhancement limits."""
        
        # Check if chunk is high-value before processing
        if not self._is_high_value_chunk(text_chunk):
            enhanced_logger.debug("Skipping low-value chunk", chunk_preview=text_chunk[:50])
            return None
        
        max_retries = 2  # Limit LLM enhancement calls
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Identify manufacturing keywords in chunk
                chunk_lower = text_chunk.lower()
                detected_keywords = []
                for category, keywords in self.manufacturing_keywords.items():
                    found = [kw for kw in keywords if kw in chunk_lower]
                    detected_keywords.extend(found)
                
                # Format RAG context
                rag_context_str = ""
                if rag_context:
                    rag_context_str = "\n".join([
                        f"- {ctx.get('text', '')[:100]}..." 
                        for ctx in rag_context[:3]
                    ])
                
                # Run rule extraction chain
                rule = self.rule_extraction_chain.invoke({
                    'text_chunk': text_chunk,
                    'industry_sector': document_context.industry_sector,
                    'technical_domain': document_context.technical_domain,
                    'document_type': document_context.document_type,
                    'rag_context': rag_context_str,
                    'manufacturing_keywords': ", ".join(detected_keywords),
                    'format_instructions': self.rule_parser.get_format_instructions()
                })

                if self.config.api_request_delay:
                    time.sleep(self.config.api_request_delay)
                
                # Validate extracted rule quality
                if self._is_rule_quality_acceptable(rule):
                    # Add computed fields
                    rule.readability_score = flesch_reading_ease(text_chunk)
                    rule.complexity_score = len(detected_keywords) / len(text_chunk.split()) if text_chunk.split() else 0
                    rule.extraction_method = "langchain_structured"
                    return rule
                
                # If rule quality is poor and we have retries left, try enhancement
                if retry_count < max_retries:
                    retry_count += 1
                    enhanced_logger.debug("Rule quality poor, attempting enhancement", 
                                        retry=retry_count, 
                                        confidence=rule.confidence_score)
                    
                    # Try to enhance the rule
                    rule = self._enhance_rule_quality(rule, text_chunk, document_context)
                    continue
                
                # No more retries, return the rule as-is
                rule.readability_score = flesch_reading_ease(text_chunk)
                rule.complexity_score = len(detected_keywords) / len(text_chunk.split()) if text_chunk.split() else 0
                rule.extraction_method = "langchain_structured"
                return rule
                
            except Exception as e:
                if _retry and self._ensure_llm_available(e):
                    return self.extract_single_rule(
                        text_chunk,
                        document_context,
                        rag_context,
                        _retry=False,
                    )
                enhanced_logger.error("Rule extraction failed", 
                                    chunk_preview=text_chunk[:100],
                                    retry=retry_count,
                                    error=str(e))
                
                if retry_count < max_retries:
                    retry_count += 1
                    continue
                return None
        
        return None

    def extract_rules_from_chunk(
        self,
        text_chunk: str,
        document_context: Any = None,
        rag_context: List[Dict] = None,
        *,
        _retry: bool = True,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Extract multiple rules from chunk - LLM output flows verbatim to JSON.
        NO post-processing, NO validation, NO mutation.
        """

        try:
            if not self._respect_tpd_limit():
                return [], 0

            self._sleep_for_throttle()
            
            # Call LLM with mega-prompt
            result = self.rule_extraction_chain.invoke({
                'text_chunk': text_chunk,
            })

            if self.config.api_request_delay:
                time.sleep(self.config.api_request_delay)

            # Extract rules list from LLM response - NO MUTATION
            rules = result.get('rules', []) if isinstance(result, dict) else []
            
            return rules, len(rules)
            
        except Exception as e:
            self._update_tpd_from_error(e)
            if _retry and self._ensure_llm_available(e):
                return self.extract_rules_from_chunk(
                    text_chunk,
                    document_context,
                    rag_context,
                    _retry=False,
                )
            enhanced_logger.error(
                "Rule extraction failed",
                chunk_preview=text_chunk[:100],
                error=str(e),
            )
            return [], 0

    def extract_raw_rules_from_chunk(
        self,
        text_chunk: str,
        document_context: DocumentContext,
        rag_context: List[Dict] = None,
        *,
        _retry: bool = True,
    ) -> List[ManufacturingRule]:
        """Lightweight raw/bulk extraction returning simple rule texts.

        This method favors recall and returns rules wrapped as
        `ManufacturingRule` objects with conservative default metadata.
        """

        if not self._is_high_value_chunk(text_chunk):
            enhanced_logger.debug("Skipping low-value chunk (raw)", chunk_preview=text_chunk[:50])
            return []

        try:
            if not self._respect_tpd_limit():
                return []

            chunk_lower = text_chunk.lower()
            detected_keywords: List[str] = []
            for _, keywords in self.manufacturing_keywords.items():
                detected_keywords.extend([kw for kw in keywords if kw in chunk_lower])

            rag_context_str = ""
            if rag_context:
                rag_context_str = "\n".join(
                    [f"- {ctx.get('text', '')[:100]}..." for ctx in rag_context[:3]]
                )

            self._sleep_for_throttle()
            raw_list: RawRuleList = self.bulk_extraction_chain.invoke({
                'text_chunk': text_chunk,
                'format_instructions': self.raw_rule_list_parser.get_format_instructions(),
            })

            if self.config.api_request_delay:
                time.sleep(self.config.api_request_delay)

            wrapped: List[ManufacturingRule] = []
            for item in raw_list.rules:
                text = item.text.strip()
                if not text:
                    continue
                try:
                    # Canonicalize raw rule text for consistent downstream merging
                    text_clean = self._canonicalize_rule_text(text)
                    rule = ManufacturingRule(
                        rule_text=text_clean[:500],
                        rule_category=ManufacturingCategory.GENERAL,
                        rule_type=RuleType.GENERAL,
                        primary_feature="",
                        secondary_feature="",
                        primary_object="",
                        secondary_object="",
                        operator="",
                        value=None,
                        unit="",
                        tolerance=None,
                        confidence_score=float(getattr(item, 'confidence_score', 0.6) or 0.6),
                        confidence_level=ConfidenceLevel.MEDIUM,
                        correctness_tag=CorrectnessTag.NEEDS_REVIEW,
                        manufacturing_relevance=0.5,
                        source_document="",
                        document_section="",
                        extraction_method="raw_bulk",
                    )
                    rule.readability_score = flesch_reading_ease(text_clean)
                    rule.complexity_score = len(detected_keywords) / len(text_clean.split()) if text_clean.split() else 0
                    wrapped.append(rule)
                except Exception as e:
                    enhanced_logger.warning("Failed to wrap raw rule into ManufacturingRule", error=str(e), rule_text=text[:200])

            return wrapped

        except Exception as e:
            self._update_tpd_from_error(e)
            if _retry and self._ensure_llm_available(e):
                return self.extract_raw_rules_from_chunk(text_chunk, document_context, rag_context, _retry=False)
            enhanced_logger.error("Raw rule extraction failed", chunk_preview=text_chunk[:100], error=str(e))
            return []
    
    async def extract_rules_parallel(self, text: str, filename: str = "") -> Dict[str, Any]:
        """Extract rules using parallel processing for production speed."""
        
        start_time = datetime.utcnow()
        token_usage = {'input_tokens': 0, 'output_tokens': 0}
        
        try:
            # Semantic chunking only
            chunks = self.semantic_chunk_text(text)
            enhanced_logger.info("Document chunked", 
                               chunk_count=len(chunks),
                               total_tokens=sum(c['token_count'] for c in chunks))
            
            # Extract rules from all chunks - NO POST-PROCESSING
            all_rules: List[Dict[str, Any]] = []

            for idx, chunk_data in enumerate(chunks, 1):
                chunk_text = chunk_data['text']

                enhanced_logger.info("Processing chunk", chunk=idx, total=len(chunks))

                if not self._respect_tpd_limit():
                    enhanced_logger.warning("TPD window active, stopping extraction")
                    break

                chunk_rules, _ = self.extract_rules_from_chunk(chunk_text, None, None)
                all_rules.extend(chunk_rules)

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Create output structure
            output = {
                'source_pdf': filename,
                'rule_count': len(all_rules),
                'rules': all_rules,
                'processing_time': processing_time,
                'chunks_processed': len(chunks)
            }
            
            # Save to JSON file
            output_dir = Path('output')
            output_dir.mkdir(exist_ok=True)
            
            pdf_name = Path(filename).stem if filename else 'untitled'
            output_file = output_dir / f"{pdf_name}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            enhanced_logger.info("Rule extraction completed",
                               rules_count=len(all_rules),
                               processing_time=processing_time,
                               output_file=str(output_file))
            
            return output
            
        except Exception as e:
            enhanced_logger.error("Rule extraction failed", error=str(e))
            return {
                'source_pdf': filename,
                'rule_count': 0,
                'rules': [],
                'processing_time': 0,
                'chunks_processed': 0,
                'error': str(e)
            }
    
    def _post_process_rules(
        self,
        rules: List[ManufacturingRule],
    ) -> Tuple[List[ManufacturingRule], Dict[str, Any]]:
        """Post-process rules with deduplication and quality enhancement.

        Returns both the final rule list and a small diagnostics dictionary
        describing how many rules survived each stage. This is surfaced back
        to callers for analytics/debugging.
        """

        stats: Dict[str, Any] = {
            'raw_rules_before_postprocessing': len(rules),
            'rules_after_deduplication': 0,
            'rules_after_quality_filter': 0,
            'rules_after_clustering': 0,
            'rules_before_cap': 0,
            'max_rules_cap': int(self.config.max_rules_per_document),
            'hit_rule_cap': False,
        }

        if not rules:
            return rules, stats

        # Step 1: Semantic deduplication
        unique_rules = self._deduplicate_semantic(rules)
        stats['rules_after_deduplication'] = len(unique_rules)

        # Step 2: Quality filtering (relaxed or strict based on mode)
        if getattr(self, "_recall_mode", False):
            quality_filtered = unique_rules  # defer filtering; keep recall high
        else:
            quality_filtered = [
                rule
                for rule in unique_rules
                if (
                    rule.confidence_score >= self.config.min_confidence_threshold
                    and rule.manufacturing_relevance
                    >= self.config.min_manufacturing_relevance
                )
            ]
        stats['rules_after_quality_filter'] = len(quality_filtered)

        # Step 3: Log escalation cases (based on unique, pre-filter rules)
        self._log_escalation_cases(unique_rules)

        # Step 4: Clustering for similar rules
        clustered_rules = quality_filtered
        if self.config.enable_rule_clustering and len(quality_filtered) > 5:
            clustered_rules = self._cluster_similar_rules(quality_filtered)
        stats['rules_after_clustering'] = len(clustered_rules)

        # Step 5: Sort by confidence and enforce document-level cap
        clustered_rules.sort(key=lambda x: x.confidence_score, reverse=True)
        stats['rules_before_cap'] = len(clustered_rules)
        stats['hit_rule_cap'] = bool(len(clustered_rules) > int(self.config.max_rules_per_document))
        final_rules = clustered_rules[: self.config.max_rules_per_document]

        return final_rules, stats
    
    def _heuristic_extract_from_chunk(self, text_chunk: str, document_context: DocumentContext) -> List[ManufacturingRule]:
        """A cheap, local heuristic extractor that identifies candidate rule sentences.

        This is used when high-recall is desired but the LLM is unavailable or
        when the user enables the local heuristic mode. It favors recall and
        returns conservative, low-confidence rule candidates.
        """

        candidates: List[ManufacturingRule] = []
        sentences = re.split(r'(?<=[.!?])\s+', text_chunk)
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue

            lower = s_clean.lower()
            # Heuristic triggers: must/shall, numeric values, measurement units, high-priority keywords
            trigger = False
            if any(kw in lower for kw in self.manufacturing_keywords['high_priority']):
                trigger = True
            if re.search(r'\b(\d+\.?\d*|\d*\.?\d+)\b', s_clean):
                trigger = True
            if any(unit in lower for unit in ['mm', 'cm', 'inch', 'inches', 'kg', 'g']):
                trigger = True
            if 'shall' in lower or 'must' in lower:
                trigger = True

            if not trigger:
                continue

            try:
                rule = ManufacturingRule(
                    rule_text=s_clean[:500],
                    rule_category=ManufacturingCategory.GENERAL,
                    rule_type=RuleType.GENERAL,
                    primary_feature="",
                    secondary_feature="",
                    primary_object="",
                    secondary_object="",
                    operator="",
                    value=None,
                    unit="",
                    tolerance=None,
                    confidence_score=0.45,
                    confidence_level=ConfidenceLevel.LOW,
                    correctness_tag=CorrectnessTag.NEEDS_REVIEW,
                    manufacturing_relevance=0.45,
                    source_document="",
                    document_section="",
                    extraction_method="heuristic_local",
                )
                rule.readability_score = flesch_reading_ease(s_clean)
                rule.complexity_score = len([kw for kw in self.manufacturing_keywords['high_priority'] if kw in lower])
                candidates.append(rule)
            except Exception as e:
                enhanced_logger.warning("Heuristic rule wrapping failed", error=str(e), text_preview=s_clean[:80])

        return candidates

    def _deduplicate_semantic(self, rules: List[ManufacturingRule]) -> List[ManufacturingRule]:
        """Advanced semantic deduplication using text similarity."""
        
        if len(rules) <= 1:
            return rules
        
        # Extract rule texts for similarity comparison
        rule_texts = [rule.rule_text for rule in rules]
        
        try:
            # Use TF-IDF for similarity calculation
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(rule_texts)
            similarity_matrix = (tfidf_matrix * tfidf_matrix.T).toarray()
            
            # Identify duplicates (similarity threshold depends on mode).
            # In recall mode we dedupe less aggressively to avoid accidentally
            # merging distinct rules that share similar phrasing.
            similarity_threshold = 0.9 if getattr(self, "_recall_mode", False) else 0.8
            unique_indices = []
            for i, rule in enumerate(rules):
                is_duplicate = False
                for j in unique_indices:
                    if similarity_matrix[i][j] > similarity_threshold:
                        # Keep the rule with higher confidence
                        if rule.confidence_score > rules[j].confidence_score:
                            unique_indices.remove(j)
                            unique_indices.append(i)
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_indices.append(i)
            
            return [rules[i] for i in unique_indices]
            
        except Exception as e:
            enhanced_logger.warning("Semantic deduplication failed", error=str(e))
            # Fallback to simple text-based deduplication
            seen_texts = set()
            unique_rules = []
            for rule in rules:
                normalized_text = re.sub(r'\W+', '', rule.rule_text.lower())
                if normalized_text not in seen_texts:
                    seen_texts.add(normalized_text)
                    unique_rules.append(rule)
            return unique_rules
    
    def _cluster_similar_rules(self, rules: List[ManufacturingRule]) -> List[ManufacturingRule]:
        """Cluster similar rules and merge if appropriate."""
        
        try:
            rule_texts = [rule.rule_text for rule in rules]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(rule_texts)
            
            # Use KMeans for clustering
            n_clusters = min(5, len(rules) // 3)  # Adaptive cluster count
            if n_clusters < 2:
                return rules
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(tfidf_matrix.toarray())
            
            # For each cluster, keep the highest confidence rule
            clustered_rules = []
            for cluster_id in range(n_clusters):
                cluster_rules = [rules[i] for i, c in enumerate(clusters) if c == cluster_id]
                if cluster_rules:
                    best_rule = max(cluster_rules, key=lambda x: x.confidence_score)
                    clustered_rules.append(best_rule)
            
            return clustered_rules
            
        except Exception as e:
            enhanced_logger.warning("Rule clustering failed", error=str(e))
            return rules
    
    def _log_escalation_cases(self, rules: List[ManufacturingRule]):
        """Log rules that require escalation for review."""
        
        escalation_rules = [
            rule for rule in rules 
            if rule.correctness_tag in [CorrectnessTag.OUT_OF_SCOPE, CorrectnessTag.LOW_CONFIDENCE]
        ]
        
        if escalation_rules:
            enhanced_logger.warning("Rules requiring escalation detected",
                                  escalation_count=len(escalation_rules),
                                  total_rules=len(rules))
            
            for rule in escalation_rules:
                enhanced_logger.info("Escalation case",
                                   rule_text=rule.rule_text[:100],
                                   correctness_tag=rule.correctness_tag.value,
                                   confidence_score=rule.confidence_score,
                                   manufacturing_relevance=rule.manufacturing_relevance,
                                   source_document=rule.source_document)
    
    def _is_high_value_chunk(self, text_chunk: str) -> bool:
        """Determine if a text chunk contains high-value manufacturing content."""
        
        chunk_lower = text_chunk.lower()
        
        # Count high-priority manufacturing keywords
        high_priority_count = sum(1 for kw in self.manufacturing_keywords['high_priority'] 
                                if kw in chunk_lower)
        
        # Count manufacturing process keywords
        manufacturing_count = sum(1 for kw in self.manufacturing_keywords['manufacturing'] 
                                if kw in chunk_lower)
        
        # Check for numeric values (indicating specifications)
        has_numbers = bool(re.search(r'\d+', text_chunk))
        
        # Modal requirements often indicate actionable rules without numbers
        has_modal_requirement = any(m in chunk_lower for m in [' shall ', ' must ', ' should '])
        
        # Calculate manufacturing density
        total_words = len(text_chunk.split())
        manufacturing_density = (high_priority_count + manufacturing_count) / total_words if total_words > 0 else 0
        
        # In recall mode, accept nearly all non-empty chunks to preserve coverage
        if getattr(self, "_recall_mode", False):
            return len(text_chunk.strip()) > 10

        # Default relaxed logic: accept almost anything with manufacturing cues
        is_high_value = (
            manufacturing_density >= 0.005 or  # ultra-low threshold
            has_numbers or  # any numbers
            has_modal_requirement or  # modal verbs
            high_priority_count > 0 or  # ANY high priority keyword
            manufacturing_count > 0  # ANY manufacturing keyword
        )

        return is_high_value
    
    def _is_rule_quality_acceptable(self, rule: ManufacturingRule) -> bool:
        """Check if extracted rule meets quality standards."""
        # Recall mode: keep liberal; rely on downstream dedupe instead of strict gating
        if getattr(self, "_recall_mode", False):
            if rule.confidence_score < max(0.05, self.config.min_confidence_threshold):
                return False
            if rule.manufacturing_relevance < max(0.05, self.config.min_manufacturing_relevance):
                return False
            return len(rule.rule_text.strip()) >= 8

        # Default precision-oriented checks
        min_confidence = max(self.config.min_confidence_threshold, 0.3)
        if rule.confidence_score < min_confidence:
            return False

        min_relevance = max(self.config.min_manufacturing_relevance, 0.15)
        if rule.manufacturing_relevance < min_relevance:
            return False

        rule_text_lower = rule.rule_text.lower()
        has_specific_terms = any(kw in rule_text_lower for kw in self.manufacturing_keywords['high_priority'])
        has_numbers = bool(re.search(r'\d+', rule.rule_text))
        has_modal_requirement = any(m in rule_text_lower for m in [' shall ', ' must ', ' should '])

        if not (has_specific_terms or has_numbers or has_modal_requirement):
            return False

        if len(rule.rule_text.strip()) < 15:
            return False

        return True
    
    def _enhance_rule_quality(self, rule: ManufacturingRule, original_chunk: str, 
                            document_context: DocumentContext) -> ManufacturingRule:
        """Attempt to enhance rule quality using additional context."""
        
        try:
            if not self._respect_tpd_limit():
                return rule
            # Prepare enhancement context
            similar_rules_str = ""
            if self.vector_manager:
                similar = self.vector_manager.similarity_search(
                    rule.rule_text, top_k=2, score_threshold=0.6
                )
                if similar:
                    similar_rules_str = "\n".join([s['text'][:100] for s in similar])
            
            # Run enhancement chain
            self._sleep_for_throttle()
            enhanced_rule = self.enhancement_chain.invoke({
                'original_rule': rule.dict(),
                'document_context': document_context.dict(),
                'similar_rules': similar_rules_str,
                'format_instructions': self.rule_parser.get_format_instructions()
            })

            if self.config.api_request_delay:
                time.sleep(self.config.api_request_delay)
            
            # Preserve original metadata but update core fields
            enhanced_rule.source_document = rule.source_document
            enhanced_rule.extracted_at = rule.extracted_at
            enhanced_rule.extraction_method = f"enhanced_{rule.extraction_method}"
            
            enhanced_logger.debug("Rule enhancement attempted",
                                original_confidence=rule.confidence_score,
                                enhanced_confidence=enhanced_rule.confidence_score)
            
            return enhanced_rule
            
        except Exception as e:
            self._update_tpd_from_error(e)
            enhanced_logger.warning("Rule enhancement failed", error=str(e))
            return rule
    
    def process_document(self, document_path: str) -> RuleExtractionResult:
        """Process a single document and extract rules."""
        
        filename = document_path.split('/')[-1]
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        async def _process():
            from pathlib import Path
            payload = await self.loader.load(Path(document_path))
            text = payload.text
            res = await self.extract_rules_parallel(text, filename)
            return res, text

        result, text = loop.run_until_complete(_process())
        
        # Add to vector database if available
        if self.vector_manager and result.rules:
            chunks = self.semantic_chunk_text(text)
            metadata = {'source_file': filename, 'rule_count': len(result.rules)}
            self.vector_manager.add_texts(
                [chunk['text'] for chunk in chunks],
                [metadata] * len(chunks)
            )
        
        return result
    
    def validate_against_hcl_dataset(self, hcl_csv_path: str) -> Dict[str, float]:
        """Validate extraction accuracy against HCL classification dataset."""
        
        try:
            # Load HCL dataset
            df = pd.read_csv(hcl_csv_path)
            
            validation_results = {
                'total_samples': len(df),
                'correctly_classified': 0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0
            }
            
            # Process each rule text
            for idx, row in df.iterrows():
                rule_text = row['rule_text']
                expected_label = row['classification_label']
                
                # Extract rule using our engine (sync wrapper around async)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                result = loop.run_until_complete(
                    self.extract_rules_parallel(rule_text, f"hcl_sample_{idx}")
                )

                if result.rules:
                    # Use the highest confidence rule for comparison
                    best_rule = max(result.rules, key=lambda x: x.confidence_score)
                    
                    # Simple classification: 0 = general, 1 = specific manufacturing
                    predicted_label = 1 if best_rule.confidence_score > 0.7 else 0
                    
                    if predicted_label == expected_label:
                        validation_results['correctly_classified'] += 1
            
            # Calculate metrics
            accuracy = validation_results['correctly_classified'] / validation_results['total_samples']
            validation_results['accuracy'] = accuracy
            
            enhanced_logger.info("HCL validation completed",
                               accuracy=accuracy,
                               total_samples=validation_results['total_samples'])
            
            return validation_results
            
        except Exception as e:
            enhanced_logger.error("HCL validation failed", error=str(e))
            return {'error': str(e)}

    def export_results(self, results: List[RuleExtractionResult], 
                      output_format: str = "excel") -> str:
        """Export extraction results in various formats."""
        
        # Flatten all rules
        all_rules = []
        for result in results:
            all_rules.extend(result.rules)
        
        # Convert to DataFrame
        rules_data = []
        for rule in all_rules:
            rules_data.append({
                'rule_text': rule.rule_text,
                'classification_label': 1 if rule.confidence_score > 0.7 else 0,
                'confidence_score': rule.confidence_score,
                'rule_category': rule.rule_category.value,
                'rule_type': rule.rule_type.value,
                'primary_feature': rule.primary_feature,
                'operator': rule.operator,
                'value': rule.value,
                'unit': rule.unit,
                'source_document': rule.source_document,
                'extraction_method': rule.extraction_method,
                'manufacturing_relevance': rule.manufacturing_relevance
            })
        
        df = pd.DataFrame(rules_data)
        
        # Export based on format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == "excel":
            output_path = f"enhanced_rules_export_{timestamp}.xlsx"
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Manufacturing_Rules', index=False)
                
                # Add summary sheet
                summary_df = pd.DataFrame({
                    'Metric': ['Total Rules', 'Avg Confidence', 'High Confidence Rules', 'Manufacturing Categories'],
                    'Value': [
                        len(df),
                        df['confidence_score'].mean(),
                        len(df[df['confidence_score'] > 0.8]),
                        df['rule_category'].nunique()
                    ]
                })
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        elif output_format == "csv":
            output_path = f"enhanced_rules_export_{timestamp}.csv"
            df.to_csv(output_path, index=False)
        
        else:  # JSON
            output_path = f"enhanced_rules_export_{timestamp}.json"
            df.to_json(output_path, orient='records', indent=2)
        
        enhanced_logger.info("Results exported", 
                           output_path=output_path,
                           rule_count=len(df))
        
        return output_path

    def _result_to_dict(
        self,
        result: Dict[str, Any],
        *,
        fallback_filename: str = "ad_hoc.txt",
    ) -> Dict[str, Any]:
        # result is already a dict from extract_rules_parallel
        # Just return it as-is since it's already in the correct format
        return result