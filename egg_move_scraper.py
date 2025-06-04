#!/usr/bin/env python3
"""
Pokemon Egg Move Scraper

This script downloads egg moves for a given Pokemon from PokemonDB
and outputs them in a format that can be used by the hg-engine project.
"""

import argparse
import json
import os
import sys
from download_pokemon_html import download_pokemon_html

# Global dictionary to store our results
# This will be structured like: {"SPECIES_POKEMON": ["MOVE_X", "MOVE_Y", ...]}
egg_moves_data = {}

def extract_egg_moves(soup, pokemon_name):
    """
    Extract egg moves from the BeautifulSoup object.
    
    Args:
        soup: BeautifulSoup object of the HTML
        pokemon_name: Name of the Pokemon to process
        
    Returns:
        A list of move names in the format "MOVE_NAME"
    """
    print(f"Extracting egg moves for {pokemon_name}...")
    
    # List to store egg moves
    egg_moves = []
    
    # Find the egg moves section
    # First look for the 'Egg moves' header
    egg_moves_header = soup.find('h3', string='Egg moves')
    
    # If we didn't find the header, the Pokemon might not have egg moves
    if not egg_moves_header:
        print(f"No egg moves section found for {pokemon_name}. It might not have egg moves in Gen 9.")
        return egg_moves
    
    # Find the table that follows the egg moves header
    # The table will be a sibling element after the header
    egg_moves_table = None
    current_element = egg_moves_header.next_sibling
    
    # Look for the table in the next few elements
    for _ in range(5):  # Check the next 5 elements
        if current_element and hasattr(current_element, 'name') and current_element.name == 'table':
            egg_moves_table = current_element
            break
        elif current_element:
            current_element = current_element.next_sibling
        else:
            break
    
    # If we didn't find the table, try a different approach
    if not egg_moves_table:
        # Try to find the table with class 'data-table'
        tables = soup.find_all('table', class_='data-table')
        for table in tables:
            # Check if this table is preceded by the egg moves header
            previous_header = table.find_previous('h3')
            if previous_header and previous_header.string == 'Egg moves':
                egg_moves_table = table
                break
    
    # If we still didn't find the table, check if the page explicitly says no egg moves
    if not egg_moves_table:
        no_egg_moves_text = soup.find(string=lambda text: text and "does not learn any moves by breeding" in text.lower())
        if no_egg_moves_text:
            print(f"{pokemon_name} does not learn any moves by breeding.")
        else:
            print(f"Could not find the egg moves table for {pokemon_name}.")
        return egg_moves
    
    # Process the table to extract move information
    # Each row in the table contains information about a move
    rows = egg_moves_table.find_all('tr')[1:]  # Skip the header row
    
    for row in rows:
        cells = row.find_all('td')
        
        # Make sure we have enough cells
        if len(cells) >= 1:
            # Extract move name (in the first cell)
            move_name_cell = cells[0]
            
            # Get the actual text of the move name
            move_text = move_name_cell.text.strip()
            
            # Convert the move name to our format (MOVE_NAME)
            # Convert spaces to underscores and uppercase everything
            formatted_move = "MOVE_" + move_text.upper().replace(' ', '_').replace('-', '_')
            
            # Remove any special characters that might cause issues
            formatted_move = ''.join(c for c in formatted_move if c.isalnum() or c == '_')
            
            # Add the move to our list
            egg_moves.append(formatted_move)
    
    print(f"Found {len(egg_moves)} egg moves for {pokemon_name}.")
    return egg_moves

