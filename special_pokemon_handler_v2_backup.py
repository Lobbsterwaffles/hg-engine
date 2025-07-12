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
import datetime  # Added datetime module for log file timestamps
from datetime import datetime
from construct import Container, Struct, Int8ul, Int16ul

# Import boss trainer definitions and data structures
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from boss_team_adjuster import (
    BOSS_TRAINERS, trainer_pokemon_struct, trainer_pokemon_moves_struct,
    TRAINER_POKEMON_NARC_PATH, TRAINER_DATA_NARC_PATH
)

from pokemon_shared import mondata_struct

# Pokemon stats NARC file path
POKEMON_STATS_NARC_PATH = "a/0/0/2" 

# Stat names for logging
STAT_NAMES = ["HP", "Attack", "Defense", "Speed", "Sp. Atk", "Sp. Def"]

# Import Pokemon data utilities
from pokemon_shared import read_mondata, read_pokemon_names

class SpecialPokemonHandler:
    """Handler for special Pokémon (Mimics, Pivots, Fulcrums)"""
    
    def __init__(self, rom_path, base_path=".", log_file=None):
        """Initialize the handler with ROM and data paths"""
        self.rom_path = rom_path
        self.base_path = base_path
        self.data_path = os.path.join(base_path, "data")
        
        # Setup logging
        self.log_file = log_file
        self.log_handle = None
        if log_file:
            try:
                self.log_handle = open(log_file, 'w', encoding='utf-8')
                self.log(f"Special Pokémon Handler Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.log(f"ROM: {rom_path}")
                self.log("-" * 60)
            except Exception as e:
                print(f"Warning: Could not open log file: {e}")
        
        # Load special Pokémon data
        self.mimics = self.load_mimics_data()
        self.pivots = self.load_pivots_data()
        self.fulcrums = self.load_fulcrums_data()
        
        # Load temp data for dynamic gym types
        self.gym_assignments = self.load_temp_data()
        
        # Cache for Pokémon stats and mondata
        self.pokemon_stats = {}
        self.mondata = None
        # Dictionary to store Pokémon name cache
        self.pokemon_names = {}
    
    def log(self, message):
        """Log a message to console and optionally to file"""
        # Replace any special characters that might cause problems
        safe_message = message
        
        # Replace gender symbols with (M) and (F)
        safe_message = safe_message.replace('\u2642', '(M)')
        safe_message = safe_message.replace('\u2640', '(F)')
        
        # Handle other problematic characters
        try:
            print(safe_message)
        except UnicodeEncodeError:
            # If we still have encoding issues, use a more aggressive approach
            print(safe_message.encode('ascii', 'replace').decode('ascii'))
            
        if self.log_handle:
            try:
                self.log_handle.write(f"{message}\n")
            except UnicodeEncodeError:
                # For the log file, we can preserve more characters
                self.log_handle.write(f"{safe_message}\n")
            self.log_handle.flush()  # Ensure it's written immediately
    
    def load_temp_data(self):
        """Load temporary data saved by the randomizer"""
        temp_file = self.rom_path.replace('.nds', '_temp_data.json')
        try:
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('gym_type_assignments', {})
        except (FileNotFoundError, json.JSONDecodeError):
            print("Warning: No temp data found, using default boss types")
            return {}
    
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
                
        self.log(f"Warning: Could not find species ID for {species_name}")
        return None
    
    def get_pokemon_name(self, species_id):
        """Get Pokémon name from species ID with caching"""
        if species_id in self.pokemon_names:
            return self.pokemon_names[species_id]
        
        try:
            from pokemon_names import get_pokemon_name
            # Fix the off-by-one error: Add 1 to the species_id to get the correct Pokémon name
            # This is because the game data uses 0-indexed IDs but the name lookup expects 1-indexed
            name = get_pokemon_name(species_id + 1)
            self.pokemon_names[species_id] = name
            return name
        except:
            # Fallback to just the ID if something goes wrong
            return f"Pokemon #{species_id}"

    def apply_special_pokemon(self, rom, trainer_id, use_mimics=False, use_pivots=False, use_fulcrums=False, battle_type="Unknown"):
        """Apply special Pokémon to a single boss trainer"""
        # Skip processing if the trainer doesn't have any special Pokémon to add
        if not any([use_mimics, use_pivots, use_fulcrums]):
            return False
        
        # Try to find trainer in dynamic gym assignments first
        if str(trainer_id) in self.gym_assignments:
            trainer_info = self.gym_assignments[str(trainer_id)]
            trainer_name = trainer_info.get('trainer_name', f'Trainer {trainer_id}')
            trainer_type = trainer_info.get('assigned_type')
            battle_label = "Rematch" if battle_type == "Rematch" else battle_type
        # Fall back to static boss trainer data
        elif trainer_id in BOSS_TRAINERS:
            trainer_name, trainer_type = BOSS_TRAINERS[trainer_id]
            battle_label = "Gym" if battle_type == "Gym" else battle_type
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
                
    self.log(f"Warning: Could not find species ID for {species_name}")
    return None
    
def get_pokemon_name(self, species_id):
    """Get Pokémon name from species ID with caching"""
    if species_id in self.pokemon_names:
        return self.pokemon_names[species_id]
        
    try:
        from pokemon_names import get_pokemon_name
        # Fix the off-by-one error: Add 1 to the species_id to get the correct Pokémon name
        # This is because the game data uses 0-indexed IDs but the name lookup expects 1-indexed
        name = get_pokemon_name(species_id + 1)
        self.pokemon_names[species_id] = name
        return name
    except:
        # Fallback to just the ID if something goes wrong
        return f"Pokemon #{species_id}"

def apply_special_pokemon(self, rom, trainer_id, use_mimics=False, use_pivots=False, use_fulcrums=False, battle_type="Unknown"):
    """Apply special Pokémon to a single boss trainer"""
    # Skip processing if the trainer doesn't have any special Pokémon to add
    if not any([use_mimics, use_pivots, use_fulcrums]):
        return False
        
    # Try to find trainer in dynamic gym assignments first
    if str(trainer_id) in self.gym_assignments:
        trainer_info = self.gym_assignments[str(trainer_id)]
        trainer_name = trainer_info.get('trainer_name', f'Trainer {trainer_id}')
        trainer_type = trainer_info.get('assigned_type')
        battle_label = "Rematch" if battle_type == "Rematch" else battle_type
    # Fall back to static boss trainer data
    elif trainer_id in BOSS_TRAINERS:
        trainer_name, trainer_type = BOSS_TRAINERS[trainer_id]
        battle_label = "Gym" if battle_type == "Gym" else battle_type
    else:
        # Not a recognized boss trainer
        return False
        
    self.log(f"\n==================================================\nProcessing {trainer_name} {battle_label} (ID {trainer_id}) - {trainer_type} type")
        
    # Get trainer's Pokémon
    pokemon_list, has_moves = self.get_trainer_pokemon(rom, trainer_id)
    if not pokemon_list:
        self.log(f"Warning: No Pokémon found for trainer {trainer_id}")
        return False
        
    self.log(f"\n{'=' * 50}")
    self.log(f"Processing {trainer_name} (ID {trainer_id}) - {trainer_type} type")
    self.log(f"Current team size: {len(pokemon_list)}")
        
    # Log original team for reference
    self.log("\nOriginal team:")
    for i, poke in enumerate(pokemon_list):
        species_name = self.get_pokemon_name(poke.species)
        self.log(f"  {i+1}. {species_name} (ID: {poke.species}) - Level {poke.level}")
        
    # Find the ace (never replace this)
    ace_index = self.find_ace_pokemon(pokemon_list)
    excluded_indices = {ace_index} if ace_index is not None else set()
        
    if ace_index is not None:
        ace_pokemon = pokemon_list[ace_index]
        ace_name = self.get_pokemon_name(ace_pokemon.species)
        self.log(f"\nIdentified ace Pokémon: {ace_name} (Level {ace_pokemon.level}) at position {ace_index + 1}")
        
    modifications_made = False
        
    # Apply Mimics (if trainer has ≥ 4 Pokémon)
    if use_mimics and len(pokemon_list) >= 4:
        self.log("\nAttempting to add a Mimic Pokémon...")
        if trainer_type.lower() in self.mimics and self.mimics[trainer_type.lower()]:
            # Find a non-ace Pokémon to replace
            candidates = [i for i in range(len(pokemon_list)) if i not in excluded_indices]
            if candidates:
                target_index = random.choice(candidates)
                target_species = pokemon_list[target_index].species
                target_name = self.get_pokemon_name(target_species)
                target_bst = self.get_bst_for_species(target_species)
                    
                self.log(f"  Selected {target_name} (BST: {target_bst}) at position {target_index + 1} for replacement")
                    
                # Find suitable mimic
                mimic_id = self.find_replacement_by_bst(target_bst, self.mimics[trainer_type.lower()])
                if mimic_id:
                    mimic_name = self.get_pokemon_name(mimic_id)
                    mimic_bst = self.get_bst_for_species(mimic_id)
                        
                    # Replace the Pokémon
                    pokemon_list[target_index].species = mimic_id
                    excluded_indices.add(target_index)
                    modifications_made = True
                        
                    self.log(f"  Added {mimic_name} (ID: {mimic_id}, BST: {mimic_bst}) as {trainer_type.lower()} mimic")
                    self.log(f"     Replaced: {target_name} -> {mimic_name}")
                else:
                    self.log("  Could not find a suitable mimic replacement")
            else:
                self.log("  No suitable candidates for replacement")
        else:
            self.log(f"  No mimics available for {trainer_type.lower()} type")
        
    # Apply Pivots (if trainer has 6 Pokémon)
    if use_pivots and len(pokemon_list) == 6:
        self.log("\nAttempting to add a Pivot Pokémon...")
        if trainer_type.lower() in self.pivots and self.pivots[trainer_type.lower()]:
            candidates = [i for i in range(len(pokemon_list)) if i not in excluded_indices]
            if candidates:
                target_index = random.choice(candidates)
                target_species = pokemon_list[target_index].species
                target_name = self.get_pokemon_name(target_species)
                target_bst = self.get_bst_for_species(target_species)
                    
                self.log(f"  Selected {target_name} (BST: {target_bst}) at position {target_index + 1} for replacement")
                    
                pivot_id = self.find_replacement_by_bst(target_bst, self.pivots[trainer_type.lower()])
                if pivot_id:
                    pivot_name = self.get_pokemon_name(pivot_id)
                    pivot_bst = self.get_bst_for_species(pivot_id)
                        
                    # Replace the Pokémon
                    pokemon_list[target_index].species = pivot_id
                    excluded_indices.add(target_index)
                    modifications_made = True
                        
                    self.log(f"  Added {pivot_name} (ID: {pivot_id}, BST: {pivot_bst}) as {trainer_type.lower()} pivot")
                    self.log(f"     Replaced: {target_name} -> {pivot_name}")
                else:
                    self.log("  Could not find a suitable pivot replacement")
            else:
                self.log("  No suitable candidates for replacement")
        else:
            self.log(f"  No pivots available for {trainer_type.lower()} type")
        
    # Apply Fulcrums (if trainer has 6 Pokémon)
    if use_fulcrums and len(pokemon_list) == 6:
        self.log("\nAttempting to add a Fulcrum Pokémon...")
        if trainer_type.lower() in self.fulcrums and self.fulcrums[trainer_type.lower()]:
            candidates = [i for i in range(len(pokemon_list)) if i not in excluded_indices]
            if candidates:
                target_index = random.choice(candidates)
                target_species = pokemon_list[target_index].species
                target_name = self.get_pokemon_name(target_species)
                target_bst = self.get_bst_for_species(target_species)
                    
                self.log(f"  Selected {target_name} (BST: {target_bst}) at position {target_index + 1} for replacement")
                    
                fulcrum_id = self.find_replacement_by_bst(target_bst, self.fulcrums[trainer_type.lower()])
                if fulcrum_id:
                    fulcrum_name = self.get_pokemon_name(fulcrum_id)
                    fulcrum_bst = self.get_bst_for_species(fulcrum_id)
                        
                    # Replace the Pokémon
                    pokemon_list[target_index].species = fulcrum_id
                    excluded_indices.add(target_index)
                    modifications_made = True
                        
                    self.log(f"  Added {fulcrum_name} (ID: {fulcrum_id}, BST: {fulcrum_bst}) as {trainer_type.lower()} fulcrum")
                    self.log(f"     Replaced: {target_name} -> {fulcrum_name}")
                else:
                    self.log("  Could not find a suitable fulcrum replacement")
            else:
                self.log("  No suitable candidates for replacement")
        else:
            self.log(f"  No fulcrums available for {trainer_type.lower()} type")
        
    # Log the final team composition
    if modifications_made:
        self.log("\nFinal team composition:")
        for i, poke in enumerate(pokemon_list):
            species_name = self.get_pokemon_name(poke.species)
            special_tag = ""
            if i == ace_index:
                special_tag = "(ACE)"
            self.log(f"  {i+1}. {species_name} (ID: {poke.species}) - Level {poke.level} {special_tag}")
                    
                    self.log(f"  Selected {target_name} (BST: {target_bst}) at position {target_index + 1} for replacement")
                    
                    pivot_id = self.find_replacement_by_bst(target_bst, self.pivots[trainer_type_lower]pe])
                    if pivot_id:
                        pivot_name = self.get_pokemon_name(pivot_id)
                        pivot_bst = self.get_bst_for_species(pivot_id)
                        
                        # Replace the Pokémon
                        pokemon_list[target_index].species = pivot_id
                        excluded_indices.add(target_index)
                        modifications_made = True
                        
                        self.log(f"  Added {pivot_name} (ID: {pivot_id}, BST: {pivot_bst}) as {assigned_type} pivot")
                        self.log(f"     Replaced: {target_name} -> {pivot_name}")
                    else:
                        self.log("  Could not find a suitable pivot replacement")
                else:
                    self.log("  No suitable candidates for replacement")
            else:
                self.log(f"  No pivots available for {assigned_type} type")
        
        # Apply Fulcrums (if trainer has 6 Pokémon)
        if use_fulcrums and len(pokemon_list) == 6:
            self.log("\nAttempting to add a Fulcrum Pokémon...")
            if assigned_type in self.fulcrums and self.fulcrums[assigned_type]:
                candidates = [i for i in range(len(pokemon_list)) if i not in excluded_indices]
                if candidates:
                    target_index = random.choice(candidates)
                    target_species = pokemon_list[target_index].species
                    target_name = self.get_pokemon_name(target_species)
                    target_bst = self.get_bst_for_species(target_species)
                    
                    self.log(f"  Selected {target_name} (BST: {target_bst}) at position {target_index + 1} for replacement")
                    
                    fulcrum_id = self.find_replacement_by_bst(target_bst, self.fulcrums[assigned_type])
                    if fulcrum_id:
                        fulcrum_name = self.get_pokemon_name(fulcrum_id)
                        fulcrum_bst = self.get_bst_for_species(fulcrum_id)
                        
                        # Replace the Pokémon
                        pokemon_list[target_index].species = fulcrum_id
                        excluded_indices.add(target_index)
                        modifications_made = True
                        
                        self.log(f"  Added {fulcrum_name} (ID: {fulcrum_id}, BST: {fulcrum_bst}) as {assigned_type} fulcrum")
                        self.log(f"     Replaced: {target_name} -> {fulcrum_name}")
                    else:
                        self.log("  Could not find a suitable fulcrum replacement")
                else:
                    self.log("  No suitable candidates for replacement")
            else:
                self.log(f"  No fulcrums available for {assigned_type} type")
        
        # Log the final team composition
        if modifications_made:
            self.log("\nFinal team composition:")
            for i, poke in enumerate(pokemon_list):
                species_name = self.get_pokemon_name(poke.species)
                special_tag = ""
                if i == ace_index:
                    special_tag = "(ACE)"
                self.log(f"  {i+1}. {species_name} (ID: {poke.species}) - Level {poke.level} {special_tag}")
            
            # Save changes if any were made
            self.save_trainer_pokemon(rom, trainer_id, pokemon_list, has_moves)
            self.log(f"\nSuccessfully updated {trainer_name}'s team")
            return True
        else:
            self.log("\nNo modifications were made to the team")
            return False
    
    def process_all_bosses(self, rom, use_mimics=False, use_pivots=False, use_fulcrums=False):
        """Process all boss trainers for special Pokémon"""
        self.log("Loading Pokémon stats and data...")
        
        # Read Pokémon stats and move data from ROM (critical step!)
        self.read_pokemon_stats(rom)
        self.load_mondata(rom)
        
        self.log(f"\nProcessing boss trainers with special Pokémon:")
        self.log(f"  Mimics: {'Enabled' if use_mimics else 'Disabled'}")
        self.log(f"  Pivots: {'Enabled' if use_pivots else 'Disabled'}")
        self.log(f"  Fulcrums: {'Enabled' if use_fulcrums else 'Disabled'}")
        
        modified_count = 0
        
        # Create a mapping of trainer ID to battle type (Gym or Rematch)
        # The IDs in BOSS_TRAINERS are the original gym battles
        # The IDs in gym_assignments are the rematch battles
        battle_type_mapping = {}
        
        # Write mapping debug file showing static and dynamic IDs
        with open('trainer_id_debug.txt', 'w') as debug_file:
            debug_file.write("===== ORIGINAL GYM BATTLES (ID: NAME - TYPE) =====\n")
            for tid, (name, type_) in BOSS_TRAINERS.items():
                battle_type_mapping[tid] = "Gym"
                debug_file.write(f"{tid}: {name} - {type_} (Gym Battle)\n")
            
            debug_file.write("\n===== REMATCH BATTLES (ID: NAME - TYPE) =====\n")
            for tid, info in self.gym_assignments.items():
                if tid.isdigit() and int(tid) not in BOSS_TRAINERS:
                    battle_type_mapping[int(tid)] = "Rematch"
                    trainer_name = info.get('trainer_name', f'Trainer {tid}')
                    assigned_type = info.get('assigned_type', 'Unknown')
                    debug_file.write(f"{tid}: {trainer_name} - {assigned_type} (Rematch Battle)\n")
        
        # Get all boss trainer IDs (from both original gym battles and rematch battles)
        all_boss_ids = set(BOSS_TRAINERS.keys())
        all_boss_ids.update(int(tid) for tid in self.gym_assignments.keys() if tid.isdigit())
        
        self.log(f"Found {len(all_boss_ids)} boss trainers to process")
        
        # Process all trainers, both gym battles and rematch battles
        for trainer_id in sorted(all_boss_ids):
            # Determine if this is a gym battle or rematch
            battle_type = battle_type_mapping.get(trainer_id, "Unknown")
            
            if self.apply_special_pokemon(rom, trainer_id, use_mimics, use_pivots, use_fulcrums, battle_type):
                modified_count += 1
        
        self.log(f"\nModified {modified_count} boss trainers with special Pokémon")
        return modified_count

