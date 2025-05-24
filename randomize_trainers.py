from construct import *
import random
import os
import re

import ndspy.rom
import ndspy.narc

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

# Direct parsing approach for hge.nds
# Based on the ROM analysis, we need a different approach

# Pokémon entry structure (each Pokémon is 8 bytes without moves, 20 bytes with moves)
trainer_pokemon_struct = Struct(
    "ivs" / Int8ul,             # IVs byte
    "abilityslot" / Int8ul,     # Ability slot
    "level" / Int16ul,          # Level (halfword)
    "species" / Int16ul,        # Species ID (halfword)
    "ball" / Int8ul,            # Ball type
    "padding" / Int8ul,         # Padding byte for alignment
)

# Pokémon with moves structure 
trainer_pokemon_moves_struct = Struct(
    "ivs" / Int8ul,             # IVs byte
    "abilityslot" / Int8ul,     # Ability slot
    "level" / Int16ul,          # Level (halfword)
    "species" / Int16ul,        # Species ID (halfword)
    "item" / Int16ul,           # Held item
    "move1" / Int16ul,          # Move 1
    "move2" / Int16ul,          # Move 2
    "move3" / Int16ul,          # Move 3
    "move4" / Int16ul,          # Move 4
    "ball" / Int8ul,            # Ball type
    "padding" / Int8ul,         # Padding
)

# In hge.nds, trainers seem to be stored without the standard header
# We'll directly parse the Pokémon entries instead of relying on nummons

# These functions are now imported from pokemon_shared.py

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
        try:
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
                
            # Special handling for problem trainers (keep as is)
            if i in [651, 652, 654, 658, 659]:
                print(f"Keeping original data for problematic trainer {i}")
                trainers.append((i, trainer))
                continue
            
            # First, check if this is a trainer with moves
            # Usually if data length is divisible by 20 and not by 8, it has moves
            if len(data) % 20 == 0 and len(data) > 0:
                has_moves = True
                pokemon_size = 20
                
            # If expected Pokémon count is available, use it to guess format
            if expected_pokemon > 0:
                # Check if the data size matches expected count with moves
                if len(data) == expected_pokemon * 20:
                    has_moves = True
                    pokemon_size = 20
                # Check if data size matches expected count without moves
                elif len(data) == expected_pokemon * 8:
                    has_moves = False
                    pokemon_size = 8
            
            # Calculate number of Pokémon based on data length and detected format
            num_pokemon = len(data) // pokemon_size
            trainer.nummons = num_pokemon
            
            # Now parse each Pokémon entry
            for j in range(num_pokemon):
                offset = j * pokemon_size
                
                # Make sure we have enough data left
                if offset + pokemon_size > len(data):
                    break
                
                # Parse the Pokémon data
                if has_moves:
                    # Pokémon with moves (20 bytes)
                    pokemon_data = data[offset:offset+pokemon_size]
                    pokemon = trainer_pokemon_moves_struct.parse(pokemon_data)
                else:
                    # Standard Pokémon (8 bytes)
                    pokemon_data = data[offset:offset+pokemon_size]
                    pokemon = trainer_pokemon_struct.parse(pokemon_data)
                
                # Add to trainer's team
                trainer.pokemon.append(pokemon)
            
            # If we found Pokémon, flag this trainer as having moves if needed
            if has_moves and len(trainer.pokemon) > 0:
                trainer.trainerdata = 2  # Set flag for having moves
            
            trainers.append((i, trainer))
            print(f"Trainer {i}: Parsed {len(trainer.pokemon)} Pokémon" + (" with moves" if has_moves else ""))
            
        except Exception as e:
            # If parsing fails, create an empty trainer
            from construct import Container
            trainer = Container()
            trainer.trainerdata = 0
            trainer.trainerclass = 0
            trainer.battletype = 0
            trainer.nummons = 0
            trainer.items = [0, 0, 0, 0]
            trainer.ai_flags = 0
            trainer.padding = 0
            trainer.pokemon = []
            trainers.append((i, trainer))
            print(f"Error parsing trainer {i}: {e}")
    
    print(f"Total trainers processed: {len(trainers)}")
    return trainers, trainer_narc_data

# find_replacements is now imported from pokemon_shared.py

