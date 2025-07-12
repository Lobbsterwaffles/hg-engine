from construct import *
import random
import os
import re
import argparse
import sys
import json
from datetime import datetime

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

# Team size adjustments will be handled by boss_team_adjuster.py

# Special Pokemon handlers will be called separately

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
    DEBUG_TRAINER_PARSING
)

# Direct parsing approach for hge.nds
# Based on the ROM analysis, we need a different approach

# Data structures and parsing functions are now imported from trainer_data_parser.py

# map_gym_trainer_names_to_ids function moved to trainer_data_parser.py

# read_trainer_names function moved to trainer_data_parser.py

# read_trainer_data function moved to trainer_data_parser.py

# find_replacements is now imported from pokemon_shared.py

def save_temp_data(rom_path, gym_types=None, settings=None):
    """Save temporary data for other scripts to use
    
    Args:
        rom_path (str): Path to the ROM file
        gym_types (dict): Gym type assignments {trainer_id: type}
        settings (dict): Randomization settings used
    """
    temp_data = {
        "timestamp": datetime.now().isoformat(),
        "rom_path": rom_path
    }
    
    if gym_types:
        temp_data["gym_type_assignments"] = gym_types
    
    if settings:
        temp_data["randomization_settings"] = settings
    
    # Save temp data file alongside the ROM
    temp_file = rom_path.replace('.nds', '_temp_data.json')
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(temp_data, f, indent=2)
    
    return temp_file

def load_temp_data(rom_path):
    """Load temporary data saved by previous scripts
    
    Args:
        rom_path (str): Path to the ROM file
        
    Returns:
        dict: Temporary data or empty dict if not found
    """
    temp_file = rom_path.replace('.nds', '_temp_data.json')
    try:
        with open(temp_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def cleanup_temp_data(rom_path):
    """Clean up temporary data file
    
    Args:
        rom_path (str): Path to the ROM file
    """
    temp_file = rom_path.replace('.nds', '_temp_data.json')
    try:
        os.remove(temp_file)
    except FileNotFoundError:
        pass

def randomize_trainer_pokemon(trainer_id, trainer, mondata, trainer_name, log_function=None, base_path=".", bst_mode="bst", gym_types=None, use_gym_types=False):
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

    # Special Pokemon handling will be done separately

    # Function modifies trainer.pokemon in place, no return needed

def replace_moves_with_splash(trainer):
    """Replace all moves of a trainer's Pokémon with Splash"""
    # Skip if trainer has no Pokémon or Pokémon don't have moves
    if not hasattr(trainer, 'pokemon') or not trainer.pokemon:
        return trainer
    
    # Check if the Pokémon have moves (if they have move1 attribute)
    if not hasattr(trainer.pokemon[0], 'move1'):
        return trainer
    
    # Replace all moves with Splash (move ID 150)
    for pokemon in trainer.pokemon:
        pokemon.move1 = 150  # Splash move ID
        pokemon.move2 = 150
        pokemon.move3 = 150
        pokemon.move4 = 150
        
    return trainer

def randomize_trainers(rom, log_function=None, progress_callback=None, replace_moves=False, base_path=".", bst_mode="bst", use_gym_types=False, seed=None):
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
            randomize_trainer_pokemon(trainer_id, trainer, mondata, trainer_name, log_function, base_path, bst_mode, gym_types, use_gym_types)
        
        # Rebuild trainer data and save it back to the NARC
        try:
            # Skip trainers with no Pokémon to avoid errors
            if trainer.nummons == 0 or not hasattr(trainer, 'pokemon') or len(trainer.pokemon) == 0:
                print(f"Skipping trainer {trainer_id} with no Pokémon")
                continue
            
            # Use the rebuild_trainer_data function from trainer_data_parser.py
            rebuilt_data = rebuild_trainer_data(trainer)
            
            # Save the rebuilt data back to the NARC
            trainer_narc_data.files[trainer_id] = bytes(rebuilt_data)
            
            # Update the poke_count field to match the actual Pokemon count
            # This ensures synchronization after randomization
            update_trainer_poke_count_field(rom, trainer_id, len(trainer.pokemon))
            
            # Check if trainer has moves for logging
            has_moves = len(trainer.pokemon) > 0 and hasattr(trainer.pokemon[0], 'move1')
            if DEBUG_TRAINER_PARSING:
                print(f"Successfully rebuilt trainer {trainer_id} with {len(trainer.pokemon)} Pokémon" + 
                      (" with moves" if has_moves else ""))
                print(f"Updated poke_count field to {len(trainer.pokemon)} for consistency")
            
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
    
    # Save temporary data for other scripts to use
    if use_gym_types and gym_types:
        # Import our new gym type data utility
        from gym_type_data import save_gym_type_data
        
        # Convert gym_types structure to simple trainer_id: type mapping
        gym_assignments = {}
        for location, gym_info in gym_types.items():
            gym_type = gym_info.get('type')
            for trainer_name, trainer_id in gym_trainer_ids.get(location, []):
                if trainer_id is not None:
                    gym_assignments[str(trainer_id)] = {
                        "trainer_name": trainer_name,
                        "gym_location": location,
                        "assigned_type": gym_type,
                        "is_leader": trainer_name in gym_info.get('leader', '')
                    }
        
        # Save gym type assignments using our dedicated utility
        gym_types_file = save_gym_type_data(rom.filename if hasattr(rom, 'filename') else 'unknown', 
                                         gym_assignments)
        print(f"Saved gym type assignments to {gym_types_file} for special Pokémon handler")
        
        # Also save other settings in the regular temp data
        settings = {
            "bst_mode": bst_mode,
            "use_gym_types": use_gym_types,
            "replace_moves": replace_moves,
            "seed": seed
        }
        
        temp_file = save_temp_data(rom.filename if hasattr(rom, 'filename') else 'unknown', 
                                 None, settings)  # Don't include gym assignments here
        print(f"Saved temporary data to {temp_file} for other scripts")
    
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
    # Boss team size adjustments will be handled by boss_team_adjuster.py
    
    # Special Pokémon options will be handled by a separate script
    
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
                               seed=args.seed)
    
    # Boss team size adjustments will be handled by boss_team_adjuster.py separately
    
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
    # Boss team indicators will be added by boss_team_adjuster.py
    
    # Special Pokémon indicators will be added by separate script
        
    output_path = rom_path.replace(".nds", f"{output_name}.nds")
    rom.saveToFile(output_path)
    print(f"ROM saved to {output_path}")
    
    # Close log file if opened
    if args.log:
        log_file_handle.close()

if __name__ == "__main__":
    main()
