#!/usr/bin/env python3
"""
Move Reader Utilities for the Pokémon Move Handler
This module contains functions for reading and parsing Pokémon move data
"""

import os
import json
import logging
import re
from construct import *
import ndspy.rom
import ndspy.narc

# Define the move data structure based on armips/include/movemacros.s
move_struct = Struct(
    "effect" / Int16ul,            # Battle effect (halfword = 2 bytes)
    "category" / Int8ul,           # Physical/Special split (byte = 1 byte)
    "power" / Int8ul,              # Base power (byte = 1 byte)
    "type" / Int8ul,               # Move type (byte = 1 byte)
    "accuracy" / Int8ul,           # Accuracy (byte = 1 byte)
    "pp" / Int8ul,                 # PP (byte = 1 byte)
    "effect_chance" / Int8ul,      # Effect chance (byte = 1 byte)
    "target" / Int16ul,            # Target range (halfword = 2 bytes)
    "priority" / Int8ul,           # Priority (byte = 1 byte)
    "flags" / Int8ul,              # Flags (byte = 1 byte)
    "appeal" / Int8ul,             # Contest appeal (byte = 1 byte)
    "contest_type" / Int8ul,       # Contest type (byte = 1 byte)
    "padding" / Int16ul,           # Padding at the end (16 bits/2 bytes)
)

# Define constants for move categories
CATEGORY_PHYSICAL = 0
CATEGORY_SPECIAL = 1
CATEGORY_STATUS = 2

# Define constants for move types
TYPE_NAMES = {
    0: "Normal", 1: "Fighting", 2: "Flying", 3: "Poison", 4: "Ground",
    5: "Rock", 6: "Bug", 7: "Ghost", 8: "Steel", 9: "Fire",
    10: "Water", 11: "Grass", 12: "Electric", 13: "Psychic", 14: "Ice",
    15: "Dragon", 16: "Dark", 17: "Fairy"
}

# Cache for expensive data loading operations
_move_data_cache = None
_levelup_cache = None
_eggmoves_cache = None
_tm_learnset_cache = None
_move_names_cache = None
_move_blacklist_cache = None
_move_whitelist_cache = None

def read_move_names(base_path):
    """Read move names from text files in ROM if possible"""
    global _move_names_cache
    
    # Return cached data if available
    if _move_names_cache is not None:
        return _move_names_cache
    
    try:
        # Based on movemacros.s, move names are in file 750
        with open(os.path.join(base_path, "build/rawtext/750.txt"), "r", encoding="utf-8") as f:
            _move_names_cache = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        # Try alternate location
        try:
            with open(os.path.join(base_path, "build/rawtext/58.txt"), "r", encoding="utf-8") as f:
                _move_names_cache = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            logging.warning("Move name file not found. Using generic names.")
            _move_names_cache = [f"Move {i}" for i in range(1000)]  # Just a placeholder
    
    return _move_names_cache

def parse_move_data(data):
    """Parse move data from binary data"""
    try:
        move = move_struct.parse(data)
        return move
    except Exception as e:
        logging.error(f"Error parsing move data: {e}")
        return None

def read_moves(rom, base_path="."):
    """Read all move data from ROM"""
    global _move_data_cache
    
    # Return cached data if available
    if _move_data_cache is not None:
        return _move_data_cache
    
    # Based on movemacros.s, moves are in a011 NARC
    try:
        # First try the a011 location (from movemacros.s)
        narc_file_id = rom.filenames.idOf("a/0/1/1")
        move_narc = rom.files[narc_file_id]
    except ValueError:
        # If not found, search for potential move data files
        logging.warning("Standard move data location not found. Searching for possible alternatives...")
        potential_files = []
        for file_id, file_path in rom.filenames.items():
            if "move" in file_path.lower() or "a011" in file_path.lower():
                logging.info(f"Potential move data file: {file_path} (ID: {file_id})")
                potential_files.append((file_id, file_path))
                
        if not potential_files:
            logging.error("No move files found.")
            return []
        
        # Try the first potential file
        narc_file_id = potential_files[0][0]
        move_narc = rom.files[narc_file_id]
    
    # Load the move data NARC
    move_narc_data = ndspy.narc.NARC(move_narc)
    logging.info(f"Found {len(move_narc_data.files)} move entries in ROM")
    
    # Read move names if possible
    move_names = read_move_names(base_path)
    
    # Parse each move entry
    moves = []
    for i, data in enumerate(move_narc_data.files):
        move = parse_move_data(data)
        if move:
            # Add name and index
            move.index = i
            move.name = f"MOVE_{move_names[i]}" if i < len(move_names) else f"MOVE_{i}"
            moves.append(move)
    
    # Cache the results
    _move_data_cache = moves
    return moves

