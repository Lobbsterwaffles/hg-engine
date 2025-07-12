#!/usr/bin/env python3
# Smart Move Handler - Enhanced trainer Pokémon move management
# This tool enhances the original move handler with intelligent STAB move selection

import os
import sys
import json
import random
import logging
import argparse
from datetime import datetime
from construct import Container

import ndspy.rom
import ndspy.narc

# Import shared modules
from pokemon_shared import read_mondata, read_pokemon_names
from trainer_data_parser import (
    read_trainer_data,
    read_trainer_names,
    rebuild_trainer_data,
    update_trainer_poke_count_field
)
from Move_reader import read_moves

# Constants
TRAINER_DATA_TYPE_NOTHING = 0
TRAINER_DATA_TYPE_ITEMS = 1
TRAINER_DATA_TYPE_MOVES = 2
TRAINER_DATA_TYPE_BOTH = 3

# Types
TYPE_NORMAL = 0
TYPE_FIGHTING = 1
TYPE_FLYING = 2
TYPE_POISON = 3
TYPE_GROUND = 4
TYPE_ROCK = 5
TYPE_BUG = 6
TYPE_GHOST = 7
TYPE_STEEL = 8
TYPE_FIRE = 9
TYPE_WATER = 10
TYPE_GRASS = 11
TYPE_ELECTRIC = 12
TYPE_PSYCHIC = 13
TYPE_ICE = 14
TYPE_DRAGON = 15
TYPE_DARK = 16
TYPE_FAIRY = 17

# Move split types
SPLIT_PHYSICAL = 0
SPLIT_SPECIAL = 1
SPLIT_STATUS = 2

# Move selection criteria
MIN_MOVE_POWER = 50
MAX_MOVE_POWER = 84
MIN_MOVE_ACCURACY = 80

# Attack type determination threshold (20%)
ATTACK_DIFFERENCE_THRESHOLD = 0.2

# Setup logging
def setup_logging(debug=False, log_file=False):
    """
    Set up logging for the smart move handler
    
    Args:
        debug: Enable debug logging
        log_file: Save logs to a file
    """
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Create logs directory if it doesn't exist
    if log_file and not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Set up logging format
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Configure logging
    if log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/smart_move_handler_{timestamp}.log"
        logging.basicConfig(level=log_level, format=log_format,
                           handlers=[
                               logging.FileHandler(log_filename),
                               logging.StreamHandler(sys.stdout)
                           ])
    else:
        logging.basicConfig(level=log_level, format=log_format)
    
    logging.info("Smart Move Handler Started")

# Load move blacklist and whitelist
def load_move_lists(base_path):
    """
    Load move blacklist and whitelist from JSON files
    
    Args:
        base_path: Base path to the project
        
    Returns:
        blacklist: List of blacklisted move IDs
        whitelist: List of whitelisted move IDs
    """
    blacklist_path = os.path.join(base_path, "move_lists", "blacklist.json")
    whitelist_path = os.path.join(base_path, "move_lists", "whitelist.json")
    
    blacklist = []
    whitelist = []
    
    # Load blacklist if it exists
    if os.path.exists(blacklist_path):
        try:
            with open(blacklist_path, 'r') as f:
                blacklist_data = json.load(f)
                blacklist = [move["move_id"] for move in blacklist_data]
                logging.info(f"Loaded {len(blacklist)} moves in blacklist")
        except Exception as e:
            logging.error(f"Error loading blacklist: {e}")
            blacklist = []
    else:
        logging.warning(f"Blacklist file not found at {blacklist_path}")
    
    # Load whitelist if it exists
    if os.path.exists(whitelist_path):
        try:
            with open(whitelist_path, 'r') as f:
                whitelist_data = json.load(f)
                whitelist = [move["move_id"] for move in whitelist_data]
                logging.info(f"Loaded {len(whitelist)} moves in whitelist")
        except Exception as e:
            logging.error(f"Error loading whitelist: {e}")
            whitelist = []
    else:
        logging.warning(f"Whitelist file not found at {whitelist_path}")
    
    return blacklist, whitelist

