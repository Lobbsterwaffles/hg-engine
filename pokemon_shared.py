"""
Shared Pokemon data and utilities for randomizers.
This module contains data structures and functions that can be reused across
different randomization passes.
"""

from construct import *
import ndspy.rom
import ndspy.narc
import os

# List of Pokémon that should not be replaced when randomizing
SPECIAL_POKEMON = set(
    [
        # Legendaries and special Pokémon
        150,
        151,  # Mewtwo, Mew
        243,
        244,
        245,  # Raikou, Entei, Suicune
        249,
        250,
        251,  # Lugia, Ho-Oh, Celebi
        377,
        378,
        379,
        380,
        381,
        382,
        383,
        384,
        385,
        386,  # Gen 3 legendaries
        480,
        481,
        482,
        483,
        484,
        485,
        486,
        487,
        488,
        489,
        490,
        491,
        492,
        493,
        494,  # Gen 4 legendaries
    ]
)

# Cache for expensive data loading operations
_pokemon_names_cache = None
_mondata_cache = None
_blacklist_cache = None  # Cache for blacklist

# Pokémon mondata structure based on ROM data (26 bytes total)
mondata_struct = Struct(
    # Base stats (6 bytes)
    "hp" / Int8ul,
    "attack" / Int8ul,
    "defense" / Int8ul,
    "speed" / Int8ul,
    "sp_attack" / Int8ul,
    "sp_defense" / Int8ul,
    # Types (2 bytes)
    "type1" / Int8ul,
    "type2" / Int8ul,
    # Catch rate (1 byte)
    "catch_rate" / Int8ul,
    # Base experience or padding (1 byte)
    "base_exp" / Int8ul,
    # EV yields or item flags (2 bytes)
    "ev_yields" / Int16ul,
    # Items (4 bytes) - may be differently formatted in this ROM
    "item1" / Int16ul,
    "item2" / Int16ul,
    # Gender, egg cycles, growth rate (3 bytes)
    "gender_ratio" / Int8ul,
    "egg_cycles" / Int8ul,
    "base_friendship" / Int8ul,
    # Growth and egg info (3 bytes)
    "growth_rate" / Int8ul,
    "egg_group1" / Int8ul,
    "egg_group2" / Int8ul,
    # Abilities (2 bytes)
    "ability1" / Int8ul,
    "ability2" / Int8ul,
    # Additional data (2 bytes)
    "additional1" / Int8ul,
    "additional2" / Int8ul
)


def parse_mondata(data):
    """Parse mondata from binary data and add calculated BST field."""
    mon = mondata_struct.parse(data)
    # Add BST as a calculated field
    mon.bst = (
        mon.hp + mon.attack + mon.defense + mon.speed + mon.sp_attack + mon.sp_defense
    )
    return mon


def build_mondata(mondata_dict):
    """Build binary mondata from dictionary."""
    return mondata_struct.build(mondata_dict)


def read_mondata(rom, names):
    """Read all Pokemon mondata from ROM and attach names. Results are cached."""
    global _mondata_cache
    
    # Return cached data if available
    if _mondata_cache is not None:
        return _mondata_cache
    
    # Load and cache the data
    all = []
    narc_file_id = rom.filenames.idOf("a/0/0/2")
    encounter_narc = rom.files[narc_file_id]
    narc_data = ndspy.narc.NARC(encounter_narc)
    for i, data in enumerate(narc_data.files):
        mon = parse_mondata(data)
        mon.name = names[i]
        all.append(mon)
    
    _mondata_cache = all
    return all


def read_pokemon_names(base_path):
    """Read Pokemon names from text file. Results are cached."""
    global _pokemon_names_cache
    
    # Return cached data if available
    if _pokemon_names_cache is not None:
        return _pokemon_names_cache
    
    # Define paths to try
    paths_to_try = [
        os.path.join(base_path, "build/rawtext/237.txt"),  # With base path
        "build/rawtext/237.txt",                          # Original path
        os.path.join(base_path, "data/pokemon_names.txt")   # Alternative path
    ]
    
    names = None
    used_path = None
    
    # Try each path until we find a valid file
    for path in paths_to_try:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    names = [line.strip() for line in f.readlines()]
                used_path = path
                print(f"Successfully loaded {len(names)} Pokémon names from {path}")
                break
        except Exception as e:
            print(f"Warning: Could not read Pokémon names from {path}: {e}")
    
    # If no file was found, create a basic set of names
    if names is None:
        print("Warning: No Pokémon name file found. Creating basic names.")
        names = ["-----"]
        # Add basic placeholder names for Pokémon 1-493 (Gen 1-4)
        for i in range(1, 494):
            names.append(f"SPECIES_{i}")
    
    _pokemon_names_cache = names
    return names


def read_blacklist(base_path="."):
    """Read Pokemon blacklist from file. Results are cached.
    
    The blacklist file can contain Pokemon names or IDs.
    Lines starting with # are ignored as comments.
    
    Args:
        base_path: Base directory path for the blacklist file
        
    Returns:
        set: Set of Pokemon IDs to exclude from randomization
    """
    global _blacklist_cache
    
    # Return cached data if available
    if _blacklist_cache is not None:
        return _blacklist_cache
    
    blacklist = set()
    blacklist_path = f"{base_path}/data/blacklist.txt"
    
    try:
        # Load Pokemon names to convert name entries to IDs
        names = read_pokemon_names(base_path)
        name_to_id = {name.lower(): i for i, name in enumerate(names)}
        
        # Read and process blacklist file
        if os.path.exists(blacklist_path):
            with open(blacklist_path, "r", encoding="utf-8") as f:
                for line in f:
                    # Remove comments
                    line = line.split('#', 1)[0].strip()
                    if not line:
                        continue
                        
                    # Try to parse as ID first
                    try:
                        pokemon_id = int(line)
                        blacklist.add(pokemon_id)
                    except ValueError:
                        # Not an ID, try as name
                        name = line.lower()
                        if name in name_to_id:
                            blacklist.add(name_to_id[name])
                        else:
                            print(f"Warning: Unknown Pokémon in blacklist: {line}")
            
            print(f"Loaded {len(blacklist)} Pokémon from blacklist")
        else:
            print(f"No blacklist file found at {blacklist_path}, using empty blacklist")
    except Exception as e:
        print(f"Error reading blacklist: {e}")
    
    # Cache the results
    _blacklist_cache = blacklist
    return blacklist

def find_replacements(mon, mondata, bstrmin, bstrmax, base_path="."):
    """Find suitable replacement Pokemon within BST range, excluding special and blacklisted Pokemon.
    
    Args:
        mon: Pokemon to find replacements for
        mondata: All Pokemon data
        bstrmin: Minimum BST ratio (e.g., 0.9 for 90%)
        bstrmax: Maximum BST ratio (e.g., 1.1 for 110%)
        base_path: Base directory path for the blacklist file
        
    Returns:
        list: Indices of suitable replacement Pokemon
    """
    bstmin = mon.bst * bstrmin
    bstmax = mon.bst * bstrmax
    
    # Get blacklisted Pokemon
    blacklist = read_blacklist(base_path)
    
    # Combine SPECIAL_POKEMON and blacklist for exclusions
    excluded = SPECIAL_POKEMON.union(blacklist)
    
    # Return indices of suitable replacements, excluding:
    # 1. Special and blacklisted Pokemon
    # 2. Pokemon with placeholder names ("-----")
    return [i for i, r in enumerate(mondata) 
            if bstmin <= r.bst <= bstmax 
            and i not in excluded
            and r.name != "-----"]
