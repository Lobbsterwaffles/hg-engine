#!/usr/bin/env python3

"""
Pokémon Encounter Randomizer

A standalone tool for randomizing wild Pokémon encounters in hg-engine ROM files.
This tool will replace each Pokémon with another of similar strength (within 10% BST).
Once a Pokémon is replaced, all instances of that Pokémon will be replaced with the same new one.

How to use:
1. Put this script in the same folder as your ROM file
2. Open a command prompt/terminal in that folder
3. Type: python pokemon_encounter_randomizer.py your_rom_file.nds
4. A new randomized ROM will be created with "_randomized" added to the filename
"""

import os
import sys
import struct
import random
import binascii
import argparse
from collections import defaultdict
import subprocess  # Added back for ndstool and narcpy calls
import tempfile
import shutil
import struct
from pathlib import Path

# ==========================================================
# POKÉMON DATA - Base Stat Totals for matching similar strength
# ==========================================================

POKEMON_BST = {
    # Gen 1
    1: {"name": "BULBASAUR", "bst": 318},
    2: {"name": "IVYSAUR", "bst": 405},
    3: {"name": "VENUSAUR", "bst": 525},
    4: {"name": "CHARMANDER", "bst": 309},
    5: {"name": "CHARMELEON", "bst": 405},
    6: {"name": "CHARIZARD", "bst": 534},
    7: {"name": "SQUIRTLE", "bst": 314},
    8: {"name": "WARTORTLE", "bst": 405},
    9: {"name": "BLASTOISE", "bst": 530},
    10: {"name": "CATERPIE", "bst": 195},
    11: {"name": "METAPOD", "bst": 205},
    12: {"name": "BUTTERFREE", "bst": 395},
    13: {"name": "WEEDLE", "bst": 195},
    14: {"name": "KAKUNA", "bst": 205},
    15: {"name": "BEEDRILL", "bst": 395},
    16: {"name": "PIDGEY", "bst": 251},
    17: {"name": "PIDGEOTTO", "bst": 349},
    18: {"name": "PIDGEOT", "bst": 479},
    19: {"name": "RATTATA", "bst": 253},
    20: {"name": "RATICATE", "bst": 413},
    21: {"name": "SPEAROW", "bst": 262},
    22: {"name": "FEAROW", "bst": 442},
    23: {"name": "EKANS", "bst": 288},
    24: {"name": "ARBOK", "bst": 438},
    25: {"name": "PIKACHU", "bst": 320},
    26: {"name": "RAICHU", "bst": 485},
    27: {"name": "SANDSHREW", "bst": 300},
    28: {"name": "SANDSLASH", "bst": 450},
    29: {"name": "NIDORAN_F", "bst": 275},
    30: {"name": "NIDORINA", "bst": 365},
    31: {"name": "NIDOQUEEN", "bst": 505},
    32: {"name": "NIDORAN_M", "bst": 273},
    33: {"name": "NIDORINO", "bst": 365},
    34: {"name": "NIDOKING", "bst": 505},
    35: {"name": "CLEFAIRY", "bst": 323},
    36: {"name": "CLEFABLE", "bst": 483},
    37: {"name": "VULPIX", "bst": 299},
    38: {"name": "NINETALES", "bst": 505},
    39: {"name": "JIGGLYPUFF", "bst": 270},
    40: {"name": "WIGGLYTUFF", "bst": 435},
    # Gen 2
    152: {"name": "CHIKORITA", "bst": 318},
    153: {"name": "BAYLEEF", "bst": 410},
    154: {"name": "MEGANIUM", "bst": 525},
    155: {"name": "CYNDAQUIL", "bst": 309},
    156: {"name": "QUILAVA", "bst": 405},
    157: {"name": "TYPHLOSION", "bst": 534},
    158: {"name": "TOTODILE", "bst": 314},
    159: {"name": "CROCONAW", "bst": 405},
    160: {"name": "FERALIGATR", "bst": 530},
    161: {"name": "SENTRET", "bst": 215},
    162: {"name": "FURRET", "bst": 415},
    163: {"name": "HOOTHOOT", "bst": 262},
    164: {"name": "NOCTOWL", "bst": 442},
    # Note: You should add more Pokémon to this list
    # You can find BST data on sites like Bulbapedia
}

