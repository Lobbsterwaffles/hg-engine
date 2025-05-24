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
import traceback
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QProgressBar,
    QTextEdit,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QLineEdit,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

import ndspy.rom

from randomize_encounters import randomize_encounters
from randomize_trainers import randomize_trainers

# Settings file to remember user preferences
SETTINGS_FILE = "randomizer_settings.json"


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
        print(f"Error loading settings: {e}")
        return default_settings


def save_settings(settings):
    """Save user settings to the settings file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error saving settings: {e}")


class RandomizerThread(QThread):
    """Thread for running the randomization process without freezing the GUI."""

    progress_update = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, rom_path, output_path, randomize_encounters=True, randomize_trainers=True, log_function=None):
        super().__init__()
        self.rom_path = rom_path
        self.output_path = output_path
        self.randomize_encounters = randomize_encounters
        self.randomize_trainers = randomize_trainers
        self.rom_bytes = None
        self.log_function = log_function

    def run(self):
        try:
            rom = ndspy.rom.NintendoDSRom.fromFile(self.rom_path)
            
            # Randomize encounters if selected
            if self.randomize_encounters:
                if self.log_function:
                    self.log_function("Starting encounter randomization...")
                    
                # Pass the progress callback to the randomize_encounters function
                randomize_encounters(
                    rom,
                    self.log_function,
                    lambda percent: self.progress_value.emit(percent),
                )
                
            # Randomize trainers if selected
            if self.randomize_trainers:
                if self.log_function:
                    self.log_function("Starting trainer randomization...")
                    
                # Pass the progress callback to the randomize_trainers function
                randomize_trainers(
                    rom,
                    self.log_function,
                    lambda percent: self.progress_value.emit(percent),
                )

            # Log the start of ROM saving
            if self.log_function:
                self.log_function("Saving randomized ROM to file...")

            rom.saveToFile(self.output_path)

            # Log completion of ROM saving
            if self.log_function:
                self.log_function(f"ROM saved successfully to: {self.output_path}")

            # Determine what was randomized for the success message
            randomized_features = []
            if self.randomize_encounters:
                randomized_features.append("wild encounters")
            if self.randomize_trainers:
                randomized_features.append("trainer Pokémon")
            
            # Join the list of features into a readable string
            features_text = " and ".join(randomized_features)
            
            self.finished_signal.emit(
                True,
                f"Randomization of {features_text} completed successfully!\nOutput saved to: {self.output_path}",
            )
        except Exception as e:
            # Get the full stack trace as a string
            error_traceback = traceback.format_exc()

            # Log the full error details
            print(f"Error during randomization: {e}\n{error_traceback}")

            # Show a more detailed error message to the user
            error_message = f"Randomization failed: {str(e)}\n\nFull Error Details (for debugging):\n{error_traceback}"

            error_message = f"Randomization failed: {str(e)}"
            self.finished_signal.emit(False, error_message)


class RandomizerGUI(QMainWindow):
    """GUI for the Pokémon encounter randomizer."""

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        # Truncate log file on startup with UTF-8 encoding
        with open("randomizer.log", "w", encoding="utf-8") as f:
            f.write("")
        self.last_file_position = 0  # Track where we last read from the file
        self.original_log_content = ""  # Store original unfiltered log content
        self.init_ui()

        # Set up file tailing timer
        self.tail_timer = QTimer()
        self.tail_timer.timeout.connect(self.tail_log_file)
        self.tail_timer.start(100)  # Check every 100ms

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Pokémon Encounter Randomizer")
        self.setMinimumSize(800, 500)

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
        self.input_path_label.setStyleSheet(
            "background-color: #f0f0f0; padding: 5px; border-radius: 3px;"
        )
        self.browse_input_button = QPushButton("Browse...")
        self.browse_input_button.clicked.connect(self.browse_input)
        input_layout.addWidget(self.input_path_label, 1)
        input_layout.addWidget(self.browse_input_button)
        file_layout.addRow("Input ROM:", input_layout)

        # Output ROM selection
        output_layout = QHBoxLayout()
        self.output_path_label = QLabel("No file selected")
        self.output_path_label.setStyleSheet(
            "background-color: #f0f0f0; padding: 5px; border-radius: 3px;"
        )
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
        
        # Randomization type selection
        randomization_type_layout = QVBoxLayout()
        self.randomize_encounters_checkbox = QCheckBox("Randomize Wild Encounters")
        self.randomize_trainers_checkbox = QCheckBox("Randomize Trainer Pokémon")
        
        # Set both options checked by default
        self.randomize_encounters_checkbox.setChecked(True)
        self.randomize_trainers_checkbox.setChecked(True)
        
        randomization_type_layout.addWidget(self.randomize_encounters_checkbox)
        randomization_type_layout.addWidget(self.randomize_trainers_checkbox)
        options_layout.addRow(randomization_type_layout)

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

        # Search/filter area for log
        search_layout = QHBoxLayout()
        search_label = QLabel("Filter logs:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Type to filter log lines (case-insensitive)..."
        )
        self.search_box.textChanged.connect(self.filter_logs)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        progress_layout.addLayout(search_layout)

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
        # Only log to file, not GUI (to avoid threading issues)
        with open("randomizer.log", "a", encoding="utf-8") as f:
            f.write("Welcome to the Pokémon Encounter Randomizer!\n")

        # Load last ROM path if available
        last_rom_path = self.settings.get("last_rom_path", "")
        if last_rom_path and os.path.exists(last_rom_path):
            self.input_path_label.setText(last_rom_path)
            # Only log to file, not GUI (to avoid threading issues)
            with open("randomizer.log", "a", encoding="utf-8") as f:
                f.write(f"Loaded last used ROM: {last_rom_path}\n")

            # Set output path based on last ROM
            base, ext = os.path.splitext(last_rom_path)
            output_path = f"{base}_randomized{ext}"
            self.output_path_label.setText(output_path)

            # Enable start button
            self.start_button.setEnabled(True)
        else:
            # Only log to file, not GUI (to avoid threading issues)
            with open("randomizer.log", "a", encoding="utf-8") as f:
                f.write("Select a ROM file to begin.\n")

    def log(self, message):
        """Add a message to the log display."""
        # Only log to file, not GUI (to avoid threading issues)
        with open("randomizer.log", "a", encoding="utf-8") as f:
            f.write(message + "\n")

    def tail_log_file(self):
        """Read new content from the log file and update the display."""
        try:
            with open("randomizer.log", "r", encoding="utf-8") as f:
                f.seek(self.last_file_position)
                new_content = f.read()
                if new_content:
                    # Update the original log content
                    self.original_log_content += new_content

                    # If there's an active filter, reapply it to the entire content
                    search_text = self.search_box.text().lower()
                    if search_text:
                        lines = self.original_log_content.split("\n")
                        filtered_lines = [
                            line for line in lines if search_text in line.lower()
                        ]
                        self.log_display.setText("\n".join(filtered_lines))
                    else:
                        # No filter, just append new content
                        self.log_display.insertPlainText(new_content)

                    # Auto-scroll to the bottom
                    cursor = self.log_display.textCursor()
                    cursor.movePosition(cursor.End)
                    self.log_display.setTextCursor(cursor)

                    # Update our position tracker
                    self.last_file_position = f.tell()
        except (FileNotFoundError, PermissionError):
            # File might not exist yet or be locked, just ignore
            pass

    def filter_logs(self):
        """Filter log lines based on search text."""
        search_text = self.search_box.text().lower()
        lines = self.original_log_content.split("\n")
        filtered_lines = [line for line in lines if search_text in line.lower()]
        self.log_display.setText("\n".join(filtered_lines))

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
            # Only log to file, not GUI (to avoid threading issues)
            with open("randomizer.log", "a", encoding="utf-8") as f:
                f.write(f"Saved this ROM location for future use\n")

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

        # Check if at least one randomization option is selected
        if not self.randomize_encounters_checkbox.isChecked() and not self.randomize_trainers_checkbox.isChecked():
            QMessageBox.warning(self, "Error", "Please select at least one randomization option.")
            return
            
        # Get options
        seed = None
        if self.use_seed_checkbox.isChecked():
            seed = self.seed_spinbox.value()
            random.seed(seed)

        # Reset progress
        self.progress_bar.setValue(0)
        # Only log to file, not GUI (to avoid threading issues)
        with open("randomizer.log", "a", encoding="utf-8") as f:
            f.write("Starting randomization...\n")

        # Disable UI during randomization
        self.start_button.setEnabled(False)

        # Get randomization options
        randomize_encounters = self.randomize_encounters_checkbox.isChecked()
        randomize_trainers = self.randomize_trainers_checkbox.isChecked()
        
        # Start randomization in a separate thread
        self.randomizer_thread = RandomizerThread(
            input_path, 
            output_path, 
            randomize_encounters=randomize_encounters,
            randomize_trainers=randomize_trainers,
            log_function=self.log
        )
        self.randomizer_thread.progress_update.connect(self.log)
        self.randomizer_thread.progress_value.connect(self.progress_bar.setValue)
        self.randomizer_thread.finished_signal.connect(self.randomization_finished)
        self.randomizer_thread.start()

    def randomization_finished(self, success, message):
        """Handle randomization completion."""
        # Only log to file, not GUI (to avoid threading issues)
        with open("randomizer.log", "a", encoding="utf-8") as f:
            f.write(message + "\n")

        # Re-enable UI
        self.start_button.setEnabled(True)

        # Log completion message to the UI instead of showing a modal dialog
        status_message = "✅ " + message if success else "❌ " + message
        self.log(status_message)

        # Show error dialog only for failures
        if not success:
            QMessageBox.critical(self, "Error", message)


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Randomize Pokémon encounters in NDS ROMs"
    )
    parser.add_argument("rom", nargs="?", help="Input ROM file path")
    parser.add_argument("-o", "--output", help="Output ROM file path")
    parser.add_argument("-s", "--seed", type=int, help="Random seed")
    parser.add_argument(
        "-c", "--cli", action="store_true", help="Run in command-line mode (no GUI)"
    )

    args = parser.parse_args()

    # Command-line mode
    if args.cli and args.rom:
        try:
            output = randomize_encounters(
                args.rom, args.output, args.seed, update_callback=print
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
