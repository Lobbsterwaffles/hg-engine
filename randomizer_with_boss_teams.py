#!/usr/bin/env python3
"""
Pokémon HGSS Trainer Randomizer with Boss Team Size Adjuster
-----------------------------------------------------------
This script randomizes all trainer Pokémon based on BST (Base Stat Total) and
ensures that boss trainers (gym leaders, Elite Four, rivals) have full teams of 6 Pokémon.

Features:
- Randomize all trainer Pokémon while maintaining similar power levels
- Set all boss trainers to have full teams of 6 Pokémon
- Generate new Pokémon for bosses based on their existing Pokémon's BST
- Fix any team size inconsistencies

Usage:
  python randomizer_with_boss_teams.py [rom_file] [options]
"""

import ndspy.rom
import ndspy.narc
import random
import os
import sys
import argparse
from construct import *
from statistics import median

# Import shared Pokémon data and utilities
try:
    from pokemon_shared import (
        SPECIAL_POKEMON,
        mondata_struct,
        parse_mondata,
        build_mondata,
        read_mondata,
        read_pokemon_names,
        find_replacements
    )
except ImportError:
    print("Error importing pokemon_shared.py - make sure it's in the same directory")
    sys.exit(1)

# Try to import move reader if available
try:
    from Move_reader import read_moves
except ImportError:
    print("Warning: Move_reader.py not found - move data will not be available")
    read_moves = None

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

# NARC file paths
TRAINER_POKEMON_NARC_PATH = "a/0/5/6"  # Pokémon data
TRAINER_DATA_NARC_PATH = "a/0/5/5"     # Trainer data including poke_count

# Debug switch - set to True to enable detailed hex debugging
DEBUG_TRAINER_PARSING = False

# Move ID constants
SPLASH_MOVE_ID = 150  # Move ID for Splash
BASE_TRAINER_NARC_PATH = "a/0/5/6"

# Known boss trainers with their IDs and preferred types
BOSS_TRAINERS = {
    # Format: trainer_id: (name, preferred_type)
    20: ("Falkner", "Flying"),
    21: ("Bugsy", "Bug"),
    30: ("Whitney", "Normal"),
    33: ("Morty", "Ghost"),
    38: ("Chuck", "Fighting"),
    39: ("Jasmine", "Steel"),
    47: ("Pryce", "Ice"),
    56: ("Clair", "Dragon"),
    # Kanto Gym Leaders
    60: ("Brock", "Rock"),
    62: ("Misty", "Water"),
    67: ("Lt. Surge", "Electric"),
    72: ("Erika", "Grass"),
    77: ("Janine", "Poison"),
    82: ("Sabrina", "Psychic"),
    88: ("Blaine", "Fire"),
    93: ("Blue", "Normal"),
    # Elite Four
    94: ("Will", "Psychic"),
    95: ("Koga", "Poison"),
    96: ("Bruno", "Fighting"),
    97: ("Karen", "Dark"),
    98: ("Lance", "Dragon"),
}

# Rival (Silver) battles - the first entry is the starter-only battle
RIVAL_BATTLES = [
    (112, False),  # First battle - don't give full team
    (113, True),   # Later battles should have full teams
    (114, True),
    (115, True),
    (116, True),
    (117, True),
    (118, True),
    (119, True),
]

# Common Pokémon species by type - used when adding Pokémon to teams
COMMON_POKEMON = {
    # Normal types
    "Normal": [16, 17, 19, 20, 161, 162, 163, 164, 165, 166, 167, 168, 174, 175, 203, 206, 216, 217],
    # Water types  
    "Water": [54, 55, 60, 61, 118, 119, 129, 130, 183, 184, 194, 195],
    # Fire types
    "Fire": [4, 5, 37, 38, 58, 59, 155, 156],
    # Electric types
    "Electric": [25, 26, 81, 82, 100, 101, 125, 172, 179, 180, 181],
    # Grass types
    "Grass": [43, 44, 45, 69, 70, 71, 102, 103, 114, 152, 153],
    # Ice types
    "Ice": [86, 87, 124, 220, 221, 225],
    # Fighting types
    "Fighting": [56, 57, 66, 67, 68, 106, 107, 214, 236, 237],
    # Poison types
    "Poison": [23, 24, 29, 30, 32, 33, 41, 42, 88, 89],
    # Ground types
    "Ground": [27, 28, 50, 51, 74, 75, 76, 104, 105, 111, 112, 194, 195],
    # Flying types
    "Flying": [16, 17, 18, 21, 22, 41, 42, 83, 84, 142, 163, 164, 169, 198],
    # Psychic types
    "Psychic": [63, 64, 65, 79, 80, 96, 97, 102, 103, 121, 124, 177, 178, 196, 199, 201, 202, 203],
    # Bug types
    "Bug": [10, 11, 12, 13, 14, 15, 46, 47, 48, 123, 127, 165, 166, 167, 168, 193, 204, 205, 212, 213, 214],
    # Rock types
    "Rock": [74, 75, 76, 95, 111, 112, 138, 139, 140, 141, 142, 185, 213, 219, 220, 221],
    # Ghost types
    "Ghost": [92, 93, 94, 200, 292],
    # Dragon types
    "Dragon": [147, 148, 230],
    # Dark types
    "Dark": [198, 215, 228, 229, 261, 262],
    # Steel types
    "Steel": [81, 82, 208, 227],
}

