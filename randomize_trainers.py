from construct import *
import random
import os
import re
import argparse
import sys

import ndspy.rom
import ndspy.narc

# Import our gym type handler
from gym_type_handler import read_gym_types, get_trainer_gym_type, select_themed_replacement

# Import shared Pokemon data and utilities
from pokemon_shared import (
    SPECIAL_POKEMON,
    mondata_struct,
    parse_mondata,
    build_mondata,
    read_mondata,
    read_pokemon_names,
    find_replacements
)

# Import move reader to use move data
from Move_reader import read_moves

# Import team size adjustment functions
from randomizer_functions import max_team_size_bosses

# Import special Pokemon handlers
from special_pokemon_handler import apply_special_pokemon

# Direct parsing approach for hge.nds
# Based on the ROM analysis, we need a different approach

# Pokémon entry structure (each Pokémon is 8 bytes) - Fixed alignment
trainer_pokemon_struct = Struct(
    "ivs" / Int8ul,             # 1 byte - IVs
    "abilityslot" / Int8ul,     # 1 byte - Ability slot
    "level" / Int16ul,          # 2 bytes - Level (halfword)
    "species" / Int16ul,        # 2 bytes - Species ID (halfword)
    "ballseal" / Int16ul,       # 2 bytes - Ball seal (halfword, not byte!)
)

# Pokémon with moves structure (20 bytes total)
trainer_pokemon_moves_struct = Struct(
    "ivs" / Int8ul,             # 1 byte - IVs
    "abilityslot" / Int8ul,     # 1 byte - Ability slot
    "level" / Int16ul,          # 2 bytes - Level (halfword)
    "species" / Int16ul,        # 2 bytes - Species ID (halfword)
    "item" / Int16ul,           # 2 bytes - Held item
    "move1" / Int16ul,          # 2 bytes - Move 1
    "move2" / Int16ul,          # 2 bytes - Move 2
    "move3" / Int16ul,          # 2 bytes - Move 3
    "move4" / Int16ul,          # 2 bytes - Move 4
    "ballseal" / Int16ul,       # 2 bytes - Ball seal (halfword)
)

# In hge.nds, trainers seem to be stored without the standard header
# We'll directly parse the Pokémon entries instead of relying on nummons

# These functions are now imported from pokemon_shared.py

# Debug switch - set to True to enable detailed hex debugging
DEBUG_TRAINER_PARSING = False

# Move ID constants
SPLASH_MOVE_ID = 150  # Move ID for Splash
BASE_TRAINER_NARC_PATH = "a/0/5/6"

# Gym trainer data organized by location
GYM_TRAINERS = {
    "Violet City": ["Falkner", "Abe", "Rod"],
    "Azalea Town": ["Bugsy", "Al", "Benny", "Amy & Mimi"],
    "Goldenrod City": ["Victoria", "Samantha", "Carrie", "Cathy", "Whitney"],
    "Ecruteak City": ["Georgina", "Grace", "Edith", "Martha", "Morty"],
    "Cianwood City": ["Yoshi", "Lao", "Lung", "Nob", "Chuck"],
    "Olivine City": ["Jasmine"],
    "Mahogany Town": ["Pryce", "Diana", "Patton", "Deandre", "Jill", "Gerardo"],
    "Blackthorn City": ["Paulo", "Lola", "Cody", "Fran", "Mike", "Clair"],
    "Pewter City": ["Jerry", "Edwin", "Brock"],
    "Cerulean City": ["Parker", "Eddie", "Diana", "Joy", "Briana", "Misty"],
    "Vermillion City": ["Horton", "Vincent", "Gregory", "Lt. Surge"],
    "Celadon City": ["Jo & Zoe", "Michelle", "Tanya", "Julia", "Erika"],
    "Fuchsia City": ["Cindy", "Barry", "Alice", "Linda", "Janine"],
    "Saffron City": ["Rebecca", "Jared", "Darcy", "Franklin", "Sabrina"],
    "Seafoam Islands": ["Lowell", "Daniel", "Cary", "Linden", "Waldo", "Merle", "Blaine"],
    "Viridian City": ["Arabella", "Salma", "Bonita", "Elan & Ida", "Blue"],
    "Elite Four": ["Will", "Koga", "Bruno", "Karen", "Lance"]
}

# Override dictionary for duplicate trainer names
# Format: (location, trainer_name): trainer_id
GYM_TRAINER_OVERRIDES = {
    ("Mahogany Town", "Diana"): 480,  # Diana in Mahogany Town
    ("Cerulean City", "Diana"): 297,  # Diana in Cerulean City
    # Add more overrides here as needed
}

