#!/usr/bin/env python3
"""
Test script to verify that the trainer randomizer now properly synchronizes
the poke_count field with actual Pokemon data after randomization.
"""

import ndspy.rom
import sys
import os
from trainer_data_parser import get_trainer_poke_count_from_rom, read_trainer_data
from boss_team_adjuster import get_trainer_pokemon


def test_trainer_synchronization_before_after(original_rom_path, randomized_rom_path, test_trainers=None):
    """
    Test trainer synchronization by comparing original and randomized ROMs.
    
    Args:
        original_rom_path: Path to the original ROM file
        randomized_rom_path: Path to the randomized ROM file  
        test_trainers: List of specific trainer IDs to test (default: test first 50)
    """
    print(f"=== TRAINER SYNCHRONIZATION TEST ===")
    print(f"Original ROM: {original_rom_path}")
    print(f"Randomized ROM: {randomized_rom_path}")
    
    # Load both ROMs
    print("Loading ROMs...")
    original_rom = ndspy.rom.NintendoDSRom.fromFile(original_rom_path)
    randomized_rom = ndspy.rom.NintendoDSRom.fromFile(randomized_rom_path)
    
    # Get trainer data from both
    print("Reading trainer data...")
    original_trainers, _ = read_trainer_data(original_rom)
    randomized_trainers, _ = read_trainer_data(randomized_rom)
    
    # Test specific trainers or first 50
    if test_trainers is None:
        test_trainers = list(range(min(50, len(original_trainers))))
    
    print(f"Testing {len(test_trainers)} trainers for synchronization...\n")
    
    sync_issues = []
    improvements = []
    
    for trainer_id in test_trainers:
        if trainer_id >= len(original_trainers) or trainer_id >= len(randomized_trainers):
            continue
            
        # Original ROM data
        orig_poke_count = get_trainer_poke_count_from_rom(original_rom, trainer_id)
        try:
            orig_pokemon, _ = get_trainer_pokemon(original_rom, trainer_id)
            orig_actual_count = len(orig_pokemon)
        except:
            orig_actual_count = 0
        
        # Randomized ROM data
        rand_poke_count = get_trainer_poke_count_from_rom(randomized_rom, trainer_id)
        try:
            rand_pokemon, _ = get_trainer_pokemon(randomized_rom, trainer_id)
            rand_actual_count = len(rand_pokemon)
        except:
            rand_actual_count = 0
        
        # Check synchronization
        orig_synced = (orig_poke_count == orig_actual_count)
        rand_synced = (rand_poke_count == rand_actual_count)
        
        # Report results
        if not rand_synced:
            sync_issues.append((trainer_id, rand_poke_count, rand_actual_count))
            status = "[SYNC ISSUE]"
        elif not orig_synced and rand_synced:
            improvements.append((trainer_id, orig_poke_count, orig_actual_count, rand_poke_count, rand_actual_count))
            status = "[IMPROVED]"
        elif orig_synced and rand_synced:
            status = "[OK]"
        else:
            status = "[DEGRADED]"
        
        # Only show issues and improvements
        if status in ["[SYNC ISSUE]", "[IMPROVED]", "[DEGRADED]"]:
            print(f"Trainer {trainer_id:3d} {status}")
            print(f"  Original: poke_count={orig_poke_count}, actual={orig_actual_count} {'OK' if orig_synced else 'MISMATCH'}")
            print(f"  Random:   poke_count={rand_poke_count}, actual={rand_actual_count} {'OK' if rand_synced else 'MISMATCH'}")
            print()
    
    # Summary
    print(f"{'='*60}")
    print(f"SYNCHRONIZATION TEST RESULTS:")
    print(f"Total trainers tested: {len(test_trainers)}")
    print(f"Synchronization issues found: {len(sync_issues)}")
    print(f"Trainers improved by fix: {len(improvements)}")
    
    if sync_issues:
        print(f"\n[ERROR] Synchronization issues in randomized ROM:")
        for trainer_id, poke_count, actual_count in sync_issues:
            print(f"  Trainer {trainer_id}: poke_count={poke_count} but actual={actual_count}")
    
    if improvements:
        print(f"\n[SUCCESS] Trainers fixed by synchronization update:")
        for trainer_id, orig_poke, orig_actual, rand_poke, rand_actual in improvements:
            print(f"  Trainer {trainer_id}: {orig_poke}!={orig_actual} -> {rand_poke}={rand_actual}")
    
    if not sync_issues:
        print(f"\nSUCCESS: All tested trainers show proper synchronization!")
        print(f"SUCCESS: The trainer randomizer poke_count fix is working correctly.")
        return True
    else:
        print(f"\nERROR: Found {len(sync_issues)} synchronization issues.")
        print(f"ERROR: The trainer randomizer poke_count fix needs more work.")
        return False


def test_specific_problematic_trainers(rom_path):
    """
    Test the specific trainers that were known to have issues.
    
    Args:
        rom_path: Path to the ROM file
    """
    print(f"=== TESTING SPECIFIC PROBLEMATIC TRAINERS ===")
    print(f"ROM: {rom_path}")
    
    # Known problematic trainers from our previous testing
    problematic_trainers = [400, 500, 20, 21, 30]
    
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    print(f"Testing trainers: {problematic_trainers}\n")
    
    all_synced = True
    
    for trainer_id in problematic_trainers:
        # Get poke_count field
        poke_count = get_trainer_poke_count_from_rom(rom, trainer_id)
        
        # Get actual Pokemon data
        try:
            pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
            actual_count = len(pokemon_list)
            moves_info = "with moves" if has_moves else "without moves"
        except Exception as e:
            actual_count = 0
            moves_info = f"ERROR: {e}"
        
        # Check synchronization
        is_synced = (poke_count == actual_count)
        status = "SYNCED" if is_synced else "NOT SYNCED"
        
        print(f"Trainer {trainer_id}: {status}")
        print(f"  poke_count field: {poke_count}")
        print(f"  actual Pokemon: {actual_count} ({moves_info})")
        
        if not is_synced:
            all_synced = False
            print(f"  [ISSUE] Mismatch detected!")
        
        print()
    
    if all_synced:
        print("SUCCESS: All problematic trainers are now properly synchronized!")
    else:
        print("ERROR: Some trainers still have synchronization issues.")
    
    return all_synced


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_synchronization_fix.py <randomized_rom> [original_rom]")
        print("  python test_synchronization_fix.py <randomized_rom> --specific")
        print("")
        print("Examples:")
        print("  python test_synchronization_fix.py randomized.nds original.nds")
        print("  python test_synchronization_fix.py randomized.nds --specific")
        sys.exit(1)
    
    randomized_rom_path = sys.argv[1]
    
    if not os.path.exists(randomized_rom_path):
        print(f"Error: ROM file {randomized_rom_path} not found")
        sys.exit(1)
    
    if len(sys.argv) >= 3 and sys.argv[2] == "--specific":
        # Test specific problematic trainers
        success = test_specific_problematic_trainers(randomized_rom_path)
    elif len(sys.argv) >= 3:
        # Compare original vs randomized
        original_rom_path = sys.argv[2]
        if not os.path.exists(original_rom_path):
            print(f"Error: Original ROM file {original_rom_path} not found")
            sys.exit(1)
        success = test_trainer_synchronization_before_after(original_rom_path, randomized_rom_path)
    else:
        # Test just the randomized ROM for sync issues
        success = test_specific_problematic_trainers(randomized_rom_path)
    
    sys.exit(0 if success else 1)