def randomize_trainer_pokemon(trainer_id, trainer, mondata, trainer_name, log_function=None):
    """Randomize a trainer's Pokémon independently by BST"""
    # Determine if this trainer's Pokémon have moves defined
    has_moves = hasattr(trainer.pokemon[0], 'move1') if trainer.nummons > 0 and len(trainer.pokemon) > 0 else False
    
    for i, pokemon in enumerate(trainer.pokemon):
        original_species = pokemon.species
        
        # Skip if it's not a valid species or it's a special Pokémon
        if original_species >= len(mondata) or original_species in SPECIAL_POKEMON or original_species == 0:
            continue
        
        # Get the original Pokémon data
        original_mon = mondata[original_species]
        
        # Find suitable replacements within 10% of original BST
        replacements = find_replacements(original_mon, mondata, 0.9, 1.1)
        
        # Additionally filter out any species that exceed the length of mondata
        replacements = [r for r in replacements if r < len(mondata)]
        
        # If no suitable replacements found, keep original
        if not replacements:
            continue
        
        # Choose a random replacement
        new_species = random.choice(replacements)
        new_mon = mondata[new_species]
        
        # Apply the new species
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
            
            # Format log message
            log_message = f"{trainer_id:<4} {trainer_name:<30} {i:<2} {orig_name:<15} {original_mon.bst:<4} {'-->':<3} {new_name:<15} {new_mon.bst:<4} {percent_diff:+.1f}%"
            if move_info:
                log_message += f"\n{' '*53}{move_info}"
            log_function(log_message)

def randomize_trainers(rom, log_function=None, progress_callback=None):
    """Randomize all trainers' Pokémon independently by BST"""
    # Read Pokémon data
    names = read_pokemon_names(".")
    mondata = read_mondata(rom, names)
    
    # Read trainer names
    trainer_names = read_trainer_names(".")
    
    # Read trainer data
    trainers, trainer_narc_data = read_trainer_data(rom)
    
    # Set up logging
    header_message = f"{'ID':<4} {'Trainer':<30} {'#':<2} {'Original':<15} {'BST':<4} {'-->':<3} {'Replacement':<15} {'BST':<4} {'Diff%':<6}"
    separator_message = "-" * 100
    
    if log_function:
        log_function(header_message)
        log_function(separator_message)
    
    # Randomize each trainer's Pokémon
    total_trainers = len(trainers)
    for i, (trainer_id, trainer) in enumerate(trainers):
        # Skip empty or invalid trainers
        if trainer.nummons == 0:
            continue
            
        # Get trainer name if available, otherwise use ID
        trainer_name = trainer_names.get(trainer_id, f"Trainer {trainer_id}")
        
        # Randomize this trainer's Pokémon
        randomize_trainer_pokemon(trainer_id, trainer, mondata, trainer_name, log_function)
        
        # Rebuild trainer data and save it back to the NARC
        try:
            # Skip trainers with no Pokémon to avoid errors
            if trainer.nummons == 0 or not hasattr(trainer, 'pokemon') or len(trainer.pokemon) == 0:
                print(f"Skipping trainer {trainer_id} with no Pokémon")
                continue
                
            # For problematic trainers, keep original data
            if trainer_id in [651, 652, 654, 658, 659]:
                print(f"Keeping original data for problematic trainer {trainer_id}")
                continue
                
            # In hge.nds, the trainer data is just a sequence of Pokémon entries
            # We don't need to rebuild the full trainer structure
            
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
    
    # Save changes back to ROM
    narc_file_id = rom.filenames.idOf("a/0/5/6")
    rom.files[narc_file_id] = trainer_narc_data.save()