# Dictionary to store gym trainer name to ID mapping
GYM_TRAINER_IDS = {}

def map_gym_trainer_names_to_ids(trainer_names):
    """
    Create a mapping from gym trainer names to their numeric IDs.
    
    Args:
        trainer_names: Dictionary mapping trainer IDs to names (from read_trainer_names)
        
    Returns:
        Dictionary mapping gym locations to lists of (trainer_name, trainer_id) tuples
        
    Raises:
        ValueError: If any gym trainer name cannot be matched to a trainer ID
    """
    # Create a reverse mapping from names to IDs
    name_to_id = {}
    for trainer_id, name in trainer_names.items():
        name_to_id[name] = trainer_id
    
    # Create a mapping for gym trainers
    gym_trainer_ids = {}
    missing_trainers = []
    
    # Track duplicate trainer names
    all_trainer_locations = {}  # Maps trainer_name to list of locations where it appears
    
    # First pass: gather all occurrences of each trainer name
    for location, trainers in GYM_TRAINERS.items():
        for trainer_name in trainers:
            if trainer_name not in all_trainer_locations:
                all_trainer_locations[trainer_name] = []
            all_trainer_locations[trainer_name].append(location)
    
    # Find duplicate trainer names (appear in more than one location)
    duplicate_trainers = []
    for trainer_name, locations in all_trainer_locations.items():
        if len(locations) > 1:
            duplicate_trainers.append((trainer_name, locations))
    
    # If we found duplicates that aren't in the override dictionary, warn the user
    unhandled_duplicates = []
    for trainer_name, locations in duplicate_trainers:
        has_override = all((location, trainer_name) in GYM_TRAINER_OVERRIDES 
                          for location in locations)
        if not has_override:
            unhandled_duplicates.append((trainer_name, locations))
    
    if unhandled_duplicates:
        error_msg = "Found duplicate trainer names without overrides:\n"
        for trainer_name, locations in unhandled_duplicates:
            error_msg += f"  - {trainer_name} appears in: {', '.join(locations)}\n"
        error_msg += "\nPlease add overrides for these trainers in the GYM_TRAINER_OVERRIDES dictionary."
        raise ValueError(error_msg)
    
    # Second pass: map trainer names to IDs using overrides where applicable
    for location, trainers in GYM_TRAINERS.items():
        gym_trainer_ids[location] = []
        for trainer_name in trainers:
            # Check if there's an override for this trainer
            if (location, trainer_name) in GYM_TRAINER_OVERRIDES:
                # Use the override ID
                trainer_id = GYM_TRAINER_OVERRIDES[(location, trainer_name)]
            else:
                # Try to find an exact match
                trainer_id = name_to_id.get(trainer_name)
                
                # If no exact match, try case-insensitive match
                if trainer_id is None:
                    for name, id in name_to_id.items():
                        if name.lower() == trainer_name.lower():
                            trainer_id = id
                            break
                
                # If still no match, try partial match (for names like "Lt. Surge" vs "LtSurge")
                if trainer_id is None:
                    for name, id in name_to_id.items():
                        # Remove spaces and punctuation for comparison
                        clean_name = ''.join(c for c in name if c.isalnum()).lower()
                        clean_trainer_name = ''.join(c for c in trainer_name if c.isalnum()).lower()
                        
                        if clean_name == clean_trainer_name or \
                           clean_name in clean_trainer_name or \
                           clean_trainer_name in clean_name:
                            trainer_id = id
                            break
            
            # If we still couldn't find a match, add to the list of missing trainers
            if trainer_id is None:
                missing_trainers.append((location, trainer_name))
            
            gym_trainer_ids[location].append((trainer_name, trainer_id))
    
    # If any trainers couldn't be found, raise an error
    if missing_trainers:
        error_msg = "Could not find the following gym trainers in the ROM:\n"
        for location, trainer in missing_trainers:
            error_msg += f"  - {trainer} (in {location})\n"
        error_msg += "\nPlease check the trainer names and make sure they match the names in the ROM."
        raise ValueError(error_msg)
    
    # Update the global dictionary
    global GYM_TRAINER_IDS
    GYM_TRAINER_IDS = gym_trainer_ids
    
    return gym_trainer_ids

