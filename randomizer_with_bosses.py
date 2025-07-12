#!/usr/bin/env python3
"""
Enhanced Trainer Randomizer with Boss Team Control
-------------------------------------------------
This script randomizes trainer Pokémon in HeartGold/SoulSilver ROMs
and can set all boss trainers (gym leaders, Elite Four) to have full teams.

New feature:
- --max-boss-teams: Makes all gym leaders, Elite Four, and important rivals have full teams
- --boss-team-size: Controls how many Pokémon bosses will have (default: 6)
"""

# Import necessary libraries
import ndspy.rom
import ndspy.narc
import os
import sys
import random
import argparse
import json
from construct import *

# Known boss trainers with their IDs
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

# Pokémon entry structures
trainer_pokemon_struct = Struct(
    "ivs" / Int8ul,             # 1 byte - IVs
    "abilityslot" / Int8ul,     # 1 byte - Ability slot
    "level" / Int16ul,          # 2 bytes - Level (halfword)
    "species" / Int16ul,        # 2 bytes - Species ID (halfword)
    "ballseal" / Int16ul,       # 2 bytes - Ball seal (halfword)
)

# Pokémon with moves structure (18 bytes total)
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

# Common Pokémon species to use when adding to teams
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

def get_trainer_pokemon(rom, trainer_id):
    """
    Get a trainer's Pokémon list from the ROM.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        
    Returns:
        tuple: (pokemon_list, has_moves) - The list of Pokémon and whether they have moves
    """
    # Get the trainer Pokémon NARC
    narc_file_id = rom.filenames.idOf("a/0/5/6")
    trainer_narc_data = ndspy.narc.NARC(rom.files[narc_file_id])
    
    # Check if trainer exists
    if trainer_id >= len(trainer_narc_data.files):
        raise ValueError(f"Trainer ID {trainer_id} does not exist in the ROM")
    
    # Get trainer's Pokémon data
    pokemon_data = trainer_narc_data.files[trainer_id]
    
    # Check if trainer has Pokémon with moves
    # A trainer with moves will have 18 bytes per Pokémon
    has_moves = (len(pokemon_data) % 18 == 0) and len(pokemon_data) > 0
    pokemon_size = 18 if has_moves else 8
    
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

def update_trainer_poke_count(rom, trainer_id, new_count):
    """
    Update a trainer's poke_count value in the ROM.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        new_count: The new number of Pokémon
    """
    # Get the trainer data NARC
    narc_file_id = rom.filenames.idOf("a/0/5/5")
    trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
    
    # Check if trainer exists
    if trainer_id >= len(trainer_data_narc.files):
        raise ValueError(f"Trainer ID {trainer_id} does not exist in the ROM")
    
    # Get trainer's data
    trainer_data = bytearray(trainer_data_narc.files[trainer_id])
    
    # Update poke_count value
    # Based on what we learned, poke_count is at offset 3
    trainer_data[3] = new_count
    
    # Save back to NARC
    trainer_data_narc.files[trainer_id] = bytes(trainer_data)
    rom.files[narc_file_id] = trainer_data_narc.save()
    
    print(f"Updated trainer {trainer_id}'s poke_count to {new_count}")

def save_trainer_pokemon(rom, trainer_id, pokemon_list, has_moves):
    """
    Save a trainer's Pokémon list back to the ROM.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        pokemon_list: List of Pokémon objects
        has_moves: Whether Pokémon have moves
    """
    # Get the trainer Pokémon NARC
    narc_file_id = rom.filenames.idOf("a/0/5/6")
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
    
    print(f"Updated trainer {trainer_id}'s Pokémon data ({len(pokemon_list)} Pokémon)")

def add_pokemon_to_trainer(rom, trainer_id, species_id, level, moves=None):
    """
    Add a Pokémon to a trainer's team.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        species_id: The Pokémon species ID
        level: The Pokémon's level
        moves: Optional list of move IDs, if the trainer has Pokémon with moves
        
    Returns:
        bool: True if successful
    """
    try:
        # Get the trainer's current Pokémon
        pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
        
        # Create the new Pokémon
        new_pokemon = Container()
        new_pokemon.ivs = 50  # Default IVs
        new_pokemon.abilityslot = 0
        new_pokemon.level = level
        new_pokemon.species = species_id
        new_pokemon.ballseal = 0
        
        if has_moves:
            new_pokemon.item = 0  # No held item
            if moves and len(moves) == 4:
                new_pokemon.move1 = moves[0]
                new_pokemon.move2 = moves[1]
                new_pokemon.move3 = moves[2]
                new_pokemon.move4 = moves[3]
            else:
                # Default moves
                new_pokemon.move1 = 33  # Tackle
                new_pokemon.move2 = 45  # Growl
                new_pokemon.move3 = 0   # No move
                new_pokemon.move4 = 0   # No move
        
        # Add the new Pokémon to the list
        pokemon_list.append(new_pokemon)
        
        # Save the updated Pokémon list
        save_trainer_pokemon(rom, trainer_id, pokemon_list, has_moves)
        
        # Update the trainer's poke_count value
        update_trainer_poke_count(rom, trainer_id, len(pokemon_list))
        
        return True
    except Exception as e:
        print(f"Error adding Pokémon to trainer {trainer_id}: {e}")
        return False

