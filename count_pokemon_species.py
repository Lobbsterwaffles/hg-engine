#!/usr/bin/env python3

"""
Count Unique Pokémon Species in encounters.s

This script reads the encounters.s file and counts how many unique Pokémon 
species appear in it. It looks for 'pokemon SPECIES_X' and 'encounter SPECIES_X'
patterns to find all species.
"""

import os
import re
import sys

def count_species(file_path):
    """
    Count the unique Pokémon species in the encounters.s file.
    
    Args:
        file_path: Path to the encounters.s file
    
    Returns:
        A set of unique species names and the total count
    """
    # Read the file
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Look for both types of species references:
    # 1. pokemon SPECIES_XXX
    # 2. encounter SPECIES_XXX, level1, level2
    
    # Find all pokemon SPECIES_XXX patterns
    pokemon_pattern = r'pokemon\s+SPECIES_([A-Z0-9_\']+)'
    pokemon_matches = re.findall(pokemon_pattern, content)
    
    # Find all encounter SPECIES_XXX patterns
    encounter_pattern = r'encounter\s+SPECIES_([A-Z0-9_\']+)'
    encounter_matches = re.findall(encounter_pattern, content)
    
    # Combine the lists and count unique species
    all_species = pokemon_matches + encounter_matches
    unique_species = set(all_species)
    
    # Count occurrences of each species
    species_count = {}
    for species in all_species:
        if species in species_count:
            species_count[species] += 1
        else:
            species_count[species] = 1
    
    # Sort species by frequency (most common first)
    sorted_species = sorted(species_count.items(), key=lambda x: x[1], reverse=True)
    
    return unique_species, sorted_species, len(all_species)

def main():
    encounters_file = os.path.join("armips", "data", "encounters.s")
    
    # Make sure the file exists
    if not os.path.exists(encounters_file):
        print(f"Error: File not found: {encounters_file}")
        return 1
    
    # Count species
    unique_species, species_counts, total_occurrences = count_species(encounters_file)
    
    # Output results
    print("=" * 60)
    print(f"POKÉMON SPECIES ANALYSIS")
    print("=" * 60)
    print(f"Total unique species found: {len(unique_species)}")
    print(f"Total occurrences (including duplicates): {total_occurrences}")
    print()
    
    print("Top 20 most common species:")
    print("-" * 60)
    for i, (species, count) in enumerate(species_counts[:20]):
        print(f"{i+1:2d}. SPECIES_{species:15s}: {count:3d} occurrences")
    print()
    
    print("All unique species (alphabetical order):")
    print("-" * 60)
    # Sort and format for better readability
    sorted_unique = sorted(unique_species)
    for i, species in enumerate(sorted_unique):
        print(f"{i+1:3d}. SPECIES_{species}")
    
    # Save the results to a file
    with open("pokemon_species_analysis.txt", "w") as f:
        f.write("=" * 60 + "\n")
        f.write(f"POKÉMON SPECIES ANALYSIS\n")
        f.write("=" * 60 + "\n")
        f.write(f"Total unique species found: {len(unique_species)}\n")
        f.write(f"Total occurrences (including duplicates): {total_occurrences}\n\n")
        
        f.write("All unique species (alphabetical order):\n")
        f.write("-" * 60 + "\n")
        for i, species in enumerate(sorted_unique):
            f.write(f"{i+1:3d}. SPECIES_{species}\n")
        
        f.write("\n\nSpecies by frequency (most common first):\n")
        f.write("-" * 60 + "\n")
        for i, (species, count) in enumerate(species_counts):
            f.write(f"{i+1:3d}. SPECIES_{species:15s}: {count:3d} occurrences\n")
    
    print(f"\nDetailed analysis saved to: pokemon_species_analysis.txt")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
