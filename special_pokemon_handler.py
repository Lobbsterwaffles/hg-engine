# Special Pokémon Handler Module
# Handles pivot, fulcrum, and mimic Pokémon selection

import os
import random
import time
from typing import Dict, List, Tuple, Optional, Set
from pokemon_shared import find_replacements

# Type constants for easy reference
TYPES = [
    'TYPE_NORMAL', 'TYPE_FIRE', 'TYPE_WATER', 'TYPE_GRASS', 'TYPE_ELECTRIC',
    'TYPE_ICE', 'TYPE_FIGHTING', 'TYPE_POISON', 'TYPE_GROUND', 'TYPE_FLYING',
    'TYPE_PSYCHIC', 'TYPE_BUG', 'TYPE_ROCK', 'TYPE_GHOST', 'TYPE_DRAGON',
    'TYPE_DARK', 'TYPE_STEEL', 'TYPE_FAIRY'
]

# Cache for loaded special Pokémon data
_pivot_cache = None
_fulcrum_cache = None
_mimic_cache = None


def read_pivot_data(base_path: str) -> Dict[str, List[str]]:
    """Read pivot Pokémon data from file."""
    global _pivot_cache
    if _pivot_cache is not None:
        return _pivot_cache
    
    _pivot_cache = {}
    pivot_path = os.path.join(base_path, 'data', 'pivot_analysis.txt')
    
    if not os.path.exists(pivot_path):
        print(f"Warning: Pivot data file not found at {pivot_path}")
        return {}
        
    current_type = None
    with open(pivot_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if line.startswith('[') and line.endswith(']'):
                current_type = line[1:-1]  # Remove brackets
                _pivot_cache[current_type] = []
            elif current_type:
                _pivot_cache[current_type].append(line)
                
    print(f"Loaded pivot data: {len(_pivot_cache)} type sections")
    return _pivot_cache


def read_fulcrum_data(base_path: str) -> Dict[str, List[str]]:
    """Read fulcrum Pokémon data from file."""
    global _fulcrum_cache
    if _fulcrum_cache is not None:
        return _fulcrum_cache
    
    _fulcrum_cache = {}
    fulcrum_path = os.path.join(base_path, 'data', 'fulcrumsmonlist.txt')
    
    if not os.path.exists(fulcrum_path):
        print(f"Warning: Fulcrum data file not found at {fulcrum_path}")
        return {}
        
    current_type = None
    with open(fulcrum_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if line.startswith('[') and line.endswith(']'):
                current_type = line[1:-1]  # Remove brackets
                _fulcrum_cache[current_type] = []
            elif current_type:
                _fulcrum_cache[current_type].append(line)
                
    print(f"Loaded fulcrum data: {len(_fulcrum_cache)} type sections")
    return _fulcrum_cache


def read_mimic_data(base_path: str) -> Dict[str, List[str]]:
    """Read mimic Pokémon data from file."""
    global _mimic_cache
    if _mimic_cache is not None:
        return _mimic_cache
    
    _mimic_cache = {}
    mimic_path = os.path.join(base_path, 'data', 'type_mimics_with_prevos.txt')
    
    if not os.path.exists(mimic_path):
        print(f"Warning: Mimic data file not found at {mimic_path}")
        return {}
        
    print(f"Reading mimic data from {mimic_path}")
    current_type = None
    section_counts = {}
    
    with open(mimic_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if line.startswith('[') and line.endswith(']'):
                # Extract type name from brackets
                section_type = line[1:-1]  # Remove brackets
                # Convert to standardized format (TYPE_WATER instead of WATER)
                if not section_type.startswith("TYPE_"):
                    current_type = "TYPE_" + section_type
                else:
                    current_type = section_type
                    
                # Initialize the list for this type
                _mimic_cache[current_type] = []
                # Also add an entry with the non-prefixed key for compatibility
                if not section_type.startswith("TYPE_"):
                    _mimic_cache[section_type] = []
            elif current_type:
                # Store the species name
                _mimic_cache[current_type].append(line)
                # Also add to non-prefixed version if applicable
                if current_type.startswith("TYPE_") and current_type[5:] in _mimic_cache:
                    _mimic_cache[current_type[5:]].append(line)
    
    # Print summary of what we found
    print("\nMimic data sections found:")
    for type_name, species_list in _mimic_cache.items():
        if type_name.startswith("TYPE_"):
            print(f"  {type_name}: {len(species_list)} Pokémon")
                
    return _mimic_cache


def get_pivot_pokemon(gym_type, mondata, base_path=".", used_ids=None):
    """Get a suitable pivot Pokémon for the given gym type
    
    Args:
        gym_type (str): The gym type to get a pivot for
        mondata (list): List of Pokémon data dictionaries
        base_path (str): Base path for loading data files
        used_ids (list): List of Pokémon IDs already used, to avoid duplicates
    
    Returns:
        int: ID of selected pivot Pokémon, or None if no suitable pivot found
    """
    global _pivot_cache
    
    # Make sure used_ids is a set for faster lookups
    used_ids_set = set(used_ids or [])
    
    # Load pivot data if not already loaded
    if not _pivot_cache:
        read_pivot_data(base_path)
    
    # Standard format is TYPE_WATER, but handle both with and without prefix
    search_types = []
    if gym_type.startswith('TYPE_'):
        search_types.append(gym_type)
        search_types.append(gym_type[5:])  # also try without the TYPE_ prefix
    else:
        search_types.append(gym_type)
        search_types.append(f'TYPE_{gym_type}')  # also try with the TYPE_ prefix
    
    # Try each search type to find matching Pokémon
    for type_key in search_types:
        if type_key in _pivot_cache:
            # Get list of species from the pivot data
            species_list = _pivot_cache[type_key]
            if not species_list:
                continue
                
            # Randomize the list
            random.shuffle(species_list)
            
            # Find the first species ID that's not in used_ids
            for species_name in species_list:
                # Most species are in format "SPECIES_PIKACHU"
                species_name_no_prefix = species_name.replace('SPECIES_', '')
                
                # Look for this species in mondata
                for species_id, mon in enumerate(mondata):
                    # Skip if already used
                    if species_id in used_ids_set:
                        continue
                        
                    # Check if this is the right species
                    name = mon.get('name', '')
                    if not name and 'species_name' in mon:
                        name = mon['species_name']
                    
                    if not name:
                        continue
                        
                    if name.upper() == species_name_no_prefix:
                        print(f"Selected pivot Pokémon for {gym_type}: {name} (ID: {species_id})")
                        return species_id
    
    print(f"Could not find any valid pivot Pokémon for {gym_type}")
    return None


def get_fulcrum_pokemon(type_name: str, mondata, base_path: str,
                       blacklist: Optional[Set[int]] = None) -> Optional[int]:
    """Get a fulcrum Pokémon for the given type.
    
    Args:
        type_name (str): The gym type to get a fulcrum for
        mondata (list): List of Pokémon data dictionaries
        base_path (str): Base path for loading data files
        blacklist (set): Set of Pokémon IDs to exclude
    
    Returns:
        int: ID of selected fulcrum Pokémon, or None if no suitable fulcrum found
    """
    global _fulcrum_cache
    
    # Make sure blacklist is a set for faster lookups
    blacklist_set = blacklist or set()
    
    # Load fulcrum data if not already loaded
    if not _fulcrum_cache:
        read_fulcrum_data(base_path)
    
    # Standard format is TYPE_WATER, but handle both with and without prefix
    search_types = []
    if type_name.startswith('TYPE_'):
        search_types.append(type_name)
        search_types.append(type_name[5:])  # also try without the TYPE_ prefix
    else:
        search_types.append(type_name)
        search_types.append(f'TYPE_{type_name}')  # also try with the TYPE_ prefix
    
    # Try each search type to find matching Pokémon
    for type_key in search_types:
        if type_key in _fulcrum_cache:
            # Get list of species from the fulcrum data
            species_list = _fulcrum_cache[type_key]
            if not species_list:
                continue
                
            # Randomize the list
            random.shuffle(species_list)
            
            # Find the first species ID that's not in blacklist
            for species_name in species_list:
                # Most species are in format "SPECIES_PIKACHU"
                species_name_no_prefix = species_name.replace('SPECIES_', '')
                
                # Look for this species in mondata
                for species_id, mon in enumerate(mondata):
                    # Skip if in blacklist
                    if species_id in blacklist_set:
                        continue
                        
                    # Check if this is the right species
                    name = mon.get('name', '')
                    if not name and 'species_name' in mon:
                        name = mon['species_name']
                    
                    if not name:
                        continue
                        
                    if name.upper() == species_name_no_prefix:
                        print(f"Selected fulcrum Pokémon for {type_name}: {name} (ID: {species_id})")
                        return species_id
    
    print(f"Could not find any valid fulcrum Pokémon for {type_name}")
    return None


def get_mimic_pokemon(type_name: str, mondata, base_path: str, 
                     blacklist: Optional[Set[int]] = None) -> Optional[int]:
    """Get a mimic Pokémon for the given type.
    
    Args:
        type_name (str): The gym type to get a mimic for (e.g., 'FLYING', 'WATER')
        mondata (list): List of Pokémon data dictionaries
        base_path (str): Base path for loading data files
        blacklist (set): Set of Pokémon IDs to exclude
    
    Returns:
        int: ID of selected mimic Pokémon, or None if no suitable mimic found
    """
    # Store original type name for logging
    original_type = type_name
    
    # Standardize type_name format (with and without TYPE_ prefix for flexibility)
    type_with_prefix = type_name
    type_without_prefix = type_name
    
    if not type_name.startswith('TYPE_'):
        type_with_prefix = 'TYPE_' + type_name.upper()
        type_without_prefix = type_name.upper()
    else:
        type_without_prefix = type_name[5:] if len(type_name) > 5 else type_name
    
    print(f"Looking for a mimic Pokémon for gym type: {original_type} (searching as {type_with_prefix})")
        
    # Load mimic data if not already loaded
    if not _mimic_cache:
        read_mimic_data(base_path)
    
    # Check if we have mimics for this type (try both formats)
    if type_with_prefix in _mimic_cache and _mimic_cache[type_with_prefix]:
        type_name = type_with_prefix
    elif type_without_prefix in _mimic_cache and _mimic_cache[type_without_prefix]:
        type_name = type_without_prefix
        print(f"Found mimics under {type_without_prefix} instead of {type_with_prefix}")
    else:
        print(f"No mimics found for type {type_with_prefix} or {type_without_prefix}")
        return None
    
    # Get species names for this specific gym type
    species_names = _mimic_cache[type_name]
    
    if not species_names:
        print(f"Empty mimic list for type {type_name}")
        return None
    
    print(f"Found {len(species_names)} potential mimics for {type_name}")
    
    # Map species names to IDs
    candidates = []
    for species_name in species_names:
        if not species_name.startswith('SPECIES_'):
            continue
            
        # Extract the species name without the SPECIES_ prefix
        species_name_no_prefix = species_name[8:]
        
        # Find the species ID based on the name
        for mon in mondata:
            # The ID is just the index in the mondata list
            species_id = mondata.index(mon)
            
            if blacklist and species_id in blacklist:
                continue
                
            # Compare the name (removing SPECIES_ prefix)
            name = mon.get('name', '')
            if not name and 'species_name' in mon:
                name = mon['species_name']
            
            if not name:
                continue
                
            if name.upper() == species_name_no_prefix:
                candidates.append((species_id, name))
                break
    
    if candidates:
        # Now candidates contains tuples of (species_id, name)
        chosen = random.choice(candidates)
        print(f"Selected mimic Pokémon for {type_name}: {chosen[1]} (ID: {chosen[0]})")
        return chosen[0]
        
    print(f"Could not find any valid mimic Pokémon for {type_name}")
    return None


def apply_special_pokemon(trainer_pokemon, gym_type: str, mondata, base_path: str,
                         use_pivots: bool = False, use_fulcrums: bool = False, use_mimics: bool = False,
                         blacklist: Optional[Set[int]] = None):
    """Apply special Pokémon selections to a trainer's team.
    
    Args:
        trainer_pokemon (list): List of trainer's Pokémon
        gym_type (str): The gym type to apply special Pokémon for
        mondata (list): List of Pokémon data dictionaries
        base_path (str): Base path for loading data files
        use_pivots (bool): Whether to use pivot Pokémon
        use_fulcrums (bool): Whether to use fulcrum Pokémon
        use_mimics (bool): Whether to use mimic Pokémon
        blacklist (set): Set of Pokémon IDs to exclude
        
    Returns:
        list: Updated list of trainer's Pokémon
    """
    if not any([use_pivots, use_fulcrums, use_mimics]) or not gym_type:
        return trainer_pokemon
        
    # We'll modify a copy of the trainer's Pokémon list
    result = trainer_pokemon.copy()
    
    # Apply special Pokémon based on team size requirements
    # Track which Pokémon IDs we've already used
    used_ids = set(mon['species'] for mon in result)
    if blacklist:
        used_ids.update(blacklist)
        
    # Get indices to replace (we won't replace the first Pokémon)
    indices_to_replace = list(range(1, len(result)))
    random.shuffle(indices_to_replace)
    
    # Apply special Pokémon based on team size
    team_size = len(result)
    
    # Try to add a mimic Pokémon (requires 4+ Pokémon)
    if use_mimics and indices_to_replace and team_size >= 4:
        print(f"\nTeam size {team_size} meets mimic requirement (4+)")
        print(f"Trying to add a mimic Pokémon for gym type: {gym_type}")
        mimic_id = get_mimic_pokemon(gym_type, mondata, base_path, used_ids)
        if mimic_id and mimic_id not in used_ids:
            idx = indices_to_replace.pop(0)
            # Find the Pokémon name for logging
            pokemon_name = "Unknown"
            for mon in mondata:
                if mondata.index(mon) == mimic_id:
                    pokemon_name = mon.get('name', '') or mon.get('species_name', 'Unknown')
                    break
                    
            print(f"Added mimic Pokémon {pokemon_name} (ID: {mimic_id}) to team position {idx}")
            result[idx]['species'] = mimic_id
            used_ids.add(mimic_id)
        else:
            print(f"Could not add a mimic Pokémon for {gym_type} (none found or already used)")
    else:
        if use_mimics:
            print(f"Team size {team_size} is too small for mimic (needs 4+)")
            
    # Try to add a pivot Pokémon (requires 5+ Pokémon)
    if use_pivots and indices_to_replace and team_size >= 5:
        print(f"\nTeam size {team_size} meets pivot requirement (5+)")
        pivot_id = get_pivot_pokemon(gym_type, mondata, base_path, used_ids)
        if pivot_id and pivot_id not in used_ids:
            idx = indices_to_replace.pop(0)
            result[idx]['species'] = pivot_id
            used_ids.add(pivot_id)
            print(f"Added pivot Pokémon (ID: {pivot_id}) to team position {idx}")
        else:
            print(f"Could not add a pivot Pokémon for {gym_type} (none found or already used)")
    else:
        if use_pivots:
            print(f"Team size {team_size} is too small for pivot (needs 5+)")
            
    # Try to add a fulcrum Pokémon (requires exactly 6 Pokémon)
    if use_fulcrums and indices_to_replace and team_size == 6:
        print(f"\nTeam size {team_size} meets fulcrum requirement (exactly 6)")
        fulcrum_id = get_fulcrum_pokemon(gym_type, mondata, base_path, used_ids)
        if fulcrum_id and fulcrum_id not in used_ids:
            idx = indices_to_replace.pop(0)
            result[idx]['species'] = fulcrum_id
            used_ids.add(fulcrum_id)
            print(f"Added fulcrum Pokémon (ID: {fulcrum_id}) to team position {idx}")
        else:
            print(f"Could not add a fulcrum Pokémon for {gym_type} (none found or already used)")
    else:
        if use_fulcrums:
            print(f"Team size {team_size} is not exactly 6 for fulcrum requirement")

    
    return result
