"""
Three-tier adaptive bucket and domain classifier for DFM rules.

Uses a hybrid tiered approach (Regex/Keywords -> Embeddings -> LLM Fallback)
to classify both structural buckets and manufacturing domains with optimized token cost.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, TYPE_CHECKING

import numpy as np

from dfm_rule_pipeline.taxonomy.bucket_registry import (
    BUCKET_REGISTRY,
    get_all_exemplars,
)
from dfm_rule_pipeline.taxonomy.schema_registry import SchemaRegistry

if TYPE_CHECKING:
    from core_v2.embeddings import EmbeddingManager

logger = logging.getLogger("taxonomy.classifier")


@dataclass
class ClassificationResult:
    """Result of bucket + domain classification."""
    bucket: str
    domain: str
    confidence: str  # "high", "medium", "low"
    method: str      # "regex", "embedding", "llm" or "default"


# ---------------------------------------------------------------
# Tier 1: Regex patterns for buckets — only fire on unambiguous matches
# ---------------------------------------------------------------
_REGEX_PATTERNS: List[tuple[str, re.Pattern]] = [
    # DistanceRule: "distance between X and Y"
    ("DistanceRule", re.compile(
        r"(?i)\b(?:distance|clearance|spacing)\s+between\b"
    )),
    # ConditionalValidation: "for <feature> with ...", "if ...", "when ...", "where ..."
    ("ConditionalValidation", re.compile(
        r"(?i)\b(?:for|when|if|where|given)\b.+?\b(?:with|is|having|equal|greater|less|between|should|must)\b"
    )),
    # RangeValidation: "between <number> and <number>" (only for simple unconditional range rules)
    ("RangeValidation", re.compile(
        r"(?i)\bbetween\s+[\d.]+\s+and\s+[\d.]+"
    )),
    # SetMembership: "from the following list"
    ("SetMembership", re.compile(
        r"(?i)\b(?:from the following list|one of the following|any of the following)\b"
    )),
    # AdditionalInfoValidation: "additionally" or "also check"
    ("AdditionalInfoValidation", re.compile(
        r"(?i)\b(?:additionally|also\s+check|also\s+report)\b"
    )),
]

# ---------------------------------------------------------------
# Domain keywords for keyword scoring
# ---------------------------------------------------------------
_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "SheetMetal": [
        "sheet metal", "sheetmetal", "sheet thickness", "bend", "flange",
        "hem", "bridge", "cutout", "louver", "spoon", "gusset", "emboss",
        "stamp", "dowel", "dimple", "card guide",
    ],
    "Sheetmetal Forming": [
        "sheetmetal forming", "sheet metal forming", "smform", "nominal thickness",
    ],
    "Drilling": [
        "drill", "drilling", "hole", "thread", "blind hole", "through hole",
        "counterbore", "countersink", "tap", "bore", "hole diameter", "hole depth",
    ],
    "Milling": [
        "mill", "milling", "pocket", "milled pocket", "chamfer", "slot",
    ],
    "Injection Molding": [
        "injection", "molding", "moulding", "mold", "draft angle",
        "pin", "boss", "rib", "lip", "wall thickness", "nominal wall thickness",
        "rib height", "rib thickness", "rib radius",
    ],
    "Die Casting": [
        "die cast", "casting", "mold face", "mold wall",
    ],
    "Assembly": [
        "assembly", "fastener", "bolt", "nut", "washer", "component",
        "engaged", "interference",
    ],
    "Additive Manufacturing": [
        "additive", "3d print", "am face", "print size", "layer",
    ],
    "Turning": [
        "turning", "lathe", "turn corner", "groove", "bored hole",
        "turn profile",
    ],
    "Tubing": [
        "tubing", "tube", "pipe", "bend radius",
    ],
    "General": [
        "flatness", "parallelism", "perpendicularity", "runout",
        "concentricity", "gd&t", "tolerance", "surface profile", "line profile",
    ],
}

# ---------------------------------------------------------------
# Domain exemplars for embedding-based similarity lookup
# ---------------------------------------------------------------
DOMAIN_EXEMPLARS = {
    "SheetMetal": [
        "minimum flange height should be 3 times thickness",
        "distance between bridge features in sheetmetal parts",
        "hem opening radius must not exceed 2.0",
        "closed hem length and rolled hem support"
    ],
    "Sheetmetal Forming": [
        "nominal thickness of the sheet metal forming process",
        "forming tool relief and draw radius requirements",
        "simple hole depth and taper angle for smform segment"
    ],
    "Die Casting": [
        "draft angle for die cast mold features",
        "minimum wall thickness for casting aluminum alloy",
        "mold face classification type undercut or fillet"
    ],
    "Injection Molding": [
        "injection molding nominal wall thickness requirements",
        "mold wall classification and pin height draft angle",
        "lip min thickness and rib radius at bot in molded part"
    ],
    "Drilling": [
        "drill depth for blind threaded tapped holes",
        "hole diameter and exit angle for drilled hole segments",
        "counterbore depth and countersink sunk angle"
    ],
    "Milling": [
        "pocket side face angle and open pocket depth limit",
        "milled pocket bottom fillet radius and chamfer width",
        "milling pocket side face angle and pocket depth"
    ],
    "Assembly": [
        "fastener clearance and bolt thread engagement length",
        "washer present check on bolt washer nut assembly",
        "clearnace hole depth shank length nut wrench flat diameter"
    ],
    "Additive Manufacturing": [
        "am print size length width height envelope limits",
        "support structures for additive manufacturing wall thickness",
        "am face min thickness and gap requirements"
    ],
    "Turning": [
        "lathe turn profile segment diameter maximum",
        "turned shaft corner radius and groove top width",
        "turned profile segment and groove corner radius"
    ],
    "Tubing": [
        "tube thickness and bend outer diameter overlap",
        "straight tubing segment minimum length support",
        "uniform bend radius support for straight pipe tubing"
    ],
    "General": [
        "flatness tolerance and perpendicularity gd&t check",
        "partbody material name specification and thread unit",
        "part body tight box length tight box width volume"
    ]
}


class BucketClassifier:
    """
    Hybrid classifier for DFM rule buckets and manufacturing domains.
    """

    def __init__(
        self,
        schema_registry: SchemaRegistry,
        embedder: Optional[EmbeddingManager] = None,
        similarity_threshold: float = 0.45,
    ):
        self._registry = schema_registry
        self._embedder = embedder
        self._threshold = similarity_threshold
        
        # Pre-embed bucket exemplars
        self._exemplar_labels: List[str] = []
        self._exemplar_matrix: Optional[np.ndarray] = None
        
        # Pre-embed domain exemplars
        self._domain_labels: List[str] = []
        self._domain_matrix: Optional[np.ndarray] = None
        
        if embedder is not None:
            self._build_exemplar_index()
            self._build_domain_index()

    def _build_exemplar_index(self) -> None:
        """Embed all bucket exemplar sentences and store for cosine lookup."""
        all_exemplars = get_all_exemplars()
        all_sentences: List[str] = []
        labels: List[str] = []
        
        for bucket_id, sentences in all_exemplars.items():
            for sentence in sentences:
                all_sentences.append(sentence)
                labels.append(bucket_id)
        
        if not all_sentences:
            return
        
        embeddings = self._embedder.embed(all_sentences)
        self._exemplar_matrix = np.array(embeddings)
        self._exemplar_labels = labels
        
        logger.info(
            f"Built bucket exemplar index: {len(all_sentences)} sentences "
            f"across {len(all_exemplars)} buckets"
        )

    def _build_domain_index(self) -> None:
        """Embed all domain exemplar sentences and store for cosine lookup."""
        all_sentences: List[str] = []
        labels: List[str] = []
        
        for domain, sentences in DOMAIN_EXEMPLARS.items():
            for sentence in sentences:
                all_sentences.append(sentence)
                labels.append(domain)
        
        if not all_sentences:
            return
        
        embeddings = self._embedder.embed(all_sentences)
        self._domain_matrix = np.array(embeddings)
        self._domain_labels = labels
        
        logger.info(
            f"Built domain exemplar index: {len(all_sentences)} sentences "
            f"across {len(DOMAIN_EXEMPLARS)} domains"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(
        self,
        rule_text: str,
        explicit_domain: Optional[str] = None,
        llm_client=None,
    ) -> ClassificationResult:
        """
        Classify a rule's bucket type and domain.
        
        Runs fast local classifiers (Regex, Keyword scoring, and Embeddings)
        to predict the domain and bucket, then double-verifies the predictions
        using the LLM when active.
        """
        # 1. Compute Fast Candidate predictions
        fast_domain = self._detect_domain_fast(rule_text, explicit_domain)
        
        # Fast bucket prediction
        fast_bucket = self._regex_classify(rule_text)
        fast_bucket_method = "regex"
        
        if not fast_bucket:
            if self._exemplar_matrix is not None:
                emb_bucket, score = self._embedding_classify(rule_text)
                if emb_bucket and score >= self._threshold:
                    fast_bucket = emb_bucket
                    fast_bucket_method = "embedding"
            
        if not fast_bucket:
            fast_bucket = "SimpleValidation"
            fast_bucket_method = "default"

        # 2. Double-Verify using LLM (if client is provided)
        if llm_client is not None:
            verified = self._llm_double_verify(rule_text, fast_domain, fast_bucket, llm_client)
            if verified:
                v_domain, v_bucket = verified
                
                # Reconcile domain and bucket against Ground Truth Schema & Regex Guards
                final_domain = self._reconcile_domain(rule_text, v_domain, fast_domain, explicit_domain)
                final_bucket = self._reconcile_bucket(rule_text, v_bucket, fast_bucket)
                
                is_match = (final_domain == fast_domain and final_bucket == fast_bucket)
                method = "double_verified" if is_match else "double_verified_reconciled"
                
                logger.info(
                    f"Double verification 2-Pass Result: domain={final_domain} (llm={v_domain}, fast={fast_domain}), "
                    f"bucket={final_bucket} (llm={v_bucket}, fast={fast_bucket}) -> method={method}"
                )
                return ClassificationResult(
                    bucket=final_bucket,
                    domain=final_domain,
                    confidence="high",
                    method=method,
                )
        
        # 3. Offline/Fallback return using fast results
        final_domain = self._reconcile_domain(rule_text, None, fast_domain, explicit_domain)
        final_bucket = self._reconcile_bucket(rule_text, None, fast_bucket)
        
        confidence = "medium"
        if fast_bucket_method == "regex":
            confidence = "high"
        return ClassificationResult(
            bucket=final_bucket,
            domain=final_domain,
            confidence=confidence,
            method=f"fast_{fast_bucket_method}",
        )

    def _reconcile_domain(
        self,
        rule_text: str,
        llm_domain: Optional[str],
        fast_domain: str,
        explicit_domain: Optional[str] = None
    ) -> str:
        """Reconcile LLM domain prediction with deterministic ground-truth schema feature ownership."""
        if explicit_domain:
            canonical = self._registry.get_canonical_domain(explicit_domain)
            if canonical:
                return canonical

        rule_lower = rule_text.lower()

        # Step 1: Check for explicit CAD feature ownership in schema_registry
        for domain in self._registry.list_domains():
            features = self._registry.get_features(domain)
            for feat_name in features.keys():
                if feat_name in {"PartBody", "PartFace", "PartEdge", "PMI", "Thread"}:
                    continue
                pattern = r"\b" + re.escape(feat_name.lower()) + r"s?\b"
                if re.search(pattern, rule_lower):
                    # Ground truth feature match! If LLM domain doesn't contain this feature, override.
                    llm_feats = self._registry.get_features(llm_domain) if llm_domain else {}
                    if not llm_domain or feat_name not in llm_feats:
                        logger.info(f"Domain reconciled from '{llm_domain}' -> '{domain}' via schema feature ownership of '{feat_name}'")
                        return domain
                    return llm_domain

        # Step 2: Use LLM domain if available and valid
        if llm_domain:
            canonical = self._registry.get_canonical_domain(llm_domain)
            if canonical:
                return canonical

        # Step 3: Fall back to fast_domain
        return fast_domain

    def _reconcile_bucket(self, rule_text: str, llm_bucket: Optional[str], fast_bucket: str) -> str:
        """Reconcile LLM bucket prediction."""
        if llm_bucket and llm_bucket in BUCKET_REGISTRY:
            return llm_bucket

        return fast_bucket

    def _detect_domain_fast(
        self,
        rule_text: str,
        explicit_domain: Optional[str] = None,
    ) -> str:
        """Runs fast local domain classifiers (explicit, keyword scoring, embedding)."""
        # Tier 1: Explicit Override / Direct Matches
        if explicit_domain:
            canonical = self._registry.get_canonical_domain(explicit_domain)
            if canonical:
                return canonical

        rule_lower = rule_text.lower()
        scores: Dict[str, float] = {}

        # 1. Feature Name Schema Matching (Weight = 10.0)
        # Check every domain's features directly from schema_registry
        for domain in self._registry.list_domains():
            features = self._registry.get_features(domain)
            for feat_name in features.keys():
                # Skip universal cross-domain objects
                if feat_name in {"PartBody", "PartFace", "PartEdge", "PMI", "Thread"}:
                    continue
                
                # Check singular and plural feature name matches
                pattern = r"\b" + re.escape(feat_name.lower()) + r"s?\b"
                if re.search(pattern, rule_lower):
                    scores[domain] = scores.get(domain, 0.0) + 10.0

        # 2. Keyword Scoring (Weight = 1.0 to 2.0)
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            for kw in keywords:
                pattern = r"\b" + re.escape(kw.lower()) + r"\b"
                if re.search(pattern, rule_lower):
                    scores[domain] = scores.get(domain, 0.0) + float(len(kw.split()))
        
        # If one domain stands out strongly (e.g. score >= 2.0), return it
        if scores:
            best_domain = max(scores, key=scores.get)
            if scores[best_domain] >= 2.0 or len(scores) == 1:
                return best_domain

        # Tier 2: Embedding Similarity matching
        if self._domain_matrix is not None and self._embedder is not None:
            domain, score = self._embedding_domain_classify(rule_text)
            if domain and score >= self._threshold:
                return domain

        # Final default fallback
        if scores:
            best_domain = max(scores, key=scores.get)
            return best_domain

        return "General"

    def _llm_double_verify(
        self,
        rule_text: str,
        fast_domain: str,
        fast_bucket: str,
        llm_client
    ) -> Optional[tuple[str, str]]:
        """
        Verify the predicted domain and bucket classifications using a single LLM call.
        Returns (verified_domain, verified_bucket) or None on failure.
        """
        domains = self._registry.list_domains()
        domain_items = []
        for d in domains:
            feats = list(self._registry.get_features(d).keys())
            feats_str = ", ".join(feats) if feats else "ModuleParams"
            domain_items.append(f"- {d} (Features: {feats_str})")
        domain_list_str = "\n".join(domain_items)
        
        bucket_list = "\n".join(
            f"- {bid}: {bdef.description}"
            for bid, bdef in BUCKET_REGISTRY.items()
        )
        
        prompt = f"""You are a DFM taxonomy classifier. Your task is to double-verify the domain and bucket classifications for the following rule.
        