def set_trainer_team_size(rom, trainer_id, target_size):
    """
    Set a trainer's team size to the specified target.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        target_size: The desired team size
        
    Returns:
        bool: True if successful
    """
    try:
        # Get the trainer's current Pokémon
        pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
        current_size = len(pokemon_list)
        
        # If already at target size, nothing to do
        if current_size == target_size:
            print(f"Trainer {trainer_id} already has {target_size} Pokémon")
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
            # Determine preferred type for this trainer
            preferred_type = None
            if trainer_id in BOSS_TRAINERS:
                preferred_type = BOSS_TRAINERS[trainer_id][1]
            
            # Determine level for new Pokémon
            levels = [p.level for p in pokemon_list]
            avg_level = sum(levels) / len(levels) if levels else 30
            
            # Add new Pokémon
            for _ in range(target_size - current_size):
                # Choose a species
                if preferred_type and preferred_type in COMMON_POKEMON:
                    # Use the trainer's preferred type
                    species_id = random.choice(COMMON_POKEMON[preferred_type])
                else:
                    # No preference, pick a random type
                    random_type = random.choice(list(COMMON_POKEMON.keys()))
                    species_id = random.choice(COMMON_POKEMON[random_type])
                
                # Calculate level - slightly randomized around the average
                new_level = int(avg_level + random.randint(-2, 2))
                if new_level < 1:
                    new_level = 1
                
                # Create moves if trainer has Pokémon with moves
                moves = None
                if has_moves:
                    # Some basic move IDs (Tackle, Growl, Quick Attack, etc.)
                    move_options = [33, 45, 98, 28, 39, 31, 43]
                    moves = [
                        random.choice(move_options),
                        random.choice(move_options),
                        random.choice(move_options),
                        0   # Empty move
                    ]
                    # Randomize a bit to avoid all having the same moves
                    random.shuffle(moves)
                
                # Add the Pokémon
                add_pokemon_to_trainer(rom, trainer_id, species_id, new_level, moves)
            
            return True
            
    except Exception as e:
        print(f"Error setting team size for trainer {trainer_id}: {e}")
        return False

def max_team_size_bosses(rom, target_size=6):
    """
    Set all boss trainers to have full teams of the specified size.
    
    Args:
        rom: The ROM object
        target_size: The desired team size for bosses (default 6)
    
    Returns:
        int: Number of trainers modified
    """
    modified_count = 0
    
    # Process known boss trainers
    for trainer_id, (name, preferred_type) in BOSS_TRAINERS.items():
        print(f"Setting {name} (ID: {trainer_id}) to have {target_size} Pokémon")
        
        if set_trainer_team_size(rom, trainer_id, target_size):
            modified_count += 1
            
    # Process rival battles
    for trainer_id, should_have_full in RIVAL_BATTLES:
        if should_have_full:
            print(f"Setting Rival (ID: {trainer_id}) to have {target_size} Pokémon")
            
            if set_trainer_team_size(rom, trainer_id, target_size):
                modified_count += 1
    
    return modified_count

def randomize_trainers(rom):
    """
    Basic function to randomize trainer Pokémon. This is a simplified version.
    In a real application, this would be more complex.
    """
    print("Randomizing trainer Pokémon (simplified version for testing)...")
    # Normally this would perform actual randomization
    # For this example, we just show how to connect with boss team size feature
    return True

def main():
    """Main function for running the randomizer"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom_file", help="Path to the ROM file")
    parser.add_argument("--randomize", action="store_true", help="Randomize trainer Pokémon")
    parser.add_argument("--max-boss-teams", action="store_true", help="Set boss trainers to have full teams")
    parser.add_argument("--boss-team-size", type=int, default=6, help="Team size for bosses (default: 6)")
    args = parser.parse_args()

    # Check if ROM file exists
    if not os.path.exists(args.rom_file):
        print(f"Error: ROM file {args.rom_file} not found")
        return 1

    # Open ROM file
    print(f"Opening ROM file: {args.rom_file}")
    rom = ndspy.rom.NintendoDSRom.fromFile(args.rom_file)

    # Track what changes we're making for output filename
    changes = []

    # Randomize trainers if requested
    if args.randomize:
        print("Randomizing trainer Pokémon...")
        randomize_trainers(rom)
        changes.append("random")

    # Set boss team sizes if requested
    if args.max_boss_teams:
        print(f"Setting boss trainers to have {args.boss_team_size} Pokémon...")
        modified = max_team_size_bosses(rom, target_size=args.boss_team_size)
        print(f"Modified {modified} boss trainers")
        changes.append(f"bosses{args.boss_team_size}")

    # If no changes were requested, show help
    if not changes:
        parser.print_help()
        return 0

    # Build output filename
    output_name = "_".join([""] + changes)
    output_file = args.rom_file.replace(".nds", f"{output_name}.nds")

    # Save ROM file
    print(f"Saving modified ROM to {output_file}...")
    rom.saveToFile(output_file)
    print("Done!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
