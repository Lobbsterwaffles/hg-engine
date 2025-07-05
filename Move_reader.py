"""
move_reader.py - Read move data from HeartGold/SoulSilver ROM
This program reads the move data structure from a ROM file and prints all moves.
Based on the structure defined in armips/include/movemacros.s
"""

from construct import *
import ndspy.rom
import ndspy.narc
import sys
import os

# Define the move data structure based on armips/include/movemacros.s
move_struct = Struct(
    "effect" / Int16ul,            # Battle effect (halfword = 2 bytes)
    "category" / Int8ul,           # Physical/Special split (byte = 1 byte)
    "power" / Int8ul,              # Base power (byte = 1 byte)
    "type" / Int8ul,               # Move type (byte = 1 byte)
    "accuracy" / Int8ul,           # Accuracy (byte = 1 byte)
    "pp" / Int8ul,                 # PP (byte = 1 byte)
    "effect_chance" / Int8ul,      # Effect chance (byte = 1 byte)
    "target" / Int16ul,            # Target range (halfword = 2 bytes)
    "priority" / Int8ul,           # Priority (byte = 1 byte)
    "flags" / Int8ul,              # Flags (byte = 1 byte)
    "appeal" / Int8ul,             # Contest appeal (byte = 1 byte)
    "contest_type" / Int8ul,       # Contest type (byte = 1 byte)
    "padding" / Int16ul,           # Padding at the end (16 bits/2 bytes)
)

# Define constants for move categories
CATEGORY_NAMES = {
    0: "Physical",
    1: "Special",
    2: "Status"
}

# Define constants for move types
TYPE_NAMES = {
    0: "Normal", 1: "Fighting", 2: "Flying", 3: "Poison", 4: "Ground",
    5: "Rock", 6: "Bug", 7: "Ghost", 8: "Steel", 9: "Fire",
    10: "Water", 11: "Grass", 12: "Electric", 13: "Psychic", 14: "Ice",
    15: "Dragon", 16: "Dark", 17: "Fairy"
}

# Define move target types
TARGET_NAMES = {
    0: "Single",
    1: "Special",
    2: "Random",
    4: "AllAdj",
    8: "AllFoe",
    16: "User",
    32: "UserSide",
    64: "Field",
    128: "FoeSide"
}

def read_move_names(base_path):
    """Read move names from text files in ROM if possible"""
    try:
        # Based on movemacros.s, move names are in file 750
        with open(os.path.join(base_path, "build/rawtext/750.txt"), "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        # Try alternate location
        try:
            with open(os.path.join(base_path, "build/rawtext/58.txt"), "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            print("Move name file not found. Using generic names.")
            return [f"Move {i}" for i in range(1000)]  # Just a placeholder

def parse_move_data(data):
    """Parse move data from binary data"""
    try:
        move = move_struct.parse(data)
        return move
    except Exception as e:
        print(f"Error parsing move data: {e}")
        return None

def read_moves(rom, base_path="."):
    """Read all move data from ROM"""
    # Based on movemacros.s, moves are in a011 NARC
    try:
        # First try the a011 location (from movemacros.s)
        narc_file_id = rom.filenames.idOf("a/0/1/1")
        move_narc = rom.files[narc_file_id]
    except ValueError:
        # If not found, search for potential move data files
        print("Standard move data location not found. Searching for possible alternatives...")
        potential_files = []
        for file_id, file_path in rom.filenames.items():
            if "move" in file_path.lower() or "a011" in file_path.lower():
                print(f"Potential move data file: {file_path} (ID: {file_id})")
                potential_files.append((file_id, file_path))
                
        if not potential_files:
            # List all available files as a last resort
            print("No move files found. Listing all available files:")
            for i, (file_id, file_path) in enumerate(rom.filenames.items()):
                print(f"{file_id}: {file_path}")
                if i > 30:  # Limit to first 30 files to avoid excessive output
                    print("...(more files)...")
                    break
            return []
        
        # Try the first potential file
        narc_file_id = potential_files[0][0]
        move_narc = rom.files[narc_file_id]
    
    # Load the move data NARC
    move_narc_data = ndspy.narc.NARC(move_narc)
    print(f"Found {len(move_narc_data.files)} move entries in ROM")
    
    # Read move names if possible
    move_names = read_move_names(base_path)
    
    # Parse each move entry
    moves = []
    for i, data in enumerate(move_narc_data.files):
        move = parse_move_data(data)
        if move:
            # Add name and index
            move.index = i
            move.name = move_names[i] if i < len(move_names) else f"Move {i}"
            moves.append(move)
    
    return moves

def print_move_details(moves):
    """Print detailed information about all moves"""
    print("\n=== MOVE DATA ===")
    print(f"Total moves: {len(moves)}")
    
    # Print table header
    print(f"\n{'ID':<4} {'Name':<20} {'Type':<10} {'Cat':<8} {'Pow':<4} {'Acc':<4} {'PP':<3} {'Effect':<6} {'Chance':<6} {'Target':<6} {'Prio':<5} {'Flags':<10}")
    print("-" * 100)
    
    # Print each move
    for move in moves:
        type_name = TYPE_NAMES.get(move.type, f"Type{move.type}")
        category = CATEGORY_NAMES.get(move.category, f"Cat{move.category}")
        
        # Get target name or value
        target_value = move.target
        target_display = ""
        for bit, name in TARGET_NAMES.items():
            if target_value & bit:
                if target_display:
                    target_display += "+"
                target_display += name
        if not target_display:
            target_display = str(target_value)
            
        print(f"{move.index:<4} {move.name:<20} {type_name:<10} {category:<8} "
              f"{move.power if move.power else '-':<4} "
              f"{move.accuracy if move.accuracy else '-':<4} "
              f"{move.pp:<3} {move.effect:<6} {move.effect_chance:<6}% "
              f"{target_display:<6} {move.priority:<5} {hex(move.flags):<10}")

def main():
    """Main function for reading move data from ROM"""
    if len(sys.argv) < 2:
        print("Usage: python move_reader.py <rom_path>")
        return
    
    rom_path = sys.argv[1]
    if not os.path.exists(rom_path):
        print(f"Error: ROM file '{rom_path}' not found.")
        return
    
    print(f"Opening ROM file: {rom_path}")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Get the base path (directory containing the ROM)
    base_path = os.path.dirname(os.path.abspath(rom_path))
    
    moves = read_moves(rom, base_path)
    if moves:
        print_move_details(moves)
    else:
        print("No move data could be read from the ROM.")

if __name__ == "__main__":
    main()