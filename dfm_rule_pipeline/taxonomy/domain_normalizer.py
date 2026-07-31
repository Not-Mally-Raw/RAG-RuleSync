"""
Domain normalizer for DFM rule pipelines.

This module provides utilities to normalize domain names and aliases
into a set of canonical domain strings.
"""
from typing import Dict, List, Optional

# Canonical domains
CANONICAL_DOMAINS = [
    "SheetMetal",
    "Sheetmetal Forming",
    "Die Casting",
    "Injection Molding",
    "Milling",
    "Drilling",
    "Assembly",
    "Additive Manufacturing",
    "Turning",
    "Tubing",
    "General"
]

DOMAIN_ALIASES: Dict[str, str] = {
    # Sheet Metal
    "sheet metal": "SheetMetal",
    "sm": "SheetMetal",
    "sheetmetal": "SheetMetal",
    
    # Injection Molding
    "injection molding": "Injection Molding",
    "injection moulding": "Injection Molding",
    "im": "Injection Molding",
    
    # Sheetmetal Forming
    "sheetmetal forming": "Sheetmetal Forming",
    "sheet metal forming": "Sheetmetal Forming",
    
    # Die Casting
    "die casting": "Die Casting",
    "casting": "Die Casting",
    
    # Milling
    "milling": "Milling",
    "mill": "Milling",
    
    # Drilling
    "drilling": "Drilling",
    "drill": "Drilling",
    
    # Assembly
    "assembly": "Assembly",
    
    # Additive Manufacturing
    "additive manufacturing": "Additive Manufacturing",
    "additive": "Additive Manufacturing",
    "3d printing": "Additive Manufacturing",
    "am": "Additive Manufacturing",
    
    # Turning
    "turning": "Turning",
    "lathe": "Turning",
    
    # Tubing
    "tubing": "Tubing",
    "tube": "Tubing",
    
    # General
    "general": "General"
}

# Ensure canonical domains themselves map to themselves
for _canonical in CANONICAL_DOMAINS:
    DOMAIN_ALIASES[_canonical.lower()] = _canonical


def normalize_domain(raw: str) -> Optional[str]:
    """
    Normalize a raw domain string to its canonical representation.
    
    Matches are case-insensitive and check against a predefined list of aliases.
    
    Args:
        raw (str): The raw domain string to normalize.
        
    Returns:
        Optional[str]: The canonical domain string, or None if not recognized.
    """
    if not raw:
        return None
    
    lower_raw = raw.strip().lower()
    return DOMAIN_ALIASES.get(lower_raw)

def is_valid_domain(domain: str) -> bool:
    """
    Check if a given domain is a valid canonical domain.
    
    Args:
        domain (str): The domain string to check.
        
    Returns:
        bool: True if the domain is a recognized canonical domain, False otherwise.
    """
    if not domain:
        return False
    return domain in CANONICAL_DOMAINS

def list_domains() -> List[str]:
    """
    Get a list of all canonical domains.
    
    Returns:
        List[str]: A list of canonical domain strings.
    """
    return list(CANONICAL_DOMAINS)
