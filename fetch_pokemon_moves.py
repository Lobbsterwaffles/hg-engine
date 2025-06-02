import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re

# This script will fetch move data from PokemonDB and create JSON files with modern move data
# It will gather:
# 1. TM moves (generation 9)
# 2. Egg moves (generation 9)

# Dictionary to store our move data
all_move_data = {
    'tm_moves': {},  # Format: {'SPECIES_NAME': ['MOVE_NAME1', 'MOVE_NAME2', ...]}
    'egg_moves': {}  # Format: {'SPECIES_NAME': ['MOVE_NAME1', 'MOVE_NAME2', ...]}
}

# Get the base directory
base_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths
species_file = os.path.join(base_dir, 'asm', 'include', 'species.inc')
output_dir = os.path.join(base_dir, 'data')
tm_json_file = os.path.join(output_dir, 'modern_tm_learnset.json')
egg_json_file = os.path.join(output_dir, 'modern_egg_moves.json')
egg_assembly_file = os.path.join(base_dir, 'armips', 'data', 'eggmoves.s')

# Make sure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Map from PokemonDB name format to our SPECIES_ format
def format_to_species_name(name):
    """Convert a PokemonDB Pokemon name to our SPECIES_ format"""
    # Remove special characters, spaces, and convert to uppercase
    # For example: "Mr. Mime" -> "SPECIES_MR_MIME"
    name = name.replace("'", "").replace("-", "_").replace(".", "").replace(" ", "_")
    name = re.sub(r'[^A-Za-z0-9_]', '', name)  # Remove any other special characters
    return f"SPECIES_{name.upper()}"

# Map from move name to our MOVE_ format
def format_to_move_name(name):
    """Convert a PokemonDB move name to our MOVE_ format"""
    # Remove special characters, spaces, and convert to uppercase
    # For example: "Fire Blast" -> "MOVE_FIRE_BLAST"
    name = name.replace("'", "").replace("-", "_").replace(".", "").replace(" ", "_")
    name = re.sub(r'[^A-Za-z0-9_]', '', name)  # Remove any other special characters
    return f"MOVE_{name.upper()}"