def read_trainer_names(base_path):
    """Read trainer names if available"""
    trainer_names = {}
    try:
        # Read trainer names from the assembly file using regex
        trainer_file = os.path.join(base_path, "armips/data/trainers/trainers.s")
        with open(trainer_file, "r", encoding="utf-8") as f:
            pattern = r"trainerdata\s+(\d+),\s+\"([^\"]+)\""
            for line in f:
                match = re.search(pattern, line)
                if match:
                    idx = int(match.group(1))
                    name = match.group(2)
                    trainer_names[idx] = name
        return trainer_names
    except FileNotFoundError:
        # If file doesn't exist, return empty dict
        return {}

def read_trainer_data(rom):
    """Read all trainer data from ROM"""
    narc_file_id = rom.filenames.idOf("a/0/5/6")
    trainer_narc = rom.files[narc_file_id]
    trainer_narc_data = ndspy.narc.NARC(trainer_narc)
    
    # Load the trainers.s file to get the expected number of Pokémon for each trainer
    trainer_pokemon_counts = {}
    try:
        with open("armips/data/trainers/trainers.s", "r", encoding="utf-8") as f:
            current_trainer = None
            for line in f:
                # Look for trainerdata lines to get trainer ID
                if "trainerdata" in line and "," in line:
                    try:
                        trainer_id = int(line.split("trainerdata")[1].split(",")[0].strip())
                        current_trainer = trainer_id
                    except:
                        pass
                # Look for nummons to get the number of Pokémon
                elif current_trainer is not None and "nummons" in line:
                    try:
                        num = int(line.split("nummons")[1].strip())
                        trainer_pokemon_counts[current_trainer] = num
                    except:
                        pass
        print(f"Loaded Pokémon counts for {len(trainer_pokemon_counts)} trainers from trainers.s")
    except Exception as e:
        print(f"Error loading trainer.s file: {e}")
        print("Will try to auto-detect Pokémon count from binary data")
    
    trainers = []
    for i, data in enumerate(trainer_narc_data.files):
        # Create a Container object to store trainer data
        from construct import Container
        trainer = Container()
        
        # For HG Engine, we need to parse the data differently
        # Each trainer entry seems to be just a list of Pokémon
        
        # First, set some default values
        trainer.trainerdata = 0  # Assume standard type
        trainer.trainerclass = 0
        trainer.battletype = 0
        trainer.nummons = 0
        trainer.items = [0, 0, 0, 0]
        trainer.ai_flags = 0
        trainer.padding = 0
        trainer.pokemon = []
        
        # Get the expected number of Pokémon for this trainer
        expected_pokemon = trainer_pokemon_counts.get(i, 0)
        
        # Detect if this trainer has Pokémon with moves based on data length
        # Each Pokémon with moves takes 20 bytes, without moves takes 8 bytes
        has_moves = False
        pokemon_size = 8  # Default size without moves
        
        if len(data) == 0:
            # Empty trainer, skip
            trainers.append((i, trainer))
            continue
        
        # Determine format based on expected Pokemon count and data size
        # NOTE: Pokemon with moves = 18 bytes, without moves = 8 bytes
        if expected_pokemon > 0:
            # Check if the data size matches expected count with moves (18 bytes each)
            if len(data) == expected_pokemon * 18:
                has_moves = True
                pokemon_size = 18
            # Check if data size matches expected count without moves (8 bytes each)
            elif len(data) == expected_pokemon * 8:
                has_moves = False
                pokemon_size = 8
            # If data doesn't match exactly, prefer moves format if closer to expected*18
            else:
                diff_with_moves = abs(len(data) - (expected_pokemon * 18))
                diff_without_moves = abs(len(data) - (expected_pokemon * 8))
                if diff_with_moves <= diff_without_moves:
                    has_moves = True
                    pokemon_size = 18
                else:
                    has_moves = False
                    pokemon_size = 8
        else:
            # Fallback: try to detect based on data length divisibility
            if len(data) % 18 == 0 and len(data) > 0:
                has_moves = True
                pokemon_size = 18
            elif len(data) % 8 == 0 and len(data) > 0:
                has_moves = False
                pokemon_size = 8
            else:
                # Default to no moves if unclear
                has_moves = False
                pokemon_size = 8
        
        # Calculate number of Pokémon based on data length and detected format
        num_pokemon = len(data) // pokemon_size
        trainer.nummons = num_pokemon
        
        # Debug: Print hex data for all trainers to check alignment
        if DEBUG_TRAINER_PARSING:
            print(f"\n=== TRAINER {i} DEBUG ===")
            print(f"Data length: {len(data)} bytes")
            print(f"Expected Pokemon: {expected_pokemon}")
            print(f"Has moves: {has_moves}, Pokemon size: {pokemon_size}")
            print(f"Calculated num_pokemon: {num_pokemon}")
            # Print hex data in 8-byte chunks with decimal values
            for chunk_start in range(0, len(data), 8):  # Print all data
                chunk = data[chunk_start:chunk_start+8]
                hex_str = ' '.join(f'{b:02X}({b:3d})' for b in chunk)
                print(f"Offset {chunk_start:02X}: {hex_str}")
            print("========================\n")
        
        # Now parse each Pokémon entry
        for j in range(num_pokemon):
            offset = j * pokemon_size
            
            # Parse the Pokémon data
            if has_moves:
                # Pokémon with moves (18 bytes)
                pokemon_data = data[offset:offset+pokemon_size]
                pokemon = trainer_pokemon_moves_struct.parse(pokemon_data)
            else:
                # Standard Pokémon (8 bytes)
                pokemon_data = data[offset:offset+pokemon_size]
                pokemon = trainer_pokemon_struct.parse(pokemon_data)
            
            # Debug: Print parsed data for all trainers
            if DEBUG_TRAINER_PARSING:
                if has_moves:
                    print(f"Pokemon {j}: IVs={pokemon.ivs}, Ability={pokemon.abilityslot}, Level={pokemon.level}, Species={pokemon.species}, Item={pokemon.item}, Moves=[{pokemon.move1},{pokemon.move2},{pokemon.move3},{pokemon.move4}], Ballseal={pokemon.ballseal}")
                else:
                    print(f"Pokemon {j}: IVs={pokemon.ivs}, Ability={pokemon.abilityslot}, Level={pokemon.level}, Species={pokemon.species}, Ballseal={pokemon.ballseal}")
            
            # Add to trainer's team
            trainer.pokemon.append(pokemon)
        
        # If we found Pokémon, flag this trainer as having moves if needed
        if has_moves and len(trainer.pokemon) > 0:
            trainer.trainerdata = 2  # Set flag for having moves
        
        trainers.append((i, trainer))
        if DEBUG_TRAINER_PARSING:
            print(f"Trainer {i}: Parsed {len(trainer.pokemon)} Pokémon" + (" with moves" if has_moves else ""))
    
    print(f"Total trainers processed: {len(trainers)}")
    return trainers, trainer_narc_data

