#!/usr/bin/env python3
"""
Randomization Pipeline Wrapper
Coordinates multiple randomization scripts with shared temporary data.
"""

import os
import sys
import argparse
import subprocess
from randomize_trainers import load_temp_data, cleanup_temp_data

def run_script(script_name, args, description):
    """Run a script with given arguments and handle errors"""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")
    
    cmd = [sys.executable, script_name] + args
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def randomization_pipeline(rom_path, **options):
    """
    Complete randomization pipeline that coordinates all scripts
    
    Args:
        rom_path (str): Path to the ROM file
        **options: Various randomization options
    """
    print(f"Starting randomization pipeline for: {rom_path}")
    
    # Validate ROM exists
    if not os.path.exists(rom_path):
        print(f"Error: ROM file {rom_path} not found")
        return False
    
    success = True
    current_rom = rom_path
    
    # Step 1: Randomize trainers first
    trainer_args = [current_rom]
    if options.get('bst_mode'):
        trainer_args.extend(['--bst-mode', options['bst_mode']])
    if options.get('type_themed_gyms'):
        trainer_args.append('--type-themed-gyms')
    if options.get('blacklist'):
        trainer_args.append('--blacklist')
    if options.get('splash'):
        trainer_args.append('--splash')
    if options.get('log'):
        trainer_args.append('--log')
    if options.get('seed'):
        trainer_args.extend(['--seed', str(options['seed'])])
    
    if not run_script('randomize_trainers.py', trainer_args, 
                     "Randomizing trainer Pokémon"):
        return False
    
    # Update current ROM path to the output from trainer randomizer
    current_rom = current_rom.replace('.nds', '_random')
    if options.get('type_themed_gyms'):
        current_rom += '_typegyms'
    if options.get('blacklist'):
        current_rom += '_blacklist'
    if options.get('bst_mode') == 'random':
        current_rom += '_truerandom'
    if options.get('splash'):
        current_rom += '_splash'
    current_rom += '.nds'
    
    # Step 2: Apply special Pokémon to boss teams after randomization
    if options.get('adjust_boss_teams'):
        boss_args = [current_rom]
        
        # Add the correct special Pokémon options
        if options.get('mimics'):
            boss_args.append('--mimics')
        if options.get('pivots'):
            boss_args.append('--pivots')
        if options.get('fulcrums'):
            boss_args.append('--fulcrums')
        if not (options.get('mimics') or options.get('pivots') or options.get('fulcrums')):
            # If no specific options, use --all to enable everything
            boss_args.append('--all')
            
        if options.get('log'):
            # For boss_team_adjuster.py, --log requires a filename
            log_filename = os.path.splitext(current_rom)[0] + '_boss_log.txt'
            boss_args.extend(['--log', log_filename])
        
        if not run_script('boss_team_adjuster.py', boss_args,
                         "Adjusting boss teams with special Pokémon"):
            return False
        
        # Find the output ROM with special Pokémon
        # It will typically be input filename + _mimics_pivots_fulcrums.nds or similar
        base_name = os.path.splitext(current_rom)[0]
        possible_suffixes = ['_mimics_pivots_fulcrums.nds', '_mimics.nds', '_pivots.nds', 
                           '_fulcrums.nds', '_all.nds']
        found = False
        for suffix in possible_suffixes:
            possible_file = base_name + suffix
            if os.path.exists(possible_file):
                current_rom = possible_file
                found = True
                break
                
        if not found:
            print("Warning: Could not find boss team adjuster output file, using original filename")
    
    # Note: Special Pokémon handling is now done by the boss team adjuster in Step 2
    
    # Step 4: Clean up temporary data
    print(f"\n{'='*60}")
    print("CLEANUP: Removing temporary data files")
    print(f"{'='*60}")
    cleanup_temp_data(rom_path)
    print("Temporary data cleaned up")
    
    # Final status
    print(f"\n{'='*60}")
    if success:
        print(f"[SUCCESS] PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"Final ROM: {current_rom}")
    else:
        print(f"[ERROR] PIPELINE COMPLETED WITH ERRORS")
        print(f"Partial ROM: {current_rom}")
    print(f"{'='*60}")
    
    return success

def main():
    """Main function for running the pipeline from command line"""
    parser = argparse.ArgumentParser(description="Complete Pokémon randomization pipeline.")
    parser.add_argument("rom_path", help="Path to the ROM file")
    parser.add_argument("--log", action="store_true", help="Enable logging for all scripts")
    parser.add_argument("--seed", type=int, help="Random seed for consistent results")
    
    # Trainer randomization options
    trainer_group = parser.add_argument_group("Trainer Randomization")
    trainer_group.add_argument("--bst-mode", choices=["bst", "random"], default="bst",
                              help="BST randomization mode")
    trainer_group.add_argument("--type-themed-gyms", action="store_true",
                              help="Enable type-themed gyms")
    trainer_group.add_argument("--blacklist", action="store_true",
                              help="Use Pokémon blacklist")
    trainer_group.add_argument("--splash", action="store_true",
                              help="Replace all moves with Splash")
    
    # Boss team options
    boss_group = parser.add_argument_group("Boss Team Adjustments")
    boss_group.add_argument("--adjust-boss-teams", action="store_true",
                           help="Adjust boss team sizes")
    boss_group.add_argument("--boss-team-size", type=int, default=6,
                           help="Target team size for bosses")
    
    # Special Pokémon options
    special_group = parser.add_argument_group("Special Pokémon")
    special_group.add_argument("--special-pokemon", action="store_true",
                              help="Enable special Pokémon features")
    special_group.add_argument("--pivots", action="store_true",
                              help="Add pivot Pokémon")
    special_group.add_argument("--fulcrums", action="store_true",
                              help="Add fulcrum Pokémon")
    special_group.add_argument("--mimics", action="store_true",
                              help="Add mimic Pokémon")
    
    args = parser.parse_args()
    
    # Convert args to options dict
    options = {
        'bst_mode': args.bst_mode,
        'type_themed_gyms': args.type_themed_gyms,
        'blacklist': args.blacklist,
        'splash': args.splash,
        'log': args.log,
        'seed': args.seed,
        'adjust_boss_teams': args.adjust_boss_teams or (args.boss_team_size and args.boss_team_size != 6),
        'boss_team_size': args.boss_team_size,
        'special_pokemon': args.special_pokemon or args.pivots or args.fulcrums or args.mimics,
        'pivots': args.pivots,
        'fulcrums': args.fulcrums,
        'mimics': args.mimics
    }
    
    success = randomization_pipeline(args.rom_path, **options)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
