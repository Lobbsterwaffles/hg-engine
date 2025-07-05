#!/usr/bin/env python3
"""
Team Size Adjuster for Pokémon HGSS
-----------------------------------
This script lets you adjust team sizes for specific trainers or groups of trainers.

It can:
1. Set all boss trainers to have full teams of 6 Pokémon
2. Set any trainer's team to a specific size
3. Update both Pokémon data and trainer metadata
"""

import ndspy.rom
import ndspy.narc
import sys
import os
import random
from construct import Container

# Import functions from our trainer Pokémon manager
from trainer_pokemon_manager import (
    get_trainer_pokemon,
    update_trainer_poke_count,
    save_trainer_pokemon,
    add_pokemon_to_trainer
)

# NARC file paths
TRAINER_POKEMON_NARC_PATH = "a/0/5/6"  # Pokémon data
TRAINER_DATA_NARC_PATH = "a/0/5/5"     # Trainer data including poke_count

# Define boss trainers
GYM_LEADERS = [
    "Falkner", "Bugsy", "Whitney", "Morty", "Chuck", 
    "Jasmine", "Pryce", "Clair", "Brock", "Misty",
    "Lt. Surge", "Erika", "Janine", "Sabrina", "Blaine", "Blue"
]

ELITE_FOUR = ["Will", "Koga", "Bruno", "Karen", "Lance"]

# Trainer IDs for Silver (Rival) battles
# The first battle should be excluded as it's too early for a full team
RIVAL_BATTLE_IDS = [
    # Format: (trainer_id, should_have_full_team)
    (112, False),  # First battle - starter only
    (113, True),   # Second battle - should have full team
    (114, True),   # Third battle
    (115, True),   # etc.
    (116, True),
    (117, True),
    (118, True),
    (119, True),
    (120, True),
    (121, True),
    (122, True),
    (123, True),
    (124, True),
    (125, True),
    (126, True),
    (127, True),
    (128, True),
]

def set_trainer_team_size(rom, trainer_id, target_size, mondata=None, min_level=None, max_level=None):
    """
    Set a trainer's team size to the specified target.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        target_size: The desired team size
        mondata: Optional Pokémon data for random species selection
        min_level: Minimum level for added Pokémon
        max_level: Maximum level for added Pokémon
        
    Returns:
        bool: True if successful
    """
    try:
        # Get the trainer's current Pokémon
        pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
        current_size = len(pokemon_list)
        
        # If already at target size, nothing to do
        if current_size == target_size:
            return True
        
        # If we need to remove Pokémon
        if current_size > target_size:
            # Remove from the end
            pokemon_list = pokemon_list[:target_size]
            
            # Save the updated list
            save_trainer_pokemon(rom, trainer_id, pokemon_list, has_moves)
            update_trainer_poke_count(rom, trainer_id, target_size)
            return True
            
        # If we need to add Pokémon
        if current_size < target_size:
            # Determine level for new Pokémon
            if min_level is None or max_level is None:
                # Use existing team's average level
                levels = [p.level for p in pokemon_list]
                avg_level = sum(levels) / len(levels) if levels else 30
                new_level = int(avg_level)
            else:
                new_level = random.randint(min_level, max_level)
            
            # Add new Pokémon
            for _ in range(target_size - current_size):
                if mondata:
                    # Choose a random Pokémon of similar strength to the existing team
                    # Get the average BST of the trainer's current Pokémon
                    avg_bst = 0
                    if pokemon_list:
                        bst_sum = 0
                        count = 0
                        for p in pokemon_list:
                            if p.species in mondata:
                                bst_sum += mondata[p.species].bst
                                count += 1
                        avg_bst = bst_sum / count if count else 450
                    else:
                        avg_bst = 450  # Default BST for empty teams
                    
                    # Find Pokémon with similar BST
                    candidates = []
                    for species_id, data in mondata.items():
                        # Skip special Pokémon like legendaries
                        if hasattr(data, 'special') and data.special:
                            continue
                        # Find Pokémon with BST within 10% of the average
                        if abs(data.bst - avg_bst) <= avg_bst * 0.1:
                            candidates.append(species_id)
                    
                    # If we found candidates, choose one randomly
                    if candidates:
                        species_id = random.choice(candidates)
                    else:
                        # Fallback - just pick something in the 400-500 BST range
                        species_id = random.randint(1, 493)  # Gen 4 Pokémon range
                else:
                    # No mondata provided, just pick a random species
                    species_id = random.randint(1, 493)  # Gen 4 Pokémon range
                
                # Create moves if trainer has Pokémon with moves
                moves = None
                if has_moves:
                    moves = [
                        random.randint(1, 467),  # Random move IDs
                        random.randint(1, 467),
                        random.randint(1, 467),
                        random.randint(1, 467)
                    ]
                
                # Add the Pokémon
                add_pokemon_to_trainer(rom, trainer_id, species_id, new_level, moves)
            
            return True
    except Exception as e:
        print(f"Error setting team size for trainer {trainer_id}: {e}")
        return False