def read_levelup_learnsets(filepath):
    """
    Read level-up learnsets from the levelupdata.s file.
    
    Args:
        filepath: Path to the levelupdata.s file
        
    Returns:
        Dictionary mapping species names to lists of (move_name, level) tuples
    """
    global _levelup_cache
    
    # Return cached data if available
    if _levelup_cache is not None:
        return _levelup_cache
    
    learnsets = {}
    current_species = None
    current_moves = []
    
    logging.info(f'Reading level-up learnsets from {filepath}')
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Check if this is a species definition line
                if line.startswith('levelup SPECIES_'):
                    # If we were processing a previous species, save it
                    if current_species is not None:
                        learnsets[current_species] = current_moves
                        
                    # Start a new species
                    current_species = line.replace('levelup ', '').strip()
                    current_moves = []
                
                # Check if this is a move definition line
                elif line.startswith('learnset MOVE_'):
                    # Parse the move and level
                    parts = line.replace('learnset ', '').split(',')
                    move_name = parts[0].strip()
                    level = int(parts[1].strip())
                    current_moves.append((move_name, level))
                
                # Check if this is the end of a learnset
                elif line == 'terminatelearnset':
                    if current_species is not None:
                        learnsets[current_species] = current_moves
                        current_species = None
                        current_moves = []
    
    except FileNotFoundError:
        logging.error(f"Error: Level-up learnset file not found at {filepath}")
    except Exception as e:
        logging.error(f"Error reading level-up learnsets: {e}")
    
    logging.info(f'Successfully loaded {len(learnsets)} level-up learnsets')
    
    # Cache the results
    _levelup_cache = learnsets
    return learnsets

def read_egg_moves(filepath):
    """
    Read egg moves from the modern_egg_moves.json file.
    
    Args:
        filepath: Path to the egg moves JSON file
        
    Returns:
        Dictionary mapping species names to lists of move names
    """
    global _eggmoves_cache
    
    # Return cached data if available
    if _eggmoves_cache is not None:
        return _eggmoves_cache
    
    egg_moves = {}
    
    logging.info(f'Reading egg moves from {filepath}')
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            egg_moves = json.load(f)
            logging.info(f'Successfully loaded {len(egg_moves)} egg move entries')
    except FileNotFoundError:
        logging.error(f"Error: Egg moves file not found at {filepath}")
    except json.JSONDecodeError:
        logging.error(f"Error: Invalid JSON in egg moves file")
    except Exception as e:
        logging.error(f"Error reading egg moves: {e}")
    
    # Cache the results
    _eggmoves_cache = egg_moves    
    return egg_moves

def read_tm_learnset(filepath):
    """
    Read TM learnset from the modern_tm_learnset.json file.
    
    Args:
        filepath: Path to the TM learnset JSON file
        
    Returns:
        Dictionary mapping species names to lists of move names
    """
    global _tm_learnset_cache
    
    # Return cached data if available
    if _tm_learnset_cache is not None:
        return _tm_learnset_cache
    
    tm_learnset = {}
    
    logging.info(f'Reading TM learnset from {filepath}')
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tm_learnset = json.load(f)
            logging.info(f'Successfully loaded {len(tm_learnset)} TM learnset entries')
    except FileNotFoundError:
        logging.error(f"Error: TM learnset file not found at {filepath}")
    except json.JSONDecodeError:
        logging.error(f"Error: Invalid JSON in TM learnset file")
    except Exception as e:
        logging.error(f"Error reading TM learnset: {e}")
    
    # Cache the results
    _tm_learnset_cache = tm_learnset
    return tm_learnset

def read_move_blacklist(filepath):
    """Read move blacklist from file."""
    global _move_blacklist_cache
    
    # Return cached data if available
    if _move_blacklist_cache is not None:
        return _move_blacklist_cache
    
    blacklist = set()
    
    logging.info(f'Reading move blacklist from {filepath}')
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    blacklist.add(line)
        logging.info(f'Successfully loaded {len(blacklist)} moves in blacklist')
    except FileNotFoundError:
        logging.info(f"Blacklist file not found at {filepath}, using default")
        blacklist = {"MOVE_FUTURE_SIGHT"}  # Default blacklist
    
    # Cache the results
    _move_blacklist_cache = blacklist
    return blacklist

