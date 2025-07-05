"""
Test script to check ROM Pokémon data structure
"""
import ndspy.rom
import ndspy.narc
import sys

# Simple function to print hexadecimal representation of binary data
def print_hex(data, max_bytes=32):
    hex_str = ' '.join(f'{b:02x}' for b in data[:max_bytes])
    if len(data) > max_bytes:
        hex_str += f' ... ({len(data)} bytes total)'
    return hex_str

# Main function
def main():
    print("Testing ROM Pokémon data structure...")
    
    # Check if ROM path is provided
    rom_path = 'lancecanarynoexp.nds'
    
    try:
        # Load the ROM
        print(f"Loading ROM from {rom_path}...")
        rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
        
        # Access the Pokémon data NARC
        narc_file_id = rom.filenames.idOf("a/0/0/2")
        print(f"Found Pokémon data NARC at ID {narc_file_id}")
        
        encounter_narc = rom.files[narc_file_id]
        narc_data = ndspy.narc.NARC(encounter_narc)
        
        print(f"NARC contains {len(narc_data.files)} files")
        
        # Check a few Pokémon files
        for species_id in [1, 4, 7, 25]:  # Bulbasaur, Charmander, Squirtle, Pikachu
            if species_id < len(narc_data.files):
                pokemon_data = narc_data.files[species_id]
                print(f"\nPokémon #{species_id} data:")
                print(f"  Size: {len(pokemon_data)} bytes")
                print(f"  Data: {print_hex(pokemon_data)}")
                
                # If data is too small, this is likely our issue
                if len(pokemon_data) < 28:  # Our struct expects at least 28 bytes
                    print("  WARNING: Data size too small for our struct!")
            else:
                print(f"\nPokémon #{species_id} not found in NARC")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
