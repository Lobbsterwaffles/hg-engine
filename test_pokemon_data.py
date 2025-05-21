import os
import sys
import logging
from pokemon_rom_reader import get_pokemon_data

# Simple script to read Pokémon data from a ROM and create a stats dump

def main():
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 60)
    print("POKÉMON STATS DUMP TOOL")
    print("This will create a text file with all Pokémon stats from your ROM")
    print("=" * 60)
    
    # Ask for ROM path if not provided
    if len(sys.argv) > 1:
        rom_path = sys.argv[1]
    else:
        rom_path = input("\nEnter the path to your ROM file: ")
    
    # Check if the file exists
    if not os.path.exists(rom_path):
        print(f"Error: File {rom_path} does not exist!")
        return
    
    print(f"\nReading data from ROM: {rom_path}")
    print("Please wait, this may take a few moments...\n")
    
    # Get Pokémon data from the ROM
    pokemon_data = get_pokemon_data(rom_path, use_caching=False, create_dump=True)
    
    if not pokemon_data:
        print("Error: Could not read Pokémon data from the ROM!")
        return
    
    print(f"\nFound data for {len(pokemon_data)} Pokémon species!")
    
    # Calculate some statistics
    bst_values = [data["bst"] for data in pokemon_data.values()]
    if bst_values:
        avg_bst = sum(bst_values) / len(bst_values)
        min_bst = min(bst_values)
        max_bst = max(bst_values)
        print(f"BST Statistics:")
        print(f"  Average BST: {avg_bst:.1f}")
        print(f"  Minimum BST: {min_bst}")
        print(f"  Maximum BST: {max_bst}")
    
    print("\nVerify the data in the pokemon_stats_dump.txt file!")

if __name__ == "__main__":
    main()
