#!/usr/bin/env python3
"""
This script directly edits Falkner's team in a ROM file by:
1. Changing his nummons value to 3
2. Adding a Level 10 Spearow to his team
3. Saving the changes back to the ROM
"""
import ndspy.rom
import ndspy.narc
import sys
import os
from construct import Container, Struct, Int8ul, Int16ul, Int32ul, Array

# Define the Pokémon structures
# Basic Pokémon structure (8 bytes per Pokémon)
trainer_pokemon_struct = Struct(
    "ivs" / Int8ul,             # 1 byte - IVs
    "abilityslot" / Int8ul,     # 1 byte - Ability slot
    "level" / Int16ul,          # 2 bytes - Level (halfword)
    "species" / Int16ul,        # 2 bytes - Species ID (halfword)
    "ballseal" / Int16ul,       # 2 bytes - Ball seal (halfword, not byte!)
)

# Pokémon with moves structure (18 bytes per Pokémon)
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

def main():
    # Check if ROM path is provided
    if len(sys.argv) < 2:
        print("Usage: python edit_falkner_team.py <rom_file>")
        sys.exit(1)
    
    rom_path = sys.argv[1]
    
    # Open the ROM
    print(f"Opening ROM file: {rom_path}...")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Get the trainer data NARC
    print("Reading trainer data NARC...")
    narc_file_id = rom.filenames.idOf("a/0/5/6")
    trainer_narc_data = ndspy.narc.NARC(rom.files[narc_file_id])
    
    # Falkner is Trainer ID 20
    FALKNER_ID = 20
    
    # Get Falkner's current data
    falkner_data = trainer_narc_data.files[FALKNER_ID]
    print(f"Falkner's data size: {len(falkner_data)} bytes")
    
    # Check if Falkner has Pokémon with moves
    # A trainer with moves will have 18 bytes per Pokémon
    has_moves = (len(falkner_data) % 18 == 0)
    pokemon_size = 18 if has_moves else 8
    
    # Calculate current number of Pokémon
    num_pokemon = len(falkner_data) // pokemon_size
    print(f"Falkner currently has {num_pokemon} Pokémon with{'out' if not has_moves else ''} moves")
    
    # Let's see what Pokémon Falkner has
    print("\nFalkner's current Pokémon:")
    for i in range(num_pokemon):
        start_offset = i * pokemon_size
        pokemon_data = falkner_data[start_offset:start_offset + pokemon_size]
        
        if has_moves:
            # Parse with moves struct
            pokemon = trainer_pokemon_moves_struct.parse(pokemon_data)
        else:
            # Parse with basic struct
            pokemon = trainer_pokemon_struct.parse(pokemon_data)
        
        print(f"Pokémon {i}: Species ID {pokemon.species}, Level {pokemon.level}")
        if has_moves:
            print(f"   Moves: {pokemon.move1}, {pokemon.move2}, {pokemon.move3}, {pokemon.move4}")
    
    # Create a new Spearow
    print("\nCreating a Level 10 Spearow...")
    spearow = Container()
    spearow.ivs = 50  # Match the IVs of Falkner's other Pokémon
    spearow.abilityslot = 0
    spearow.level = 10
    spearow.species = 21  # Spearow's Species ID
    spearow.ballseal = 0
    
    if has_moves:
        spearow.item = 0  # No held item
        spearow.move1 = 64  # Peck (move ID)
        spearow.move2 = 45  # Growl (move ID)
        spearow.move3 = 43  # Leer (move ID)
        spearow.move4 = 0   # No move
    
    # Create new data array with space for the new Pokémon
    new_data = bytearray()
    
    # First copy all existing Pokémon data
    new_data.extend(falkner_data)
    
    # Then add the Spearow
    if has_moves:
        spearow_binary = trainer_pokemon_moves_struct.build(spearow)
    else:
        spearow_binary = trainer_pokemon_struct.build(spearow)
    
    new_data.extend(spearow_binary)
    
    # Update Falkner's data in the NARC
    trainer_narc_data.files[FALKNER_ID] = bytes(new_data)
    
    # Update the ROM with the modified trainer data
    rom.files[narc_file_id] = trainer_narc_data.save()
    
    # Save to a new ROM file
    output_path = rom_path.replace(".nds", "_falkner_3pokemon.nds")
    print(f"\nSaving modified ROM to {output_path}...")
    rom.saveToFile(output_path)
    print("Modified ROM saved successfully!")
    
    print("\nNow run check_trainer_pokemon_count.py on the new ROM to verify the changes.")

if __name__ == "__main__":
    main()