def main():
    """Main function for running the special Pokémon handler from command line"""
    parser = argparse.ArgumentParser(description="Add special Pokémon to boss teams")
    parser.add_argument("rom_path", help="Path to the ROM file")
    parser.add_argument("--output", help="Path for the output ROM file. If not specified, will overwrite the input file.")
    parser.add_argument("--mimics", action="store_true", help="Add mimic Pokémon (thematic fit but not of the gym's type)")
    parser.add_argument("--pivots", action="store_true", help="Add pivot Pokémon (defensive Pokémon that cover gym weaknesses)")
    parser.add_argument("--fulcrums", action="store_true", help="Add fulcrum Pokémon (offensive Pokémon that counter gym counters)")
    parser.add_argument("--log", action="store_true", help="Enable detailed logging to a file")
        
    args = parser.parse_args()
        
    # Validate ROM path
    if not os.path.exists(args.rom_path):
        print(f"Error: ROM file {args.rom_path} not found")
        sys.exit(1)
        
    # Set output path if not specified
    output_path = args.output or args.rom_path
        
    # Setup logging
    log_file = None
    if args.log:
        log_file = output_path.replace(".nds", "_special_pokemon_log.txt")
        print(f"Logging enabled: {log_file}")
        
    # Initialize the handler
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    handler = SpecialPokemonHandler(args.rom_path, base_path=base_path, log_file=log_file)
        
    # Load the ROM
    rom = ndspy.rom.NintendoDSRom.fromFile(args.rom_path)
        
    # Process all boss trainers
    print("Adding special Pokémon to boss trainers...")
        
    # Check if any special Pokémon options are enabled
    if not (args.mimics or args.pivots or args.fulcrums):
        print("Warning: No special Pokémon options selected (--mimics, --pivots, --fulcrums)")
        print("No changes will be made to the ROM")
        return
        
    # Log which options are enabled
    print(f"Options enabled: " + 
          ("Mimics " if args.mimics else "") + 
          ("Pivots " if args.pivots else "") + 
          ("Fulcrums" if args.fulcrums else ""))
        
    modified = handler.process_all_bosses(rom, 
                                        use_mimics=args.mimics, 
                                        use_pivots=args.pivots, 
                                        use_fulcrums=args.fulcrums)
        
    # Save the ROM if any changes were made
    if modified:
        rom.saveToFile(output_path)
        print(f"ROM saved to {output_path}")
        
        # Close log file if open
        if handler.log_handle:
            handler.log_handle.close()
            print(f"Log saved to {log_file}")
    else:
        print("No changes were made to the ROM")

if __name__ == "__main__":
    sys.exit(main())
