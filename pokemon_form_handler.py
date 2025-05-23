#!/usr/bin/env python3

"""
Pokémon Form Handler

This module provides a practical approach to handling Pokémon forms in the HG Engine.
It creates a mapping of known alternate forms and provides functions to work with them.
"""

import logging

# Set up logging
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# FORM HANDLING APPROACH:
# -------------------------------------------------------------------------
# In the HG Engine, Pokémon forms are stored as unique species IDs
# (not as bitfields). The table in PokeFormDataTbl.c defines which forms
# belong to which base species.
#
# For randomization purposes, we need to:
# 1. Identify if a Pokémon ID represents a form variant
# 2. Find its base species
# 3. When randomizing, replace it with a form of the new base species
# -------------------------------------------------------------------------

# A simplified map of known form Pokémon to their base species
# Format: {form_pokemon_id: base_pokemon_id}
# This can be expanded manually as needed
FORM_TO_BASE = {
    # Mega Evolutions
    # Venusaur and Mega Venusaur
    3: 3,  # Normal Venusaur
    1000: 3,  # Mega Venusaur
    
    # Charizard and its forms
    6: 6,  # Normal Charizard
    1001: 6,  # Mega Charizard X
    1002: 6,  # Mega Charizard Y
    
    # Blastoise
    9: 9,  # Normal Blastoise
    1003: 9,  # Mega Blastoise
    
    # Regional Forms - adding some common ones
    # Alolan Variants
    19: 19,  # Normal Rattata
    830: 19,  # Alolan Rattata
    
    26: 26,  # Normal Raichu
    831: 26,  # Alolan Raichu
    
    27: 27,  # Normal Sandshrew
    832: 27,  # Alolan Sandshrew
    
    28: 28,  # Normal Sandslash
    833: 28,  # Alolan Sandslash
    
    37: 37,  # Normal Vulpix
    834: 37,  # Alolan Vulpix
    
    38: 38,  # Normal Ninetales
    835: 38,  # Alolan Ninetales
    
    # Galarian Forms
    52: 52,  # Normal Meowth
    860: 52,  # Galarian Meowth
    
    77: 77,  # Normal Ponyta
    861: 77,  # Galarian Ponyta
    
    78: 78,  # Normal Rapidash
    862: 78,  # Galarian Rapidash
    
    83: 83,  # Normal Farfetch'd
    865: 83,  # Galarian Farfetch'd
    
    110: 110,  # Normal Weezing
    866: 110,  # Galarian Weezing
    
    # Special Forms
    479: 479,  # Normal Rotom
    580: 479,  # Rotom Heat
    581: 479,  # Rotom Wash
    582: 479,  # Rotom Frost
    583: 479,  # Rotom Fan
    584: 479,  # Rotom Mow
    
    # Deoxys Forms
    386: 386,  # Normal Deoxys
    410: 386,  # Attack Deoxys
    411: 386,  # Defense Deoxys
    412: 386,  # Speed Deoxys
    
    # Giratina Forms
    487: 487,  # Altered Giratina
    650: 487,  # Origin Giratina
    
    # Shaymin Forms
    492: 492,  # Land Shaymin
    651: 492,  # Sky Shaymin
    
    # Arceus Forms - treat all as same base species
    493: 493,  # Normal Arceus
    # 494-512 are all Arceus forms
}

# Add more Arceus forms
for i in range(494, 513):
    FORM_TO_BASE[i] = 493

# A reverse mapping for convenience - base species to list of forms
BASE_TO_FORMS = {}
for form_id, base_id in FORM_TO_BASE.items():
    if base_id not in BASE_TO_FORMS:
        BASE_TO_FORMS[base_id] = []
    BASE_TO_FORMS[base_id].append(form_id)

def is_form_pokemon(pokemon_id):
    """
    Check if a Pokémon ID represents a form variant
    
    Args:
        pokemon_id (int): The Pokémon ID to check
        
    Returns:
        bool: True if this is a form variant, False otherwise
    """
    # A Pokémon is a form if it's in our mapping and not a base species
    return pokemon_id in FORM_TO_BASE and FORM_TO_BASE[pokemon_id] != pokemon_id

