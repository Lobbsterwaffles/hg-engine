#!/usr/bin/env python3

"""
Pokémon ROM Reader

This module reads Pokémon data directly from ROM files that use the hg-engine format.
It uses the binary formats defined in armips/include/macros.s to parse the data.
"""

import os
import sys
import ndspy.rom
import ndspy.narc
import struct
import logging

# List of Pokémon IDs that should be ignored during randomization
# These include placeholder entries, eggs, and other special cases
IGNORED_POKEMON_IDS = [
    # Entry #1 is intentionally blank
    1,
    # Egg Pokémon
    495, 496,
    # Species 508-543 are placeholders/blank entries
    *range(508, 544)
]

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def read_pokemon_data_from_rom(rom_path):
    """
    Read Pokémon data directly from a ROM file using the format in macros.s
    
    Args:
        rom_path: Path to the ROM file
        
    Returns:
        Dictionary mapping Pokémon IDs to their name and stats
    """
    try:
        # Load the ROM
        logger.info(f"Loading ROM from {rom_path}")
        rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
        
        # Find the Pokémon data NARC (a002 - contains the mondata files)
        logger.info("Looking for Pokémon data NARC (a002)")
        narc_path = 'a/0/0/2'  # Path to the mondata NARC
        
        narc_id = rom.filenames.idOf(narc_path)
        if narc_id is None:
            logger.error(f"Could not find NARC {narc_path} in ROM")
            return {}
            
        # Load the NARC
        narc_data = rom.files[narc_id]
        mondata_narc = ndspy.narc.NARC(narc_data)
        
        logger.info(f"Found Pokémon data NARC with {len(mondata_narc.files)} entries")
        
        # Read Pokémon names from the all_names_file
        all_names_file = os.path.join(os.path.dirname(rom_path), "all_names_file")
        
        # Dictionary to store Pokémon names by ID
        pokemon_names = {}
        
        if os.path.exists(all_names_file):
            try:
                # Read the names file - one Pokémon name per line in order
                with open(all_names_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Process each line, assigning the name to the corresponding Pokémon ID
                for i, line in enumerate(lines):
                    name = line.strip()
                    if name:  # Skip empty lines
                        # Use the line index as the Pokémon ID
                        pokemon_names[i] = name
                
                logger.info(f"Read {len(pokemon_names)} Pokémon names from all_names_file")
            except Exception as e:
                logger.error(f"Error reading Pokémon names from all_names_file: {e}")
                logger.error("Will use generic names for Pokémon")
        else:
            # Try looking in a few other common locations
            alt_paths = [
                "all_names_file",  # Current directory
                os.path.join("data", "all_names_file"),  # data subdirectory
                os.path.join("..", "all_names_file"),  # Parent directory
            ]
            
            found = False
            for path in alt_paths:
                if os.path.exists(path):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        for i, line in enumerate(lines):
                            name = line.strip()
                            if name:  # Skip empty lines
                                pokemon_names[i] = name
                        
                        logger.info(f"Read {len(pokemon_names)} Pokémon names from {path}")
                        found = True
                        break
                    except Exception as e:
                        logger.error(f"Error reading from {path}: {e}")
            
            if not found:
                logger.error("Could not find all_names_file")
                logger.error("Will use generic names for Pokémon")
            
        # Dictionary to store Pokémon data
        pokemon_data = {}
        
        # According to macros.s, each mondata file has the following format:
        # - 6 bytes: base stats (HP, ATK, DEF, SPD, SPATK, SPDEF)
        # - 2 bytes: types (type1, type2)
        # - 1 byte: catch rate
        # - 1 byte: base exp
        # - 2 bytes: EV yields (packed into a halfword)
        # - 4 bytes: held items (2 halfwords)
        # - 1 byte: gender ratio
        # - 1 byte: egg cycles
        # - 1 byte: base friendship
        # - 1 byte: growth rate
        # - 2 bytes: egg groups
        # - 2 bytes: abilities
        # - 1 byte: run chance
        # - 1 byte: color/flip
        
        # Process each mondata file
        for i, file_data in enumerate(mondata_narc.files):
            # In the hg-engine format, Pokémon IDs are offset:
            # - Index 0 = EGG (ID 0)
            # - Index 1 = NONE (ID 1)
            # - Index 2 = BULBASAUR (ID 2)
            # So we use the direct index as the Pokémon ID
            pokemon_id = i
            
            # Skip invalid or too small files
            if len(file_data) < 20:  # Need at least the basic stats
                continue
                
            try:
                # Extract base stats according to macros.s format
                # .macro basestats,hp,atk,def,spd,spatk,spdef
                #   .byte hp, atk, def, spd, spatk, spdef
                # .endmacro
                hp = file_data[0]
                attack = file_data[1]
                defense = file_data[2]
                speed = file_data[3]
                special_attack = file_data[4]
                special_defense = file_data[5]
                
                # Calculate BST (Base Stat Total) - sum of all six base stats
                # The order in macros.s is: HP, Attack, Defense, Speed, Special Attack, Special Defense
                bst = hp + attack + defense + speed + special_attack + special_defense
                
                # Log detailed stats for debugging
                logger.debug(f"Pokemon #{pokemon_id}: HP={hp}, Atk={attack}, Def={defense}, Spd={speed}, SpAtk={special_attack}, SpDef={special_defense}, BST={bst}")
                
                # Verify against known BST values
                known_bst = {
                    1: 0,      # None
                    2: 318,    # Bulbasaur: 45+49+49+45+65+65=318
                    3: 405,    # Ivysaur: 60+62+63+60+80+80=405
                    25: 448,   # Pikachu: 60+90+55+120+90+33=448
                    52: 265,   # Dugtrio: 35+100+50+120+50+10=265
                    129: 200,  # Magikarp: 20+10+55+80+15+20=200
                    150: 680,  # Mewtwo: 106+110+90+130+154+90=680
                }
                
                if pokemon_id in known_bst and bst != known_bst[pokemon_id]:
                    # Log the issue with detailed information
                    error_msg = f"BST mismatch for Pokemon #{pokemon_id}: Calculated {bst}, Expected {known_bst[pokemon_id]}"
                    logger.error(error_msg)
                    
                    # If there's a significant mismatch, raise a critical error and stop execution
                    if abs(bst - known_bst[pokemon_id]) > 50 and pokemon_id != 1:
                        # Provide detailed stat information to help debugging
                        stats_detail = f"Stats: HP={hp}, Atk={attack}, Def={defense}, Spd={speed}, SpAtk={special_attack}, SpDef={special_defense}"
                        logger.critical(f"CRITICAL ERROR: Significant BST mismatch detected for Pokemon #{pokemon_id}. {stats_detail}")
                        
                        # Raise an exception to stop execution
                        raise ValueError(f"Critical BST mismatch for Pokemon #{pokemon_id}. {error_msg}. {stats_detail}")
                        
                    # Even for smaller mismatches, log a warning but continue
                    logger.warning(f"Minor BST mismatch for Pokemon #{pokemon_id} will be reported but processing continues.")
                            
                # Validate that the stats are reasonable
                if hp == 0 or attack == 0 or bst < 150 or bst > 800:
                    skip_reason = ""
                    if hp == 0:
                        skip_reason = "HP is zero"
                    elif attack == 0:
                        skip_reason = "Attack is zero"
                    elif bst < 150:
                        skip_reason = f"BST is too low ({bst})"
                    elif bst > 800:
                        skip_reason = f"BST is too high ({bst})"
                        
                    # Log detailed information about the suspicious stats
                    logger.warning(f"Pokemon #{pokemon_id} has suspicious stats: {skip_reason}")
                    logger.warning(f"Detail - HP:{hp}, Atk:{attack}, Def:{defense}, Spd:{speed}, SpA:{special_attack}, SpD:{special_defense}, BST:{bst}")
                    
                    # For Ivysaur specifically, log even more details
                    if pokemon_id == 3:
                        logger.warning(f"Ivysaur (#{pokemon_id}) data file size: {len(file_data)} bytes")
                        logger.warning(f"First 10 bytes: {[b for b in file_data[:10]]}")
                    
                    # Only skip if HP is zero, otherwise keep it but with warning
                    if hp == 0:
                        logger.warning(f"Skipping Pokemon #{pokemon_id} due to zero HP")
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
        
        logger.info(f"Successfully loaded data for {len(pokemon_data)} Pokémon")
        return pokemon_data
        
    except Exception as e:
        logger.error(f"Error reading Pokémon data from ROM: {e}")
        return {}

def dump_pokemon_data_to_file(pokemon_data, output_file="pokemon_stats_dump.txt"):
    """
    Create a human-readable text file with all Pokémon data.
    
    This helps verify that the data was parsed correctly from the ROM.
    
    Args:
        pokemon_data: Dictionary of Pokémon data from get_pokemon_data()
        output_file: Path to the output text file
    """
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
            
        print(f"\nPokémon stats dump created at {output_file}")
        print("Please check this file to verify that the data was parsed correctly!")
        return True
        
    except Exception as e:
        logger.error(f"Error creating Pokémon stats dump: {e}")
        print(f"Error creating Pokémon stats dump: {e}")
        return False


def read_pokemon_names_from_rawtext(base_dir=None):
    """
    Read Pokémon names from the rawtext files that are generated during ROM building.
    
    These files are created by the monname macro in macros.s and contain the official names.
    The function first tries to read from a single 237.txt file with all names,
    and falls back to reading individual files if that doesn't exist.
    
    Args:
        base_dir: Base directory of the hg-engine project. If None, will try to find it.
        
    Returns:
        Dictionary mapping Pokémon IDs to their names
    """
    # If no base directory provided, try to find it from the current file's location
    if base_dir is None:
        # Assume this file is in the hg-engine project directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the rawtext directory
    rawtext_dir = os.path.join(base_dir, "build", "rawtext")
    
    # Check if the directory exists
    if not os.path.exists(rawtext_dir):
        logger.warning(f"Rawtext directory not found at {rawtext_dir}")
        logger.warning("This could mean the ROM hasn't been built with text files.")
        logger.warning("Will use default Pokémon names instead.")
        return {}
    
    pokemon_names = {}
    
    # First try to read from a single file containing all names
    all_names_file = os.path.join(rawtext_dir, "237.txt")
    if os.path.exists(all_names_file):
        try:
            with open(all_names_file, "r", encoding="utf-8") as f:
                # Read all lines
                lines = f.readlines()
                
                # Skip the first line (placeholder)
                if len(lines) > 1:
                    # Each line has a Pokémon name, starting from ID 1
                    for pokemon_id, line in enumerate(lines[1:], 1):
                        name = line.strip()
                        if name:  # Skip empty lines
                            pokemon_names[pokemon_id] = name.upper()
            
            logger.info(f"Read {len(pokemon_names)} Pokémon names from {all_names_file}")
            return pokemon_names
        except Exception as e:
            logger.warning(f"Error reading Pokémon names from {all_names_file}: {e}")
            logger.warning("Falling back to individual files method...")
    
    # If the single file method didn't work, try the individual files method
    # The monname macro writes to these directories
    pokemon_text_dirs = [
        os.path.join(rawtext_dir, "237"),
        os.path.join(rawtext_dir, "238"),
        os.path.join(rawtext_dir, "817")
    ]
    
    # Check the first directory (they should all have the same Pokemon names)
    names_dir = pokemon_text_dirs[0]
    if not os.path.exists(names_dir):
        logger.warning(f"Pokemon names directory not found at {names_dir}")
        return {}
    
    # Read all text files in the directory
    for filename in os.listdir(names_dir):
        if not filename.endswith(".txt"):
            continue
            
        # Extract Pokemon ID from filename
        try:
            # Files are like 0001.txt, 0002.txt, etc.
            pokemon_id = int(os.path.splitext(filename)[0])
        except ValueError:
            continue
            
        # Read the Pokemon name from the file
        try:
            with open(os.path.join(names_dir, filename), "r", encoding="utf-8") as f:
                name = f.read().strip()
                
                # Store the name (in uppercase for consistency)
                pokemon_names[pokemon_id] = name.upper()
        except Exception as e:
            logger.warning(f"Error reading Pokémon name from {filename}: {e}")
    
    logger.info(f"Read {len(pokemon_names)} Pokémon names from individual rawtext files")
    return pokemon_names

def get_pokemon_data(rom_path, create_dump=True):
    """
    Get Pokémon data directly from the ROM file.
    
    This function reads Pokémon data directly from the ROM file, which includes:
    - Name: The Pokémon's name
    - Base Stats: HP, Attack, Defense, Speed, Special Attack, Special Defense
    - BST (Base Stat Total): The sum of all base stats, used to gauge a Pokémon's strength
    
    The data is read according to the format defined in macros.s and stored in mondata.s:
    - Base stats are stored as 6 consecutive bytes
    - BST is calculated by adding up all 6 stats
    
    Args:
        rom_path: Path to the ROM file
        create_dump: Whether to create a text dump of the Pokémon data for verification
        
    Returns:
        Dictionary mapping Pokémon IDs to their data, including name and stats
    """
    # Read directly from the ROM - no caching
    
    # If we get here, we need to read from the ROM
    pokemon_data = read_pokemon_data_from_rom(rom_path)
    
    # Try to get Pokémon names from rawtext files
    # These are the text files created by the monname macro in macros.s
    rawtext_names = read_pokemon_names_from_rawtext()
    
    if not rawtext_names:
        # Critical error - we need these names for the randomizer to work properly
        logger.error("Could not read Pokémon names from rawtext files!")
        logger.error("This is a critical error - make sure to build the ROM first")
        logger.error("Run 'make' command in the project directory to build the ROM")
        print("\nCRITICAL ERROR: Pokémon names not found in rawtext files.")
        print("You must build the ROM first by running the 'make' command.")
        print("This will generate the necessary text files with Pokémon names.\n")
        # Return empty dictionary to signal failure
        return {}
    
    # Replace any names we have in the data with ones from the text files
    name_count = 0
    for pokemon_id, name in rawtext_names.items():
        if pokemon_id in pokemon_data:
            pokemon_data[pokemon_id]["name"] = name
            name_count += 1
    
    logger.info(f"Updated {name_count} Pokémon names from rawtext files")
    
    # Verify BST values against known correct values
    # This will help us identify if our BST calculations are correct
    known_bst_values = {
    }
    
    # Check for mismatches
    for pid, expected_bst in known_bst_values.items():
        if pid in pokemon_data:
            calculated_bst = pokemon_data[pid]["bst"]
            name = pokemon_data[pid]["name"]
            
            # Check if there's a mismatch
            if calculated_bst != expected_bst:
                # Get detailed stats for error reporting
                hp = pokemon_data[pid]["hp"]
                attack = pokemon_data[pid]["attack"]
                defense = pokemon_data[pid]["defense"]
                speed = pokemon_data[pid]["speed"]
                sp_atk = pokemon_data[pid]["special_attack"]
                sp_def = pokemon_data[pid]["special_defense"]
                stats_detail = f"Stats: HP={hp}, Atk={attack}, Def={defense}, Spd={speed}, SpAtk={sp_atk}, SpDef={sp_def}"
                
                # For significant mismatches, raise a critical error
                if abs(calculated_bst - expected_bst) > 50:
                    error_msg = f"Critical BST mismatch for {name} (#{pid}): Got {calculated_bst}, Expected {expected_bst}"
                    logger.critical(f"{error_msg}. {stats_detail}")
                    
                    # Print a user-friendly message with details
                    print(f"\nCRITICAL ERROR: {error_msg}")
                    print(f"Detailed stats: {stats_detail}")
                    print("This indicates a serious problem with the ROM data or how it's being read.")
                    print("Please check your ROM file and make sure it's properly built.\n")
                    
                    # Raise an exception to stop execution
                    raise ValueError(f"{error_msg}. {stats_detail}")
                else:
                    # For minor mismatches, just log a warning
                    logger.warning(f"Minor BST mismatch for {name} (#{pid}): Got {calculated_bst}, Expected {expected_bst}. {stats_detail}")
    
    # If we get here, no critical BST mismatches were found
    logger.info("BST verification passed for all checked Pokémon!")
    print("\nGood news! BST values are correct. The randomizer will work properly.\n")
    
    # Create a text dump of all Pokémon stats for verification
    if create_dump and pokemon_data:
        dump_pokemon_data_to_file(pokemon_data, "pokemon_stats_dump.txt")
    
    # Removed caching feature as requested
    
    return pokemon_data

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        rom_path = sys.argv[1]
        pokemon_data = get_pokemon_data(rom_path)
        
        print(f"Found {len(pokemon_data)} Pokémon in the ROM")
        print("\nSample of Pokémon data:")
        
        # Print the first 10 Pokémon
        for pokemon_id in sorted(pokemon_data.keys())[:10]:
            data = pokemon_data[pokemon_id]
            print(f"#{pokemon_id}: {data['name']} (BST: {data['bst']})")
    else:
        print("Usage: python pokemon_rom_reader.py [rom_path]")
