"""
Randomizer functions for Pokémon HGSS
-------------------------------------
This file contains helper functions for the randomizer, including
team size adjustment functions that can be called from the main randomizer.
"""

import random
from construct import Container

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

def get_trainer_poke_count(rom, trainer_id):
    """
    Get a trainer's poke_count value from the ROM.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        
    Returns:
        int: The poke_count value
    """
    # Get the trainer data NARC
    from ndspy.narc import NARC
    narc_file_id = rom.filenames.idOf("a/0/5/5")
    trainer_data_narc = NARC(rom.files[narc_file_id])
    
    # Check if trainer exists
    if trainer_id >= len(trainer_data_narc.files):
        raise ValueError(f"Trainer ID {trainer_id} does not exist in the ROM")
    
    # Get trainer's data
    trainer_data = trainer_data_narc.files[trainer_id]
    
    # poke_count is at offset 3
    return trainer_data[3]

def update_trainer_poke_count(rom, trainer_id, new_count, log_function=None):
    """
    Update a trainer's poke_count value in the ROM.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        new_count: The new number of Pokémon
        log_function: Optional logging function
    """
    if log_function is None:
        log_function = print
        
    # Get the trainer data NARC
    from ndspy.narc import NARC
    narc_file_id = rom.filenames.idOf("a/0/5/5")
    trainer_data_narc = NARC(rom.files[narc_file_id])
    
    # Check if trainer exists
    if trainer_id >= len(trainer_data_narc.files):
        raise ValueError(f"Trainer ID {trainer_id} does not exist in the ROM")
    
    # Get trainer's data
    trainer_data = bytearray(trainer_data_narc.files[trainer_id])
    
    # Update poke_count value
    trainer_data[3] = new_count
    
    # Save back to NARC
    trainer_data_narc.files[trainer_id] = bytes(trainer_data)
    rom.files[narc_file_id] = trainer_data_narc.save()
    
    log_function(f"Updated trainer {trainer_id}'s poke_count to {new_count}")

def add_pokemon_to_team(trainer, species_id, level, moves=None):
    """
    Add a Pokémon to a trainer's team.
    
    Args:
        trainer: The trainer object
        species_id: The Pokémon species ID
        level: The Pokémon's level
        moves: Optional list of move IDs
        
    Returns:
        The updated trainer object
    """
    # Create the new Pokémon
    new_pokemon = Container()
    new_pokemon.ivs = 50  # Default IVs
    new_pokemon.abilityslot = 0
    new_pokemon.level = level
    new_pokemon.species = species_id
    new_pokemon.ballseal = 0
    
    # Check if trainer has Pokémon with moves
    has_moves = hasattr(trainer, 'pokemon') and trainer.pokemon and hasattr(trainer.pokemon[0], 'move1')
    
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
            new_pokemon.move2 = 0   # No move
            new_pokemon.move3 = 0   # No move
            new_pokemon.move4 = 0   # No move
    
    # Add the new Pokémon to the trainer's team
    trainer.pokemon.append(new_pokemon)
    trainer.nummons = len(trainer.pokemon)
    
    return trainer

