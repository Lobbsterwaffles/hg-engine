#!/usr/bin/env python3
"""
Test script to check for placeholder Pokémon names
"""

import pokemon_shared
import ndspy.rom
import sys

# Check if a ROM file is provided
if len(sys.argv) < 2:
    print("Usage: python test_placeholder_names.py <rom_file>")
    sys.exit(1)

# Load the ROM
rom_path = sys.argv[1]
print(f"Loading ROM file: {rom_path}")
try:
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
except Exception as e:
    print(f"Error loading ROM: {e}")
    sys.exit(1)

# Read Pokémon names
print("Reading Pokémon names...")
try:
    names = pokemon_shared.read_pokemon_names(".")
except Exception as e:
    print(f"Error reading Pokémon names: {e}")
    sys.exit(1)

# Read all Pokémon data
print("Reading Pokémon data...")
try:
    all_pokemon = pokemon_shared.read_mondata(rom, names)
except Exception as e:
    print(f"Error reading Pokémon data: {e}")
    sys.exit(1)

# Count and print Pokémon with "-----" as their name
placeholder_count = 0
placeholder_ids = []

for i, mon in enumerate(all_pokemon):
    if mon.name == "-----":
        placeholder_count += 1
        placeholder_ids.append(i)
        # Print some info about the first 10 placeholder Pokémon
        if len(placeholder_ids) <= 10:
            print(f"ID: {i}, Name: '{mon.name}', BST: {mon.bst}")

print(f"\nFound {placeholder_count} Pokémon with placeholder names ('-----')")
print(f"First few placeholder IDs: {placeholder_ids[:10]}...")

# Let's check if our filter is working properly
# We'll make a sample search for replacements for a Pokémon with BST around 400
sample_mon = next(mon for mon in all_pokemon if 395 <= mon.bst <= 405)
print(f"\nTesting replacement search for {sample_mon.name} (BST: {sample_mon.bst})")

# Regular find_replacements
all_replacements = pokemon_shared.find_replacements(sample_mon, all_pokemon, 0.9, 1.1)
print(f"Found {len(all_replacements)} possible replacements")

# Check if any of the replacements have placeholder names
placeholder_in_replacements = [i for i in all_replacements if all_pokemon[i].name == "-----"]
print(f"Number of placeholder Pokémon in replacements: {len(placeholder_in_replacements)}")
if placeholder_in_replacements:
    print(f"Example placeholder replacements: {placeholder_in_replacements[:5]}")