# Add placeholder entries for Pokémon not in our list (prevents errors)
for i in range(1, 252):  # Gen 1-2
    if i not in POKEMON_BST:
        POKEMON_BST[i] = {"name": f"POKEMON_{i}", "bst": 300}  # Default BST

# Pokémon species that should not be randomized (legendaries, special Pokémon)
SPECIAL_POKEMON = [
    144, 145, 146,  # Articuno, Zapdos, Moltres
    150, 151,       # Mewtwo, Mew
    243, 244, 245,  # Raikou, Entei, Suicune
    249, 250, 251,  # Lugia, Ho-Oh, Celebi
    # Add any other special Pokémon you don't want randomized
]

# ==========================================================
# ROM HANDLING FUNCTIONS
# ==========================================================

def make_backup(rom_path):
    """Create a backup of the original ROM file."""
    backup_path = rom_path + ".backup"
    if not os.path.exists(backup_path):
        print(f"Creating backup of original ROM at {backup_path}")
        with open(rom_path, "rb") as original:
            with open(backup_path, "wb") as backup:
                backup.write(original.read())
    else:
        print(f"Backup already exists at {backup_path}")

def search_narc_file(rom_data):
    """
    Search for the a037 NARC file in the ROM.
    NARC files start with the bytes 'NARC' followed by file size info.
    """
    print("Searching for encounter data NARC file (a037)...")
    
    # Search for NARC files
    narc_positions = []
    for i in range(0, len(rom_data) - 4):
        if rom_data[i:i+4] == b'NARC':
            narc_positions.append(i)
    
    print(f"Found {len(narc_positions)} potential NARC files")
    
    # In a real implementation, we'd need to identify which NARC is a037
    # For now, we'll provide a framework that can be completed later
    
    # Placeholder - in reality, we'd need to analyze ROM structure
    return {
        "narc_offset": narc_positions[0] if narc_positions else None,
        "estimated_size": 100000,  # Placeholder size
        "narc_positions": narc_positions  # Include the positions we found
    }

def find_similar_strength_pokemon(species_id, species_mapping, used_replacements):
    """Find a Pokémon with similar BST (within 10%) to replace the given species."""
    # If this species has already been mapped, use the consistent replacement
    if species_id in species_mapping:
        return species_mapping[species_id]
    
    # Don't replace special Pokémon
    if species_id in SPECIAL_POKEMON:
        species_mapping[species_id] = species_id
        return species_id
    
    # If we don't know the BST, don't replace
    if species_id not in POKEMON_BST:
        species_mapping[species_id] = species_id
        return species_id
    
    target_bst = POKEMON_BST[species_id]["bst"]
    min_bst = target_bst - (target_bst * 0.1)  # 10% below
    max_bst = target_bst + (target_bst * 0.1)  # 10% above
    
    candidates = []
    
    for id, data in POKEMON_BST.items():
        # Skip special Pokémon, the original species, and already used replacements
        if (id in SPECIAL_POKEMON or 
            id == species_id or 
            id in used_replacements):
            continue
            
        # Check if BST is within range
        if min_bst <= data["bst"] <= max_bst:
            candidates.append(id)
    
    # If we found candidates, pick one randomly
    if candidates:
        replacement = random.choice(candidates)
        species_mapping[species_id] = replacement
        used_replacements.add(replacement)
        return replacement
    
    # If no suitable replacement, keep the original
    species_mapping[species_id] = species_id
    return species_id