def set_trainer_team_size(trainer_id, trainer, target_size, mondata=None, log_function=None):
    """
    Set a trainer's team size to the specified target.
    
    Args:
        trainer_id: The trainer ID (for reference only)
        trainer: The trainer object
        target_size: The desired team size
        mondata: Optional Pokémon data for species selection
        log_function: Optional logging function
        
    Returns:
        The updated trainer object
    """
    if log_function is None:
        log_function = print
        
    current_size = len(trainer.pokemon)
    
    # If already at target size, nothing to do
    if current_size == target_size:
        log_function(f"Trainer {trainer_id} already has {target_size} Pokémon")
        return trainer
    
    # If we need to remove Pokémon
    if current_size > target_size:
        # Remove from the end
        trainer.pokemon = trainer.pokemon[:target_size]
        trainer.nummons = target_size
        log_function(f"Reduced trainer {trainer_id}'s team from {current_size} to {target_size} Pokémon")
        return trainer
        
    # If we need to add Pokémon
    if current_size < target_size:
        # Determine preferred type for this trainer
        preferred_type = None
        if trainer_id in BOSS_TRAINERS:
            preferred_type = BOSS_TRAINERS[trainer_id][1]
        
        # Determine level for new Pokémon
        levels = [p.level for p in trainer.pokemon]
        avg_level = sum(levels) / len(levels) if levels else 30
        
        # Add new Pokémon
        for _ in range(target_size - current_size):
            # Choose a species
            if mondata and len(mondata) > 0:
                # If we have mondata, choose a random species from it
                species_id = random.choice(list(mondata.keys()))
                
                # Try to pick a Pokémon of similar strength to existing team
                if hasattr(trainer.pokemon[0], 'species') and trainer.pokemon[0].species in mondata:
                    bst_target = mondata[trainer.pokemon[0].species].bst
                    
                    # Try to find a Pokémon with similar BST
                    candidates = []
                    for mon_id, mon_data in mondata.items():
                        if abs(mon_data.bst - bst_target) < 50:  # Within 50 BST
                            candidates.append(mon_id)
                    
                    if candidates:
                        species_id = random.choice(candidates)
            
            elif preferred_type and preferred_type in COMMON_POKEMON:
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
            if hasattr(trainer.pokemon[0], 'move1'):
                # Some basic move IDs (Tackle, Growl, Quick Attack, etc.)
                move_options = [33, 45, 98, 28, 39, 31, 43]
                moves = [
                    random.choice(move_options),
                    random.choice(move_options),
                    0,  # Empty move
                    0   # Empty move
                ]
                # Randomize a bit to avoid all having the same moves
                random.shuffle(moves)
            
            # Add the Pokémon
            trainer = add_pokemon_to_team(trainer, species_id, new_level, moves)
        
        log_function(f"Expanded trainer {trainer_id}'s team from {current_size} to {target_size} Pokémon")
    
    return trainer

def max_team_size_bosses(trainers, target_size=6, mondata=None, log_function=None):
    """
    Set all boss trainers to have full teams of the specified size.
    
    Args:
        trainers: List of (trainer_id, trainer) tuples
        target_size: The desired team size for bosses (default 6)
        mondata: Optional Pokémon data for species selection
        log_function: Optional logging function
    
    Returns:
        List of modified (trainer_id, trainer) tuples
    """
    if log_function is None:
        log_function = print
        
    modified_trainers = []
    modified_count = 0
    
    # Process all trainers
    for trainer_id, trainer in trainers:
        # Skip invalid trainers
        if not hasattr(trainer, 'pokemon') or not trainer.pokemon:
            continue
        
        # Check if this is a boss trainer
        is_boss = trainer_id in BOSS_TRAINERS
        is_rival = False
        
        # Check for rival battles
        for rival_id, should_have_full in RIVAL_BATTLES:
            if trainer_id == rival_id:
                is_rival = should_have_full
                break
        
        # Only modify boss trainers and eligible rival battles
        if is_boss or is_rival:
            trainer_name = BOSS_TRAINERS.get(trainer_id, ("Rival", None))[0] if is_boss else "Rival"
            log_function(f"Setting {trainer_name} (ID: {trainer_id}) to have {target_size} Pokémon")
            
            # Update the trainer's team size
            updated_trainer = set_trainer_team_size(trainer_id, trainer, target_size, mondata, log_function)
            modified_trainers.append((trainer_id, updated_trainer))
            modified_count += 1
        else:
            # Keep the trainer unchanged
            modified_trainers.append((trainer_id, trainer))
    
    log_function(f"Modified {modified_count} boss trainers to have {target_size} Pokémon")
    return modified_trainers
