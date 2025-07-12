#!/usr/bin/env python3
"""
Quick test to verify boss trainers are properly synchronized after team size adjustments.
"""

import ndspy.rom
import sys
from trainer_data_parser import get_trainer_poke_count_from_rom
from boss_team_adjuster import get_trainer_pokemon

def test_boss_trainers(rom_path):
    """Test specific boss trainers that were modified."""
    
    # Boss trainers that were adjusted to 6 Pokemon
    boss_trainers = [
        (20, "Falkner"),
        (21, "Bugsy"), 
        (30, "Whitney"),
        (31, "Morty"),
        (253, "Brock"),
        (254, "Misty"),
        (258, "Sabrina"),
        (259, "Blaine"),
        (112, "Rival"),
        (244, "Lance")
    ]
    
    print(f"Testing boss trainer synchronization in: {rom_path}")
    print(f"Expected: All trainers should have poke_count = actual_count = 6\n")
    
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    all_good = True
    
    for trainer_id, name in boss_trainers:
        # Get poke_count field
        poke_count = get_trainer_poke_count_from_rom(rom, trainer_id)
        
        # Get actual Pokemon
        try:
            pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
            actual_count = len(pokemon_list)
            moves_info = "with moves" if has_moves else "without moves"
        except Exception as e:
            actual_count = 0
            moves_info = f"ERROR: {e}"
        
        # Check if properly synchronized
        is_synced = (poke_count == actual_count)
        expected_six = (poke_count == 6 and actual_count == 6)
        
        status = "PERFECT" if expected_six else ("SYNCED" if is_synced else "ISSUE")
        
        print(f"Trainer {trainer_id:3d} ({name:8s}): {status}")
        print(f"  poke_count: {poke_count}, actual: {actual_count} ({moves_info})")
        
        if not is_synced:
            all_good = False
            print(f"  [ERROR] Synchronization issue!")
        elif not expected_six:
            print(f"  [NOTE] Synchronized but not 6 Pokemon as expected")
        
        print()
    
    if all_good:
        print("SUCCESS: All boss trainers are properly synchronized!")
    else:
        print("ERROR: Some boss trainers have synchronization issues.")
    
    return all_good

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_boss_sync.py <rom_path>")
        sys.exit(1)
    
    success = test_boss_trainers(sys.argv[1])
    sys.exit(0 if success else 1)
