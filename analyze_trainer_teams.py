#!/usr/bin/env python3
"""
Trainer Team Size Analyzer
-------------------------
This script analyzes trainer team sizes in Pokémon HGSS ROMs.
It shows you how many Pokémon each boss trainer has.
"""

import ndspy.rom
import ndspy.narc
import os
import sys
import argparse

# NARC file paths
TRAINER_POKEMON_NARC_PATH = "a/0/5/6"  # Pokémon data
TRAINER_DATA_NARC_PATH = "a/0/5/5"     # Trainer data including poke_count

# Known boss trainers with their IDs and names
BOSS_TRAINERS = {
    20: "Falkner (Flying)",
    21: "Bugsy (Bug)",
    30: "Whitney (Normal)",
    33: "Morty (Ghost)",
    38: "Chuck (Fighting)",
    39: "Jasmine (Steel)",
    47: "Pryce (Ice)",
    56: "Clair (Dragon)",
    # Kanto Gym Leaders
    60: "Brock (Rock)",
    62: "Misty (Water)",
    67: "Lt. Surge (Electric)",
    72: "Erika (Grass)",
    77: "Janine (Poison)",
    82: "Sabrina (Psychic)",
    88: "Blaine (Fire)",
    93: "Blue (Normal)",
    # Elite Four
    94: "Will (Psychic)",
    95: "Koga (Poison)",
    96: "Bruno (Fighting)",
    97: "Karen (Dark)",
    98: "Lance (Dragon)",
}

# Rival (Silver) battles
RIVAL_BATTLES = {
    112: "Rival (First Battle)",
    113: "Rival (Azalea)",
    114: "Rival (Burned Tower)",
    115: "Rival (Goldenrod Underground)",
    116: "Rival (Victory Road)",
    117: "Rival (Mt. Moon)",
    118: "Rival (Dragon's Den)",
    119: "Rival (Indigo Plateau)",
}

def get_trainer_poke_count(rom, trainer_id):
    """
    Get the poke_count value from trainer metadata.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        
    Returns:
        int: Number of Pokémon in the trainer's team
    """
    try:
        # Get the trainer data NARC
        narc_file_id = rom.filenames.idOf(TRAINER_DATA_NARC_PATH)
        trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
        
        # Check if trainer exists
        if trainer_id >= len(trainer_data_narc.files):
            return None
        
        # Get trainer's data
        trainer_data = trainer_data_narc.files[trainer_id]
        
        # poke_count is at offset 3
        poke_count = trainer_data[3]
        return poke_count
    except Exception as e:
        print(f"Error reading trainer {trainer_id}: {e}")
        return None

def get_trainer_pokemon_count_from_data(rom, trainer_id):
    """
    Count the number of Pokémon by examining the Pokémon data file.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        
    Returns:
        tuple: (count, has_moves) - Number of Pokémon and whether they have moves
    """
    try:
        # Get the trainer Pokémon NARC
        narc_file_id = rom.filenames.idOf(TRAINER_POKEMON_NARC_PATH)
        trainer_narc_data = ndspy.narc.NARC(rom.files[narc_file_id])
        
        # Check if trainer exists
        if trainer_id >= len(trainer_narc_data.files):
            return None, None
        
        # Get trainer's Pokémon data
        pokemon_data = trainer_narc_data.files[trainer_id]
        
        # Check if data exists
        if not pokemon_data:
            return 0, False
        
        # Check data size - trainers with moves have 18 bytes per Pokémon
        # Trainers without moves have 8 bytes per Pokémon
        if len(pokemon_data) % 18 == 0 and len(pokemon_data) > 0:
            return len(pokemon_data) // 18, True
        elif len(pokemon_data) % 8 == 0 and len(pokemon_data) > 0:
            return len(pokemon_data) // 8, False
        else:
            print(f"Warning: Trainer {trainer_id} has unusual data size: {len(pokemon_data)} bytes")
            return None, None
    except Exception as e:
        print(f"Error analyzing trainer {trainer_id}: {e}")
        return None, None

