#!/usr/bin/env python3
"""
Update Empty Egg Moves Script

This script checks the modern_egg_moves.json file for Pokemon with empty egg move lists
and tries to update them by looking at Generation 8 and 7 egg moves if Generation 9 
doesn't have any.
"""

import json
import os
import time
import sys
from egg_move_scraper import process_pokemon
from download_pokemon_html import download_pokemon_html

# File containing the modern egg moves
EGG_MOVES_FILE = "data/modern_egg_moves.json"

def load_egg_moves():
    """
    Load the current egg moves JSON file.
    
    Returns:
        Dictionary mapping Pokemon species to their egg moves
    """
    # Check if the file exists
    if not os.path.exists(EGG_MOVES_FILE):
        print(f"Error: {EGG_MOVES_FILE} does not exist!")
        return {}
    
    # Load the JSON data
    with open(EGG_MOVES_FILE, "r") as f:
        egg_moves = json.load(f)
    
    print(f"Loaded egg moves for {len(egg_moves)} Pokemon")
    return egg_moves

def find_empty_egg_move_lists(egg_moves):
    """
    Find Pokemon with empty egg move lists.
    
    Args:
        egg_moves: Dictionary mapping Pokemon species to their egg moves
        
    Returns:
        List of Pokemon species with empty egg move lists
    """
    empty_lists = []
    
    for species, moves in egg_moves.items():
        if not moves:  # If the moves list is empty
            empty_lists.append(species)
    
    print(f"Found {len(empty_lists)} Pokemon with empty egg move lists")
    return empty_lists

def convert_species_to_pokemon_name(species):
    """
    Convert a species name (like SPECIES_PIKACHU) to a Pokemon name for the URL (like pikachu).
    
    Args:
        species: The species name (e.g., "SPECIES_PIKACHU")
        
    Returns:
        The Pokemon name for the URL (e.g., "pikachu")
    """
    # Remove "SPECIES_" prefix
    if species.startswith("SPECIES_"):
        name = species[8:]
    else:
        name = species
    
    # Handle special cases (same ones from egg_move_scraper.py)
    special_cases = {
        "NIDORAN_F": "nidoran-f",
        "NIDORAN_M": "nidoran-m",
        "MR_MIME": "mr-mime",
        "MIME_JR": "mime-jr",
        "TAPU_KOKO": "tapu-koko",
        "TAPU_LELE": "tapu-lele", 
        "TAPU_BULU": "tapu-bulu",
        "TAPU_FINI": "tapu-fini",
        "TYPE_NULL": "type-null",
        "JANGMO_O": "jangmo-o",
        "HAKAMO_O": "hakamo-o",
        "KOMMO_O": "kommo-o",
        "WO_CHIEN": "wo-chien",
        "CHIEN_PAO": "chien-pao",
        "TING_LU": "ting-lu",
        "CHI_YU": "chi-yu",
    }
    
    if name in special_cases:
        return special_cases[name]
    
    # Convert underscores to hyphens and lowercase
    return name.replace("_", "-").lower()

def update_empty_egg_moves():
    """
    Main function to update empty egg move lists.
    """
    # Load the current egg moves
    egg_moves = load_egg_moves()
    
    # Find Pokemon with empty egg move lists
    empty_lists = find_empty_egg_move_lists(egg_moves)
    
    if not empty_lists:
        print("No Pokemon with empty egg move lists found! All Pokemon have egg moves defined.")
        return
    
    # Ask user if they want to proceed
    total = len(empty_lists)
    print(f"\nFound {total} Pokemon with empty egg move lists.")
    print("This script will try to update them by looking at Gen 8 and Gen 7 egg moves.")
    print("This process may take a while, as it needs to download data for each Pokemon.")
    
    # Update the egg moves for each Pokemon
    updated_count = 0
    failed_count = 0
    
    for i, species in enumerate(empty_lists):
        # Convert the species name to a Pokemon name for the URL
        pokemon_name = convert_species_to_pokemon_name(species)
        
        print(f"\n[{i+1}/{total}] Processing {species} ({pokemon_name})...")
        
        # Try to update the egg moves
        try:
            success = process_pokemon(pokemon_name, EGG_MOVES_FILE)
            
            if success:
                updated_count += 1
            else:
                failed_count += 1
                
            # Sleep briefly to avoid overloading the server
            time.sleep(1)
        except Exception as e:
            print(f"Error processing {species}: {str(e)}")
            failed_count += 1
    
    # Print summary
    print("\n" + "=" * 50)
    print("UPDATE SUMMARY")
    print("=" * 50)
    print(f"Total Pokemon processed: {total}")
    print(f"Successfully updated: {updated_count}")
    print(f"Failed to update: {failed_count}")
    print("\nThe modern_egg_moves.json file has been updated.")
    print("You can now restart the Pokemon Set Builder to see the updated egg moves in the dropdown menus.")

if __name__ == "__main__":
    print("=" * 50)
    print("UPDATE EMPTY EGG MOVES")
    print("=" * 50)
    print("This script will update Pokemon with empty egg move lists")
    print("by looking at Gen 8 and Gen 7 egg moves if Gen 9 doesn't have any.")
    
    update_empty_egg_moves()