def max_team_size_bosses(rom, trainer_names, gym_trainer_ids=None, target_size=6, mondata=None):
    """
    Set all boss trainers (gym leaders, Elite Four, Silver except first battle)
    to have full teams of 6 Pokémon.
    
    Args:
        rom: The ROM object
        trainer_names: Dictionary mapping trainer IDs to names
        gym_trainer_ids: Optional dictionary mapping gym locations to trainer IDs
        target_size: The desired team size for bosses (default 6)
        mondata: Optional Pokémon data for random species selection
    
    Returns:
        int: Number of trainers modified
    """
    modified_count = 0
    
    # Create name-to-id mapping
    name_to_id = {}
    for trainer_id, name in trainer_names.items():
        name_to_id[name] = trainer_id
    
    # Process gym leaders and Elite Four
    boss_names = GYM_LEADERS + ELITE_FOUR
    for boss_name in boss_names:
        if boss_name in name_to_id:
            trainer_id = name_to_id[boss_name]
            print(f"Setting {boss_name} (ID: {trainer_id}) to have {target_size} Pokémon")
            
            if set_trainer_team_size(rom, trainer_id, target_size, mondata):
                modified_count += 1
            
    # Process rival battles
    for trainer_id, should_have_full in RIVAL_BATTLE_IDS:
        if should_have_full:
            rival_name = trainer_names.get(trainer_id, f"Silver {trainer_id}")
            print(f"Setting {rival_name} (ID: {trainer_id}) to have {target_size} Pokémon")
            
            if set_trainer_team_size(rom, trainer_id, target_size, mondata):
                modified_count += 1
    
    return modified_count

def main():
    """Main function for running from command line"""
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nUsage:")
        print("  python team_size_adjuster.py boss <rom_file> [team_size]")
        print("  python team_size_adjuster.py trainer <rom_file> <trainer_id> <team_size>")
        sys.exit(1)
    
    command = sys.argv[1]
    rom_path = sys.argv[2]
    
    # Open ROM
    print(f"Opening ROM file: {rom_path}...")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Import functions from randomizer if needed
    try:
        from randomize_trainers import read_trainer_names, read_mondata, read_pokemon_names
        have_randomizer = True
    except ImportError:
        have_randomizer = False
    
    if command == "boss":
        # Set boss teams to full size
        team_size = 6  # Default
        if len(sys.argv) > 3:
            team_size = int(sys.argv[3])
        
        if have_randomizer:
            # Get trainer names and mondata
            trainer_names = read_trainer_names(".")
            pokemon_names = read_pokemon_names(".")
            mondata = read_mondata(rom, pokemon_names)
            
            # Set boss teams
            modified = max_team_size_bosses(rom, trainer_names, target_size=team_size, mondata=mondata)
        else:
            # Don't have randomizer functions, so run without mondata
            # Create a simple trainer name list from a/0/5/5
            narc_file_id = rom.filenames.idOf(TRAINER_DATA_NARC_PATH)
            trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
            
            # Create simple trainer names dictionary
            trainer_names = {i: f"Trainer_{i}" for i in range(len(trainer_data_narc.files))}
            
            # Set boss teams
            modified = max_team_size_bosses(rom, trainer_names, target_size=team_size)
        
        print(f"Modified {modified} boss trainers to have {team_size} Pokémon")
        
    elif command == "trainer":
        if len(sys.argv) < 5:
            print("Error: Missing arguments")
            print(__doc__)
            sys.exit(1)
        
        trainer_id = int(sys.argv[3])
        team_size = int(sys.argv[4])
        
        # Set team size for specific trainer
        if set_trainer_team_size(rom, trainer_id, team_size):
            print(f"Successfully set trainer {trainer_id}'s team size to {team_size}")
        else:
            print(f"Failed to set trainer {trainer_id}'s team size")
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)
    
    # Save ROM
    output_path = rom_path.replace(".nds", "_team_adjusted.nds")
    print(f"Saving modified ROM to {output_path}...")
    rom.saveToFile(output_path)
    print(f"Modified ROM saved successfully!")

if __name__ == "__main__":
    main()
