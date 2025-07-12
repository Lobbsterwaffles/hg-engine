#!/usr/bin/env python3
"""
Test script to verify trainer Pokémon counts are correct.
This compares our trainer data parser with the boss team adjuster approach.
"""

import ndspy.rom
import sys
from trainer_data_parser import read_trainer_data
from boss_team_adjuster import get_trainer_pokemon

def test_trainer_counts(rom_path):
    """Test that trainer counts match between our methods and boss team adjuster"""
    
    print(f"Loading ROM: {rom_path}")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Test some key trainers
    test_trainers = [
        20,   # Falkner (Gym Leader)
        21,   # Bugsy (Gym Leader)  
        30,   # Whitney (Gym Leader)
        112,  # Rival battle
        400,  # Lance (Elite Four)
        500,  # Random trainer
    ]
    
    # Get trainer data using our parser
    print("\n=== Using trainer_data_parser.py ===")
    trainers, _ = read_trainer_data(rom)
    trainer_dict = {tid: trainer for tid, trainer in trainers}
    
    print("\n=== Using boss_team_adjuster.py ===")
    
    print("\n=== COMPARISON ===")
    for trainer_id in test_trainers:
        try:
            # Our method
            if trainer_id in trainer_dict:
                our_pokemon = trainer_dict[trainer_id].pokemon
                our_count = len(our_pokemon)
                our_has_moves = any(hasattr(p, 'move1') for p in our_pokemon)
            else:
                our_count = 0
                our_has_moves = False
                
            # Boss team adjuster method
            try:
                boss_pokemon, boss_has_moves = get_trainer_pokemon(rom, trainer_id)
                boss_count = len(boss_pokemon)
            except:
                boss_count = 0
                boss_has_moves = False
                
            # Compare
            match = "[OK]" if our_count == boss_count else "[MISMATCH]"
            moves_match = "[OK]" if our_has_moves == boss_has_moves else "[MOVE_MISMATCH]"
            
            print(f"Trainer {trainer_id:3d}: Parser={our_count} ({our_has_moves}), Boss={boss_count} ({boss_has_moves}) {match} {moves_match}")
            
            if our_count != boss_count:
                print(f"  *** MISMATCH: Our parser found {our_count}, boss adjuster found {boss_count} ***")
                
        except Exception as e:
            print(f"Trainer {trainer_id:3d}: ERROR - {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_trainer_counts.py <rom_file>")
        sys.exit(1)
        
    test_trainer_counts(sys.argv[1])
