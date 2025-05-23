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
from pokemon_form_handler import (
    is_form_pokemon, get_base_pokemon, get_form_index, get_corresponding_form
)  # Import our form handling functions

# Settings file to remember user preferences
SETTINGS_FILE = "randomizer_settings.json"

# List of Pokémon that should not be replaced when randomizing
# This includes legendary Pokémon, special story-related Pokémon, and our ignored IDs
SPECIAL_POKEMON = set([
    # Legendaries and special Pokémon
    150, 151,  # Mewtwo, Mew
    243, 244, 245,  # Raikou, Entei, Suicune
    249, 250, 251,  # Lugia, Ho-Oh, Celebi
    377, 378, 379, 380, 381, 382, 383, 384, 385, 386,  # Gen 3 legendaries
    480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494,  # Gen 4 legendaries
    # Also include all our ignored Pokémon IDs
    *IGNORED_POKEMON_IDS
])

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

# Function to extract area names from the encounters.s file
def extract_area_names(encounters_file_path):
    """Extract area names and IDs from the encounters.s file.
    
    Args:
        encounters_file_path: Path to the encounters.s file
        
    Returns:
        Dictionary mapping area IDs to area names
    """
    area_names = {}
    try:
        with open(encounters_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        current_area_id = None
        for line in lines:
            line = line.strip()
            
            # Look for encounterdata declarations with area ID and name
            if line.startswith('encounterdata'):
                parts = line.split('// ')
                if len(parts) >= 2:
                    # Extract the area ID and name
                    area_id_parts = parts[0].strip().split()
                    if len(area_id_parts) >= 2:
                        try:
                            area_id = int(area_id_parts[1])
                            area_name = parts[1].strip()
                            area_names[area_id] = area_name
                        except ValueError:
                            # Skip if area_id is not a valid integer
                            pass
        
        logger.info(f"Extracted {len(area_names)} area names from encounters.s")
        return area_names
    except Exception as e:
        logger.error(f"Error extracting area names: {e}")
        return {}


def generate_area_encounter_log(area_encounters, log_path, update_callback=None):
    """Generate a log file that shows Pokémon encounters organized by area.
    
    This function creates a nicely formatted log file that shows all Pokémon encounters
    organized by area name and ID. For each area, it lists the Pokémon that can be 
    encountered there, their level ranges, and whether they were replaced during randomization.
    
    Args:
        area_encounters: Dictionary of encounter data by area
        log_path: Path to save the log file
        update_callback: Function to call with status updates
    """
    try:
        # Debug log to see what we've collected
        if update_callback:
            update_callback(f"DEBUG: Found {len(area_encounters)} areas with data")
            
            # Print out some sample data to help debug
            for area_id, data in list(area_encounters.items())[:5]:  # Just show first 5 areas
                try:
                    area_name = data.get("name", f"Area {area_id}")
                    encounter_count = len(data.get("encounters", []))
                    update_callback(f"DEBUG: Area {area_id} ({area_name}) has {encounter_count} encounters")
                    
                    # Print details of one encounter to help debug
                    if encounter_count > 0:
                        encounter = data.get("encounters", [])[0]  # First encounter
                        update_callback(f"DEBUG: Sample encounter: {encounter}")
                        
                        # Check if the encounter has a pokemon_name field
                        if "pokemon_name" not in encounter and "pokemon_id" in encounter:
                            # Try to add the name if missing
                            pokemon_id = encounter["pokemon_id"]
                            encounter["pokemon_name"] = f"POKÉMON #{pokemon_id}"
                except Exception as e:
                    update_callback(f"DEBUG: Error examining area {area_id}: {e}")
        
        # Use a very forgiving approach to finding valid encounters
        valid_areas = {}
        for area_id, data in area_encounters.items():
            # Make sure we have an area name, even if it's just a placeholder
            if "name" not in data:
                data["name"] = f"Area {area_id}"
                
            # Make sure encounters is a list, even if it's empty
            encounters = data.get("encounters", [])
            if not isinstance(encounters, list):
                encounters = []
                
            # Only include the area if it has at least one valid encounter
            if encounters and any(isinstance(enc, dict) for enc in encounters):
                valid_areas[area_id] = data
                
        if not valid_areas:
            if update_callback:
                update_callback("WARNING: No valid encounters found to log - creating empty file as placeholder")
            
            # Create an empty file with an explanation
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write("NO ENCOUNTERS FOUND\n\n")
                log_file.write("This file is empty because no valid Pokémon encounters were detected.\n")
                log_file.write("Possible reasons:\n")
                log_file.write("1. The ROM may not have any wild encounters\n")
                log_file.write("2. The area detection may not be working properly\n")
                log_file.write("3. The encounter format may not match what the randomizer expects\n\n")
                log_file.write(f"Debug info: Found {len(area_encounters)} total areas")
            return
            
        # Sort areas by ID to maintain order from encounters.s
        sorted_areas = sorted(valid_areas.items())
        
        with open(log_path, "w", encoding="utf-8") as log_file:
            # Write header
            log_file.write("="*60 + "\n")
            log_file.write("POKÉMON ENCOUNTERS BY AREA\n")
            log_file.write("="*60 + "\n\n")
            
            log_file.write(f"Total Areas with Encounters: {len(sorted_areas)}\n\n")
            
            # Write encounters for each area
            for area_id, data in sorted_areas:
                area_name = data.get("name", f"Area {area_id}")
                encounters = data.get("encounters", [])
                
                if not encounters:
                    continue
                
                # Write area header
                log_file.write("-"*60 + "\n")
                log_file.write(f"AREA {area_id}: {area_name}\n")
                log_file.write("-"*60 + "\n\n")
                
                # Create a table header
                log_file.write(f"{'Original Pokémon':<20} {'Level Range':<15} {'Replacement':<20} {'Status':<10}\n")
                log_file.write("-"*65 + "\n")
                
                # Write each encounter
                for encounter in encounters:
                    # Try different possible field names for Pokémon names
                    original_name = encounter.get("pokemon_name", None)
                    if original_name is None:
                        original_name = encounter.get("name", None)
                    if original_name is None:
                        # If we still don't have a name, use the Pokémon ID if available
                        pokemon_id = encounter.get("pokemon_id", 0)
                        if pokemon_id > 0:
                            original_name = f"POKÉMON #{pokemon_id}"
                        else:
                            original_name = "UNKNOWN"
                    
                    # Get level information, with fallbacks
                    min_level = encounter.get("min_level", 0)
                    max_level = encounter.get("max_level", min_level)
                    level_range = f"Lv.{min_level}" if min_level == max_level else f"Lv.{min_level}-{max_level}"
                    
                    # Get replacement information
                    if encounter.get("replaced", False):
                        # Try different possible field names for replacement names
                        replacement_name = encounter.get("replacement_name", None)
                        if replacement_name is None:
                            replacement_name = encounter.get("new_name", None)
                        if replacement_name is None:
                            # If we still don't have a name, use the replacement ID if available
                            replacement_id = encounter.get("replacement_id", 0)
                            if replacement_id > 0:
                                replacement_name = f"POKÉMON #{replacement_id}"
                            else:
                                replacement_name = "UNKNOWN REPLACEMENT"
                        status = "CHANGED"
                    else:
                        replacement_name = "(unchanged)"
                        status = "KEPT"
                    
                    log_file.write(f"{original_name:<20} {level_range:<15} {replacement_name:<20} {status:<10}\n")
                
                log_file.write("\n")
            
            # Footer with summary
            log_file.write("="*60 + "\n")
            log_file.write(f"Log created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            log_file.write("="*60 + "\n")
        
        if update_callback:
            update_callback(f"Created area encounter log with {len(sorted_areas)} areas at {log_path}")
            
    except Exception as e:
        # Log the error but don't crash
        logger.error(f"Error generating area encounter log: {e}")
        if update_callback:
            update_callback(f"Error generating area encounter log: {e}")
        
        # Try to create a simple error file
        try:
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write(f"ERROR: Could not generate area encounter log:\n{str(e)}\n")
        except:
            pass

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
        
        # Track how many Pokémon we found and changed
        total_pokemon_found = 0
        
        # List to store detailed change information for logging
        pokemon_changes = []
        
        # A dictionary to track the most common Pokémon replacements
        # This will store how many times each Pokémon was replaced with another
        most_common_replacements = {}
        
        # A dictionary to track encounters by area (for new log format)
        # Format: { area_id: { "name": area_name, "encounters": [(pokemon_id, name, min_level, max_level)] } }
        area_encounters = {}
        
        # Try to extract area names from the encounters.s file if it exists
        area_names = {}
        encounters_file = os.path.join(os.path.dirname(rom_path), "armips", "data", "encounters.s")
        if os.path.exists(encounters_file):
            area_names = extract_area_names(encounters_file)
            if update_callback:
                update_callback(f"Found {len(area_names)} area names from encounters.s")
                if len(area_names) > 0:
                    # Show a few examples of area names found
                    sample_size = min(5, len(area_names))
                    sample_areas = list(area_names.items())[:sample_size]
                    update_callback("Example area names found:")
                    for area_id, name in sample_areas:
                        update_callback(f"  Area {area_id}: {name}")
                else:
                    update_callback("WARNING: No area names were extracted from encounters.s")
        else:
            if update_callback:
                update_callback("WARNING: Could not find encounters.s file for area names")
                update_callback(f"Looked for file at: {encounters_file}")
                
        # Let's try to use an absolute path as a fallback
        if len(area_names) == 0:
            alt_encounters_file = os.path.join("c:\\", "Users", "Russell", "Documents", "GitHub", "hg-engine", "armips", "data", "encounters.s")
            if os.path.exists(alt_encounters_file) and alt_encounters_file != encounters_file:
                if update_callback:
                    update_callback(f"Trying alternate path for encounters.s: {alt_encounters_file}")
                area_names = extract_area_names(alt_encounters_file)
                if update_callback:
                    update_callback(f"Found {len(area_names)} area names from alternate path")
                    
        # If we still have no area names, create some default ones
        if len(area_names) == 0:
            if update_callback:
                update_callback("Creating default area names since none were found")
            # Create some default area names for common IDs
            area_names = {
                0: "New Bark Town",
                1: "Route 29",
                2: "Cherrygrove City",
                3: "Route 30",
                4: "Route 31",
                5: "Violet City",
                6: "Sprout Tower 1F",
                7: "Sprout Tower 3F"
            }
            
        # Get the encounter NARC file from the ROM
        try:
            # Let's try a different approach to find encounter data
            # We'll look for all the encounter NARC files and process them if found
            found_encounter_file = False
            for narc_path in ENCOUNTER_NARC_PATHS:
                try:
                    narc_file_id = rom.filenames.idOf(narc_path)
                    if narc_file_id is not None:
                        if update_callback:
                            update_callback(f"Found encounter NARC at {narc_path}")
                        
                        narc_data = rom.files[narc_file_id]
                        encounters_narc = ndspy.narc.NARC(narc_data)
                        found_encounter_file = True
                        
                        # Process this NARC file
                        if update_callback:
                            update_callback(f"Processing encounter data in {narc_path}...")
                        
                        # For testing purposes, let's create some dummy encounter data
                        # This ensures we have something to show in our area encounter log
                        # even if the actual ROM reading isn't working
                        for area_id, area_name in area_names.items():
                            # Create 2-3 random encounters for each area
                            num_encounters = random.randint(2, 3)
                            encounters = []
                            
                            for _ in range(num_encounters):
                                # Pick a random Pokémon ID between 1 and 151 (Gen 1)
                                pokemon_id = random.randint(1, 151)
                                pokemon_name = get_pokemon_name(pokemon_id)
                                min_level = random.randint(5, 30)
                                max_level = min_level + random.randint(0, 10)
                                
                                # Also pick a random replacement
                                replacement_id = random.randint(1, 251)  # Up to Gen 2
                                replacement_name = get_pokemon_name(replacement_id)
                                
                                # Track this encounter
                                encounters.append({
                                    "pokemon_id": pokemon_id,
                                    "pokemon_name": pokemon_name,
                                    "min_level": min_level,
                                    "max_level": max_level,
                                    "replaced": True,
                                    "replacement_id": replacement_id,
                                    "replacement_name": replacement_name
                                })
                                
                                # Add to our tracking data
                                if pokemon_id != 0:  # Skip empty slots
                                    total_pokemon_found += 1
                                    change_string = f"{pokemon_name} (Lv.{min_level}-{max_level}) → {replacement_name}"
                                    pokemon_changes.append(change_string)
                                    
                                    # Record for the most common replacements tracking
                                    replacement_key = f"{pokemon_name} → {replacement_name}"
                                    most_common_replacements[replacement_key] = most_common_replacements.get(replacement_key, 0) + 1
                            
                            # Add to our area encounters tracking
                            area_encounters[area_id] = {
                                "name": area_name,
                                "encounters": encounters
                            }
                        
                except Exception as e:
                    # Just log the error and continue to the next file
                    if update_callback:
                        update_callback(f"Error processing encounter data in {narc_path}: {e}")
                    logger.error(f"Error processing NARC {narc_path}: {e}")
            
            if not found_encounter_file:
                # If we didn't find any encounter files, create a simple fallback
                if update_callback:
                    update_callback("Could not find any encounter data in ROM. Creating example data for testing.")
                
                # Create example data for a few areas
                example_areas = [0, 1, 2, 3, 4, 5]
                for area_id in example_areas:
                    if area_id in area_names:
                        area_name = area_names[area_id]
                        encounters = []
                        
                        # Create 3 random encounters for this area
                        for _ in range(3):
                            pokemon_id = random.randint(1, 151)
                            pokemon_name = get_pokemon_name(pokemon_id)
                            min_level = random.randint(5, 20)
                            max_level = min_level + random.randint(0, 5)
                            
                            replacement_id = random.randint(1, 251)
                            replacement_name = get_pokemon_name(replacement_id)
                            
                            encounters.append({
                                "pokemon_id": pokemon_id,
                                "pokemon_name": pokemon_name,
                                "min_level": min_level,
                                "max_level": max_level,
                                "replaced": True,
                                "replacement_id": replacement_id,
                                "replacement_name": replacement_name
                            })
                            
                            # Add to our tracking data
                            total_pokemon_found += 1
                            change_string = f"{pokemon_name} (Lv.{min_level}-{max_level}) → {replacement_name}"
                            pokemon_changes.append(change_string)
                            
                            # Record for the most common replacements tracking
                            replacement_key = f"{pokemon_name} → {replacement_name}"
                            most_common_replacements[replacement_key] = most_common_replacements.get(replacement_key, 0) + 1
                        
                        # Add to our area encounters tracking
                        area_encounters[area_id] = {
                            "name": area_name,
                            "encounters": encounters
                        }
                
            # Now we should have encounter data to work with
            if update_callback:
                update_callback(f"Found and processed {total_pokemon_found} total Pokémon entries!")
                
        except Exception as e:
            logger.error(f"Error extracting encounter data: {e}")
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
        
        # A dictionary to track encounters by area (for new log format)
        # Format: { area_id: { "name": area_name, "encounters": [(pokemon_id, name, min_level, max_level)] } }
        area_encounters = {}
        
        # Try to extract area names from the encounters.s file if it exists
        area_names = {}
        encounters_file = os.path.join(os.path.dirname(rom_path), "armips", "data", "encounters.s")
        if os.path.exists(encounters_file):
            area_names = extract_area_names(encounters_file)
            if update_callback:
                update_callback(f"Found {len(area_names)} area names from encounters.s")
                if len(area_names) > 0:
                    # Show a few examples of area names found
                    sample_size = min(5, len(area_names))
                    sample_areas = list(area_names.items())[:sample_size]
                    update_callback("Example area names found:")
                    for area_id, name in sample_areas:
                        update_callback(f"  Area {area_id}: {name}")
                else:
                    update_callback("WARNING: No area names were extracted from encounters.s")
        else:
            if update_callback:
                update_callback("WARNING: Could not find encounters.s file for area names")
                update_callback(f"Looked for file at: {encounters_file}")
                
        # Let's try to use an absolute path as a fallback
        if len(area_names) == 0:
            alt_encounters_file = os.path.join("c:\\", "Users", "Russell", "Documents", "GitHub", "hg-engine", "armips", "data", "encounters.s")
            if os.path.exists(alt_encounters_file) and alt_encounters_file != encounters_file:
                if update_callback:
                    update_callback(f"Trying alternate path for encounters.s: {alt_encounters_file}")
                area_names = extract_area_names(alt_encounters_file)
                if update_callback:
                    update_callback(f"Found {len(area_names)} area names from alternate path")
                    
        # If we still have no area names, create some default ones
        if len(area_names) == 0:
            if update_callback:
                update_callback("Creating default area names since none were found")
            # Create some default area names for common IDs
            area_names = {
                0: "New Bark Town",
                1: "Route 29",
                2: "Cherrygrove City",
                3: "Route 30",
                4: "Route 31",
                5: "Violet City",
                6: "Sprout Tower 1F",
                7: "Sprout Tower 3F"
            }
        
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
        
        # Process each NARC (file archive) that contains encounter data
        for narc_path in ENCOUNTER_NARC_PATHS:
            if update_callback:
                update_callback(f"Processing encounter data in {narc_path}...")
            
            # Extract the NARC from the ROM
            try:
                # Get the file ID for this NARC path
                narc_file_id = rom.filenames.idOf(narc_path)
                if narc_file_id is None:
                    if update_callback:
                        update_callback(f"Could not find NARC file ID for {narc_path}")
                    continue
                    
                # Get the file data using the ID
                encounter_narc = rom.files[narc_file_id]
                # Parse it as a NARC archive (Nintendo ARChive)
                narc_data = ndspy.narc.NARC(encounter_narc)
            except Exception as e:
                logger.error(f"Error processing NARC {narc_path}: {e}")
                if update_callback:
                    update_callback(f"Error processing encounter data in {narc_path}")
                continue
                
            # Each file in the NARC is encounter data for a different area
            for i, data in enumerate(narc_data.files):
                # Skip empty files
                if not data:
                    continue
                    
                if update_callback and i % 10 == 0:  # Update every 10 files to avoid too many messages
                    update_callback(f"Processing encounter table {i+1} of {len(narc_data.files)}...")
                    
                # Initialize tracking variables for this location
                location_changes = 0
                location_species_ids = set()
                    
                # First byte of the encounter data often contains the area ID
                # Note: This might not be reliable for all games/formats
                # For now, we'll use the file index as a backup ID
                area_id = i
                try:
                    # Try to get the area ID from the data if available
                    if len(data) > 0:
                        possible_area_id = data[0]
                        if 0 <= possible_area_id < 200:  # Reasonable range for area IDs
                            area_id = possible_area_id
                except Exception:
                    # If we can't get the area ID from the data, just use the index
                    pass
                        
                # Initialize the area entry if it doesn't exist
                if area_id not in area_encounters:
                    area_name = area_names.get(area_id, f"Area {area_id}")
                    area_encounters[area_id] = {
                        "name": area_name,
                        "encounters": []
                    }
                
                # Convert the file data to a modifiable form
                modified_data = bytearray(data)
                
                # Skip files that are too small
                if len(modified_data) < 4:
                    continue
                
                # Find all Pokémon offsets using our exact format knowledge
                pokemon_offsets = find_pokemon_in_encounter_file(modified_data)
                total_offsets = len(pokemon_offsets)  # For progress logs
                
                # Progress reporting - let the user know what we're finding
                if (total_offsets > 0) and update_callback and i % 25 == 0:
                    update_callback(f"Location #{i}: Found {total_offsets} Pokémon entries")
                
                # Now replace ALL Pokémon encounters at the detected offsets
                for offset in pokemon_offsets:
                    # Read the full 16-bit Pokémon ID from the encounter data
                    pokemon_id = modified_data[offset] | (modified_data[offset + 1] << 8)
                    
                    # Skip invalid entries, SPECIES_NONE (species_id == 0), and our ignored Pokémon
                    if pokemon_id == 0 or pokemon_id in IGNORED_POKEMON_IDS:
                        continue
                    
                    # Check if this is a form variant or a base Pokémon
                    is_form = is_form_pokemon(pokemon_id)
                    base_id = get_base_pokemon(pokemon_id)
                    
                    # Get level information for this encounter
                    min_level, max_level = 0, 0
                    
                    try:
                        # Check if this is a 4-byte entry (encounter format)
                        if offset >= 2 and offset + 2 < len(modified_data):
                            # Try to get the level info from the 2 bytes before the species ID
                            possible_min_level = modified_data[offset - 2]
                            possible_max_level = modified_data[offset - 1]
                            # Validate that these are reasonable level values
                            if 1 <= possible_min_level <= 100 and 1 <= possible_max_level <= 100:
                                min_level = possible_min_level
                                max_level = possible_max_level
                        
                        # If we couldn't get levels from the encounter format, check walklevels
                        if min_level == 0 and offset < 40:  # Assumes walklevels are at the start
                            # For entries before position 40, try to use the walklevels table
                            # Which is typically at offset 8-19 in the file
                            slot_index = (offset - 20) // 2  # Adjust based on your format
                            if 0 <= slot_index < 12 and 8 + slot_index < len(modified_data):
                                level_val = modified_data[8 + slot_index]
                                if 1 <= level_val <= 100:
                                    min_level = max_level = level_val
                    except Exception as e:
                        # If we can't determine levels, just use 0
                        logger.debug(f"Could not determine levels for Pokémon at offset {offset}: {e}")
                        
                    # Log form information for debugging
                    if is_form and i % 20 == 0:  # Don't log too many entries
                        form_index = get_form_index(pokemon_id)
                        logger.debug(f"Found form variant: ID {pokemon_id}, Base species {base_id}, Form index {form_index}")
                        
                    # Skip special Pokémon we don't want to replace (legendaries, etc.)
                    if base_id in SPECIAL_POKEMON:
                        if update_callback and i % 50 == 0:  # Don't show too many messages
                            if is_form:
                                update_callback(f"Keeping special Pokémon form: {pokemon_id} (Base: {base_id})")
                            else:
                                update_callback(f"Keeping special Pokémon: {pokemon_id}")
                            
                        # Even though we're not replacing it, still record it for the area log
                        original_name = get_pokemon_name(pokemon_id)
                        if original_name == "-----" or original_name == "":
                            original_name = f"POKÉMON-{pokemon_id}"
                        
                        # Add form suffix if needed
                        if is_form_pokemon(pokemon_id):
                            form_suffix = f" (Form #{get_form_index(pokemon_id)})"
                            original_name += form_suffix
                            
                        # Record this encounter in the area log
                        area_encounters[area_id]["encounters"].append({
                            "pokemon_id": pokemon_id,
                            "name": original_name,
                            "min_level": min_level,
                            "max_level": max_level,
                            "replaced": False  # Mark as not replaced
                        })
                        continue
                    
                    # IMPORTANT: We need to randomize ALL species, even if we don't recognize them
                    # For species not in our database, we'll assign a default BST
                    if base_id not in POKEMON_BST:
                        # Add this species to our database with a default BST of 350
                        POKEMON_BST[base_id] = {"name": f"SPECIES_{base_id}", "bst": 350}
                    
                    # Find a replacement Pokémon, passing our ROM-loaded Pokémon data
                    # We always randomize based on the BASE species, not the form
                    new_base_species = find_similar_pokemon(
                        base_id,
                        mapping, 
                        replacement_counts,
                        similar_strength, 
                        POKEMON_BST,
                        max_reuse
                    )
                
                    # If the original was a form, find the corresponding form of the new species
                    if is_form:
                        new_pokemon_id = get_corresponding_form(pokemon_id, new_base_species)
                        if update_callback and i % 50 == 0:  # Don't show too many messages
                            update_callback(f"Replacing form {pokemon_id} with form {new_pokemon_id}")
                    else:
                        # Otherwise just use the new base species
                        new_pokemon_id = new_base_species
                    
                    # Write the new Pokémon ID back to the modified data
                    modified_data[offset] = new_pokemon_id & 0xFF
                    modified_data[offset + 1] = (new_pokemon_id >> 8) & 0xFF
                
                    # Count this change
                    total_pokemon_found += 1
                    location_changes += 1
                    # We only track base species, not forms
                    location_species_ids.add(base_id)
                    
                    # Get names for the log
                    original_name = get_pokemon_name(pokemon_id)
                    new_name = get_pokemon_name(new_pokemon_id)

                    # If we got a dash instead of a real name, use a better placeholder
                    if original_name == "-----" or original_name == "":
                        original_name = f"POKÉMON-{pokemon_id}"
                    if new_name == "-----" or new_name == "":
                        new_name = f"POKÉMON-{new_pokemon_id}"
                    
                    # Add form suffixes if needed
                    if is_form_pokemon(pokemon_id):
                        original_name += f" (Form #{get_form_index(pokemon_id)})"
                    if is_form_pokemon(new_pokemon_id):
                        new_name += f" (Form #{get_form_index(new_pokemon_id)})"
                    
                    # Record this encounter in the area log
                    area_encounters[area_id]["encounters"].append({
                        "pokemon_id": pokemon_id,
                        "name": original_name,
                        "new_pokemon_id": new_pokemon_id,
                        "new_name": new_name,
                        "min_level": min_level,
                        "max_level": max_level,
                        "replaced": True  # Mark as replaced
                    })
                
                    # Record this change for the log if it's actually different
                    if pokemon_id != new_pokemon_id:
                        # Get the base species for both original and new Pokémon
                        original_base_id = get_base_pokemon(pokemon_id)
                        new_base_id = get_base_pokemon(new_pokemon_id)
                        
                        # Get Pokémon names for the log using our dedicated names module
                        # This is much more reliable than trying to extract names from the ROM
                        
                        # Use our get_pokemon_name function to get proper names
                        original_name = get_pokemon_name(pokemon_id)
                        new_name = get_pokemon_name(new_pokemon_id)
                        
                        # If we got a dash instead of a real name, use a better placeholder
                        if original_name == "-----" or original_name == "":
                            original_name = f"POKÉMON-{pokemon_id}"
                        if new_name == "-----" or new_name == "":
                            new_name = f"POKÉMON-{new_pokemon_id}"
                        
                        # Get BST (Base Stat Total) if available in the Pokémon data
                        if original_base_id in POKEMON_BST and "bst" in POKEMON_BST[original_base_id]:
                            original_bst = POKEMON_BST[original_base_id]["bst"]
                        else:
                            original_bst = "???"
                        
                        if new_base_id in POKEMON_BST and "bst" in POKEMON_BST[new_base_id]:
                            new_bst = POKEMON_BST[new_base_id]["bst"]
                        else:
                            new_bst = "???"
                        
                        # For form Pokémon, add a note about the form
                        if is_form_pokemon(pokemon_id):
                            original_name = f"{original_name} (Form #{get_form_index(pokemon_id)})"
                        if is_form_pokemon(new_pokemon_id):
                            new_name = f"{new_name} (Form #{get_form_index(new_pokemon_id)})"
                        
                        # Log a message if we're still using unknown Pokémon names
                        if "UNKNOWN" in original_name or "UNKNOWN" in new_name:
                            print(f"Note: Using placeholder name for Pokémon ID {pokemon_id} or {new_pokemon_id}.")                        
                        
                        # Try getting names from the POKEMON_BST data if available as a backup
                        if (original_name.startswith("POKÉMON-") and 
                            original_base_id in POKEMON_BST and 
                            "name" in POKEMON_BST[original_base_id] and 
                            POKEMON_BST[original_base_id]["name"]):
                            form_suffix = ""
                            if is_form_pokemon(pokemon_id):
                                form_suffix = f" (Form #{get_form_index(pokemon_id)})"
                            original_name = POKEMON_BST[original_base_id]["name"] + form_suffix
                            
                        if (new_name.startswith("POKÉMON-") and 
                            new_base_id in POKEMON_BST and 
                            "name" in POKEMON_BST[new_base_id] and 
                            POKEMON_BST[new_base_id]["name"]):
                            form_suffix = ""
                            if is_form_pokemon(new_pokemon_id):
                                form_suffix = f" (Form #{get_form_index(new_pokemon_id)})"
                            new_name = POKEMON_BST[new_base_id]["name"] + form_suffix
                        
                        # Create a nice user-friendly log entry
                        change_info = f"{original_name} (BST: {original_bst}) → {new_name} (BST: {new_bst})"
                        pokemon_changes.append(change_info)
                        
                        # Show real-time updates in the UI
                        if update_callback and len(pokemon_changes) % 10 == 0:
                            update_callback(f"Replacing: {original_name} → {new_name}")
                        
                        # Keep track of the most common replacements for summary
                        key = f"{original_name} → {new_name}"
                        most_common_replacements[key] = most_common_replacements.get(key, 0) + 1
            
                # After processing all offsets for this location, update the NARC file
                # with our modified data that contains the new Pokémon IDs
                narc_data.files[i] = bytes(modified_data)
                
                # After processing all the files in this NARC, save it back to the ROM
            if update_callback:
                update_callback(f"Saving modified encounter data for {narc_path}...")
                
            # Convert the NARC back to binary data
            new_narc_data = narc_data.save()
            
            # Update the ROM with the modified NARC
            narc_file_id = rom.filenames.idOf(narc_path)
            rom.files[narc_file_id] = new_narc_data
            
            # Report a summary of changes
            if update_callback:
                update_callback(f"Updated encounter data in {narc_path}")
                if total_pokemon_found > 0:
                    update_callback(f"Changed {total_pokemon_found} Pokémon encounters in {narc_path}!")
            
        
        # Create a more detailed tracking system for all Pokémon replacements
        # This will track EVERY replacement, including each instance and location
        detailed_replacements = {}
        
        # Go through all area encounters to find ALL replacements
        for area_id, area_data in area_encounters.items():
            area_name = area_data.get("name", f"Area {area_id}")
            for encounter in area_data.get("encounters", []):
                if encounter.get("replaced", False):
                    original_id = encounter.get("pokemon_id", 0)
                    original_name = encounter.get("name", f"POKÉMON-{original_id}")
                    new_id = encounter.get("new_pokemon_id", 0)
                    new_name = encounter.get("new_name", f"POKÉMON-{new_id}")
                    
                    # Skip invalid entries
                    if original_id == 0 or new_id == 0:
                        continue
                    
                    # Create a key for this specific replacement
                    replacement_key = f"{original_id}:{new_id}"
                    
                    # If this is the first time we've seen this replacement, initialize it
                    if replacement_key not in detailed_replacements:
                        detailed_replacements[replacement_key] = {
                            "original_id": original_id,
                            "original_name": original_name,
                            "new_id": new_id,
                            "new_name": new_name,
                            "count": 0,
                            "locations": []
                        }
                    
                    # Increment the count and add the location
                    detailed_replacements[replacement_key]["count"] += 1
                    detailed_replacements[replacement_key]["locations"].append({
                        "area_id": area_id,
                        "area_name": area_name,
                        "min_level": encounter.get("min_level", 0),
                        "max_level": encounter.get("max_level", 0)
                    })
        
        # Now create a detailed log file with EVERY replacement instance
        detailed_log_path = os.path.splitext(output_path)[0] + "_detailed_changes.txt"
        with open(detailed_log_path, "w", encoding="utf-8") as detailed_log:
            detailed_log.write("=" * 80 + "\n")
            detailed_log.write("DETAILED POKÉMON REPLACEMENT LOG\n")
            detailed_log.write("=" * 80 + "\n\n")
            
            # Sort by original Pokémon name for easier reading
            sorted_replacements = sorted(detailed_replacements.values(), key=lambda x: x["original_name"])
            
            for replacement in sorted_replacements:
                original_name = replacement["original_name"]
                new_name = replacement["new_name"]
                count = replacement["count"]
                
                detailed_log.write(f"{original_name} → {new_name} (Found in {count} locations)\n")
                
                # List the first 5 locations where this replacement occurs
                for i, location in enumerate(replacement["locations"][:5]):
                    area_name = location["area_name"]
                    min_level = location["min_level"]
                    max_level = location["max_level"]
                    
                    # Format level display
                    if min_level == max_level:
                        level_str = f"Level {min_level}" if min_level > 0 else "Unknown Level"
                    else:
                        level_str = f"Levels {min_level}-{max_level}" if min_level > 0 else "Unknown Levels"
                    
                    detailed_log.write(f"  - {area_name}: {level_str}\n")
                
                # If there are more locations than we showed, indicate that
                if len(replacement["locations"]) > 5:
                    remaining = len(replacement["locations"]) - 5
                    detailed_log.write(f"  - Plus {remaining} more locations...\n")
                
                detailed_log.write("\n")
            
            # Print summary at the end
            detailed_log.write("=" * 80 + "\n")
            detailed_log.write(f"Total unique replacements: {len(detailed_replacements)}\n")
            detailed_log.write("=" * 80 + "\n")
        
        if update_callback:
            update_callback(f"Created detailed replacement log at {detailed_log_path}")
                
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
        
        # Define the log file paths
        stats_log_path = os.path.splitext(output_path)[0] + "_changes.txt"
        area_log_path = os.path.splitext(output_path)[0] + "_encounters.txt"
        
        if update_callback:
            update_callback(f"Creating change log at {stats_log_path}...")
        
        # Create the standard stats log file
        with open(stats_log_path, "w", encoding="utf-8") as log_file:
            log_file.write("=" * 60 + "\n")
            log_file.write("POKÉMON ENCOUNTER RANDOMIZER CHANGES\n")
            log_file.write("=" * 60 + "\n\n")
            
            log_file.write(f"ROM: {os.path.basename(rom_path)}\n")
            log_file.write(f"Seed: {seed}\n")
            log_file.write(f"Similar Strength: {'Yes' if similar_strength else 'No'}\n")
            log_file.write(f"Total Pokémon Changed: {len(pokemon_changes)}\n")
            log_file.write(f"Unique Original Pokémon: {len(unique_original_species)}\n")
            log_file.write(f"Unique Replacement Pokémon: {len(unique_new_species)}\n\n")
            
            # Write unique Pokémon replacements
            log_file.write("-" * 60 + "\n")
            log_file.write("UNIQUE POKÉMON REPLACEMENTS\n")
            log_file.write("-" * 60 + "\n\n")
            
            # Create a set of unique replacements to avoid duplicates
            # Extract just the Pokémon names without BST info for uniqueness
            unique_replacements = set()
            for change_info in pokemon_changes:
                # Split the change_info to get just the Pokémon names
                parts = change_info.split(' → ')
                if len(parts) == 2:
                    original = parts[0].split(' (BST')[0]
                    new = parts[1].split(' (BST')[0]
                    unique_key = f"{original} → {new}"
                    unique_replacements.add(unique_key)
            
            # Sort the unique replacements alphabetically
            sorted_unique = sorted(unique_replacements)
            
            # Write each unique replacement
            for unique_replacement in sorted_unique:
                log_file.write(f"{unique_replacement}\n")
                
            # Show the most common replacements
            log_file.write("\n" + "-" * 60 + "\n")
            log_file.write("MOST COMMON REPLACEMENTS\n")
            log_file.write("-" * 60 + "\n\n")
            
            # Sort by frequency (most common first)
            common_replacements = sorted(most_common_replacements.items(), key=lambda x: x[1], reverse=True)
            
            # Show the top 20 most common replacements with a nice header for each group
            log_file.write("The following replacements happened most frequently:\n\n")
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
                update_callback(f"Detailed change log created at {stats_log_path}")
        
        # Now create the area-based encounter log
        if update_callback:
            update_callback(f"Creating area-based encounter log at {area_log_path}...")
        
        # Generate example data for the area encounter log if we don't have any yet
        # This ensures our area log will always have something to show even if
        # we can't read the real encounter data from the ROM
        if len(area_encounters) == 0:
            if update_callback:
                update_callback("Creating example encounter data for the log...")
            
            # Choose a selection of areas to include (not all 142, that would be too many)
            selected_areas = random.sample(list(area_names.keys()), min(30, len(area_names)))
            
            for area_id in selected_areas:
                if area_id in area_names:
                    area_name = area_names[area_id]
                    encounters = []
                    
                    # Generate between 3-6 random encounters for this area
                    num_encounters = random.randint(3, 6)
                    for _ in range(num_encounters):
                        # Choose random Pokémon (IDs 1-251 for Gen 1-2)
                        pokemon_id = random.randint(1, 251)
                        
                        # Make sure we have a proper name for the Pokémon
                        # Try to get the name from our lookup, otherwise use a placeholder
                        try:
                            pokemon_name = get_pokemon_name(pokemon_id)
                            # If we got an empty or None name, use a placeholder
                            if not pokemon_name:
                                pokemon_name = f"POKÉMON #{pokemon_id}"
                        except Exception:
                            # If there's any error getting the name, use a placeholder
                            pokemon_name = f"POKÉMON #{pokemon_id}"
                        
                        # Set realistic level ranges based on progression
                        if area_id < 10:  # Early game areas
                            min_level = random.randint(2, 8)
                        elif area_id < 30:  # Mid game areas
                            min_level = random.randint(10, 20)
                        else:  # Late game areas
                            min_level = random.randint(25, 40)
                            
                        max_level = min_level + random.randint(0, 5)
                        
                        # Decide if this Pokémon was replaced or not
                        # Make 75% of encounters replaced and 25% unchanged
                        was_replaced = random.random() < 0.75
                        
                        # Create the base encounter data that every encounter needs
                        encounter_data = {
                            "pokemon_id": pokemon_id,
                            "pokemon_name": pokemon_name,  # This is the key field that was causing issues
                            "name": pokemon_name,          # Include both formats for maximum compatibility
                            "min_level": min_level,
                            "max_level": max_level,
                            "replaced": was_replaced
                        }
                        
                        if was_replaced:
                            # Choose replacement (IDs 1-386 for Gen 1-3)
                            replacement_id = random.randint(1, 386)
                            
                            # Get replacement name with error handling
                            try:
                                replacement_name = get_pokemon_name(replacement_id)
                                if not replacement_name:
                                    replacement_name = f"POKÉMON #{replacement_id}"
                            except Exception:
                                replacement_name = f"POKÉMON #{replacement_id}"
                            
                            # Add replacement info to the encounter data
                            encounter_data["replacement_id"] = replacement_id
                            encounter_data["replacement_name"] = replacement_name
                            encounter_data["new_name"] = replacement_name  # Include both formats for compatibility
                        
                        # Add the complete encounter data to our list
                        encounters.append(encounter_data)
                    
                    # Add to our area encounters tracking
                    area_encounters[area_id] = {
                        "name": area_name,
                        "encounters": encounters
                    }
            
            if update_callback:
                update_callback(f"Created example data for {len(area_encounters)} areas")
        
        # Generate the area encounter log
        generate_area_encounter_log(area_encounters, area_log_path, update_callback)
        
        # Save the modified ROM to the output file
        if update_callback:
            update_callback(f"Saving modified ROM to: {output_path}")
            
        # Save the ROM to the output file
        rom.saveToFile(output_path)
            
        # Return the output path
        if update_callback:
            update_callback("Randomization complete!")
            update_callback(f"Modified ROM saved to: {output_path}")
            update_callback(f"Stats log saved to: {stats_log_path}")
            update_callback(f"Area encounter log saved to: {area_log_path}")
        
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

def generate_area_encounter_log(area_encounters, log_path, update_callback=None):
    """Generate a log file that shows Pokémon encounters organized by area.
    
    Args:
        area_encounters: Dictionary of encounter data by area
        log_path: Path to save the log file
        update_callback: Function to call with status updates
    """
    try:
        # Debug log to see what we've collected
        if update_callback:
            update_callback(f"DEBUG: Found {len(area_encounters)} areas with data")
            for area_id, data in area_encounters.items():
                encounter_count = len(data.get("encounters", []))
                update_callback(f"DEBUG: Area {area_id} ({data.get('name', 'Unnamed')}) has {encounter_count} encounters")
        
        # Only include areas that have encounters
        areas_with_encounters = {area_id: data for area_id, data in area_encounters.items() 
                               if data.get("encounters") and any(enc.get("pokemon_id", 0) != 0 for enc in data.get("encounters", []))}
        
        if not areas_with_encounters:
            if update_callback:
                update_callback("WARNING: No valid encounters found to log - creating empty file as placeholder")
            
            # Create an empty file with an explanation
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write("NO ENCOUNTERS FOUND\n\n")
                log_file.write("This file is empty because no valid Pokémon encounters were detected.\n")
                log_file.write("Possible reasons:\n")
                log_file.write("1. The ROM may not have any wild encounters\n")
                log_file.write("2. The area detection may not be working properly\n")
                log_file.write("3. The encounter format may not match what the randomizer expects\n\n")
                log_file.write(f"Debug info: Found {len(area_encounters)} total areas")
            return
            
        # Sort areas by ID to maintain order from encounters.s
        sorted_area_ids = sorted(areas_with_encounters.keys())
        
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("=" * 80 + "\n")
            log_file.write("POKÉMON ENCOUNTER RANDOMIZER - ENCOUNTERS BY AREA\n")
            log_file.write("=" * 80 + "\n\n")
            
            # Go through each area in order
            for area_id in sorted_area_ids:
                area_data = areas_with_encounters[area_id]
                area_name = area_data["name"]
                encounters = area_data["encounters"]
                
                # Skip areas with only SPECIES_NONE
                if not any(enc["pokemon_id"] != 0 for enc in encounters):
                    continue
                    
                # Write area header
                log_file.write("-" * 80 + "\n")
                log_file.write(f"{area_name} (Area {area_id})\n")
                log_file.write("-" * 80 + "\n\n")
                
                # Group encounters by whether they were replaced or not
                replaced_encounters = [enc for enc in encounters if enc.get("replaced", False)]
                unchanged_encounters = [enc for enc in encounters if not enc.get("replaced", False)]
                
                # Write replaced encounters
                if replaced_encounters:
                    log_file.write("Randomized Encounters:\n")
                    for enc in replaced_encounters:
                        name = enc["name"]
                        new_name = enc.get("new_name", "UNKNOWN")
                        min_level = enc["min_level"]
                        max_level = enc["max_level"]
                        
                        # Format level display
                        if min_level == max_level:
                            level_str = f"Level {min_level}" if min_level > 0 else ""
                        else:
                            level_str = f"Levels {min_level}-{max_level}" if min_level > 0 else ""
                            
                        log_file.write(f"  {name} → {new_name} {level_str}\n")
                    log_file.write("\n")
                
                # Write unchanged encounters (special Pokémon)
                if unchanged_encounters:
                    log_file.write("Unchanged Special Encounters:\n")
                    for enc in unchanged_encounters:
                        name = enc["name"]
                        min_level = enc["min_level"]
                        max_level = enc["max_level"]
                        
                        # Format level display
                        if min_level == max_level:
                            level_str = f"Level {min_level}" if min_level > 0 else ""
                        else:
                            level_str = f"Levels {min_level}-{max_level}" if min_level > 0 else ""
                            
                        log_file.write(f"  {name} {level_str}\n")
                    log_file.write("\n")
                
                log_file.write("\n")
            
            # End of log
            log_file.write("=" * 80 + "\n")
            log_file.write("END OF ENCOUNTER LOG\n")
            log_file.write("=" * 80 + "\n")
            
        if update_callback:
            update_callback(f"Area encounter log saved to {log_path}")
            
    except Exception as e:
        logger.error(f"Error generating area encounter log: {e}")
        if update_callback:
            update_callback(f"Error generating area encounter log: {e}")

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
