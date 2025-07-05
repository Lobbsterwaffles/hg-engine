#!/usr/bin/env python3
"""
Generates pre-computed lists of special Pokémon (pivots, fulcrums, mimics) for the randomizer.

This script reads the raw data files for special Pokémon and converts them into JSON format
for faster access during randomization.
"""

import json
import os
import re
from typing import Dict, List, Set, Optional

def read_pivot_data(base_path=".") -> Dict[str, List[int]]:
    """Read pivot Pokémon data from file."""
    pivot_path = os.path.join(base_path, "data", "pivots.txt")
    print(f"Reading pivot data from {pivot_path}")
    
    # Initialize with both naming formats for compatibility
    pivot_data = {}
    current_type = None
    
    try:
        with open(pivot_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Check if this is a type section header
                if line.startswith("[") and line.endswith("]"):
                    # Extract type name from section header
                    type_name = line[1:-1]  # Remove brackets
                    
                    # Store both with and without TYPE_ prefix for compatibility
                    clean_type = type_name.replace("TYPE_", "") if type_name.startswith("TYPE_") else type_name
                    standard_type = clean_type
                    prefixed_type = f"TYPE_{clean_type}"
                    
                    # Initialize both key formats
                    pivot_data[standard_type] = []
                    pivot_data[prefixed_type] = []
                    current_type = type_name
                else:
                    # Try to extract Pokémon ID
                    try:
                        pokemon_id = int(line)
                        if current_type:
                            # Get clean type name
                            clean_type = current_type.replace("TYPE_", "") if current_type.startswith("TYPE_") else current_type
                            
                            # Add to both key formats
                            pivot_data[clean_type].append(pokemon_id)
                            pivot_data[f"TYPE_{clean_type}"].append(pokemon_id)
                    except ValueError:
                        print(f"Warning: Could not parse pivot ID: {line}")
        
        # Count entries for each type
        print("Loaded pivot Pokémon data:")
        for type_name, pokemon_ids in pivot_data.items():
            print(f"  {type_name}: {len(pokemon_ids)} Pokémon")
        
        return pivot_data
    
    except FileNotFoundError:
        print(f"Warning: Pivot data file not found at {pivot_path}")
        return {}

def read_fulcrum_data(base_path=".") -> Dict[str, List[int]]:
    """Read fulcrum Pokémon data from file."""
    fulcrum_path = os.path.join(base_path, "data", "fulcrums.txt")
    print(f"Reading fulcrum data from {fulcrum_path}")
    
    # Initialize with both naming formats for compatibility
    fulcrum_data = {}
    current_type = None
    
    try:
        with open(fulcrum_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Check if this is a type section header
                if line.startswith("[") and line.endswith("]"):
                    # Extract type name from section header
                    type_name = line[1:-1]  # Remove brackets
                    
                    # Store both with and without TYPE_ prefix for compatibility
                    clean_type = type_name.replace("TYPE_", "") if type_name.startswith("TYPE_") else type_name
                    standard_type = clean_type
                    prefixed_type = f"TYPE_{clean_type}"
                    
                    # Initialize both key formats
                    fulcrum_data[standard_type] = []
                    fulcrum_data[prefixed_type] = []
                    current_type = type_name
                else:
                    # Try to extract Pokémon ID
                    try:
                        pokemon_id = int(line)
                        if current_type:
                            # Get clean type name
                            clean_type = current_type.replace("TYPE_", "") if current_type.startswith("TYPE_") else current_type
                            
                            # Add to both key formats
                            fulcrum_data[clean_type].append(pokemon_id)
                            fulcrum_data[f"TYPE_{clean_type}"].append(pokemon_id)
                    except ValueError:
                        print(f"Warning: Could not parse fulcrum ID: {line}")
        
        # Count entries for each type
        print("Loaded fulcrum Pokémon data:")
        for type_name, pokemon_ids in fulcrum_data.items():
            print(f"  {type_name}: {len(pokemon_ids)} Pokémon")
        
        return fulcrum_data
    
    except FileNotFoundError:
        print(f"Warning: Fulcrum data file not found at {fulcrum_path}")
        return {}

def read_mimic_data(base_path=".") -> Dict[str, List[int]]:
    """Read mimic Pokémon data from file."""
    mimic_path = os.path.join(base_path, "data", "type_mimics_with_prevos.txt")
    print(f"Reading mimic data from {mimic_path}")
    
    # Initialize with both naming formats for compatibility
    mimic_data = {}
    current_type = None
    
    try:
        with open(mimic_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Check if this is a type section header
                if line.startswith("[") and line.endswith("]"):
                    # Extract type name from section header
                    type_name = line[1:-1]  # Remove brackets
                    
                    # Store both with and without TYPE_ prefix for compatibility
                    clean_type = type_name.replace("TYPE_", "") if type_name.startswith("TYPE_") else type_name
                    standard_type = clean_type
                    prefixed_type = f"TYPE_{clean_type}"
                    
                    # Initialize both key formats
                    mimic_data[standard_type] = []
                    mimic_data[prefixed_type] = []
                    current_type = type_name
                else:
                    # Try to extract Pokémon ID
                    try:
                        # Handle either just ID numbers or ID:Name format
                        if ":" in line:
                            pokemon_id = int(line.split(":")[0])
                        else:
                            pokemon_id = int(line)
                            
                        if current_type:
                            # Get clean type name
                            clean_type = current_type.replace("TYPE_", "") if current_type.startswith("TYPE_") else current_type
                            
                            # Add to both key formats
                            mimic_data[clean_type].append(pokemon_id)
                            mimic_data[f"TYPE_{clean_type}"].append(pokemon_id)
                    except ValueError:
                        print(f"Warning: Could not parse mimic ID: {line}")
        
        # Count entries for each type
        print("Loaded mimic Pokémon data:")
        for type_name, pokemon_ids in mimic_data.items():
            print(f"  {type_name}: {len(pokemon_ids)} Pokémon")
        
        return mimic_data
    
    except FileNotFoundError:
        print(f"Warning: Mimic data file not found at {mimic_path}")
        return {}

def generate_special_pokemon_lists(base_path="."):
    """Generate pre-computed lists of special Pokémon for the randomizer to use."""
    # Create output directory
    special_lists_dir = os.path.join(base_path, "data", "special_lists")
    os.makedirs(special_lists_dir, exist_ok=True)
    
    # Generate pivot lists
    print("\nGenerating pivot lists...")
    pivot_data = read_pivot_data(base_path)
    
    # Save pivot lists
    pivot_path = os.path.join(special_lists_dir, "pivot_lists.json")
    with open(pivot_path, "w") as f:
        json.dump(pivot_data, f, indent=2)
    print(f"Saved pivot lists to {pivot_path}")
    
    # Generate fulcrum lists
    print("\nGenerating fulcrum lists...")
    fulcrum_data = read_fulcrum_data(base_path)
    
    # Save fulcrum lists
    fulcrum_path = os.path.join(special_lists_dir, "fulcrum_lists.json")
    with open(fulcrum_path, "w") as f:
        json.dump(fulcrum_data, f, indent=2)
    print(f"Saved fulcrum lists to {fulcrum_path}")
    
    # Generate mimic lists
    print("\nGenerating mimic lists...")
    mimic_data = read_mimic_data(base_path)
    
    # Save mimic lists
    mimic_path = os.path.join(special_lists_dir, "mimic_lists.json")
    with open(mimic_path, "w") as f:
        json.dump(mimic_data, f, indent=2)
    print(f"Saved mimic lists to {mimic_path}")
    
    print("\nSpecial Pokémon lists generated successfully!")
    print("These lists can be used by the randomizer for faster special Pokémon selection.")

if __name__ == "__main__":
    generate_special_pokemon_lists()
