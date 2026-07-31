"""
Schema Registry for DFM Taxonomy V3.

Loads domain/feature/attribute definitions from schema_registry.json
and provides validation and filtering utilities.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set


# The General domain contains cross-domain objects (PartBody, PartEdge, PMI,
# Thread, etc.) that apply universally across all manufacturing domains.
_GENERAL_DOMAIN = "General"


class SchemaRegistry:
    """
    Central registry for domain feature schemas.
    
    Loaded once at startup from schema_registry.json. Provides:
    - Domain alias resolution
    - ExpName path validation
    - Keyword-based schema filtering for selective prompting
    """

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "schema_registry.json"
        
        self._config_path = config_path
        
        with open(config_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        
        self._domains: Dict[str, dict] = raw.get("domains", {})
        
        # Build alias → canonical lookup
        self._alias_map: Dict[str, str] = {}
        for canonical, domain_def in self._domains.items():
            self._alias_map[canonical.lower()] = canonical
            for alias in domain_def.get("aliases", []):
                self._alias_map[alias.lower()] = canonical

    # ------------------------------------------------------------------
    # Domain resolution
    # ------------------------------------------------------------------

    def get_canonical_domain(self, raw: str) -> Optional[str]:
        """Resolve a raw domain string to its canonical name."""
        if not raw:
            return None
        return self._alias_map.get(raw.strip().lower())

    def list_domains(self) -> List[str]:
        """Return all canonical domain names."""
        return list(self._domains.keys())

    def is_valid_domain(self, domain: str) -> bool:
        """Check if a domain exists in the registry."""
        return domain in self._domains

    # ------------------------------------------------------------------
    # Feature / attribute access
    # ------------------------------------------------------------------

    def get_features(self, domain: str) -> Dict[str, List[str]]:
        """Get all features and their attributes for a domain.
        
        Automatically merges features from the General domain so that
        cross-domain objects (PartBody, PartEdge, PMI, etc.) are always
        available regardless of the target domain.
        """
        domain_def = self._domains.get(domain, {})
        features = dict(domain_def.get("features", {}))
        
        # Merge General domain features (cross-domain objects)
        if domain != _GENERAL_DOMAIN:
            general_def = self._domains.get(_GENERAL_DOMAIN, {})
            for feat_name, attrs in general_def.get("features", {}).items():
                if feat_name not in features:
                    features[feat_name] = attrs
        
        return features

    def get_module_params(self, domain: str) -> Dict[str, List[str]]:
        """Get module-level parameters for a domain.
        
        Merges General domain module_params as well.
        """
        domain_def = self._domains.get(domain, {})
        params = dict(domain_def.get("module_params", {}))
        
        # Merge General domain module params
        if domain != _GENERAL_DOMAIN:
            general_def = self._domains.get(_GENERAL_DOMAIN, {})
            for mp_name, mp_attrs in general_def.get("module_params", {}).items():
                if mp_name not in params:
                    params[mp_name] = mp_attrs
        
        return params

    def get_all_objects(self, domain: str) -> Set[str]:
        """Get the union of all feature names and module param keys for a domain."""
        features = self.get_features(domain)
        module_params = self.get_module_params(domain)
        return set(features.keys()) | set(module_params.keys())

    def get_attributes_for_object(self, domain: str, obj_name: str) -> Optional[List[str]]:
        """
        Get the attribute list for a specific object in a domain.
        Searches both features and module_params.
        Returns None if the object doesn't exist.
        """
        features = self.get_features(domain)
        if obj_name in features:
            return features[obj_name]
        
        module_params = self.get_module_params(domain)
        if obj_name in module_params:
            return module_params[obj_name]
        
        return None

    # ------------------------------------------------------------------
    # ExpName validation
    # ------------------------------------------------------------------

    def validate_exp_name(self, domain: str, exp_name: str, auto_register: bool = True) -> List[str]:
        """
        Validate an ExpName path against the domain schema.
        
        Handles patterns:
        - Direct:       Pocket.SideFaceAngle
        - Ratio:        Hole.TotalDepth/Hole.DiameterAtTop
        - Hierarchical: Fastener.FirstEngagedComp.Material
        
        Returns a list of error messages (empty if valid).
        """
        if not exp_name or exp_name.strip() == "":
            return []  # Placeholder — skip validation
        
        errors = []
        
        # Handle ratio expressions (A/B)
        if "/" in exp_name:
            parts = exp_name.split("/")
            for part in parts:
                part_errors = self._validate_single_path(domain, part.strip(), auto_register=auto_register)
                errors.extend(part_errors)
            return errors
        
        return self._validate_single_path(domain, exp_name, auto_register=auto_register)

    def _validate_single_path(self, domain: str, path: str, auto_register: bool = True) -> List[str]:
        """Validate a single dotted path like Pocket.SideFaceAngle."""
        errors = []
        parts = path.split(".", 1)
        
        if len(parts) < 2:
            # Single-word ExpName — might be a module-level reference
            return []
        
        root = parts[0]
        attr_path = parts[1]
        
        # Check if root object exists
        all_objects = self.get_all_objects(domain)
        if root not in all_objects:
            errors.append(
                f"Object '{root}' does not exist in domain '{domain}'. "
                f"Valid objects: {sorted(all_objects)}"
            )
            return errors
        
        # For hierarchical paths (Fastener.FirstEngagedComp.Material),
        # we only validate the root object exists since sub-object
        # paths are dynamic and context-dependent.
        if "." in attr_path:
            # Hierarchical — root exists, accept the rest
            return errors
        
        # Check if attribute exists for the root object
        attrs = self.get_attributes_for_object(domain, root)
        if attrs is not None and attr_path not in attrs:
            if auto_register:
                # Auto-register new attribute into schema_registry.json on disk
                registered = self.register_attribute(domain, root, attr_path)
                if registered:
                    errors.append(
                        f"NEW_ATTRIBUTE_REGISTERED: New attribute '{attr_path}' was auto-registered under '{root}' in '{domain}'."
                    )
                else:
                    errors.append(
                        f"Attribute '{attr_path}' does not exist for '{root}' in '{domain}'. "
                        f"Valid attributes: {sorted(attrs)}"
                    )
            else:
                errors.append(
                    f"Attribute '{attr_path}' does not exist for '{root}' in '{domain}'. "
                    f"Valid attributes: {sorted(attrs)}"
                )
        
        return errors

    def register_attribute(self, domain: str, root_object: str, attr_name: str) -> bool:
        """
        Dynamically registers a new attribute under a root object in a domain
        and persists the update to schema_registry.json on disk.
        
        Returns True if a new attribute was registered, False if already present.
        """
        if not attr_name or not root_object:
            return False
        
        target_domain = domain if domain in self._domains else _GENERAL_DOMAIN
        domain_def = self._domains.get(target_domain, {})
        
        # Check features
        features = domain_def.get("features", {})
        if root_object in features:
            if attr_name not in features[root_object]:
                features[root_object].append(attr_name)
                self._save_to_disk()
                return True
        
        # Check module_params
        module_params = domain_def.get("module_params", {})
        if root_object in module_params:
            if attr_name not in module_params[root_object]:
                module_params[root_object].append(attr_name)
                self._save_to_disk()
                return True

        # Check General domain cross-domain features
        general_def = self._domains.get(_GENERAL_DOMAIN, {})
        gen_features = general_def.get("features", {})
        if root_object in gen_features:
            if attr_name not in gen_features[root_object]:
                gen_features[root_object].append(attr_name)
                self._save_to_disk()
                return True

        return False

    def _save_to_disk(self) -> None:
        """Persists self._domains back to schema_registry.json on disk."""
        try:
            import logging
            log = logging.getLogger("taxonomy.schema_registry")
            data = {"domains": self._domains}
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            log.info(f"Persisted updated schema registry to {self._config_path}")
        except Exception as e:
            import logging
            logging.getLogger("taxonomy.schema_registry").error(f"Failed to save schema_registry.json: {e}")

    def validate_formula_refs(self, domain: str, formula: str) -> List[str]:
        """
        Extract and validate all schema path references from a formula value.
        E.g., '4.5*SheetMetal.Thickness' → validates SheetMetal.Thickness
        """
        refs = extract_schema_refs(formula)
        errors = []
        for ref in refs:
            ref_errors = self.validate_exp_name(domain, ref)
            errors.extend(ref_errors)
        return errors

    # ------------------------------------------------------------------
    # Keyword-based schema filtering (for selective prompting)
    # ------------------------------------------------------------------

    def filter_schema_for_rule(self, domain: str, rule_text: str) -> Dict[str, List[str]]:
        """
        Return only the features/attributes that keyword-match
        words in the rule text. Used by prompt_context.py to build
        minimal, targeted prompts.
        
        Always includes module_params for the domain.
        Falls back to top-5 features if no keyword matches found.
        """
        features = self.get_features(domain)
        module_params = self.get_module_params(domain)
        
        if not features:
            return {}
        
        # Tokenize rule text
        rule_words = set(re.findall(r'[a-zA-Z]+', rule_text.lower()))
        
        matched: Dict[str, List[str]] = {}
        
        for feature_name, attrs in features.items():
            feature_lower = feature_name.lower()
            # Check if any rule word matches the feature name
            # or if any rule word matches an attribute name
            attr_lowers = {a.lower() for a in attrs}
            
            if (feature_lower in rule_words or
                any(word in feature_lower for word in rule_words if len(word) > 3) or
                any(al in rule_words for al in attr_lowers)):
                matched[feature_name] = attrs
        
        # Always include module params
        for mp_name, mp_attrs in module_params.items():
            matched[f"Module:{mp_name}"] = mp_attrs
        
        # Fallback: if no feature matches, include top-5 features
        if not any(k for k in matched if not k.startswith("Module:")):
            for i, (fname, fattrs) in enumerate(features.items()):
                if i >= 5:
                    break
                matched[fname] = fattrs
        
        return matched

    def format_filtered_schema(self, filtered: Dict[str, List[str]]) -> str:
        """Format filtered schema dict into a readable string for prompts."""
        lines = []
        for name, attrs in filtered.items():
            if name.startswith("Module:"):
                display = name.replace("Module:", "Module Parameter: ")
            else:
                display = f"Object: {name}"
            lines.append(f"  {display}")
            lines.append(f"  Attributes: {', '.join(attrs)}")
            lines.append("")
        return "\n".join(lines)


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

# Regex to extract schema references like SheetMetal.Thickness from formulas
_SCHEMA_REF_PATTERN = re.compile(r'([A-Z][a-zA-Z]+(?:\.[A-Z][a-zA-Z]+)+)')


def extract_schema_refs(value: str) -> List[str]:
    """
    Extract all schema path references from a value string.
    E.g., '4.5*SheetMetal.Thickness' → ['SheetMetal.Thickness']
    E.g., 'Hole.Depth/Hole.Diameter' → ['Hole.Depth', 'Hole.Diameter']
    """
    if not value:
        return []
    return _SCHEMA_REF_PATTERN.findall(value)
