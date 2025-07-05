#!/usr/bin/env python3
"""
Trainer Pokémon Manager
-----------------------
This script lets you add and remove Pokémon from trainers in HeartGold/SoulSilver ROMs.

It updates both:
1. The trainer's Pokémon data (species, level, moves) in NARC file a/0/5/6
2. The trainer's poke_count value in NARC file a/0/5/5

Usage:
  python trainer_pokemon_manager.py add <rom_file> <trainer_id> <species_id> <level>
  python trainer_pokemon_manager.py remove <rom_file> <trainer_id> <pokemon_index>
  python trainer_pokemon_manager.py list <rom_file> <trainer_id>
"""

from construct import *
import ndspy.rom
import ndspy.narc
import sys
import os

# Pokémon entry structure (each Pokémon is 8 bytes) - Fixed alignment
trainer_pokemon_struct = Struct(
    "ivs" / Int8ul,             # 1 byte - IVs
    "abilityslot" / Int8ul,     # 1 byte - Ability slot
    "level" / Int16ul,          # 2 bytes - Level (halfword)
    "species" / Int16ul,        # 2 bytes - Species ID (halfword)
    "ballseal" / Int16ul,       # 2 bytes - Ball seal (halfword, not byte!)
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
        from construct import Container
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
                new_pokemon.move2 = 0   # No move
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

def remove_pokemon_from_trainer(rom, trainer_id, pokemon_index):
    """
    Remove a Pokémon from a trainer's team.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        pokemon_index: The index of the Pokémon to remove (0-based)
        
    Returns:
        bool: True if successful
    """
    try:
        # Get the trainer's current Pokémon
        pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
        
        # Check if the index is valid
        if pokemon_index < 0 or pokemon_index >= len(pokemon_list):
            print(f"Error: Pokémon index {pokemon_index} is out of range. Trainer has {len(pokemon_list)} Pokémon.")
            return False
        
        # Make sure we're not removing the last Pokémon
        if len(pokemon_list) <= 1:
            print("Error: Cannot remove the last Pokémon from a trainer.")
            return False
        
        # Remove the Pokémon
        removed_pokemon = pokemon_list.pop(pokemon_index)
        print(f"Removed Pokémon {removed_pokemon.species} (Level {removed_pokemon.level}) from trainer {trainer_id}")
        
        # Save the updated Pokémon list
        save_trainer_pokemon(rom, trainer_id, pokemon_list, has_moves)
        
        # Update the trainer's poke_count value
        update_trainer_poke_count(rom, trainer_id, len(pokemon_list))
        
        return True
    except Exception as e:
        print(f"Error removing Pokémon from trainer {trainer_id}: {e}")
        return False

def list_trainer_pokemon(rom, trainer_id):
    """
    List all Pokémon in a trainer's team.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
    """
    try:
        # Get the trainer's current Pokémon
        pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
        
        print(f"Trainer {trainer_id} has {len(pokemon_list)} Pokémon:")
        for i, pokemon in enumerate(pokemon_list):
            print(f"  {i}: Species {pokemon.species}, Level {pokemon.level}", end="")
            if has_moves:
                print(f", Moves: {pokemon.move1}, {pokemon.move2}, {pokemon.move3}, {pokemon.move4}")
            else:
                print("")
    except Exception as e:
        print(f"Error listing Pokémon for trainer {trainer_id}: {e}")

def main():
    """Main function for running from command line"""
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    rom_path = sys.argv[2]
    
    # Open ROM
    print(f"Opening ROM file: {rom_path}...")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    if command == "list":
        if len(sys.argv) < 4:
            print("Error: Missing trainer_id argument")
            print(__doc__)
            sys.exit(1)
        
        trainer_id = int(sys.argv[3])
        list_trainer_pokemon(rom, trainer_id)
        
    elif command == "add":
        if len(sys.argv) < 6:
            print("Error: Missing arguments")
            print(__doc__)
            sys.exit(1)
        
        trainer_id = int(sys.argv[3])
        species_id = int(sys.argv[4])
        level = int(sys.argv[5])
        
        moves = None
        if len(sys.argv) >= 10:
            moves = [int(sys.argv[6]), int(sys.argv[7]), int(sys.argv[8]), int(sys.argv[9])]
        
        if add_pokemon_to_trainer(rom, trainer_id, species_id, level, moves):
            output_path = rom_path.replace(".nds", f"_trainer{trainer_id}_edited.nds")
            print(f"Saving modified ROM to {output_path}...")
            rom.saveToFile(output_path)
            print(f"Modified ROM saved successfully!")
        
    elif command == "remove":
        if len(sys.argv) < 5:
            print("Error: Missing arguments")
            print(__doc__)
            sys.exit(1)
        
        trainer_id = int(sys.argv[3])
        pokemon_index = int(sys.argv[4])
        
        if remove_pokemon_from_trainer(rom, trainer_id, pokemon_index):
            output_path = rom_path.replace(".nds", f"_trainer{trainer_id}_edited.nds")
            print(f"Saving modified ROM to {output_path}...")
            rom.saveToFile(output_path)
            print(f"Modified ROM saved successfully!")
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
