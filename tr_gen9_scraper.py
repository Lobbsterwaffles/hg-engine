#!/usr/bin/env python3
"""
TR Gen 9 Scraper Tool for Pokémon Set Builder

This script scrapes TR move data from PokemonDB Generation 8 (Sword/Shield)
specifically for Pokémon that ARE in Generation 9, and adds the TR moves
to the modern_tm_learnset.json file as if they were TMs.

This is the opposite of the tr_move_scraper.py which skips Gen 9 Pokémon.
"""

import argparse
import json
import os
import re
import requests
from bs4 import BeautifulSoup
import time

def format_move_name(move_name):
    """
    Format a move name from the website format to the game format 
    (e.g., "Thunderbolt" -> "MOVE_THUNDERBOLT")
    """
    # Dictionary of known moves to ensure proper formatting
    known_moves = {
        # Common TR moves with special formatting
        "double-edge": "MOVE_DOUBLEEDGE",
        "self-destruct": "MOVE_SELFDESTRUCT",
        "thunder punch": "MOVE_THUNDERPUNCH",
        "fire punch": "MOVE_FIRE_PUNCH",
        "ice punch": "MOVE_ICE_PUNCH",
        "fake out": "MOVE_FAKE_OUT",
        "belly drum": "MOVE_BELLY_DRUM",
        "double kick": "MOVE_DOUBLE_KICK",
        "mud slap": "MOVE_MUD_SLAP",
        "dragon rush": "MOVE_DRAGON_RUSH",
        "dragon tail": "MOVE_DRAGON_TAIL",
        "iron tail": "MOVE_IRON_TAIL",
        "metal claw": "MOVE_METAL_CLAW",
        "aqua ring": "MOVE_AQUA_RING",
        "water spout": "MOVE_WATER_SPOUT",
        "life dew": "MOVE_LIFE_DEW",
        "mirror coat": "MOVE_MIRROR_COAT",
        "petal dance": "MOVE_PETAL_DANCE",
        "disarming voice": "MOVE_DISARMING_VOICE",
        "tickle": "MOVE_TICKLE",
        "wish": "MOVE_WISH",
        "flail": "MOVE_FLAIL",
        "hyper voice": "MOVE_HYPER_VOICE"  # Added this specifically for Sylveon
    }
    
    # Clean up the move name first
    # Remove any text about move stats, power, accuracy, etc.
    move_name = re.sub(r'\s+\d+.*$', '', move_name)
    
    # Extract just the move name without the type
    # First, detect and remove type information
    type_names = [
        "normal", "fighting", "flying", "poison", "ground", "rock", "bug", "ghost", 
        "steel", "fire", "water", "grass", "electric", "psychic", "ice", "dragon", "dark", "fairy"
    ]
    
    # Remove concatenated types (like ToxicPoison or FlailNormal)
    for type_name in type_names:
        pattern = f"(\w+){type_name}$"
        match = re.search(pattern, move_name, re.IGNORECASE)
        if match:
            move_name = match.group(1)
            break
    
    # Remove space-separated types (like "Flail Normal")
    for type_name in type_names:
        pattern = f"(.+)\s+{type_name}$"
        match = re.search(pattern, move_name, re.IGNORECASE)
        if match:
            move_name = match.group(1).strip()
            break
    
    # Check for specific known moves
    if move_name.lower() in known_moves:
        return known_moves[move_name.lower()]
    
    # Remove any punctuation and spaces, replace with underscore
    formatted_name = re.sub(r'[^\w\s]', '', move_name)
    # Replace spaces with underscores and convert to uppercase
    formatted_name = formatted_name.replace(' ', '_').upper()
    # Add MOVE_ prefix
    return f"MOVE_{formatted_name}"

def has_gen9_moves(pokemon_name):
    """
    Check if a Pokémon has any Gen 9 moves.
    
    Args:
        pokemon_name: Name of the Pokémon (e.g., "bulbasaur")
        
    Returns:
        Boolean indicating whether the Pokémon has Gen 9 moves
    """
    print(f"Checking if {pokemon_name} has Gen 9 moves...")
    
    # URL for the Pokémon's Gen 9 move page
    url = f"https://pokemondb.net/pokedex/{pokemon_name.lower()}/moves/9"
    
    try:
        # Add a user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad status codes
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for move sections (tables)
        move_sections = soup.find_all('h3', class_='svtabs-item')
        if not move_sections:
            # Check for more general move sections without the class
            move_sections = soup.find_all('h3')
            
        # Look for move links, which indicate the presence of moves
        move_links = soup.find_all('a', href=lambda href: href and href.startswith('/move/'))
        
        # Check for "not in this generation" message
        not_in_gen_msg = soup.find(string=re.compile(r'not\s+in\s+this\s+generation', re.IGNORECASE))
        
        if not_in_gen_msg and not move_links:
            print(f"No move sections found for {pokemon_name} in Generation 9")
            return False
        
        # If we found any move sections or move links, the Pokémon has Gen 9 moves
        has_moves = len(move_sections) > 0 or len(move_links) > 0
        
        if has_moves:
            print(f"{pokemon_name} has Gen 9 moves")
        else:
            print(f"No move sections found for {pokemon_name} in Generation 9")
            
        return has_moves
        
    except Exception as e:
        print(f"Error checking Gen 9 moves for {pokemon_name}: {str(e)}")
        return False  # Assume no Gen 9 moves on error

