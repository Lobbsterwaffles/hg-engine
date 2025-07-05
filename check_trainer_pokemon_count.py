#!/usr/bin/env python3
"""
This script analyzes a Pokémon ROM file to check how many Pokémon each trainer has,
and explains how the nummons value in the assembly relates to the compiled ROM.
"""
import ndspy.rom
import ndspy.narc
import sys
import os
import struct
from construct import Struct, Int8ul, Int16ul, Int32ul, Array, Const, Padding, this

# Import functions from randomize_trainers to reuse code
# (Note: We're using some of the same structures from the randomizer)
from randomize_trainers import (
    read_trainer_data,
)

def main():
    # Check if ROM path is provided
    if len(sys.argv) < 2:
        print("Usage: python check_trainer_pokemon_count.py <rom_file>")
        sys.exit(1)
    
    rom_path = sys.argv[1]
    
    # Open the ROM
    print(f"Opening ROM file: {rom_path}...")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Read trainer data
    print("Reading trainer data...")
    trainers, trainer_narc_data = read_trainer_data(rom)
    print(f"Loaded {len(trainers)} trainers")
    
    # Look at Falkner's data specifically (Trainer ID 20)
    print("\n--- Analyzing Falkner (Trainer ID 20) ---")
    falkner = None
    for trainer_id, trainer in trainers:
        if trainer_id == 20:
            falkner = trainer
            break
    
    if falkner:
        print(f"Falkner's nummons value: {falkner.nummons}")
        print(f"Actual number of Pokémon in team: {len(falkner.pokemon)}")
        print("\nFalkner's Pokémon:")
        for i, pokemon in enumerate(falkner.pokemon):
            print(f"  Pokémon {i}: Species ID {pokemon.species}, Level {pokemon.level}")
        
        # Check if there are additional fields that might store the team size
        print("\nAll fields in Falkner's data structure:")
        for field_name, field_value in falkner.items():
            if field_name != 'pokemon':  # Skip the pokemon array for clarity
                print(f"  {field_name}: {field_value}")
    else:
        print("Could not find Falkner (Trainer ID 20) in the ROM!")
    
    # Show distribution of team sizes
    team_sizes = {}
    for trainer_id, trainer in trainers:
        if not hasattr(trainer, 'nummons'):
            continue
        
        size = trainer.nummons
        if size not in team_sizes:
            team_sizes[size] = 0
        team_sizes[size] += 1
    
    print("\n--- Team Size Distribution ---")
    print("Number of Pokémon | Number of Trainers")
    for size, count in sorted(team_sizes.items()):
        print(f"{size:^16} | {count:^17}")
    
    # Look for discrepancies between nummons and actual team size
    print("\n--- Checking for Discrepancies ---")
    discrepancies = []
    for trainer_id, trainer in trainers:
        if hasattr(trainer, 'nummons') and hasattr(trainer, 'pokemon'):
            if trainer.nummons != len(trainer.pokemon):
                discrepancies.append((trainer_id, trainer.nummons, len(trainer.pokemon)))
    
    if discrepancies:
        print("Found trainers where nummons doesn't match actual team size:")
        print("Trainer ID | nummons | Actual Team Size")
        for trainer_id, nummons, actual_size in discrepancies:
            print(f"{trainer_id:^10} | {nummons:^7} | {actual_size:^15}")
    else:
        print("No discrepancies found - all trainers have nummons matching their actual team size.")
    
    print("\n--- Understanding nummons in the ROM ---")
    print("The nummons value in trainers.s is the value that gets compiled into the ROM.")
    print("This value tells the game how many Pokémon to load for each trainer.")
    print("When a trainer battle starts, the game reads this value to determine")
    print("how many Pokémon the trainer should have in the battle.")
    print("\nIf you want to add more Pokémon to a trainer like Falkner, you need to:")
    print("1. Change the nummons value in trainers.s to the new team size")
    print("2. Add the new Pokémon data in the party section")
    print("3. Recompile the ROM so the changes take effect")

if __name__ == "__main__":
    main()
