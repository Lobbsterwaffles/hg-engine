#!/usr/bin/env python3

"""
HGSS Game Randomizer Wrapper

This script runs both the boss team adjuster and trainer randomizer in sequence.
It simplifies the process of creating a fully randomized ROM.
"""

import os
import sys
import argparse
import random
import subprocess

def parse_args():
    """
    Parse command line arguments for the randomizer wrapper.
    """
    parser = argparse.ArgumentParser(description="HGSS Game Randomizer - Run both boss adjuster and trainer randomizer")
    
    # Input ROM argument
    parser.add_argument("input_rom", help="Path to the input ROM file")
    
    # Core randomization options
    parser.add_argument("--bst-mode", choices=["bst", "random"], default="bst", 
                        help="BST mode selects Pokemon with similar stats. Random mode is completely random.")
    parser.add_argument("--type-themed-gyms", action="store_true", 
                        help="Make gym trainers use Pokemon of the same type as the leader")
    parser.add_argument("--seed", type=int, 
                        help="Seed for random number generator. If not provided, a random seed will be used.")
    
    # Special Pokemon options
    parser.add_argument("--pivots", action="store_true", 
                        help="Add pivot Pokemon to gym teams (defensive Pokemon that cover gym weaknesses)")
    parser.add_argument("--fulcrums", action="store_true", 
                        help="Add fulcrum Pokemon to gym teams (offensive Pokemon that counter gym weaknesses)")
    parser.add_argument("--mimics", action="store_true", 
                        help="Add mimic Pokemon to gym teams (thematically fitting Pokemon not of the gym's type)")
    
    # Boss team adjuster options
    parser.add_argument("--scaling", action="store_true", 
                        help="Scale boss teams: early gym leaders have 4 Pokemon, others have 6")
    
    # Other options
    parser.add_argument("--log", action="store_true", 
                        help="Enable logging of Pokemon changes")
    
    return parser.parse_args()

def main():
    """
    Main function to run boss team adjuster and trainer randomizer in sequence.
    """
    args = parse_args()
    
    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)
    else:
        # Generate a random seed and print it for reproducibility
        seed = random.randint(0, 2**32 - 1)
        print(f"Using random seed: {seed}")
        random.seed(seed)
    
    # Check if input ROM exists
    if not os.path.exists(args.input_rom):
        print(f"Error: Input ROM '{args.input_rom}' not found.")
        return 1
    
    # Step 1: Run boss team adjuster if scaling is enabled
    intermediate_rom = args.input_rom
    if args.scaling:
        print("Running boss team adjuster with scaling...")
        
        # Determine output filename for boss adjuster
        output_rom = os.path.splitext(args.input_rom)[0] + "_bossesScaled.nds"
        
        # Build command for boss team adjuster
        boss_cmd = [
            sys.executable,
            "boss_team_adjuster.py",
            args.input_rom,
            "--scaling"
        ]
        
        # Run boss team adjuster
        try:
            subprocess.run(boss_cmd, check=True)
            intermediate_rom = output_rom
            print(f"Boss team adjuster completed successfully. Output: {intermediate_rom}")
        except subprocess.CalledProcessError as e:
            print(f"Error running boss team adjuster: {e}")
            return 1
    
    # Step 2: Run trainer randomizer with all specified options
    print("Running trainer randomizer...")
    
    # Build command for trainer randomizer
    randomizer_cmd = [
        sys.executable,
        "randomize_trainers.py",
        intermediate_rom,
        f"--bst-mode", args.bst_mode
    ]
    
    # Add optional arguments
    if args.type_themed_gyms:
        randomizer_cmd.append("--type-themed-gyms")
    if args.pivots:
        randomizer_cmd.append("--pivots")
    if args.fulcrums:
        randomizer_cmd.append("--fulcrums")
    if args.mimics:
        randomizer_cmd.append("--mimics")
    if args.log:
        randomizer_cmd.append("--log")
    if args.seed:
        randomizer_cmd.extend(["--seed", str(args.seed)])
    
    # Run trainer randomizer
    try:
        subprocess.run(randomizer_cmd, check=True)
        print("Trainer randomizer completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error running trainer randomizer: {e}")
        return 1
    
    print("\nRandomization complete! Your game has been successfully randomized.")
    print("Enjoy your adventure with new Pokemon teams!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
