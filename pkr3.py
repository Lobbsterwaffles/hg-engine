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
    QTabWidget,
    QSlider,
    QRadioButton,
    QButtonGroup,
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

    def __init__(self, rom_path, output_path, randomize_encounters=True, randomize_trainers=True, 
                 type_themed_gyms=False, by_bst=False, pivot=False, fulcrum=False, type_mimic=False,
                 force_stab=False, optimized_movesets=False, held_items=False, no_useless_items=False,
                 optimized_items=False, goldilockes_scaling=False, 
                 log_function=None):
        super().__init__()
        self.rom_path = rom_path
        self.output_path = output_path
        self.randomize_encounters = randomize_encounters
        self.randomize_trainers = randomize_trainers
        self.type_themed_gyms = type_themed_gyms
        self.by_bst = by_bst
        self.pivot = pivot
        self.fulcrum = fulcrum
        self.type_mimic = type_mimic
        self.force_stab = force_stab
        self.optimized_movesets = optimized_movesets
        self.held_items = held_items
        self.no_useless_items = no_useless_items
        self.optimized_items = optimized_items
        self.goldilockes_scaling = goldilockes_scaling
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

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Pokémon Encounters tab
        encounters_tab = QWidget()
        encounters_layout = QVBoxLayout(encounters_tab)
        
        # Encounters randomization options
        encounters_options_group = QGroupBox("Wild Encounter Options")
        encounters_options_layout = QVBoxLayout()
        
        self.randomize_encounters_checkbox = QCheckBox("Randomize Wild Encounters")
        self.randomize_encounters_checkbox.setChecked(True)  # Checked by default
        encounters_options_layout.addWidget(self.randomize_encounters_checkbox)
        
        encounters_options_group.setLayout(encounters_options_layout)
        encounters_layout.addWidget(encounters_options_group)
        encounters_layout.addStretch(1)  # Add stretch to keep controls at the top
        
        # Trainers tab
        trainers_tab = QWidget()
        trainers_layout = QVBoxLayout(trainers_tab)
        
        # First add the Bosses panel (at the top)
        boss_movesets_group = QGroupBox("Bosses")
        boss_movesets_layout = QVBoxLayout()
        
        # Create a horizontal layout for the first row of checkboxes
        first_row_layout = QHBoxLayout()
        
        # Add the checkboxes for Boss Movesets side by side
        self.force_stab_checkbox = QCheckBox("Force Damaging STAB move")
        first_row_layout.addWidget(self.force_stab_checkbox)
        
        first_row_layout.addSpacing(20)  # Add some space between the checkboxes
        
        self.optimized_movesets_checkbox = QCheckBox("Optimized Movesets")
        first_row_layout.addWidget(self.optimized_movesets_checkbox)
        
        # Add stretch at the end to keep everything left-aligned
        first_row_layout.addStretch(1)
        
        # Add the first row to the main layout
        boss_movesets_layout.addLayout(first_row_layout)
        
        # Type-Themed Gyms horizontal layout with sub-options to the right
        type_themed_row = QHBoxLayout()
        
        # Type-Themed Gyms checkbox on the left
        self.type_themed_gyms_checkbox = QCheckBox("Type-Themed Gyms")
        type_themed_row.addWidget(self.type_themed_gyms_checkbox)
        type_themed_row.addSpacing(20)  # Space between checkbox and sub-options
        
        # Sub-options to the right of Type-Themed Gyms with tooltips
        # Pivot with tooltip
        pivot_layout = QHBoxLayout()
        self.pivot_checkbox = QCheckBox("Pivot")
        pivot_tooltip = "A defensive swap into the type's common weaknesses.\n\nExample: Fire is weak to Ground/Rock/Water ->\na Grass/Fighting dual-type resists all three."
        self.pivot_checkbox.setToolTip(pivot_tooltip)
        pivot_layout.addWidget(self.pivot_checkbox)
        
        # Add question mark icon directly next to Pivot checkbox text
        pivot_help_label = QLabel("(?)")
        pivot_help_label.setToolTip(pivot_tooltip)
        pivot_layout.addWidget(pivot_help_label)
        pivot_layout.setSpacing(0)  # No space between checkbox and label
        pivot_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins completely
        
        # Add the pivot layout to the main row
        type_themed_row.addLayout(pivot_layout)
        
        type_themed_row.addSpacing(10)  # Space between sub-options
        
        # Fulcrum with tooltip
        fulcrum_layout = QHBoxLayout()
        self.fulcrum_checkbox = QCheckBox("Fulcrum")
        fulcrum_tooltip = "Has good offensive coverage against theme type's common weaknesses.\n\nExample: Fire is weak to Ground/Rock/Water ->\na Water/Electric dual-type hits all 3 with STAB."
        self.fulcrum_checkbox.setToolTip(fulcrum_tooltip)
        fulcrum_layout.addWidget(self.fulcrum_checkbox)
        
        fulcrum_help_label = QLabel("(?)")
        fulcrum_help_label.setToolTip(fulcrum_tooltip)
        fulcrum_layout.addWidget(fulcrum_help_label)
        fulcrum_layout.setSpacing(0)  # No space between checkbox and label
        fulcrum_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins completely
        
        type_themed_row.addLayout(fulcrum_layout)
        
        type_themed_row.addSpacing(10)  # Space between sub-options
        
        # Type Mimic with tooltip
        type_mimic_layout = QHBoxLayout()
        self.type_mimic_checkbox = QCheckBox("Type Mimic")
        type_mimic_tooltip = "Off-type pokemon which is thematically\nsimilar to the type.\n\nExample: Dragon -> Charizard"
        self.type_mimic_checkbox.setToolTip(type_mimic_tooltip)
        type_mimic_layout.addWidget(self.type_mimic_checkbox)
        
        type_mimic_help_label = QLabel("(?)")
        type_mimic_help_label.setToolTip(type_mimic_tooltip)
        type_mimic_layout.addWidget(type_mimic_help_label)
        type_mimic_layout.setSpacing(0)  # No space between checkbox and label
        type_mimic_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins completely
        
        type_themed_row.addLayout(type_mimic_layout)
        
        # Add the Type-Themed Gyms row to the layout
        boss_movesets_layout.addLayout(type_themed_row)
        
        # Goldilockes Scaling checkbox (right-aligned)
        goldilockes_layout = QHBoxLayout()
        goldilockes_layout.addStretch(1)  # This pushes the checkbox to the right
        
        self.goldilockes_scaling_checkbox = QCheckBox("Goldilockes Scaling")
        self.goldilockes_scaling_checkbox.setEnabled(False)  # Disabled by default
        goldilockes_layout.addWidget(self.goldilockes_scaling_checkbox)
        
        boss_movesets_layout.addLayout(goldilockes_layout)
        
        # Set the layout for the Boss Movesets panel
        boss_movesets_group.setLayout(boss_movesets_layout)
        trainers_layout.addWidget(boss_movesets_group)
        
        # Now add the Trainers randomization options panel (below the Boss Movesets panel)
        trainers_options_group = QGroupBox("Trainer Options")
        trainers_options_layout = QVBoxLayout()
        
        # First row: Randomize Trainer Pokémon with By BST to the right
        first_trainers_row = QHBoxLayout()
        
        self.randomize_trainers_checkbox = QCheckBox("Randomize Trainer Pokémon")
        self.randomize_trainers_checkbox.setChecked(True)  # Checked by default
        first_trainers_row.addWidget(self.randomize_trainers_checkbox)
        
        first_trainers_row.addSpacing(20)  # Space between checkboxes
        
        self.by_bst_checkbox = QCheckBox("By BST")
        self.by_bst_checkbox.setEnabled(False)  # Disabled by default
        first_trainers_row.addWidget(self.by_bst_checkbox)
        
        # Add stretch to keep items aligned to the left
        first_trainers_row.addStretch(1)
        
        trainers_options_layout.addLayout(first_trainers_row)
        
        # Level Multiplier row with radio buttons and text field
        level_multiplier_row = QHBoxLayout()
        
        # Add label for Level Multiplier
        level_multiplier_label = QLabel("Level Multiplier:")
        level_multiplier_row.addWidget(level_multiplier_label)
        
        level_multiplier_row.addSpacing(10)  # Space after label
        
        # Radio button for 1x
        self.radio_1x = QRadioButton("1x")
        self.radio_1x.setChecked(True)  # Default option
        level_multiplier_row.addWidget(self.radio_1x)
        
        # Radio button for 1.1x
        self.radio_1_1x = QRadioButton("1.1x")
        level_multiplier_row.addWidget(self.radio_1_1x)
        
        # Radio button for 1.5x
        self.radio_1_5x = QRadioButton("1.5x")
        level_multiplier_row.addWidget(self.radio_1_5x)
        
        # Custom text field
        self.custom_multiplier = QLineEdit()
        self.custom_multiplier.setMaxLength(3)  # Limit to 3 characters
        self.custom_multiplier.setFixedWidth(40)  # Make it small
        level_multiplier_row.addWidget(self.custom_multiplier)
        
        # Radio button for custom
        self.radio_custom = QRadioButton("")
        level_multiplier_row.addWidget(self.radio_custom)
        
        # Set up a button group to make the radio buttons exclusive
        self.multiplier_group = QButtonGroup()
        self.multiplier_group.addButton(self.radio_1x)
        self.multiplier_group.addButton(self.radio_1_1x)
        self.multiplier_group.addButton(self.radio_1_5x)
        self.multiplier_group.addButton(self.radio_custom)
        
        # Connect custom text field to select its radio button when text is entered
        self.custom_multiplier.textChanged.connect(self.select_custom_radio)
        
        # Add stretch to fill remaining space
        level_multiplier_row.addStretch(1)
        
        # Add the level multiplier row to the layout
        trainers_options_layout.addLayout(level_multiplier_row)
        
        # Held Items horizontal layout with sub-options to the right
        held_items_row = QHBoxLayout()
        
        # Held Items checkbox on the left
        self.held_items_checkbox = QCheckBox("Held Items")
        held_items_row.addWidget(self.held_items_checkbox)
        held_items_row.addSpacing(20)  # Space between checkbox and sub-options
        
        # Sub-options to the right of Held Items
        self.no_useless_items_checkbox = QCheckBox("no useless items")
        self.no_useless_items_checkbox.setEnabled(False)  # Disabled by default
        held_items_row.addWidget(self.no_useless_items_checkbox)
        
        held_items_row.addSpacing(10)  # Space between sub-options
        
        self.optimized_items_checkbox = QCheckBox("optimized items")
        self.optimized_items_checkbox.setEnabled(False)  # Disabled by default
        held_items_row.addWidget(self.optimized_items_checkbox)
        
        # Add the held items row to the layout
        trainers_options_layout.addLayout(held_items_row)
        
        # Force fully-evolved with slider row
        fully_evolved_row = QHBoxLayout()
        self.force_fully_evolved_checkbox = QCheckBox("Force fully-evolved")
        fully_evolved_row.addWidget(self.force_fully_evolved_checkbox)
        
        fully_evolved_row.addSpacing(10)  # Space between checkbox and slider
        
        # Add a slider that goes from 1 to 100
        self.fully_evolved_slider = QSlider(Qt.Horizontal)
        self.fully_evolved_slider.setMinimum(1)
        self.fully_evolved_slider.setMaximum(100)
        self.fully_evolved_slider.setValue(50)  # Default value
        self.fully_evolved_slider.setEnabled(False)  # Disabled by default
        fully_evolved_row.addWidget(self.fully_evolved_slider)
        
        # Add a label to show the current value
        self.slider_value_label = QLabel("50")
        fully_evolved_row.addWidget(self.slider_value_label)
        
        # Connect the slider value change to update the label
        self.fully_evolved_slider.valueChanged.connect(self.update_slider_label)
        
        # Connect the checkbox to enable/disable the slider
        self.force_fully_evolved_checkbox.stateChanged.connect(self.update_slider_enabled)
        
        trainers_options_layout.addLayout(fully_evolved_row)
        
        # AI options row
        ai_options_row = QHBoxLayout()
        self.max_trainer_ai_checkbox = QCheckBox("Max Trainer AI")
        ai_options_row.addWidget(self.max_trainer_ai_checkbox)
        
        ai_options_row.addSpacing(20)  # Space between checkboxes
        
        self.experimental_smart_ai_checkbox = QCheckBox("Experimental Smart AI")
        ai_options_row.addWidget(self.experimental_smart_ai_checkbox)
        
        # Add stretch to keep items aligned to the left
        ai_options_row.addStretch(1)
        
        trainers_options_layout.addLayout(ai_options_row)
        
        # Set the layout for the Trainer Options panel
        trainers_options_group.setLayout(trainers_options_layout)
        trainers_layout.addWidget(trainers_options_group)
        
        # Connect checkboxes to their respective handler methods
        # Type-Themed Gyms is now in Boss Movesets panel but still needs to be connected to trainers checkbox
        self.randomize_trainers_checkbox.stateChanged.connect(self.update_type_themed_gyms_enabled)
        self.type_themed_gyms_checkbox.stateChanged.connect(self.update_sub_options_state)
        
        # Connect held items checkboxes to their handlers
        self.held_items_checkbox.stateChanged.connect(self.update_held_items_options)
        self.optimized_items_checkbox.stateChanged.connect(self.update_goldilockes_scaling_state)
        
        trainers_options_group.setLayout(trainers_options_layout)
        trainers_layout.addWidget(trainers_options_group)
        trainers_layout.addStretch(1)  # Add stretch to keep controls at the top
        
        # Add tabs to tab widget
        self.tab_widget.addTab(encounters_tab, "Pokémon Encounters")
        self.tab_widget.addTab(trainers_tab, "Trainers")
        
        # General options group
        options_group = QGroupBox("General Options")
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
                
    def update_type_themed_gyms_enabled(self, state):
        """Enable or disable the Type Themed Gyms checkbox and related options based on trainer randomization"""
        # Enable/disable all the first level checkboxes based on trainer randomization
        is_enabled = (state == Qt.Checked)
        self.by_bst_checkbox.setEnabled(is_enabled)
        self.type_themed_gyms_checkbox.setEnabled(is_enabled)
        
        # If trainers aren't being randomized, make sure all checkboxes are unchecked
        if not is_enabled:
            self.by_bst_checkbox.setChecked(False)
            self.type_themed_gyms_checkbox.setChecked(False)
            self.pivot_checkbox.setChecked(False)
            self.fulcrum_checkbox.setChecked(False)
            self.type_mimic_checkbox.setChecked(False)
            
        # Also update the second level checkboxes state
        self.update_sub_options_state()
        
    def update_sub_options_state(self):
        """Enable or disable the second-level checkboxes based on Type Themed Gyms checkbox"""
        is_enabled = self.type_themed_gyms_checkbox.isChecked() and self.randomize_trainers_checkbox.isChecked()
        self.pivot_checkbox.setEnabled(is_enabled)
        self.fulcrum_checkbox.setEnabled(is_enabled)
        self.type_mimic_checkbox.setEnabled(is_enabled)
        
        # If Type Themed Gyms is unchecked, make sure all second level checkboxes are unchecked
        if not is_enabled:
            self.pivot_checkbox.setChecked(False)
            self.fulcrum_checkbox.setChecked(False)
            self.type_mimic_checkbox.setChecked(False)
    
    def update_held_items_options(self, state):
        """Enable or disable the held items sub-options based on Held Items checkbox"""
        # The 'state' parameter is the state of the checkbox (checked or not)
        is_enabled = (state == Qt.Checked)
        
        # Enable or disable the first level of indented checkboxes
        self.no_useless_items_checkbox.setEnabled(is_enabled)
        self.optimized_items_checkbox.setEnabled(is_enabled)
        
        # If Held Items is unchecked, uncheck all sub-options
        if not is_enabled:
            self.no_useless_items_checkbox.setChecked(False)
            self.optimized_items_checkbox.setChecked(False)
            self.goldilockes_scaling_checkbox.setChecked(False)
            self.goldilockes_scaling_checkbox.setEnabled(False)
        else:
            # If Held Items is checked, check if optimized_items is also checked
            self.update_goldilockes_scaling_state()
    
    def update_goldilockes_scaling_state(self):
        """Enable or disable the Goldilockes Scaling checkbox based on optimized items"""
        # Only enable Goldilockes Scaling if both Held Items and optimized items are checked
        is_enabled = self.held_items_checkbox.isChecked() and self.optimized_items_checkbox.isChecked()
        self.goldilockes_scaling_checkbox.setEnabled(is_enabled)
        
        # If optimized items is unchecked, uncheck Goldilockes Scaling
        if not is_enabled:
            self.goldilockes_scaling_checkbox.setChecked(False)
            
    def update_slider_label(self, value):
        """Update the label that shows the current slider value"""
        self.slider_value_label.setText(str(value))
        
    def update_slider_enabled(self, state):
        """Enable or disable the slider based on the Force fully-evolved checkbox"""
        self.fully_evolved_slider.setEnabled(state == Qt.Checked)
        
    def select_custom_radio(self, text):
        """Select the custom radio button when text is entered in the custom multiplier field"""
        if text:
            self.radio_custom.setChecked(True)

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
        type_themed_gyms = self.type_themed_gyms_checkbox.isChecked()
        by_bst = self.by_bst_checkbox.isChecked()
        pivot = self.pivot_checkbox.isChecked()
        fulcrum = self.fulcrum_checkbox.isChecked()
        type_mimic = self.type_mimic_checkbox.isChecked()
        
        # Get boss movesets options
        force_stab = self.force_stab_checkbox.isChecked()
        optimized_movesets = self.optimized_movesets_checkbox.isChecked()
        held_items = self.held_items_checkbox.isChecked()
        no_useless_items = self.no_useless_items_checkbox.isChecked()
        optimized_items = self.optimized_items_checkbox.isChecked()
        goldilockes_scaling = self.goldilockes_scaling_checkbox.isChecked()
        
        # Start randomization in a separate thread
        self.randomizer_thread = RandomizerThread(
            input_path, 
            output_path, 
            randomize_encounters=randomize_encounters,
            randomize_trainers=randomize_trainers,
            type_themed_gyms=type_themed_gyms,
            by_bst=by_bst,
            pivot=pivot,
            fulcrum=fulcrum,
            type_mimic=type_mimic,
            force_stab=force_stab,
            optimized_movesets=optimized_movesets,
            held_items=held_items,
            no_useless_items=no_useless_items,
            optimized_items=optimized_items,
            goldilockes_scaling=goldilockes_scaling,
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
