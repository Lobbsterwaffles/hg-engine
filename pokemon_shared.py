"""
Shared Pokemon data and utilities for randomizers.
This module contains data structures and functions that can be reused across
different randomization passes.
"""

from construct import *
import ndspy.rom
import ndspy.narc

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

# Pokémon mondata structure based on macros.s
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
    # Base experience (1 byte)
    "base_exp" / Int8ul,
    # EV yields (2 bytes as halfword with bit fields)
    "ev_yields"
    / BitStruct(
        "hp_yield" / BitsInteger(2),
        "attack_yield" / BitsInteger(2),
        "defense_yield" / BitsInteger(2),
        "speed_yield" / BitsInteger(2),
        "sp_attack_yield" / BitsInteger(2),
        "sp_defense_yield" / BitsInteger(2),
        Padding(4),  # Remaining 4 bits
    ),
    # Items (4 bytes)
    "item1" / Int16ul,
    "item2" / Int16ul,
    # Gender ratio (1 byte)
    "gender_ratio" / Int8ul,
    # Egg cycles (1 byte)
    "egg_cycles" / Int8ul,
    # Base friendship (1 byte)
    "base_friendship" / Int8ul,
    # Growth rate (1 byte)
    "growth_rate" / Int8ul,
    # Egg groups (2 bytes)
    "egg_group1" / Int8ul,
    "egg_group2" / Int8ul,
    # Abilities (2 bytes)
    "ability1" / Int8ul,
    "ability2" / Int8ul,
    # Run chance (1 byte)
    "run_chance" / Int8ul,
    # Color and flip (1 byte with bit field)
    "color_flip" / BitStruct("color" / BitsInteger(7), "flip" / Flag),
    # TM data (18 bytes total)
    Padding(2),  # padding halfword
    "tm_data1" / Int32ul,
    "tm_data2" / Int32ul,
    "tm_data3" / Int32ul,
    "tm_data4" / Int32ul,
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
    
    # Load and cache the data
    with open("build/rawtext/237.txt", "r", encoding="utf-8") as f:
        names = [line.strip() for line in f.readlines()]
    
    _pokemon_names_cache = names
    return names


def find_replacements(mon, mondata, bstrmin, bstrmax):
    """Find suitable replacement Pokemon within BST range, excluding special Pokemon."""
    bstmin = mon.bst * bstrmin
    bstmax = mon.bst * bstrmax
    # Return indices of suitable replacements, excluding special Pokemon
    return [i for i, r in enumerate(mondata) if bstmin <= r.bst <= bstmax and i not in SPECIAL_POKEMON]
