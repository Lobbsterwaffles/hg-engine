#!/usr/bin/env python3
"""
Special Pokémon Handler v2 for Pokémon HGSS
-------------------------------------------
This script adds special Pokémon (Fulcrums, Pivots, Mimics) to boss trainers.
It integrates with the randomization pipeline to use dynamic type assignments.

Features:
- Reads boss trainers from boss_team_adjuster.py definitions
- Uses dynamic gym type assignments from randomization pipeline
- Implements Mimics, Pivots, and Fulcrums with BST matching
- Preserves trainer's "Ace" (highest level Pokémon)

Usage:
  python special_pokemon_handler_v2.py [rom_file] [options]
"""

import ndspy.rom
import ndspy.narc
import os
import sys
import random
import argparse
import json
import statistics
from construct import Container, Struct, Int8ul, Int16ul
from gym_type_data import load_gym_type_data  # Import our new utility

# Import boss trainer definitions and data structures
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from boss_team_adjuster import (
    BOSS_TRAINERS, trainer_pokemon_struct, trainer_pokemon_moves_struct,
    stats_struct, TRAINER_POKEMON_NARC_PATH, TRAINER_DATA_NARC_PATH,
    POKEMON_STATS_NARC_PATH, STAT_NAMES
)

# Import Pokemon data utilities
from pokemon_shared import read_mondata, read_pokemon_names

