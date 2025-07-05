#!/usr/bin/env python3

import os
import re

# This script analyzes pivot Pokémon based on pivots.txt and mondata.s

def load_pokemon_types_and_abilities(mondata_path):
    """Load Pokémon types and abilities from mondata.s file."""
    pokemon_data = {}
    
    print("Starting to parse mondata.s file...")
    with open(mondata_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Split file into Pokémon entries
    pokemon_blocks = re.split(r'\nmondata\s+', '\n' + content)
    if pokemon_blocks[0].strip() == '':
        pokemon_blocks.pop(0)
    
    # Process each block
    for block in pokemon_blocks:
        if not block.strip():
            continue
            
        # Extract species name
        species_match = re.match(r'(SPECIES_[^,\s]+)', block)
        if not species_match:
            continue
        
        species = species_match.group(1).strip()
        pokemon_info = {'types': None, 'abilities': []}
        
        # Extract types
        types_match = re.search(r'types\s+([^\n]+)', block)
        if types_match:
            type_line = types_match.group(1)
            type_values = []
            
            # Split by comma to get both type entries
            type_entries = type_line.split(',')
            
            for entry in type_entries:
                # Check if this is a conditional expression
                conditional_match = re.search(r'\([^)]+\)\s*\?\s*(TYPE_\w+)\s*:\s*(TYPE_\w+)', entry)
                if conditional_match:
                    # Use the first option from the conditional
                    type_values.append(conditional_match.group(1).strip())
                else:
                    # Try to find a direct TYPE_X pattern
                    direct_match = re.search(r'(TYPE_\w+)', entry)
                    if direct_match:
                        type_values.append(direct_match.group(1).strip())
            
            # Store the types if found
            if len(type_values) == 2:
                pokemon_info['types'] = tuple(type_values)
        
        # Extract abilities
        abilities_match = re.search(r'abilities\s+([^\n]+)', block)
        if abilities_match:
            abilities_line = abilities_match.group(1)
            
            # Extract all ability entries
            ability_entries = abilities_line.split(',')
            for entry in ability_entries:
                ability_match = re.search(r'(ABILITY_\w+)', entry)
                if ability_match:
                    pokemon_info['abilities'].append(ability_match.group(1).strip())
        
        # Store the Pokémon data if we have the required information
        if pokemon_info['types'] or pokemon_info['abilities']:
            pokemon_data[species] = pokemon_info
    
    print(f"Found {len(pokemon_data)} Pokémon with type/ability information")
    return pokemon_data

def load_pivot_combinations(pivot_path):
    """Load type and ability combinations from pivots.txt."""
    pivot_combinations = {}
    current_type = None
    
    print("Loading pivot combinations from pivots.txt...")
    with open(pivot_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
                
            # Check if this is a section header
            if line.startswith('[') and line.endswith(']'):
                current_type = line[1:-1]  # Remove brackets
                pivot_combinations[current_type] = []
            elif current_type is not None:
                # Handle ABILITY_ entries
                if line.startswith('ABILITY_'):
                    pivot_combinations[current_type].append(("ability", line))
                # Handle type combinations
                else:
                    types = [t.strip() for t in line.split(',')]
                    if len(types) == 1:  # Single type
                        pivot_combinations[current_type].append(("type", (types[0], types[0])))
                    elif len(types) == 2:  # Type combination
                        pivot_combinations[current_type].append(("type", (types[0], types[1])))
    
    print(f"Found {len(pivot_combinations)} type sections in pivots.txt")
    return pivot_combinations

def generate_output_file(pivot_combinations, pokemon_data, output_path):
    """Generate output file listing Pokémon by pivot combinations."""
    print("Generating output file...")
    
    # Create dictionaries to map combinations to Pokémon
    type_to_pokemon = {}
    ability_to_pokemon = {}
    
    # Map each Pokémon to its types and abilities
    for species, data in pokemon_data.items():
        # Map by types
        if data['types']:
            # Sort types to ensure consistent matching regardless of order
            sorted_types = tuple(sorted(data['types']))
            if sorted_types not in type_to_pokemon:
                type_to_pokemon[sorted_types] = []
            type_to_pokemon[sorted_types].append(species)
        
        # Map by abilities
        for ability in data['abilities']:
            if ability not in ability_to_pokemon:
                ability_to_pokemon[ability] = []
            ability_to_pokemon[ability].append(species)
    
    # Write output file
    with open(output_path, 'w', encoding='utf-8') as f:
        # For each main type section
        for main_type, combinations in pivot_combinations.items():
            f.write(f"[{main_type}]\n")
            
            # For each pivot combination under this type
            for combo_type, combo in combinations:
                if combo_type == "type":  # Type combination
                    # Normalize type order
                    sorted_combo = tuple(sorted(combo))
                    
                    # Get Pokémon with this type combination
                    pokemon_list = type_to_pokemon.get(sorted_combo, [])
                    
                    # Write the type combination header
                    if len(set(combo)) == 1:  # Single type
                        f.write(f"# {combo[0].replace('TYPE_', '')}\n")
                    else:  # Dual type
                        f.write(f"# {combo[0].replace('TYPE_', '')}/{combo[1].replace('TYPE_', '')}\n")
                    
                    # Write Pokémon list
                    if pokemon_list:
                        for species in sorted(pokemon_list):
                            f.write(f"{species}\n")
                    else:
                        f.write("# No Pokémon match this type combination\n")
                    
                    f.write("\n")
                    
                elif combo_type == "ability":  # Ability
                    ability = combo
                    
                    # Get Pokémon with this ability
                    pokemon_list = ability_to_pokemon.get(ability, [])
                    
                    # Write the ability header
                    f.write(f"# {ability}\n")
                    
                    # Write Pokémon list
                    if pokemon_list:
                        for species in sorted(pokemon_list):
                            f.write(f"{species}\n")
                    else:
                        f.write(f"# No Pokémon have the ability {ability}\n")
                    
                    f.write("\n")
            
            # Add extra line between main sections
            f.write("\n")
    
    print(f"Analysis complete! Output saved to {os.path.abspath(output_path)}")

def main():
    # Define file paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pivot_path = os.path.join(base_dir, 'data', 'pivots.txt')
    mondata_path = os.path.join(base_dir, 'armips', 'data', 'mondata.s')
    output_path = os.path.join(base_dir, 'data', 'pivot_analysis.txt')
    
    # Load pivot combinations from pivots.txt
    pivot_combinations = load_pivot_combinations(pivot_path)
    
    # Load Pokémon data from mondata.s
    pokemon_data = load_pokemon_types_and_abilities(mondata_path)
    
    # Generate the output file
    generate_output_file(pivot_combinations, pokemon_data, output_path)

if __name__ == "__main__":
    main()