def read_move_whitelist(filepath):
    """Read move whitelist from file."""
    global _move_whitelist_cache
    
    # Return cached data if available
    if _move_whitelist_cache is not None:
        return _move_whitelist_cache
    
    whitelist = set()
    
    logging.info(f'Reading move whitelist from {filepath}')
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    whitelist.add(line)
        logging.info(f'Successfully loaded {len(whitelist)} moves in whitelist')
    except FileNotFoundError:
        logging.info(f"Whitelist file not found at {filepath}, using default")
        whitelist = {"MOVE_DOUBLE_HIT"}  # Default whitelist
    
    # Cache the results
    _move_whitelist_cache = whitelist
    return whitelist

def classify_pokemon_attacker_type(pokemon_data):
    """
    Classify a Pokémon as Physical, Special, or Mixed attacker.
    
    Args:
        pokemon_data: Pokémon data including attack and special attack stats
        
    Returns: 
        str: "Physical", "Special", or "Mixed"
    """
    # Get attack and special attack stats
    attack = pokemon_data.attack
    sp_attack = pokemon_data.sp_attack
    
    # Calculate the difference percentage
    if attack > sp_attack:
        diff = (attack - sp_attack) / attack * 100
        if diff >= 20:  # 20% threshold
            return "Physical"
    elif sp_attack > attack:
        diff = (sp_attack - attack) / sp_attack * 100
        if diff >= 20:  # 20% threshold
            return "Special"
    
    # If we get here, it's Mixed
    return "Mixed"

def check_move_in_learnset(species_name, move_name, level, levelup_data, egg_moves_data, tm_learnset_data):
    """
    Check if a move is in the Pokémon's learnset at the given level.
    
    Args:
        species_name: Species name (e.g., "SPECIES_FERALIGATR")
        move_name: Move name (e.g., "MOVE_HYDRO_PUMP" or "Hydro Pump")
        level: Current Pokémon level
        levelup_data: Level-up learnset data
        egg_moves_data: Egg moves data
        tm_learnset_data: TM learnset data
        
    Returns:
        bool: True if the move is learnable, False otherwise
    """
    import logging
    
    # First, let's create two versions of the move name for comparison:
    # 1. The MOVE_NAME_FORMAT version (e.g., MOVE_FLAMETHROWER)
    # 2. The Name Format version (e.g., Flamethrower)
    
    # Create the MOVE_FORMAT version
    move_format_version = move_name
    if not move_name.startswith("MOVE_"):
        move_format_version = "MOVE_" + move_name.replace(" ", "_").upper()
    
    # Create the Name Format version
    name_format_version = move_name
    if move_name.startswith("MOVE_"):
        name_format_version = move_name[5:].replace("_", " ").title()
    
    logging.debug(f"Checking if {move_name} is in learnset for {species_name}")
    logging.debug(f"Comparing with formats: {move_format_version} and {name_format_version}")
    
    # Try several variations of the species name to find it in levelup data
    species_variations = [species_name]
    
    # Add SPECIES_ prefix version if not already present
    if not species_name.startswith("SPECIES_"):
        species_variations.append("SPECIES_" + species_name.replace(" ", "_").upper())
    
    # Handle special characters in species names
    # Try replacing apostrophes and spaces with different formats
    for variant in list(species_variations):  # Create a copy to iterate over
        if "'" in variant:
            # Try both with and without apostrophe
            species_variations.append(variant.replace("'", ""))
            # Try with D instead of 'D for Farfetch'd -> FarfetchD
            if "'D" in variant.upper():
                species_variations.append(variant.upper().replace("'D", "D"))
        
        # Try with hyphen for special cases
        if "-" in variant:
            species_variations.append(variant.replace("-", "_"))
        
        # Handle Mr. Mime special case
        if "MR." in variant.upper() or "MR_" in variant.upper():
            species_variations.append(variant.upper().replace("MR.", "MR").replace("MR_", "MR"))
    
    # Check each species variant in the levelup data
    species_found = False
    for variant in species_variations:
        if variant in levelup_data:
            species_name = variant  # Use the variant that worked
            species_found = True
            break
    
    if not species_found:
        logging.debug(f"{species_name} not found in level-up learnset data. Tried variations: {species_variations}")
        return False
        
    # Check level-up learnset
    for learn_move_name, learn_level in levelup_data[species_name]:
        # We need to normalize the learnset move name for comparison
        normalized_learn_move = learn_move_name
        name_format_learn_move = learn_move_name
        
        if learn_move_name.startswith("MOVE_"):
            name_format_learn_move = learn_move_name[5:].replace("_", " ").title()
        else:
            normalized_learn_move = "MOVE_" + learn_move_name.replace(" ", "_").upper()
            
        # Now compare both formats
        if ((move_format_version == normalized_learn_move or 
             name_format_version == name_format_learn_move) and 
            learn_level <= level):
            logging.debug(f"{move_name} found in level-up learnset for {species_name} at level {learn_level}")
            return True
    
    # Check egg moves
    if egg_moves_data and species_name in egg_moves_data:
        for egg_move in egg_moves_data[species_name]:
            # Normalize egg move name for comparison
            normalized_egg_move = egg_move
            name_format_egg_move = egg_move
            
            if egg_move.startswith("MOVE_"):
                name_format_egg_move = egg_move[5:].replace("_", " ").title()
            else:
                normalized_egg_move = "MOVE_" + egg_move.replace(" ", "_").upper()
                
            # Compare both formats
            if (move_format_version == normalized_egg_move or 
                name_format_version == name_format_egg_move):
                logging.debug(f"{move_name} found in egg moves for {species_name}")
                return True
    
    # Check TM learnset
    if tm_learnset_data and species_name in tm_learnset_data:
        for tm_move in tm_learnset_data[species_name]:
            # Normalize TM move name for comparison
            normalized_tm_move = tm_move
            name_format_tm_move = tm_move
            
            if tm_move.startswith("MOVE_"):
                name_format_tm_move = tm_move[5:].replace("_", " ").title()
            else:
                normalized_tm_move = "MOVE_" + tm_move.replace(" ", "_").upper()
                
            # Compare both formats
            if (move_format_version == normalized_tm_move or 
                name_format_version == name_format_tm_move):
                logging.debug(f"{move_name} found in TM learnset for {species_name}")
                return True
                
    # Move not found in any learnset
    logging.debug(f"{move_name} not found in any learnset for {species_name}")
    return False

