#!/usr/bin/env python3
# Move Handler Tool
# A tool for modifying trainer Pokemon move configurations

import os
import sys
import argparse
import ndspy.rom
import ndspy.narc
import json
import logging
import random
from datetime import datetime
from construct import Container

# Import trainer data parsing functions
from trainer_data_parser import (
    read_trainer_names,
    read_trainer_data,
    map_gym_trainer_names_to_ids,
    rebuild_trainer_data,
    update_trainer_poke_count_field,
    GYM_TRAINERS,
    GYM_TRAINER_OVERRIDES,
    GYM_TRAINER_IDS,
    DEBUG_TRAINER_PARSING,
    trainer_pokemon_struct,
    trainer_pokemon_moves_struct
)

# Import Pokemon data
from pokemon_shared import read_mondata, read_pokemon_names

# Import move reader utilities
from move_reader_util import (
    read_moves,
    read_levelup_learnsets,
    read_egg_moves,
    read_tm_learnset,
    read_move_blacklist,
    read_move_whitelist,
    classify_pokemon_attacker_type,
    find_suitable_moves
)

# Define constants for trainer data types
TRAINER_DATA_TYPE_NOTHING = 0x00
TRAINER_DATA_TYPE_MOVES = 0x01
TRAINER_DATA_TYPE_ITEMS = 0x02

# Define Pokémon name mappings for shortened ROM names
POKEMON_NAME_MAPPINGS = {
    # Shortened ROM name : Full name in learnset data
    "Crabomnabl": "Crabominable",
    "Corviknite": "Corviknight",
    "Corvsquire": "Corvisquire",
    "Baraskewda": "Barraskewda",
    "Centskorch": "Centiskorch",
    "Polchgeist": "Polteageist",
    "Poltegeist": "Polteageist",
    "Kilowatrel": "Kilowattrel",
    "Flechinder": "Fletchinder",
    "Blacefalon": "Blacephalon",
    "Bramblgast": "Bramblin",
    "Stonjorner": "Stonjourner",
    "Hakamo-o": "Hakamo-o",
    "Kommo-o": "Kommo-o",
    "Jangmo-o": "Jangmo-o",
    "Chien-Pao": "Chien-Pao",
    "Ting-Lu": "Ting-Lu",
    "Chi-Yu": "Chi-Yu",
    "Ironbundle": "Iron Bundle",
    "Iron Neck": "Iron Thorns",
    "Iron Valor": "Iron Valiant",
    "SandyShock": "Sandy Shocks",
    "ScreamTail": "Scream Tail",
    "RoarinMoon": "Roaring Moon",
    "GouginFire": "Gouging Fire",
    "Mr. Mime": "Mr. Mime",
    "Mr. Rime": "Mr. Rime",
    "Mime Jr.": "Mime Jr.",
    "Squawkbily": "Squawkabilly",
    "Sirfetch'd": "Sirfetch'd",
    "Farfetch'd": "Farfetch'd",
    "Nidoran♀": "Nidoran-F",
    "Nidoran♂": "Nidoran-M",
    "Dudunspars": "Dudunsparce",
    # Add mappings for basic Pokemon
    "Caterpie": "CATERPIE",
    "Weedle": "WEEDLE",
    "Cyndaquil": "CYNDAQUIL",
    "Totodile": "TOTODILE",
    "Porygon-Z": "PORYGON_Z",
    "Mr. Mime": "MR_MIME",
    # Map "Unknown" to "UNOWN" according to species.h
    "Unknown": "UNOWN"
}

# Define paths for data files
BASE_TRAINER_NARC_PATH = 'a/0/5/5'
LEVELUPDATA_PATH = 'armips/data/levelupdata.s'
EGGMOVES_PATH = 'data/modern_egg_moves.json'
TM_LEARNSET_PATH = 'data/modern_tm_learnset.json'
MOVE_BLACKLIST_PATH = 'data/move_blacklist.txt'
MOVE_WHITELIST_PATH = 'data/move_whitelist.txt'

# Debug flag
DEBUG = True

def setup_logging(debug=False, log_to_file=False):
    """Set up logging configuration"""
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Configure logging
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    for handler in logger.handlers[:]: 
        logger.removeHandler(handler)
    
    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_to_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"move_handler_{timestamp}.log")
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)
        
        logging.info(f"Logging to file: {log_file}")
    
    return logger

def log_message(message):
    """Print a log message if debug is enabled"""
    if DEBUG:
        logging.debug(message)

def get_trainer_data_type(trainer):
    """
    Determine the data type of a trainer's Pokemon (with or without moves)
    
    Args:
        trainer: The trainer object to check
        
    Returns:
        int: The trainer data type flag
    """
    # Check if the trainer has Pokemon with moves
    if hasattr(trainer, 'pokemon') and trainer.pokemon and hasattr(trainer.pokemon[0], 'move1'):
        return TRAINER_DATA_TYPE_MOVES
    return TRAINER_DATA_TYPE_NOTHING

