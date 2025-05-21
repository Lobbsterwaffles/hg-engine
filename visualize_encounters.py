#!/usr/bin/env python3

"""
Visualize Pokémon Encounter Data

This tool creates a visual representation of the binary data in encounter files
to help understand the patterns and find all Pokémon species.
"""

import os
import sys
import argparse
import ndspy.rom
import ndspy.narc
from pokemon_data import POKEMON_BST

def get_pokemon_name(species_id):
    """Get a Pokémon's name from its species ID."""
    if species_id in POKEMON_BST:
        return POKEMON_BST[species_id]["name"]
    return f"UNKNOWN_{species_id}"

def visualize_encounter_file(data, file_index):
    """Create a visual representation of an encounter file."""
    if len(data) < 4:
        return f"File {file_index}: Too small ({len(data)} bytes)\n"
    
    result = f"File {file_index}: {len(data)} bytes\n"
    result += "-" * 60 + "\n"
    
    # Look for Pokémon patterns
    pokemon_found = []
    
    # Add hex dump of the first part of the file
    result += "Hex dump (first 64 bytes):\n"
    for i in range(0, min(64, len(data)), 16):
        line = data[i:i+16]
        hex_values = " ".join(f"{b:02X}" for b in line)
        ascii_values = "".join(chr(b) if 32 <= b <= 126 else "." for b in line)
        result += f"{i:04X}: {hex_values.ljust(48)} | {ascii_values}\n"
    
    result += "\n"
    
    # Check for walkrate, surfrate at the start of the file (common pattern)
    if len(data) >= 8:
        # First 8 bytes usually contain rate values
        rates = data[:8]
        result += f"Possible rates: {' '.join(f'{b:02X}' for b in rates)}\n"
        result += f"  - As values: {' '.join(str(b) for b in rates)}\n"
        
        # Try to interpret as walkrate, surfrate, etc.
        if rates[0] <= 100:  # walkrate is usually 0-100
            result += f"  - Likely walkrate: {rates[0]}\n"
        if rates[1] <= 100:  # surfrate is usually 0-100
            result += f"  - Likely surfrate: {rates[1]}\n"
    
    result += "\n"
    
    # Look for Pokémon IDs using two different approaches
    
    # 1. Find 2-byte values that could be Pokémon IDs
    result += "Possible Pokémon IDs (all 2-byte values that could be species):\n"
    for offset in range(0, len(data) - 1, 2):
        species_id = data[offset] | (data[offset + 1] << 8)
        if 1 <= species_id <= 649 and species_id in POKEMON_BST:
            pokemon_found.append((offset, species_id))
            if len(pokemon_found) <= 30:  # Limit display to avoid excessive output
                name = get_pokemon_name(species_id)
                result += f"  Offset {offset:04X}: Species #{species_id:3d} ({name})"
                
                # If this is preceded by what looks like a level (1-100), note it
                if offset > 0 and 1 <= data[offset-1] <= 100:
                    result += f" - Possible level: {data[offset-1]}"
                result += "\n"
    
    if len(pokemon_found) > 30:
        result += f"  ... and {len(pokemon_found) - 30} more Pokémon IDs found\n"
    
    result += f"\nTotal possible Pokémon found: {len(pokemon_found)}\n"
    
    # 2. Look for patterns of Pokémon entries
    # Try to detect "morning", "day", "night" sections with 12 Pokémon each
    result += "\nLooking for Pokémon sections (groups of 12):\n"
    
    for start_offset in range(0, len(data) - 24, 4):
        # Check if there's a pattern of 12 Pokémon entries starting here
        valid_pokemon = 0
        for p in range(12):
            if start_offset + (p*2) + 1 >= len(data):
                break
                
            offset = start_offset + (p*2)
            species_id = data[offset] | (data[offset + 1] << 8)
            
            if 1 <= species_id <= 649 and species_id in POKEMON_BST:
                valid_pokemon += 1
        
        # If we found at least 10 valid Pokémon in a row, this looks like a section
        if valid_pokemon >= 10:
            result += f"  Possible Pokémon section at offset {start_offset:04X}:\n"
            
            for p in range(12):
                if start_offset + (p*2) + 1 >= len(data):
                    break
                    
                offset = start_offset + (p*2)
                species_id = data[offset] | (data[offset + 1] << 8)
                
                if 1 <= species_id <= 649 and species_id in POKEMON_BST:
                    name = get_pokemon_name(species_id)
                    result += f"    Slot {p+1:2d}: Species #{species_id:3d} ({name})\n"
                else:
                    result += f"    Slot {p+1:2d}: Invalid/None (ID: {species_id})\n"
            
            result += "\n"
    
    # 3. Look for "encounter" style entries (4-byte entries with level + species)
    result += "\nLooking for \"encounter\" style entries (4-byte format):\n"
    
    for offset in range(0, len(data) - 4, 4):
        # Each encounter entry is typically 4 bytes
        # Byte 0: Encounter rate/chance
        # Byte 1: Level
        # Bytes 2-3: Species ID
        
        chance = data[offset]
        level = data[offset+1]
        species_id = data[offset+2] | (data[offset+3] << 8)
        
        # Check if this looks like a valid encounter entry
        if 1 <= chance <= 100 and 1 <= level <= 100 and 1 <= species_id <= 649 and species_id in POKEMON_BST:
            name = get_pokemon_name(species_id)
            result += f"  Offset {offset:04X}: {chance}% chance, Level {level}, #{species_id:3d} ({name})\n"
    
    return result