def find_suitable_moves(moves_data, pokemon_species, pokemon_types, pokemon_stats, level=50,
                      levelup_data=None, egg_moves_data=None, tm_learnset_data=None,
                      move_blacklist=None, move_whitelist=None):
    """
    Find suitable moves for a Pokémon based on its species, types, and stats.
    
    Args:
        moves_data: List of move data objects
        pokemon_species: Species name (e.g., "SPECIES_CHARIZARD")
        pokemon_types: List of Pokémon's types
        pokemon_stats: Dictionary of Pokémon's stats
        level: Pokémon's level
        levelup_data: Level-up learnset data
        egg_moves_data: Egg moves data
        tm_learnset_data: TM learnset data
        move_blacklist: List of moves to exclude
        move_whitelist: List of moves to prioritize
        
    Returns:
        List of suitable moves, prioritized by type and stat relevance
    """
    if move_blacklist is None:
        move_blacklist = []
        
    if move_whitelist is None:
        move_whitelist = []
    
    # Normalize the species name for learnset lookup
    normalized_species = pokemon_species
    if not pokemon_species.startswith("SPECIES_"):
        normalized_species = "SPECIES_" + pokemon_species.replace(" ", "_").upper()
        logging.debug(f"Normalized species name: {pokemon_species} -> {normalized_species}")
    
    # After normalization, pokemon_species should be the normalized version for consistency
    pokemon_species = normalized_species
    
    # Verify this species exists in the levelup data
    # This check is redundant with the one in move_handler.py, but provides a safety net
    if levelup_data and pokemon_species not in levelup_data:
        logging.error(f"ERROR: Species {pokemon_species} not found in levelup data!")
        # We don't raise an error here because move_handler.py should have caught this already
        
    primary_type = pokemon_types[0] if pokemon_types else None
    secondary_type = pokemon_types[1] if len(pokemon_types) > 1 else None
    
    # Determine attacking stat dominance
    phys_atk = pokemon_stats.get('attack', 0)
    spec_atk = pokemon_stats.get('sp_attack', 0)
    physical_attacker = phys_atk > spec_atk
    
    primary_stab_moves = []
    secondary_stab_moves = []
    other_damaging_moves = []
    
    logging.debug(f"Finding suitable moves for {pokemon_species} (types: {pokemon_types}, level: {level})")
    
    # Check if pokemon_species is in the learnset data
    if levelup_data:
        if pokemon_species in levelup_data:
            logging.debug(f"Found {pokemon_species} in levelup data with {len(levelup_data[pokemon_species])} moves")
        else:
            logging.warning(f"WARNING: {pokemon_species} not found in levelup data")
            
    if egg_moves_data and pokemon_species not in egg_moves_data:
        logging.debug(f"{pokemon_species} not found in egg moves data")
    
    if tm_learnset_data and pokemon_species not in tm_learnset_data:
        logging.debug(f"{pokemon_species} not found in TM learnset data")
    
    # Log available move counts for debugging
    move_counts = {}
    if levelup_data and pokemon_species in levelup_data:
        move_counts['levelup'] = len(levelup_data[pokemon_species])
    if egg_moves_data and pokemon_species in egg_moves_data:
        move_counts['egg'] = len(egg_moves_data[pokemon_species])
    if tm_learnset_data and pokemon_species in tm_learnset_data:
        move_counts['tm'] = len(tm_learnset_data[pokemon_species])
    logging.debug(f"Available moves for {pokemon_species}: {move_counts}")
    
    # Process at most 650 moves to avoid performance issues with large move lists
    for move_id, move in enumerate(moves_data[:650]):
        if not move:
            continue
            
        try:
            move_name = move.name if hasattr(move, 'name') else move.get('name')
            move_type = move.type if hasattr(move, 'type') else move.get('type')
            move_power = move.power if hasattr(move, 'power') else move.get('power')
            move_accuracy = move.accuracy if hasattr(move, 'accuracy') else move.get('accuracy')
            move_category = move.category if hasattr(move, 'category') else move.get('category')
            
            # Skip blacklisted moves
            if move_name in move_blacklist:
                logging.debug(f"Skipping {move_name} (blacklisted)")
                continue
            
            # Skip moves with no power (status moves)
            if move_power == 0:
                logging.debug(f"Skipping {move_name} (no power)")
                continue
            
            # Skip moves with low accuracy
            if move_accuracy < 80 and move_accuracy != 0:  # 0 accuracy means it doesn't miss
                logging.debug(f"Skipping {move_name} (low accuracy: {move_accuracy})")
                continue
                
            # Skip moves that don't match the Pokémon's attacking stat dominance
            if (physical_attacker and move_category != 0) or (not physical_attacker and move_category != 1):
                logging.debug(f"Skipping {move_name} (category mismatch: {move_category})")
                continue
            
            # Verify the move is in the Pokémon's learnset
            if levelup_data and egg_moves_data and tm_learnset_data:
                if not check_move_in_learnset(pokemon_species, move_name, level, levelup_data, egg_moves_data, tm_learnset_data):
                    logging.debug(f"Skipping {move_name} (not in learnset for {pokemon_species})")
                    continue
            
            # Categorize moves by type
            if move_type == primary_type:
                logging.debug(f"Adding {move_name} to primary STAB moves (type: {move_type}, power: {move_power})")
                primary_stab_moves.append((move_id, move_power))
            elif move_type == secondary_type:
                logging.debug(f"Adding {move_name} to secondary STAB moves (type: {move_type}, power: {move_power})")
                secondary_stab_moves.append((move_id, move_power))
            else:
                logging.debug(f"Adding {move_name} to other damaging moves (type: {move_type}, power: {move_power})")
                other_damaging_moves.append((move_id, move_power))
                
        except Exception as e:
            logging.error(f"Error processing move {move_id}: {e}")
    
    # Sort moves by power in descending order
    primary_stab_moves.sort(key=lambda x: x[1], reverse=True)
    secondary_stab_moves.sort(key=lambda x: x[1], reverse=True)
    other_damaging_moves.sort(key=lambda x: x[1], reverse=True)
    
    # Prioritize moves by type
    prioritized_moves = [move_id for move_id, _ in primary_stab_moves + secondary_stab_moves + other_damaging_moves]
    
    # Apply whitelist priority
    for move_id, move in enumerate(moves_data[:650]):
        if not move:
            continue
            
        move_name = move.name if hasattr(move, 'name') else move.get('name')
        if move_name in move_whitelist and move_id not in prioritized_moves:
            prioritized_moves.append(move_id)
    
    logging.debug(f"Found {len(prioritized_moves)} suitable moves for {pokemon_species}")
    return prioritized_moves