def convert_trainer_to_moves(trainer, default_moves=[1, 1, 1, 1], force_update=False):
    """
    Convert a trainer's Pokemon to have moves
    
    Args:
        trainer: The trainer object to modify
        default_moves: List of 4 move IDs to assign as default moves
        
    Returns:
        trainer: Updated trainer object
    """
    
    # Convert each Pokemon to have moves
    for i, pokemon in enumerate(trainer.pokemon):
        # Create a new Pokemon with moves structure
        new_pokemon = {
            "ivs": pokemon.ivs,
            "abilityslot": pokemon.abilityslot,
            "level": pokemon.level,
            "species": pokemon.species,
            "item": 0,  # No item by default
            "move1": default_moves[0],
            "move2": default_moves[1],
            "move3": default_moves[2],
            "move4": default_moves[3],
            "ballseal": pokemon.ballseal
        }
        
        # Replace the old Pokemon with the new one
        trainer.pokemon[i] = Container(**new_pokemon)
    
    # Update the trainer's data type flag if needed
    if hasattr(trainer, 'trainerdata'):
        trainer.trainerdata |= TRAINER_DATA_TYPE_MOVES
    else:
        trainer.trainerdata = TRAINER_DATA_TYPE_MOVES
        
    return trainer

def assign_fallback_move_by_type(moves_data, pokemon_types, move_slot):
    """
    Assign a fallback move based on the Pokemon's type. This is used when no suitable moves are found.
    
    Args:
        moves_data (list): List of move data
        pokemon_types (list): List of Pokemon's types [type1, type2]
        move_slot (int): Move slot index (0-3)
        
    Returns:
        int or None: Move ID or None if no suitable move found
    """
    # Common attack moves by type
    type_moves = {
        0: [],  # Normal
        1: [52, 98],  # Fighting - Karate Chop, Quick Attack
        2: [16, 17],  # Flying - Gust, Wing Attack
        3: [51, 89],  # Poison - Acid, Poison Powder
        4: [28, 111],  # Ground - Sand Attack, Dig
        5: [33, 88],  # Rock - Rock Throw, Rock Slide
        6: [],  # Bug
        7: [95, 122],  # Ghost - Night Shade, Lick
        8: [232, 231],  # Steel - Metal Claw, Iron Tail
        9: [52, 83],  # Fire - Ember, Fire Spin
        10: [55, 61],  # Water - Water Gun, Bubble
        11: [73, 75],  # Grass - Vine Whip, Razor Leaf
        12: [84, 85],  # Electric - Thunder Shock, Thunderbolt
        13: [93, 94],  # Psychic - Confusion, Psychic
        14: [58, 59],  # Ice - Ice Beam, Blizzard
        15: [82, 63],  # Dragon - Dragon Rage, Dragon Breath
        16: [180, 185],  # Dark - Faint Attack, Bite
        17: [118, 186]   # Fairy - Fairy Wind, Moonlight
    }
    
    # Basic moves for all types as fallback
    basic_moves = [33, 1, 40]  # Tackle, Pound, Scratch
    
    if not pokemon_types or not all(t >= 0 for t in pokemon_types):
        # If types are missing or invalid, use basic moves
        if move_slot < len(basic_moves):
            return basic_moves[move_slot]
        return None
    
    # Try to get a move for the primary type
    primary_type = pokemon_types[0]
    if primary_type in type_moves and type_moves[primary_type] and move_slot < len(type_moves[primary_type]):
        return type_moves[primary_type][move_slot]
    
    # If we have a second type and it's different from the first, try that
    if len(pokemon_types) > 1 and pokemon_types[1] != primary_type:
        secondary_type = pokemon_types[1]
        if secondary_type in type_moves and type_moves[secondary_type] and move_slot < len(type_moves[secondary_type]):
            return type_moves[secondary_type][move_slot]
    
    # Fallback to basic moves
    if move_slot < len(basic_moves):
        return basic_moves[move_slot]
    
    return None


