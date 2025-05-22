#!/usr/bin/env python3

"""
Pokémon Encounter Randomizer using ndspy

This version uses the ndspy library to handle NDS ROM files directly,
without requiring external tools like ndstool.
"""

import os
import sys
import random
import tempfile
import shutil
import argparse
import logging

# Set up detailed logging to both console and file
logging.basicConfig(
    level=logging.DEBUG,  # Show all log levels
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("randomizer_debug.log"),  # Save logs to a file
        logging.StreamHandler()  # Also show logs in console
    ]
)
import json
import traceback  # Added for detailed stack traces
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QProgressBar, QTextEdit,
    QCheckBox, QSpinBox, QComboBox, QGroupBox, QFormLayout,
    QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import ndspy.rom
import ndspy.narc
import struct
from pokemon_rom_reader import IGNORED_POKEMON_IDS  # Import our list of Pokémon to ignore

# Settings file to remember user preferences
SETTINGS_FILE = "randomizer_settings.json"

# List of Pokémon that should not be replaced when randomizing
# This includes legendary Pokémon, special story-related Pokémon, and our ignored IDs
SPECIAL_POKEMON = [
    # Legendaries and special Pokémon
    150, 151,  # Mewtwo, Mew
    243, 244, 245,  # Raikou, Entei, Suicune
    249, 250, 251,  # Lugia, Ho-Oh, Celebi
    377, 378, 379, 380, 381, 382, 383, 384, 385, 386,  # Gen 3 legendaries
    480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494,  # Gen 4 legendaries
    # Also include all our ignored Pokémon IDs
    *IGNORED_POKEMON_IDS
]

# Load saved settings from file
def load_settings():
    """Load user settings from the settings file."""
    default_settings = {
        "last_rom_path": "",
        "use_similar_strength": True
    }
    
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
            return settings
        return default_settings
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return default_settings

