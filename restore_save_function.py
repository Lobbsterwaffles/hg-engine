"""
This script will fix the save_pokemon_set function in pokemon_set_builder.py
It restores the correct function and updates it to match the format in
existing Pokemon set files.
"""

import os
import re

def fix_save_function():
    # Path to the Pokemon set builder file
    file_path = os.path.join(os.getcwd(), 'pokemon_set_builder.py')
    
    # Read the entire file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define the correct save_pokemon_set function
    correct_function = """    def save_pokemon_set(self):
        \"\"\"Save the current Pokemon set\"\"\"
        # Check if a Pokemon is selected
        if not self.current_pokemon:
            QMessageBox.warning(self, "Warning", "Please select a Pokemon first.")
            return

        # Check if at least one move is selected
        if not any(self.current_moves):
            QMessageBox.warning(self, "Warning", "Please select at least one move.")
            return

        # Create the Pokemon set data
        pokemon_set = {
            'species': self.current_pokemon,
            'name': self.all_pokemon_data[self.current_pokemon]['name'],
            'moves': []
        }

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
        
        # Add moves to the set, including their source type (level-up, egg, tm, tutor, modern_egg, modern_tm)
        for i, move in enumerate(self.current_moves):
            if move:
                move_type = self.current_move_types[i]
                move_display_name = self.format_move_name(move)
                
                # Match the format of existing files with slot number (1-based)
                move_info = {
                    'name': move,
                    'source': move_type,
                    'display_name': move_display_name,
                    'slot': i + 1
                }
                
                pokemon_set['moves'].append(move_info)
        
        # Get the file path to save to
        save_directory = os.path.join(os.getcwd(), 'pokemon_sets')
        os.makedirs(save_directory, exist_ok=True)
        
        # Use the species name and current timestamp for the filename
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{pokemon_set['name']}_{timestamp}.json"
        file_path = os.path.join(save_directory, filename)
        
        # Add generation field like in the existing files
        generation = self.get_pokemon_generation(pokemon_set['species']) if hasattr(self, 'get_pokemon_generation') else 1
        pokemon_set['generation'] = generation
        
        # Save the set to a JSON file
        with open(file_path, 'w') as f:
            json.dump(pokemon_set, f, indent=4)
        
        print(f"Saved Pokemon set to {file_path}")
        QMessageBox.information(self, "Success", f"Pokemon set saved to {filename}")"""
    
    # Find the broken save_pokemon_set function
    pattern = r'def save_pokemon_set\(self\):(?:.*?)def save_to_file'
    replacement = correct_function + "\n\n    def save_to_file"
    
    # Replace using regex with DOTALL flag to match across lines
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the corrected content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Successfully restored and updated the save_pokemon_set function!")

if __name__ == "__main__":
    fix_save_function()
