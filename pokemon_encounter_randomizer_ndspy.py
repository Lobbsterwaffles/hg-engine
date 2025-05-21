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

# Import the complete Pokémon data
from pokemon_data import POKEMON_BST, SPECIAL_POKEMON

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
            logger.error(f"Error during randomization: {e}")
            self.finished_signal.emit(False, f"Randomization failed: {str(e)}")

def find_similar_pokemon(species_id, mapping, used, similar_strength=True):
    """Find a similar-strength Pokémon to replace the original."""
    # If already mapped, use consistent replacement
    if species_id in mapping:
        return mapping[species_id]
    
    # Don't replace special Pokémon
    if species_id in SPECIAL_POKEMON:
        return species_id
    
    # Skip if not in our database
    if species_id not in POKEMON_BST:
        return species_id
    
    if similar_strength:
        # Find Pokémon with similar BST (within 15% for more options)
        original_bst = POKEMON_BST[species_id]["bst"]
        min_bst = original_bst * 0.85
        max_bst = original_bst * 1.15
        
        candidates = []
        for pid, data in POKEMON_BST.items():
            # Skip special Pokémon and the same species
            if pid in SPECIAL_POKEMON or pid == species_id:
                continue
                
            # Be less strict about "used" Pokémon
            # Only skip if we have plenty of options
            if pid in used and len(candidates) > 10:
                continue
                
            # Check if BST is in range
            if min_bst <= data["bst"] <= max_bst:
                candidates.append(pid)
    else:
        # Use any Pokémon except special ones and the original
        candidates = []
        for pid in POKEMON_BST.keys():
            if pid not in SPECIAL_POKEMON and pid != species_id:
                candidates.append(pid)
    
    # Choose random replacement if we have candidates
    if candidates:
        # If we have few candidates, we can re-use Pokémon
        if len(candidates) < 5:
            # Just pick randomly and don't mark as used
            new_id = random.choice(candidates)
        else:
            # We have plenty of options, so avoid re-using if possible
            unused_candidates = [pid for pid in candidates if pid not in used]
            if unused_candidates:
                new_id = random.choice(unused_candidates)
            else:
                new_id = random.choice(candidates)
            
            # Mark as used
            used.add(new_id)
            
        mapping[species_id] = new_id
        return new_id
    
    # If we get here, we couldn't find a replacement, so just pick any valid Pokémon
    all_options = [pid for pid in POKEMON_BST.keys() 
                 if pid != species_id and pid not in SPECIAL_POKEMON]
    
    if all_options:
        new_id = random.choice(all_options)
        mapping[species_id] = new_id
        return new_id
        
    # Absolute fallback - keep original
    return species_id

def find_pokemon_offsets(data):
    """Find offsets in `data` that likely hold Pokémon species IDs.

    This uses two heuristics that work well for HG/SS encounter files:
    1. "Cluster" heuristic: contiguous lists of at least 4 valid species IDs
       stored as little-endian 16-bit values (common for land encounters).
    2. "Water/Fishing" heuristic: 4-byte records of the form
       [chance][level][species_lo][species_hi].  The chance and level bytes
       must both be in the 1-100 range.
       
    IMPROVED VALIDATION:
    - Filters out potential level 1 encounters as they're not valid in-game
    - Uses higher validation thresholds to avoid false positives
    - Requires longer contiguous sequences (12+ not just 4+) to match route tables
    """
    offsets: list[int] = []

    data_len = len(data)
    
    # First check for the walkrate/surfrate header pattern
    # This is common at the start of encounter files
    has_header_pattern = False
    if len(data) >= 16:
        walkrate = data[0]
        surfrate = data[1]
        rocksmashrate = data[2]
        # Valid rate values should be in a reasonable range
        if 0 <= walkrate <= 100 and 0 <= surfrate <= 100 and 0 <= rocksmashrate <= 100:
            has_header_pattern = True

    # ---------------------------------------------
    # 1. Cluster heuristic (2-byte species lists)
    # ---------------------------------------------
    # For encounter clusters, we're usually looking for 12 consecutive entries
    # (morning/day/night slots)
    i = 0
    while i < data_len - 1:
        val = data[i] | (data[i + 1] << 8)
        species_id = val & 0x7FF  # lower 11 bits
        if 1 <= species_id <= 649:
            cluster_positions = [i]
            j = i + 2
            while j < data_len - 1:
                nxt = data[j] | (data[j + 1] << 8)
                nxt_species = nxt & 0x7FF
                if 1 <= nxt_species <= 649:
                    cluster_positions.append(j)
                    j += 2
                else:
                    break
                    
            # In the encounter files, we're looking for clusters of 12 entries
            # (morning/day/night), but we'll accept 8+ to be a bit flexible,
            # especially in files that have the correct header pattern
            min_cluster_size = 8 if has_header_pattern else 12
            if len(cluster_positions) >= min_cluster_size:
                offsets.extend(cluster_positions)
            i = j  # continue scanning after the cluster
        else:
            i += 2

    # --------------------------------------------------
    # 2. Water / fishing encounter heuristic (4-byte)
    # --------------------------------------------------
    for off in range(0, data_len - 3, 4):
        chance = data[off]
        level = data[off + 1]
        species_val = data[off + 2] | (data[off + 3] << 8)
        species_id = species_val & 0x7FF
        
        # IMPORTANT: Filter out level 1 since it's not valid in the wild
        # Valid chance is 1-100, valid level is 2-100
        if 1 <= chance <= 100 and 2 <= level <= 100 and 1 <= species_id <= 649:
            offsets.append(off + 2)  # store pointer to species word (little-endian)

    # Deduplicate and sort
    return sorted(set(offsets))

