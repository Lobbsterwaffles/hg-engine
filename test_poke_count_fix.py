#!/usr/bin/env python3
"""
Test script to verify that trainer_data_parser now correctly reads the authoritative
poke_count field from trainer data NARC, which is what boss_team_adjuster updates.
"""

import ndspy.rom
import sys
from trainer_data_parser import read_trainer_data, get_trainer_poke_count_from_rom
from boss_team_adjuster import get_trainer_pokemon


def compare_poke_counts(rom_path):
    """
    Compare poke_count values between different methods to ensure consistency.
    
    Args:
        rom_path: Path to the ROM file
    """
    print(f"Opening ROM: {rom_path}")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    print("Reading trainer data...")
    trainers, _ = read_trainer_data(rom)
    
    print(f"\nTesting Pokémon count consistency for first 50 trainers...\n")
    
    mismatches = []
    
    for i in range(min(50, len(trainers))):
        trainer_id, trainer = trainers[i]
        
        # Method 1: Get authoritative poke_count from trainer data NARC (offset 3)
        authoritative_count = get_trainer_poke_count_from_rom(rom, trainer_id)
        
        # Method 2: Get count from our trainer parser
        parser_count = trainer.nummons
        
        # Method 3: Get count from boss team adjuster method
        try:
            boss_pokemon, _ = get_trainer_pokemon(rom, trainer_id)
            boss_count = len(boss_pokemon)
        except:
            boss_count = 0
        
        # Check for mismatches
        if authoritative_count != parser_count or authoritative_count != boss_count:
            mismatches.append((trainer_id, authoritative_count, parser_count, boss_count))
            print(f"[MISMATCH] Trainer {trainer_id:3d}: poke_count={authoritative_count}, parser={parser_count}, boss_method={boss_count}")
        else:
            if authoritative_count > 0:  # Only show trainers with Pokémon
                print(f"[OK] Trainer {trainer_id:3d}: All methods agree on {authoritative_count} Pokemon")
    
    print(f"\n{'='*60}")
    if mismatches:
        print(f"[ERROR] Found {len(mismatches)} mismatches!")
        print("These trainers need further investigation:")
        for trainer_id, auth, parser, boss in mismatches:
            print(f"  Trainer {trainer_id}: poke_count={auth}, parser={parser}, boss_method={boss}")
    else:
        print("[SUCCESS] All tested trainers show consistent Pokemon counts!")
        print("The trainer randomizer should now work correctly with boss team adjustments.")
    
    return len(mismatches) == 0


def test_specific_trainers(rom_path, trainer_ids):
    """
    Test specific trainers that were problematic before.
    
    Args:
        rom_path: Path to the ROM file
        trainer_ids: List of trainer IDs to test
    """
    print(f"Opening ROM: {rom_path}")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    print("Reading trainer data...")
    trainers, _ = read_trainer_data(rom)
    
    print(f"\nTesting specific problematic trainers: {trainer_ids}\n")
    
    for trainer_id in trainer_ids:
        if trainer_id < len(trainers):
            trainer = trainers[trainer_id][1]
            
            # Get authoritative count
            authoritative_count = get_trainer_poke_count_from_rom(rom, trainer_id)
            
            # Get parser count
            parser_count = trainer.nummons
            
            # Get boss method count
            try:
                boss_pokemon, has_moves = get_trainer_pokemon(rom, trainer_id)
                boss_count = len(boss_pokemon)
                moves_info = "with moves" if has_moves else "without moves"
            except Exception as e:
                boss_count = 0
                moves_info = f"ERROR: {e}"
            
            print(f"Trainer {trainer_id}:")
            print(f"  Authoritative poke_count: {authoritative_count}")
            print(f"  Parser count: {parser_count}")
            print(f"  Boss method count: {boss_count} ({moves_info})")
            
            if authoritative_count == parser_count == boss_count:
                print(f"  [OK] All methods agree!")
            else:
                print(f"  [MISMATCH] Detected inconsistency!")
            print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_poke_count_fix.py <rom_file> [trainer_ids...]")
        print("Example: python test_poke_count_fix.py rom.nds")
        print("Example: python test_poke_count_fix.py rom.nds 400 500")
        sys.exit(1)
    
    rom_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        # Test specific trainers
        trainer_ids = [int(tid) for tid in sys.argv[2:]]
        test_specific_trainers(rom_path, trainer_ids)
    else:
        # Test general consistency
        success = compare_poke_counts(rom_path)
        sys.exit(0 if success else 1)
