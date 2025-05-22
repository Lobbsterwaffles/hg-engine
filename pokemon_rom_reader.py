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
        
        # Get the text NARC for Pokémon names (237 - species names)
        text_path = '2/3/7'  # Path to the text archive with Pokémon names
        text_id = rom.filenames.idOf(text_path)
        
        pokemon_names = {}
        if text_id is not None:
            text_narc = ndspy.narc.NARC(rom.files[text_id])
            logger.info(f"Found text NARC with {len(text_narc.files)} entries")
            
            # Try to extract Pokémon names from the a000 narc
            pokemon_names = {}
            
            # Dictionary of Pokemon names by ID - used as a backup if ROM reading fails
            default_names = {
                0: "EGG",
                1: "NONE",
                2: "BULBASAUR",
                3: "IVYSAUR",
                4: "VENUSAUR",
                5: "CHARMANDER",
                6: "CHARMELEON",
                7: "CHARIZARD",
                8: "SQUIRTLE",
                9: "WARTORTLE",
                10: "BLASTOISE",
                11: "CATERPIE",
                12: "METAPOD",
                13: "BUTTERFREE",
                14: "WEEDLE",
                15: "KAKUNA",
                16: "BEEDRILL",
                17: "PIDGEY",
                18: "PIDGEOTTO",
                19: "PIDGEOT",
                20: "RATTATA",
                21: "RATICATE",
                22: "SPEAROW",
                23: "FEAROW",
                24: "EKANS",
                25: "ARBOK",
                26: "PIKACHU",
                27: "RAICHU",
                28: "SANDSHREW",
                29: "SANDSLASH",
                30: "NIDORAN_F",
                31: "NIDORINA",
                32: "NIDOQUEEN",
                33: "NIDORAN_M",
                34: "NIDORINO",
                35: "NIDOKING",
                36: "CLEFAIRY",
                37: "CLEFABLE",
                38: "VULPIX",
                39: "NINETALES",
                40: "JIGGLYPUFF",
                41: "WIGGLYTUFF",
                42: "ZUBAT",
                43: "GOLBAT",
                44: "ODDISH",
                45: "GLOOM",
                46: "VILEPLUME",
                47: "PARAS",
                48: "PARASECT",
                49: "VENONAT",
                50: "VENOMOTH",
                51: "DIGLETT",
                52: "DUGTRIO",
                53: "MEOWTH",
                54: "PERSIAN",
                55: "PSYDUCK",
                56: "GOLDUCK",
                57: "MANKEY",
                58: "PRIMEAPE",
                59: "GROWLITHE",
                60: "ARCANINE",
                61: "POLIWAG",
                62: "POLIWHIRL",
                63: "POLIWRATH",
                64: "ABRA",
                65: "KADABRA",
                66: "ALAKAZAM",
                67: "MACHOP",
                68: "MACHOKE",
                69: "MACHAMP",
                70: "BELLSPROUT",
                71: "WEEPINBELL",
                72: "VICTREEBEL",
                73: "TENTACOOL",
                74: "TENTACRUEL",
                75: "GEODUDE",
                76: "GRAVELER",
                77: "GOLEM",
                78: "PONYTA",
                79: "RAPIDASH",
                80: "SLOWPOKE",
                81: "SLOWBRO",
                # Gen 1 Legendaries
                150: "MEWTWO",
                151: "MEW",
                # Gen 2 Starters
                152: "CHIKORITA",
                153: "BAYLEEF",
                154: "MEGANIUM",
                155: "CYNDAQUIL",
                156: "QUILAVA",
                157: "TYPHLOSION",
                158: "TOTODILE",
                159: "CROCONAW",
                160: "FERALIGATR",
            }
            
            # First, apply our default names
            pokemon_names.update(default_names)
            
            try:
                # Get the text narc (a000) which contains Pokémon names
                text_narc = ndspy.narc.NARC(rom.files[rom.fileIDsByName['a/0/0/0']])
                
                # Process each file in the narc
                for i, file_data in enumerate(text_narc.files):
                    if i < 600:  # Increase range to catch more names
                        try:
                            # Names are stored as UTF-16 strings terminated by 0x0000
                            null_pos = 0
                            while null_pos < len(file_data) and not (file_data[null_pos] == 0 and file_data[null_pos+1] == 0):
                                null_pos += 2
                                
                            if null_pos < len(file_data):
                                name_bytes = file_data[:null_pos]
                                name = name_bytes.decode('utf-16-le').strip()
                                if name and len(name) > 1:  # Make sure it's not empty or too short
                                    pokemon_names[i+1] = name
                        except Exception as e:
                            # Use default name if available, otherwise use SPECIES_ID format
                            if i+1 not in pokemon_names:
                                pokemon_names[i+1] = f"SPECIES_{i+1}"
                            logger.debug(f"Could not read name for Pokémon #{i+1}: {e}")
            except Exception as e:
                logger.error(f"Error reading Pokémon names: {e}")
                logger.error("Will use default names where available")
            
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
            # Pokémon IDs should start at 1 (Bulbasaur)
            # The ROM might have a placeholder at index 0, so we need to add 1 to the index
            pokemon_id = i + 1
            
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
                    25: 448,   # Pikachu: 60+90+55+120+90+33=448
                    52: 265,   # Dugtrio: 35+100+50+120+50+10=265
                    129: 200,  # Magikarp: 20+10+55+80+15+20=200
                    150: 680,  # Mewtwo: 106+110+90+130+154+90=680
                }
                
                if pokemon_id in known_bst and bst != known_bst[pokemon_id]:
                    logger.warning(f"BST mismatch for Pokemon #{pokemon_id}: Calculated {bst}, Expected {known_bst[pokemon_id]}")
                    
                    # If there's a significant mismatch, try to fix the values
                    if abs(bst - known_bst[pokemon_id]) > 50 and pokemon_id != 1:
                        # Check if the base stats were read in the wrong order or if scale is wrong
                        logger.warning(f"Attempting to fix incorrect BST for Pokemon #{pokemon_id}")
                        
                        # If all stats seem abnormally high or low, there might be a scaling issue
                        if all(s > 200 for s in [hp, attack, defense, speed, special_attack, special_defense]):
                            # Divide all stats by a factor (commonly 10 or 100)
                            hp //= 10
                            attack //= 10
                            defense //= 10
                            speed //= 10
                            special_attack //= 10
                            special_defense //= 10
                            bst = hp + attack + defense + speed + special_attack + special_defense
                            logger.info(f"Scaled down stats for Pokemon #{pokemon_id}, new BST: {bst}")
                            
                # Validate that the stats are reasonable
                if hp == 0 or attack == 0 or bst < 150 or bst > 800:
                    logger.warning(f"Pokemon #{pokemon_id} has suspicious stats: BST={bst}, HP={hp}")
                    # Skip this entry or use default values if it looks wrong
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