def format_pokemon_name(name):
    """
    Convert a pokemon name from the URL format to our SPECIES_NAME format.
    
    Args:
        name: The Pokemon name in URL format (e.g. "mr-mime", "tapu-koko")
        
    Returns:
        The Pokemon name in SPECIES_NAME format
    """
    # Handle special cases
    special_cases = {
        "nidoran-f": "NIDORAN_F",
        "nidoran-m": "NIDORAN_M",
        "mr-mime": "MR_MIME",
        "mime-jr": "MIME_JR",
        "tapu-koko": "TAPU_KOKO",
        "tapu-lele": "TAPU_LELE",
        "tapu-bulu": "TAPU_BULU",
        "tapu-fini": "TAPU_FINI",
        "type-null": "TYPE_NULL",
        "jangmo-o": "JANGMO_O",
        "hakamo-o": "HAKAMO_O",
        "kommo-o": "KOMMO_O",
        "wo-chien": "WO_CHIEN",
        "chien-pao": "CHIEN_PAO",
        "ting-lu": "TING_LU",
        "chi-yu": "CHI_YU",
    }
    
    if name.lower() in special_cases:
        return "SPECIES_" + special_cases[name.lower()]
    
    # For names with hyphens (like "great-tusk"), convert to underscores
    formatted_name = name.upper().replace('-', '_')
    
    return "SPECIES_" + formatted_name

def save_to_existing_json(pokemon_name, egg_moves, output_file):
    """
    Add the Pokemon's egg moves to the existing JSON file or create a new one.
    
    Args:
        pokemon_name: The Pokemon name
        egg_moves: List of egg moves
        output_file: Path to the output JSON file
    """
    # Convert pokemon_name to our format (SPECIES_NAME)
    formatted_name = format_pokemon_name(pokemon_name)
    
    # Load existing data if the file exists
    data = {}
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            data = json.load(f)
    
    # Add our new data
    data[formatted_name] = egg_moves
    
    # Sort the data by Pokemon name
    sorted_data = {k: data[k] for k in sorted(data.keys())}
    
    # Save the updated data
    with open(output_file, 'w') as f:
        json.dump(sorted_data, f, indent=4)
    
    print(f"Added {formatted_name} with {len(egg_moves)} egg moves to {output_file}")

def process_pokemon(pokemon_name, output_file="data/modern_egg_moves.json"):
    """
    Process a single Pokemon - download its data and extract egg moves.
    First tries Gen 9, then falls back to Gen 8 and Gen 7 if needed.
    
    Args:
        pokemon_name: Name of the Pokemon to process
        output_file: Path to the output JSON file
    """
    try:
        # Try generations in order: 9, 8, 7
        generations = ["9", "8", "7"]
        egg_moves = []
        
        for gen in generations:
            try:
                print(f"Checking Gen {gen} egg moves for {pokemon_name}...")
                # Download the HTML for this generation
                _, soup = download_pokemon_html(pokemon_name, gen)
                
                # Extract egg moves
                current_gen_moves = extract_egg_moves(soup, pokemon_name)
                
                # If we found egg moves, use them and stop looking
                if current_gen_moves:
                    egg_moves = current_gen_moves
                    print(f"Found {len(egg_moves)} egg moves for {pokemon_name} in Gen {gen}")
                    break
                else:
                    print(f"No egg moves found for {pokemon_name} in Gen {gen}, trying next generation...")
            except Exception as gen_error:
                print(f"Error getting Gen {gen} egg moves for {pokemon_name}: {str(gen_error)}")
                # Continue to next generation
        
        # If we found egg moves in any generation, save them
        if egg_moves:
            # Save to JSON file
            save_to_existing_json(pokemon_name, egg_moves, output_file)
            print(f"Saved {len(egg_moves)} egg moves for {pokemon_name}")
        else:
            # No egg moves found in any generation
            print(f"No egg moves found for {pokemon_name} in any generation (9, 8, 7)")
            # Still save an empty list for this Pokémon
            save_to_existing_json(pokemon_name, [], output_file)
        
        return True
    except Exception as e:
        print(f"Error processing {pokemon_name}: {str(e)}")
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract egg moves for a Pokemon from PokemonDB')
    parser.add_argument('pokemon', help='Pokemon name (e.g., bulbasaur, pikachu)')
    parser.add_argument('--output', default='data/modern_egg_moves.json', 
                        help='Output JSON file (default: data/modern_egg_moves.json)')
    
    args = parser.parse_args()
    
    # Make sure the output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Process the Pokemon
    process_pokemon(args.pokemon, args.output)

if __name__ == "__main__":
    main()