def assign_smart_moves(trainer_data, moves_data, levelup_data, egg_moves_data, tm_learnset_data, move_blacklist, move_whitelist, min_level=1, max_level=100):
    """
    Assign smart moves to trainer Pokemon based on their species and level.
    
    Args:
        trainer_data: Dictionary mapping trainer IDs to trainer data
        moves_data: List of move data objects
        levelup_data: Dictionary mapping species to level-up moves
        egg_moves_data: Dictionary mapping species to egg moves
        tm_learnset_data: Dictionary mapping species to TM moves
        move_blacklist: List of move names to exclude
        move_whitelist: List of move names to prioritize
        min_level: Minimum Pokémon level to modify moves for (default: 1)
        max_level: Maximum Pokémon level to modify moves for (default: 100)
    """
    logging.info("Assigning smart moves to trainer Pokemon...")
    
    # Count how many Pokemon we processed
    total_pokemon = 0
    assigned_pokemon = 0  # Count of Pokemon that were successfully assigned moves
    assigned_moves = 0    # Total number of moves assigned
    failed_pokemon = 0    # Count of Pokemon that had errors during move assignment
    fallback_pokemon = 0  # Count of Pokemon that used fallback moves
    fallback_moves = 0    # Total number of fallback moves assigned
    basic_fallback_pokemon = 0  # Count of Pokemon that used basic fallback moves (like Tackle)
    unmapped_species = set()  # Track species that don't have a mapping
    
    # Log learnset data statistics
    logging.info(f"Loaded {len(levelup_data) if levelup_data else 0} species in level-up data")
    logging.info(f"Loaded {len(egg_moves_data) if egg_moves_data else 0} species in egg moves data")
    logging.info(f"Loaded {len(tm_learnset_data) if tm_learnset_data else 0} species in TM learnset data")
    
    # Sample a few species from each data source to verify format
    if levelup_data:
        sample_species = list(levelup_data.keys())[:3]
        logging.info(f"Sample species in levelup data: {sample_species}")
    
    if egg_moves_data:
        sample_species = list(egg_moves_data.keys())[:3]
        logging.info(f"Sample species in egg moves data: {sample_species}")
    
    # Iterate through each trainer
    for trainer_id, trainer in trainer_data.items():
        trainer_name = getattr(trainer, 'name', f'Unknown Trainer {trainer_id}')
        pokemon_count = len(trainer.pokemon) if trainer.pokemon else 0
        logging.info(f"Processing Trainer {trainer_id} ({trainer_name}) with {pokemon_count} Pokémon")
        
        # Skip if no pokemon
        if not trainer.pokemon or len(trainer.pokemon) == 0:
            logging.info(f"Trainer {trainer_id} has no Pokémon, skipping")
            continue
            
        # Process each pokemon
        for pokemon_idx, pokemon in enumerate(trainer.pokemon):
            total_pokemon += 1
            
            # Skip Pokémon outside the specified level range
            if pokemon.level < min_level or pokemon.level > max_level:
                species_name = getattr(pokemon, 'species_name', 'Unknown')
                logging.info(f"Trainer {trainer_id}, Pokémon {pokemon_idx+1}: {species_name} (Level {pokemon.level}) - outside level range {min_level}-{max_level}, skipping")
                continue
            
            try:
                # Get pokemon species name
                species_name = getattr(pokemon, 'species_name', 'Unknown')
                if species_name == 'Unknown' and hasattr(pokemon, 'get'):
                    species_name = pokemon.get('species_name', 'Unknown')
                
                # Apply name mapping for shortened ROM names
                original_species_name = species_name
                
                # Check if the species name is in our mapping dictionary
                if species_name in POKEMON_NAME_MAPPINGS:
                    lookup_species_name = POKEMON_NAME_MAPPINGS[species_name]
                    logging.debug(f"Mapped species name: {species_name} -> {lookup_species_name}")
                else:
                    lookup_species_name = species_name
                    # Track unmapped species to report at the end
                    unmapped_species.add(species_name)
                
                # Verify the species exists in levelup data
                normalized_species = lookup_species_name
                if not normalized_species.startswith("SPECIES_"):
                    normalized_species = "SPECIES_" + normalized_species.replace(" ", "_").upper()
                
                if normalized_species not in levelup_data:
                    error_msg = f"ERROR: Species {normalized_species} (original: {original_species_name}) not found in levelup data!"
                    logging.error(error_msg)
                    print(error_msg)
                    raise ValueError(f"Species {normalized_species} not found in levelup data. Check POKEMON_NAME_MAPPINGS dictionary.")
                
                # Get pokemon type and stats
                pokemon_types = []
                
                # Get type_1 with error handling
                if hasattr(pokemon, 'type_1') and pokemon.type_1 is not None:
                    pokemon_types.append(pokemon.type_1)
                else:
                    # Default to NORMAL type if missing
                    pokemon_types.append(0)  # Assuming 0 is NORMAL type
                    
                # Get type_2 with error handling
                if hasattr(pokemon, 'type_2') and pokemon.type_2 is not None and \
                   pokemon.type_2 != pokemon_types[0]:
                    pokemon_types.append(pokemon.type_2)
                
                # Get stats with error handling
                pokemon_stats = {}
                for stat in ['hp', 'attack', 'defense', 'speed', 'sp_attack', 'sp_defense']:
                    if hasattr(pokemon, stat):
                        pokemon_stats[stat] = getattr(pokemon, stat)
                    else:
                        # Default to 50 if missing
                        pokemon_stats[stat] = 50
                
                # Find suitable moves for this Pokémon
                logging.info(f"Trainer {trainer_id}, Pokémon {pokemon_idx+1}: Finding suitable moves for {original_species_name} (mapped to {lookup_species_name})")
                
                suitable_moves = find_suitable_moves(
                    moves_data,
                    lookup_species_name,
                    pokemon_types,
                    pokemon_stats,
                    pokemon.level,
                    levelup_data,
                    egg_moves_data,
                    tm_learnset_data,
                    move_blacklist,
                    move_whitelist
                )
                
                # Assign up to 4 moves
                move_count = 0
                assigned_any_moves = False
                
                # Check if pokemon has moves attribute
                if not hasattr(pokemon, 'moves'):
                    # Create moves list if it doesn't exist
                    pokemon.moves = [0, 0, 0, 0]  # Initialize with empty moves
                
                # Check if moves is a proper list or array
                if not hasattr(pokemon.moves, '__getitem__') or not hasattr(pokemon.moves, '__setitem__'):
                    # If moves isn't indexable, create a new list
                    pokemon.moves = [0, 0, 0, 0]  # Initialize with empty moves
                
                # Ensure moves has at least 4 slots
                while len(pokemon.moves) < 4:
                    pokemon.moves.append(0)
                
                if suitable_moves:
                    # Log the move names we're assigning
                    move_names = []
                    for i in range(min(4, len(suitable_moves))):
                        try:
                            move_id = suitable_moves[i]
                            pokemon.moves[i] = move_id
                            
                            # Get move name for logging
                            if move_id < len(moves_data) and moves_data[move_id]:
                                move_name = moves_data[move_id].name if hasattr(moves_data[move_id], 'name') else \
                                            moves_data[move_id].get('name', 'Unknown')
                                move_names.append(f"{move_name} (ID: {move_id})")
                            else:
                                move_names.append(f"Unknown (ID: {move_id})")
                            move_count += 1
                            assigned_any_moves = True
                        except (IndexError, TypeError, AttributeError) as e:
                            logging.warning(f"Trainer {trainer_id}, Pokémon {pokemon_idx+1}: Error setting move {i} for {original_species_name}: {str(e)}")
                    
                    logging.info(f"Trainer {trainer_id}, Pokémon {pokemon_idx+1}: Successfully assigned {move_count} moves to {original_species_name} (Level {pokemon.level}): {', '.join(move_names)}")
                    assigned_moves += move_count
                else:
                    # If we have no moves yet, try to assign fallback moves
                    if not assigned_any_moves:
                        logging.warning(f"Trainer {trainer_id}, Pokémon {pokemon_idx+1}: No suitable moves found for {original_species_name} (Level {pokemon.level}). Using fallback moves.")
                        fallback_pokemon += 1
                        
                        # Fallback to type-based moves
                        type_based_moves_assigned = False
                        if pokemon_types and len(pokemon_types) > 0:
                            for type_name in pokemon_types:
                                # Get moves of this type
                                moves_of_type = get_moves_by_type(moves_data, type_name)
                                
                                if moves_of_type and len(moves_of_type) > 0:
                                    # Use some basic type moves
                                    move_names = []
                                    fallback_count = 0
                                    
                                    for i, move_id in enumerate(moves_of_type[:4]):
                                        if i < 4: # Safety check
                                            pokemon.moves[i] = move_id
                                            fallback_count += 1
                                            
                                            # Get move name for logging
                                            if move_id < len(moves_data) and moves_data[move_id]:
                                                move_name = moves_data[move_id].name if hasattr(moves_data[move_id], 'name') else \
                                                            moves_data[move_id].get('name', 'Unknown')
                                                move_names.append(f"{move_name} (ID: {move_id})")
                                            else:
                                                move_names.append(f"Unknown (ID: {move_id})")
                                    
                                    type_based_moves_assigned = True
                                    logging.warning(f"Trainer {trainer_id}, Pokémon {pokemon_idx+1}: Assigned {fallback_count} {type_name}-type fallback moves to {original_species_name}: {', '.join(move_names)}")
                                    fallback_moves += fallback_count
                                    break
                        
                        # If we still don't have moves, use very basic fallbacks
                        if not type_based_moves_assigned:
                            logging.warning(f"Trainer {trainer_id}, Pokémon {pokemon_idx+1}: No type-based fallback moves found for {original_species_name}. Using basic fallbacks.")
                            basic_fallback_pokemon += 1
                            
                            # Very basic fallbacks - tackle, pound, etc.
                            basic_moves = [1, 2, 3, 4] # Move IDs for basic moves like tackle
                            move_names = []
                            fallback_count = 0
                            
                            for i, move_id in enumerate(basic_moves):
                                if i < 4: # Safety check
                                    pokemon.moves[i] = move_id
                                    fallback_count += 1
                                    
                                    # Get move name for logging
                                    if move_id < len(moves_data) and moves_data[move_id]:
                                        move_name = moves_data[move_id].name if hasattr(moves_data[move_id], 'name') else \
                                                    moves_data[move_id].get('name', 'Unknown')
                                        move_names.append(f"{move_name} (ID: {move_id})")
                                    else:
                                        move_names.append(f"Unknown (ID: {move_id})")
                            
                            logging.warning(f"Trainer {trainer_id}, Pokémon {pokemon_idx+1}: Assigned {fallback_count} basic fallback moves to {original_species_name}: {', '.join(move_names)}")
                            fallback_moves += fallback_count
                
                # If we couldn't find enough moves, pad with empty moves
                try:
                    for i in range(move_count, 4):
                        pokemon.moves[i] = 0
                except (IndexError, TypeError, AttributeError) as e:
                    logging.warning(f"Error padding moves for {species_name}: {str(e)}")
                    
            except Exception as e:
                # Get species name safely for error logging
                try:
                    species_name = getattr(pokemon, 'species_name', 'Unknown')
                except:
                    species_name = 'Unknown'
                
                logging.error(f"Failed to assign moves to Pokemon {species_name}: {str(e)}")
                failed_pokemon += 1
                continue
    
    logging.info(f"===== Move Assignment Summary =====")
    logging.info(f"Total trainers processed: {len(trainer_data)}")
    logging.info(f"Total Pokemon processed: {total_pokemon}")
    logging.info(f"Successfully assigned moves: {assigned_pokemon} Pokemon (with {assigned_moves} total moves)")
    logging.info(f"Used fallback moves: {fallback_pokemon} Pokemon (with {fallback_moves} fallback moves)")
    logging.info(f"Used basic fallback moves: {basic_fallback_pokemon} Pokemon")
    
    # Add success percentage calculation
    success_rate = (assigned_pokemon / total_pokemon) * 100 if total_pokemon > 0 else 0
    fallback_rate = (fallback_pokemon / total_pokemon) * 100 if total_pokemon > 0 else 0
    basic_fallback_rate = (basic_fallback_pokemon / total_pokemon) * 100 if total_pokemon > 0 else 0
    
    logging.info(f"Success rate: {success_rate:.2f}%")
    logging.info(f"Fallback rate: {fallback_rate:.2f}%")
    logging.info(f"Basic fallback rate: {basic_fallback_rate:.2f}%")
    logging.info(f"===============================")
    if failed_pokemon > 0:
        logging.error(f"Failed to assign moves to {failed_pokemon} Pokemon due to errors.")
    
    # Report any species that don't have mappings
    if unmapped_species:
        logging.warning(f"Found {len(unmapped_species)} species without mappings in POKEMON_NAME_MAPPINGS:")
        for species in sorted(unmapped_species):
            logging.warning(f"  Missing mapping: \"{species}\": \"{species}\",")
    
    logging.info(f"Assigned {assigned_moves} moves, used fallback for {fallback_pokemon} Pokémon, failed for {failed_pokemon} Pokémon")
    logging.info(f"Processed {total_pokemon} Pokémon in total")
    
    return trainer_data