def test_trainer_parser():
    """Create and test a simple trainer structure"""
    # Create a simple trainer data structure to test our parser
    # This will help us validate that our parsing logic works correctly
    
    # Standard trainer without moves (type 0)
    standard_trainer = bytearray([
        0,      # Trainer type 0 (standard)
        1,      # Trainer class
        0,      # Battle type
        2,      # Number of Pokémon (2)
        0, 0,   # Item 1
        0, 0,   # Item 2
        0, 0,   # Item 3
        0, 0,   # Item 4
        0, 0, 0, 0,  # AI flags
        0, 0, 0, 0,  # Padding
        # Pokémon 1
        30,     # IVs
        0,      # Ability slot
        20, 0,  # Level 20
        25, 0,  # Species 25 (Pikachu)
        0,      # Ball
        # Pokémon 2
        30,     # IVs
        0,      # Ability slot
        22, 0,  # Level 22
        26, 0,  # Species 26 (Raichu)
        0,      # Ball
    ])
    
    # Trainer with moves (type 2)
    moves_trainer = bytearray([
        2,      # Trainer type 2 (with moves)
        2,      # Trainer class
        0,      # Battle type
        1,      # Number of Pokémon (1)
        0, 0,   # Item 1
        0, 0,   # Item 2
        0, 0,   # Item 3
        0, 0,   # Item 4
        0, 0, 0, 0,  # AI flags
        0, 0, 0, 0,  # Padding
        # Pokémon 1 with moves
        30,     # IVs
        0,      # Ability slot
        50, 0,  # Level 50
        6, 0,   # Species 6 (Charizard)
        0, 0,   # Held item
        5, 0,   # Move 1 (Flamethrower)
        10, 0,  # Move 2 (Earthquake)
        15, 0,  # Move 3 (Hyper Beam)
        20, 0,  # Move 4 (Solarbeam)
        0,      # Ball
        0,      # Padding
    ])
    
    print("Testing standard trainer parser...")
    try:
        trainer = trainer_struct.parse(standard_trainer)
        print(f"Success! Found {trainer.nummons} Pokémon")
        for i, mon in enumerate(trainer.pokemon):
            print(f"  Pokémon {i+1}: Species {mon.species}, Level {mon.level}")
    except Exception as e:
        print(f"Error parsing standard trainer: {e}")
    
    print("\nTesting trainer with moves parser...")
    try:
        trainer = Struct(
            "trainerdata" / Int8ul,
            "trainerclass" / Int8ul,
            "battletype" / Int8ul,
            "nummons" / Int8ul,
            "items" / Array(4, Int16ul),
            "ai_flags" / Int32ul,
            "padding" / Int32ul,
            "pokemon" / Array(lambda ctx: ctx.nummons, trainer_pokemon_moves_struct),
        ).parse(moves_trainer)
        print(f"Success! Found {trainer.nummons} Pokémon")
        for i, mon in enumerate(trainer.pokemon):
            print(f"  Pokémon {i+1}: Species {mon.species}, Level {mon.level}, Moves: {mon.move1}, {mon.move2}, {mon.move3}, {mon.move4}")
    except Exception as e:
        print(f"Error parsing trainer with moves: {e}")


def check_trainer_count(rom):
    """Check the total number of trainers in the ROM"""
    narc_file_id = rom.filenames.idOf("a/0/5/6")
    trainer_narc = rom.files[narc_file_id]
    trainer_narc_data = ndspy.narc.NARC(trainer_narc)
    
    print(f"Total trainers in ROM: {len(trainer_narc_data.files)}")
    
    # Sample some normal trainers and problematic ones
    test_trainers = [1, 10, 100, 651, 652, 654, 658, 659]
    successful = 0
    failed = 0
    
    for trainer_id in test_trainers:
        if trainer_id < len(trainer_narc_data.files):
            data = trainer_narc_data.files[trainer_id]
            print(f"\nTrainer {trainer_id} data length: {len(data)} bytes")
            print(f"First few bytes: {[b for b in data[:16]]}")
            
            # For HG Engine ROM format, we need to directly parse the Pokémon entries
            try:
                # Check if data is divisible by 8 (standard Pokémon) or 20 (Pokémon with moves)
                if len(data) % 20 == 0 and len(data) > 0:
                    # Likely Pokémon with moves
                    pokemon_size = 20
                    num_pokemon = len(data) // pokemon_size
                    pokemon_list = []
                    
                    for j in range(num_pokemon):
                        offset = j * pokemon_size
                        if offset + pokemon_size <= len(data):
                            pokemon = trainer_pokemon_moves_struct.parse(data[offset:offset+pokemon_size])
                            pokemon_list.append(pokemon)
                    
                    print(f"Successfully parsed trainer {trainer_id} with {num_pokemon} Pokémon (with moves)")
                    for i, mon in enumerate(pokemon_list):
                        print(f"  Pokémon {i+1}: Species {mon.species}, Level {mon.level}, Moves: {mon.move1}, {mon.move2}, {mon.move3}, {mon.move4}")
                    successful += 1
                elif len(data) % 8 == 0 and len(data) > 0:
                    # Likely standard Pokémon
                    pokemon_size = 8
                    num_pokemon = len(data) // pokemon_size
                    pokemon_list = []
                    
                    for j in range(num_pokemon):
                        offset = j * pokemon_size
                        if offset + pokemon_size <= len(data):
                            pokemon = trainer_pokemon_struct.parse(data[offset:offset+pokemon_size])
                            pokemon_list.append(pokemon)
                    
                    print(f"Successfully parsed trainer {trainer_id} with {num_pokemon} Pokémon")
                    for i, mon in enumerate(pokemon_list):
                        print(f"  Pokémon {i+1}: Species {mon.species}, Level {mon.level}")
                    successful += 1
                else:
                    print(f"Cannot determine Pokémon format for trainer {trainer_id}")
                    failed += 1
            except Exception as e:
                print(f"Error parsing trainer {trainer_id}: {e}")
                failed += 1
        else:
            print(f"Trainer {trainer_id} doesn't exist in ROM")
    
    print(f"\nParsing results: {successful} successful, {failed} failed")
    
    # Find some working trainers with different Pokémon counts to analyze
    print("\nScanning for different trainer types...")
    for pokemon_count in [1, 2, 3, 6]:  # Try to find trainers with different numbers of Pokémon
        for i in range(1, 700):  # Scan through trainers
            try:
                if i >= len(trainer_narc_data.files):
                    break
                    
                data = trainer_narc_data.files[i]
                
                # Check if divisible by 8 first (more common)
                if len(data) == pokemon_count * 8:
                    # Found a trainer with the desired number of standard Pokémon
                    pokemon_list = []
                    for j in range(pokemon_count):
                        offset = j * 8
                        pokemon = trainer_pokemon_struct.parse(data[offset:offset+8])
                        pokemon_list.append(pokemon)
                    
                    print(f"\nFound trainer {i} with {pokemon_count} standard Pokémon:")
                    for k, mon in enumerate(pokemon_list):
                        print(f"  Pokémon {k+1}: Species {mon.species}, Level {mon.level}, IVs {mon.ivs}")
                    break
                # Check if divisible by 20 (Pokémon with moves)
                elif len(data) == pokemon_count * 20:
                    # Found a trainer with the desired number of Pokémon with moves
                    pokemon_list = []
                    for j in range(pokemon_count):
                        offset = j * 20
                        pokemon = trainer_pokemon_moves_struct.parse(data[offset:offset+20])
                        pokemon_list.append(pokemon)
                    
                    print(f"\nFound trainer {i} with {pokemon_count} Pokémon with moves:")
                    for k, mon in enumerate(pokemon_list):
                        print(f"  Pokémon {k+1}: Species {mon.species}, Level {mon.level}, IVs {mon.ivs}")
                        print(f"    Moves: {mon.move1}, {mon.move2}, {mon.move3}, {mon.move4}")
                    break
            except Exception:
                continue