# find_replacements is now imported from pokemon_shared.py

def randomize_trainer_pokemon(trainer_id, trainer, mondata, trainer_name, log_function=None, base_path=".", bst_mode="bst", gym_types=None, use_gym_types=False, use_pivots=False, use_fulcrums=False, use_mimics=False):
    """Randomize a trainer's Pokémon based on selected mode
    
    Args:
        trainer_id: The trainer's ID number
        trainer: The trainer object containing Pokémon data
        mondata: Pokémon stats data
        trainer_name: Name of the trainer for logging
        log_function: Optional function for logging changes
        base_path: Base directory path for finding the blacklist file
        bst_mode: Mode for randomization - "bst" (use similar BST values) or "random" (fully random)
        gym_types: Dictionary of gym type information
        use_gym_types: Whether to use type-themed gyms for randomization
    """
    if not hasattr(trainer, 'pokemon') or not trainer.pokemon:
        return  # Skip if no Pokémon
        
    has_moves = any(hasattr(p, 'move1') for p in trainer.pokemon)
    
    # Get blacklisted Pokémon
    from pokemon_shared import read_blacklist
    blacklist = read_blacklist(base_path)
    
    # Combine special Pokémon and blacklist
    excluded_pokemon = SPECIAL_POKEMON.union(blacklist)
    
    # Check if this is a gym leader or gym trainer
    gym_type = None
    is_gym_leader = False
    
    # Only check gym type if the feature is enabled and gym_types is provided
    if use_gym_types and gym_types:
        gym_type, is_gym_leader = get_trainer_gym_type(trainer_name, gym_types)
        
        if gym_type:
            if log_function:
                leader_status = "LEADER" if is_gym_leader else "trainer"
                log_function(f"Using {gym_type}-type theme for gym {leader_status} {trainer_name}")
    
    # For random mode, prepare a list of all valid replacement Pokémon
    if bst_mode == "random":
        # Get all Pokémon that aren't in excluded list
        all_valid_pokemon = [i for i, _ in enumerate(mondata) 
                              if i > 0 and i < len(mondata) and i not in excluded_pokemon]
        
        if log_function:
            log_function(f"Using RANDOM mode with {len(all_valid_pokemon)} valid Pokémon choices")
    else:  # BST mode
        if log_function:
            log_function(f"Using BST mode (selecting Pokémon with similar stats)")
    
    for i, pokemon in enumerate(trainer.pokemon):
        original_species = pokemon.species
        
        # Skip if not a valid species or it's a special Pokémon
        if original_species >= len(mondata) or original_species <= 0:
            continue  # Skip invalid species IDs
            
        # Get the original Pokémon data
        original_mon = mondata[original_species]
        
        # Don't randomize special Pokémon
        if original_species in SPECIAL_POKEMON:
            continue
        
        # Special handling for gym trainers - use type-themed Pokémon
        if gym_type and use_gym_types:
            # For gym leaders and trainers, select Pokémon of the appropriate type
            # Leaders get stronger type Pokémon (tighter BST range)
            bst_range = 0.15 if is_gym_leader else 0.25
            
            # Try to find a Pokémon of the gym's type with similar BST
            replacement = select_themed_replacement(
                original_mon, mondata, gym_type, excluded_pokemon, bst_range)
                
            if replacement is not None:
                new_species = replacement
                
                # For important leaders, make sure we have good Pokémon
                if is_gym_leader and i == len(trainer.pokemon) - 1:  # Last Pokémon (ace)
                    # Try again with a wider BST range to get a stronger Pokémon if possible
                    ace_replacement = select_themed_replacement(
                        original_mon, mondata, gym_type, excluded_pokemon, 0.3)
                    if ace_replacement is not None:
                        new_species = ace_replacement
            else:
                # Fall back to normal randomization if no type match found
                if bst_mode == "random":
                    if all_valid_pokemon:
                        new_species = random.choice(all_valid_pokemon)
                    else:
                        continue  # No valid options
                else:  # BST mode
                    potential_replacements = find_replacements(original_mon, mondata, 0.9, 1.1, base_path)
                    if not potential_replacements:
                        continue
                    new_species = random.choice(potential_replacements)
        else:
            # Regular randomization for non-gym trainers
            if bst_mode == "random":
                # For random mode, pick any valid Pokémon
                if all_valid_pokemon:  # Make sure we have valid options
                    new_species = random.choice(all_valid_pokemon)
                else:
                    # If somehow we have no valid options, keep original
                    continue
            else:  # BST mode
                # Find potential replacements with similar BST (and applying blacklist)
                potential_replacements = find_replacements(original_mon, mondata, 0.9, 1.1, base_path)
                
                # If no replacements found, keep original
                if not potential_replacements:
                    continue
                    
                # Choose a random replacement from BST-similar options
                new_species = random.choice(potential_replacements)
        
        # Get data for the new Pokémon
        new_mon = mondata[new_species]
        
        # Update the species ID in the Pokémon object
        pokemon.species = new_species
        
        # Log the change if logging is enabled
        if log_function:
            # Calculate percentage difference in BST
            percent_diff = ((new_mon.bst - original_mon.bst) / original_mon.bst) * 100 if original_mon.bst > 0 else 0
            move_info = ""
            
            # Add move info if this Pokémon has moves
            if has_moves:
                move_info = f"  Moves: {pokemon.move1}, {pokemon.move2}, {pokemon.move3}, {pokemon.move4}"
                
            # Replace special characters in Pokémon names with ASCII equivalents
            orig_name = original_mon.name.replace('♂', '[M]').replace('♀', '[F]').replace('é', 'e')
            new_name = new_mon.name.replace('♂', '[M]').replace('♀', '[F]').replace('é', 'e')
            
            # Handle placeholder Pokémon names for better readability
            if orig_name == "-----":
                orig_name = "[Form Variant]"
            if new_name == "-----":
                new_name = "[Form Variant]"
            
            # Format log message
            log_message = f"{trainer_id:<4} {trainer_name:<30} {i:<2} {orig_name:<15} {original_mon.bst:<4} {'-->':<3} {new_name:<15} {new_mon.bst:<4} {percent_diff:+.1f}%"
            if move_info:
                log_message += f"\n{' '*53}{move_info}"
            log_function(log_message)

    # Apply special Pokémon (pivots, fulcrums, mimics) if enabled
    if any([use_pivots, use_fulcrums, use_mimics]) and gym_type:
        # Convert gym type format from "Fire" to "TYPE_FIRE" format for special Pokémon handlers
        special_gym_type = f"TYPE_{gym_type.upper()}" if gym_type else None
        
        # Log what type we're using for special Pokémon
        if log_function:
            log_function(f"\nApplying special Pokémon for gym type: {gym_type} (as {special_gym_type})")
            
        new_pokemon = apply_special_pokemon(
            trainer.pokemon, special_gym_type, mondata, base_path,
            use_pivots, use_fulcrums, use_mimics
        )
        if log_function:
            if use_pivots:
                log_function(f"    Added pivot Pokémon for {trainer_name} (Gym type: {gym_type})")
            if use_fulcrums:
                log_function(f"    Added fulcrum Pokémon for {trainer_name} (Gym type: {gym_type})")
            if use_mimics:
                log_function(f"    Added mimic Pokémon for {trainer_name} (Gym type: {gym_type})")

    # Return the updated Pokémon list
    return trainer.pokemon