# ==========================================================
# MAIN RANDOMIZATION FUNCTION
# ==========================================================

def randomize_encounters(rom_path, output_path=None, seed=None):
    """Main function to randomize wild encounters in a ROM."""
    
    try:
        # ---------------------------
        # 1. Set random seed
        # ---------------------------
        if seed is not None:
            random.seed(seed)
            print(f"Using random seed: {seed}")
        else:
            random_seed = random.randrange(100000)
            random.seed(random_seed)
            print(f"Using random seed: {random_seed}")
        
        # ---------------------------
        # 2. Prepare paths & backups
        # ---------------------------
        rom_path = os.path.abspath(rom_path)
        if not os.path.isfile(rom_path):
            print(f"Error: ROM file '{rom_path}' not found!")
            return False
        
        # For Windows, we need the .exe extension
        ndstool_path = os.path.join(os.path.dirname(__file__), "tools", "ndstool.exe")
        narcpy_path  = os.path.join(os.path.dirname(__file__), "tools", "narcpy.py")
        if not os.path.isfile(ndstool_path):
            print("Error: ndstool.exe not found in tools folder.")
            return False
        if not os.path.isfile(narcpy_path):
            print("Error: narcpy.py not found in tools folder.")
            return False
        
        if output_path is None:
            output_path = os.path.splitext(rom_path)[0] + "_randomized.nds"
        output_path = os.path.abspath(output_path)
        
        make_backup(rom_path)
        
        # ---------------------------
        # 3. Extract ROM with ndstool
        # ---------------------------
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir    = os.path.join(tmp_dir, "base")
            filesys_dir = os.path.join(tmp_dir, "filesys")
            overlay_dir = os.path.join(base_dir, "overlay")
            os.makedirs(base_dir, exist_ok=True)
            os.makedirs(filesys_dir, exist_ok=True)
            os.makedirs(overlay_dir, exist_ok=True)

            print("[1/5] Extracting ROM files (this may take a moment)...")
            # Get just the name of the ndstool executable
            ndstool_name = os.path.basename(ndstool_path)
            # Get the directory where ndstool.exe is located
            tools_dir = os.path.dirname(ndstool_path)
            
            # Make command using just the executable name (we'll run from its directory)
            extract_cmd = ["./"+ndstool_name, "-x", rom_path,
                           "-9", os.path.join(base_dir, "arm9.bin"),
                           "-7", os.path.join(base_dir, "arm7.bin"),
                           "-y9", os.path.join(base_dir, "overarm9.bin"),
                           "-y7", os.path.join(base_dir, "overarm7.bin"),
                           "-d", filesys_dir,
                           "-y", overlay_dir,
                           "-t", os.path.join(base_dir, "banner.bin"),
                           "-h", os.path.join(base_dir, "header.bin")]
            
            # Run the command from the tools directory so it can find its DLL files
            old_dir = os.getcwd()
            os.chdir(tools_dir)
            try:
                subprocess.run(extract_cmd, check=True)
            finally:
                # Always change back to the original directory when done
                os.chdir(old_dir)

            # ---------------------------
            # 4. Extract encounter NARC
            # ---------------------------
            encounter_narc_path = os.path.join(filesys_dir, "a", "0", "3", "7")
            if not os.path.isfile(encounter_narc_path):
                print("Error: Encounter NARC a/0/3/7 not found in extracted ROM.")
                return False
            encounters_dir = os.path.join(tmp_dir, "encounters")
            os.makedirs(encounters_dir, exist_ok=True)
            print("[2/5] Extracting encounter NARC with narcpy...")
            subprocess.run([sys.executable, narcpy_path, "extract", encounter_narc_path, "-o", encounters_dir], check=True)

            # ---------------------------
            # 5. Randomize each encounter file
            # ---------------------------
            print("[3/5] Randomizing encounters...")
            species_mapping: dict[int, int] = {}
            used_replacements: set[int] = set()
            for fname in os.listdir(encounters_dir):
                fpath = os.path.join(encounters_dir, fname)
                with open(fpath, "rb") as f:
                    data = bytearray(f.read())
                # Iterate over 2-byte species entries
                for off in range(0, len(data)-1, 2):
                    val = struct.unpack_from("<H", data, off)[0]
                    species_id = val & 0x7FF  # lower 11 bits
                    form_bits  = val & 0xF800 # upper 5 bits stay
                    if species_id == 0 or species_id in SPECIAL_POKEMON:
                        continue
                    new_id = find_similar_strength_pokemon(species_id, species_mapping, used_replacements)
                    new_val = (new_id & 0x7FF) | form_bits
                    struct.pack_into("<H", data, off, new_val)
                # Write back
                with open(fpath, "wb") as f:
                    f.write(data)
            print(f"    -> Replaced {len(species_mapping)} species across all areas.")

            # ---------------------------
            # 6. Rebuild encounter NARC
            # ---------------------------
            rebuilt_narc = os.path.join(tmp_dir, "encounters_rebuilt.narc")
            print("[4/5] Rebuilding NARC with narcpy...")
            subprocess.run([sys.executable, narcpy_path, "create", rebuilt_narc, encounters_dir], check=True)
            # Replace old NARC
            shutil.copy2(rebuilt_narc, encounter_narc_path)

            # ---------------------------
            # 7. Rebuild ROM with ndstool
            # ---------------------------
            print("[5/5] Rebuilding ROM...")
            # Same approach as earlier - run ndstool from its directory
            build_cmd = ["./"+ndstool_name, "-c", output_path,
                         "-9", os.path.join(base_dir, "arm9.bin"),
                         "-7", os.path.join(base_dir, "arm7.bin"),
                         "-y9", os.path.join(base_dir, "overarm9.bin"),
                         "-y7", os.path.join(base_dir, "overarm7.bin"),
                         "-d", filesys_dir,
                         "-y", overlay_dir,
                         "-t", os.path.join(base_dir, "banner.bin"),
                         "-h", os.path.join(base_dir, "header.bin")]
                         
            # Change to tools directory to run the command
            os.chdir(tools_dir)
            try:
                subprocess.run(build_cmd, check=True)
            finally:
                # Change back to the original directory
                os.chdir(old_dir)

        print(f"\nRandomization complete! Output ROM: {output_path}")
        return True
    
    except Exception as e:
        import traceback
        print(f"\nError during randomization: {e}")
        traceback.print_exc()
        return False