def visualize_encounters(rom_path):
    """
    Visualize the encounter data in a Pokémon ROM.
    
    Args:
        rom_path: Path to the ROM file
    """
    print(f"Analyzing ROM: {rom_path}")
    print("=" * 60)
    
    # Load the ROM
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Find the encounter NARC file (a/0/3/7)
    encounter_path = 'a/0/3/7'
    narc_file_id = rom.filenames.idOf(encounter_path)
    
    if narc_file_id is None:
        print(f"Error: Could not find encounter NARC at {encounter_path}")
        return
    
    narc_data = rom.files[narc_file_id]
    encounters_narc = ndspy.narc.NARC(narc_data)
    
    print(f"NARC file contains {len(encounters_narc.files)} sub-files")
    print("=" * 60)
    
    # Create output directory if it doesn't exist
    output_dir = "encounter_analysis"
    os.makedirs(output_dir, exist_ok=True)
    
    # Process a subset of files to avoid too much output
    max_files = 10  # Limit to first 10 files for brevity
    
    with open(os.path.join(output_dir, "summary.txt"), "w", encoding="utf-8") as summary_file:
        summary_file.write(f"Encounter Data Analysis\n")
        summary_file.write(f"ROM: {rom_path}\n")
        summary_file.write(f"NARC: {encounter_path}\n")
        summary_file.write(f"Total encounter files: {len(encounters_narc.files)}\n")
        summary_file.write("=" * 60 + "\n\n")
        
        # Overall statistics
        total_pokemon = 0
        pokemon_by_file = []
        
        # Analyze each file
        for i, file_data in enumerate(encounters_narc.files):
            if not file_data:
                continue
                
            # Count Pokémon in this file
            pokemon_count = 0
            for offset in range(0, len(file_data) - 1, 2):
                species_id = file_data[offset] | (file_data[offset + 1] << 8)
                if 1 <= species_id <= 649 and species_id in POKEMON_BST:
                    pokemon_count += 1
            
            pokemon_by_file.append((i, pokemon_count))
            total_pokemon += pokemon_count
            
            # Write detailed analysis for a subset of files
            if i < max_files:
                file_analysis = visualize_encounter_file(file_data, i)
                
                # Write to individual file
                with open(os.path.join(output_dir, f"file_{i:03d}.txt"), "w", encoding="utf-8") as file:
                    file.write(file_analysis)
                
                # Add summary to the main file
                summary_file.write(f"File {i}: {len(file_data)} bytes, approximately {pokemon_count} Pokémon\n")
        
        # Sort files by Pokémon count and show the top files
        pokemon_by_file.sort(key=lambda x: x[1], reverse=True)
        
        summary_file.write("\n" + "=" * 60 + "\n")
        summary_file.write("Top 10 files by Pokémon count:\n")
        for i, (file_idx, count) in enumerate(pokemon_by_file[:10]):
            summary_file.write(f"{i+1}. File {file_idx}: {count} Pokémon\n")
        
        summary_file.write("\n" + "=" * 60 + "\n")
        summary_file.write(f"Total Pokémon detected across all files: {total_pokemon}\n")
    
    print(f"Analysis complete!")
    print(f"Results saved to: {output_dir}/")
    print(f"Summary file: {output_dir}/summary.txt")
    print(f"Detailed analysis of {min(max_files, len(encounters_narc.files))} files available in {output_dir}/")

def main():
    parser = argparse.ArgumentParser(description="Visualize Pokémon encounter data in ROM files")
    parser.add_argument("rom", help="Path to the ROM file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.rom):
        print(f"Error: ROM file not found: {args.rom}")
        return 1
    
    visualize_encounters(args.rom)
    return 0

if __name__ == "__main__":
    sys.exit(main())