def read_trainer_pokemon(rom, trainer_id):
    """
    Read a trainer's Pokémon data from the ROM
    
    Args:
        rom: ROM object
        trainer_id: Trainer ID to read
        
    Returns:
        tuple: (pokemon_list, has_moves) where pokemon_list is a list of Pokémon objects
        and has_moves is a boolean indicating whether the Pokémon have move data
    """
    # Get the trainer Pokémon NARC
    narc_file_id = rom.filenames.idOf(TRAINER_POKEMON_NARC_PATH)
    trainer_narc_data = ndspy.narc.NARC(rom.files[narc_file_id])
    
    # Check if trainer exists
    if trainer_id >= len(trainer_narc_data.files):
        return [], False
    
    # Get trainer's Pokémon data
    pokemon_data = trainer_narc_data.files[trainer_id]
    
    # Check if trainer has Pokémon with moves
    # A trainer with moves will have 20 bytes per Pokémon
    has_moves = (len(pokemon_data) % 20 == 0) and len(pokemon_data) > 0
    pokemon_size = 20 if has_moves else 8
    
    # Calculate number of Pokémon
    num_pokemon = len(pokemon_data) // pokemon_size
    
    # Parse each Pokémon
    pokemon_list = []
    for i in range(num_pokemon):
        start_offset = i * pokemon_size
        pokemon_bytes = pokemon_data[start_offset:start_offset + pokemon_size]
        
        if has_moves:
            # Parse with moves struct
            pokemon = trainer_pokemon_moves_struct.parse(pokemon_bytes)
        else:
            # Parse with basic struct
            pokemon = trainer_pokemon_struct.parse(pokemon_bytes)
        
        pokemon_list.append(pokemon)
    
    return pokemon_list, has_moves