# Save settings to file
def save_settings(settings):
    """Save user settings to the settings file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        # Continue without saving settings - not critical

# Import the ROM reader to get Pokémon data directly from the ROM
from pokemon_rom_reader import get_pokemon_data

# Import our Pokémon name lookup function
from pokemon_names import get_pokemon_name, POKEMON_NAMES

# Special Pokémon that should not be randomized (legendaries, special Pokémon)
SPECIAL_POKEMON = [
    144, 145, 146,  # Articuno, Zapdos, Moltres
    150, 151,       # Mewtwo, Mew
    243, 244, 245,  # Raikou, Entei, Suicune
    249, 250, 251,  # Lugia, Ho-Oh, Celebi
    # Add any other special Pokémon you don't want randomized
]

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Paths to the NARCs containing encounter data (in the NDS file system)
# HeartGold/SoulSilver store encounters in multiple files
ENCOUNTER_NARC_PATHS = [
    'a/0/3/7',    # Main wild encounters
    'a/0/3/9',    # Possible additional encounters
    'a/0/4/0',    # Possible additional encounters
    'a/0/4/1',    # Possible headbutt encounters
    'a/0/4/2',    # Possible fishing/surfing encounters
]

class RandomizerThread(QThread):
    """Thread for running the randomization process without freezing the GUI."""
    progress_update = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, rom_path, output_path, seed=None, similar_strength=True):
        super().__init__()
        self.rom_path = rom_path
        self.output_path = output_path
        self.seed = seed
        self.similar_strength = similar_strength

    def run(self):
        try:
            result = randomize_encounters(
                self.rom_path, 
                self.output_path, 
                self.seed, 
                self.similar_strength,
                update_callback=self.progress_update.emit,
                progress_callback=self.progress_value.emit
            )
            self.finished_signal.emit(True, f"Randomization completed successfully!\nOutput saved to: {result}")
        except Exception as e:
            # Get the full stack trace as a string
            error_traceback = traceback.format_exc()
            
            # Log the full error details
            logger.error(f"Error during randomization: {e}\n{error_traceback}")
            
            # Show a more detailed error message to the user
            error_message = f"Randomization failed: {str(e)}\n\nFull Error Details (for debugging):\n{error_traceback}"
            self.finished_signal.emit(False, error_message)

def find_similar_pokemon(species_id, mapping, replacement_counts, similar_strength=True, pokemon_data=None, max_reuse=5):
    """Find a similar-strength Pokémon to replace the original.
    
    Args:
        species_id: The ID of the Pokémon to replace
        mapping: Dictionary mapping original IDs to replacement IDs
        replacement_counts: Dictionary tracking how many times each Pokémon has been used
        similar_strength: Whether to find a Pokémon with similar stats
        pokemon_data: Dictionary with Pokémon data from the ROM
        max_reuse: Maximum number of times a Pokémon can be used as a replacement
        
    Returns:
        ID of the replacement Pokémon
    """
    # If already mapped, use consistent replacement
    if species_id in mapping:
        return mapping[species_id]
    
    # Don't replace special Pokémon
    if species_id in SPECIAL_POKEMON:
        return species_id
    
    # Skip if we don't have Pokémon data
    if not pokemon_data:
        return species_id
        
    # Skip if not in our database
    if species_id not in pokemon_data:
        return species_id
    
    if similar_strength:
        # WEIGHTED RANDOMIZATION: Find Pokémon with similar strength based on Base Stat Total (BST)
        # BST is the sum of all six stats (HP, Attack, Defense, Speed, Special Attack, Special Defense)
        
        # Get the original Pokémon's BST from the ROM data
        original_bst = pokemon_data[species_id]["bst"]
        
        # Allow a range of 15% higher or lower for variety
        # Example: If original BST is 400, we'll accept 340-460
        min_bst = original_bst * 0.85  # 15% lower
        max_bst = original_bst * 1.15  # 15% higher
        
        # Create a list of potential replacement Pokémon
        candidates = []
        candidate_weights = []  # For weighted selection based on similarity
        
        # Check each Pokémon in our data
        for pid, data in pokemon_data.items():
            # Skip special Pokémon (legendaries) and the original species
            if pid in SPECIAL_POKEMON or pid == species_id:
                continue
                
            # Check if this Pokémon has been used too many times already
            # This helps create more variety in our randomization
            times_used = replacement_counts.get(pid, 0)
            
            # Skip if we've already used this Pokémon too many times
            # But be less strict if we don't have many candidates yet
            if times_used >= max_reuse and len(candidates) > 10:
                continue
                
            # Check if BST is in the acceptable range
            if min_bst <= data["bst"] <= max_bst:
                candidates.append(pid)  # Add to our list of candidates
                
                # Calculate a weight based on how close the BST is to the original
                # Closer matches get higher weights for better balance
                bst_difference = abs(data["bst"] - original_bst)
                similarity = 1.0 - (bst_difference / (original_bst * 0.15))
                candidate_weights.append(max(0.1, similarity))  # Minimum weight of 0.1
    else:
        # If similar_strength is False, just pick any valid Pokémon (not weighted)
        # Make sure to exclude special Pokémon, eggs, and placeholders
        candidates = [pid for pid in pokemon_data.keys() 
                      if pid != species_id and 
                         pid not in SPECIAL_POKEMON and
                         pid not in IGNORED_POKEMON_IDS]
        candidate_weights = None  # No weights for random selection
    
    # Choose random replacement if we have candidates
    if candidates:
        # If we have weights, use weighted random selection
        # This means Pokémon more similar to the original are more likely to be chosen
        if similar_strength and candidate_weights:
            # random.choices returns a list of selections, so we use [0] to get the first one
            replacement = random.choices(candidates, weights=candidate_weights, k=1)[0]
            
            # Log the replacement for debugging
            if pokemon_data and species_id in pokemon_data and replacement in pokemon_data:
                orig_name = pokemon_data[species_id].get('name', f'POKEMON_{species_id}')
                new_name = pokemon_data[replacement].get('name', f'POKEMON_{replacement}')
                orig_bst = pokemon_data[species_id].get('bst', 0)
                new_bst = pokemon_data[replacement].get('bst', 0)
                logger.debug(f"Replaced {orig_name} (BST: {orig_bst}) with {new_name} (BST: {new_bst})")
        else:
            # Otherwise use regular random selection
            replacement = random.choice(candidates)
        
        # Track how many times this Pokémon has been used as a replacement
        # This helps us create more variety in the randomization
        replacement_counts[replacement] = replacement_counts.get(replacement, 0) + 1
        
        # Store this replacement for consistency (same species always replaced by same Pokémon)
        mapping[species_id] = replacement
        
        # Log this replacement
        if pokemon_data and species_id in pokemon_data and replacement in pokemon_data:
            orig_name = pokemon_data[species_id].get('name', f'POKEMON_{species_id}')
            new_name = pokemon_data[replacement].get('name', f'POKEMON_{replacement}')
            logger.debug(f"Replaced {orig_name} with {new_name} (used {replacement_counts[replacement]} times)")
            
        return replacement
    
    # If we get here, we couldn't find a replacement within the BST range
    # As a fallback, we'll use any valid Pokémon that isn't special, ignored, or the original
    # Try to find Pokémon that haven't been used too much yet
    all_options = [pid for pid in pokemon_data.keys() 
                  if pid != species_id and 
                     pid not in SPECIAL_POKEMON and 
                     pid not in IGNORED_POKEMON_IDS and
                     replacement_counts.get(pid, 0) < max_reuse]
    
    if all_options:
        logger.info(f"Couldn't find similar-strength replacement for {species_id}, using any available Pokémon")
        replacement = random.choice(all_options)
        
        # Track this replacement
        replacement_counts[replacement] = replacement_counts.get(replacement, 0) + 1
        mapping[species_id] = replacement
        
        return replacement
    
    # Absolute fallback - if we can't find ANY replacement, return the original species
    # This should almost never happen unless we've used every possible Pokémon
    logger.warning(f"No replacement found for Pokémon #{species_id}, keeping original")
    return species_id

def find_pokemon_in_encounter_file(data):
    """Find all Pokémon species in an encounter file using the exact format.
    
    Based on the macros.s file, the encounter data has this structure:
    - Bytes 0-7: Header with walkrate, surfrate, etc.
    - Bytes 8-19: 12 level values for each slot
    - Byte 20+: The actual encounters
    
    Encounters can be in two formats:
    1. Just "pokemon SPECIES_X" (2 bytes) for morning/day/night slots
    2. "encounter SPECIES_X, level1, level2" (4 bytes) for water/fishing entries
    
    Each 4-byte encounter is [minlevel, maxlevel, species_lo, species_hi]
    """
    offsets = []
    
    # Check if this looks like a valid encounter file
    # We need at least 20 bytes (header + levels)
    if len(data) < 20:
        return offsets
    
    # Check if header values are reasonable
    walkrate = data[0]
    surfrate = data[1]
    rocksmashrate = data[2]
    oldrodrate = data[3]
    goodrodrate = data[4]
    superrodrate = data[5]
    
    # Valid rate values should be in a reasonable range (0-100)
    valid_rates = all(0 <= rate <= 100 for rate in 
                      [walkrate, surfrate, rocksmashrate, 
                       oldrodrate, goodrodrate, superrodrate])
    
    if not valid_rates:
        return offsets
    
    # Check levels at offset 8-19 (should all be 2-100)
    levels_valid = all(2 <= level <= 100 for level in data[8:20])
    if not levels_valid:
        return offsets
    
    # Now we know this is a properly formatted encounter file!
    # Process the encounter data in the expected format
    
    # Starting offset for encounters is 20 (header + level bytes)
    current_offset = 20
    
    # ---------------------------------------------
    # 1. First handle morning/day/night encounters
    # ---------------------------------------------
    # Each time slot has 12 entries, and each entry is 2 bytes (just species ID)
    # Process morning, day, and night slots (36 total Pokémon)
    slots_to_process = 36 if walkrate > 0 else 0
    for i in range(slots_to_process):
        # Make sure we don't go past the end of the file
        if current_offset + 1 >= len(data):
            break
            
        # Get the species value (2 bytes, little-endian)
        species_val = data[current_offset] | (data[current_offset + 1] << 8)
        species_id = species_val & 0x7FF  # Lower 11 bits are the species ID
        
        # If it's a valid species, add to our list
        if 1 <= species_id <= 1000:
            offsets.append(current_offset)
            
        current_offset += 2
    
    # ---------------------------------------------
    # 2. Next, process all other encounter types
    # ---------------------------------------------
    
    # The structure repeats for each encounter type, with different counts:
    # - 2 Hoenn radio slots
    # - 2 Sinnoh radio slots
    # - 5 surf encounters
    # - 5 old rod encounters  
    # - 5 good rod encounters
    # - 5 super rod encounters
    # - 2 rock smash encounters
    # - 4 headbutt tree encounters
    
    # Each special encounter is 4 bytes: [minlevel, maxlevel, species_lo, species_hi]
    # Process radio encounters (2 hoenn + 2 sinnoh = 4 total)
    slots_to_process = 4
    for i in range(slots_to_process):
        # Make sure we don't go past the end of the file
        if current_offset + 3 >= len(data):
            break
            
        # Check if it's a valid level range
        min_level = data[current_offset]
        max_level = data[current_offset + 1]
        
        # Get the species ID (last 2 bytes)
        species_offset = current_offset + 2
        species_val = data[species_offset] | (data[species_offset + 1] << 8)
        species_id = species_val & 0x7FF  # Lower 11 bits are the species ID
        
        # Make sure it's a valid entry
        if 2 <= min_level <= 100 and min_level <= max_level <= 100 and 1 <= species_id <= 1000:
            offsets.append(species_offset)
            
        current_offset += 4
    
    # Process water-based encounters (surfing)
    if surfrate > 0:
        slots_to_process = 5  # 5 surf encounters
        for i in range(slots_to_process):
            if current_offset + 3 >= len(data):
                break
                
            # Check if it's a valid level range
            min_level = data[current_offset]
            max_level = data[current_offset + 1]
            
            # Get the species ID (last 2 bytes)
            species_offset = current_offset + 2
            species_val = data[species_offset] | (data[species_offset + 1] << 8)
            species_id = species_val & 0x7FF  # Lower 11 bits are the species ID
            
            # Make sure it's a valid entry
            if 2 <= min_level <= 100 and min_level <= max_level <= 100 and 1 <= species_id <= 1000:
                offsets.append(species_offset)
                
            current_offset += 4
    
    # Process fishing encounters (old rod)
    if oldrodrate > 0:
        slots_to_process = 5  # 5 old rod encounters
        for i in range(slots_to_process):
            if current_offset + 3 >= len(data):
                break
                
            # Check if it's a valid level range
            min_level = data[current_offset]
            max_level = data[current_offset + 1]
            
            # Get the species ID (last 2 bytes)
            species_offset = current_offset + 2
            species_val = data[species_offset] | (data[species_offset + 1] << 8)
            species_id = species_val & 0x7FF  # Lower 11 bits are the species ID
            
            # Make sure it's a valid entry
            if 2 <= min_level <= 100 and min_level <= max_level <= 100 and 1 <= species_id <= 1000:
                offsets.append(species_offset)
                
            current_offset += 4
    
    # Process fishing encounters (good rod)
    if goodrodrate > 0:
        slots_to_process = 5  # 5 good rod encounters
        for i in range(slots_to_process):
            if current_offset + 3 >= len(data):
                break
                
            # Get the species ID (last 2 bytes)
            species_offset = current_offset + 2
            species_val = data[species_offset] | (data[species_offset + 1] << 8)
            species_id = species_val & 0x7FF  # Lower 11 bits are the species ID
            
            # Make sure it's a valid entry
            if 1 <= species_id <= 1000:
                offsets.append(species_offset)
                
            current_offset += 4
    
    # Process fishing encounters (super rod)
    if superrodrate > 0:
        slots_to_process = 5  # 5 super rod encounters
        for i in range(slots_to_process):
            if current_offset + 3 >= len(data):
                break
                
            # Get the species ID (last 2 bytes)
            species_offset = current_offset + 2
            species_val = data[species_offset] | (data[species_offset + 1] << 8)
            species_id = species_val & 0x7FF  # Lower 11 bits are the species ID
            
            # Make sure it's a valid entry
            if 1 <= species_id <= 1000:
                offsets.append(species_offset)
                
            current_offset += 4
    
    # Process rock smash encounters
    if rocksmashrate > 0:
        slots_to_process = 2  # 2 rock smash encounters
        for i in range(slots_to_process):
            if current_offset + 3 >= len(data):
                break
                
            # Get the species ID (last 2 bytes)
            species_offset = current_offset + 2
            species_val = data[species_offset] | (data[species_offset + 1] << 8)
            species_id = species_val & 0x7FF  # Lower 11 bits are the species ID
            
            # Make sure it's a valid entry
            if 1 <= species_id <= 1000:
                offsets.append(species_offset)
                
            current_offset += 4
    
    # Return all the offsets where we found valid Pokémon
    return offsets

def randomize_encounters(rom_path, output_path=None, seed=None, similar_strength=True,
                         update_callback=None, progress_callback=None):
    """
    Main function to randomize wild encounters in a ROM.
    
    Args:
        rom_path: Path to the ROM file
        output_path: Where to save the randomized ROM (default: *_randomized.nds)
        seed: Random seed for reproducible results
        similar_strength: Whether to replace Pokémon with others of similar strength
        update_callback: Function to call with status updates
        progress_callback: Function to call with progress percentage
    
    Returns:
        Path to the output ROM
    """
    
    # Set up output path if not provided
    if output_path is None:
        base, ext = os.path.splitext(rom_path)
        output_path = f"{base}_randomized{ext}"
    
    # Load Pokémon data directly from the ROM
    if update_callback:
        update_callback("Loading Pokémon data from ROM...")
    
    # This reads the actual Pokémon data from the ROM instead of using hardcoded values
    # Including actual Pokémon names is CRUCIAL for our logs
    POKEMON_BST = get_pokemon_data(rom_path)
    
    # Check if we got proper names - this is important for beginners to understand what's happening
    names_found = sum(1 for data in POKEMON_BST.values() 
                     if "name" in data and data["name"] and 
                        not data["name"].startswith("POKEMON_") and 
                        not data["name"].startswith("SPECIES_"))
    
    if update_callback:
        update_callback(f"Found data for {len(POKEMON_BST)} Pokémon in ROM")
        update_callback(f"Found {names_found} Pokémon with proper names")
        
        # Give helpful information if we didn't find many names
        if names_found < 100:
            update_callback("Warning: Not many Pokémon names were found in ROM.")
            update_callback("The log will use ID numbers for some Pokémon.")
        else:
            update_callback("Successfully loaded Pokémon names for the log file!")
    
    # Initialize random seed
    if seed is not None:
        random.seed(seed)
        if update_callback:
            update_callback(f"Using random seed: {seed}")
    else:
        seed = random.randrange(100000)
        random.seed(seed)
        if update_callback:
            update_callback(f"Using random seed: {seed}")
    
    try:
        if update_callback:
            update_callback("Loading ROM file...")
        if progress_callback:
            progress_callback(10)
        
        # Load the ROM file using ndspy
        rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
        
        if update_callback:
            update_callback("Extracting encounter data...")
        if progress_callback:
            progress_callback(30)
        
        # Get the encounter NARC file from the ROM
        try:
            # We'll focus on the main encounter NARC file (a/0/3/7)
            # This contains all wild Pokémon encounters in the game
            narc_file_id = rom.filenames.idOf(ENCOUNTER_NARC_PATHS[0])
            if narc_file_id is None:
                raise FileNotFoundError(f"Could not find encounter NARC at {ENCOUNTER_NARC_PATHS[0]}")
            
            narc_data = rom.files[narc_file_id]
            encounters_narc = ndspy.narc.NARC(narc_data)
            
            if update_callback:
                update_callback(f"Found encounter data with {len(encounters_narc.files)} location tables")
                
        except Exception as e:
            raise Exception(f"Error extracting encounter data: {e}")
        
        if update_callback:
            update_callback("Randomizing encounters...")
        if progress_callback:
            progress_callback(50)
        
        # Variables to track our mapping and replacements
        mapping = {}  # This dictionary keeps track of what Pokémon replaces what
                     # For example, mapping[16] = 165 means "replace Pidgey with Ledyba"
        
        # We limit how many times a single Pokémon can be used as a replacement
        # to ensure more variety
        replacement_counts = {}  # Counts how many times each Pokémon has been used
        max_reuse = 5  # Maximum times a single Pokémon can be used as a replacement
        used = set()
        
        # Track how many Pokémon we found and changed
        total_pokemon_found = 0
        
        # List to store detailed change information for logging
        pokemon_changes = []
        
        # A dictionary to track the most common Pokémon replacements
        # This will store how many times each Pokémon was replaced with another
        # Initialize this here to avoid the "string indices must be integers" error
        most_common_replacements = {}
        
        # This section is critical for finding all Pokémon!
        # We need to understand the exact data format
        
        # From analyzing the encounters.s file, we know there are 12 Pokémon each for:
        # - Morning encounters
        # - Day encounters
        # - Night encounters
        # - Then 2 for Hoenn radio
        # - 2 for Sinnoh radio
        # - 5 for surf
        # - 2 for rock smash
        # - 5 each for old/good/super fishing rod
        # - 4 for swarm encounters
        
        # Let's record these exact structures to find all Pokémon
        
        # Parse each encounter file in the NARC
        total_files = len(encounters_narc.files)
        
        if update_callback:
            update_callback(f"Found {total_files} encounter tables to randomize...")
            
        # Track how many Pokémon we found and changed
        total_pokemon_found = 0
        
        for i, file_data in enumerate(encounters_narc.files):
            # Skip empty files
            if not file_data:
                continue
            
            if update_callback and i % 10 == 0:  # Update every 10 files to avoid too many messages
                update_callback(f"Processing encounter table {i+1} of {total_files}...")
                
            # Convert the file data to a modifiable form
            modified_data = bytearray(file_data)
            
            # Skip files that are too small
            if len(modified_data) < 4:
                continue
            
            # Find all Pokémon offsets using our exact format knowledge
            pokemon_offsets = find_pokemon_in_encounter_file(modified_data)
            total_offsets = len(pokemon_offsets)  # For progress logs
            
            # Progress reporting - let the user know what we're finding
            if (total_offsets > 0) and update_callback and i % 25 == 0:
                update_callback(f"Location #{i}: Found {total_offsets} Pokémon entries")
            
            # Track changes for this location
            location_changes = 0
            location_species_ids = set()

            # Now replace ALL Pokémon encounters at the detected offsets
            for offset in pokemon_offsets:
                val = modified_data[offset] | (modified_data[offset + 1] << 8)
                species_id = val & 0x7FF
                
                # Skip invalid entries, SPECIES_NONE (species_id == 0), and our ignored Pokémon
                if species_id == 0 or species_id in IGNORED_POKEMON_IDS:
                    continue
                    
                # Also skip special Pokémon we don't want to replace (legendaries, etc.)
                if species_id in SPECIAL_POKEMON:
                    if update_callback and i % 50 == 0:  # Don't show too many messages
                        update_callback(f"Keeping special Pokémon: {species_id}")
                    continue
                    
                # IMPORTANT: We need to randomize ALL species, even if we don't recognize them
                # For species not in our database, we'll assign a default BST
                if species_id not in POKEMON_BST:
                    # Add this species to our database with a default BST of 350
                    POKEMON_BST[species_id] = {"name": f"SPECIES_{species_id}", "bst": 350}
                
                # Find a replacement Pokémon, passing our ROM-loaded Pokémon data
                # Also pass our replacement_counts dictionary to track variety
                new_species = find_similar_pokemon(
                    species_id,
                    mapping, 
                    replacement_counts,
                    similar_strength, 
                    POKEMON_BST,
                    max_reuse
                )
                
                # Apply the change to the data
                new_val = (val & 0xF800) | (new_species & 0x7FF)
                struct.pack_into('<H', modified_data, offset, new_val)
                
                # Count this change
                total_pokemon_found += 1
                location_changes += 1
                location_species_ids.add(species_id)
                
                # Record this change for the log if it's actually different
                if species_id != new_species:
                    # Get Pokémon names for the log using our dedicated names module
                    # This is much more reliable than trying to extract names from the ROM
                    
                    # Use our get_pokemon_name function to get proper names
                    original_name = get_pokemon_name(species_id)
                    new_name = get_pokemon_name(new_species)
                    
                    # Get BST (Base Stat Total) if available in the Pokémon data
                    if species_id in POKEMON_BST and "bst" in POKEMON_BST[species_id]:
                        original_bst = POKEMON_BST[species_id]["bst"]
                    else:
                        original_bst = "???"
                    
                    if new_species in POKEMON_BST and "bst" in POKEMON_BST[new_species]:
                        new_bst = POKEMON_BST[new_species]["bst"]
                    else:
                        new_bst = "???"
                    
                    # Log a message if we're still using unknown Pokémon names
                    if "UNKNOWN" in original_name or "UNKNOWN" in new_name:
                        print(f"Note: Using placeholder name for Pokémon ID {species_id} or {new_species}.")
                    
                    # Create a nice user-friendly log entry
                    change_info = f"{original_name} (BST: {original_bst}) → {new_name} (BST: {new_bst})"
                    pokemon_changes.append(change_info)
                    
                    # Show real-time updates in the UI
                    if update_callback and len(pokemon_changes) % 10 == 0:
                        update_callback(f"Replacing: {original_name} → {new_name}")
                    
                    # Keep track of the most common replacements for summary
                    key = f"{original_name} → {new_name}"
                    most_common_replacements[key] = most_common_replacements.get(key, 0) + 1
            
            # Report detailed changes for this location if significant
            if location_changes > 0 and update_callback:
                if i % 25 == 0 or location_changes > 20:  # Show more details for important locations
                    update_callback(f"Location #{i}: Changed {location_changes} encounters, {len(location_species_ids)} unique species")
            
            # Update the file in the NARC
            encounters_narc.files[i] = bytes(modified_data)
            
            # Update progress
            if progress_callback and total_files > 0:
                progress_value = 50 + (i / total_files) * 40
                progress_callback(int(progress_value))
        
        if update_callback:
            update_callback("Rebuilding ROM...")
        if progress_callback:
            progress_callback(90)
        
        # Update the NARC in the ROM
        rom.files[narc_file_id] = encounters_narc.save()
        
        # Save the modified ROM
        rom.saveToFile(output_path)
        
        # Create a log file with the changes
        log_path = os.path.splitext(output_path)[0] + "_changes.txt"
        
        if update_callback:
            update_callback(f"Creating change log at {log_path}...")
            update_callback(f"Found and processed {total_pokemon_found} total Pokémon entries!")
        
        # Sort changes alphabetically by original Pokémon name
        # Note: we now store changes as strings, not dictionaries
        pokemon_changes.sort()
        
        # Count unique species that were randomized
        unique_original_species = set()
        unique_new_species = set()
        
        # Calculate this from our string-based changes now
        for change_info in pokemon_changes:
            # These are now strings like "BULBASAUR (BST: 318) → CHIKORITA (BST: 318)"
            # So we just count them for statistics
            unique_original_species.add(change_info.split(' (BST')[0])
            new_species_part = change_info.split(' → ')[1]
            unique_new_species.add(new_species_part.split(' (BST')[0])
            
        if update_callback:
            update_callback(f"Randomized {len(unique_original_species)} unique Pokémon species!")
            update_callback(f"Used {len(unique_new_species)} unique Pokémon species as replacements!")
        
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("=" * 60 + "\n")
            log_file.write("POKÉMON ENCOUNTER RANDOMIZER CHANGES\n")
            log_file.write("=" * 60 + "\n\n")
            
            log_file.write(f"ROM: {os.path.basename(rom_path)}\n")
            log_file.write(f"Seed: {seed}\n")
            log_file.write(f"Similar Strength: {'Yes' if similar_strength else 'No'}\n")
            log_file.write(f"Total Pokémon Changed: {len(pokemon_changes)}\n")
            log_file.write(f"Unique Original Pokémon: {len(unique_original_species)}\n")
            log_file.write(f"Unique Replacement Pokémon: {len(unique_new_species)}\n\n")
            
            # Write all individual changes
            log_file.write("-" * 60 + "\n")
            log_file.write("ALL POKÉMON REPLACEMENTS\n")
            log_file.write("-" * 60 + "\n\n")
            
            # Now we can directly write our nicely formatted change strings
            for change_info in pokemon_changes:
                log_file.write(f"{change_info}\n")
                
            # Show the most common replacements
            log_file.write("\n" + "-" * 60 + "\n")
            log_file.write("MOST COMMON REPLACEMENTS\n")
            log_file.write("-" * 60 + "\n\n")
            
            # Sort by frequency (most common first)
            common_replacements = sorted(most_common_replacements.items(), key=lambda x: x[1], reverse=True)
            
            # Show the top 20 most common replacements with a nice header for each group
            log_file.write("The following replacements happened most frequently:\n\n")
            
            # Format the replacements in a nice readable way
            for i, (replacement, count) in enumerate(common_replacements[:20]):
                # Split the replacement into original and new
                parts = replacement.split(" → ")
                if len(parts) == 2:
                    original, new = parts
                    # Format with clear labels for beginners
                    log_file.write(f"{count}x: {original} was replaced with {new}\n")
                else:
                    # Fallback if the format is unexpected
                    log_file.write(f"{count}x: {replacement}\n")
                
                # Also show these in the UI for real-time feedback
                if i < 10 and update_callback:  # Only show top 10 in UI to avoid clutter
                    if len(parts) == 2:
                        update_callback(f"Common change: {parts[0]} → {parts[1]} ({count} times)")
                    else:
                        update_callback(f"Common replacement: {count}x {replacement}")
                    
            if update_callback:
                update_callback(f"Detailed change log created at {log_path}")
            
            log_file.write("\n" + "=" * 60 + "\n")
            log_file.write(f"Total Pokémon Changed: {len(pokemon_changes)}\n")
            log_file.write("=" * 60 + "\n")
        
        if update_callback:
            update_callback("Randomization complete!")
            update_callback(f"Change log saved to: {log_path}")
        if progress_callback:
            progress_callback(100)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error during randomization: {e}")
        raise e

class RandomizerGUI(QMainWindow):
    """GUI for the Pokémon encounter randomizer."""
    
    def __init__(self):
        super().__init__()
        
        # Load saved settings
        self.settings = load_settings()
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Pokémon Encounter Randomizer")
        self.setMinimumSize(600, 500)
        
        # Main widget and layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # File selection area
        file_group = QGroupBox("ROM Selection")
        file_layout = QFormLayout()
        
        # Input ROM selection
        input_layout = QHBoxLayout()
        self.input_path_label = QLabel("No file selected")
        self.input_path_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        self.browse_input_button = QPushButton("Browse...")
        self.browse_input_button.clicked.connect(self.browse_input)
        input_layout.addWidget(self.input_path_label, 1)
        input_layout.addWidget(self.browse_input_button)
        file_layout.addRow("Input ROM:", input_layout)
        
        # Output ROM selection
        output_layout = QHBoxLayout()
        self.output_path_label = QLabel("No file selected")
        self.output_path_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        self.browse_output_button = QPushButton("Browse...")
        self.browse_output_button.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_path_label, 1)
        output_layout.addWidget(self.browse_output_button)
        file_layout.addRow("Output ROM:", output_layout)
        
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # Options area
        options_group = QGroupBox("Randomization Options")
        options_layout = QFormLayout()
        
        # Seed input
        seed_layout = QHBoxLayout()
        self.use_seed_checkbox = QCheckBox("Use specific seed")
        self.seed_spinbox = QSpinBox()
        self.seed_spinbox.setRange(0, 99999999)
        self.seed_spinbox.setEnabled(False)
        self.use_seed_checkbox.toggled.connect(self.seed_spinbox.setEnabled)
        seed_layout.addWidget(self.use_seed_checkbox)
        seed_layout.addWidget(self.seed_spinbox)
        options_layout.addRow("Random Seed:", seed_layout)
        
        # Similar strength option
        self.similar_strength_checkbox = QCheckBox("Replace with similar-strength Pokémon")
        self.similar_strength_checkbox.setChecked(True)
        options_layout.addRow("Balance:", self.similar_strength_checkbox)
        
        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)
        
        # Progress area
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("font-family: Consolas, monospace;")
        self.log_display.setMinimumHeight(150)
        progress_layout.addWidget(self.log_display)
        
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Randomization")
        self.start_button.clicked.connect(self.start_randomization)
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        
        main_layout.addLayout(button_layout)
        
        # Initialize state
        self.randomizer_thread = None
        self.log("Welcome to the Pokémon Encounter Randomizer!")
        
        # Load last ROM path if available
        last_rom_path = self.settings.get("last_rom_path", "")
        if last_rom_path and os.path.exists(last_rom_path):
            self.input_path_label.setText(last_rom_path)
            self.log(f"Loaded last used ROM: {last_rom_path}")
            
            # Set output path based on last ROM
            base, ext = os.path.splitext(last_rom_path)
            output_path = f"{base}_randomized{ext}"
            self.output_path_label.setText(output_path)
            
            # Enable start button
            self.start_button.setEnabled(True)
        else:
            self.log("Select a ROM file to begin.")
    
    def log(self, message):
        """Add a message to the log display."""
        self.log_display.append(message)
        # Auto-scroll to the bottom
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def browse_input(self):
        """Browse for input ROM file."""
        # Start from last directory if available
        start_dir = ""
        last_rom = self.settings.get("last_rom_path", "")
        if last_rom and os.path.exists(os.path.dirname(last_rom)):
            start_dir = os.path.dirname(last_rom)
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ROM File", start_dir, "NDS ROM Files (*.nds);;All Files (*)"
        )
        if file_path:
            self.input_path_label.setText(file_path)
            
            # Auto-generate output path
            base, ext = os.path.splitext(file_path)
            output_path = f"{base}_randomized{ext}"
            self.output_path_label.setText(output_path)
            
            # Save this path for next time
            self.settings["last_rom_path"] = file_path
            save_settings(self.settings)
            self.log(f"Saved this ROM location for future use")
            
            # Enable start button
            self.start_button.setEnabled(True)
    
    def browse_output(self):
        """Browse for output ROM file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Randomized ROM As", "", "NDS ROM Files (*.nds);;All Files (*)"
        )
        if file_path:
            self.output_path_label.setText(file_path)
            
            # Enable start button if we have both paths
            if self.input_path_label.text() != "No file selected":
                self.start_button.setEnabled(True)
    
    def start_randomization(self):
        """Start the randomization process."""
        input_path = self.input_path_label.text()
        output_path = self.output_path_label.text()
        
        # Validation
        if input_path == "No file selected" or not os.path.exists(input_path):
            QMessageBox.warning(self, "Error", "Please select a valid input ROM file.")
            return
        
        if output_path == "No file selected":
            QMessageBox.warning(self, "Error", "Please select an output location.")
            return
        
        # Get options
        seed = None
        if self.use_seed_checkbox.isChecked():
            seed = self.seed_spinbox.value()
        
        similar_strength = self.similar_strength_checkbox.isChecked()
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.log("Starting randomization...")
        
        # Disable UI during randomization
        self.start_button.setEnabled(False)
        
        # Start randomization in a separate thread
        self.randomizer_thread = RandomizerThread(
            input_path, output_path, seed, similar_strength
        )
        self.randomizer_thread.progress_update.connect(self.log)
        self.randomizer_thread.progress_value.connect(self.progress_bar.setValue)
        self.randomizer_thread.finished_signal.connect(self.randomization_finished)
        self.randomizer_thread.start()
    
    def randomization_finished(self, success, message):
        """Handle randomization completion."""
        self.log(message)
        
        # Re-enable UI
        self.start_button.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Randomize Pokémon encounters in NDS ROMs")
    parser.add_argument("rom", nargs="?", help="Input ROM file path")
    parser.add_argument("-o", "--output", help="Output ROM file path")
    parser.add_argument("-s", "--seed", type=int, help="Random seed")
    parser.add_argument("--no-similar-strength", action="store_true", 
                      help="Don't match Pokemon by similar strength")
    parser.add_argument("-c", "--cli", action="store_true", 
                      help="Run in command-line mode (no GUI)")
    
    args = parser.parse_args()
    
    # Command-line mode
    if args.cli and args.rom:
        try:
            output = randomize_encounters(
                args.rom, 
                args.output, 
                args.seed, 
                not args.no_similar_strength,
                update_callback=print
            )
            print(f"Randomization completed successfully!\nOutput saved to: {output}")
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    # GUI mode
    app = QApplication(sys.argv)
    window = RandomizerGUI()
    window.show()
    
    # If ROM was specified as argument, load it
    if args.rom:
        if os.path.exists(args.rom):
            window.input_path_label.setText(args.rom)
            
            # Set output path
            if args.output:
                window.output_path_label.setText(args.output)
            else:
                base, ext = os.path.splitext(args.rom)
                output_path = f"{base}_randomized{ext}"
                window.output_path_label.setText(output_path)
            
            # Enable start button
            window.start_button.setEnabled(True)
        else:
            print(f"Warning: Input ROM not found: {args.rom}")
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())