def analyze_trainers(rom, trainers_to_check=None):
    """
    Analyze team sizes for all trainers or a specific list.
    
    Args:
        rom: The ROM object
        trainers_to_check: Optional list of trainer IDs to check
        
    Returns:
        dict: Dictionary with analysis results
    """
    results = {}
    
    # If no specific trainers provided, use all boss trainers and rivals
    if trainers_to_check is None:
        trainers_to_check = list(BOSS_TRAINERS.keys()) + list(RIVAL_BATTLES.keys())
    
    # Check each trainer
    for trainer_id in trainers_to_check:
        # Get metadata poke_count
        poke_count = get_trainer_poke_count(rom, trainer_id)
        
        # Get actual count from data size
        actual_count, has_moves = get_trainer_pokemon_count_from_data(rom, trainer_id)
        
        # Get trainer name
        if trainer_id in BOSS_TRAINERS:
            trainer_name = BOSS_TRAINERS[trainer_id]
        elif trainer_id in RIVAL_BATTLES:
            trainer_name = RIVAL_BATTLES[trainer_id]
        else:
            trainer_name = f"Trainer {trainer_id}"
        
        # Store results
        results[trainer_id] = {
            "name": trainer_name,
            "poke_count": poke_count,
            "actual_count": actual_count,
            "has_moves": has_moves,
            "consistent": poke_count == actual_count
        }
    
    return results

def print_analysis_results(results):
    """
    Print the analysis results in a readable format.
    
    Args:
        results: Dictionary with analysis results
    """
    print("\n=== Trainer Team Size Analysis ===\n")
    print(f"{'ID':<5} {'Trainer':<30} {'Size':<5} {'Actual':<8} {'Moves':<7} {'OK?':<4}")
    print("=" * 65)
    
    # First, print gym leaders
    print("\n--- Gym Leaders ---")
    gym_leader_ids = [id for id in results.keys() if id in BOSS_TRAINERS and id < 94]
    for trainer_id in sorted(gym_leader_ids):
        r = results[trainer_id]
        print(f"{trainer_id:<5} {r['name']:<30} {r['poke_count']:<5} {r['actual_count']:<8} "
              f"{'Yes' if r['has_moves'] else 'No':<7} {'OK' if r['consistent'] else 'NO':<4}")
    
    # Then print Elite Four
    print("\n--- Elite Four ---")
    elite_four_ids = [id for id in results.keys() if id >= 94 and id in BOSS_TRAINERS]
    for trainer_id in sorted(elite_four_ids):
        r = results[trainer_id]
        print(f"{trainer_id:<5} {r['name']:<30} {r['poke_count']:<5} {r['actual_count']:<8} "
              f"{'Yes' if r['has_moves'] else 'No':<7} {'OK' if r['consistent'] else 'NO':<4}")
    
    # Finally print rival battles
    print("\n--- Rival Battles ---")
    rival_ids = [id for id in results.keys() if id in RIVAL_BATTLES]
    for trainer_id in sorted(rival_ids):
        r = results[trainer_id]
        print(f"{trainer_id:<5} {r['name']:<30} {r['poke_count']:<5} {r['actual_count']:<8} "
              f"{'Yes' if r['has_moves'] else 'No':<7} {'OK' if r['consistent'] else 'NO':<4}")
    
    # Check for inconsistencies
    inconsistencies = [id for id, r in results.items() if not r['consistent']]
    if inconsistencies:
        print("\nWARNING: Found inconsistencies in trainer data!")
        print(f"{len(inconsistencies)} trainers have mismatched poke_count and actual Pokémon counts.")
    else:
        print("\nAll trainer data is consistent!")

def main():
    """Main function for running the script directly"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom_file", help="Path to the ROM file")
    args = parser.parse_args()
    
    # Check if ROM file exists
    if not os.path.exists(args.rom_file):
        print(f"Error: ROM file {args.rom_file} not found")
        return 1
        
    # Open ROM file
    print(f"Analyzing ROM file: {args.rom_file}")
    rom = ndspy.rom.NintendoDSRom.fromFile(args.rom_file)
    
    # Analyze trainers
    results = analyze_trainers(rom)
    
    # Print results
    print_analysis_results(results)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