RULE TEXT: "{rule_text}"

CANDIDATE CLASSIFICATION (predicted by fast local classifier):
- Candidate Domain: "{fast_domain}"
- Candidate Bucket: "{fast_bucket}"

VALID CANONICAL DOMAINS:
{domain_list_str}

VALID BUCKETS AND DESCRIPTIONS:
{bucket_list}

Analyze the rule semantically. If the candidates are correct, verify them. If they are incorrect, select the correct canonical domain and bucket.

Output a JSON response. Do NOT wrap the response in markdown code blocks (e.g. do NOT use ```json ... ```). Return ONLY the raw JSON string starting with {{ and ending with }}:
{{
  "domain": "<verified canonical domain>",
  "bucket": "<verified bucket type>",
  "explanation": "<short explanation of your verification/correction>"
}}"""
        
        try:
            import json
            response = llm_client.call(prompt, json_mode=True)
            data = json.loads(response.strip())
            
            v_domain = data.get("domain", "").strip()
            v_bucket = data.get("bucket", "").strip()
            
            # Resolve to canonical domain name
            canonical_domain = self._registry.get_canonical_domain(v_domain)
            if not canonical_domain:
                canonical_domain = fast_domain  # Fallback to fast predicted domain if LLM returns invalid
                
            # Verify bucket is valid
            if v_bucket not in BUCKET_REGISTRY:
                v_bucket = fast_bucket  # Fallback to fast predicted bucket if LLM returns invalid
                
            return canonical_domain, v_bucket
            
        except Exception as e:
            logger.warning(f"LLM double-verification failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Tier 1: Regex
    # ------------------------------------------------------------------

    def _regex_classify(self, rule_text: str) -> Optional[str]:
        """Run high-precision regex patterns. Returns bucket_id or None."""
        matches = []
        for bucket_id, pattern in _REGEX_PATTERNS:
            if pattern.search(rule_text):
                matches.append(bucket_id)
        
        # Only return if exactly one pattern matched (unambiguous)
        if len(matches) == 1:
            return matches[0]
        
        # Exception: DistanceRule takes priority over RangeValidation
        if "DistanceRule" in matches and "RangeValidation" in matches:
            return "DistanceRule"
        
        return None

    # ------------------------------------------------------------------
    # Tier 2: Embedding similarity
    # ------------------------------------------------------------------

    def _embedding_classify(self, rule_text: str) -> tuple[Optional[str], float]:
        """Embed rule text and find most similar exemplar. Returns (bucket_id, score)."""
        if self._exemplar_matrix is None or self._embedder is None:
            return None, 0.0
        
        rule_embedding = np.array(self._embedder.embed([rule_text])[0])
        
        rule_norm = rule_embedding / (np.linalg.norm(rule_embedding) + 1e-9)
        exemplar_norms = self._exemplar_matrix / (
            np.linalg.norm(self._exemplar_matrix, axis=1, keepdims=True) + 1e-9
        )
        
        similarities = exemplar_norms @ rule_norm
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        best_bucket = self._exemplar_labels[best_idx]
        
        return best_bucket, best_score

    # ------------------------------------------------------------------
    # Tier 3: LLM fallback
    # ------------------------------------------------------------------

    def _llm_classify(self, rule_text: str, llm_client) -> Optional[str]:
        """Use a lightweight LLM call to classify the bucket type."""
        bucket_list = "\n".join(
            f"- {bid}: {bdef.description}"
            for bid, bdef in BUCKET_REGISTRY.items()
        )
        
        prompt = f"""Classify this manufacturing rule into exactly ONE bucket type.

