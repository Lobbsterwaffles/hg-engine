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

def assign_smart_moves(trainer, move_data, mondata, levelup_data, egg_moves_data, tm_learnset_data, blacklist, whitelist):
    """
    Assign smart moves to trainer's Pokemon based on stats, types, and learnsets
    
    Args:
        trainer: Trainer object
        move_data: List of all move data 
        mondata: List of Pokemon data
        levelup_data, egg_moves_data, tm_learnset_data: Learnset data sources
        blacklist, whitelist: Move blacklist and whitelist sets
        
    Returns:
        trainer: Updated trainer object with smart moves
    """
    
    # Convert each Pokemon to have moves
    for i, pokemon in enumerate(trainer.pokemon):
        # Log the Pokemon we're processing
        species_id = pokemon.species
        level = pokemon.level
        
        # Skip if species doesn't exist in mondata or is out of range
        if species_id >= len(mondata) or not mondata[species_id]:
            logging.warning(f"Pokemon species ID {species_id} not found in mondata, using default moves")
            continue
            
        # Get Pokemon data
        pokemon_data = mondata[species_id]
        species_name = f"SPECIES_{pokemon_data.name}"
        logging.info(f"Processing {species_name} (Level {level}) - ID: {species_id}")
        
        # Classify attacker type
        attacker_type = classify_pokemon_attacker_type(pokemon_data)
        logging.info(f"{species_name} classified as {attacker_type} attacker")
        
        # Find STAB moves - this returns a list of move names like "MOVE_Tackle"
        move_names = find_suitable_moves(
            species_name, pokemon_data.type1, pokemon_data.type2, level, attacker_type,
            move_data, levelup_data, egg_moves_data, tm_learnset_data, blacklist, whitelist
        )
        
        # Convert move names to move IDs
        selected_moves = []
        for move_name in move_names:
            # Find the move ID by its name
            move_id = 1  # Default to Tackle (move ID 1)
            for id, move in enumerate(move_data):
                if move is not None and hasattr(move, 'name') and move.name == move_name:
                    move_id = id
                    break
            selected_moves.append(move_id)
        
        # Make sure we have exactly 4 moves
        while len(selected_moves) < 4:
            selected_moves.append(1)  # Tackle as fallback
        
        # Log the selected moves
        move_names = [move_data[move_id].name if move_id < len(move_data) else f"Unknown Move {move_id}" 
                     for move_id in selected_moves]
        logging.info(f"Selected moves for {species_name}: {move_names}")
        
        # Create a new Pokemon with moves structure
        new_pokemon = {
            "ivs": pokemon.ivs,
            "abilityslot": pokemon.abilityslot,
            "level": pokemon.level,
            "species": pokemon.species,
            "item": 0,  # No item by default
            "move1": selected_moves[0],
            "move2": selected_moves[1],
            "move3": selected_moves[2],
            "move4": selected_moves[3],
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
            trainer = assign_smart_moves(trainer, move_data, mondata, levelup_data, egg_moves_data, 
                                        tm_learnset_data, blacklist, whitelist)
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
    
    args = parser.parse_args()
    
    # Set debug mode
    global DEBUG
    DEBUG = args.debug
    
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
        for trainer_id, trainer in trainers:
            # Get trainer name if available
            trainer_name = trainer_names.get(trainer_id, "Unknown")
            logging.debug(f"Processing trainer ID {trainer_id} ({trainer_name})")
            
            if process_trainer(rom, trainer_id, trainer, args.enable_moves, args.default_moves, force_update=True,
                use_smart_moves=args.smart_moves, move_data=move_data, mondata=mondata, 
                levelup_data=levelup_data, egg_moves_data=egg_moves_data, 
                tm_learnset_data=tm_learnset_data, blacklist=blacklist, whitelist=whitelist):
                modified_count += 1
                changes_made = True
            processed_count += 1
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
