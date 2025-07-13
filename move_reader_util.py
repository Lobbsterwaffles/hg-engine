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
        move_name: Move name (e.g., "MOVE_HYDRO_PUMP")
        level: Pokémon's current level
        levelup_data: Level-up learnset data
        egg_moves_data: Egg moves data
        tm_learnset_data: TM learnset data
        
    Returns:
        bool: True if the move is learnable, False otherwise
    """
    import logging
    
    # Check level-up moves first
    if species_name in levelup_data:
        try:
            for learn_move_name, learn_level in levelup_data[species_name]:
                if learn_move_name == move_name and learn_level <= level:
                    logging.debug(f"{move_name} found in level-up learnset for {species_name} at level {learn_level}")
                    return True
        except Exception as e:
            logging.error(f"Error checking level-up learnset for {species_name}: {e}")
    else:
        logging.debug(f"{species_name} not found in level-up learnset data")
    
    # Check egg moves
    if species_name in egg_moves_data:
        try:
            if move_name in egg_moves_data[species_name]:
                logging.debug(f"{move_name} found in egg moves for {species_name}")
                return True
        except Exception as e:
            logging.error(f"Error checking egg moves for {species_name}: {e}")
    else:
        logging.debug(f"{species_name} not found in egg moves data")
    
    # Check TM learnset
    if species_name in tm_learnset_data:
        try:
            if move_name in tm_learnset_data[species_name]:
                logging.debug(f"{move_name} found in TM learnset for {species_name}")
                return True
        except Exception as e:
            logging.error(f"Error checking TM learnset for {species_name}: {e}")
    else:
        logging.debug(f"{species_name} not found in TM learnset data")
    
    logging.debug(f"{move_name} not found in any learnset for {species_name}")
    return False

def find_suitable_moves(species_name, pokemon_type1, pokemon_type2, level, attacker_type,
                   move_data, levelup_data, egg_moves_data, tm_learnset_data, blacklist, whitelist):
    """
    Find suitable STAB (Same Type Attack Bonus) moves for a Pokémon.
    
    Args:
        species_name: Species name (e.g., "SPECIES_FERALIGATR")
        pokemon_type1: Pokémon's primary type
        pokemon_type2: Pokémon's secondary type (if dual-typed)
        level: Pokémon's current level
        attacker_type: "Physical", "Special", or "Mixed"
        move_data: Dictionary of move data
        levelup_data, egg_moves_data, tm_learnset_data: Learnset data
        blacklist, whitelist: Move blacklist and whitelist sets
    
    Returns:
        List of up to 4 move names (e.g., ["MOVE_Tackle", "MOVE_WaterGun", ...])
    """
    import logging
    
    # Lists to store primary and secondary type moves
    primary_type_moves = []
    secondary_type_moves = []
    other_damaging_moves = []  # Non-STAB damaging moves as a backup
    
    logging.info(f"Finding moves for {species_name} - Type1: {pokemon_type1}, Type2: {pokemon_type2}, Level: {level}")
    logging.info(f"Attacker type: {attacker_type}")
    
    # Process each move to find suitable ones
    for move_id, move in enumerate(move_data):
        # Skip missing moves
        if move is None:
            continue
            
        # Get move properties
        move_name = move.name if hasattr(move, 'name') else ''
        move_type = move.type if hasattr(move, 'type') else 0
        move_power = move.power if hasattr(move, 'power') else 0
        move_accuracy = move.accuracy if hasattr(move, 'accuracy') else 0
        move_category = move.category if hasattr(move, 'category') else 0
        
        # Skip moves without names
        if not move_name:
            continue
            
        # Skip blacklisted moves
        if move_name in blacklist:
            logging.debug(f"{move_name} - SKIPPED: in blacklist")
            continue
            
        # Check if it's a damaging move (not status)
        if move_category == 0:  # STATUS
            logging.debug(f"{move_name} - SKIPPED: status move")
            continue
            
        # Check power range (min 50, max 110)
        if move_power < 50:
            logging.debug(f"{move_name} - SKIPPED: power too low ({move_power})")
            continue
        if move_power > 110:
            logging.debug(f"{move_name} - SKIPPED: power too high ({move_power})")
            continue
            
        # Check accuracy (≥80% or 0 which means always hits)
        if 0 < move_accuracy < 80:  
            logging.debug(f"{move_name} - SKIPPED: accuracy too low ({move_accuracy})")
            continue
            
        # Check if move category matches attacker type
        if attacker_type == "Physical" and move_category != 1:  # PHYSICAL
            logging.debug(f"{move_name} - SKIPPED: not physical move for physical attacker")
            continue
        if attacker_type == "Special" and move_category != 2:  # SPECIAL
            logging.debug(f"{move_name} - SKIPPED: not special move for special attacker")
            continue
        # Mixed attackers can use either type
        
        # Always include whitelisted moves that pass above checks
        if move_name in whitelist:
            logging.info(f"{move_name} - INCLUDED: in whitelist")
            if move_type == pokemon_type1:
                primary_type_moves.append(move_name)
            elif move_type == pokemon_type2 and pokemon_type2 != pokemon_type1:
                secondary_type_moves.append(move_name)
            else:
                other_damaging_moves.append(move_name)
            continue
            
        # Check if move is in learnset
        if not check_move_in_learnset(species_name, move_name, level, 
                                     levelup_data, egg_moves_data, tm_learnset_data):
            logging.debug(f"{move_name} - SKIPPED: not in learnset")
            continue
            
        # Move passed all checks - categorize it by type
        if move_type == pokemon_type1:
            logging.info(f"{move_name} - INCLUDED: primary type STAB move")
            primary_type_moves.append(move_name)
        elif move_type == pokemon_type2 and pokemon_type2 != pokemon_type1:
            logging.info(f"{move_name} - INCLUDED: secondary type STAB move")
            secondary_type_moves.append(move_name)
        else:
            logging.debug(f"{move_name} - INCLUDED: non-STAB damaging move (backup)")
            other_damaging_moves.append(move_name)
    
    # Now select up to 4 moves with priority
    final_moves = []
    
    # Priority 1: Primary type moves (up to 2)
    if primary_type_moves:
        logging.info(f"Primary type moves found: {len(primary_type_moves)}")
        final_moves.extend(primary_type_moves[:2])
    
    # Priority 2: Secondary type moves
    if len(final_moves) < 4 and secondary_type_moves:
        logging.info(f"Secondary type moves found: {len(secondary_type_moves)}")
        remaining = 4 - len(final_moves)
        final_moves.extend(secondary_type_moves[:remaining])
    
    # Priority 3: Other damaging moves
    if len(final_moves) < 4 and other_damaging_moves:
        logging.info(f"Other damaging moves found: {len(other_damaging_moves)}")
        remaining = 4 - len(final_moves)
        final_moves.extend(other_damaging_moves[:remaining])
    
    # If we have no moves at all, add Tackle as fallback
    if not final_moves:
        logging.warning(f"No suitable moves found for {species_name}, using Tackle/Pound as fallback")
        final_moves.append("MOVE_Tackle")
    
    # Make sure we return at most 4 moves
    final_moves = final_moves[:4]
    
    logging.info(f"Final moves selected for {species_name}: {final_moves}")
    return final_moves
