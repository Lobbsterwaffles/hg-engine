#!/usr/bin/env python3
"""
Pokémon HGSS Trainer Randomizer with Boss Team Size Adjuster
-----------------------------------------------------------
This script combines the trainer randomizer and boss team size adjuster
by running both in sequence.

Features:
- Randomizes all trainer Pokémon (optional)
- Sets all boss trainers to have full teams of 6 Pokémon
- Fixes any team size inconsistencies

Usage:
  python run_randomizer_with_bosses.py [rom_file] [options]
"""

import os
import sys
import argparse
import subprocess

def main():
    """
    Main entry point for the combined randomizer
    """
    parser = argparse.ArgumentParser(description="Pokémon HGSS Trainer Randomizer with Boss Team Size Adjuster")
    parser.add_argument("rom", help="Path to the ROM file")
    parser.add_argument("--output", "-o", help="Output ROM path (default: original_random_bosses6.nds)")
    parser.add_argument("--no-randomize", action="store_true", help="Don't randomize trainer Pokémon")
    parser.add_argument("--team-size", type=int, default=6, help="Target team size for boss trainers (1-6)")
    parser.add_argument("--boss-only", action="store_true", help="Only adjust boss teams, no randomization")
    
    args = parser.parse_args()
    
    # Validate args
    if not os.path.isfile(args.rom):
        print(f"Error: ROM file '{args.rom}' not found")
        return 1
        
    if args.team_size < 1 or args.team_size > 6:
        print("Error: Team size must be between 1 and 6")
        return 1
    
    # Determine intermediate and output paths
    base_name = os.path.splitext(args.rom)[0]
    
    if args.boss_only or args.no_randomize:
        # Only run boss team adjuster
        boss_output = args.output or f"{base_name}_bosses{args.team_size}.nds"
        
        print(f"Setting boss trainers to have {args.team_size} Pokémon teams...")
        
        # Run boss team adjuster
        boss_cmd = ["python", "boss_team_adjuster.py", args.rom, "--team-size", str(args.team_size), "--output", boss_output]
        subprocess.run(boss_cmd, check=True)
        
        print(f"Done! Output saved to {boss_output}")
    
    else:
        # Run both randomizer and boss adjuster
        intermediate_output = f"{base_name}_random.nds"
        final_output = args.output or f"{base_name}_random_bosses{args.team_size}.nds"
        
        # Step 1: Run randomizer
        print("Step 1: Randomizing trainer Pokémon...")
        rand_cmd = ["python", "randomize_trainers.py", args.rom, "-o", intermediate_output]
        subprocess.run(rand_cmd, check=True)
        
        # Step 2: Run boss team adjuster
        print(f"Step 2: Setting boss trainers to have {args.team_size} Pokémon teams...")
        boss_cmd = ["python", "boss_team_adjuster.py", intermediate_output, "--team-size", str(args.team_size), "--output", final_output]
        subprocess.run(boss_cmd, check=True)
        
        # Clean up intermediate file
        if os.path.exists(intermediate_output):
            os.remove(intermediate_output)
            print(f"Removed intermediate file: {intermediate_output}")
        
        print(f"Done! Final output saved to {final_output}")
    
    # Run the analyzer to verify the changes
    print("\nVerifying boss team sizes...")
    analyze_cmd = ["python", "analyze_trainer_teams.py", args.output or f"{base_name}_bosses{args.team_size}.nds" if args.boss_only or args.no_randomize else final_output]
    subprocess.run(analyze_cmd, check=True)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
