#!/usr/bin/env python3
"""
Boss Team Adjuster for Pokémon HGSS
-----------------------------------
This script gives all boss trainers (gym leaders, Elite Four, rivals) full teams.
It works as a standalone script or can be imported into the randomizer.

Usage:
  python boss_team_adjuster.py [rom_file] --team-size [size] [--use-bst]
"""

import ndspy.rom
import ndspy.narc
import os
import sys
import random
import argparse
import statistics  # For calculating mean BST
from construct import Container, Struct, Int8ul, Int16ul

# Pokémon entry structures - These match the data format in the ROM
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

# NARC file paths
TRAINER_POKEMON_NARC_PATH = "a/0/5/6"  # Pokémon data
TRAINER_DATA_NARC_PATH = "a/0/5/5"     # Trainer data including poke_count
POKEMON_STATS_NARC_PATH = "a/0/1/1"    # Pokémon base stats

# Stats to read from Pokémon data
STAT_NAMES = ["hp", "attack", "defense", "speed", "spatk", "spdef"]

# Pokémon stats structure
stats_struct = Struct(
    "hp" / Int8ul,
    "attack" / Int8ul,
    "defense" / Int8ul,
    "speed" / Int8ul,
    "spatk" / Int8ul,
    "spdef" / Int8ul,
)

# Known boss trainers with their IDs and preferred types
BOSS_TRAINERS = {
    # Format: trainer_id: (name, preferred_type)
    # Johto Gym Leaders - Original Battles
    20: ("Falkner", "Flying"),
    21: ("Bugsy", "Bug"),
    30: ("Whitney", "Normal"),
    31: ("Morty", "Ghost"),
    34: ("Chuck", "Fighting"),
    33: ("Jasmine", "Steel"),
    32: ("Pryce", "Ice"),
    35: ("Clair", "Dragon"),
    # Kanto Gym Leaders - Original Battles
    253: ("Brock", "Rock"),
    254: ("Misty", "Water"),
    255: ("Lt. Surge", "Electric"),
    256: ("Erika", "Grass"),
    257: ("Janine", "Poison"),
    258: ("Sabrina", "Psychic"),
    259: ("Blaine", "Fire"),
    261: ("Blue", "Normal"),
    # Elite Four - Original Battles
    245: ("Will", "Psychic"),
    247: ("Koga", "Poison"),
    418: ("Bruno", "Fighting"),
    246: ("Karen", "Dark"),
    244: ("Lance", "Dragon"),
    # You can add rematch battles if needed (IDs 701-727)
}