def get_trainer_poke_count(rom, trainer_id):
    """
    Get the poke_count value from trainer metadata
    
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
            return 0
        
        # Get trainer's data
        trainer_data = trainer_data_narc.files[trainer_id]
        
        # poke_count is at offset 3
        poke_count = trainer_data[3]
        return poke_count
    except Exception as e:
        print(f"Error reading trainer {trainer_id}: {e}")
        return 0

def update_trainer_poke_count(rom, trainer_id, new_count):
    """
    Update a trainer's poke_count value in the ROM
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        new_count: The new number of Pokémon
    """
    # Get the trainer data NARC
    narc_file_id = rom.filenames.idOf(TRAINER_DATA_NARC_PATH)
    trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
    
    # Check if trainer exists
    if trainer_id >= len(trainer_data_narc.files):
        print(f"Warning: Trainer ID {trainer_id} does not exist in the ROM")
        return
    
    # Get trainer's data
    trainer_data = bytearray(trainer_data_narc.files[trainer_id])
    
    # Update poke_count value (at offset 3)
    trainer_data[3] = new_count
    
    # Save back to NARC
    trainer_data_narc.files[trainer_id] = bytes(trainer_data)
    rom.files[narc_file_id] = trainer_data_narc.save()
    
    if DEBUG_TRAINER_PARSING:
        print(f"Updated trainer {trainer_id}'s poke_count to {new_count}")

def save_trainer_pokemon(rom, trainer_id, pokemon_list, has_moves):
    """
    Save a trainer's Pokémon list back to the ROM
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        pokemon_list: List of Pokémon objects
        has_moves: Whether Pokémon have moves
    """
    # Get the trainer Pokémon NARC
    narc_file_id = rom.filenames.idOf(TRAINER_POKEMON_NARC_PATH)
    trainer_narc_data = ndspy.narc.NARC(rom.files[narc_file_id])
    
    # Build the new Pokémon data
    new_data = bytearray()
    for pokemon in pokemon_list:
        if has_moves:
            pokemon_bytes = trainer_pokemon_moves_struct.build(pokemon)
        else:
            pokemon_bytes = trainer_pokemon_struct.build(pokemon)
        new_data.extend(pokemon_bytes)
    
    # Save back to NARC
    trainer_narc_data.files[trainer_id] = bytes(new_data)
    rom.files[narc_file_id] = trainer_narc_data.save()
    
    # Update the trainer's poke_count value
    update_trainer_poke_count(rom, trainer_id, len(pokemon_list))
    
    if DEBUG_TRAINER_PARSING:
        print(f"Updated trainer {trainer_id}'s Pokémon data ({len(pokemon_list)} Pokémon)")

def read_all_trainer_data(rom):
    """
    Read all trainer data from the ROM
    
    Args:
        rom: ROM object
        
    Returns:
        list: List of (trainer_id, pokemon_list, has_moves) tuples
    """
    # Get the trainer Pokémon NARC
    narc_file_id = rom.filenames.idOf(TRAINER_POKEMON_NARC_PATH)
    trainer_narc_data = ndspy.narc.NARC(rom.files[narc_file_id])
    
    trainers = []
    for trainer_id in range(len(trainer_narc_data.files)):
        pokemon_list, has_moves = read_trainer_pokemon(rom, trainer_id)
        if pokemon_list:  # Only include trainers with Pokémon
            trainers.append((trainer_id, pokemon_list, has_moves))
    
    return trainers


def get_pokemon_bst(pokemon_id, pokemon_stats):
    """
    Calculate the Base Stat Total (BST) for a Pokémon
    
    BST is the sum of all a Pokémon's base stats (HP, Attack, Defense, etc.)
    It gives us a rough idea of how strong the Pokémon is overall.
    
    Args:
        pokemon_id: Pokémon species ID
        pokemon_stats: Dictionary of Pokémon stats data
        
    Returns:
        int: BST value or 0 if not found
    """
    if pokemon_id not in pokemon_stats:
        return 0
    
    stats = pokemon_stats[pokemon_id]
    # Sum up all the base stats for this Pokémon
    bst = stats.get('hp', 0) + stats.get('attack', 0) + stats.get('defense', 0) + \
          stats.get('spattack', 0) + stats.get('spdefense', 0) + stats.get('speed', 0)
    return bst


def get_bst_range(base_bst, variance_percent=15):
    """
    Calculate an acceptable BST range for replacement Pokémon
    
    This creates a range of values that are similar in power to the original Pokémon.
    For example, if a Pokémon has BST 400, we might look for replacements with BST 340-460.
    
    Args:
        base_bst: Base Stat Total to center the range around
        variance_percent: How much stronger/weaker the replacement can be (percentage)
        
    Returns:
        tuple: (min_bst, max_bst) acceptable range
    """
    min_bst = int(base_bst * (100 - variance_percent) / 100)
    max_bst = int(base_bst * (100 + variance_percent) / 100)
    return min_bst, max_bst


def find_bst_match(species_id, pokemon_stats, pokemon_names, exclude_ids=None):
    """
    Find a Pokémon with similar BST to replace the given species
    
    Args:
        species_id: Original species ID to match
        pokemon_stats: Dictionary of Pokémon stats
        pokemon_names: Dictionary of Pokémon names
        exclude_ids: List of species IDs to exclude from selection
        
    Returns:
        int: New species ID with similar BST
    """
    if exclude_ids is None:
        exclude_ids = []
    
    # Get original BST
    original_bst = get_pokemon_bst(species_id, pokemon_stats)
    if original_bst == 0:
        # If we can't get the original BST, pick a random Pokémon
        valid_species = [s for s in pokemon_stats.keys() if s not in exclude_ids and s not in SPECIAL_POKEMON]
        if not valid_species:
            return species_id  # Return original if no valid replacements
        return random.choice(valid_species)
    
    # Calculate acceptable BST range
    min_bst, max_bst = get_bst_range(original_bst)
    
    # Find all species within the BST range
    valid_species = []
    for species, stats in pokemon_stats.items():
        if species in exclude_ids or species in SPECIAL_POKEMON:
            continue
        
        species_bst = get_pokemon_bst(species, pokemon_stats)
        if min_bst <= species_bst <= max_bst:
            valid_species.append(species)
    
    # If no matches found, widen the search
    if not valid_species:
        min_bst, max_bst = get_bst_range(original_bst, 30)  # 30% variance
        for species, stats in pokemon_stats.items():
            if species in exclude_ids or species in SPECIAL_POKEMON:
                continue
            
            species_bst = get_pokemon_bst(species, pokemon_stats)
            if min_bst <= species_bst <= max_bst:
                valid_species.append(species)
    
    # If still no matches, use any valid species
    if not valid_species:
        valid_species = [s for s in pokemon_stats.keys() if s not in exclude_ids and s not in SPECIAL_POKEMON]
    
    if not valid_species:
        return species_id  # Return original if no valid replacements
    
    # Choose a random species from the valid options
    return random.choice(valid_species)


def create_new_pokemon(has_moves, trainer_type, preferred_species=None, median_level=50, median_bst=400):
    """
    Create a new Pokémon for a boss trainer
    
    Args:
        has_moves: Whether the trainer has Pokémon with moves
        trainer_type: Preferred type of the trainer
        preferred_species: List of preferred species IDs
        median_level: Median level of existing Pokémon
        median_bst: Median BST of existing Pokémon
        
    Returns:
        dict: New Pokémon data
    """
    # Choose a species
    species_id = None
    if preferred_species and random.random() < 0.7:  # 70% chance to use preferred species
        species_id = random.choice(preferred_species)
    
    if species_id is None and trainer_type in COMMON_POKEMON and random.random() < 0.8:  # 80% chance for type-based
        type_pokemon = COMMON_POKEMON[trainer_type]
        if type_pokemon:
            species_id = random.choice(type_pokemon)
    
    if species_id is None:  # Random pick if still None
        # Use a common Pokémon from any type
        all_common = []
        for type_list in COMMON_POKEMON.values():
            all_common.extend(type_list)
        species_id = random.choice(all_common)
    
    # Create Pokémon data
    if has_moves:
        return {
            'ivs': random.randint(0, 31),        # Random IVs
            'abilityslot': random.randint(0, 1),  # Random ability slot
            'level': median_level,                # Use median level
            'species': species_id,                # Selected species
            'item': 0,                            # No held item
            'move1': SPLASH_MOVE_ID,              # Default move
            'move2': 0,                           # No move
            'move3': 0,                           # No move
            'move4': 0,                           # No move
            'ballseal': 0                         # No ball seal
        }
    else:
        return {
            'ivs': random.randint(0, 31),        # Random IVs
            'abilityslot': random.randint(0, 1),  # Random ability slot
            'level': median_level,                # Use median level
            'species': species_id,                # Selected species
            'ballseal': 0                         # No ball seal
        }


def calculate_team_stats(pokemon_list, pokemon_stats):
    """
    Calculate statistics for a trainer's team
    
    Args:
        pokemon_list: List of Pokémon objects
        pokemon_stats: Dictionary of Pokémon stats
        
    Returns:
        dict: Team statistics including median level and BST
    """
    if not pokemon_list:
        return {'median_level': 50, 'median_bst': 400}
    
    levels = [p.level for p in pokemon_list]
    bst_values = [get_pokemon_bst(p.species, pokemon_stats) for p in pokemon_list]
    
    # Filter out any zero BST values
    bst_values = [bst for bst in bst_values if bst > 0]
    if not bst_values:
        bst_values = [400]  # Default if no valid BST
    
    return {
        'median_level': int(median(levels)),
        'median_bst': int(median(bst_values))
    }


def add_pokemon_to_team(pokemon_list, has_moves, trainer_type, pokemon_stats, target_size=6):
    """
    Add Pokémon to a team to reach the target size
    
    Args:
        pokemon_list: Original list of Pokémon
        has_moves: Whether the trainer has Pokémon with moves
        trainer_type: Trainer's preferred type
        pokemon_stats: Dictionary of Pokémon stats
        target_size: Target team size
        
    Returns:
        list: Updated Pokémon list
    """
    if len(pokemon_list) >= target_size:
        return pokemon_list  # Already at or above target size
    
    # Get median level and BST of existing Pokémon
    team_stats = calculate_team_stats(pokemon_list, pokemon_stats)
    median_level = team_stats['median_level']
    median_bst = team_stats['median_bst']
    
    # Get a list of existing species to avoid duplicates
    existing_species = [p.species for p in pokemon_list]
    
    # Add new Pokémon until we reach the target size
    while len(pokemon_list) < target_size:
        new_pokemon = create_new_pokemon(
            has_moves=has_moves,
            trainer_type=trainer_type,
            preferred_species=None,
            median_level=median_level,
            median_bst=median_bst
        )
        
        # Avoid duplicates when possible
        if len(pokemon_list) < 3 or new_pokemon['species'] not in existing_species:
            pokemon_list.append(new_pokemon)
            existing_species.append(new_pokemon['species'])
    
    return pokemon_list


def randomize_trainer(trainer_id, pokemon_list, has_moves, pokemon_stats, pokemon_names, preserve_types=False):
    """
    Randomize a trainer's Pokémon team
    
    Args:
        trainer_id: Trainer ID
        pokemon_list: List of Pokémon
        has_moves: Whether the trainer has Pokémon with moves
        pokemon_stats: Dictionary of Pokémon stats
        pokemon_names: Dictionary of Pokémon names
        preserve_types: Whether to preserve original Pokémon types
        
    Returns:
        list: Updated Pokémon list
    """
    new_pokemon_list = []
    used_species = []
    
    for i, pokemon in enumerate(pokemon_list):
        # Find a replacement with similar BST
        new_species = find_bst_match(pokemon.species, pokemon_stats, pokemon_names, used_species)
        used_species.append(new_species)
        
        # Create a copy of the original Pokémon data with the new species
        new_pokemon = dict(pokemon)
        new_pokemon['species'] = new_species
        new_pokemon_list.append(new_pokemon)
    
    return new_pokemon_list


def max_team_size_bosses(rom, pokemon_stats, target_size=6):
    """
    Ensure all boss trainers have the target team size
    
    Args:
        rom: ROM object
        pokemon_stats: Dictionary of Pokémon stats
        target_size: Target team size for bosses
        
    Returns:
        int: Number of trainers modified
    """
    count_modified = 0
    
    # Process gym leaders and Elite Four
    for trainer_id, (name, type_pref) in BOSS_TRAINERS.items():
        # Read current team
        pokemon_list, has_moves = read_trainer_pokemon(rom, trainer_id)
        
        if not pokemon_list:
            print(f"Warning: No Pok\u00e9mon data found for {name} (ID: {trainer_id})")
            continue
        
        # Check if already at target size
        current_size = len(pokemon_list)
        if current_size >= target_size:
            print(f"{name} already has {current_size} Pok\u00e9mon")
            continue
        
        print(f"Setting {name} to have {target_size} Pok\u00e9mon...")
        
        # Add Pokémon to reach target size
        new_pokemon_list = add_pokemon_to_team(
            pokemon_list, has_moves, type_pref, pokemon_stats, target_size
        )
        
        # Save changes back to ROM
        save_trainer_pokemon(rom, trainer_id, new_pokemon_list, has_moves)
        count_modified += 1
    
    # Process rival battles
    for trainer_id, should_max in RIVAL_BATTLES:
        if not should_max:
            continue  # Skip battles that shouldn't have max teams
        
        # Read current team
        pokemon_list, has_moves = read_trainer_pokemon(rom, trainer_id)
        
        if not pokemon_list:
            print(f"Warning: No Pok\u00e9mon data found for Rival (ID: {trainer_id})")
            continue
        
        # Check if already at target size
        current_size = len(pokemon_list)
        if current_size >= target_size:
            print(f"Rival (ID: {trainer_id}) already has {current_size} Pok\u00e9mon")
            continue
        
        print(f"Setting Rival (ID: {trainer_id}) to have {target_size} Pok\u00e9mon...")
        
        # Add Pokémon to reach target size - use Normal type for rivals
        new_pokemon_list = add_pokemon_to_team(
            pokemon_list, has_moves, "Normal", pokemon_stats, target_size
        )
        
        # Save changes back to ROM
        save_trainer_pokemon(rom, trainer_id, new_pokemon_list, has_moves)
        count_modified += 1
    
    # Fix any inconsistencies
    fix_team_size_inconsistencies(rom)
    
    return count_modified


def fix_team_size_inconsistencies(rom):
    """
    Fix inconsistencies between poke_count and actual Pokémon count
    
    Args:
        rom: ROM object
        
    Returns:
        int: Number of trainers fixed
    """
    fixed_count = 0
    
    # Process gym leaders, Elite Four, and rivals
    trainer_ids = list(BOSS_TRAINERS.keys())
    trainer_ids.extend([trainer_id for trainer_id, _ in RIVAL_BATTLES])
    
    for trainer_id in trainer_ids:
        # Get actual Pokémon count
        pokemon_list, _ = read_trainer_pokemon(rom, trainer_id)
        actual_count = len(pokemon_list)
        
        # Get metadata poke_count
        poke_count = get_trainer_poke_count(rom, trainer_id)
        
        # Check for inconsistency
        if poke_count != actual_count and actual_count > 0:
            print(f"Found inconsistency for trainer {trainer_id}: poke_count={poke_count}, actual={actual_count}")
            
            # Update poke_count to match actual count
            update_trainer_poke_count(rom, trainer_id, actual_count)
            
            # Get trainer name for reporting
            if trainer_id in BOSS_TRAINERS:
                name = BOSS_TRAINERS[trainer_id][0]
                print(f"Fixed {name} - updated poke_count to {actual_count}")
            else:
                print(f"Fixed Rival (ID: {trainer_id}) - updated poke_count to {actual_count}")
                
            fixed_count += 1
    
    if fixed_count > 0:
        print(f"Fixed {fixed_count} trainer data inconsistencies")
    
    return fixed_count


def randomize_trainers(rom, options):
    """
    Main function to randomize all trainer Pokémon
    
    Args:
        rom: ROM object
        options: Dictionary of options
    """
    # Read Pokémon data
    print("Reading Pok\u00e9mon data...")
    pokemon_names = read_pokemon_names(rom)
    pokemon_stats = read_mondata(rom, pokemon_names)
    
    # Read all trainers
    print("Reading trainer data...")
    all_trainers = read_all_trainer_data(rom)
    print(f"Found {len(all_trainers)} trainers with Pok\u00e9mon")
    
    # Randomize trainer Pokémon
    if options.get('randomize_trainers', True):
        print("Randomizing trainer Pok\u00e9mon...")
        for trainer_id, pokemon_list, has_moves in all_trainers:
            # Skip empty trainers
            if not pokemon_list:
                continue
                
            # Randomize the trainer's team
            new_pokemon_list = randomize_trainer(
                trainer_id, pokemon_list, has_moves, pokemon_stats, pokemon_names
            )
            
            # Save changes back to ROM
            save_trainer_pokemon(rom, trainer_id, new_pokemon_list, has_moves)
    
    # Max out boss trainer teams
    if options.get('max_boss_teams', True):
        target_size = options.get('boss_team_size', 6)
        print(f"Setting boss trainers to have {target_size} Pok\u00e9mon...")
        modified = max_team_size_bosses(rom, pokemon_stats, target_size)
        print(f"Modified {modified} boss trainers")


def main():
    """
    Main entry point for the randomizer
    """
    parser = argparse.ArgumentParser(description="Pok\u00e9mon HGSS Trainer Randomizer with Boss Team Adjuster")
    parser.add_argument("rom", help="Path to the ROM file")
    parser.add_argument("--output", "-o", help="Output ROM path (default: original_bosses6.nds)")
    parser.add_argument("--no-randomize", action="store_true", help="Don't randomize trainer Pok\u00e9mon")
    parser.add_argument("--team-size", type=int, default=6, help="Target team size for boss trainers (1-6)")
    parser.add_argument("--no-boss-adjust", action="store_true", help="Don't adjust boss team sizes")
    
    args = parser.parse_args()
    
    # Validate args
    if not os.path.isfile(args.rom):
        print(f"Error: ROM file '{args.rom}' not found")
        return 1
        
    if args.team_size < 1 or args.team_size > 6:
        print("Error: Team size must be between 1 and 6")
        return 1
    
    # Determine output path
    if not args.output:
        base_name = os.path.splitext(args.rom)[0]
        args.output = f"{base_name}_bosses{args.team_size}.nds"
    
    # Open the ROM
    print(f"Opening ROM file: {args.rom}")
    try:
        rom = ndspy.rom.NintendoDSRom.fromFile(args.rom)
    except Exception as e:
        print(f"Error opening ROM: {e}")
        return 1
    
    # Set options
    options = {
        'randomize_trainers': not args.no_randomize,
        'max_boss_teams': not args.no_boss_adjust,
        'boss_team_size': args.team_size
    }
    
    # Run randomization
    randomize_trainers(rom, options)
    
    # Save the modified ROM
    print(f"Saving modified ROM to {args.output}...")
    rom.saveToFile(args.output)
    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
