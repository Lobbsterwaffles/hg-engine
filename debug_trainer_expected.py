#!/usr/bin/env python3
"""
Debug the expected Pokémon count parsing from trainers.s
"""

import sys

def debug_expected_counts():
    """Debug the expected counts for specific trainers"""
    
    # Load the trainers.s file to get the expected number of Pokémon for each trainer
    trainer_pokemon_counts = {}
    try:
        with open("armips/data/trainers/trainers.s", "r", encoding="utf-8") as f:
            current_trainer = None
            for line_num, line in enumerate(f, 1):
                # Look for trainerdata lines to get trainer ID
                if "trainerdata" in line and "," in line:
                    try:
                        trainer_id = int(line.split("trainerdata")[1].split(",")[0].strip())
                        current_trainer = trainer_id
                        print(f"Line {line_num}: Found trainer {trainer_id}: {line.strip()}")
                    except Exception as e:
                        print(f"Line {line_num}: Error parsing trainerdata: {e} - {line.strip()}")
                # Look for nummons to get the number of Pokémon
                elif current_trainer is not None and "nummons" in line:
                    try:
                        num = int(line.split("nummons")[1].strip())
                        trainer_pokemon_counts[current_trainer] = num
                        print(f"Line {line_num}: Trainer {current_trainer} has {num} Pokemon: {line.strip()}")
                        if current_trainer in [20, 21, 30, 112, 400, 500]:
                            print(f"  *** KEY TRAINER {current_trainer}: Expected {num} Pokemon ***")
                    except Exception as e:
                        print(f"Line {line_num}: Error parsing nummons: {e} - {line.strip()}")
                        
        print(f"\nTotal trainers with expected counts: {len(trainer_pokemon_counts)}")
        
        # Check specific trainers
        test_trainers = [20, 21, 30, 112, 400, 500]
        print(f"\n=== EXPECTED COUNTS FOR TEST TRAINERS ===")
        for tid in test_trainers:
            expected = trainer_pokemon_counts.get(tid, "NOT FOUND")
            print(f"Trainer {tid}: {expected}")
            
    except Exception as e:
        print(f"Error loading trainer.s file: {e}")

if __name__ == "__main__":
    debug_expected_counts()