def main():
    """Main function for running the randomizer from command line"""
    import argparse
    parser = argparse.ArgumentParser(description="Randomize trainer Pokémon in HeartGold/SoulSilver ROM")
    parser.add_argument("rom_path", nargs='?', help="Path to the ROM file")
    parser.add_argument("--log", action="store_true", help="Enable logging to file")
    parser.add_argument("--seed", type=int, help="Random seed for consistent results")
    parser.add_argument("--check", action="store_true", help="Check trainer structure without randomizing")
    parser.add_argument("--test", action="store_true", help="Test parser on trainer data")
    args = parser.parse_args()
    
    # Test mode - we'll create a small test file to validate our parser
    if args.test:
        print("Running parser test...")
        test_trainer_parser()
        return
        
    # Validate we have a ROM path for non-test modes
    if not args.rom_path:
        parser.error("You must provide a ROM path unless using --test")
    
    # Set random seed if specified
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")
    
    # Open ROM
    print("Opening ROM file...")
    rom = ndspy.rom.NintendoDSRom.fromFile(args.rom_path)
    
    # If check flag is set, just check trainer count and exit
    if args.check:
        check_trainer_count(rom)
        return
    
    # Setup logging
    log_file = None
    if args.log:
        log_file = open("trainer_randomizer.log", "w", encoding="utf-8")
        print("Logging enabled. Will save to trainer_randomizer.log")
        
    def log_function(message):
        print(message)
        if log_file:
            log_file.write(message + "\n")
    
    def progress_callback(percent):
        print(f"Progress: {percent}%", end="\r")
    
    # Run randomizer
    print("Starting randomization process...")
    randomize_trainers(rom, log_function, progress_callback)
    
    # Save ROM
    output_path = args.rom_path.replace(".nds", "_trainers_randomized.nds")
    print(f"\nSaving randomized ROM to {output_path}...")
    rom.saveToFile(output_path)
    print(f"Randomized ROM saved successfully!")
    
    # Close log file
    if log_file:
        log_file.close()
        print("Log file closed.")

if __name__ == "__main__":
    main()
