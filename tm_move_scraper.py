#!/usr/bin/env python3
"""
TM Move Scraper Tool for Pokémon Set Builder

This script scrapes TM move data from PokemonDB for specified Pokémon
and adds it to the modern_tm_learnset.json file in the proper format.
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
        # Common TM moves with special formatting
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
        "flail": "MOVE_FLAIL"
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

def get_tm_moves(pokemon_name):
    """
    Scrape TM moves for a given Pokémon from PokemonDB.
    
    Args:
        pokemon_name: Name of the Pokémon (e.g., "bulbasaur")
        
    Returns:
        List of TM moves in the format ["MOVE_NAME1", "MOVE_NAME2", ...]
    """
    print(f"Fetching TM moves for {pokemon_name}...")
    
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
        
        # Find the TM moves section
        tm_section = None
        for h3 in soup.find_all('h3'):
            if "Moves learnt by TM" in h3.text:
                tm_section = h3.parent
                break
        
        if not tm_section:
            print(f"No TM moves section found for {pokemon_name}")
            return []
        
        # Extract the move names
        tm_moves = []
        for a in tm_section.find_all('a'):
            # Only get the move names, not the TM numbers or types
            if a.get('href', '').startswith('/move/'):
                move_name = a.text.strip()
                if move_name and not move_name.isdigit() and "type" not in move_name.lower():
                    tm_moves.append(format_move_name(move_name))
        
        # Remove duplicates and sort
        tm_moves = sorted(list(set(tm_moves)))
        
        print(f"Found {len(tm_moves)} TM moves for {pokemon_name}")
        return tm_moves
    
    except Exception as e:
        print(f"Error fetching TM moves for {pokemon_name}: {str(e)}")
        return []

def update_tm_moves(pokemon_species, tm_moves):
    """
    Update the modern_tm_learnset.json file with the scraped TM moves
    
    Args:
        pokemon_species: The SPECIES_NAME format of the Pokémon
        tm_moves: List of TM moves in the format ["MOVE_NAME1", "MOVE_NAME2", ...]
    """
    if not tm_moves:
        print(f"No TM moves to add for {pokemon_species}")
        return
    
    # Clean up any remaining type suffixes in move names
    cleaned_moves = []
    for move in tm_moves:
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
    
    # Path to the modern_tm_learnset.json file
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'modern_tm_learnset.json')
    
    # Load existing JSON data
    try:
        with open(json_path, 'r') as f:
            learnset_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty/invalid, create a new dictionary
        learnset_data = {}
    
    # Update the TM moves for this Pokémon
    learnset_data[pokemon_species] = cleaned_moves
    
    # Write back to the file with pretty formatting
    with open(json_path, 'w') as f:
        json.dump(learnset_data, f, indent=4)
    
    print(f"Updated {json_path} with {len(cleaned_moves)} TM moves for {pokemon_species}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape TM moves from PokemonDB for the modern_tm_learnset.json file')
    parser.add_argument('pokemon', nargs='+', help='Pokémon name(s) to scrape (e.g., bulbasaur charizard pikachu)')
    parser.add_argument('--species', action='store_true', help='Names are already in SPECIES_NAME format')
    args = parser.parse_args()
    
    for pokemon in args.pokemon:
        # Add a small delay between requests to be polite to the server
        if pokemon != args.pokemon[0]:
            time.sleep(1)
            
        if args.species:
            # Convert SPECIES_NAME to regular name for the web request
            pokemon_name = pokemon.replace('SPECIES_', '').lower()
            species_name = pokemon
        else:
            # Convert regular name to SPECIES_NAME for the JSON file
            pokemon_name = pokemon.lower()
            species_name = f"SPECIES_{pokemon.upper()}"
        
        # Get TM moves and update the JSON file
        tm_moves = get_tm_moves(pokemon_name)
        update_tm_moves(species_name, tm_moves)

if __name__ == "__main__":
    main()