# Rival (Silver) battles with their IDs
RIVAL_BATTLES = [
    112,  # First battle - just starter
    113,  # Second battle - Gastly and Zubat
    114,  # Later battles
    115,
    116,
    117,
    118,
    119,
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
    narc_file_id = rom.filenames.idOf(TRAINER_POKEMON_NARC_PATH)
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
    narc_file_id = rom.filenames.idOf(TRAINER_DATA_NARC_PATH)
    trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
    
    # Check if trainer exists
    if trainer_id >= len(trainer_data_narc.files):
        raise ValueError(f"Trainer ID {trainer_id} does not exist in the ROM")
    
    # Get trainer's data
    trainer_data = bytearray(trainer_data_narc.files[trainer_id])
    
    # Update poke_count value (at offset 3)
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

def fix_team_size_inconsistencies(rom):
    """
    Find and fix trainers whose poke_count doesn't match their actual Pokémon count.
    This is important because the game uses the poke_count value to determine how many
    Pokémon to load for a trainer.
    
    Args:
        rom: The ROM object
        
    Returns:
        int: Number of trainers fixed
    """
    fixed_count = 0
    
    # Get the trainer data NARC
    narc_file_id = rom.filenames.idOf(TRAINER_DATA_NARC_PATH)
    trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
    
    # Check all trainers (up to 800, which should cover all trainers in the game)
    for trainer_id in range(min(len(trainer_data_narc.files), 800)):
        try:
            # Skip trainers with no data
            if len(trainer_data_narc.files[trainer_id]) == 0:
                continue
                
            # Get the poke_count from trainer data
            trainer_data = trainer_data_narc.files[trainer_id]
            poke_count = trainer_data[3]
            
            # Get the actual Pokémon count from the Pokémon data
            pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
            actual_count = len(pokemon_list)
            
            # If there's a mismatch, fix it
            if poke_count != actual_count:
                # Only fix if this is a boss trainer or rival
                is_boss = trainer_id in BOSS_TRAINERS
                is_rival = any(trainer_id == rid for rid, _ in RIVAL_BATTLES)
                
                if is_boss or is_rival:
                    print(f"Found inconsistency for trainer {trainer_id}: poke_count={poke_count}, actual={actual_count}")
                    
                    # Update the poke_count value
                    update_trainer_poke_count(rom, trainer_id, actual_count)
                    
                    # Get the trainer name for the log
                    if trainer_id in BOSS_TRAINERS:
                        name = BOSS_TRAINERS[trainer_id][0]
                    else:
                        name = f"Rival (ID: {trainer_id})"
                        
                    print(f"Fixed {name} - updated poke_count to {actual_count}")
                    fixed_count += 1
        except Exception as e:
            # Skip problematic trainers
            continue
    
    return fixed_count

def set_trainer_team_size(rom, trainer_id, target_size, use_bst=False):
    """
    Set a trainer's team size to the specified target.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        target_size: The desired team size
        use_bst: Whether to use BST-based selection for new Pokémon
        
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
            
        # If we need to remove Pokémon, remove from the end
        if current_size > target_size:
            pokemon_list = pokemon_list[:target_size]
            save_trainer_pokemon(rom, trainer_id, pokemon_list, has_moves)
            update_trainer_poke_count(rom, trainer_id, target_size)
            return True
            
        # Otherwise, we need to add Pokémon
        if current_size < target_size:
            # Determine average level and valid moves
            avg_level = sum(p.level for p in pokemon_list) // max(1, len(pokemon_list))
            new_level = avg_level or 5  # Default to level 5 if avg_level is 0
            
            # Get trainer's preferred type
            preferred_type = None
            if trainer_id in BOSS_TRAINERS:
                preferred_type = BOSS_TRAINERS[trainer_id][1]
                
            # For BST-based selection, we need to read Pokémon stats
            pokemon_stats = None
            if use_bst and current_size > 0:
                pokemon_stats = read_pokemon_stats(rom)
                
                # Get mean BST of existing team
                target_bst = get_mean_bst(pokemon_list, pokemon_stats)
                print(f"Target BST for new Pokémon: {target_bst}")
                
                # Get existing species IDs to avoid duplicates
                existing_species = [p.species for p in pokemon_list]
            
            # Add Pokémon until we reach target size
            for i in range(current_size, target_size):
                # Choose a species based on BST or type
                if use_bst and pokemon_stats:
                    species_id = find_pokemon_in_bst_range(
                        target_bst, 
                        pokemon_stats, 
                        preferred_type,
                        existing_species
                    )
                    # Add to existing species to avoid duplicates in future iterations
                    existing_species.append(species_id)
                else:
                    # Use the simple type-based selection
                    if preferred_type and preferred_type in COMMON_POKEMON and COMMON_POKEMON[preferred_type]:
                        species_id = random.choice(COMMON_POKEMON[preferred_type])
                    else:
                        species_id = random.choice(COMMON_POKEMON["Normal"])
                
                # Set up moves if needed
                moves = None
                if has_moves:
                    # If we have existing Pokémon, copy some moves from them
                    move_options = []
                    for p in pokemon_list:
                        if hasattr(p, "move1") and p.move1 > 0:
                            move_options.append(p.move1)
                        if hasattr(p, "move2") and p.move2 > 0:
                            move_options.append(p.move2)
                        if hasattr(p, "move3") and p.move3 > 0:
                            move_options.append(p.move3)
                        if hasattr(p, "move4") and p.move4 > 0:
                            move_options.append(p.move4)
                    
                    # If we have moves, create a moveset
                    if move_options:
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

def max_team_size_bosses(rom, target_size=6, use_bst=False, use_scaling=False):
    """
    Set all boss trainers to have full teams of the specified size.
    With scaling option, early gym leaders will have smaller teams.
    
    Args:
        rom: The ROM object
        target_size: The desired team size for bosses (default 6)
        use_bst: Whether to use BST-based selection for new Pokémon
        use_scaling: Whether to scale team sizes (early gyms have smaller teams)
    
    Returns:
        int: Number of trainers modified
    """
    modified_count = 0
    
    # Process known boss trainers
    for trainer_id, (name, preferred_type) in BOSS_TRAINERS.items():
        # If scaling is enabled, set team sizes based on gym progression
        actual_size = target_size
        if use_scaling:
            # First two gym leaders (Falkner and Bugsy) have smaller teams
            if trainer_id in [20, 21]:  # Falkner and Bugsy
                actual_size = 4
        
        print(f"Setting {name} (ID: {trainer_id}) to have {actual_size} Pokémon")
        
        if set_trainer_team_size(rom, trainer_id, actual_size, use_bst):
            modified_count += 1
            
    # Process rival battles
    for trainer_id in RIVAL_BATTLES:
        # Determine team size based on which rival battle this is
        rival_size = target_size
        if use_scaling:
            if trainer_id == 112:  # First rival battle
                rival_size = 1  # Only starter
                print(f"Setting first Rival battle (ID: {trainer_id}) to have {rival_size} Pokémon")
            elif trainer_id == 113:  # Second rival battle
                rival_size = 4  # Scaled team for second battle
                print(f"Setting second Rival battle (ID: {trainer_id}) to have {rival_size} Pokémon")
            else:  # Later battles
                print(f"Setting Rival battle (ID: {trainer_id}) to have {rival_size} Pokémon")
        else:
            print(f"Setting Rival (ID: {trainer_id}) to have {rival_size} Pokémon")
            
        if set_trainer_team_size(rom, trainer_id, rival_size, use_bst):
            modified_count += 1
    
    # Fix any remaining inconsistencies
    fix_count = fix_team_size_inconsistencies(rom)
    if fix_count > 0:
        print(f"Fixed {fix_count} trainer data inconsistencies")
        modified_count += fix_count
    
    return modified_count

def main():
    """Main function for running the script directly"""
    parser = argparse.ArgumentParser(description="Set all boss trainers to have the specified number of Pokémon")
    parser.add_argument("rom_file", help="Path to the ROM file")
    parser.add_argument("--team-size", type=int, default=4, help="Number of Pokémon for each boss trainer (1-6)")
    parser.add_argument("--output", "-o", help="Output ROM path (default: original_bosses<team_size>.nds)")
    parser.add_argument("--use-bst", action='store_true', help="Use BST-based selection for added Pokémon")
    parser.add_argument("--scaling", action='store_true', 
                       help="Scale team sizes (Falkner/Bugsy: 4 Pokémon, first rival: 1, second rival: 4, others: 6)")
    args = parser.parse_args()
    
    # Validate team size
    if args.team_size < 1 or args.team_size > 6:
        print("Error: Team size must be between 1 and 6")
        return 1
    
    # If scaling is enabled, target size should be 6
    target_size = args.team_size
    if args.scaling:
        target_size = 6
        print("Scaling mode enabled: Falkner and Bugsy will have 4 Pokémon, others will have 6")
    
    # Open ROM
    print(f"Opening ROM file: {args.rom_file}")
    rom = ndspy.rom.NintendoDSRom.fromFile(args.rom_file)
    
    # Modify boss trainers
    modified_count = max_team_size_bosses(rom, target_size, args.use_bst, args.scaling)
    
    # Generate output filename
    if args.output:
        output_path = args.output
    else:
        if args.scaling:
            output_path = os.path.splitext(args.rom_file)[0] + "_bossesScaled.nds"
        else:
            output_path = os.path.splitext(args.rom_file)[0] + f"_bosses{target_size}.nds"
    
    # Save modified ROM
    print(f"Saving modified ROM to {output_path}...")
    rom.saveToFile(output_path)
    print("Done!")
    
    return 0

def read_pokemon_stats(rom):
    """
    Read all Pokémon base stats from the ROM.
    
    Args:
        rom: The ROM object
        
    Returns:
        dict: Dictionary mapping species IDs to their base stats
    """
    try:
        # Get the Pokémon stats NARC
        narc_file_id = rom.filenames.idOf(POKEMON_STATS_NARC_PATH)
        stats_narc = ndspy.narc.NARC(rom.files[narc_file_id])
        
        # Dictionary to store stats for each species
        pokemon_stats = {}
        
        # Parse stats for each Pokémon species
        for species_id, file_data in enumerate(stats_narc.files):
            # Skip empty entries
            if len(file_data) < 28:  # Basic sanity check
                continue
                
            # The base stats are at offset 0x14 (20) in the data
            stats_offset = 0x14
            stats_data = file_data[stats_offset:stats_offset + 6]  # 6 stats, 1 byte each
            
            # Parse the stats
            try:
                stats = stats_struct.parse(stats_data)
                pokemon_stats[species_id] = stats
            except Exception:
                # Skip problematic entries
                continue
        
        return pokemon_stats
    except Exception as e:
        print(f"Error reading Pokémon stats: {e}")
        return {}

def calculate_bst(stats):
    """
    Calculate the Base Stat Total (BST) of a Pokémon.
    
    Args:
        stats: Stats container from stats_struct
        
    Returns:
        int: The Base Stat Total
    """
    return sum(getattr(stats, stat) for stat in STAT_NAMES)

def get_bst_for_species(species_id, pokemon_stats):
    """
    Get the BST for a specific Pokémon species.
    
    Args:
        species_id: The Pokémon species ID
        pokemon_stats: Dictionary of Pokémon stats
        
    Returns:
        int: The BST for the species, or 300 if not found (reasonable default)
    """
    if species_id in pokemon_stats:
        return calculate_bst(pokemon_stats[species_id])
    return 300  # Default BST if not found

def get_mean_bst(pokemon_list, pokemon_stats):
    """
    Calculate the mean (average) BST of a list of Pokémon.
    
    Args:
        pokemon_list: List of Pokémon objects
        pokemon_stats: Dictionary of Pokémon stats
        
    Returns:
        float: The mean BST
    """
    if not pokemon_list:
        return 300.0  # Default if empty list
        
    bst_values = [get_bst_for_species(pokemon.species, pokemon_stats) for pokemon in pokemon_list]
    return statistics.mean(bst_values)

def find_pokemon_in_bst_range(target_bst, pokemon_stats, preferred_type=None, existing_species=None):
    """
    Find a Pokémon within 10% of the target BST.
    
    Args:
        target_bst: The target BST to match
        pokemon_stats: Dictionary of Pokémon stats
        preferred_type: Optional preferred type
        existing_species: List of species IDs to exclude
        
    Returns:
        int: A suitable species ID
    """
    # Set BST range (within 10%)
    min_bst = target_bst * 0.9
    max_bst = target_bst * 1.1
    
    # Filter by type if specified
    valid_species = []
    
    # Define type-specific pool first
    type_pool = None
    if preferred_type and preferred_type in COMMON_POKEMON:
        type_pool = COMMON_POKEMON[preferred_type]
    
    # Check all species in our pool
    for species_id, stats in pokemon_stats.items():
        # Skip existing species
        if existing_species and species_id in existing_species:
            continue
            
        # Calculate BST
        bst = calculate_bst(stats)
        
        # Check if within range
        if min_bst <= bst <= max_bst:
            # If we have a type preference and this species is in our type pool, prioritize it
            if type_pool and species_id in type_pool:
                valid_species.append((species_id, 2))  # Priority 2 for type match + BST match
            else:
                valid_species.append((species_id, 1))  # Priority 1 for BST match only
    
    # If we found type matches, prioritize those
    priority_2 = [sid for sid, priority in valid_species if priority == 2]
    if priority_2:
        return random.choice(priority_2)
    
    # Otherwise use any BST match
    priority_1 = [sid for sid, priority in valid_species if priority == 1]
    if priority_1:
        return random.choice(priority_1)
    
    # Fallback: if no good matches, just pick from type pool or normal pool
    if type_pool:
        return random.choice(type_pool)
    return random.choice(COMMON_POKEMON["Normal"])

if __name__ == "__main__":
    sys.exit(main())