def get_base_pokemon(pokemon_id):
    """
    Get the base Pokémon ID for any Pokémon (form or base)
    
    Args:
        pokemon_id (int): The Pokémon ID to check
        
    Returns:
        int: The base Pokémon ID (or the same ID if already a base Pokémon)
    """
    # If it's a known form, return its base species
    if pokemon_id in FORM_TO_BASE:
        return FORM_TO_BASE[pokemon_id]
    # Otherwise, it's already a base species or an unknown Pokémon
    return pokemon_id

def get_form_index(pokemon_id):
    """
    Get the form index (position in the form list) for a Pokémon
    
    Args:
        pokemon_id (int): The Pokémon ID to check
        
    Returns:
        int: The form index (0 for base form, 1+ for alternate forms)
              or 0 if not a known form
    """
    # If it's not a known Pokémon, return 0 (base form)
    if pokemon_id not in FORM_TO_BASE:
        return 0
        
    base_id = FORM_TO_BASE[pokemon_id]
    
    # If it's a base form itself, return 0
    if pokemon_id == base_id:
        return 0
        
    # Find its position in the form list
    if base_id in BASE_TO_FORMS and pokemon_id in BASE_TO_FORMS[base_id]:
        forms = BASE_TO_FORMS[base_id]
        # Sort forms to ensure consistent ordering
        forms.sort()
        try:
            # Add 1 because 0 is the base form
            return forms.index(pokemon_id) + 1
        except ValueError:
            return 0
    return 0

def get_corresponding_form(original_pokemon_id, new_base_pokemon_id):
    """
    When replacing a Pokémon with another, get the corresponding form
    
    Args:
        original_pokemon_id (int): The original Pokémon ID
        new_base_pokemon_id (int): The new base Pokémon ID
        
    Returns:
        int: The corresponding form of the new Pokémon,
             or just the new base Pokémon if no matching form exists
    """
    # Get the form index of the original Pokémon
    form_index = get_form_index(original_pokemon_id)
    
    # If it's not a form (index 0), just return the new base Pokémon
    if form_index == 0:
        return new_base_pokemon_id
        
    # Get the base ID of the new Pokémon
    new_base_id = get_base_pokemon(new_base_pokemon_id)
    
    # Check if the new base Pokémon has forms
    if new_base_id in BASE_TO_FORMS:
        forms = BASE_TO_FORMS[new_base_id]
        forms.sort()  # Ensure consistent ordering
        
        # If there are enough forms, return the corresponding one
        if form_index <= len(forms):
            return forms[form_index - 1]  # -1 because form_index starts at 1
    
    # If we can't find a corresponding form, just return the base form
    return new_base_pokemon_id

# Test the functionality if this file is run directly
if __name__ == "__main__":
    # Set up console logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test some examples
    test_pokemon = [
        3,    # Venusaur (base)
        1000, # Mega Venusaur (form)
        6,    # Charizard (base)
        1001, # Mega Charizard X (form)
        1002, # Mega Charizard Y (form)
        25,   # Pikachu (not in our form mapping)
        832,  # Alolan Sandshrew (form)
        27,   # Sandshrew (base)
    ]
    
    print("Testing form detection:")
    for poke_id in test_pokemon:
        is_form = is_form_pokemon(poke_id)
        base_id = get_base_pokemon(poke_id)
        form_idx = get_form_index(poke_id)
        print(f"Pokémon #{poke_id}: Is form? {is_form}, Base: #{base_id}, Form index: {form_idx}")
    
    print("\nTesting form correspondence:")
    # Test replacing Mega Charizard X with a form of Venusaur
    original = 1001  # Mega Charizard X
    new_base = 3      # Venusaur
    new_form = get_corresponding_form(original, new_base)
    print(f"Replacing #{original} with a form of #{new_base} gives: #{new_form}")
    
    # Test replacing Alolan Sandshrew with a form of Vulpix
    original = 832  # Alolan Sandshrew
    new_base = 37   # Vulpix
    new_form = get_corresponding_form(original, new_base)
    print(f"Replacing #{original} with a form of #{new_base} gives: #{new_form}")
