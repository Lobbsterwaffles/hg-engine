#!/usr/bin/env python3
"""
ROM Comparison Tool

This script compares two Nintendo DS ROM files and reports the differences between them.
It unpacks both ROMs into their individual files and analyzes the binary differences.
"""

import os
import sys
import argparse
import difflib
import binascii
from pathlib import Path
import tempfile
import shutil

# Import ndspy for Nintendo DS ROM handling
import ndspy.rom
import ndspy.narc

# Text formatting helpers
class TextFormat:
    # No ANSI colors - use simple text formatting instead
    HEADER = ''
    BOLD = ''
    UNDERLINE = ''
    
    # Helper methods for consistent formatting
    @staticmethod
    def header(text):
        return f"{TextFormat.BOLD}{text}{TextFormat.BOLD}"
    
    @staticmethod
    def section(text):
        return f"{TextFormat.BOLD}{text}{TextFormat.BOLD}"
    
    @staticmethod
    def highlight(text):
        return f">{text}<"
    
    @staticmethod
    def format_file_header(file_path, a_size, b_size):
        return f"{TextFormat.BOLD}File: {file_path}{TextFormat.BOLD}"

def extract_rom_files(rom_path, output_dir):
    """
    Extract all files from a Nintendo DS ROM to a directory structure.
    
    Args:
        rom_path (str): Path to the ROM file
        output_dir (str): Directory to extract files to
    
    Returns:
        dict: A mapping of file paths to their content
    """
    print(f"Loading ROM file: {rom_path}")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Create a dictionary to store all extracted files
    extracted_files = {}
    
    print(f"Extracting files from ROM...")
    # Extract files from the ROM's filesystem
    # Create a list to store all file paths
    all_file_paths = []
    
    # Get a list of all file IDs in the ROM
    for file_id in range(len(rom.files)):
        # Skip empty file slots
        if file_id >= len(rom.files) or rom.files[file_id] is None:
            continue
            
        # Get the file content
        file_content = rom.files[file_id]
        
        # Create a simple file path based on the ID
        file_path = f"file_{file_id:04d}"
        all_file_paths.append(file_path)
        
        # Create the output directory structure
        full_path = os.path.join(output_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Store the file content
        extracted_files[file_path] = file_content
        
        # Write the file to disk for reference
        with open(full_path, 'wb') as f:
            f.write(file_content)
        
        # Try to extract NARC archives (collections of files)
        try:
            # Check if this file is a NARC archive
            if file_content.startswith(b'NARC'):
                narc_data = ndspy.narc.NARC(file_content)
                
                # Create a directory for the NARC contents
                narc_dir = full_path + ".narc"
                os.makedirs(narc_dir, exist_ok=True)
                
                # Extract each file in the NARC
                for i, narc_file in enumerate(narc_data.files):
                    # Create a path for this NARC file
                    narc_file_path = f"{file_path}/narc/{i:04d}"
                    
                    # Store the NARC file content
                    extracted_files[narc_file_path] = narc_file
                    
                    # Also write the file to disk
                    disk_path = os.path.join(narc_dir, f"{i:04d}.bin")
                    with open(disk_path, 'wb') as f:
                        f.write(narc_file)
        except Exception as e:
            # Not a NARC or other issue
            print(f"  Note: Could not extract NARC from {file_path}: {str(e)}[:100]")
            pass
    
    print(f"Extracted {len(extracted_files)} files and archives")
    return extracted_files

def analyze_pokemon_changes(data_a, data_b, offset, value_a, value_b):
    """
    Analyzes a byte change to determine if it might be a Pokémon ID change.
    
    Args:
        data_a (bytes): First binary data
        data_b (bytes): Second binary data
        offset (int): Offset where the change was found
        value_a (int): Byte value in file A
        value_b (int): Byte value in file B
        
    Returns:
        dict or None: Information about potential Pokémon change or None
    """
    # Look for common Pokemon ID patterns
    # In most Pokemon games, IDs are stored as 2-byte values
    # We'll check both little-endian and big-endian possibilities
    result = None
    
    # Check if this might be part of a Pokémon ID (simple heuristic)
    # For byte at offset i, check bytes at i-1 and i+1 as well
    if offset > 0 and offset < len(data_a) - 1:
        # Try to interpret as a 16-bit Pokémon ID (little endian)
        if data_a[offset+1] == data_b[offset+1] and data_a[offset+1] == 0x00:
            # Possible Pokémon ID in little-endian format
            pokemon_id_a = value_a
            pokemon_id_b = value_b
            result = {
                'type': 'pokemon_id',
                'endian': 'little',
                'id_a': pokemon_id_a,
                'id_b': pokemon_id_b
            }
        # Try to interpret as a 16-bit Pokémon ID (big endian)
        elif data_a[offset-1] == data_b[offset-1] and data_a[offset-1] == 0x00:
            # Possible Pokémon ID in big-endian format
            pokemon_id_a = value_a
            pokemon_id_b = value_b
            result = {
                'type': 'pokemon_id',
                'endian': 'big',
                'id_a': pokemon_id_a,
                'id_b': pokemon_id_b
            }
    
    return result

def compare_binaries(data_a, data_b, max_diff_bytes=100):
    """
    Compare two binary data objects and return their differences.
    
    Args:
        data_a (bytes): First binary data
        data_b (bytes): Second binary data
        max_diff_bytes (int): Maximum number of different bytes to report
    
    Returns:
        list: List of differences, each with offset and values
    """
    differences = []
    
    # Get lengths of both data
    len_a = len(data_a)
    len_b = len(data_b)
    
    # Handle size differences
    if len_a != len_b:
        differences.append({
            'type': 'size',
            'a_size': len_a,
            'b_size': len_b,
            'diff': abs(len_a - len_b)
        })
    
    # Compare byte by byte
    diff_count = 0
    min_len = min(len_a, len_b)
    
    for i in range(min_len):
        if data_a[i] != data_b[i]:
            diff_count += 1
            
            # Add to differences list if we haven't exceeded max_diff_bytes
            if diff_count <= max_diff_bytes:
                # Check if this might be a Pokémon ID change
                pokemon_analysis = analyze_pokemon_changes(
                    data_a, data_b, i, data_a[i], data_b[i]
                )
                
                diff = {
                    'type': 'content',
                    'offset': i,
                    'a_value': data_a[i],
                    'b_value': data_b[i],
                    'a_hex': f"0x{data_a[i]:02X}",
                    'b_hex': f"0x{data_b[i]:02X}",
                    'pokemon_analysis': pokemon_analysis
                }
                
                differences.append(diff)
    
    # If there are more differences than we reported, add a note
    if diff_count > max_diff_bytes:
        differences.append({
            'type': 'limit',
            'total_diffs': diff_count,
            'reported': max_diff_bytes
        })
    
    return differences

def format_hex_dump(data, offset, context=8):
    """
    Create a formatted hex dump of binary data around a specific offset.
    
    Args:
        data (bytes): Binary data
        offset (int): Center offset for the dump
        context (int): Number of bytes to show before and after the offset
    
    Returns:
        str: Formatted hex dump
    """
    start = max(0, offset - context)
    end = min(len(data), offset + context + 1)
    
    result = []
    for i in range(start, end, 16):
        # Address
        line = f"{i:08X}: "
        
        # Hex bytes
        chunk = data[i:min(i+16, end)]
        hex_part = ""
        for j, byte in enumerate(chunk):
            if i + j == offset:
                # Highlight the specific offset with markers
                hex_part += f"[{byte:02X}] "
            else:
                hex_part += f"{byte:02X} "
        
        # Pad hex part if needed
        hex_part = hex_part.ljust(3 * 16)
        
        # ASCII representation
        ascii_part = ""
        for byte in chunk:
            if 32 <= byte <= 126:  # Printable ASCII
                ascii_part += chr(byte)
            else:
                ascii_part += "."
        
        result.append(f"{line}{hex_part} |{ascii_part}|")
    
    return "\n".join(result)

def compare_roms(rom_a_path, rom_b_path, output_file=None):
    """
    Compare two ROM files and generate a detailed report of differences.
    
    Args:
        rom_a_path (str): Path to the first ROM file (A version)
        rom_b_path (str): Path to the second ROM file (B version)
        output_file (str, optional): Path to write the comparison report
    """
    # Create temporary directories to extract ROM files
    with tempfile.TemporaryDirectory() as temp_a, tempfile.TemporaryDirectory() as temp_b:
        print(f"Comparing ROM files:")
        print(f"  A: {rom_a_path}")
        print(f"  B: {rom_b_path}")
        
        # Extract files from both ROMs
        files_a = extract_rom_files(rom_a_path, temp_a)
        files_b = extract_rom_files(rom_b_path, temp_b)
        
        # Get sets of file paths for easy comparison
        paths_a = set(files_a.keys())
        paths_b = set(files_b.keys())
        
        # Files only in A
        only_in_a = paths_a - paths_b
        # Files only in B
        only_in_b = paths_b - paths_a
        # Files in both A and B
        common_files = paths_a.intersection(paths_b)
        
        # Open output file if specified
        if output_file:
            f_out = open(output_file, 'w')
            write = lambda s: f_out.write(s + '\n')
        else:
            write = print
        
        # Write report header
        write("\n" + "="*80)
        write("ROM COMPARISON REPORT")
        write("="*80)
        
        # Summary
        write(f"\nSUMMARY:")
        write(f"  ROM A: {rom_a_path}")
        write(f"  ROM B: {rom_b_path}")
        write(f"  Total files in A: {len(paths_a)}")
        write(f"  Total files in B: {len(paths_b)}")
        write(f"  Files only in A: {len(only_in_a)}")
        write(f"  Files only in B: {len(only_in_b)}")
        write(f"  Files in both ROMs: {len(common_files)}")
        
        # Files only in A
        if only_in_a:
            write(f"\nFILES ONLY IN ROM A:")
            for path in sorted(only_in_a):
                write(f"  - {path} ({len(files_a[path])} bytes)")
        
        # Files only in B
        if only_in_b:
            write(f"\nFILES ONLY IN ROM B:")
            for path in sorted(only_in_b):
                write(f"  - {path} ({len(files_b[path])} bytes)")
        
        # Compare common files
        write(f"\nDIFFERENCES IN COMMON FILES:")
        
        # Analyze NARC headers to find potential Pokémon ID changes
        potential_pokemon_changes = []
        
        # Track total differences for summary
        total_diff_files = 0
        total_diff_bytes = 0
        
        for path in sorted(common_files):
            data_a = files_a[path]
            data_b = files_b[path]
            
            # Skip identical files
            if data_a == data_b:
                continue
            
            total_diff_files += 1
            differences = compare_binaries(data_a, data_b)
            
            # Calculate difference percentage
            max_size = max(len(data_a), len(data_b))
            diff_count = sum(1 for d in differences if d['type'] == 'content')
            diff_percent = (diff_count / max_size) * 100 if max_size > 0 else 0
            
            total_diff_bytes += diff_count
            
            # Write file difference header
            write(f"\nFile: {path}")
            
            # Size difference
            size_diff = [d for d in differences if d['type'] == 'size']
            if size_diff:
                d = size_diff[0]
                write(f"  Size: A={d['a_size']} bytes, B={d['b_size']} bytes (Diff: {d['diff']} bytes)")
            
            # Content differences
            content_diffs = [d for d in differences if d['type'] == 'content']
            if content_diffs:
                write(f"  {len(content_diffs)} different bytes ({diff_percent:.2f}% of file)")
                
                # Keep track of potential Pokémon ID changes
                pokemon_changes = []
                
                # Show up to 20 byte differences in detail
                for i, d in enumerate(content_diffs[:20]):
                    write(f"  Offset {d['offset']:08X}: A={d['a_hex']} B={d['b_hex']}")
                    
                    # Check if this might be a Pokémon ID change
                    if d['pokemon_analysis']:
                        pokemon_info = d['pokemon_analysis']
                        write(f"    POSSIBLE POKEMON ID CHANGE: {pokemon_info['id_a']} → {pokemon_info['id_b']}")
                        pokemon_changes.append(pokemon_info)
                    
                    # For important differences (first few), show context
                    if i < 5:
                        write("\n  Context in ROM A:")
                        write(format_hex_dump(data_a, d['offset']))
                        write("\n  Context in ROM B:")
                        write(format_hex_dump(data_b, d['offset']))
                        write("")
                
                # Indicate if there are more differences not shown
                remaining = len(content_diffs) - 20
                if remaining > 0:
                    write(f"  ... and {remaining} more differences")
                    
                # Add potential Pokémon changes to the global list for summary
                if pokemon_changes:
                    for change in pokemon_changes:
                        potential_pokemon_changes.append({
                            'file': path,
                            'change': change
                        })
            
            # Truncated report note
            limit_info = [d for d in differences if d['type'] == 'limit']
            if limit_info:
                d = limit_info[0]
                write(f"  Note: Only showing {d['reported']} of {d['total_diffs']} total differences")
        
        # Summary of differences
        write("\n" + "="*80)
        write("DIFFERENCE SUMMARY:")
        write(f"  Different files: {total_diff_files} out of {len(common_files)} common files")
        write(f"  Total bytes changed: {total_diff_bytes}")
        
        # Add Pokemon analysis section if any potential Pokemon changes were found
        if potential_pokemon_changes:
            write("\n" + "="*80)
            write("POKEMON ANALYSIS:")
            write("  The following changes might be related to Pokemon IDs:")
            
            # Group changes by Pokemon IDs for easier analysis
            by_pokemon_ids = {}
            for item in potential_pokemon_changes:
                key = f"{item['change']['id_a']} to {item['change']['id_b']}"
                if key not in by_pokemon_ids:
                    by_pokemon_ids[key] = []
                by_pokemon_ids[key].append(item['file'])
            
            # Display grouped changes
            for change_key, files in by_pokemon_ids.items():
                ids = change_key.split(' to ')
                if len(ids) == 2:
                    id_a, id_b = int(ids[0]), int(ids[1])
                    write(f"\n  Pokemon ID {id_a} changed to {id_b} in {len(files)} locations:")
                    write(f"    - This could be a change from Pokemon #{id_a} to Pokemon #{id_b}")
                    write(f"    - Found in files: {', '.join(files[:3])}" + (", and others..." if len(files) > 3 else ""))
            
            write("\n  Note: This is based on simple pattern matching and may not be 100% accurate.")
            write("  Pokemon IDs in ROM files may be stored in various formats and structures.")
        
        write("="*80 + "\n")
        
        if output_file:
            f_out.close()
            print(f"Report saved to: {output_file}")

def main():
    """Main entry point for the script."""
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Compare two Nintendo DS ROM files and report differences.")
    parser.add_argument("rom_a", help="Path to the first ROM file (A version)")
    parser.add_argument("rom_b", help="Path to the second ROM file (B version)")
    parser.add_argument("-o", "--output", help="Output file for the comparison report (default: print to console)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate ROM files exist
    if not os.path.isfile(args.rom_a):
        print(f"Error: ROM file A not found: {args.rom_a}")
        return 1
    
    if not os.path.isfile(args.rom_b):
        print(f"Error: ROM file B not found: {args.rom_b}")
        return 1
    
    # Compare ROMs
    compare_roms(args.rom_a, args.rom_b, args.output)
    return 0

if __name__ == "__main__":
    sys.exit(main())