def replace_moves_with_splash(trainer):
    """Replace all moves of a trainer's Pokémon with Splash"""
    # Skip if trainer has no Pokémon or Pokémon don't have moves
    if not hasattr(trainer, 'pokemon') or not trainer.pokemon:
        return trainer
    
    # Check if the Pokémon have moves (if they have move1 attribute)
    if not hasattr(trainer.pokemon[0], 'move1'):
        return trainer
    
    # Replace all moves with Splash
    for pokemon in trainer.pokemon:
        pokemon.move1 = SPLASH_MOVE_ID
        pokemon.move2 = SPLASH_MOVE_ID
        pokemon.move3 = SPLASH_MOVE_ID
        pokemon.move4 = SPLASH_MOVE_ID
        
    return trainer

def randomize_trainers(rom, log_function=None, progress_callback=None, replace_moves=False, base_path=".", bst_mode="bst", use_gym_types=False, use_pivots=False, use_fulcrums=False, use_mimics=False, seed=None):
    """Randomize all trainers' Pokémon based on selected mode
    
    Args:
        rom: The ROM object to modify
        log_function: Function for logging changes (defaults to print)
        progress_callback: Optional function for reporting progress
        replace_moves: Whether to replace all moves with Splash
        base_path: Base directory path for finding data files
        bst_mode: Mode for randomization - "bst" (use similar BST values) or "random" (fully random)
        use_gym_types: Whether to use type-themed gyms (gym leaders and trainers use Pokémon of their type)
        seed: Random seed for consistent results
    """
    # Log function defaults to print if not provided
    if log_function is None:
        log_function = print
    
    print("Reading Pokémon data...")
    names = read_pokemon_names(".")
    mondata = read_mondata(rom, names)
    print(f"Loaded data for {len(mondata)} Pokémon")
    
    print("Reading trainer data...")
    trainers, trainer_narc_data = read_trainer_data(rom)
    print(f"Loaded {len(trainers)} trainers")
    
    # Read trainer names from the assembly file
    trainer_names = read_trainer_names(".")
    
    # Load gym type information if we're using type-themed gyms
    gym_types = None
    if use_gym_types:
        print("Loading gym type data for type-themed gyms...")
        # Pass the seed to ensure consistent random types if a seed was provided
        gym_types = read_gym_types(base_path, randomize_types=True, seed=seed)
        
        if not gym_types:
            print("Warning: No gym type data found. Type-themed gyms will be disabled.")
            use_gym_types = False
        else:
            print(f"Loaded and randomized type information for {len(gym_types)} gyms")
            log_function(f"Using RANDOM TYPE-THEMED GYMS: Each gym has a randomly assigned type")
            
            # Print gym types for verification after randomization
            for gym_location, gym_info in gym_types.items():
                print(f"  {gym_location}: {gym_info.get('type')}-type (Leader: {gym_info.get('leader')})")
                print(f"    Trainers: {', '.join(gym_info.get('trainers', []))}")
                
            # Save the random type assignments to a file for reference
            random_types_file = "random_gym_types.txt"
            print(f"Saving random gym type assignments to {random_types_file}...")
            with open(random_types_file, "w") as f:
                f.write("RANDOM GYM TYPE ASSIGNMENTS\n")
                f.write("=========================\n\n")
                for gym_location, gym_info in gym_types.items():
                    f.write(f"{gym_location}: {gym_info.get('type')}-type\n")
                    f.write(f"  Leader: {gym_info.get('leader')}\n")
                    f.write(f"  Trainers: {', '.join(gym_info.get('trainers', []))}\n\n")
    
    print(f"Loaded {len(trainer_names)} trainer names")
    
    # Map gym trainer names to their IDs
    gym_trainer_ids = map_gym_trainer_names_to_ids(trainer_names)
    
    # Save gym trainer IDs to a file for reference
    print("Saving gym trainer ID mapping to 'gym_trainer_ids.txt'...")
    with open("gym_trainer_ids.txt", "w") as f:
        f.write("GYM TRAINER ID MAPPING\n")
        f.write("===================\n\n")
        for location, trainers_with_ids in gym_trainer_ids.items():
            f.write(f"\n{location}:\n")
            for trainer_name, trainer_id in trainers_with_ids:
                id_status = str(trainer_id) if trainer_id is not None else "NOT FOUND"
                f.write(f"  {trainer_name}: {id_status}\n")
    print("Gym trainer ID mapping saved successfully!")
    
    # Count trainers with Pokémon that have moves
    trainers_with_moves = sum(1 for trainer in trainers if trainer and hasattr(trainer, 'pokemon') and 
                             trainer.pokemon and hasattr(trainer.pokemon[0], 'move1'))
    print(f"{trainers_with_moves} trainers have Pokémon with moves")
    
    # Randomize each trainer
    total_trainers = len(trainers)
    for i, (trainer_id, trainer) in enumerate(trainers):
        # Skip empty or invalid trainers
        if trainer.nummons == 0:
            continue
            
        # Get trainer name if available, otherwise use ID
        trainer_name = trainer_names.get(trainer_id, f"Trainer {trainer_id}")
        
        # Skip trainers with no Pokémon
        if not hasattr(trainer, 'pokemon') or not trainer.pokemon:
            continue
        
        # Replace moves with Splash if requested
        if replace_moves:
            trainer = replace_moves_with_splash(trainer)
            log_function(f"Replaced all moves with Splash for {trainer_name}")
        else:
            # Randomize this trainer's Pokémon - pass gym type info if we're using type-themed gyms
            trainer.pokemon = randomize_trainer_pokemon(trainer_id, trainer, mondata, trainer_name, log_function, base_path, bst_mode, gym_types, use_gym_types, use_pivots, use_fulcrums, use_mimics)
        
        # Rebuild trainer data and save it back to the NARC
        try:
            # Skip trainers with no Pokémon to avoid errors
            if trainer.nummons == 0 or not hasattr(trainer, 'pokemon') or len(trainer.pokemon) == 0:
                print(f"Skipping trainer {trainer_id} with no Pokémon")
                continue
                            
            # Create a new empty byte array for the rebuilt data
            rebuilt_data = bytearray()
            
            # Check if trainer has Pokémon with moves
            has_moves = hasattr(trainer, 'trainerdata') and trainer.trainerdata & 2
            # Also check the first Pokémon (more reliable)
            if len(trainer.pokemon) > 0 and hasattr(trainer.pokemon[0], 'move1'):
                has_moves = True
                
            # Add each Pokémon to the data
            for pokemon in trainer.pokemon:
                if has_moves:
                    # Pokémon with moves
                    pokemon_data = trainer_pokemon_moves_struct.build(pokemon)
                else:
                    # Standard Pokémon
                    pokemon_data = trainer_pokemon_struct.build(pokemon)
                    
                # Add the Pokémon data to the rebuilt data
                rebuilt_data.extend(pokemon_data)
                
            # Save the rebuilt data back to the NARC
            trainer_narc_data.files[trainer_id] = bytes(rebuilt_data)
            print(f"Successfully rebuilt trainer {trainer_id} with {len(trainer.pokemon)} Pokémon" + 
                  (" with moves" if has_moves else ""))
            
        except Exception as e:
            print(f"Error rebuilding trainer {trainer_id}: {e}")
            # Keep the original data for this trainer
            print(f"Keeping original data for trainer {trainer_id}")
        
        # Update progress
        if progress_callback:
            progress_percent = int((i + 1) * 100 / total_trainers)
            progress_callback(progress_percent)
    
    # Save the updated trainer NARC back to the ROM file
    print("Saving trainer data back to ROM file...")
    try:
        # Get the file ID for the trainer data NARC
        narc_file_id = rom.filenames.idOf("a/0/5/6")
        
        # Save the updated NARC data back to the ROM file
        rom.files[narc_file_id] = trainer_narc_data.save()
        print("Successfully saved trainer data to ROM")
    except Exception as e:
        print(f"Error saving trainer data to ROM: {e}")
    
    # Return the trainers list so it can be further modified if needed
    return trainers

