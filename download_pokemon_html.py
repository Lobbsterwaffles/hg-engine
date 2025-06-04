#!/usr/bin/env python3
"""
Pokemon HTML Downloader

This script downloads the HTML for a Pokemon's page from PokemonDB and saves it to a file
for inspection and debugging of the egg move scraper.
"""

import argparse
import os
import requests
from bs4 import BeautifulSoup

def download_pokemon_html(pokemon_name, generation="9"):
    """
    Download the HTML for a Pokemon's moves page from PokemonDB.
    
    Args:
        pokemon_name: Name of the Pokemon (e.g., "bulbasaur")
        generation: Game generation to download data for (default: "9")
        
    Returns:
        The raw HTML content and a BeautifulSoup object
    """
    print(f"Downloading HTML for {pokemon_name} (Gen {generation})...")
    
    # URL for the Pokemon's move page
    url = f"https://pokemondb.net/pokedex/{pokemon_name.lower()}/moves/{generation}"
    
    # Add a user agent to avoid being blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error for bad status codes
    
    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')
    
    return response.content, soup

def save_html_to_file(content, pokemon_name, generation="9"):
    """
    Save the HTML content to a file.
    
    Args:
        content: The HTML content to save
        pokemon_name: Name of the Pokemon
        generation: Game generation
    """
    # Create a filename
    filename = f"{pokemon_name}_gen{generation}_moves.html"
    
    # Save the HTML to a file
    with open(filename, 'wb') as f:
        f.write(content)
    
    print(f"Saved HTML to {filename}")
    return filename

def analyze_html(soup, pokemon_name):
    """
    Perform basic analysis of the HTML to help debugging.
    
    Args:
        soup: BeautifulSoup object of the HTML
        pokemon_name: Name of the Pokemon
    """
    print("\n===== HTML ANALYSIS =====")
    
    # Check for egg moves section
    egg_moves_found = False
    egg_section_content = ""
    
    # Method 1: Look for egg moves h3
    egg_h3 = soup.find('h3', string='Egg moves')
    if egg_h3:
        egg_moves_found = True
        print("Found 'Egg moves' section header")
        
        # Get the next elements after the h3
        egg_section_content = "Content after 'Egg moves' header:\n"
        current = egg_h3.next_sibling
        for i in range(5):  # Get next 5 elements
            if current:
                if hasattr(current, 'name'):
                    egg_section_content += f"- Tag: {current.name}, Text: {current.text.strip()[:100]}...\n"
                else:
                    egg_section_content += f"- Text node: {str(current).strip()[:100]}...\n"
                current = current.next_sibling
            else:
                break
    
    # Method 2: Search for text mentioning egg moves
    egg_text = soup.find(string=lambda text: text and "egg moves" in text.lower())
    if egg_text and not egg_moves_found:
        egg_moves_found = True
        print("Found text mentioning 'egg moves'")
        parent = egg_text.parent
        egg_section_content += f"Parent tag: {parent.name}, Content: {parent.text.strip()[:100]}...\n"
    
    # Method 3: Look for tabsets that might contain egg moves
    tabset = soup.find('div', class_='tabset-moves')
    if tabset:
        print("Found 'tabset-moves' div")
        tabs = tabset.find_all('div', class_='tab-pane')
        for i, tab in enumerate(tabs):
            tab_title = tab.find_previous('a', href=lambda h: h and h.startswith('#'))
            if tab_title:
                print(f"Tab {i+1}: {tab_title.text.strip()}")
                if 'egg' in tab_title.text.lower():
                    egg_moves_found = True
                    egg_section_content += f"Tab content: {tab.text.strip()[:100]}...\n"
    
    if not egg_moves_found:
        print("Could not find any egg moves section")
    else:
        print("\nEgg Section Content:")
        print(egg_section_content)
    
    # Look for text explicitly stating no egg moves
    no_egg_moves_text = soup.find(string=lambda text: text and "does not learn any moves by breeding" in text.lower())
    if no_egg_moves_text:
        print("\nFound explicit statement that Pokemon has no egg moves:")
        print(no_egg_moves_text.strip())
    
    # Print all h2 and h3 headers for context
    print("\nAll section headers:")
    for h in soup.find_all(['h2', 'h3']):
        print(f"{h.name}: {h.text.strip()}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download Pokemon HTML for debugging the egg move scraper')
    parser.add_argument('pokemon', help='Pokemon name (e.g., bulbasaur)')
    parser.add_argument('--gen', default='9', help='Game generation (default: 9)')
    args = parser.parse_args()
    
    # Download HTML
    content, soup = download_pokemon_html(args.pokemon, args.gen)
    
    # Save to file
    filename = save_html_to_file(content, args.pokemon, args.gen)
    
    # Analyze HTML
    analyze_html(soup, args.pokemon)
    
    print(f"\nHTML has been downloaded to {filename}. Please inspect this file to debug the egg move scraper.")

if __name__ == "__main__":
    main()
