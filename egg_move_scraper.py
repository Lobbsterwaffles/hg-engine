#!/usr/bin/env python3
"""
Egg Move Scraper Tool for Pokémon Set Builder

This script scrapes egg move data from PokemonDB for specified Pokémon
and adds it to the modern_egg_moves.json file in the proper format.
"""

import argparse
import json
import os
import re
import requests
import traceback
from bs4 import BeautifulSoup
import time

def format_move_name(move_name):
    """
    Format a move name from the website format to the game format 
    (e.g., "Thunderbolt" -> "MOVE_THUNDERBOLT")
    """
    # Dictionary of known moves to ensure proper formatting
    known_moves = {
        # Common egg moves
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
        "present": "MOVE_PRESENT",
        "charm": "MOVE_CHARM",
        "curse": "MOVE_CURSE",
        "ingrain": "MOVE_INGRAIN",
        "toxic": "MOVE_TOXIC",
        "bite": "MOVE_BITE",
        "counter": "MOVE_COUNTER",
        "yawn": "MOVE_YAWN",
        "mist": "MOVE_MIST",
        "detect": "MOVE_DETECT",
        "charge": "MOVE_CHARGE",
        "ancient power": "MOVE_ANCIENT_POWER",
        "fake out": "MOVE_FAKE_OUT",
        "water jet": "MOVE_WATER_SPOUT",
        "water pulse": "MOVE_WATER_PULSE",
        "mud-slap": "MOVE_MUD_SLAP",
        
        # Common partial moves that need fixing
        "dance": "MOVE_PETAL_DANCE",
        "out": "MOVE_FAKE_OUT",
        "slap": "MOVE_MUD_SLAP",
        "kick": "MOVE_DOUBLE_KICK",
        "rush": "MOVE_DRAGON_RUSH",
        "tail": "MOVE_IRON_TAIL",
        "claw": "MOVE_METAL_CLAW",
        "jet": "MOVE_AQUA_JET",
        "power": "MOVE_ANCIENT_POWER",
        "spout": "MOVE_WATER_SPOUT",
        
        # Handle Pokemon names in data
        "bulbasaur": None,
        "charmander": None,
        "squirtle": None,
        "pikachu": None,
        "eevee": None
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
    
    # Remove any move descriptions and other excessive text
    if len(move_name) > 30:
        # This is likely a description, not a move name
        # Try to extract just the first word or phrase
        first_words = move_name.split(' ')[:2]  # Take first two words at most
        move_name = ' '.join(first_words)
    
    # Remove any numbers, parentheses, and other non-alphabetic characters
    move_name = re.sub(r'[^\w\s-]', '', move_name)
    
    # Remove specific known bad text patterns
    bad_patterns = [
        r'learns the following moves',
        r'via breeding',
        r'picnics',
        r'details',
        r'compatible',
        r'parents',
        r'scarlet',
        r'violet',
        r'\blearns\b',
        r'\begg\b',
        r'\bmoves\b'
    ]
    
    for pattern in bad_patterns:
        move_name = re.sub(pattern, '', move_name, flags=re.IGNORECASE)
    
    # Final cleanup
    move_name = move_name.strip().lower()
    
    # Check for known moves or partial moves
    if move_name in known_moves:
        return known_moves[move_name]
            
    # Format the move name if it wasn't in our dictionary
    if move_name:
        # Remove any punctuation and spaces, replace with underscore
        formatted_name = re.sub(r'[^\w\s]', '', move_name)
        # Replace spaces with underscores and convert to uppercase
        formatted_name = formatted_name.replace(' ', '_').upper()
        # Add MOVE_ prefix
        return f"MOVE_{formatted_name}"
    else:
        return None  # Return None for invalid moves

def get_egg_moves(pokemon_name):
    """
    Scrape egg moves for a given Pokémon from PokemonDB.
    
    Args:
        pokemon_name: Name of the Pokémon (e.g., "bulbasaur")
        
    Returns:
        List of egg moves in the format ["MOVE_NAME1", "MOVE_NAME2", ...]
    """
    print(f"Fetching egg moves for {pokemon_name}...")
    
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
        
        # Method 1: Direct approach - find the dash-list of egg moves which typically follows h3
        egg_moves = []
        content = str(soup)
        
        # Find egg moves section and extract moves
        for h2 in soup.find_all('h2'):
            if 'egg move parents' in h2.text.lower():
                # Search for bullet list following the Egg moves header
                main_div = h2.parent
                egg_moves_section = main_div.find('h3', text='Egg moves')
                
                if egg_moves_section:
                    # The egg moves are in a bullet list after this h3
                    # or sometimes in dash-separated text
                    
                    # First look for a bullet list
                    egg_move_list = None
                    current = egg_moves_section.next_sibling
                    
                    # Skip text nodes until we find a ul or p tag
                    while current and not egg_move_list:
                        if current.name == 'ul':
                            egg_move_list = current
                            # Found a bullet list, extract moves
                            for li in egg_move_list.find_all('li'):
                                move_name = li.text.strip()
                                formatted_move = format_move_name(move_name)
                                if formatted_move:
                                    egg_moves.append(formatted_move)
                            break
                        elif current.name == 'p' and '-' in current.text:
                            # Found dash-separated text
                            lines = current.text.strip().split('\n')
                            for line in lines:
                                parts = line.split('-')
                                for part in parts:
                                    move = part.strip()
                                    if move and not move.lower().startswith('egg moves') and not 'egg groups' in move.lower():
                                        formatted_move = format_move_name(move)
                                        if formatted_move:
                                            egg_moves.append(formatted_move)
                            break
                        current = current.next_sibling
                        
                    # If we still don't have moves, try text extraction
                    if not egg_moves:
                        # Look for text nodes that might contain the moves
                        text_after_h3 = ''
                        current = egg_moves_section.next_sibling
                        while current and (not current.name or current.name not in ['h2', 'h3']):
                            if isinstance(current, str):
                                text_after_h3 += current
                            elif hasattr(current, 'text'):
                                text_after_h3 += current.text
                            current = current.next_sibling
                        
                        # Extract moves from the text
                        move_candidates = re.split(r'[\n-]', text_after_h3)
                        for move in move_candidates:
                            move = move.strip()
                            if move and not move.lower().startswith('egg') and not 'groups' in move.lower():
                                formatted_move = format_move_name(move)
                                if formatted_move:
                                    egg_moves.append(formatted_move)
                break

        # Backup method - try to find all plaintext instances of egg moves
        if not egg_moves:
            # Find the section that mentions egg moves
            egg_section_text = ""
            for p in soup.find_all('p'):
                if 'egg moves for' in p.text.lower():
                    # Found the egg moves section
                    egg_section_text = p.text
                    break
            
            if egg_section_text:
                # Extract the lines that might contain egg moves
                lines = egg_section_text.split('\n')
                for line in lines:
                    if '-' in line:
                        # This might be a line with egg moves
                        parts = line.split('-')
                        for part in parts[1:]:  # Skip the first part which is often a header
                            move = part.strip()
                            if move:
                                formatted_move = format_move_name(move)
                                if formatted_move:
                                    egg_moves.append(formatted_move)
        
        # Print the HTML for debugging if no egg moves were found
        if not egg_moves:
            print(f"Could not find egg moves on the page for {pokemon_name}")
            
            # Try to extract from the "Egg moves" direct text
            egg_moves_patterns = [
                r'Egg moves[\s\n]*[-–]([^\n]+)', 
                r'Egg moves:\s*([^\n]+)',
                r'Egg moves\s*([^\n]+)'
            ]
            
            for pattern in egg_moves_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        # Split by dashes or commas
                        for move in re.split(r'[-,\n]', match):
                            move = move.strip()
                            if move and not move.lower().startswith('egg') and not 'groups' in move.lower():
                                formatted_move = format_move_name(move)
                                if formatted_move:
                                    egg_moves.append(formatted_move)
        
        # Last resort - look for specific egg move patterns in HTML
        if not egg_moves:
            # Look for headers for each egg move
            for h3 in soup.find_all('h3'):
                if h3.text and not h3.text.lower() == 'egg moves' and not 'level' in h3.text.lower() and not 'tm' in h3.text.lower():
                    move = h3.text.strip()
                    formatted_move = format_move_name(move)
                    if formatted_move:
                        egg_moves.append(formatted_move)
        
        # Remove duplicates and sort
        egg_moves = sorted(list(set(egg_moves)))
        
        print(f"Found {len(egg_moves)} egg moves for {pokemon_name}")
        return egg_moves
    
    except Exception as e:
        print(f"Error fetching egg moves for {pokemon_name}: {str(e)}")
        traceback.print_exc()
        return []

def update_egg_moves(pokemon_species, egg_moves):
    """
    Update the modern_egg_moves.json file with the scraped egg moves
    
    Args:
        pokemon_species: The SPECIES_NAME format of the Pokémon
        egg_moves: List of egg moves in the format ["MOVE_NAME1", "MOVE_NAME2", ...]
    """
    if not egg_moves:
        print(f"No egg moves to add for {pokemon_species}")
        return
    
    # Clean up any remaining type suffixes in move names
    cleaned_moves = []
    for move in egg_moves:
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
    
    # Path to the modern_egg_moves.json file
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'modern_egg_moves.json')
    
    # Load existing JSON data
    try:
        with open(json_path, 'r') as f:
            learnset_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty/invalid, create a new dictionary
        learnset_data = {}
    
    # Update the egg moves for this Pokémon
    learnset_data[pokemon_species] = cleaned_moves
    
    # Write back to the file with pretty formatting
    with open(json_path, 'w') as f:
        json.dump(learnset_data, f, indent=4)
    
    print(f"Updated {json_path} with {len(cleaned_moves)} egg moves for {pokemon_species}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape egg moves from PokemonDB for the modern_egg_moves.json file')
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
        
        # Get egg moves and update the JSON file
        egg_moves = get_egg_moves(pokemon_name)
        update_egg_moves(species_name, egg_moves)

if __name__ == "__main__":
    main()