# Get list of Pokemon from species.inc
def parse_species_file():
    """Parse the species.inc file to get Pokemon names and IDs"""
    species_data = {}
    
    try:
        with open(species_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('.equ SPECIES_'):
                    parts = line.split(',')
                    if len(parts) == 2:
                        species_name = parts[0].replace('.equ ', '').strip()
                        id_value = parts[1].strip()
                        
                        # Skip if the ID is a complex expression
                        if id_value.startswith('(') or '+' in id_value or '-' in id_value or '*' in id_value or '/' in id_value:
                            continue
                        
                        try:
                            species_id = int(id_value)
                        except ValueError:
                            # If we can't parse it as an integer, skip this entry
                            continue
                        
                        # Skip special forms and non-standard Pokemon
                        if (not species_name.startswith('SPECIES_EGG') and 
                            not species_name == 'SPECIES_NONE' and 
                            not species_name == 'SPECIES_BAD_EGG' and
                            not '_FORM' in species_name and
                            not '_REGIONAL' in species_name and
                            not '_START' in species_name):
                            species_data[species_name] = {
                                'id': species_id,
                                'db_name': convert_species_to_db_name(species_name)
                            }
        
        print(f"Successfully parsed {len(species_data)} Pokemon from species file.")
        return species_data
    
    except Exception as e:
        print(f"Error parsing species file: {str(e)}")
        return {}

# Convert SPECIES_NAME to PokemonDB name format
def convert_species_to_db_name(species_name):
    """Convert SPECIES_NAME to PokemonDB URL format"""
    # Remove SPECIES_ prefix
    name = species_name.replace('SPECIES_', '')
    
    # Handle special cases
    if name == 'NIDORANF':
        return 'nidoran-f'
    elif name == 'NIDORANM':
        return 'nidoran-m'
    elif name == 'FARFETCHD':
        return 'farfetchd'
    elif name == 'MR_MIME':
        return 'mr-mime'
    elif name == 'HO_OH':
        return 'ho-oh'
    elif name == 'MIME_JR':
        return 'mime-jr'
    elif name == 'PORYGON_Z':
        return 'porygon-z'
    
    # Convert to lowercase and replace underscores with hyphens
    return name.lower().replace('_', '-')

# Fetch move data from PokemonDB
def fetch_pokemon_moves(pokemon_db_name):
    """Fetch move data for a given Pokemon from PokemonDB"""
    url = f"https://pokemondb.net/pokedex/{pokemon_db_name}/moves/9"
    
    try:
        # Add a delay to be respectful to the website
        time.sleep(1)
        
        # Make the request
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch data for {pokemon_db_name}: HTTP {response.status_code}")
            return None
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract move data
        move_data = {
            'tm_moves': [],
            'egg_moves': []
        }
        
        # Find TM moves section
        tm_section = soup.find('h3', text='Moves learnt by TM')
        if tm_section:
            # TM moves are listed in the table after the heading
            tm_table = tm_section.find_next('table')
            if tm_table:
                # Find move names in the table
                for row in tm_table.find_all('tr')[1:]:  # Skip header row
                    # Move name is in the first column
                    move_link = row.find('a')
                    if move_link:
                        move_name = move_link.text.strip()
                        move_data['tm_moves'].append(format_to_move_name(move_name))
        
        # Find Egg moves section
        egg_section = soup.find('h3', text='Egg moves')
        if egg_section:
            # Egg moves are listed as links after the heading
            move_links = egg_section.find_next('div').find_all('a')
            for link in move_links:
                move_name = link.text.strip()
                move_data['egg_moves'].append(format_to_move_name(move_name))
        
        return move_data
    
    except Exception as e:
        print(f"Error fetching moves for {pokemon_db_name}: {str(e)}")
        return None

# Main function
def main():
    print("Starting Pokemon move data collection...")
    
    # Parse species file to get Pokemon data
    species_data = parse_species_file()
    if not species_data:
        print("Failed to parse species file. Exiting.")
        return
    
    # Count for progress tracking
    total_pokemon = len(species_data)
    processed = 0
    
    # Process each Pokemon
    for species_name, data in species_data.items():
        processed += 1
        db_name = data['db_name']
        
        print(f"Processing {processed}/{total_pokemon}: {species_name} ({db_name})")
        
        # Fetch move data from PokemonDB
        move_data = fetch_pokemon_moves(db_name)
        
        if move_data:
            # Store TM moves
            if move_data['tm_moves']:
                all_move_data['tm_moves'][species_name] = move_data['tm_moves']
                print(f"  Found {len(move_data['tm_moves'])} TM moves")
            
            # Store Egg moves
            if move_data['egg_moves']:
                all_move_data['egg_moves'][species_name] = move_data['egg_moves']
                print(f"  Found {len(move_data['egg_moves'])} Egg moves")
    
    # Save TM moves to JSON
    with open(tm_json_file, 'w') as f:
        json.dump(all_move_data['tm_moves'], f, indent=4)
    print(f"Saved TM moves to {tm_json_file}")
    
    # Save Egg moves to JSON
    with open(egg_json_file, 'w') as f:
        json.dump(all_move_data['egg_moves'], f, indent=4)
    print(f"Saved Egg moves to {egg_json_file}")
    
    # Update eggmoves.s assembly file
    update_egg_moves_assembly()
    
    print("Data collection complete!")

# Update the eggmoves.s assembly file
def update_egg_moves_assembly():
    """Update the eggmoves.s assembly file with the new egg move data"""
    try:
        # Create the header content
        header = """.nds
.thumb

.include "armips/include/macros.s"

.include "asm/include/moves.inc"
.include "asm/include/species.inc"

// the egg moves of each mon
// needs to be in species order
// This file is auto-generated from PokemonDB data (Generation 9)

"""
        
        # Create the content for each Pokemon
        content = []
        
        # Sort Pokemon by their species ID to maintain correct order
        sorted_species = sorted(
            [(name, data) for name, data in all_move_data['egg_moves'].items()],
            key=lambda x: next((sd['id'] for sn, sd in parse_species_file().items() if sn == x[0]), 9999)
        )
        
        for species_name, moves in sorted_species:
            if moves:  # Only include Pokemon with egg moves
                # Add the species entry
                content.append(f"\neggmoveentry {species_name}")
                
                # Add each move
                for move in moves:
                    content.append(f"    eggmove {move}")
        
        # Write to the file
        with open(egg_assembly_file, 'w') as f:
            f.write(header)
            f.write('\n'.join(content))
        
        print(f"Updated {egg_assembly_file} with new egg move data")
    
    except Exception as e:
        print(f"Error updating egg moves assembly file: {str(e)}")

if __name__ == "__main__":
    main()