def main():
    """Main function for running the randomizer from command line"""
    parser = argparse.ArgumentParser(description="Randomize trainer Pokémon in HeartGold/SoulSilver ROM.")
    parser.add_argument("rom_path", help="Path to the ROM file")
    parser.add_argument("--log", action="store_true", help="Enable logging of changes")
    parser.add_argument("--seed", type=int, help="Random seed for consistent results")
    parser.add_argument("--splash", action="store_true", help="Replace all trainer moves with Splash")
    parser.add_argument("--blacklist", action="store_true", help="Use blacklist from data/blacklist.txt")
    parser.add_argument("--bst-mode", choices=["bst", "random"], default="bst", 
                      help="BST randomization mode: 'bst' (select Pokémon with similar stats) or 'random' (completely random)")
    parser.add_argument("--type-themed-gyms", action="store_true", 
                       help="Enable type-themed gyms (gym leaders and trainers use Pokémon matching their gym's type)")
    parser.add_argument("--max-boss-teams", action="store_true", help="Give all boss trainers full teams")
    parser.add_argument("--boss-team-size", type=int, default=6, help="Set the team size for boss trainers (default: 6)")
    
    # Special Pokémon options
    special_group = parser.add_argument_group("Special Pokémon Options")
    special_group.add_argument("--pivots", action="store_true", 
                            help="Add pivot Pokémon that defend against a gym's type weaknesses")
    special_group.add_argument("--fulcrums", action="store_true", 
                            help="Add fulcrum Pokémon that offensively counter a gym's weaknesses")
    special_group.add_argument("--mimics", action="store_true", 
                            help="Add mimic Pokémon that thematically fit a gym's type without being that type")
    
    args = parser.parse_args()
    
    # Validate we have a ROM path
    rom_path = args.rom_path
    if not os.path.exists(rom_path):
        print(f"Error: ROM file {rom_path} not found")
        sys.exit(1)
    
    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")
        
    # Setup logging if requested
    log_function = None
    if args.log:
        log_file = rom_path.replace('.nds', '_random_log.txt')
        log_file_handle = open(log_file, 'w', encoding='utf-8')
        def log_to_file(message):
            print(message)
            log_file_handle.write(message + '\n')
        log_function = log_to_file
        print(f"Logging to {log_file}")
    
    # Open the ROM file
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Get base path for finding data files
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    # Log blacklist information if enabled
    if args.blacklist:
        print("Using Pokémon blacklist from data/blacklist.txt")
    else:
        print("Blacklist disabled")
    
    # Log BST mode information
    print(f"Using {args.bst_mode.upper()} randomization mode")
    
    # Log type-themed gyms information if enabled
    if args.type_themed_gyms:
        print("Type-themed gyms ENABLED: Gym leaders and trainers will use Pokémon of their gym's type")
    else:
        print("Type-themed gyms disabled")
    
    # Randomize trainers
    trainers = randomize_trainers(rom, log_function=log_function, replace_moves=args.splash, 
                               base_path=base_path, bst_mode=args.bst_mode, use_gym_types=args.type_themed_gyms,
                               use_pivots=args.pivots, use_fulcrums=args.fulcrums, use_mimics=args.mimics,
                               seed=args.seed)
    
    # If max-boss-teams is enabled, adjust boss team sizes after randomization
    if args.max_boss_teams:
        message = f"Setting boss trainers to have {args.boss_team_size} Pokémon..."
        print(message)
        if log_function:
            log_function(message)
            
        trainers = max_team_size_bosses(trainers, target_size=args.boss_team_size, log_function=log_function)
        
        # Update trainer poke_count values in the ROM
        from randomizer_functions import update_trainer_poke_count
        for trainer_id, trainer in trainers:
            update_trainer_poke_count(rom, trainer_id, len(trainer.pokemon))
            
        # Need to rebuild and save the Pokémon data
        narc_file_id = rom.filenames.idOf("a/0/5/6")
        trainer_narc_data = ndspy.narc.NARC(rom.files[narc_file_id])
        
        for trainer_id, trainer in trainers:
            if hasattr(trainer, 'pokemon') and trainer.pokemon:
                data = rebuild_trainer_data(trainer)
                trainer_narc_data.files[trainer_id] = data
                
        rom.files[narc_file_id] = trainer_narc_data.save()
    
    # Save the ROM with a descriptive name
    output_name = "_random"
    if args.splash:
        output_name += "_splash"
    if args.blacklist:
        output_name += "_blacklist"
    if args.type_themed_gyms:
        output_name += "_typegyms"
    if args.bst_mode == "random":
        output_name += "_truerandom"
    if args.max_boss_teams:
        output_name += f"_bosses{args.boss_team_size}"
    
    # Add special Pokémon indicators to filename
    if args.pivots:
        output_name += "_pivots"
    if args.fulcrums:
        output_name += "_fulcrums"
    if args.mimics:
        output_name += "_mimics"
        
    output_path = rom_path.replace(".nds", f"{output_name}.nds")
    rom.saveToFile(output_path)
    print(f"ROM saved to {output_path}")
    
    # Close log file if opened
    if args.log:
        log_file_handle.close()

if __name__ == "__main__":
    main()
