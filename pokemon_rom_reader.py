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
            
            # Default names for common Pokémon to ensure we have something readable
            # This is a fallback in case we can't read the names from the ROM
            default_names = {
                1: "NONE", # Usually a placeholder
                2: "BULBASAUR",
                3: "IVYSAUR",
                4: "VENUSAUR",
                5: "CHARMANDER",
                6: "CHARMELEON",
                7: "CHARIZARD",
                8: "SQUIRTLE",
                9: "WARTORTLE",
                10: "BLASTOISE",
                25: "PIKACHU",
                26: "RAICHU",
                150: "MEWTWO",
                151: "MEW",
                # Add more defaults as needed
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
            pokemon_id = i + 1  # Pokémon IDs start at 1
            
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
