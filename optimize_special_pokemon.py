#!/usr/bin/env python3
"""
Optimizes special Pokémon selection by pre-computing type combinations.

This script creates a mapping of type combinations to lists of Pokémon IDs
to make pivot, fulcrum, and mimic selection much faster during randomization.
"""

import json
import os
import random
import time
from typing import Dict, List, Set, Optional, Tuple

# Import our Pokémon data loader
from pokemon_shared import read_mondata

# Global caches
_pivot_cache = {}
_fulcrum_cache = {}
_mimic_cache = {}

# Type combination cache (what we're building)
_type_combo_cache = {}

def read_pivot_data(base_path="."):
    """Read pivot type combinations from file."""
    pivot_path = os.path.join(base_path, "data", "pivots.txt")
    print(f"Reading pivot data from {pivot_path}")
    
    global _pivot_cache
    _pivot_cache = {}
    current_type = None
    
    try:
        with open(pivot_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Check if this is a type section header
                if line.startswith("[") and line.endswith("]"):
                    # Extract type name from section header
                    current_type = line[1:-1]  # Remove brackets
                    _pivot_cache[current_type] = []
                else:
                    # Add this type combination to the current type's list
                    if current_type:
                        _pivot_cache[current_type].append(line)
        
        # Count entries for each type
        print("Loaded pivot type combinations:")
        for type_name, type_combos in _pivot_cache.items():
            print(f"  {type_name}: {len(type_combos)} type combinations")
            
        return _pivot_cache
    
    except FileNotFoundError:
        print(f"Warning: Pivot data file not found at {pivot_path}")
        return {}

def read_fulcrum_data(base_path="."):
    """Read fulcrum type combinations from file."""
    fulcrum_path = os.path.join(base_path, "data", "fulcrums.txt")
    print(f"Reading fulcrum data from {fulcrum_path}")
    
    global _fulcrum_cache
    _fulcrum_cache = {}
    current_type = None
    
    try:
        with open(fulcrum_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Check if this is a type section header
                if line.startswith("[") and line.endswith("]"):
                    # Extract type name from section header
                    current_type = line[1:-1]  # Remove brackets
                    _fulcrum_cache[current_type] = []
                else:
                    # Add this type combination to the current type's list
                    if current_type:
                        _fulcrum_cache[current_type].append(line)
        
        # Count entries for each type
        print("Loaded fulcrum type combinations:")
        for type_name, type_combos in _fulcrum_cache.items():
            print(f"  {type_name}: {len(type_combos)} type combinations")
            
        return _fulcrum_cache
    
    except FileNotFoundError:
        print(f"Warning: Fulcrum data file not found at {fulcrum_path}")
        return {}

def get_mon_types(mon) -> Tuple[List[str], int]:
    """Extract type information and BST from a Pokémon data entry."""
    # Get the type data from the monster
    mon_types = []
    bst = 0
    
    if "types" in mon:
        mon_types = mon["types"]
        if isinstance(mon_types, str):
            mon_types = [mon_types]
    elif "type1" in mon:
        mon_types = [mon["type1"]]
        if mon.get("type2"):
            mon_types.append(mon["type2"])
    
    # Get BST if available
    if "bst" in mon:
        bst = mon["bst"]
    elif hasattr(mon, "bst"):
        bst = mon.bst
    
    return mon_types, bst

def build_type_combination_cache(mondata):
    """Build a cache mapping type combinations to lists of matching Pokémon IDs."""
    start_time = time.time()
    print("Building type combination cache...")
    
    global _type_combo_cache
    _type_combo_cache = {}
    
    # Process all pivot type combinations
    for gym_type, pivot_types in _pivot_cache.items():
        for pivot_type in pivot_types:
            if pivot_type not in _type_combo_cache:
                _type_combo_cache[pivot_type] = []
            
            # Find all Pokémon matching this type combination
            for mon_id, mon in enumerate(mondata):
                mon_types, _ = get_mon_types(mon)
                
                # Skip Pokémon with no type data
                if not mon_types:
                    continue
                
                # Check if pivot type matches this Pokémon's types
                pivot_type_match = True
                pivot_types = pivot_type.split(", ")
                
                # All pivot types must be in the Pokémon's types
                for pt in pivot_types:
                    if pt not in mon_types:
                        pivot_type_match = False
                        break
                
                # If match found, add to type combination cache
                if pivot_type_match and mon_id not in _type_combo_cache[pivot_type]:
                    _type_combo_cache[pivot_type].append(mon_id)
    
    # Process all fulcrum type combinations
    for gym_type, fulcrum_types in _fulcrum_cache.items():
        for fulcrum_type in fulcrum_types:
            if fulcrum_type not in _type_combo_cache:
                _type_combo_cache[fulcrum_type] = []
            
            # Find all Pokémon matching this type combination
            for mon_id, mon in enumerate(mondata):
                mon_types, _ = get_mon_types(mon)
                
                # Skip Pokémon with no type data
                if not mon_types:
                    continue
                
                # Check if fulcrum type matches this Pokémon's types
                fulcrum_type_match = True
                fulcrum_types = fulcrum_type.split(", ")
                
                # All fulcrum types must be in the Pokémon's types
                for ft in fulcrum_types:
                    if ft not in mon_types:
                        fulcrum_type_match = False
                        break
                
                # If match found, add to type combination cache
                if fulcrum_type_match and mon_id not in _type_combo_cache[fulcrum_type]:
                    _type_combo_cache[fulcrum_type].append(mon_id)
    
    # Count matches for each type combination
    total_combinations = len(_type_combo_cache)
    total_matches = sum(len(matches) for matches in _type_combo_cache.values())
    
    end_time = time.time()
    print(f"Type combination cache built in {end_time - start_time:.2f} seconds")
    print(f"Found {total_combinations} unique type combinations with {total_matches} total Pokémon matches")
    
    # Save the type combination cache to a file
    cache_file = os.path.join(base_path, "data", "special_lists", "type_combo_cache.json")
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    
    with open(cache_file, "w") as f:
        json.dump(_type_combo_cache, f, indent=2)
    
    print(f"Saved type combination cache to {cache_file}")
    return _type_combo_cache

def optimize_special_pokemon(base_path="."):
    """Pre-compute type combinations and matching Pokémon for faster special Pokémon selection."""
    print("Loading Pokémon data...")
    mondata = read_mondata(base_path)
    print(f"Loaded {len(mondata)} Pokémon")
    
    # Read pivot and fulcrum data
    read_pivot_data(base_path)
    read_fulcrum_data(base_path)
    
    # Build and save the type combination cache
    build_type_combination_cache(mondata)
    
    # Test the cache with a few lookups
    print("\nTesting type combination cache with sample lookups:")
    test_combos = []
    
    # Get 5 random type combinations to test
    all_combos = list(_type_combo_cache.keys())
    if all_combos:
        test_combos = random.sample(all_combos, min(5, len(all_combos)))
    
    for combo in test_combos:
        matching_pokemon = _type_combo_cache[combo]
        print(f"  {combo}: {len(matching_pokemon)} matching Pokémon")
    
    print("\nOptimization complete! The randomizer can now use the type_combo_cache.json file")
    print("for faster special Pokémon selection.")

if __name__ == "__main__":
    optimize_special_pokemon()