class SpecialPokemonHandler:
    """Handler for special Pokémon (Mimics, Pivots, Fulcrums)"""
    
    def __init__(self, rom_path, base_path="."):
        """Initialize the handler with ROM and data paths"""
        self.rom_path = rom_path
        self.base_path = base_path
        self.data_path = os.path.join(base_path, "data")
        
        # Load special Pokémon data
        self.mimics = self.load_mimics_data()
        self.pivots = self.load_pivots_data()
        self.fulcrums = self.load_fulcrums_data()
        
        # Load temp data for dynamic gym types
        self.gym_assignments = self.load_temp_data()
        
        # Cache for Pokémon stats and mondata
        self.pokemon_stats = {}
        self.mondata = None
    
    def load_temp_data(self):
        """Load gym type assignments using the gym_type_data utility"""
        # Use our dedicated gym_type_data utility to load the gym types
        gym_types = load_gym_type_data(self.rom_path)
        
        if gym_types:
            print(f"Successfully loaded gym type assignments for {len(gym_types)} trainers")
            
            # Print a sample of the loaded gym types for debugging
            sample_size = min(3, len(gym_types))
            if sample_size > 0:
                print("Sample of loaded gym types:")
                for i, (trainer_id, data) in enumerate(list(gym_types.items())[:sample_size]):
                    trainer_name = data.get("trainer_name", "Unknown")
                    assigned_type = data.get("assigned_type", "Unknown")
                    print(f"  Trainer {trainer_id} ({trainer_name}): {assigned_type}")
        else:
            print("Warning: No gym type assignments found, using default boss types")
            
        return gym_types
    
    def load_mimics_data(self):
        """Load type mimic Pokémon from data file"""
        mimics = {}
        current_type = None
        
        try:
            with open(os.path.join(self.data_path, "type_mimics_with_prevos.txt"), 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        current_type = line[1:-1].lower()
                        mimics[current_type] = []
                    elif current_type and line.startswith('SPECIES_'):
                        # Convert SPECIES_NAME to species ID (this will need mapping)
                        species_name = line.replace('SPECIES_', '').lower()
                        mimics[current_type].append(species_name)
        
        except FileNotFoundError:
            print("Warning: type_mimics_with_prevos.txt not found")
            return {}
        
        return mimics
    
    def load_pivots_data(self):
        """Load pivot Pokémon from data file"""
        pivots = {}
        current_type = None
        
        try:
            with open(os.path.join(self.data_path, "pivot_analysis.txt"), 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('[TYPE_'):
                        current_type = line[6:-1].lower()  # Remove [TYPE_ and ]
                        pivots[current_type] = []
                    elif current_type and line.startswith('SPECIES_'):
                        species_name = line.replace('SPECIES_', '').lower()
                        pivots[current_type].append(species_name)
        
        except FileNotFoundError:
            print("Warning: pivot_analysis.txt not found")
            return {}
        
        return pivots
    
    def load_fulcrums_data(self):
        """Load fulcrum Pokémon from data file"""
        fulcrums = {}
        current_type = None
        
        try:
            with open(os.path.join(self.data_path, "fulcrumsmonlist.txt"), 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        current_type = line[1:-1].lower()
                        fulcrums[current_type] = []
                    elif current_type and line.startswith('SPECIES_'):
                        species_name = line.replace('SPECIES_', '').lower()
                        fulcrums[current_type].append(species_name)
        
        except FileNotFoundError:
            print("Warning: fulcrumsmonlist.txt not found")
            return {}
        
        return fulcrums
    
    def read_pokemon_stats(self, rom):
        """Read Pokémon stats from ROM"""
        if self.pokemon_stats:  # Return cached stats
            return self.pokemon_stats
            
        try:
            pokemon_narc_data = ndspy.narc.NARC(rom.files[rom.filenames.idOf(POKEMON_STATS_NARC_PATH)])
            
            for species_id, file_data in enumerate(pokemon_narc_data.files):
                if len(file_data) < 28:
                    continue
                    
                stats_offset = 0x14
                stats_data = file_data[stats_offset:stats_offset + 6]
                
                try:
                    stats = stats_struct.parse(stats_data)
                    self.pokemon_stats[species_id] = stats
                except Exception:
                    continue
            
            return self.pokemon_stats
        except Exception as e:
            print(f"Error reading Pokémon stats: {e}")
            return {}
    
    def calculate_bst(self, stats):
        """Calculate Base Stat Total"""
        return sum(getattr(stats, stat) for stat in STAT_NAMES)
    
    def get_bst_for_species(self, species_id):
        """Get BST for a specific species"""
        if species_id in self.pokemon_stats:
            return self.calculate_bst(self.pokemon_stats[species_id])
        return 300  # Default BST
    
    def get_trainer_pokemon(self, rom, trainer_id):
        """Get a trainer's Pokémon list"""
        try:
            trainer_narc_data = ndspy.narc.NARC(rom.files[rom.filenames.idOf(TRAINER_POKEMON_NARC_PATH)])
            pokemon_data = trainer_narc_data.files[trainer_id]
            
            if not pokemon_data:
                return [], False
            
            # Check if this trainer has moves (18 bytes per Pokémon vs 8 bytes)
            has_moves = (len(pokemon_data) % 18) == 0 and len(pokemon_data) > 0
            
            pokemon_list = []
            if has_moves:
                # Parse with moves structure
                bytes_per_pokemon = 18
                struct_to_use = trainer_pokemon_moves_struct
            else:
                # Parse without moves structure
                bytes_per_pokemon = 8
                struct_to_use = trainer_pokemon_struct
            
            num_pokemon = len(pokemon_data) // bytes_per_pokemon
            
            for i in range(num_pokemon):
                offset = i * bytes_per_pokemon
                pokemon_bytes = pokemon_data[offset:offset + bytes_per_pokemon]
                pokemon = struct_to_use.parse(pokemon_bytes)
                pokemon_list.append(pokemon)
            
            return pokemon_list, has_moves
            
        except Exception as e:
            print(f"Error reading trainer {trainer_id}: {e}")
            return [], False
    
    def save_trainer_pokemon(self, rom, trainer_id, pokemon_list, has_moves):
        """Save trainer's Pokémon back to ROM"""
        try:
            trainer_narc_data = ndspy.narc.NARC(rom.files[rom.filenames.idOf(TRAINER_POKEMON_NARC_PATH)])
            
            if has_moves:
                struct_to_use = trainer_pokemon_moves_struct
            else:
                struct_to_use = trainer_pokemon_struct
            
            # Build the new data
            new_data = b''
            for pokemon in pokemon_list:
                new_data += struct_to_use.build(pokemon)
            
            trainer_narc_data.files[trainer_id] = new_data
            
            # Save back to ROM
            rom.files[rom.filenames.idOf(TRAINER_POKEMON_NARC_PATH)] = trainer_narc_data.save()
            
        except Exception as e:
            print(f"Error saving trainer {trainer_id}: {e}")
    
    def find_ace_pokemon(self, pokemon_list):
        """Find the trainer's ace (highest level Pokémon)"""
        if not pokemon_list:
            return None
        
        ace = max(pokemon_list, key=lambda p: p.level)
        return pokemon_list.index(ace)
    
    def find_replacement_by_bst(self, target_bst, special_list):
        """Find a suitable special Pokémon replacement within BST range"""
        if not special_list or not self.mondata:
            return None
        
        min_bst = int(target_bst * 0.9)
        max_bst = int(target_bst * 1.1)
        
        candidates = []
        
        # Convert species names to IDs and check BST
        for species_name in special_list:
            species_id = self.name_to_species_id(species_name)
            if species_id is not None:
                species_bst = self.get_bst_for_species(species_id)
                if min_bst <= species_bst <= max_bst:
                    candidates.append(species_id)
        
        if candidates:
            return random.choice(candidates)
        
        # If no perfect BST matches, try any from the list
        for species_name in special_list:
            species_id = self.name_to_species_id(species_name)
            if species_id is not None:
                return species_id
        
        return None
    
    def load_mondata(self, rom):
        """Load Pokemon data for species name mapping"""
        if self.mondata is None:
            # Load Pokemon names first
            names = read_pokemon_names(self.base_path)
            self.mondata = read_mondata(rom, names)
        return self.mondata
    
    def name_to_species_id(self, species_name):
        """Convert species name to species ID using mondata"""
        if not self.mondata:
            print(f"Warning: mondata not loaded for species lookup: {species_name}")
            return None
            
        # Remove SPECIES_ prefix if present
        clean_name = species_name.replace('SPECIES_', '').upper()
        
        # Search through mondata for matching species
        for species_id, mon in enumerate(self.mondata):
            if not mon:
                continue
                
            # Check various name fields
            name = mon.get('name', '')
            if not name and 'species_name' in mon:
                name = mon['species_name']
                
            if name and name.upper() == clean_name:
                return species_id
                
        print(f"Warning: Could not find species ID for {species_name}")
        return None
    
    def apply_special_pokemon(self, rom, trainer_id, use_mimics=False, use_pivots=False, use_fulcrums=False):
        """Apply special Pokémon to a boss trainer"""
        # Get trainer info
        if trainer_id not in BOSS_TRAINERS:
            trainer_name = self.gym_assignments.get(str(trainer_id), {}).get('trainer_name', f'Trainer {trainer_id}')
        else:
            trainer_name, _ = BOSS_TRAINERS[trainer_id]
        
        # Get dynamic type assignment
        if str(trainer_id) in self.gym_assignments:
            assigned_type = self.gym_assignments[str(trainer_id)]['assigned_type'].lower()
        elif trainer_id in BOSS_TRAINERS:
            _, assigned_type = BOSS_TRAINERS[trainer_id]
            assigned_type = assigned_type.lower()
        else:
            print(f"Warning: No type info for trainer {trainer_id}")
            return False
        
        # Get trainer's Pokémon
        pokemon_list, has_moves = self.get_trainer_pokemon(rom, trainer_id)
        if not pokemon_list:
            print(f"Warning: No Pokémon found for trainer {trainer_id}")
            return False
        
        print(f"\nProcessing {trainer_name} (ID {trainer_id}) - {assigned_type.title()} type")
        print(f"Current team size: {len(pokemon_list)}")
        
        # Find the ace (never replace this)
        ace_index = self.find_ace_pokemon(pokemon_list)
        excluded_indices = {ace_index} if ace_index is not None else set()
        
        modifications_made = False
        
        # Apply Mimics (if trainer has ≥ 4 Pokémon)
        if use_mimics and len(pokemon_list) >= 4:
            if assigned_type in self.mimics and self.mimics[assigned_type]:
                # Find a non-ace Pokémon to replace
                candidates = [i for i in range(len(pokemon_list)) if i not in excluded_indices]
                if candidates:
                    target_index = random.choice(candidates)
                    target_bst = self.get_bst_for_species(pokemon_list[target_index].species)
                    
                    # Find suitable mimic
                    mimic_id = self.find_replacement_by_bst(target_bst, self.mimics[assigned_type])
                    if mimic_id:
                        pokemon_list[target_index].species = mimic_id
                        excluded_indices.add(target_index)
                        modifications_made = True
                        print(f"  Added {assigned_type} mimic at position {target_index + 1}")
        
        # Apply Pivots (if trainer has 6 Pokémon)
        if use_pivots and len(pokemon_list) == 6:
            if assigned_type in self.pivots and self.pivots[assigned_type]:
                candidates = [i for i in range(len(pokemon_list)) if i not in excluded_indices]
                if candidates:
                    target_index = random.choice(candidates)
                    target_bst = self.get_bst_for_species(pokemon_list[target_index].species)
                    
                    pivot_id = self.find_replacement_by_bst(target_bst, self.pivots[assigned_type])
                    if pivot_id:
                        pokemon_list[target_index].species = pivot_id
                        excluded_indices.add(target_index)
                        modifications_made = True
                        print(f"  Added {assigned_type} pivot at position {target_index + 1}")
        
        # Apply Fulcrums (if trainer has 6 Pokémon)
        if use_fulcrums and len(pokemon_list) == 6:
            if assigned_type in self.fulcrums and self.fulcrums[assigned_type]:
                candidates = [i for i in range(len(pokemon_list)) if i not in excluded_indices]
                if candidates:
                    target_index = random.choice(candidates)
                    target_bst = self.get_bst_for_species(pokemon_list[target_index].species)
                    
                    fulcrum_id = self.find_replacement_by_bst(target_bst, self.fulcrums[assigned_type])
                    if fulcrum_id:
                        pokemon_list[target_index].species = fulcrum_id
                        excluded_indices.add(target_index)
                        modifications_made = True
                        print(f"  Added {assigned_type} fulcrum at position {target_index + 1}")
        
        # Save changes if any were made
        if modifications_made:
            self.save_trainer_pokemon(rom, trainer_id, pokemon_list, has_moves)
            return True
        
        return False
    
    def process_all_bosses(self, rom, use_mimics=False, use_pivots=False, use_fulcrums=False):
        """Process all boss trainers for special Pokémon"""
        print("Loading Pokémon stats and data...")
        self.read_pokemon_stats(rom)
        self.load_mondata(rom)
        
        print(f"\nProcessing boss trainers with special Pokémon:")
        print(f"  Mimics: {'Enabled' if use_mimics else 'Disabled'}")
        print(f"  Pivots: {'Enabled' if use_pivots else 'Disabled'}")
        print(f"  Fulcrums: {'Enabled' if use_fulcrums else 'Disabled'}")
        
        modified_count = 0
        
        # Get all boss trainer IDs (from BOSS_TRAINERS + dynamic assignments)
        all_boss_ids = set(BOSS_TRAINERS.keys())
        all_boss_ids.update(int(tid) for tid in self.gym_assignments.keys())
        
        for trainer_id in sorted(all_boss_ids):
            if self.apply_special_pokemon(rom, trainer_id, use_mimics, use_pivots, use_fulcrums):
                modified_count += 1
        
        print(f"\nModified {modified_count} boss trainers with special Pokémon")
        return modified_count

def main():
    """Main function for running the script directly"""
    parser = argparse.ArgumentParser(description="Add special Pokémon (Mimics, Pivots, Fulcrums) to boss trainers")
    parser.add_argument("rom_file", help="Path to the ROM file")
    parser.add_argument("--output", "-o", help="Output ROM path (default: original_special.nds)")
    parser.add_argument("--mimics", action="store_true", help="Add mimic Pokémon to bosses with ≥4 Pokémon")
    parser.add_argument("--pivots", action="store_true", help="Add pivot Pokémon to bosses with 6 Pokémon")
    parser.add_argument("--fulcrums", action="store_true", help="Add fulcrum Pokémon to bosses with 6 Pokémon")
    parser.add_argument("--log", action="store_true", help="Enable detailed logging")
    
    args = parser.parse_args()
    
    # Validate that at least one option is selected
    if not (args.mimics or args.pivots or args.fulcrums):
        print("Error: At least one special Pokémon type must be selected (--mimics, --pivots, or --fulcrums)")
        return 1
    
    # Open ROM
    print(f"Opening ROM file: {args.rom_file}")
    try:
        rom = ndspy.rom.NintendoDSRom.fromFile(args.rom_file)
    except Exception as e:
        print(f"Error opening ROM: {e}")
        return 1
    
    # Initialize handler
    handler = SpecialPokemonHandler(args.rom_file)
    
    # Process bosses
    try:
        modified_count = handler.process_all_bosses(rom, args.mimics, args.pivots, args.fulcrums)
    except Exception as e:
        print(f"Error processing bosses: {e}")
        return 1
    
    # Generate output filename
    if args.output:
        output_path = args.output
    else:
        base_name = os.path.splitext(args.rom_file)[0]
        suffixes = []
        if args.mimics:
            suffixes.append("mimics")
        if args.pivots:
            suffixes.append("pivots")
        if args.fulcrums:
            suffixes.append("fulcrums")
        output_path = f"{base_name}_{'_'.join(suffixes)}.nds"
    
    # Save ROM
    print(f"Saving ROM to: {output_path}")
    try:
        rom.saveToFile(output_path)
        print(f"[SUCCESS] Successfully saved ROM with {modified_count} modified trainers")
    except Exception as e:
        print(f"Error saving ROM: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