def get_tr_moves(pokemon_name):
    """
    Scrape TR moves for a given Pokémon from PokemonDB Gen 8.
    
    Args:
        pokemon_name: Name of the Pokémon (e.g., "bulbasaur")
        
    Returns:
        List of TR moves in the format ["MOVE_NAME1", "MOVE_NAME2", ...]
    """
    print(f"Fetching TR moves for {pokemon_name} from Gen 8...")
    
    # URL for the Pokémon's Gen 8 move page
    url = f"https://pokemondb.net/pokedex/{pokemon_name.lower()}/moves/8"
    
    try:
        # Add a user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad status codes
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the TR moves section
        tr_section = None
        for h3 in soup.find_all('h3'):
            if "Moves learnt by TR" in h3.text:
                tr_section = h3.parent
                break
        
        if not tr_section:
            print(f"No TR moves section found for {pokemon_name}")
            return []
        
        # Extract the move names
        tr_moves = []
        for a in tr_section.find_all('a'):
            # Only get the move names, not the TR numbers or types
            if a.get('href', '').startswith('/move/'):
                move_name = a.text.strip()
                if move_name and not move_name.isdigit() and "type" not in move_name.lower():
                    tr_moves.append(format_move_name(move_name))
        
        # Remove duplicates and sort
        tr_moves = sorted(list(set(tr_moves)))
        
        print(f"Found {len(tr_moves)} TR moves for {pokemon_name}")
        return tr_moves
    
    except Exception as e:
        print(f"Error fetching TR moves for {pokemon_name}: {str(e)}")
        return []

def update_tm_learnset(pokemon_species, tr_moves, output_file='data/modern_tm_learnset.json'):
    """
    Update the modern_tm_learnset.json file with the scraped TR moves
    
    Args:
        pokemon_species: The SPECIES_NAME format of the Pokémon
        tr_moves: List of TR moves in the format ["MOVE_NAME1", "MOVE_NAME2", ...]
        output_file: Path to the output JSON file
    """
    if not tr_moves:
        print(f"No TR moves to add for {pokemon_species}")
        return
    
    # Clean up any remaining type suffixes in move names
    cleaned_moves = []
    for move in tr_moves:
        # Skip incomplete entries
        if move == "MOVE_" or not move.startswith("MOVE_"):
            continue
            
        # Check for type names appended to the move
        type_names = [
            "normal", "fighting", "flying", "poison", "ground", "rock", "bug", "ghost", 
            "steel", "fire", "water", "grass", "electric", "psychic", "ice", "dragon", "dark", "fairy"
        ]
        
        clean_move = move
        for type_name in type_names:
            # Case insensitive search for the type name at the end of the move name
            if re.search(f"{type_name}$", move, re.IGNORECASE):
                # Remove the type name from the end
                clean_move = re.sub(f"{type_name}$", "", move, flags=re.IGNORECASE)
                break
        
        cleaned_moves.append(clean_move)
    
    # Use the output file path provided
    json_path = output_file
    
    # Load existing JSON data
    try:
        with open(json_path, 'r') as f:
            learnset_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty/invalid, create a new dictionary
        learnset_data = {}
    
    # Check if the Pokémon already has TM moves
    if pokemon_species in learnset_data:
        # Merge the existing TM moves with the TR moves
        existing_moves = set(learnset_data[pokemon_species])
        new_moves = set(cleaned_moves)
        combined_moves = sorted(list(existing_moves.union(new_moves)))
        learnset_data[pokemon_species] = combined_moves
        print(f"Added {len(new_moves - existing_moves)} TR moves to existing TM moves for {pokemon_species}")
    else:
        # Add the TR moves as TM moves for this Pokémon
        learnset_data[pokemon_species] = cleaned_moves
        print(f"Added {len(cleaned_moves)} TR moves for {pokemon_species}")
    
    # Write back to the file with pretty formatting
    with open(json_path, 'w') as f:
        json.dump(learnset_data, f, indent=4)
    
    print(f"Updated {json_path} with TR moves for {pokemon_species}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape TR moves from PokemonDB Gen 8 specifically for Pokémon in Gen 9')
    parser.add_argument('pokemon', nargs='+', help='Pokémon name(s) to scrape (e.g., sylveon charizard)')
    parser.add_argument('--species', action='store_true', help='Names are already in SPECIES_NAME format')
    parser.add_argument('--output', default='data/modern_tm_learnset.json',
                        help='Output JSON file (default: data/modern_tm_learnset.json)')
    args = parser.parse_args()
    
    for pokemon in args.pokemon:
        # Add a small delay between requests to be polite to the server
        if pokemon != args.pokemon[0]:
            time.sleep(2)
            
        if args.species:
            # Convert SPECIES_NAME to regular name for the web request
            pokemon_name = pokemon.replace('SPECIES_', '').lower()
            species_name = pokemon
        else:
            # Convert regular name to SPECIES_NAME for the JSON file
            pokemon_name = pokemon.lower()
            species_name = f"SPECIES_{pokemon.upper()}"
        
        # Check if the Pokémon has Gen 9 moves - 
        # ONLY process if it DOES have Gen 9 moves (opposite of original scraper)
        if not has_gen9_moves(pokemon_name):
            print(f"Skipping {pokemon_name} as it does NOT have Gen 9 moves")
            continue
            
        # Get TR moves and update the JSON file
        tr_moves = get_tr_moves(pokemon_name)
        update_tm_learnset(species_name, tr_moves, args.output)
        # Polite delay between Pokémon
        time.sleep(2)

if __name__ == "__main__":
    main()