# ==========================================================
# COMMAND LINE INTERFACE
# ==========================================================

def main():
    """Handle command line arguments and run the randomizer."""
    parser = argparse.ArgumentParser(
        description="Randomize wild Pokémon encounters in hg-engine ROMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pokemon_encounter_randomizer.py mygame.nds
  python pokemon_encounter_randomizer.py mygame.nds -o mygame_random.nds
  python pokemon_encounter_randomizer.py mygame.nds -s 12345
"""
    )
    parser.add_argument("rom_path", help="Path to the input ROM file")
    parser.add_argument("-o", "--output", help="Path for the randomized ROM (default: adds '_randomized' to filename)")
    parser.add_argument("-s", "--seed", type=int, help="Random seed for reproducible results")
    
    args = parser.parse_args()
    
    # Check if the input ROM exists
    if not os.path.exists(args.rom_path):
        print(f"Error: ROM file '{args.rom_path}' does not exist!")
        return 1
    
    # Perform the randomization
    success = randomize_encounters(args.rom_path, args.output, args.seed)
    
    if success:
        output_name = args.output if args.output else os.path.splitext(args.rom_path)[0] + "_randomized.nds"
        print(f"\nCreated file: {output_name}")
        print("Remember this is a framework version that doesn't change encounters yet.")
    else:
        print("\nRandomization failed. Please check the error messages above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
