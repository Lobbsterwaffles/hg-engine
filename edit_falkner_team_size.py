#!/usr/bin/env python3
"""
This script fixes Falkner's team size by:
1. Finding Falkner's trainer data in the ROM
2. Updating his poke_count value from 2 to 3
3. Saving the modified ROM

Use this with the ROM that already has the Spearow added to Falkner's Pokemon data.
"""
import ndspy.rom
import ndspy.narc
import sys
import os
import struct

def main():
    # Check if ROM path is provided
    if len(sys.argv) < 2:
        print("Usage: python edit_falkner_team_size.py <rom_file>")
        print("Note: Use this with a ROM that already has Spearow added to Falkner's team")
        sys.exit(1)
    
    rom_path = sys.argv[1]
    
    # Open the ROM
    print(f"Opening ROM file: {rom_path}...")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    
    # Get the trainer data NARC (this is different from the trainer Pokemon data)
    # The trainer data should be in a/0/5/5 based on the pattern
    print("Reading trainer data NARC...")
    trainer_data_path = "a/0/5/5"
    try:
        narc_file_id = rom.filenames.idOf(trainer_data_path)
        trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
        print(f"Found trainer data at {trainer_data_path}")
    except:
        print(f"Could not find trainer data at {trainer_data_path}, trying alternative paths...")
        # Try to find the trainer data by searching common paths
        possible_paths = ["a/0/5/4", "a/0/5/7", "a/0/9/1"]
        found = False
        for path in possible_paths:
            try:
                narc_file_id = rom.filenames.idOf(path)
                trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
                print(f"Found trainer data at {path}")
                trainer_data_path = path
                found = True
                break
            except:
                continue
        
        if not found:
            print("Could not find trainer data NARC. Let's try to locate it by content...")
            # Last resort: try to find it by searching for files with the right structure
            for path, file_id in rom.filenames.items():
                if not path.startswith("a/0/"): continue
                try:
                    data = rom.files[file_id]
                    # Check if this could be a NARC
                    if data[0:4] == b'NARC':
                        narc = ndspy.narc.NARC(data)
                        if len(narc.files) > 100:  # Trainer data should have many entries
                            # Check if it has the right structure
                            if len(narc.files[0]) >= 8 and len(narc.files[20]) >= 8:
                                print(f"Found potential trainer data at {path}")
                                trainer_data_narc = narc
                                trainer_data_path = path
                                narc_file_id = file_id
                                found = True
                                break
                except:
                    continue
            
            if not found:
                print("ERROR: Could not find trainer data in the ROM.")
                sys.exit(1)
    
    # Falkner is Trainer ID 20
    FALKNER_ID = 20
    
    # Get Falkner's current data
    falkner_data = trainer_data_narc.files[FALKNER_ID]
    print(f"Falkner's trainer data size: {len(falkner_data)} bytes")
    
    # Print the current data as hex for debugging
    print("Falkner's current trainer data (hex):")
    for i in range(0, len(falkner_data), 4):
        chunk = falkner_data[i:i+4]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        print(f"  {i:02X}: {hex_str}")
    
    # The trainer data structure might look like:
    # - trainer class
    # - event ID 
    # - items
    # - AI flags
    # - poke_count (this is what we need to change)
    
    # Let's try to identify where poke_count might be
    print("\nSearching for poke_count field (likely value: 02)...")
    
    # Based on the enemy_party.c code, poke_count is probably a byte value
    # Let's look for a byte with value 2 (since Falkner has 2 Pokémon)
    possible_offsets = []
    for i in range(len(falkner_data)):
        if falkner_data[i] == 2:
            possible_offsets.append(i)
    
    print(f"Found {len(possible_offsets)} bytes with value 2:")
    for offset in possible_offsets:
        print(f"  Offset {offset} (0x{offset:02X})")
    
    # Try all possible offsets
    roms_created = 0
    for offset in possible_offsets:
        # Create a copy of the data
        modified_data = bytearray(falkner_data)
        
        # Change the value from 2 to 3
        modified_data[offset] = 3
        
        # Update Falkner's data in the NARC
        trainer_data_narc.files[FALKNER_ID] = bytes(modified_data)
        
        # Update the ROM with the modified trainer data
        rom.files[narc_file_id] = trainer_data_narc.save()
        
        # Save to a new ROM file
        output_path = f"{rom_path.replace('.nds', '')}_falkner_offset{offset}.nds"
        print(f"\nSaving ROM with modification at offset {offset} to {output_path}...")
        rom.saveToFile(output_path)
        roms_created += 1
        
        # Reset for next iteration
        trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
    
    print(f"\nCreated {roms_created} ROMs with different modifications.")
    print("\nTry each ROM in an emulator to see which one correctly shows Falkner with 3 Pokémon.")
    print("Use check_trainer_pokemon_count.py on each ROM to verify the changes.")

if __name__ == "__main__":
    main()
