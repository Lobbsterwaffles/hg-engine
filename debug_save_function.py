#!/usr/bin/env python3
"""
Debug script to isolate and test the save functionality in Pokemon Set Builder
"""

import sys
import traceback
import os
import datetime
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QMessageBox, QLabel

# This is a simplified version of the PokemonSetBuilder class
# that will help us test just the save functionality
class SaveTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pokemon Set Builder - Save Tester")
        self.resize(400, 300)
        
        # Initialize main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        
        # Add description
        description = QLabel(
            "This tool will test saving a Pokemon set with dummy data.\n"
            "It will try to create a set with moves of different types\n"
            "and save it to the 'sets' directory."
        )
        main_layout.addWidget(description)
        
        # Test data that matches what's in the real application
        self.current_pokemon = "SPECIES_PIKACHU"
        self.all_pokemon_data = {
            "SPECIES_PIKACHU": {"name": "Pikachu"}
        }
        
        # Initialize move data
        self.current_moves = ["MOVE_THUNDERBOLT", "MOVE_IRON_TAIL", "MOVE_QUICK_ATTACK", None]
        self.current_move_names = ["Thunderbolt", "Iron Tail", "Quick Attack", None]
        self.current_move_types = ["tm", "egg", "level_up", None]  # Add this line
        
        # Initialize ability data
        self.current_ability = "ABILITY_STATIC"
        
        # Add test buttons
        self.save_button = QPushButton("Test Save Function")
        self.save_button.clicked.connect(self.save_pokemon_set)
        main_layout.addWidget(self.save_button)
        
        self.debug_button = QPushButton("Print Debug Info")
        self.debug_button.clicked.connect(self.print_debug_info)
        main_layout.addWidget(self.debug_button)
    
    def print_debug_info(self):
        """Print debug information about the current state"""
        print("\n===== DEBUG INFORMATION =====")
        print(f"Current Pokemon: {self.current_pokemon}")
        print(f"Pokemon Data: {self.all_pokemon_data[self.current_pokemon]}")
        print(f"Current Ability: {self.current_ability}")
        print("\nMove Information:")
        for i, (move, name, move_type) in enumerate(zip(
            self.current_moves, 
            self.current_move_names,
            self.current_move_types
        )):
            print(f"Move {i+1}: {move} ({name}) - Type: {move_type}")
        print("===========================\n")
    
    def format_move_name(self, move_name):
        """Format the move name from MOVE_NAME to Name format"""
        if not move_name or not move_name.startswith('MOVE_'):
            return move_name
        return move_name[5:].replace('_', ' ').title()
    
    def load_ability_names(self):
        """Dummy function to simulate loading ability names"""
        return {"ABILITY_STATIC": "Static"}
    
    def save_pokemon_set(self):
        """Save the current Pokemon set"""
        try:
            print("\n===== TESTING SAVE FUNCTION =====")
            # Check if a Pokemon is selected
            if not self.current_pokemon:
                print("No Pokemon selected!")
                QMessageBox.warning(self, "Warning", "Please select a Pokemon first.")
                return

            # Check if at least one move is selected
            if not any(self.current_moves):
                print("No moves selected!")
                QMessageBox.warning(self, "Warning", "Please select at least one move.")
                return

            print("Creating Pokemon set data...")
            # Create the Pokemon set data
            pokemon_set = {
                'species': self.current_pokemon,
                'name': self.all_pokemon_data[self.current_pokemon]['name'],
                'moves': []
            }

            print("Adding ability data...")
            # Add the selected ability if available
            if self.current_ability:
                # Get ability name for display
                ability_names = self.load_ability_names()
                ability_display_name = ability_names.get(
                    self.current_ability,
                    self.current_ability.replace('ABILITY_', '').replace('_', ' ').title()
                )

                pokemon_set['ability'] = {
                    'name': self.current_ability,
                    'display_name': ability_display_name
                }
            
            print("Adding moves to the set...")
            # Add moves to the set, including their source type (level-up, egg, tm, tutor, modern_egg, modern_tm)
            for i, move in enumerate(self.current_moves):
                if move:
                    # Debug output for this specific move
                    print(f"Processing move {i+1}: {move}")
                    print(f"  - Type: {self.current_move_types[i]}")
                    
                    move_type = self.current_move_types[i]
                    move_display_name = self.format_move_name(move)
                    
                    move_info = {
                        'name': move,
                        'display_name': move_display_name,
                        'source': move_type
                    }
                    
                    pokemon_set['moves'].append(move_info)
            
            print("Setting up save directory...")
            # Get the file path to save to
            save_directory = os.path.join(os.getcwd(), 'sets')
            os.makedirs(save_directory, exist_ok=True)
            
            print("Creating filename...")
            # Use the species name and current timestamp for the filename
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{pokemon_set['name']}_{timestamp}.json"
            file_path = os.path.join(save_directory, filename)
            
            print(f"Saving to file: {file_path}")
            print(f"Pokemon set data: {pokemon_set}")
            
            # Save the set to a JSON file
            with open(file_path, 'w') as f:
                json.dump(pokemon_set, f, indent=4)
            
            print(f"Successfully saved Pokemon set to {file_path}")
            QMessageBox.information(self, "Success", f"Pokemon set saved to {filename}")
            
        except Exception as e:
            print("\n===== ERROR OCCURRED =====")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("\nDetailed traceback:")
            traceback.print_exc()
            print("===== END OF ERROR =====\n")
            
            QMessageBox.critical(self, "Error", f"Failed to save Pokemon set: {str(e)}")


def main():
    try:
        print("=== Starting Pokemon Set Builder Save Tester ===")
        
        # Create the application
        app = QApplication(sys.argv)
        
        # Create and show the main window
        window = SaveTester()
        window.show()
        
        # Start the event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        print("\n=== ERROR OCCURRED ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nDetailed traceback:")
        traceback.print_exc()
        print("\n=== END OF ERROR ===")
        
        # Keep the console window open
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