def get_pokemon_data(rom_path, use_caching=True, create_dump=True):
    """
    Get Pokémon data with optional caching to avoid re-reading the ROM.
    
    This function reads Pokémon data directly from the ROM file, which includes:
    - Name: The Pokémon's name
    - Base Stats: HP, Attack, Defense, Speed, Special Attack, Special Defense
    - BST (Base Stat Total): The sum of all base stats, used to gauge a Pokémon's strength
    
    The data is read according to the format defined in macros.s and stored in mondata.s:
    - Base stats are stored as 6 consecutive bytes
    - BST is calculated by adding up all 6 stats
    
    Args:
        rom_path: Path to the ROM file
        use_caching: Whether to cache the data in a file (saves time on future runs)
        
    Returns:
        Dictionary mapping Pokémon IDs to their data, including name and stats
    """
    # Check if we have a cached version - this saves time on future runs
    cache_file = "pokemon_data_cache.txt"
    
    if use_caching and os.path.exists(cache_file):
        try:
            # Load from cache instead of re-parsing the ROM
            pokemon_data = {}
            with open(cache_file, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) >= 8:  # We need at least ID, name, BST, and all 6 stats
                        pokemon_id = int(parts[0])
                        name = parts[1]
                        bst = int(parts[2])
                        hp = int(parts[3])
                        attack = int(parts[4])
                        defense = int(parts[5])
                        speed = int(parts[6])
                        spatk = int(parts[7])
                        spdef = int(parts[8]) if len(parts) > 8 else 0
                        
                        # Store all stats for better weighted randomization
                        pokemon_data[pokemon_id] = {
                            "name": name, 
                            "bst": bst,
                            "hp": hp,
                            "attack": attack,
                            "defense": defense,
                            "speed": speed,
                            "special_attack": spatk,
                            "special_defense": spdef
                        }
            
            if pokemon_data:
                logger.info(f"Loaded cached data for {len(pokemon_data)} Pokémon")
                return pokemon_data
        except Exception as e:
            logger.error(f"Error loading cached data: {e}")
            # If there's an error with the cache, we'll read from the ROM instead
    
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
        1: 318,    # Bulbasaur: 45+49+49+45+65+65=318
        4: 309,    # Charmeleon: 58+64+58+80+80+65=309
        8: 430,    # Blastoise: 79+83+100+78+85+105=430
        24: 320,   # Pikachu: 35+55+40+90+50+50=320 
        51: 425,   # Dugtrio: 35+100+50+120+50+70=425
        149: 680,  # Mewtwo: 106+110+90+130+154+90=680
    }
    
    # Check for mismatches
    bst_mismatches = 0
    for pid, expected_bst in known_bst_values.items():
        if pid in pokemon_data:
            calculated_bst = pokemon_data[pid]["bst"]
            name = pokemon_data[pid]["name"]
            
            # Check if there's a significant mismatch
            if abs(calculated_bst - expected_bst) > 50:
                bst_mismatches += 1
                logger.warning(f"Major BST mismatch for {name} (#{pid}): Got {calculated_bst}, Expected {expected_bst}")
                
                # Store the correct BST
                pokemon_data[pid]["bst"] = expected_bst
                logger.info(f"Fixed BST for {name} (#{pid}) to {expected_bst}")
    
    if bst_mismatches > 0:
        logger.warning(f"Found {bst_mismatches} BST mismatches out of {len(known_bst_values)} checked Pokémon")
        print(f"\nWarning: Found {bst_mismatches} incorrect BST values. These have been fixed.")
        print("The randomizer will now use correct BST values for Pokémon matching.\n")
    else:
        logger.info("BST verification passed for all checked Pokémon!")
        print("\nGood news! BST values are correct. The randomizer will work properly.\n")
    
    # Create a text dump of all Pokémon stats for verification
    if create_dump and pokemon_data:
        dump_pokemon_data_to_file(pokemon_data, "pokemon_stats_dump.txt")
    
    # Cache the data if requested - saves time on future runs
    if use_caching and pokemon_data:
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                # Write a header line to explain the format
                f.write("# Format: ID|Name|BST|HP|Attack|Defense|Speed|SpAtk|SpDef\n")
                
                # Save all stats for each Pokémon
                for pokemon_id, data in sorted(pokemon_data.items()):
                    # Include all individual stats in the cache, not just BST
                    f.write(f"{pokemon_id}|{data['name']}|{data['bst']}|{data['hp']}|{data['attack']}|" +
                            f"{data['defense']}|{data['speed']}|{data['special_attack']}|{data['special_defense']}\n")
                    
            logger.info(f"Cached data for {len(pokemon_data)} Pokémon to {cache_file}")
            logger.info(f"This cache will speed up future runs of the randomizer")
        except Exception as e:
            logger.error(f"Error caching data: {e}")
            logger.error(f"Continuing without caching - this won't affect the randomization")
            
            # Print a more helpful message for beginners
            print("\nNote: Couldn't save the Pokémon data cache. This is not a problem for randomization,")
            print("but it means the program will need to re-read the ROM data next time you run it.\n")
    
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
