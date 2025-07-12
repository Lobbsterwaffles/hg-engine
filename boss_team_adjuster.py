#!/usr/bin/env python3
"""
Boss Team Adjuster for Pokémon HGSS
-----------------------------------
This tool modifies boss trainer teams (gym leaders, Elite Four, rivals) to include special Pokémon.
It runs after the randomizer to add mimics, pivots, and fulcrums to boss teams based on gym types.

Features:
- Mimics: Replace one non-ace Pokémon with a type-themed Pokémon from type_mimics_with_prevos.txt
- Pivots: Replace one non-ace Pokémon with a Pokémon from pivot_analysis.txt (teams of 5+)
- Fulcrums: Replace one non-ace Pokémon with a Pokémon from fulcrumsmonlist.txt (teams of 6)

Usage:
  python boss_team_adjuster.py [rom_file] [--mimics] [--pivots] [--fulcrums] [--all]
"""

import ndspy.rom
import ndspy.narc
import os
import sys
import random
import argparse
import statistics
import json
import pokemon_data
import re
from construct import Container, Struct, Int8ul, Int16ul

# Pokémon entry structures - These match the data format in the ROM
trainer_pokemon_struct = Struct(
    "ivs" / Int8ul,             # 1 byte - IVs
    "abilityslot" / Int8ul,     # 1 byte - Ability slot
    "level" / Int16ul,          # 2 bytes - Level (halfword)
    "species" / Int16ul,        # 2 bytes - Species ID (halfword)
    "ballseal" / Int16ul,       # 2 bytes - Ball seal (halfword)
)

# Pokémon with moves structure (18 bytes total)
trainer_pokemon_moves_struct = Struct(
    "ivs" / Int8ul,             # 1 byte - IVs
    "abilityslot" / Int8ul,     # 1 byte - Ability slot
    "level" / Int16ul,          # 2 bytes - Level (halfword)
    "species" / Int16ul,        # 2 bytes - Species ID (halfword)
    "item" / Int16ul,           # 2 bytes - Held item
    "move1" / Int16ul,          # 2 bytes - Move 1
    "move2" / Int16ul,          # 2 bytes - Move 2
    "move3" / Int16ul,          # 2 bytes - Move 3
    "move4" / Int16ul,          # 2 bytes - Move 4
    "ballseal" / Int16ul,       # 2 bytes - Ball seal (halfword)
)

# NARC file paths
TRAINER_POKEMON_NARC_PATH = "a/0/5/6"  # Pokémon data
TRAINER_DATA_NARC_PATH = "a/0/5/5"     # Trainer data including poke_count
POKEMON_STATS_NARC_PATH = "a/0/1/1"    # Pokémon base stats

# Stats to read from Pokémon data
STAT_NAMES = ["hp", "attack", "defense", "speed", "spatk", "spdef"]

# Pokémon stats structure
stats_struct = Struct(
    "hp" / Int8ul,
    "attack" / Int8ul,
    "defense" / Int8ul,
    "speed" / Int8ul,
    "spatk" / Int8ul,
    "spdef" / Int8ul,
)

# List of boss trainers that will be modified
BOSS_TRAINERS = {
    # Format: trainer_id: (name, default_type)
    # Johto Gym Leaders
    20: ("Falkner", "Flying"),
    21: ("Bugsy", "Bug"),
    30: ("Whitney", "Normal"),
    31: ("Morty", "Ghost"),
    34: ("Chuck", "Fighting"),
    33: ("Jasmine", "Steel"),
    32: ("Pryce", "Ice"),
    35: ("Clair", "Dragon"),
    # Kanto Gym Leaders
    253: ("Brock", "Rock"),
    254: ("Misty", "Water"),
    255: ("Lt. Surge", "Electric"),
    256: ("Erika", "Grass"),
    257: ("Janine", "Poison"),
    258: ("Sabrina", "Psychic"),
    259: ("Blaine", "Fire"),
    261: ("Blue", "Normal"),
    # Elite Four
    245: ("Will", "Psychic"),
    247: ("Koga", "Poison"),
    418: ("Bruno", "Fighting"),
    246: ("Karen", "Dark"),
    # Lance is excluded per requirements
}

# Rival (Silver) battles with their IDs - first battle excluded
RIVAL_BATTLES = [
    # 112,  # First battle - excluded as per requirements
    113,  # Second battle
    114,  # Later battles
    115,
    116,
    117,
    118,
    119,
]

# Define type lists
MIMIC_TYPES = {}  # Will be filled from type_mimics_with_prevos.txt
PIVOT_TYPES = {}  # Will be filled from pivot_analysis.txt
FULCRUM_LIST = [] # Will be filled from fulcrumsmonlist.txt