def find_trainer_by_name(trainers, target_name):
    """
    Find a trainer by name from the trainers list
    
    Args:
        trainers: List of (trainer_id, trainer_object) tuples
        target_name: Name of the trainer to find
        
    Returns:
        tuple: (trainer_id, trainer_object) or None if not found
    """
    for trainer_id, trainer in trainers:
        if hasattr(trainer, 'name') and trainer.name == target_name:
            return (trainer_id, trainer)
    return None

def get_moves_by_type(move_data, type_id, category=None, min_power=40):
    """
    Get moves of a specific type, with optional filtering by category and power
    
    Args:
        move_data: Dictionary of move data
        type_id: Type ID to filter by
        category: Optional move category (0=Physical, 1=Special, 2=Status)
        min_power: Minimum move power required (default: 40)
        
    Returns:
        list: List of move IDs matching the criteria
    """
    matching_moves = []
    for move_id, move in enumerate(move_data):
        if move and move.type == type_id and move.power >= min_power:
            if category is None or move.category == category:
                matching_moves.append(move_id)
    
    return matching_moves

def get_pokemon_types(mondata, species_name):
    """
    Get the types of a Pokemon species from mondata
    
    Args:
        mondata: Dictionary of Pokemon data
        species_name: Species name
        
    Returns:
        tuple: (type1, type2) or None if not found
    """
    for pokemon in mondata:
        if pokemon and pokemon.name == species_name:
            return (pokemon.type1, pokemon.type2)
    return None

