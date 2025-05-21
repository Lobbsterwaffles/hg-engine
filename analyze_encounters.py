#!/usr/bin/env python3

"""
Analyze Pokémon Encounter NARC Files

This script examines the contents of NARC files that hold Pokémon encounter data.
It helps understand how the data is structured and where Pokémon IDs are located.
"""

import os
import sys
import argparse
import ndspy.rom
import ndspy.narc
from pokemon_data import POKEMON_BST  # Import our Pokémon data

def analyze_narc(rom_path, narc_path):
    """
    Analyze the contents of a NARC file containing encounter data.
    
    Args:
        rom_path: Path to the ROM file
        narc_path: Path to the NARC file within the ROM (e.g., 'a/0/3/7')
    """
    print(f"Analyzing ROM: {rom_path}")
    print(f"Looking for NARC: {narc_path}")
    print("=" * 60)
    
    # Load the ROM
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Find and extract the NARC file
    narc_file_id = rom.filenames.idOf(narc_path)
    if narc_file_id is None:
        print(f"Error: Could not find NARC at {narc_path}")
        return
    
    narc_data = rom.files[narc_file_id]
    narc = ndspy.narc.NARC(narc_data)
    
    print(f"NARC file contains {len(narc.files)} sub-files")
    print("=" * 60)
    
    # Analyze each file in the NARC
    pokemon_count = 0
    file_with_most = (0, 0)  # (file_index, count)
    
    for i, file_data in enumerate(narc.files):
        if not file_data:
            continue
        
        print(f"\nFile {i}: {len(file_data)} bytes")
        
        # Look for Pokémon IDs in this file
        file_pokemon = []
        
        # Method 1: Look for bytes that could be valid Pokémon IDs
        for offset in range(0, len(file_data) - 1, 2):
            species_id = file_data[offset] | (file_data[offset + 1] << 8)
            if 1 <= species_id <= 649 and species_id in POKEMON_BST:
                pokemon_name = POKEMON_BST[species_id]["name"]
                file_pokemon.append((offset, species_id, pokemon_name))
        
        # Print what we found
        if file_pokemon:
            print(f"  Found {len(file_pokemon)} potential Pokémon IDs:")
            for offset, species_id, name in file_pokemon[:10]:  # Show first 10
                print(f"    Offset {offset:4d}: #{species_id:3d} {name}")
            
            if len(file_pokemon) > 10:
                print(f"    ... and {len(file_pokemon) - 10} more")
            
            # Keep track of the file with the most Pokémon
            if len(file_pokemon) > file_with_most[1]:
                file_with_most = (i, len(file_pokemon))
            
            pokemon_count += len(file_pokemon)
    
    print("\n" + "=" * 60)
    print(f"Total potential Pokémon IDs found: {pokemon_count}")
    print(f"File with most Pokémon: File {file_with_most[0]} with {file_with_most[1]} Pokémon")
    print("=" * 60)
    
    # Additional analysis of the file with the most Pokémon
    if file_with_most[1] > 0:
        print("\nDetailed analysis of file with most Pokémon:")
        file_index = file_with_most[0]
        file_data = narc.files[file_index]
        
        # Try to identify patterns in the file
        print(f"Examining file {file_index} ({len(file_data)} bytes):")
        
        # Look for repeating patterns (e.g., 12-byte structures)
        pattern_sizes = [4, 8, 12, 16, 20, 24]
        for size in pattern_sizes:
            if len(file_data) % size == 0:
                print(f"  This file's size is divisible by {size} bytes (possible structure size)")
        
        # Check if Pokémon IDs appear at regular intervals
        pokemon_offsets = []
        for offset in range(0, len(file_data) - 1, 2):
            species_id = file_data[offset] | (file_data[offset + 1] << 8)
            if 1 <= species_id <= 649 and species_id in POKEMON_BST:
                pokemon_offsets.append(offset)
        
        if len(pokemon_offsets) >= 2:
            # Calculate differences between consecutive offsets
            differences = [pokemon_offsets[i+1] - pokemon_offsets[i] for i in range(len(pokemon_offsets)-1)]
            # Check if all differences are the same (regular pattern)
            if len(set(differences)) == 1:
                print(f"  Pokémon IDs appear at regular intervals of {differences[0]} bytes")
            else:
                # Check for grouped patterns
                print("  Pokémon ID offsets:", pokemon_offsets[:10], "..." if len(pokemon_offsets) > 10 else "")
        
        # Dump the beginning of the file for visual inspection
        print("\n  First 64 bytes of data (in decimal):")
        for i in range(0, min(64, len(file_data)), 16):
            line = file_data[i:i+16]
            hex_values = " ".join(f"{b:02X}" for b in line)
            print(f"    {i:04X}: {hex_values}")

def main():
    parser = argparse.ArgumentParser(description="Analyze Pokémon encounter data in NARC files")
    parser.add_argument("rom", help="Path to the ROM file")
    parser.add_argument("--narc", default="a/0/3/7", help="Path to the NARC file in the ROM (default: a/0/3/7)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.rom):
        print(f"Error: ROM file not found: {args.rom}")
        return 1
    
    analyze_narc(args.rom, args.narc)
    return 0

if __name__ == "__main__":
    sys.exit(main())