def species_name_to_id(species_name):
    """Convert a Pokémon species name like 'SPECIES_PIKACHU' to its numeric ID.
    
    This function tries to extract the ID from the species_data.s file or uses a fallback
    method if that's not possible.
    
    Args:
        species_name (str): The species name in format 'SPECIES_NAME'
        
    Returns:
        int: The numeric species ID or a fallback value (25 for Pikachu) if not found
    """
    # If it's already a numeric ID, just return it
    if isinstance(species_name, int):
        return species_name
    
    try:
        # Try to find the species ID from the armips species file
        species_file_path = os.path.join('armips', 'data', 'species', 'species_data.s')
        
        if os.path.exists(species_file_path):
            with open(species_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Look for the specific define
                pattern = f"{species_name} equ (.+)\\n"
                match = re.search(pattern, content)
                
                if match:
                    id_str = match.group(1).strip()
                    # Handle hex values and decimal
                    if id_str.startswith('0x'):
                        return int(id_str, 16)
                    return int(id_str)
        
        # Fallback: Try to get numeric ID from National Pokédex constants
        # Extract the ID portion from SPECIES_NAME format
        if species_name.startswith('SPECIES_'):
            # Try to match with standard Pokémon from Gen 1-4 (up to 493)
            name_part = species_name[8:].lower()
            
            # Map of common Pokémon names to their National Dex numbers
            common_dex = {
                'bulbasaur': 1, 'charmander': 4, 'squirtle': 7, 'pikachu': 25,
                'eevee': 133, 'mewtwo': 150, 'mew': 151,
                'totodile': 158, 'cyndaquil': 155, 'chikorita': 152,
                'typhlosion': 157, 'meganium': 154, 'feraligatr': 160,
                'lugia': 249, 'ho_oh': 250, 'celebi': 251,
                'treecko': 252, 'torchic': 255, 'mudkip': 258,
                'kyogre': 382, 'groudon': 383, 'rayquaza': 384,
                'dialga': 483, 'palkia': 484, 'giratina': 487, 'arceus': 493
            }
            
            if name_part in common_dex:
                return common_dex[name_part]
        
        # Last resort: Return a fallback ID - 25 (Pikachu) is a safe choice
        print(f"Warning: Could not convert {species_name} to ID, using placeholder")
        return 25
    
    except Exception as e:
        print(f"Error converting species name to ID: {e}")
        return 25  # Fallback to Pikachu


def load_type_files():
    """Load mimic, pivot, and fulcrum type lists from data files
    
    Returns:
        tuple: (mimic_types, pivot_types, fulcrum_list)
    """
    # Initialize dictionaries/lists
    mimic_types = {}
    pivot_types = {}
    fulcrum_list = []
    current_type = None
    
    # Load mimic types
    try:
        with open('data/type_mimics_with_prevos.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if line.startswith('[') and line.endswith(']'):
                    current_type = line[1:-1].upper()  # Store type in uppercase for case-insensitive comparison
                    mimic_types[current_type] = []
                elif current_type and line.startswith('SPECIES_'):
                    # Add species name (will be converted to ID when needed)
                    mimic_types[current_type].append(line)
    except FileNotFoundError:
        print("Warning: data/type_mimics_with_prevos.txt not found")
    
    # Load pivot types
    try:
        with open('data/pivot_analysis.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if line.startswith('[') and line.endswith(']'):
                    current_type = line[1:-1].upper()  # Store type in uppercase for case-insensitive comparison
                    pivot_types[current_type] = []
                elif current_type and line.startswith('SPECIES_'):
                    # Add species name (will be converted to ID when needed)
                    pivot_types[current_type].append(line)
    except FileNotFoundError:
        print("Warning: data/pivot_analysis.txt not found")
    
    # Load fulcrum list
    try:
        with open('data/fulcrumsmonlist.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if line.startswith('SPECIES_'):
                    fulcrum_list.append(line)
    except FileNotFoundError:
        print("Warning: data/fulcrumsmonlist.txt not found")
    
    return mimic_types, pivot_types, fulcrum_list


def load_gym_types(rom_path):
    """Load gym type assignments from temp/gym_types.json
    
    Args:
        rom_path (str): Path to the ROM file
        
    Returns:
        dict: Trainer ID to type mapping
    """
    try:
        with open('temp/gym_types.json', 'r') as f:
            gym_types_data = json.load(f)
        
        # Create a mapping of trainer ID to type
        trainer_types = {}
        
        for entry in gym_types_data:
            if 'trainer_id' in entry and 'type' in entry:
                trainer_id = int(entry['trainer_id'])
                type_name = entry['type']
                trainer_types[trainer_id] = type_name
        
        # Update our BOSS_TRAINERS dictionary with the dynamic types
        for trainer_id, (name, _) in BOSS_TRAINERS.items():
            if trainer_id in trainer_types:
                BOSS_TRAINERS[trainer_id] = (name, trainer_types[trainer_id])
                
        return trainer_types
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load gym types: {e}")
        return {}


def load_temp_data(rom_path):
    """Load temporary data saved by previous scripts
    
    Args:
        rom_path (str): Path to the ROM file
        
    Returns:
        dict: Temporary data or empty dict if not found
    """
    temp_file = rom_path.replace('.nds', '_temp_data.json')
    try:
        with open(temp_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_temp_data(rom_path, data):
    """Save temporary data for other scripts
    
    Args:
        rom_path (str): Path to the ROM file
        data (dict): Data to save
    """
    temp_file = rom_path.replace('.nds', '_temp_data.json')
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Saved temporary data to {temp_file}")
    except Exception as e:
        print(f"Error saving temporary data: {e}")

def find_ace_pokemon(pokemon_list):
    """Find the ace Pokémon in a trainer's team (highest level Pokémon)
    
    Args:
        pokemon_list (list): List of trainer Pokémon objects
        
    Returns:
        tuple: (ace_index, ace_pokemon, is_unique)
        is_unique is False if there's a tie for highest level
    """
    if not pokemon_list:
        return None, None, False
    
    # Find the highest level
    max_level = max(p.level for p in pokemon_list)
    
    # Find Pokémon with the highest level
    ace_candidates = [(i, p) for i, p in enumerate(pokemon_list) if p.level == max_level]
    
    # If there's exactly one highest level Pokémon, that's our ace
    if len(ace_candidates) == 1:
        ace_index, ace_pokemon = ace_candidates[0]
        return ace_index, ace_pokemon, True
    
    # Otherwise we have a tie - not a unique ace
    return None, None, False

def species_name_to_id(species_name):
    """Convert a species name from the data files to a numeric ID
    
    Args:
        species_name (str): Species name like SPECIES_PIKACHU
        
    Returns:
        int: Species ID or None if not found
    """
    # This is a simplified implementation - in a real implementation,
    # you'd want to have a more comprehensive mapping table
    species_prefix = "SPECIES_"
    if not species_name.startswith(species_prefix):
        return None
        
    name = species_name[len(species_prefix):]
    
    # Search through the POKEMON_BST dictionary to find a match
    for species_id, data in pokemon_data.POKEMON_BST.items():
        if data["name"] == name:
            return species_id
    
    # Fallback: return None if not found
    return None


# Function removed as we're directly using pokemon_data.POKEMON_BST


def find_replacement_mimic(type_name, original_bst, existing_species):
    """Find a mimic replacement Pokémon of a given type
    
    Args:
        type_name (str): Type name for replacement
        original_bst (int): Original BST to match
        existing_species (list): List of existing species to avoid duplicates
        
    Returns:
        int: Mimic species ID or None
    """    
    # Convert type_name to uppercase for case-insensitive matching
    type_name_upper = type_name.upper()
    if type_name_upper not in MIMIC_TYPES:
        print(f"No mimics found for type: {type_name}")
        return None
        
    # Filter available mimics
    mimic_ids = []
    for mimic_name in MIMIC_TYPES[type_name_upper]:
        species_id = species_name_to_id(mimic_name)
        if species_id not in existing_species:
            mimic_ids.append(species_id)
            
    if not mimic_ids:
        print(f"No available mimics for type: {type_name}")
        return None
    
    # Try to find mimics with BST within 10% of original
    filtered_mimics_10 = []
    for species_id in mimic_ids:
        if species_id in pokemon_data.POKEMON_BST:
            species_bst = pokemon_data.POKEMON_BST[species_id]["bst"]
            if abs(species_bst - original_bst) <= 0.1 * original_bst:
                filtered_mimics_10.append(species_id)
    
    # If no close matches, try within 50%
    filtered_mimics_50 = []
    if not filtered_mimics_10:
        for species_id in mimic_ids:
            if species_id in pokemon_data.POKEMON_BST:
                species_bst = pokemon_data.POKEMON_BST[species_id]["bst"]
                if abs(species_bst - original_bst) <= 0.5 * original_bst:
                    filtered_mimics_50.append(species_id)
    
    # Choose from the best filtered list available
    if filtered_mimics_10:
        print(f"Found {len(filtered_mimics_10)} mimics within 10% BST for type {type_name}")
        return random.choice(filtered_mimics_10)
    elif filtered_mimics_50:
        print(f"Found {len(filtered_mimics_50)} mimics within 50% BST for type {type_name}")
        return random.choice(filtered_mimics_50)
    elif mimic_ids:
        print(f"Using any available mimic for type {type_name}")
        return random.choice(mimic_ids)  # Fallback to any available
    
    return None


def find_replacement_pivot(type_name, original_bst, existing_species):
    """Find a replacement pivot Pokémon of a given type
    
    Args:
        type_name (str): Type name for replacement
        original_bst (int): Original BST to match
        existing_species (list): List of existing species to avoid duplicates
        
    Returns:
        int: Pivot species ID or None
    """    
    # Convert type_name to uppercase for case-insensitive matching
    type_name_upper = type_name.upper()
    if type_name_upper in PIVOT_TYPES:
        # Filter available pivots
        available_pivots = []
        for pivot_name in PIVOT_TYPES[type_name_upper]:
            species_id = species_name_to_id(pivot_name)
            if species_id not in existing_species:
                available_pivots.append(species_id)
        
        if not available_pivots:
            print(f"No available pivots for type: {type_name}")
            return None
        
        # Try to find species with BST within 10% of original
        filtered_pivots_10 = []
        for pivot_id in available_pivots:
            if pivot_id in pokemon_data.POKEMON_BST:
                pivot_bst = pokemon_data.POKEMON_BST[pivot_id]["bst"]
                if abs(pivot_bst - original_bst) <= 0.1 * original_bst:  # 10% BST range
                    filtered_pivots_10.append(pivot_id)
        
        # If we found pivots within 10% range, choose one randomly
        if filtered_pivots_10:
            print(f"Found {len(filtered_pivots_10)} pivots within 10% BST for type {type_name}")
            return random.choice(filtered_pivots_10)
        
        # Try to find species with BST within 50% of original
        filtered_pivots_50 = []
        for pivot_id in available_pivots:
            if pivot_id in pokemon_data.POKEMON_BST:
                pivot_bst = pokemon_data.POKEMON_BST[pivot_id]["bst"]
                if abs(pivot_bst - original_bst) <= 0.5 * original_bst:  # 50% BST range
                    filtered_pivots_50.append(pivot_id)
        
        # If we found pivots within 50% range, choose one randomly
        if filtered_pivots_50:
            print(f"Found {len(filtered_pivots_50)} pivots within 50% BST for type {type_name}")
            return random.choice(filtered_pivots_50)
        
        # If still no match, return any available pivot
        if available_pivots:
            print(f"Using any available pivot for type {type_name}")
            return random.choice(available_pivots)
    
    print(f"No pivots found for type: {type_name}")
    return None


def find_replacement_fulcrum(original_bst, existing_species):
    """Find a replacement fulcrum Pokémon
    
    Args:
        original_bst (int): Original BST to match
        existing_species (list): List of existing species to avoid duplicates
        
    Returns:
        int: Fulcrum species ID or None
    """    
    # Filter available fulcrums
    available_fulcrums = []
    for fulcrum_name in FULCRUM_LIST:
        species_id = species_name_to_id(fulcrum_name)
        if species_id not in existing_species:
            available_fulcrums.append(species_id)
    
    if not available_fulcrums:
        print("No available fulcrums found")
        return None
    
    # Try to find species with BST within 10% of original
    filtered_fulcrums_10 = []
    for fulcrum_id in available_fulcrums:
        if fulcrum_id in pokemon_data.POKEMON_BST:
            fulcrum_bst = pokemon_data.POKEMON_BST[fulcrum_id]["bst"]
            if abs(fulcrum_bst - original_bst) <= 0.1 * original_bst:  # 10% BST range
                filtered_fulcrums_10.append(fulcrum_id)
    
    # If we found fulcrums within 10% range, choose one randomly
    if filtered_fulcrums_10:
        return random.choice(filtered_fulcrums_10)
    
    # Try to find species with BST within 50% of original
    filtered_fulcrums_50 = []
    for fulcrum_id in available_fulcrums:
        if fulcrum_id in pokemon_data.POKEMON_BST:
            fulcrum_bst = pokemon_data.POKEMON_BST[fulcrum_id]["bst"]
            if abs(fulcrum_bst - original_bst) <= 0.5 * original_bst:  # 50% BST range
                filtered_fulcrums_50.append(fulcrum_id)
    
    # If we found fulcrums within 50% range, choose one randomly
    if filtered_fulcrums_50:
        return random.choice(filtered_fulcrums_50)
    
    # If still no match, return any available fulcrum
    if available_fulcrums:
        return random.choice(available_fulcrums)
    
    print("No suitable fulcrums found")
    return None


def adjust_boss_team(rom, trainer_id, options):
    """Adjust a boss trainer's team with special Pokémon
    
    Args:
        rom: The ROM object
        trainer_id (int): Trainer ID
        options (dict): Options for team adjustment
        
    Returns:
        bool: True if the team was adjusted
    """
    # Get trainer name and type
    if trainer_id in BOSS_TRAINERS:
        trainer_name, type_name = BOSS_TRAINERS[trainer_id]
    else:
        # For Silver (rival)
        trainer_name = "Silver"
        type_name = "NORMAL"  # Default, will not be used
    
    print(f"\nProcessing {trainer_name} (ID: {trainer_id})")
    
    # Get the trainer's Pokémon
    pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
    
    if not pokemon_list:
        print(f"No Pokémon found for trainer {trainer_id}")
        return False
    
    # Find the ace Pokémon
    ace_index, ace_pokemon, is_unique = find_ace_pokemon(pokemon_list)
    
    if not is_unique:
        print(f"Error: Trainer {trainer_name} (ID: {trainer_id}) does not have a unique ace Pokémon")
        return False
    
    # Get Pokémon name if available
    ace_name = pokemon_data.POKEMON_BST.get(ace_pokemon.species, {}).get("name", "Unknown")
    print(f"Found ace Pokémon: {ace_name} (ID: {ace_pokemon.species}) at Level {ace_pokemon.level}")
    
    # Track which Pokémon have been replaced
    replaced_indices = set([ace_index])  # Don't replace the ace
    
    # Track existing species to avoid duplicates
    existing_species = [p.species for p in pokemon_list]
    
    # Apply team adjustments based on options
    changes_made = False
    
    # Apply Mimics option
    if options.get('mimics', False) and len(pokemon_list) >= 4:
        # Choose a non-ace Pokémon to replace
        available_indices = [i for i in range(len(pokemon_list)) if i != ace_index]
        
        if available_indices:
            replace_index = random.choice(available_indices)
            replace_pokemon = pokemon_list[replace_index]
            replaced_indices.add(replace_index)
            
            # Get original BST from pokemon_data module
            original_bst = None
            if replace_pokemon.species in pokemon_data.POKEMON_BST:
                original_bst = pokemon_data.POKEMON_BST[replace_pokemon.species]["bst"]
            else:
                # Default BST if not found
                original_bst = 300
            
            if original_bst:
                mimic_id = find_replacement_mimic(type_name, original_bst, existing_species)
                
                if mimic_id:
                    # Get original and replacement Pokémon names
                    original_name = pokemon_data.POKEMON_BST.get(replace_pokemon.species, {}).get("name", "Unknown")
                    mimic_name = pokemon_data.POKEMON_BST.get(mimic_id, {}).get("name", "Unknown")
                    print(f"Replacing Pokémon at index {replace_index}: {original_name} (ID: {replace_pokemon.species}) with mimic: {mimic_name} (ID: {mimic_id})")
                    pokemon_list[replace_index].species = mimic_id
                    existing_species.append(mimic_id)
                    changes_made = True
    
    # Apply Pivots option (teams of 5+)
    if options.get('pivots', False) and len(pokemon_list) >= 5:
        # Choose a non-ace, non-replaced Pokémon to replace
        available_indices = [i for i in range(len(pokemon_list)) if i != ace_index and i not in replaced_indices]
        
        if available_indices:
            replace_index = random.choice(available_indices)
            replace_pokemon = pokemon_list[replace_index]
            replaced_indices.add(replace_index)
            
            # Get original BST from pokemon_data module
            original_bst = None
            if replace_pokemon.species in pokemon_data.POKEMON_BST:
                original_bst = pokemon_data.POKEMON_BST[replace_pokemon.species]["bst"]
            else:
                # Default BST if not found
                original_bst = 300
            
            if original_bst:
                pivot_id = find_replacement_pivot(type_name, original_bst, existing_species)
                
                if pivot_id:
                    # Get original and replacement Pokémon names
                    original_name = pokemon_data.POKEMON_BST.get(replace_pokemon.species, {}).get("name", "Unknown")
                    pivot_name = pokemon_data.POKEMON_BST.get(pivot_id, {}).get("name", "Unknown")
                    print(f"Replacing Pokémon at index {replace_index}: {original_name} (ID: {replace_pokemon.species}) with pivot: {pivot_name} (ID: {pivot_id})")
                    pokemon_list[replace_index].species = pivot_id
                    existing_species.append(pivot_id)
                    changes_made = True
    
    # Apply Fulcrums option (teams of 6)
    if options.get('fulcrums', False) and len(pokemon_list) == 6:
        # Choose a non-ace, non-replaced Pokémon
        available_indices = [i for i in range(len(pokemon_list)) 
                           if i != ace_index and i not in replaced_indices]
        
        if available_indices:
            replace_index = random.choice(available_indices)
            replace_pokemon = pokemon_list[replace_index]
            replaced_indices.add(replace_index)
            
            # Get original BST from pokemon_data module
            original_bst = None
            if replace_pokemon.species in pokemon_data.POKEMON_BST:
                original_bst = pokemon_data.POKEMON_BST[replace_pokemon.species]["bst"]
            else:
                # Default BST if not found
                original_bst = 300
            
            if original_bst:
                fulcrum_id = find_replacement_fulcrum(original_bst, existing_species)
                
                if fulcrum_id:
                    # Get original and replacement Pokémon names
                    original_name = pokemon_data.POKEMON_BST.get(replace_pokemon.species, {}).get("name", "Unknown")
                    fulcrum_name = pokemon_data.POKEMON_BST.get(fulcrum_id, {}).get("name", "Unknown")
                    print(f"Replacing Pokémon at index {replace_index}: {original_name} (ID: {replace_pokemon.species}) with fulcrum: {fulcrum_name} (ID: {fulcrum_id})")
                    pokemon_list[replace_index].species = fulcrum_id
                    existing_species.append(fulcrum_id)
                    changes_made = True
    
    # Save changes if any were made
    if changes_made:
        save_trainer_pokemon(rom, trainer_id, pokemon_list, has_moves)
        print(f"Saved changes for {trainer_name} (ID: {trainer_id})")
        return True
    else:
        print(f"No changes made for {trainer_name} (ID: {trainer_id})")
        return False


def process_all_bosses(rom, rom_path, options):
    """Process all boss trainers and adjust their teams
    
    Args:
        rom: The ROM object
        rom_path: Path to the ROM file
        options (dict): Options for team adjustment
        
    Returns:
        int: Number of trainers modified
    """
    # Load gym types from JSON file
    load_gym_types(rom_path)
    
    # Load type lists from files
    global MIMIC_TYPES, PIVOT_TYPES, FULCRUM_LIST
    MIMIC_TYPES, PIVOT_TYPES, FULCRUM_LIST = load_type_files()
    
    print(f"Loaded {sum(len(mimics) for mimics in MIMIC_TYPES.values())} mimic Pokémon")
    print(f"Loaded {sum(len(pivots) for pivots in PIVOT_TYPES.values())} pivot Pokémon")
    print(f"Loaded {len(FULCRUM_LIST)} fulcrum Pokémon")
    
    modified_count = 0
    
    # Process all bosses
    print("\nProcessing boss trainers...")
    for trainer_id in BOSS_TRAINERS:
        if adjust_boss_team(rom, trainer_id, options):
            modified_count += 1
    
    # Process rival battles
    print("\nProcessing rival battles...")
    for trainer_id in RIVAL_BATTLES:
        # Skip first rival battle as per requirements
        if trainer_id == 112:  # First battle
            print(f"Skipping first rival battle (ID: {trainer_id}) as per requirements")
            continue
            
        if adjust_boss_team(rom, trainer_id, options):
            modified_count += 1
    
    return modified_count


def fix_team_size_inconsistencies(rom):
    """Find and fix trainers whose poke_count doesn't match their actual Pokemon count.
    
    Args:
        rom: The ROM object
        
    Returns:
        int: Number of trainers fixed
    """
    fixed_count = 0
    
    # Get the trainer data NARC
    try:
        narc_file_id = rom.filenames.idOf(TRAINER_DATA_NARC_PATH)
        trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
        
        # Check trainers (up to a reasonable limit)
        for trainer_id in range(min(len(trainer_data_narc.files), 500)):
            try:
                # Skip trainers with no data
                if len(trainer_data_narc.files[trainer_id]) == 0:
                    continue
                    
                # Get the poke_count from trainer data
                trainer_data = trainer_data_narc.files[trainer_id]
                poke_count = trainer_data[3]  # poke_count is at offset 3
                
                # Get the actual Pokemon count from the Pokemon data
                pokemon_list = None
                try:
                    pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
                    actual_count = len(pokemon_list)
                except Exception:
                    continue
                
                # If there's a mismatch, fix it
                if poke_count != actual_count:
                    # Only fix if this is a boss trainer or rival
                    is_boss = trainer_id in BOSS_TRAINERS
                    is_rival = trainer_id in RIVAL_BATTLES
                    
                    if is_boss or is_rival:
                        print(f"Found inconsistency for trainer {trainer_id}: poke_count={poke_count}, actual={actual_count}")
                        
                        # Update the poke_count value
                        trainer_data = bytearray(trainer_data)
                        trainer_data[3] = actual_count
                        
                        # Save back to NARC
                        trainer_data_narc.files[trainer_id] = bytes(trainer_data)
                        
                        # Get the trainer name for the log
                        if trainer_id in BOSS_TRAINERS:
                            name = BOSS_TRAINERS[trainer_id][0]
                        else:
                            name = f"Rival (ID: {trainer_id})"
                            
                        print(f"Fixed {name} - updated poke_count to {actual_count}")
                        fixed_count += 1
            except Exception as e:
                # Skip problematic trainers
                continue
                
        # Save the NARC file back to the ROM
        rom.files[narc_file_id] = trainer_data_narc.save()
    except Exception as e:
        print(f"Error fixing team sizes: {e}")
    
    return fixed_count


def get_trainer_pokemon(rom, trainer_id):
    """Get a trainer's Pokemon list from the ROM.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        
    Returns:
        tuple: (pokemon_list, has_moves) - The list of Pokemon and whether they have moves
    """
    # Get the trainer Pokemon NARC
    narc_file_id = rom.filenames.idOf(TRAINER_POKEMON_NARC_PATH)
    trainer_narc_data = ndspy.narc.NARC(rom.files[narc_file_id])
    
    # Check if trainer exists
    if trainer_id >= len(trainer_narc_data.files):
        raise ValueError(f"Trainer ID {trainer_id} does not exist in the ROM")
    
    # Get trainer's Pokemon data
    pokemon_data = trainer_narc_data.files[trainer_id]
    
    # Check if trainer has Pokemon with moves
    # A trainer with moves will have 18 bytes per Pokemon
    has_moves = (len(pokemon_data) % 18 == 0) and len(pokemon_data) > 0
    pokemon_size = 18 if has_moves else 8
    
    # Calculate number of Pokemon
    num_pokemon = len(pokemon_data) // pokemon_size
    
    # Parse each Pokemon
    pokemon_list = []
    for i in range(num_pokemon):
        start_offset = i * pokemon_size
        pokemon_bytes = pokemon_data[start_offset:start_offset + pokemon_size]
        
        if has_moves:
            # Parse with moves struct
            pokemon = trainer_pokemon_moves_struct.parse(pokemon_bytes)
        else:
            # Parse with basic struct
            pokemon = trainer_pokemon_struct.parse(pokemon_bytes)
        
        pokemon_list.append(pokemon)
    
    return pokemon_list, has_moves


def save_trainer_pokemon(rom, trainer_id, pokemon_list, has_moves):
    """Save a trainer's Pokemon list back to the ROM.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        pokemon_list: List of Pokemon objects
        has_moves: Whether Pokemon have moves
    """
    # Get the trainer Pokemon NARC
    narc_file_id = rom.filenames.idOf(TRAINER_POKEMON_NARC_PATH)
    trainer_narc_data = ndspy.narc.NARC(rom.files[narc_file_id])
    
    # Build the new Pokemon data
    new_data = bytearray()
    for pokemon in pokemon_list:
        if has_moves:
            pokemon_bytes = trainer_pokemon_moves_struct.build(pokemon)
        else:
            pokemon_bytes = trainer_pokemon_struct.build(pokemon)
        new_data.extend(pokemon_bytes)
    
    # Save back to NARC
    trainer_narc_data.files[trainer_id] = bytes(new_data)
    rom.files[narc_file_id] = trainer_narc_data.save()
    
    print(f"Updated trainer {trainer_id}'s Pokemon data ({len(pokemon_list)} Pokemon)")


def main():
    """Main function for running the script directly"""
    parser = argparse.ArgumentParser(description="Adjust boss trainer teams in Pokemon HGSS")
    parser.add_argument("rom_file", help="Path to the ROM file")
    parser.add_argument("--mimics", action="store_true",
                        help="Add mimic Pokemon to boss teams (>=4 Pokemon)")
    parser.add_argument("--pivots", action="store_true",
                        help="Add pivot Pokemon to boss teams (>=5 Pokemon)")
    parser.add_argument("--fulcrums", action="store_true",
                        help="Add fulcrum Pokemon to boss teams (==6 Pokemon)")
    parser.add_argument("--all", action="store_true",
                        help="Add all special Pokemon types (mimics, pivots, fulcrums)")
    parser.add_argument("--log", help="Path to log file for team compositions")
    
    args = parser.parse_args()
    
    # Load the ROM
    try:
        rom = ndspy.rom.NintendoDSRom.fromFile(args.rom_file)
    except Exception as e:
        print(f"Error loading ROM: {e}")
        return 1
    
    # Fix any inconsistencies in trainer data
    print("Checking for team size inconsistencies...")
    fixed = fix_team_size_inconsistencies(rom)
    print(f"Fixed {fixed} trainers with inconsistent team sizes")
    
    # Set up options based on command line args
    options = {
        'mimics': args.mimics or args.all,
        'pivots': args.pivots or args.all,
        'fulcrums': args.fulcrums or args.all,
    }
    
    # Process all boss trainers
    modified_count = process_all_bosses(rom, args.rom_file, options)
    print(f"Modified {modified_count} boss trainers")
    
    # Create output filename with appropriate suffixes
    base_name = os.path.splitext(args.rom_file)[0]
    suffix_parts = []
    
    if options['mimics']:
        suffix_parts.append("mimics")
    if options['pivots']:
        suffix_parts.append("pivots")
    if options['fulcrums']:
        suffix_parts.append("fulcrums")
    
    if suffix_parts:
        suffix = "_" + "_".join(suffix_parts)
    else:
        suffix = "_adjusted"
    
    output_name = f"{base_name}{suffix}.nds"
    
    # Save the ROM
    try:
        rom.saveToFile(output_name)
        print(f"Saved modified ROM to {output_name}")
    except Exception as e:
        print(f"Error saving ROM: {e}")
        return 1
    
    # Log final teams if requested
    if args.log:
        log_trainer_teams_after_adjustment(rom, args.log, args.rom_file)
    
    return 0


def log_trainer_teams_after_adjustment(rom, log_filename, rom_path=None):
    """Log all trainer teams after boss team adjustments to show final team compositions.
    
    Args:
        rom: The ROM object
        log_filename: Path to the log file to create/append
        rom_path: Path to ROM file for loading dynamic type assignments
    """
    try:
        # Get dynamic boss types if ROM path is provided
        if rom_path:
            boss_trainers = get_dynamic_boss_types(rom_path)
        else:
            boss_trainers = BOSS_TRAINERS
        
        # Create log header
        log_content = ["\n" + "="*80]
        log_content.append("TRAINER TEAMS AFTER BOSS TEAM ADJUSTMENTS")
        log_content.append("="*80)
        
        # Log all boss trainers
        for trainer_id, (name, preferred_type) in boss_trainers.items():
            try:
                pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
                
                log_content.append(f"\n{name} (ID: {trainer_id}, Type: {preferred_type})")
                log_content.append(f"Team Size: {len(pokemon_list)} Pokemon")
                
                for i, pokemon in enumerate(pokemon_list, 1):
                    species_name = f"Species {pokemon.species}"
                    moves_info = ""
                    if has_moves and hasattr(pokemon, 'move1'):
                        moves = [getattr(pokemon, f'move{j}', 0) for j in range(1, 5) if getattr(pokemon, f'move{j}', 0) > 0]
                        if moves:
                            moves_info = f" (Moves: {', '.join(map(str, moves))})"
                    
                    log_content.append(f"  {i}. {species_name} (Lv. {pokemon.level}){moves_info}")
                    
            except Exception as e:
                log_content.append(f"\n{name} (ID: {trainer_id}) - Error reading team: {e}")
        
        # Log rival battles
        log_content.append("\n" + "-"*40)
        log_content.append("RIVAL BATTLES")
        log_content.append("-"*40)
        
        for trainer_id in RIVAL_BATTLES:
            try:
                pokemon_list, has_moves = get_trainer_pokemon(rom, trainer_id)
                
                log_content.append(f"\nRival Battle (ID: {trainer_id})")
                log_content.append(f"Team Size: {len(pokemon_list)} Pokemon")
                
                for j, pokemon in enumerate(pokemon_list, 1):
                    species_name = f"Species {pokemon.species}"
                    moves_info = ""
                    if has_moves and hasattr(pokemon, 'move1'):
                        moves = [getattr(pokemon, f'move{k}', 0) for k in range(1, 5) if getattr(pokemon, f'move{k}', 0) > 0]
                        if moves:
                            moves_info = f" (Moves: {', '.join(map(str, moves))})"
                    
                    log_content.append(f"  {j}. {species_name} (Lv. {pokemon.level}){moves_info}")
                    
            except Exception as e:
                log_content.append(f"\nRival Battle (ID: {trainer_id}) - Error reading team: {e}")
        
        # Write to log file
        with open(log_filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_content) + '\n')
        
        print(f"Final trainer team compositions logged to: {log_filename}")
        
    except Exception as e:
        print(f"Error logging trainer teams: {e}")
        
        
def load_temp_data(rom_path):
    """Load temporary data for this ROM from previous pipeline steps
    
    Args:
        rom_path (str): Path to the ROM file
        
    Returns:
        dict: Dictionary with temporary data or None if not found
    """
    try:
        # Create a ROM-specific temp data path
        rom_name = os.path.basename(rom_path)
        rom_base = os.path.splitext(rom_name)[0]  # Remove extension
        
        # Check for temp files in several locations
        possible_paths = [
            os.path.join(os.path.dirname(__file__), 'temp', f'{rom_base}_data.json'),  # Local temp folder
            os.path.join(os.path.dirname(__file__), f'{rom_base}_data.json'),  # Same folder
            os.path.join(os.path.dirname(rom_path), f'{rom_base}_data.json'),  # ROM folder
            os.path.join(os.path.dirname(rom_path), 'temp', f'{rom_base}_data.json'),  # ROM temp folder
        ]
        
        # Also check for generic gym_types.json
        possible_paths.append(os.path.join(os.path.dirname(__file__), 'temp', 'gym_types.json'))
        possible_paths.append(os.path.join(os.path.dirname(__file__), 'data', 'gym_types.json'))
        
        # Try each path
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Loading temporary data from {path}")
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # If this is just a gym types file, wrap it in the correct structure
                    if path.endswith('gym_types.json'):
                        return {'gym_types': data}
                    return data
                    
        print("No temporary data found for this ROM")
        return None
    except Exception as e:
        print(f"Error loading temporary data: {e}")
        return None


def get_dynamic_boss_types(rom_path):
    """Get dynamic gym types from temporary data saved by previous scripts
    
    Args:
        rom_path (str): Path to the ROM file
        
    Returns:
        dict: Dict of trainer IDs to (name, type) tuples
    """
    # Start with default types
    boss_types = BOSS_TRAINERS.copy()
    
    # Try to load temp data
    temp_data = load_temp_data(rom_path)
    if not temp_data or 'gym_types' not in temp_data:
        print("No dynamic gym type assignments found, using defaults")
        return boss_types
        
    # Update with dynamic types
    gym_types = temp_data['gym_types']
    updated = 0
    
    for trainer_id_str, type_name in gym_types.items():
        # Convert trainer ID to integer
        try:
            trainer_id = int(trainer_id_str)
            if trainer_id in boss_types:
                # Update with new type while keeping the name
                name = boss_types[trainer_id][0]
                boss_types[trainer_id] = (name, type_name)
                updated += 1
        except ValueError:
            continue
    
    print(f"Updated {updated} boss trainers with dynamic type assignments")
    return boss_types

def read_pokemon_stats(rom):
    """
    Read all Pokémon base stats from the ROM.
    
    Args:
        rom: The ROM object
        
    Returns:
        dict: Dictionary mapping species IDs to their base stats
    """
    try:
        # Get the Pokémon stats NARC
        narc_file_id = rom.filenames.idOf(POKEMON_STATS_NARC_PATH)
        stats_narc = ndspy.narc.NARC(rom.files[narc_file_id])
        
        # Dictionary to store stats for each species
        pokemon_stats = {}
        
        # Parse stats for each Pokémon species
        for species_id, file_data in enumerate(stats_narc.files):
            # Skip empty entries
            if len(file_data) < 28:  # Basic sanity check
                continue
                
            # The base stats are at offset 0x14 (20) in the data
            stats_offset = 0x14
            stats_data = file_data[stats_offset:stats_offset + 6]  # 6 stats, 1 byte each
            
            # Parse the stats
            try:
                stats = stats_struct.parse(stats_data)
                pokemon_stats[species_id] = stats
            except Exception:
                # Skip problematic entries
                continue
        
        return pokemon_stats
    except Exception as e:
        print(f"Error reading Pokémon stats: {e}")
        return {}

def calculate_bst(stats):
    """
    Calculate the Base Stat Total (BST) of a Pokémon.
    
    Args:
        stats: Stats container from stats_struct
        
    Returns:
        int: The Base Stat Total
    """
    return sum(getattr(stats, stat) for stat in STAT_NAMES)

def get_bst_for_species(species_id, pokemon_stats):
    """
    Get the BST for a specific Pokémon species.
    
    Args:
        species_id: The Pokémon species ID
        pokemon_stats: Dictionary of Pokémon stats
        
    Returns:
        int: The BST for the species, or 300 if not found (reasonable default)
    """
    if species_id in pokemon_stats:
        return calculate_bst(pokemon_stats[species_id])
    return 300  # Default BST if not found

def get_mean_bst(pokemon_list, pokemon_stats):
    """
    Calculate the mean (average) BST of a list of Pokémon.
    
    Args:
        pokemon_list: List of Pokémon objects
        pokemon_stats: Dictionary of Pokémon stats
        
    Returns:
        float: The mean BST
    """
    if not pokemon_list:
        return 300.0  # Default if empty list
        
    bst_values = [get_bst_for_species(pokemon.species, pokemon_stats) for pokemon in pokemon_list]
    return statistics.mean(bst_values)

def find_pokemon_in_bst_range(target_bst, pokemon_stats, preferred_type=None, existing_species=None):
    """
    Find a Pokémon within 10% of the target BST.
    
    Args:
        target_bst: The target BST to match
        pokemon_stats: Dictionary of Pokémon stats
        preferred_type: Optional preferred type
        existing_species: List of species IDs to exclude
        
    Returns:
        int: A suitable species ID
    """
    # Set BST range (within 10%)
    min_bst = target_bst * 0.9
    max_bst = target_bst * 1.1
    
    # Filter by type if specified
    valid_species = []
    
    # Define type-specific pool first
    type_pool = None
    if preferred_type and preferred_type in COMMON_POKEMON:
        type_pool = COMMON_POKEMON[preferred_type]
    
    # Check all species in our pool
    for species_id, stats in pokemon_stats.items():
        # Skip existing species
        if existing_species and species_id in existing_species:
            continue
            
        # Calculate BST
        bst = calculate_bst(stats)
        
        # Check if within range
        if min_bst <= bst <= max_bst:
            # If we have a type preference and this species is in our type pool, prioritize it
            if type_pool and species_id in type_pool:
                valid_species.append((species_id, 2))  # Priority 2 for type match + BST match
            else:
                valid_species.append((species_id, 1))  # Priority 1 for BST match only
    
    # If we found type matches, prioritize those
    priority_2 = [sid for sid, priority in valid_species if priority == 2]
    if priority_2:
        return random.choice(priority_2)
    
    # Otherwise use any BST match
    priority_1 = [sid for sid, priority in valid_species if priority == 1]
    if priority_1:
        return random.choice(priority_1)
    
    # Fallback: if no good matches, just pick from type pool or normal pool
    if type_pool:
        return random.choice(type_pool)
    return random.choice(COMMON_POKEMON["Normal"])

if __name__ == "__main__":
    sys.exit(main())
