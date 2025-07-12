#!/usr/bin/env python3
"""
Debug specific trainer to understand parsing discrepancies
"""

import ndspy.rom
import ndspy.narc
import sys
from trainer_data_parser import read_trainer_data, DEBUG_TRAINER_PARSING, trainer_pokemon_struct, trainer_pokemon_moves_struct
from boss_team_adjuster import get_trainer_pokemon

def debug_trainer_400(rom_path):
    """Debug trainer 400 specifically"""
    
    print(f"Loading ROM: {rom_path}")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    trainer_id = 400
    
    print(f"\n=== DEBUGGING TRAINER {trainer_id} ===")
    
    # Method 1: Our trainer data parser
    print("\n--- Method 1: trainer_data_parser.py ---")
    trainers, _ = read_trainer_data(rom)
    trainer_dict = {tid: trainer for tid, trainer in trainers}
    
    if trainer_id in trainer_dict:
        trainer = trainer_dict[trainer_id]
        print(f"Found trainer {trainer_id}: {len(trainer.pokemon)} Pokémon")
        for i, pokemon in enumerate(trainer.pokemon):
            print(f"  Pokémon {i}: Species={pokemon.species}, Level={pokemon.level}")
    else:
        print(f"Trainer {trainer_id} not found in parsed data")
    
    # Method 2: Boss team adjuster 
    print("\n--- Method 2: boss_team_adjuster.py ---")
    try:
        boss_pokemon, boss_has_moves = get_trainer_pokemon(rom, trainer_id)
        print(f"Boss adjuster found {len(boss_pokemon)} Pokémon (has_moves={boss_has_moves})")
        for i, pokemon in enumerate(boss_pokemon):
            print(f"  Pokémon {i}: Species={pokemon.species}, Level={pokemon.level}")
    except Exception as e:
        print(f"Boss adjuster error: {e}")
    
    # Method 3: Manual data inspection
    print("\n--- Method 3: Raw data inspection ---")
    narc_file_id = rom.filenames.idOf("a/0/5/6")
    trainer_narc = rom.files[narc_file_id]
    trainer_narc_data = ndspy.narc.NARC(trainer_narc)
    
    if trainer_id < len(trainer_narc_data.files):
        data = trainer_narc_data.files[trainer_id]
        print(f"Raw data length: {len(data)} bytes")
        
        # Try both interpretations
        print("\nTrying 8-byte format (no moves):")
        if len(data) % 8 == 0:
            num_pokemon_8 = len(data) // 8
            print(f"  Would give {num_pokemon_8} Pokémon")
            for i in range(min(num_pokemon_8, 6)):  # Show first 6
                offset = i * 8
                pokemon_data = data[offset:offset+8]
                try:
                    pokemon = trainer_pokemon_struct.parse(pokemon_data)
                    print(f"    Pokémon {i}: Species={pokemon.species}, Level={pokemon.level}")
                except Exception as e:
                    print(f"    Pokémon {i}: Parse error - {e}")
        
        print("\nTrying 18-byte format (with moves):")
        if len(data) % 18 == 0:
            num_pokemon_18 = len(data) // 18
            print(f"  Would give {num_pokemon_18} Pokémon")
            for i in range(min(num_pokemon_18, 6)):  # Show first 6
                offset = i * 18
                pokemon_data = data[offset:offset+18]
                try:
                    pokemon = trainer_pokemon_moves_struct.parse(pokemon_data)
                    print(f"    Pokémon {i}: Species={pokemon.species}, Level={pokemon.level}")
                except Exception as e:
                    print(f"    Pokémon {i}: Parse error - {e}")
                    
        # Print raw hex data
        print(f"\nRaw hex data:")
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            print(f"  {i:04X}: {hex_str}")
    else:
        print(f"Trainer {trainer_id} data not found")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_trainer_400.py <rom_file>")
        sys.exit(1)
        
    debug_trainer_400(sys.argv[1])
