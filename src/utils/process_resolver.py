"""Process type resolution utilities for BFD mode."""

import json
import os
from typing import Dict, List, Optional, Any
from difflib import get_close_matches
import re

def load_process_hierarchy() -> Dict[str, Any]:
    """Load process units hierarchy from JSON file."""
    hierarchy_path = "/home/hvksh/processeng/process_units_hierarchy.json"
    if not os.path.exists(hierarchy_path):
        raise FileNotFoundError(f"Process hierarchy file not found: {hierarchy_path}")
    
    with open(hierarchy_path, 'r') as f:
        return json.load(f)

def load_process_aliases() -> Dict[str, str]:
    """Load process aliases from JSON file."""
    aliases_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "process_aliases.json")
    if not os.path.exists(aliases_path):
        return {}
    
    with open(aliases_path, 'r') as f:
        return json.load(f)

def find_in_hierarchy(hierarchy: Dict[str, Any], query: str) -> Optional[Dict[str, Any]]:
    """
    Search hierarchy for process type and return its details.
    Returns: {'canonical_name': str, 'area_number': int, 'process_unit_id': str, ...}
    """
    # Traverse hierarchy recursively
    for category, subcategories in hierarchy.items():
        if category == query:
            # Top-level category match (e.g., "Preliminary Treatment")
            # These typically don't have area numbers, so we'll use the first child
            if isinstance(subcategories, dict):
                for subcat, details in subcategories.items():
                    if isinstance(details, dict) and 'area_number' in details:
                        return {
                            'canonical_name': category,
                            'area_number': details['area_number'],
                            'process_unit_id': details.get('process_unit_id', 'TK'),
                            'category': category,
                            'subcategory': subcat
                        }
        
        if isinstance(subcategories, dict):
            for subcat, processes in subcategories.items():
                if subcat == query:
                    # Subcategory match (e.g., "Headworks")
                    if isinstance(processes, dict):
                        # Find first process with area number
                        for process_name, details in processes.items():
                            if isinstance(details, dict) and 'area_number' in details:
                                return {
                                    'canonical_name': subcat,
                                    'area_number': details['area_number'],
                                    'process_unit_id': details.get('process_unit_id', 'TK'),
                                    'category': category,
                                    'subcategory': subcat
                                }
                
                if isinstance(processes, dict):
                    for process_name, details in processes.items():
                        if process_name == query:
                            # Specific process match (e.g., "Coarse Screening")
                            if isinstance(details, dict) and 'area_number' in details:
                                return {
                                    'canonical_name': process_name,
                                    'area_number': details['area_number'],
                                    'process_unit_id': details.get('process_unit_id', 'TK'),
                                    'category': category,
                                    'subcategory': subcat,
                                    'process_name': process_name
                                }
    
    return None

def get_all_process_names(hierarchy: Dict[str, Any]) -> List[str]:
    """Extract all process names from hierarchy for fuzzy matching."""
    names = []
    
    for category, subcategories in hierarchy.items():
        names.append(category)
        
        if isinstance(subcategories, dict):
            for subcat, processes in subcategories.items():
                names.append(subcat)
                
                if isinstance(processes, dict):
                    for process_name, details in processes.items():
                        if isinstance(details, dict):
                            names.append(process_name)
    
    return names

def get_fuzzy_matches(query: str, hierarchy: Dict[str, Any], n: int = 3, cutoff: float = 0.6) -> List[str]:
    """Get fuzzy matches for a query string."""
    all_names = get_all_process_names(hierarchy)
    matches = get_close_matches(query, all_names, n=n, cutoff=cutoff)
    return matches

def resolve_process_type(query: str, allow_custom: bool = False) -> Optional[Dict[str, Any]]:
    """
    Resolve process type via exact match, aliases, or fuzzy match.
    
    Returns:
        Dict with canonical_name, area_number, process_unit_id, category, subcategory
        or None if not found and custom not allowed
    """
    hierarchy = load_process_hierarchy()
    aliases = load_process_aliases()
    
    # 1. Exact match in hierarchy
    found = find_in_hierarchy(hierarchy, query)
    if found:
        return found
    
    # 2. Check aliases
    if query in aliases:
        canonical = aliases[query]
        found = find_in_hierarchy(hierarchy, canonical)
        if found:
            return found
    
    # 3. Try case-insensitive match
    query_lower = query.lower()
    for name in get_all_process_names(hierarchy):
        if name.lower() == query_lower:
            found = find_in_hierarchy(hierarchy, name)
            if found:
                return found
    
    # 4. Fuzzy match (but don't auto-accept)
    matches = get_fuzzy_matches(query, hierarchy, n=3, cutoff=0.7)
    if matches and not allow_custom:
        # Return None with suggestions in the error message
        # The caller should handle this and raise an appropriate error
        return None
    
    # 5. Custom process (if allowed)
    if allow_custom:
        return {
            'canonical_name': query,
            'area_number': 900,  # Reserved for custom
            'process_unit_id': 'CUS',
            'category': 'Custom',
            'subcategory': 'User Defined',
            'is_custom': True
        }
    
    return None

def generate_semantic_id(flowsheet, base_name: str) -> str:
    """
    Generate a semantic ID for BFD units compatible with SFILES2 parsing.

    SFILES2 requires node IDs to match "name-number" pattern (single hyphen).
    E.g., "Aeration Tank" -> "AerationTank-01" (not "Aeration-Tank-01")

    Args:
        flowsheet: Flowsheet object to check for existing IDs
        base_name: Human-readable process name (e.g., "Aeration Tank")

    Returns:
        SFILES2-compatible node ID (e.g., "AerationTank-01")
    """
    # Convert to CamelCase to avoid internal hyphens
    # "Aeration Tank" -> "AerationTank"
    words = re.findall(r'[a-zA-Z0-9]+', base_name)
    normalized = ''.join(word.capitalize() for word in words)

    # Find existing units with similar base name
    existing_count = 0
    for node_id in flowsheet.state.nodes():
        # Check if node starts with our normalized name
        if node_id.startswith(normalized):
            # Extract sequence number if present (after single hyphen)
            match = re.search(r'-(\d+)$', node_id)
            if match:
                seq = int(match.group(1))
                existing_count = max(existing_count, seq)

    # Generate new ID with next sequence (single hyphen before number)
    sequence = existing_count + 1
    return f"{normalized}-{sequence:02d}"

def get_next_sequence_number(flowsheet, area_number: int, process_unit_id: str) -> int:
    """
    Find next available sequence number for given area/unit type.
    E.g., if 101-BS-01 exists, return 2 for next unit.
    """
    existing_sequences = []
    
    for node_id, node_data in flowsheet.state.nodes(data=True):
        if (node_data.get('area_number') == area_number and 
            node_data.get('process_unit_id') == process_unit_id):
            seq = node_data.get('sequence_number', 0)
            existing_sequences.append(seq)
    
    return max(existing_sequences, default=0) + 1

def extract_valid_bfd_units(hierarchy: Dict[str, Any]) -> List[str]:
    """Extract all valid BFD unit types from hierarchy."""
    return get_all_process_names(hierarchy)