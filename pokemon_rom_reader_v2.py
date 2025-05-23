#!/usr/bin/env python3
# pokemon_rom_reader_v2.py - A simpler version of the Pokémon ROM reader

import os
import logging
import ndspy.rom
import ndspy.narc

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('pokemon_rom_reader')

def get_pokemon_data(rom_path, create_dump=True):
    """
    Read Pokémon data from a DS ROM file.
    
    Args:
        rom_path (str): Path to the ROM file
        create_dump (bool): Whether to create a stats dump file
    
    Returns:
        dict: Dictionary of Pokémon data indexed by Pokémon ID
    """
    # Dictionary to store all Pokémon data
    pokemon_data = {}
    
    try:
        # Load the ROM
        logger.info(f"Loading ROM from {rom_path}")
        rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
        
        # 1. Read Pokémon names from a text file
        all_names_file = os.path.join(os.path.dirname(rom_path), "build/rawtext/237.txt")
        pokemon_names = _read_pokemon_names(all_names_file)
            
        # 2. Get the Pokémon stats from the ROM
        # Find the appropriate NARC file that contains Pokémon data
        narc_path = 'a/0/0/2'  # This is the expected path for HG/SS Pokémon data
        
        try:
            narc_id = rom.filenames.idOf(narc_path)
            narc_data = rom.files[narc_id]
            mondata_narc = ndspy.narc.NARC(narc_data)
            logger.info(f"Found Pokémon data NARC with {len(mondata_narc.files)} entries")
            
            # Process each Pokémon's data file
            for i, file_data in enumerate(mondata_narc.files):
                pokemon_id = i  # The file index is the Pokémon ID
                
                # Skip files that are too small to contain proper data
                if len(file_data) < 20:
                    continue
                
                try:
                    # Extract the 6 base stats (first 6 bytes)
                    hp = file_data[0]
                    attack = file_data[1]
                    defense = file_data[2]
                    speed = file_data[3]
                    special_attack = file_data[4]
                    special_defense = file_data[5]
                    
                    # Calculate Base Stat Total
                    bst = hp + attack + defense + speed + special_attack + special_defense
                    
                    # Skip obviously invalid Pokémon (with zero HP)
                    if hp == 0:
                        continue
                    
                    # Get Pokémon name
                    name = pokemon_names.get(pokemon_id, f"POKEMON_{pokemon_id}")
                    
                    # Store the data
                    pokemon_data[pokemon_id] = {
                        "name": name,
                        "bst": bst,
                        "hp": hp,
                        "attack": attack,
                        "defense": defense,
                        "speed": speed,
                        "special_attack": special_attack,
                        "special_defense": special_defense
                    }
                    
                except Exception as e:
                    logger.error(f"Error processing Pokémon #{pokemon_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error accessing Pokémon data NARC: {e}")
    
    except Exception as e:
        logger.error(f"Error loading ROM: {e}")
    
    # Create a stats dump file if requested
    if create_dump and pokemon_data:
        _create_stats_dump(pokemon_data, os.path.dirname(rom_path))
    
    return pokemon_data

def _read_pokemon_names(names_file_path):
    """
    Read Pokémon names from a text file.
    
    Args:
        names_file_path (str): Path to the names file
    
    Returns:
        dict: Dictionary mapping Pokémon IDs to names
    """
    pokemon_names = {}
    
    # Try several common locations for the names file
    possible_paths = [
        names_file_path,
        "all_names_file",
        os.path.join("data", "all_names_file"),
        os.path.join("..", "all_names_file")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Process each line
                for i, line in enumerate(lines):
                    name = line.strip()
                    if name:  # Skip empty lines
                        pokemon_names[i] = name
                
                logger.info(f"Read {len(pokemon_names)} Pokémon names from {path}")
                return pokemon_names
                
            except Exception as e:
                logger.error(f"Error reading names from {path}: {e}")
    
    logger.warning("Could not find a valid Pokémon names file")
    return pokemon_names

def _create_stats_dump(pokemon_data, output_dir):
    """
    Create a human-readable dump of Pokémon stats.
    
    Args:
        pokemon_data (dict): Dictionary of Pokémon data
        output_dir (str): Directory to write the output file
    """
    output_file = os.path.join(output_dir, "pokemon_stats_dump.txt")
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            # Write a header
            f.write("======================================================\n")
            f.write("POKÉMON STATS DUMP - VERIFY DATA IS CORRECT\n")
            f.write("======================================================\n\n")
            
            # Write column headers
            f.write(f"{'#':>5} {'Name':<15} {'HP':>4} {'Atk':>4} {'Def':>4} {'Spd':>4} {'SpA':>4} {'SpD':>4} {'BST':>5}\n")
            f.write("-" * 60 + "\n")
            
            # Write each Pokémon's data in a nice tabular format
            for pokemon_id, data in sorted(pokemon_data.items()):
                name = data.get("name", f"POKEMON_{pokemon_id}")
                hp = data.get("hp", 0)
                attack = data.get("attack", 0)
                defense = data.get("defense", 0)
                speed = data.get("speed", 0)
                spatk = data.get("special_attack", 0)
                spdef = data.get("special_defense", 0)
                bst = data.get("bst", 0)
                
                # Format each row with nice spacing
                f.write(f"{pokemon_id:5d} {name:<15} {hp:4d} {attack:4d} {defense:4d} {speed:4d} {spatk:4d} {spdef:4d} {bst:5d}\n")
            
            # Show some summary stats
            f.write("\n" + "-" * 60 + "\n")
            f.write(f"Total Pokémon found: {len(pokemon_data)}\n")
            
        logger.info(f"Pokémon stats dump created at {output_file}")
        
    except Exception as e:
        logger.error(f"Error creating stats dump: {e}")

# Only include functions that need to be public
__all__ = ['get_pokemon_data']

# Main function to run the script directly
if __name__ == "__main__":
    import argparse
    
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description="Read Pokémon data from a ROM file and create a stats dump")
    parser.add_argument("rom_path", help="Path to the ROM file")
    parser.add_argument("--no-dump", action="store_true", help="Don't create a stats dump file")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Get the Pokémon data
    print(f"Reading Pokémon data from {args.rom_path}...")
    pokemon_data = get_pokemon_data(args.rom_path, not args.no_dump)
    
    # Print a summary
    print(f"Found {len(pokemon_data)} Pokémon in the ROM")
    
    # List the first few Pokémon as a sample
    print("\nSample of Pokémon found:")
    count = 0
    for pokemon_id in sorted(pokemon_data.keys()):
        if count >= 20:  # Only show the first 20
            break
        data = pokemon_data[pokemon_id]
        print(f"  #{pokemon_id}: {data['name']} - HP: {data['hp']}, BST: {data['bst']}")
        count += 1
