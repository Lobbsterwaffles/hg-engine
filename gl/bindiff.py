import argparse
import hashlib
import sys
import os
from framework import *
import ndspy.rom
import ndspy.narc


class GenericNarcExtractor(NarcExtractor):
    """A generic NARC extractor that can work with any NARC path"""
    
    def __init__(self, rom, narc_path):
        self.rom = rom
        self.narc_path = narc_path
        # Load the NARC data immediately
        self.data = self.load_narc_raw()
    
    def get_narc_path(self):
        return self.narc_path
    
    def parse_file(self, file_data, index):
        # For binary diff purposes, we just return the raw bytes
        return file_data
    
    def serialize_file(self, data, index):
        # Return data as-is since we're working with raw bytes
        return data
    
    def write_to_rom(self):
        # Not needed for diff tool
        pass
    
    def load_narc_raw(self):
        """Load NARC and return raw file data"""
        try:
            narc_file_id = self.rom.filenames.idOf(self.narc_path)
            narc_file = self.rom.files[narc_file_id]
            narc_data = ndspy.narc.NARC(narc_file)
            return narc_data.files
        except Exception as e:
            print(f"Error loading NARC {self.narc_path}: {e}")
            sys.exit(1)


def load_rom(rom_path):
    """Load a ROM file"""
    try:
        with open(rom_path, "rb") as f:
            return ndspy.rom.NintendoDSRom(f.read())
    except Exception as e:
        print(f"Error loading ROM {rom_path}: {e}")
        sys.exit(1)


def calculate_sha256(data):
    """Calculate SHA256 hash of binary data"""
    return hashlib.sha256(data).hexdigest()


def print_single_rom_hashes(narc_extractor):
    """Print SHA256 hashes for all files in a single ROM"""
    print(f"SHA256 hashes for NARC: {narc_extractor.narc_path}")
    print("-" * 80)
    print(f"{'File Index':<10} {'SHA256 Hash'}")
    print("-" * 80)
    
    for i, file_data in enumerate(narc_extractor.data):
        hash_value = calculate_sha256(file_data)
        print(f"{i:<10} {hash_value}")


def compare_two_roms(narc1, narc2, show_diff=False):
    """Compare NARCs from two ROMs and show differences"""
    print(f"Comparing NARC: {narc1.narc_path}")
    print("-" * 100)
    print(f"{'File Index':<10} {'ROM1 Hash':<64} {'ROM2 Hash':<64} {'Status'}")
    print("-" * 100)
    
    max_files = max(len(narc1.data), len(narc2.data))
    differences_found = 0
    
    for i in range(max_files):
        # Handle cases where one ROM has more files than the other
        file1_data = narc1.data[i] if i < len(narc1.data) else None
        file2_data = narc2.data[i] if i < len(narc2.data) else None
        
        if file1_data is None:
            print(f"{i:<10} {'<missing>':<64} {calculate_sha256(file2_data):<64} {'ROM1 MISSING'}")
            differences_found += 1
        elif file2_data is None:
            print(f"{i:<10} {calculate_sha256(file1_data):<64} {'<missing>':<64} {'ROM2 MISSING'}")
            differences_found += 1
        else:
            hash1 = calculate_sha256(file1_data)
            hash2 = calculate_sha256(file2_data)
            
            if hash1 == hash2:
                status = "SAME"
            else:
                status = "DIFFERENT"
                differences_found += 1
                
                if show_diff:
                    print(f"{i:<10} {hash1:<64} {hash2:<64} {status}")
                    show_binary_diff(file1_data, file2_data, i)
                    print()
                else:
                    print(f"{i:<10} {hash1:<64} {hash2:<64} {status}")
            
            if not show_diff or hash1 == hash2:
                print(f"{i:<10} {hash1:<64} {hash2:<64} {status}")
    
    print("-" * 100)
    print(f"Total files compared: {max_files}")
    print(f"Files with differences: {differences_found}")


def show_binary_diff(data1, data2, file_index):
    """Show simple binary differences between two files"""
    print(f"  Binary differences in file {file_index}:")
    
    min_len = min(len(data1), len(data2))
    max_len = max(len(data1), len(data2))
    
    differences = []
    
    # Compare bytes up to the shorter length
    for i in range(min_len):
        if data1[i] != data2[i]:
            differences.append((i, data1[i], data2[i]))
    
    # Handle length differences
    if len(data1) != len(data2):
        print(f"    Length difference: ROM1={len(data1)} bytes, ROM2={len(data2)} bytes")
    
    # Show first 10 byte differences
    if differences:
        print(f"    Byte differences (showing first 10 of {len(differences)}):")
        for i, (offset, byte1, byte2) in enumerate(differences[:10]):
            print(f"      Offset 0x{offset:04X}: ROM1=0x{byte1:02X} ROM2=0x{byte2:02X}")
        
        if len(differences) > 10:
            print(f"      ... and {len(differences) - 10} more differences")
    else:
        print("    No byte differences found (files have same content but different lengths)")


def main():
    parser = argparse.ArgumentParser(
        description="Binary diff tool for NARCs in Nintendo DS ROMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show SHA256 hashes for all files in a NARC
  python bindiff.py "a/0/2/8" rom.nds
  
  # Compare the same NARC between two ROMs
  python bindiff.py "a/0/2/8" rom1.nds rom2.nds
  
  # Compare with detailed binary diff output
  python bindiff.py "a/0/2/8" rom1.nds rom2.nds --show-diff
        """
    )
    
    parser.add_argument("narc_path", help="Path to NARC within ROM (e.g., 'a/0/2/8')")
    parser.add_argument("rom1", help="First ROM file (.nds)")
    parser.add_argument("rom2", nargs="?", help="Second ROM file (.nds) for comparison")
    parser.add_argument("--show-diff", action="store_true", 
                       help="Show detailed binary differences for differing files")
    
    args = parser.parse_args()
    
    # Validate ROM files exist
    if not os.path.exists(args.rom1):
        print(f"Error: ROM file '{args.rom1}' not found")
        sys.exit(1)
    
    if args.rom2 and not os.path.exists(args.rom2):
        print(f"Error: ROM file '{args.rom2}' not found")
        sys.exit(1)
    
    # Load first ROM
    print(f"Loading ROM: {args.rom1}")
    rom1 = load_rom(args.rom1)
    narc1 = GenericNarcExtractor(rom1, args.narc_path)
    
    if args.rom2:
        # Two ROM comparison mode
        print(f"Loading ROM: {args.rom2}")
        rom2 = load_rom(args.rom2)
        narc2 = GenericNarcExtractor(rom2, args.narc_path)
        
        compare_two_roms(narc1, narc2, args.show_diff)
    else:
        # Single ROM hash mode
        print_single_rom_hashes(narc1)


if __name__ == "__main__":
    main()