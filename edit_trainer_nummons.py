#!/usr/bin/env python3
"""
This script directly edits the nummons value and Pokémon team for a trainer in a ROM file.
It modifies the binary data without needing to recompile from assembly source.
"""
import ndspy.rom
import ndspy.narc
import sys
import os
import struct
from construct import Struct, Int8ul, Int16ul, Int32ul, Array, Container

# Import trainer structures from the randomizer
from randomize_trainers import (
    read_trainer_data,
    trainer_data_struct,
    trainer_pokemon_struct,
    trainer_pokemon_moves_struct,
    trainer_struct
)

def get_trainer_binary_data(trainer, include_pokemon=True):
    """Convert trainer data back to binary format"""
    # First, build trainer data without Pokémon
    trainer_without_pokemon = Container()
    for key, value in trainer.items():
        if key != 'pokemon':
            trainer_without_pokemon[key] = value
    
    # Build trainer data binary
    trainer_bin = trainer_data_struct.build(trainer_without_pokemon)
    
    # If requested, add Pokémon data
    if include_pokemon:
        for pokemon in trainer.pokemon[:trainer.nummons]:  # Only include up to nummons Pokémon
            if hasattr(pokemon, 'move1'):
                # Pokémon with moves
                pokemon_bin = trainer_pokemon_moves_struct.build(pokemon)
            else:
                # Pokémon without moves
                pokemon_bin = trainer_pokemon_struct.build(pokemon)
            trainer_bin += pokemon_bin
    
    return trainer_bin

def main():
    # Check if ROM path is provided
    if len(sys.argv) < 2:
        print("Usage: python edit_trainer_nummons.py <rom_file>")
        sys.exit(1)
    
    rom_path = sys.argv[1]
    
    # Open the ROM
    print(f"Opening ROM file: {rom_path}...")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Read trainer data
    print("Reading trainer data...")
    trainers, trainer_narc_data = read_trainer_data(rom)
    print(f"Loaded {len(trainers)} trainers")
    
    # Find Falkner (Trainer ID 20)
    falkner = None
    for trainer_id, trainer in trainers:
        if trainer_id == 20:
            falkner = trainer
            break
    
    if not falkner:
        print("Could not find Falkner (Trainer ID 20) in the ROM!")
        sys.exit(1)
    
    # Print Falkner's current team
    print("\nFalkner's original team:")
    print(f"Number of Pokémon (nummons): {falkner.nummons}")
    for i, pokemon in enumerate(falkner.pokemon):
        print(f"  Pokémon {i}: Species ID {pokemon.species}, Level {pokemon.level}")
    
    # Create a Spearow (Species ID 21) at level 10
    print("\nCreating a Level 10 Spearow...")
    
    # Check if Falkner's Pokémon have moves
    has_moves = hasattr(falkner.pokemon[0], 'move1')
    
    # Create the new Pokémon
    from construct import Container
    spearow = Container()
    spearow.ivs = 50  # Match the IVs of Falkner's other Pokémon
    spearow.abilityslot = 0
    spearow.level = 10
    spearow.species = 21  # Spearow's Species ID
    spearow.ballseal = 0
    
    if has_moves:
        spearow.item = 0  # No held item
        spearow.move1 = 64  # Peck (move ID, adjust as needed)
        spearow.move2 = 45  # Growl
        spearow.move3 = 43  # Leer
        spearow.move4 = 0   # No move
    
    # Add Spearow to Falkner's team
    falkner.pokemon.append(spearow)
    
    # IMPORTANT: Update the nummons value
    old_nummons = falkner.nummons
    falkner.nummons = len(falkner.pokemon)
    print(f"Updated nummons from {old_nummons} to {falkner.nummons}")
    
    # Print Falkner's updated team
    print("\nFalkner's new team:")
    print(f"Number of Pokémon (nummons): {falkner.nummons}")
    for i, pokemon in enumerate(falkner.pokemon):
        print(f"  Pokémon {i}: Species ID {pokemon.species}, Level {pokemon.level}")
    
    # Convert the updated trainer data back to binary
    print("\nConverting updated trainer data to binary...")
    falkner_binary = get_trainer_binary_data(falkner)
    
    # Update the NARC file with the new data
    print("Updating NARC file...")
    trainer_narc_data.files[20] = falkner_binary
    
    # Save the changes back to the ROM
    print("Saving changes to ROM...")
    narc_file_id = rom.filenames.idOf('a/0/5/6')
    rom.files[narc_file_id] = trainer_narc_data.save()
    
    # Save to a new ROM file
    output_path = rom_path.replace(".nds", "_falkner_edited.nds")
    print(f"Saving modified ROM to {output_path}...")
    rom.saveToFile(output_path)
    print("Modified ROM saved successfully!")
    
    print("\nNow run check_trainer_pokemon_count.py on the new ROM to verify the changes.")

if __name__ == "__main__":
    main()