def generate_pokemon_name_mappings(mondata, species_h_path=None):
    """
    Generate comprehensive mappings between ROM Pokémon names and standard species names.
    
    This function creates mappings in two ways:
    1. From the mondata loaded from ROM
    2. From the species.h file if the path is provided
    
    Args:
        mondata: List of Pokémon data from ROM
        species_h_path: Path to species.h file (optional)
        
    Returns:
        dict: Dictionary mapping ROM species names to standard species names
    """
    # Start with our existing mappings
    mappings = dict(POKEMON_NAME_MAPPINGS)
    
    # Add mappings from mondata (ROM data)
    for pokemon in mondata:
        if pokemon and pokemon.name:
            # Skip if None or empty
            rom_name = pokemon.name
            
            # Some names might need special handling, but in general,
            # ROM names and standard names should match (e.g., PIKACHU = PIKACHU)
            standard_name = rom_name  # In most cases they match
            
            # Only add if not already in mappings
            if rom_name not in mappings:
                mappings[rom_name] = standard_name
    
    # If species.h path is provided, extract mappings from there too
    if species_h_path and os.path.exists(species_h_path):
        try:
            with open(species_h_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Look for #define SPECIES_XXX lines
            for line in lines:
                if line.strip().startswith('#define SPECIES_'):
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        species_name = parts[1]  # SPECIES_XXX
                        
                        # Extract the name part without SPECIES_ prefix
                        name_only = species_name[8:]
                        
                        # Add both capitalized and normal name as keys
                        normal_name = name_only.capitalize()
                        
                        # Only add if not already in mappings
                        if normal_name not in mappings:
                            mappings[normal_name] = species_name
                        
                        # Also add original case version (if different)
                        if name_only != normal_name and name_only not in mappings:
                            mappings[name_only] = species_name
        except Exception as e:
            logging.error(f"Error parsing species.h: {e}")
    
    return mappings

def get_species_name_by_id(species_id, mondata):
    """
    Convert a numeric species ID to a species name using mondata.
    
    Args:
        species_id: Numeric ID of the species from ROM data
        mondata: List of Pokémon data from the ROM
        
    Returns:
        str: Species name (e.g., 'BULBASAUR', 'PIKACHU') or 'Unknown' if not found
    """
    if species_id < len(mondata) and mondata[species_id] is not None:
        return mondata[species_id].name
    else:
        logging.warning(f"Species ID {species_id} not found in mondata")
        return "Unknown"

def process_trainer(rom, trainer_id, trainer, enable_moves=True, default_moves=[1, 1, 1, 1], force_update=False, 
                 use_smart_moves=False, move_data=None, mondata=None, levelup_data=None, 
                 egg_moves_data=None, tm_learnset_data=None, blacklist=None, whitelist=None):
    """
    Process a trainer to update their data type and potentially assign smart moves
    
    Args:
        rom: The ROM object
        trainer_id: ID of the trainer
        trainer: Trainer object
        enable_moves: True to add moves, False to remove moves
        default_moves: List of 4 move IDs to use as default moves
        force_update: If True, update all trainers regardless of current state
        use_smart_moves: If True, assign moves based on Pokémon stats, types and learnsets
        move_data: List of all move data (required for smart moves)
        mondata: Dictionary of Pokémon data (required for smart moves)
        levelup_data, egg_moves_data, tm_learnset_data: Learnset data sources
        blacklist, whitelist: Move blacklist and whitelist sets
        
    Returns:
        bool: True if changes were made, False otherwise
    """
    current_type = get_trainer_data_type(trainer)
    
    # Update trainer if they have no moves OR if force_update is True
    if enable_moves and (current_type == TRAINER_DATA_TYPE_NOTHING or force_update):
        # Get trainer name if available
        trainer_name = trainer.name if hasattr(trainer, 'name') else 'Unknown'
        
        # Show different message based on whether we're updating or adding
        if current_type == TRAINER_DATA_TYPE_MOVES and force_update:
            log_message(f"Updating moves for trainer {trainer_id} ({trainer_name})")
        else:
            log_message(f"Adding moves to trainer {trainer_id} ({trainer_name})")
        
        if use_smart_moves and move_data and mondata:
            # Use smart move assignment
            log_message(f"Using smart move assignment for trainer {trainer_id} ({trainer_name})")
            
            # First, assign species names to each Pokémon based on their species ID
            for pokemon in trainer.pokemon:
                # Get the species ID from the Pokémon data
                species_id = pokemon.species
                # Convert the ID to a species name using mondata
                pokemon.species_name = get_species_name_by_id(species_id, mondata)
                logging.debug(f"Assigned species name '{pokemon.species_name}' to Pokémon with ID {species_id}")
            
            # Create a trainer_data dictionary with just this trainer
            single_trainer_data = {trainer_id: trainer}
            
            # Call assign_smart_moves with the correct parameter order
            single_trainer_data = assign_smart_moves(single_trainer_data, move_data, levelup_data, egg_moves_data, 
                                        tm_learnset_data, blacklist, whitelist)
            
            # Get the updated trainer back
            trainer = single_trainer_data[trainer_id]
        else:
            # Use default move assignment
            trainer = convert_trainer_to_moves(trainer, default_moves, force_update=force_update)
        
        # Rebuild the trainer data
        new_data = rebuild_trainer_data(trainer)
        
        # Update the ROM with new data
        trainer_narc = rom.files[rom.filenames[BASE_TRAINER_NARC_PATH]]
        trainer_narc_data = ndspy.narc.NARC(trainer_narc)
        trainer_narc_data.files[trainer_id] = new_data
        rom.files[rom.filenames[BASE_TRAINER_NARC_PATH]] = trainer_narc_data.save()
        
        # Update the trainer Pokemon count field to match
        update_trainer_poke_count_field(rom, trainer_id, len(trainer.pokemon))
        
        return True
    
    return False

def main():
    """Main function for the move handler tool"""
    parser = argparse.ArgumentParser(description="Modify trainer Pokemon move configurations in HG/SS ROM.")
    parser.add_argument("rom_path", help="Path to the ROM file")
    parser.add_argument("--trainer", help="Trainer name or ID to modify")
    parser.add_argument("--all", action="store_true", help="Modify all trainers")
    parser.add_argument("--enable-moves", action="store_true", 
                       help="Enable custom moves for the trainer(s)")
    parser.add_argument("--default-moves", type=int, nargs=4, default=[1, 1, 1, 1],
                       help="Default moves to assign (4 move IDs)")
    parser.add_argument("--smart-moves", action="store_true",
                       help="Use smart move assignment based on Pokemon stats and types")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--log-file", action="store_true", help="Log output to file")
    parser.add_argument("--max-trainers", type=int, default=10, 
                       help="Maximum number of trainers to process for testing")
    args = parser.parse_args()
    
    # Set debug mode
    global DEBUG
    DEBUG = args.debug
    
    print("Starting script...")
    
    # Set up logging
    setup_logging(debug=args.debug, log_to_file=args.log_file)
    
    # Validate ROM path
    rom_path = args.rom_path
    if not os.path.exists(rom_path):
        print(f"Error: ROM file {rom_path} not found")
        sys.exit(1)
    
    # Open the ROM file
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Get base path for finding data files
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    # Read trainer names
    trainer_names = read_trainer_names(base_path)
    
    # Read trainer data
    trainers, trainer_narc_data = read_trainer_data(rom)
    
    # Read Pokemon data (for moves)
    logging.info("Reading Pokémon data...")
    pokemon_names = read_pokemon_names(base_path)
    mondata = read_mondata(rom, pokemon_names)
    
    # Generate comprehensive species name mappings
    species_h_path = os.path.join(base_path, "include", "constants", "species.h")
    if os.path.exists(species_h_path):
        logging.info(f"Generating comprehensive species mappings from {species_h_path}...")
        global POKEMON_NAME_MAPPINGS
        POKEMON_NAME_MAPPINGS = generate_pokemon_name_mappings(mondata, species_h_path)
        logging.info(f"Generated {len(POKEMON_NAME_MAPPINGS)} species mappings")
    else:
        logging.warning(f"Could not find species.h at {species_h_path}, using default mappings only")
    
    # Debug: Print the first 20 Pokémon IDs and names from mondata
    logging.info(f"Loaded {len(mondata)} Pokémon in mondata")
    logging.info("Sample Pokémon from mondata:")
    sample_count = min(20, len(mondata))
    for i, pokemon_data in enumerate(mondata[:sample_count]):
        if pokemon_data:
            logging.info(f"  ID {i}: {pokemon_data.name} (Types: {pokemon_data.type1}/{pokemon_data.type2})")
    
    # If smart moves are enabled, load additional data
    levelup_data = None
    egg_moves_data = None
    tm_learnset_data = None
    blacklist = None
    whitelist = None
    move_data = None
    
    if args.smart_moves:
        logging.info("Smart move generation enabled, loading additional data...")
        # Load move data from ROM
        move_data = read_moves(rom, base_path)
        logging.info(f"Loaded {len(move_data)} moves from ROM")
        
        # Read learnset data from files
        levelup_data = read_levelup_learnsets(os.path.join(base_path, LEVELUPDATA_PATH))
        egg_moves_data = read_egg_moves(os.path.join(base_path, EGGMOVES_PATH))
        tm_learnset_data = read_tm_learnset(os.path.join(base_path, TM_LEARNSET_PATH))
        
        # Read blacklist and whitelist
        blacklist = read_move_blacklist(os.path.join(base_path, MOVE_BLACKLIST_PATH))
        whitelist = read_move_whitelist(os.path.join(base_path, MOVE_WHITELIST_PATH))
    
    # Map gym trainer names to IDs for easier reference
    map_gym_trainer_names_to_ids(trainer_names)
    
    # Process trainers
    changes_made = False
    processed_count = 0
    modified_count = 0
    
    logging.info("Starting trainer processing...")
    
    # Process specific trainer by ID or name
    if args.trainer is not None and not args.all:
        # Try to parse as trainer ID
        try:
            trainer_id = int(args.trainer)
            # Find trainer with this ID
            trainer_found = False
            for tid, trainer_obj in trainers:
                if tid == trainer_id:
                    logging.info(f"Processing trainer {trainer_id} by ID")
                    print(f"Processing single trainer {trainer_id}...")
                    if process_trainer(rom, trainer_id, trainer_obj, args.enable_moves, args.default_moves, force_update=True,
                            use_smart_moves=args.smart_moves, move_data=move_data, mondata=mondata, 
                            levelup_data=levelup_data, egg_moves_data=egg_moves_data, 
                            tm_learnset_data=tm_learnset_data, blacklist=blacklist, whitelist=whitelist):
                        modified_count += 1
                    processed_count += 1
                    trainer_found = True
                    changes_made = True
                    break
                    
            if not trainer_found:
                logging.error(f"Trainer ID {trainer_id} not found")
                sys.exit(1)
        except ValueError:
            # Try as trainer name
            trainer_name = args.trainer.lower()
            logging.info(f"Looking for trainer '{trainer_name}' by name")
            found = False
            for tid, trainer_obj in trainers:
                if tid in trainer_names and trainer_names[tid].lower() == trainer_name:
                    logging.info(f"Found trainer {trainer_name} at ID {tid}")
                    print(f"Processing single trainer {tid}...")
                    if process_trainer(rom, tid, trainer_obj, args.enable_moves, args.default_moves, force_update=True,
                        use_smart_moves=args.smart_moves, move_data=move_data, mondata=mondata, 
                        levelup_data=levelup_data, egg_moves_data=egg_moves_data, 
                        tm_learnset_data=tm_learnset_data, blacklist=blacklist, whitelist=whitelist):
                        modified_count += 1
                    processed_count += 1
                    found = True
                    changes_made = True
                    break
            if not found:
                logging.error(f"Trainer '{trainer_name}' not found")
                sys.exit(1)
    # Process all trainers
    elif args.all:
        logging.info("Processing all trainers...")
        print(f"Processing up to {args.max_trainers} trainers for testing...")
        trainer_count = 0
        for trainer_id, trainer in trainers:
            if trainer_count >= args.max_trainers:
                print(f"Reached maximum trainer count ({args.max_trainers}), stopping.")
                break
                
            # Get trainer name if available
            trainer_name = trainer_names.get(trainer_id, "Unknown")
            print(f"Processing trainer ID {trainer_id} ({trainer_name})...")
            logging.debug(f"Processing trainer ID {trainer_id} ({trainer_name})")
            
            try:
                if process_trainer(rom, trainer_id, trainer, args.enable_moves, args.default_moves, force_update=True,
                    use_smart_moves=args.smart_moves, move_data=move_data, mondata=mondata, 
                    levelup_data=levelup_data, egg_moves_data=egg_moves_data, 
                    tm_learnset_data=tm_learnset_data, blacklist=blacklist, whitelist=whitelist):
                    modified_count += 1
                    changes_made = True
                processed_count += 1
                trainer_count += 1
                print(f"Finished processing trainer {trainer_id}")
            except Exception as e:
                print(f"Error processing trainer {trainer_id}: {e}")
                logging.error(f"Error processing trainer {trainer_id}: {e}")
                break
    elif not args.trainer and not args.all:
        logging.warning("No trainer specified and --all not used. Nothing to do.")
        parser.print_help()
        sys.exit(0)
    
    # Log final statistics
    logging.info(f"Total trainers processed: {processed_count}, Modified: {modified_count}")
    
    # Save the ROM with a descriptive name
    if changes_made:
        # Save the ROM file with a new name
        output_suffix = '_smart_moves.nds' if args.smart_moves else '_moves.nds'
        output_rom_name = os.path.splitext(rom_path)[0] + output_suffix
        rom.saveToFile(output_rom_name)
        logging.info(f"ROM saved as {output_rom_name}")
        logging.info(f"Processed {processed_count} trainers, modified {modified_count}")
    else:
        logging.info("No changes were made to the ROM")

# Path constants
BASE_TRAINER_NARC_PATH = "a/0/5/6"

if __name__ == "__main__":
    main()