def randomize_encounters(rom_path, output_path=None, seed=None, similar_strength=True,
                         update_callback=None, progress_callback=None):
    """
    Randomize Pokémon encounters in the ROM.
    
    Args:
        rom_path: Path to the input ROM
        output_path: Path for the output ROM (if None, uses input name + _randomized)
        seed: Random seed for consistent randomization
        similar_strength: Whether to replace Pokémon with others of similar strength
        update_callback: Function to call with status updates
        progress_callback: Function to call with progress percentage
    
    Returns:
        Path to the randomized ROM
    """
    # Track all Pokémon changes for the log file
    pokemon_changes = []
    # Set up output path if not provided
    if output_path is None:
        base, ext = os.path.splitext(rom_path)
        output_path = f"{base}_randomized{ext}"
    
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
        
        # Maps original Pokémon to their replacements for consistency
        mapping = {}
        # Track which Pokémon have been used as replacements
        used = set()
        
        # Track how many Pokémon we found and changed
        total_pokemon_found = 0
        
        # List to store detailed change information for logging
        pokemon_changes = []
        
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
            
            pokemon_offsets = find_pokemon_offsets(modified_data)
            grass_pokemon = len(pokemon_offsets)  # For progress logs, treat all together
            
            # Progress reporting - let the user know what we're finding
            if (grass_pokemon > 0) and update_callback and i % 25 == 0:
                update_callback(f"Location #{i}: Found {grass_pokemon} Pokémon entries")
            
            # Track changes for this location
            location_changes = 0
            location_species_ids = set()

            # Now replace ALL Pokémon encounters at the detected offsets
            for offset in pokemon_offsets:
                val = modified_data[offset] | (modified_data[offset + 1] << 8)
                species_id = val & 0x7FF
                
                # Skip invalid entries and SPECIES_NONE (species_id == 0)
                if species_id == 0:
                    continue
                    
                # IMPORTANT: We need to randomize ALL species, even if we don't recognize them
                # For species not in our database, we'll assign a default BST
                if species_id not in POKEMON_BST:
                    # Add this species to our database with a default BST of 350
                    POKEMON_BST[species_id] = {"name": f"SPECIES_{species_id}", "bst": 350}
                
                # Find a replacement Pokémon
                new_species = find_similar_pokemon(species_id, mapping, used, similar_strength)
                
                # Apply the change to the data
                new_val = (val & 0xF800) | (new_species & 0x7FF)
                struct.pack_into('<H', modified_data, offset, new_val)
                
                # Count this change
                total_pokemon_found += 1
                location_changes += 1
                location_species_ids.add(species_id)
                
                # Record this change for the log if it's actually different
                if species_id != new_species:
                    # Get Pokémon names for the log
                    original_name = f"POKEMON_{species_id}"
                    new_name = f"POKEMON_{new_species}"
                    
                    if species_id in POKEMON_BST:
                        original_name = POKEMON_BST[species_id]["name"]
                        original_bst = POKEMON_BST[species_id]["bst"]
                    else:
                        original_bst = "???"
                        
                    if new_species in POKEMON_BST:
                        new_name = POKEMON_BST[new_species]["name"]
                        new_bst = POKEMON_BST[new_species]["bst"]
                    else:
                        new_bst = "???"
                    
                    # Add to our changes list
                    pokemon_changes.append({
                        "original_id": species_id,
                        "original_name": original_name,
                        "original_bst": original_bst,
                        "new_id": new_species,
                        "new_name": new_name,
                        "new_bst": new_bst
                    })
            
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
        
        # Sort changes by original Pokémon ID
        pokemon_changes.sort(key=lambda x: x["original_id"])
        
        # Count unique species that were randomized
        unique_original_species = set()
        unique_new_species = set()
        for change in pokemon_changes:
            unique_original_species.add(change["original_id"])
            unique_new_species.add(change["new_id"])
            
        if update_callback:
            update_callback(f"Randomized {len(unique_original_species)} unique Pokémon species!")
            update_callback(f"Used {len(unique_new_species)} unique Pokémon species as replacements!")
        
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("=" * 60 + "\n")
            log_file.write("POKÉMON ENCOUNTER RANDOMIZER CHANGES\n")
            log_file.write("=" * 60 + "\n\n")
            
            log_file.write(f"ROM: {os.path.basename(rom_path)}\n")
            log_file.write(f"Seed: {seed}\n")
            log_file.write(f"Similar Strength: {'Yes' if similar_strength else 'No'}\n\n")
            
            log_file.write("-" * 60 + "\n")
            log_file.write("ORIGINAL POKÉMON          ->  NEW POKÉMON\n")
            log_file.write("-" * 60 + "\n")
            
            # Group changes by original Pokémon (to avoid duplicates)
            unique_changes = {}
            for change in pokemon_changes:
                original_id = change["original_id"]
                if original_id not in unique_changes:
                    unique_changes[original_id] = change
            
            # Write each unique change
            for change in unique_changes.values():
                log_file.write(f"{change['original_name']:<20} ({change['original_bst']}) -> ")
                log_file.write(f"{change['new_name']:<15} ({change['new_bst']})\n")
            
            log_file.write("\n" + "=" * 60 + "\n")
            log_file.write(f"Total Pokémon Changed: {len(unique_changes)}\n")
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
        self.log("Select a ROM file to begin.")
    
    def log(self, message):
        """Add a message to the log display."""
        self.log_display.append(message)
        # Auto-scroll to the bottom
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def browse_input(self):
        """Browse for input ROM file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ROM File", "", "NDS ROM Files (*.nds);;All Files (*)"
        )
        if file_path:
            self.input_path_label.setText(file_path)
            
            # Auto-generate output path
            base, ext = os.path.splitext(file_path)
            output_path = f"{base}_randomized{ext}"
            self.output_path_label.setText(output_path)
            
            # Enable start button if we have both paths
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