# Read level-up learnset data
def read_level_up_data(base_path):
    """
    Read level-up learnset data for all Pokémon
    
    Args:
        base_path: Base path to the project
    
    Returns:
        Dictionary mapping Pokémon species ID to list of (level, move_id) tuples
    """
    levelup_path = os.path.join(base_path, "armips", "data", "levelupdata.s")
    levelup_data = {}
    
    # First, load species names to IDs mapping
    species_ids = {}
    species_path = os.path.join(base_path, "armips", "data", "mondata.s")
    
    try:
        with open(species_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('mondata SPECIES_'):
                    parts = line.split('SPECIES_')[1].split(',')
                    species_name = parts[0].strip()
                    # Remove quotes if present
                    if len(parts) > 1:
                        species_id = len(species_ids)  # Use sequential numbering
                        species_ids[species_name] = species_id
    except Exception as e:
        logging.error(f"Error reading species data: {e}")
    
    logging.info(f"Mapped {len(species_ids)} Pokémon species names to IDs")
    
    # Now read move names to IDs mapping
    move_ids = {}
    moves_path = os.path.join(base_path, "armips", "data", "moves.s")
    
    try:
        with open(moves_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('movedata MOVE_'):
                    parts = line.split('MOVE_')[1].split(',')
                    move_name = parts[0].strip()
                    # Remove quotes if present
                    if len(parts) > 1:
                        move_id = len(move_ids) + 1  # Use sequential numbering starting from 1
                        move_ids[move_name] = move_id
    except Exception as e:
        logging.error(f"Error reading move data: {e}")
    
    logging.info(f"Mapped {len(move_ids)} move names to IDs")
    
    # Now read the level-up data
    current_species = None
    current_moves = []
    
    try:
        with open(levelup_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Check for new Pokémon definition
                if line.startswith('levelup SPECIES_'):
                    # Save previous Pokémon data if exists
                    if current_species is not None and current_species in species_ids:
                        species_id = species_ids[current_species]
                        levelup_data[species_id] = current_moves.copy()
                    
                    # Extract species name
                    species_name = line.split('SPECIES_')[1].strip()
                    current_species = species_name
                    current_moves = []
                
                # Check for move definition
                elif line.startswith('    learnset MOVE_'):
                    parts = line.split(',')
                    if len(parts) >= 2:
                        move_name = parts[0].strip().split('MOVE_')[1].strip()
                        level = int(parts[1].strip())
                        if move_name in move_ids:
                            move_id = move_ids[move_name]
                            current_moves.append((level, move_id))
                        else:
                            logging.debug(f"Move {move_name} not found in move ID mapping")
                
                # Check for end of Pokémon definition
                elif line.startswith('    terminatelearnset'):
                    if current_species is not None and current_species in species_ids:
                        species_id = species_ids[current_species]
                        levelup_data[species_id] = current_moves.copy()
                    current_species = None
                    current_moves = []
                    
        logging.info(f"Loaded level-up data for {len(levelup_data)} Pokémon species")
        
    except Exception as e:
        logging.error(f"Error reading level-up data: {e}")
    
    return levelup_data

# Read Egg Move data
def read_egg_moves(base_path):
    """
    Read egg move data for all Pokémon
    
    Args:
        base_path: Base path to the project
    
    Returns:
        Dictionary mapping Pokémon species ID to list of move IDs
    """
    egg_move_path = os.path.join(base_path, "data", "modern_egg_moves.json")
    egg_moves = {}
    
    # First, load species name to ID mapping
    species_ids = {}
    species_path = os.path.join(base_path, "armips", "data", "mondata.s")
    
    try:
        with open(species_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('mondata SPECIES_'):
                    parts = line.split('SPECIES_')[1].split(',')
                    species_name = parts[0].strip()
                    species_id = len(species_ids)  # Use sequential numbering
                    species_ids[species_name] = species_id
    except Exception as e:
        logging.error(f"Error reading species data for egg moves: {e}")
    
    logging.info(f"Mapped {len(species_ids)} Pokémon species names to IDs for egg moves")
    
    # Now read move names to IDs mapping
    move_ids = {}
    moves_path = os.path.join(base_path, "armips", "data", "moves.s")
    
    try:
        with open(moves_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('movedata MOVE_'):
                    parts = line.split('MOVE_')[1].split(',')
                    move_name = parts[0].strip()
                    move_id = len(move_ids) + 1  # Use sequential numbering starting from 1
                    move_ids[move_name] = move_id
    except Exception as e:
        logging.error(f"Error reading move data for egg moves: {e}")
    
    # Now read the egg move data
    try:
        with open(egg_move_path, 'r') as f:
            egg_moves_json = json.load(f)
        
        # Process the JSON data
        for species_name, move_list in egg_moves_json.items():
            # Strip "SPECIES_" prefix if present
            if species_name.startswith("SPECIES_"):
                species_name = species_name[8:]
                
            # Try to find the species ID
            if species_name in species_ids:
                species_id = species_ids[species_name]
                move_id_list = []
                
                for move_name in move_list:
                    # Strip "MOVE_" prefix if present
                    if move_name.startswith("MOVE_"):
                        move_name = move_name[5:]
                        
                    # Try to find the move ID
                    if move_name in move_ids:
                        move_id_list.append(move_ids[move_name])
                    else:
                        logging.debug(f"Move {move_name} not found in move ID mapping for egg moves")
                
                if move_id_list:  # Only add if there are valid moves
                    egg_moves[species_id] = move_id_list
            else:
                logging.debug(f"Species {species_name} not found in species ID mapping for egg moves")
        
        logging.info(f"Loaded egg move data for {len(egg_moves)} Pokémon species")
        
    except Exception as e:
        logging.error(f"Error reading egg move data: {e}")
    
    return egg_moves

# Read TM learnset data
def read_tm_learnset_data(base_path):
    """
    Read TM learnset data from JSON file
    
    Args:
        base_path: Base path to the project
    
    Returns:
        Dictionary mapping Pokémon species ID to list of move IDs
    """
    tm_learnset_path = os.path.join(base_path, "data", "modern_tm_learnset.json")
    tm_learnset = {}
    
    # First, load species name to ID mapping
    species_ids = {}
    species_path = os.path.join(base_path, "armips", "data", "mondata.s")
    
    try:
        with open(species_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('mondata SPECIES_'):
                    parts = line.split('SPECIES_')[1].split(',')
                    species_name = parts[0].strip()
                    species_id = len(species_ids)  # Use sequential numbering
                    species_ids[species_name] = species_id
    except Exception as e:
        logging.error(f"Error reading species data for TM learnset: {e}")
    
    logging.info(f"Mapped {len(species_ids)} Pokémon species names to IDs for TM learnset")
    
    # Now read move names to IDs mapping
    move_ids = {}
    moves_path = os.path.join(base_path, "armips", "data", "moves.s")
    
    try:
        with open(moves_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('movedata MOVE_'):
                    parts = line.split('MOVE_')[1].split(',')
                    move_name = parts[0].strip()
                    move_id = len(move_ids) + 1  # Use sequential numbering starting from 1
                    move_ids[move_name] = move_id
    except Exception as e:
        logging.error(f"Error reading move data for TM learnset: {e}")
    
    # Now read the TM learnset data
    try:
        with open(tm_learnset_path, 'r') as f:
            tm_learnset_json = json.load(f)
        
        # Process the JSON data
        for species_str, move_list in tm_learnset_json.items():
            # TM learnset uses species IDs directly as strings
            try:
                species_id = int(species_str)
                move_id_list = []
                
                for move_str in move_list:
                    try:
                        # TM learnset uses move IDs directly as strings
                        move_id = int(move_str)
                        move_id_list.append(move_id)
                    except ValueError:
                        logging.debug(f"Invalid move ID {move_str} in TM learnset for species {species_id}")
                
                if move_id_list:  # Only add if there are valid moves
                    tm_learnset[species_str] = move_id_list
            except ValueError:
                logging.debug(f"Invalid species ID {species_str} in TM learnset")
        
        logging.info(f"Loaded TM learnset data for {len(tm_learnset)} Pokémon species")
        
    except Exception as e:
        logging.error(f"Error reading TM learnset data: {e}")
    
    return tm_learnset

# ... (rest of the code remains the same)

# Main function
def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Smart Move Handler")
    parser.add_argument("rom_path", help="Path to the ROM file")
    parser.add_argument("--trainer", help="Trainer ID or name to process")
    parser.add_argument("--all", action="store_true", help="Process all trainers")
    parser.add_argument("--force-update", action="store_true", help="Force update moves even if the trainer Pokemon already has moves")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-file", action="store_true", help="Save log to file")
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    
    if args.log_file:
        log_filename = f"smart_move_handler_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(level=log_level, format=log_format, filename=log_filename, filemode="w")
        print(f"Logging to {log_filename}")
    else:
        logging.basicConfig(level=log_level, format=log_format)
    
    try:
        # Load ROM
        with open(args.rom_path, "rb") as f:
            rom_data = f.read()
            rom = ndspy.rom.NintendoDSRom(rom_data)
            
        # Get base path (directory of the script)
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Load move lists
        blacklist, whitelist = load_move_lists(base_path)
        
        # Read level-up data
        levelup_data = read_level_up_data(base_path)
        
        # Read egg move data
        egg_move_data = read_egg_moves(base_path)
        
        # Read TM learnset data
        tm_learnset_data = read_tm_learnset_data(base_path)
        
        # Read trainer data
        trainers, trainer_narc_data = trainer_data_parser.read_trainer_data(rom)
        trainer_names = trainer_data_parser.read_trainer_names(rom)
        
        # Load Pokémon base stats
        pokemon_data = pokemon_shared.load_pokemon_stats(base_path)
        logging.info(f"Loaded base stats for {len(pokemon_data)} Pokémon species")
        
        # Load move data
        move_data = Move_reader.load_move_data(base_path)
        logging.info(f"Loaded data for {len(move_data)} moves")
        
        # Process trainers
        processed_count = 0
        modified_count = 0
        changes_made = False
        
        # Process specific trainer
        if args.trainer:
            trainer_name = args.trainer
            found = False
            
            # Try to parse as integer (trainer ID)
            try:
                trainer_id = int(trainer_name)
                for tid, trainer in trainers:
                    if tid == trainer_id:
                        logging.info(f"Processing trainer ID {trainer_id} ({trainer_names.get(trainer_id, 'Unknown')})")
                        if process_trainer(rom, trainer_id, trainer, 
                                          pokemon_data, move_data,
                                          levelup_data, egg_move_data, tm_learnset_data,
                                          blacklist, whitelist, args.force_update):
                            modified_count += 1
                            changes_made = True
                        processed_count += 1
                        found = True
                        break
            except ValueError:
                # Not an integer, treat as trainer name
                for trainer_id, trainer in trainers:
                    if trainer_id in trainer_names and trainer_names[trainer_id].lower() == trainer_name.lower():
                        logging.info(f"Processing trainer {trainer_names[trainer_id]} (ID: {trainer_id})")
                        if process_trainer(rom, trainer_id, trainer, 
                                          pokemon_data, move_data,
                                          levelup_data, egg_move_data, tm_learnset_data,
                                          blacklist, whitelist, args.force_update):
                            modified_count += 1
                            changes_made = True
                        processed_count += 1
                        found = True
                        break
                
            if not found:
                logging.error(f"Trainer '{trainer_name}' not found")
        
        # Process all trainers
        elif args.all:
            for trainer_id, trainer in trainers:
                # Get trainer name if available
                trainer_name = trainer_names.get(trainer_id, "Unknown")
                logging.debug(f"Processing trainer ID {trainer_id} ({trainer_name})")
                
                if process_trainer(rom, trainer_id, trainer, 
                                  pokemon_data, move_data,
                                  levelup_data, egg_move_data, tm_learnset_data,
                                  blacklist, whitelist, args.force_update):
                    modified_count += 1
                    changes_made = True
                processed_count += 1
        
        else:
            logging.error("No trainers specified. Use --trainer or --all")
            return
        
        logging.info(f"Total trainers processed: {processed_count}, Modified: {modified_count}")
        
        # Save the ROM if changes were made
        if changes_made:
            # Add '_smart_moves' suffix to the ROM filename
            rom_path = args.rom_path
            rom_dir, rom_filename = os.path.split(rom_path)
            rom_name, rom_ext = os.path.splitext(rom_filename)
            new_rom_path = os.path.join(rom_dir, f"{rom_name}_smart_moves{rom_ext}")
            
            rom.saveToFile(new_rom_path)
            logging.info(f"ROM saved to {new_rom_path}")
            
        logging.info("Smart Move Handler Finished")
        print(f"Total trainers processed: {processed_count}")
        
    except Exception as e:
        logging.error(f"Error in Smart Move Handler: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
