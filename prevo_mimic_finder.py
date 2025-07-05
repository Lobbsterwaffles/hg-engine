#!/usr/bin/env python3

"""
Pre-Evolution Mimic Finder

This script reads Pokemon type mimics from data/type_mimics.txt and evolution data from
armips/data/evodata.s, then adds pre-evolved forms of Pokemon to their respective
type mimic categories.

For example, if Ninetales is listed under [GHOST], the script will find that Vulpix
evolves into Ninetales and add Vulpix to the [GHOST] section as well.
"""

import re
import os
from collections import defaultdict

# File paths
TYPE_MIMICS_FILE = "data/type_mimics.txt"
EVODATA_FILE = "armips/data/evodata.s"
OUTPUT_FILE = "data/type_mimics_with_prevos.txt"

def read_evodata():
    """
    Read evolution data from evodata.s and build a dictionary mapping
    evolved forms to their pre-evolved forms.
    """
    print("Reading evolution data...")
    evolution_map = {}  # Maps evolved form to its pre-evolution
    
    # To track current species being processed
    current_species = None
    
    try:
        with open(EVODATA_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Find species being defined
                species_match = re.match(r'evodata\s+(SPECIES_\w+)', line)
                if species_match:
                    current_species = species_match.group(1)
                    
                    # Look ahead for evolution entries
                    j = i + 1
                    while j < len(lines) and 'terminateevodata' not in lines[j]:
                        evo_line = lines[j].strip()
                        evo_match = re.search(r'evolution\s+(EVO_\w+),\s+\d+,\s+(SPECIES_\w+)', evo_line)
                        if evo_match:
                            evo_type = evo_match.group(1)
                            evolved_species = evo_match.group(2)
                            
                            # Skip if it's SPECIES_NONE or EVO_NONE
                            if evolved_species != "SPECIES_NONE" and evo_type != "EVO_NONE":
                                # The evolved species has current_species as its pre-evolution
                                evolution_map[evolved_species] = current_species
                                print(f"Found: {current_species} evolves into {evolved_species}")
                        j += 1
    
    except Exception as e:
        print(f"Error reading evolution data: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"Found {len(evolution_map)} evolution relationships")
    return evolution_map

def read_type_mimics():
    """
    Read type mimics from type_mimics.txt and organize by type.
    """
    print("Reading type mimics...")
    mimics_by_type = {}
    current_type = None
    
    try:
        with open(TYPE_MIMICS_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Find type headers like [TYPE_NORMAL] or [WATER]
                type_match = re.match(r'\[(TYPE_\w+|[A-Z]+)\]', line)
                if type_match:
                    current_type = type_match.group(1)
                    mimics_by_type[current_type] = set()
                elif current_type and line.startswith("SPECIES_"):
                    # Add the species to the current type
                    mimics_by_type[current_type].add(line)
    
    except Exception as e:
        print(f"Error reading type mimics: {e}")
    
    print(f"Found {len(mimics_by_type)} type categories")
    return mimics_by_type

def add_pre_evolutions(mimics_by_type, evolution_map):
    """
    Add pre-evolutions to each type category.
    """
    print("Finding pre-evolutions...")
    pre_evos_added = 0
    
    # Create a new dictionary to store the updated mimics
    updated_mimics = {}
    
    for type_name, species_list in mimics_by_type.items():
        # Create a new set for this type that includes existing Pokemon and their pre-evos
        updated_species = set(species_list)
        
        # For each species in this type category
        for species in species_list:
            # Check if it has a pre-evolution
            current = species
            while current in evolution_map:
                pre_evo = evolution_map[current]
                if pre_evo not in updated_species:
                    updated_species.add(pre_evo)
                    pre_evos_added += 1
                    print(f"Added {pre_evo} as pre-evolution of {current} to {type_name}")
                # Check if the pre-evolution itself has a pre-evolution
                current = pre_evo
        
        # Sort the updated species for this type
        updated_mimics[type_name] = sorted(updated_species)
    
    print(f"Added {pre_evos_added} pre-evolutions to the mimics list")
    return updated_mimics

def write_updated_mimics(updated_mimics):
    """
    Write the updated mimics to a new file.
    """
    print(f"Writing updated mimics to {OUTPUT_FILE}...")
    
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # Write header
            f.write("# Type Mimic Pokémon by Type (with pre-evolutions added)\n")
            f.write("# Format: [TYPE_NAME]\n")
            f.write("# Each Pokémon (with SPECIES_ prefix) on a new line under its type\n")
            f.write("# These are Pokémon that aren't of the listed type, but are thematically similar\n\n")
            
            # Write each type section
            for type_name, species_list in sorted(updated_mimics.items()):
                f.write(f"[{type_name}]\n")
                for species in species_list:
                    f.write(f"{species}\n")
                f.write("\n")
    
    except Exception as e:
        print(f"Error writing updated mimics: {e}")

def main():
    """
    Main function to run the script.
    """
    print("Starting pre-evolution mimic finder...")
    
    # Read evolution data
    evolution_map = read_evodata()
    
    # Read type mimics
    mimics_by_type = read_type_mimics()
    
    # Add pre-evolutions
    updated_mimics = add_pre_evolutions(mimics_by_type, evolution_map)
    
    # Write updated mimics
    write_updated_mimics(updated_mimics)
    
    print("Done! Updated mimics written to", OUTPUT_FILE)

if __name__ == "__main__":
    main()