BUCKET TYPES:
{bucket_list}

RULE: "{rule_text}"

Return JSON only: {{"bucket": "<bucket_id>"}}"""
        
        try:
            import json
            response = llm_client.call(prompt)
            data = json.loads(response)
            bucket = data.get("bucket", "")
            if bucket in BUCKET_REGISTRY:
                return bucket
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
        
        return None

    # ------------------------------------------------------------------
    # Domain detection (Upgraded to Hybrid)
    # ------------------------------------------------------------------

    def _detect_domain(
        self,
        rule_text: str,
        explicit_domain: Optional[str] = None,
        llm_client=None,
    ) -> str:
        """Detect the manufacturing domain using a 3-tier hybrid approach."""
        # Tier 1: Explicit Override / Direct Matches
        if explicit_domain:
            canonical = self._registry.get_canonical_domain(explicit_domain)
            if canonical:
                return canonical

        # Keyword Scoring (Tier 1 fallback)
        rule_lower = rule_text.lower()
        scores: Dict[str, int] = {}
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in rule_lower:
                    score += len(kw.split())
            if score > 0:
                scores[domain] = score
        
        # If one domain stands out strongly (e.g. score >= 2), return it instantly
        if scores:
            best_domain = max(scores, key=scores.get)
            if scores[best_domain] >= 2 or len(scores) == 1:
                return best_domain

        # Tier 2: Embedding Similarity matching
        if self._domain_matrix is not None and self._embedder is not None:
            domain, score = self._embedding_domain_classify(rule_text)
            if domain and score >= self._threshold:
                return domain

        # Tier 3: LLM Classification Fallback
        if llm_client is not None:
            domain = self._llm_domain_classify(rule_text, llm_client)
            if domain:
                return domain

        # Final default fallback
        if scores:
            best_domain = max(scores, key=scores.get)
            return best_domain

        return "General"

    def _embedding_domain_classify(self, rule_text: str) -> tuple[Optional[str], float]:
        """Embed rule text and find most similar domain. Returns (domain, score)."""
        if self._domain_matrix is None or self._embedder is None:
            return None, 0.0
        
        rule_embedding = np.array(self._embedder.embed([rule_text])[0])
        
        rule_norm = rule_embedding / (np.linalg.norm(rule_embedding) + 1e-9)
        domain_norms = self._domain_matrix / (
            np.linalg.norm(self._domain_matrix, axis=1, keepdims=True) + 1e-9
        )
        
        similarities = domain_norms @ rule_norm
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        best_domain = self._domain_labels[best_idx]
        
        return best_domain, best_score

    def _llm_domain_classify(self, rule_text: str, llm_client) -> Optional[str]:
        """Use a lightweight LLM call to classify the domain from canonical list."""
        domains = self._registry.list_domains()
        domain_list_str = "\n".join(f"- {d}" for d in domains)
        
        prompt = f"""Identify which SINGLE manufacturing domain this engineering rule belongs to.

DOMAINS:
{domain_list_str}

RULE: "{rule_text}"

Return JSON only: {{"domain": "<domain_name>"}}"""
        
        try:
            import json
            response = llm_client.call(prompt)
            data = json.loads(response)
            domain = data.get("domain", "")
            canonical = self._registry.get_canonical_domain(domain)
            if canonical:
                return canonical
        except Exception as e:
            logger.warning(f"LLM domain classification failed: {e}")
        
        return None
