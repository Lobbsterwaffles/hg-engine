#!/usr/bin/env python3

"""
Pokémon Names

This module reads Pokémon names directly from the text files generated during ROM building.
It's used by the randomizer to show Pokémon names in the log file.
"""

import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Cache for Pokémon names loaded from the text file
# We'll populate this when the module is first imported
POKEMON_NAMES = {}

def load_pokemon_names_from_file():
    """
    Load Pokémon names from the text file.
    
    Returns:
        Dictionary mapping Pokémon IDs to their names
    """
    names = {}
    
    # Path to the text file with Pokémon names
    base_dir = os.path.dirname(os.path.abspath(__file__))
    text_file = os.path.join(base_dir, "build", "rawtext", "237.txt")
    
    if not os.path.exists(text_file):
        logger.warning(f"Pokémon names file not found at {text_file}")
        logger.warning("Make sure to build the ROM first to generate text files")
        return names
    
    try:
        with open(text_file, "r", encoding="utf-8") as f:
            # Read all lines
            lines = f.readlines()
            
            # Each line in the file represents a Pokémon name
            # Line 1 (index 0) should be Pokémon #1 (Bulbasaur)
            for line_num, line in enumerate(lines):
                name = line.strip()
                if name:  # Skip empty lines
                    # The Pokémon ID is the line number + 1
                    pokemon_id = line_num + 1
                    names[pokemon_id] = name.upper()
        
        logger.info(f"Loaded {len(names)} Pokémon names from {text_file}")
    except Exception as e:
        logger.error(f"Error reading Pokémon names from {text_file}: {e}")
    
    return names

def get_pokemon_name(pokemon_id):
    """
    Get a Pokémon's name by its ID number.
    
    Args:
        pokemon_id: The ID number of the Pokémon
        
    Returns:
        The name of the Pokémon, or a formatted placeholder if not found
    """
    # In the hg-engine format, the Pokémon ID is a 16-bit number where:
    # - Lower 11 bits (0-2047): Pokémon species ID
    # - Upper 5 bits: Form information
    
    # First try the exact ID
    if pokemon_id in POKEMON_NAMES:
        return POKEMON_NAMES[pokemon_id]
    
    # Try masking out form bits to get the base species ID
    # 0x7FF = binary 0000 0111 1111 1111 (11 bits set to 1)
    base_species_id = pokemon_id & 0x7FF
    
    # If the base ID is different and exists in our names
    if base_species_id != pokemon_id and base_species_id in POKEMON_NAMES:
        # Get the form number (upper 5 bits)
        form_number = (pokemon_id >> 11) & 0x1F
        
        # Different form numbers might mean different things
        if form_number == 1:
            # Form 1 is often the shiny variant
            return f"SHINY {POKEMON_NAMES[base_species_id]}"
        elif form_number == 2:
            # Form 2 might be a regional form or gender variant
            return f"ALT {POKEMON_NAMES[base_species_id]}"
        else:
            # Other forms - just show the form number
            return f"{POKEMON_NAMES[base_species_id]} (FORM {form_number})"
    
    # If the ID is very high, it might be a custom or added Pokémon
    if base_species_id > 493 and base_species_id < 1000:
        return f"EXTRA-{base_species_id}"
    
    # If we can't find a name, return a placeholder with the ID
    return f"POKÉMON-{pokemon_id}"

# Load Pokémon names when this module is imported
POKEMON_NAMES = load_pokemon_names_from_file()

# If we couldn't load any names, log a warning
if not POKEMON_NAMES:
    logger.warning("No Pokémon names were loaded. Randomizer will use placeholder names.")
    logger.warning("Run 'make' in the project directory to build the ROM and generate text files.")
