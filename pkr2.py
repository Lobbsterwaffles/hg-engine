#!/usr/bin/env python3

"""
Pokémon Encounter Randomizer using ndspy

This version uses the ndspy library to handle NDS ROM files directly,
without requiring external tools like ndstool.
"""

import os
import sys
import random
import json
import argparse
import logging
import traceback
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QProgressBar, QTextEdit,
    QCheckBox, QSpinBox, QComboBox, QGroupBox, QFormLayout,
    QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import ndspy.rom


from randomize_encounters import randomize_encounters


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Settings file to remember user preferences
SETTINGS_FILE = "randomizer_settings.json"

# List of Pokémon that should not be replaced when randomizing
SPECIAL_POKEMON = set([
    # Legendaries and special Pokémon
    150, 151,  # Mewtwo, Mew
    243, 244, 245,  # Raikou, Entei, Suicune
    249, 250, 251,  # Lugia, Ho-Oh, Celebi
    377, 378, 379, 380, 381, 382, 383, 384, 385, 386,  # Gen 3 legendaries
    480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494,  # Gen 4 legendaries
])

def load_settings():
    """Load user settings from the settings file."""
    default_settings = {
        "last_rom_path": "",
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

def save_settings(settings):
    """Save user settings to the settings file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving settings: {e}")

class RandomizerThread(QThread):
    """Thread for running the randomization process without freezing the GUI."""
    progress_update = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, rom_path, output_path):
        super().__init__()
        self.rom_path = rom_path
        self.output_path = output_path
        self.rom_bytes = None

    def run(self):
        try:
            rom = ndspy.rom.NintendoDSRom.fromFile(self.rom_path)

            randomize_encounters(rom)

            rom.saveToFile(self.output_path)

            self.finished_signal.emit(True, f"Randomization completed successfully!\nOutput saved to: {self.output_path}")
        except Exception as e:
            # Get the full stack trace as a string
            error_traceback = traceback.format_exc()
            
            # Log the full error details
            logger.error(f"Error during randomization: {e}\n{error_traceback}")
            
            # Show a more detailed error message to the user
            error_message = f"Randomization failed: {str(e)}\n\nFull Error Details (for debugging):\n{error_traceback}"
            
            error_message = f"Randomization failed: {str(e)}"
            self.finished_signal.emit(False, error_message)

class RandomizerGUI(QMainWindow):
    """GUI for the Pokémon encounter randomizer."""
    
    def __init__(self):
        super().__init__()
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
            
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.log("Starting randomization...")
        
        # Disable UI during randomization
        self.start_button.setEnabled(False)
        
        # Start randomization in a separate thread
        self.randomizer_thread = RandomizerThread(
            input_path, output_path
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
    parser.add_argument("-c", "--cli", action="store_true", help="Run in command-line mode (no GUI)")
    
    args = parser.parse_args()
    
    # Command-line mode
    if args.cli and args.rom:
        try:
            output = randomize_encounters(
                args.rom, 
                args.output, 
                args.seed, 
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
