import sys
import os
import json
import traceback
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QComboBox, QPushButton, QLabel, 
                            QGroupBox, QMessageBox, QTabWidget, QLineEdit, QFileDialog,
                            QCheckBox)
from PyQt5.QtCore import Qt

class PokemonSetBuilder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = "Pokemon Set Builder"
        self.setWindowTitle(self.title)
        self.resize(800, 600)  # Increased size for the new layout
        
        # Initialize data structures
        self.all_pokemon_data = {}
        self.move_lists = {
            'level_up': {},
            'egg': {},
            'tm': {},
            'tutor': {}
        }
        self.pokemon_abilities = {}  # Store each Pokémon's abilities
        self.pokemon_list = []
        self.base_forms = {}  # Maps Pokemon to their base forms
        
        # Track the current selected moves (4 move slots)
        self.current_moves = [None, None, None, None]  # Stores the move data
        self.current_move_names = [None, None, None, None]  # Stores formatted display names
        
        # Track the current selected ability
        self.current_ability = None
        
        # Initialize UI
        self.init_ui()
        
        # Load all data
        self.load_data()
        
        # Populate Pokemon dropdown
        self.populate_pokemon_dropdown()
    
    def init_ui(self):
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        
        # Pokemon Selection UI
        selection_layout = QVBoxLayout()
        selection_widget = QWidget()
        selection_widget.setLayout(selection_layout)
        
        # Pokemon selection options
        options_layout = QHBoxLayout()
        
        # Checkbox for showing only fully evolved Pokémon
        self.show_fully_evolved_only = QCheckBox("Show only fully evolved Pokémon")
        self.show_fully_evolved_only.setChecked(False)  # Unchecked by default
        self.show_fully_evolved_only.stateChanged.connect(self.on_filter_changed)
        options_layout.addWidget(self.show_fully_evolved_only)
        
        options_layout.addStretch(1)
        selection_layout.addLayout(options_layout)
        
        # Pokemon selection dropdown
        pokemon_layout = QHBoxLayout()
        self.pokemon_dropdown = QComboBox()
        self.pokemon_dropdown.setMinimumWidth(200)
        self.pokemon_dropdown.currentIndexChanged.connect(self.on_pokemon_selected)
        
        pokemon_layout.addWidget(QLabel("Select Pokemon:"))
        pokemon_layout.addWidget(self.pokemon_dropdown)
        pokemon_layout.addStretch(1)
        selection_layout.addLayout(pokemon_layout)
        
        # Ability selection dropdown
        ability_layout = QHBoxLayout()
        self.ability_dropdown = QComboBox()
        self.ability_dropdown.setMinimumWidth(200)
        self.ability_dropdown.currentIndexChanged.connect(self.on_ability_selected)
        
        ability_layout.addWidget(QLabel("Select Ability:"))
        ability_layout.addWidget(self.ability_dropdown)
        ability_layout.addStretch(1)
        selection_layout.addLayout(ability_layout)
        
        # Add selection widget to main layout
        main_layout.addWidget(selection_widget)
        
        # Current Moveset Display Section
        moveset_group = QGroupBox("Current Moveset")
        moveset_layout = QVBoxLayout()
        
        # Show a grid of the current 4 moves
        moves_grid_layout = QHBoxLayout()
        
        # Create 4 move display boxes
        self.move_displays = []
        for i in range(4):
            # Create a box to display the currently selected move for this slot
            move_box = QGroupBox(f"Move {i+1}")
            move_layout = QVBoxLayout()
            move_display = QLineEdit("No Move Selected")
            move_display.setReadOnly(True)  # User can't edit directly
            move_layout.addWidget(move_display)
            move_box.setLayout(move_layout)
            
            # Add to our grid and keep a reference
            moves_grid_layout.addWidget(move_box)
            self.move_displays.append(move_display)
        
        moveset_layout.addLayout(moves_grid_layout)
        moveset_group.setLayout(moveset_layout)
        
        # Add the Moveset display to main layout
        main_layout.addWidget(moveset_group)
        
        # Create tab widget for the 4 move slots
        self.move_tabs = QTabWidget()
        
        # Lists to store all our move dropdowns
        self.level_up_dropdowns = []
        self.egg_dropdowns = []
        self.tm_dropdowns = []
        self.tutor_dropdowns = []
        
        # Create 4 tabs, one for each move slot
        for i in range(4):
            # Create a tab for this move slot
            tab = QWidget()
            tab_layout = QVBoxLayout()
            
            # Create move selection dropdowns for this tab
            move_label = QLabel(f"Select Move {i+1}:")
            tab_layout.addWidget(move_label)
            
            # Level-up moves dropdown
            level_up_group = QGroupBox("Level-up Moves")
            level_up_layout = QVBoxLayout()
            level_up_dropdown = QComboBox()
            level_up_layout.addWidget(level_up_dropdown)
            level_up_group.setLayout(level_up_layout)
            
            # Egg moves dropdown
            egg_group = QGroupBox("Egg Moves")
            egg_layout = QVBoxLayout()
            egg_dropdown = QComboBox()
            egg_layout.addWidget(egg_dropdown)
            egg_group.setLayout(egg_layout)
            
            # TM moves dropdown
            tm_group = QGroupBox("TM Moves")
            tm_layout = QVBoxLayout()
            tm_dropdown = QComboBox()
            tm_layout.addWidget(tm_dropdown)
            tm_group.setLayout(tm_layout)
            
            # Tutor moves dropdown
            tutor_group = QGroupBox("Tutor Moves")
            tutor_layout = QVBoxLayout()
            tutor_dropdown = QComboBox()
            tutor_layout.addWidget(tutor_dropdown)
            tutor_group.setLayout(tutor_layout)
            
            # Store references to our dropdowns
            self.level_up_dropdowns.append(level_up_dropdown)
            self.egg_dropdowns.append(egg_dropdown)
            self.tm_dropdowns.append(tm_dropdown)
            self.tutor_dropdowns.append(tutor_dropdown)
            
            # Connect signals to update the moveset when selections change
            # The lambda function captures the current move slot index
            level_up_dropdown.currentIndexChanged.connect(
                lambda idx, slot=i, dropdown='level_up': self.on_move_selected(idx, slot, dropdown))
            egg_dropdown.currentIndexChanged.connect(
                lambda idx, slot=i, dropdown='egg': self.on_move_selected(idx, slot, dropdown))
            tm_dropdown.currentIndexChanged.connect(
                lambda idx, slot=i, dropdown='tm': self.on_move_selected(idx, slot, dropdown))
            tutor_dropdown.currentIndexChanged.connect(
                lambda idx, slot=i, dropdown='tutor': self.on_move_selected(idx, slot, dropdown))
            
            # Add move selection groups to this tab
            tab_layout.addWidget(level_up_group)
            tab_layout.addWidget(egg_group)
            tab_layout.addWidget(tm_group)
            tab_layout.addWidget(tutor_group)
            
            # Set the layout for this tab
            tab.setLayout(tab_layout)
            
            # Add the tab to our tab widget
            self.move_tabs.addTab(tab, f"Move {i+1}")
        
        # Add the tabs to our main layout
        main_layout.addWidget(self.move_tabs)
        
        # Save button
        self.save_button = QPushButton("Save Pokemon Set")
        self.save_button.clicked.connect(self.save_pokemon_set)
        
        # Add button to main layout
        main_layout.addWidget(self.save_button)
    
    def load_data(self):
        """Load Pokemon and move data from the game files"""
        try:
            # Get the base directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            print(f"Base directory: {base_dir}")
            
            # Parse species.inc to get Pokemon names and evolution data
            species_file = os.path.join(base_dir, 'asm', 'include', 'species.inc')
            print(f"Species file path: {species_file}")
            if not os.path.exists(species_file):
                print(f"WARNING: Species file does not exist at {species_file}")
            self.parse_species_file(species_file)
            
            # Parse mondata.s for abilities (this will get accurate abilities for all Pokémon)
            mondata_file = os.path.join(base_dir, 'armips', 'data', 'mondata.s')
            print(f"Mondata file path: {mondata_file}")
            if not os.path.exists(mondata_file):
                print(f"WARNING: Mondata file does not exist at {mondata_file}")
                # Fall back to hardcoded abilities if file not found
                self.setup_pokemon_abilities()
            else:
                self.parse_abilities_file(mondata_file)
                
                # If we didn't get many abilities from parsing, use our fallback method
                if len(self.pokemon_abilities) < 10:  # Just a threshold check
                    print("Not enough abilities found from parsing, using fallback abilities")
                    self.setup_pokemon_abilities()
            
            # Parse levelupdata.s for level-up moves
            levelup_file = os.path.join(base_dir, 'armips', 'data', 'levelupdata.s')
            print(f"Level-up file path: {levelup_file}")
            if not os.path.exists(levelup_file):
                print(f"WARNING: Level-up file does not exist at {levelup_file}")
            else:
                self.parse_levelup_file(levelup_file)
            
            # Parse eggmoves.s for egg moves
            egg_file = os.path.join(base_dir, 'armips', 'data', 'eggmoves.s')
            print(f"Egg moves file path: {egg_file}")
            if not os.path.exists(egg_file):
                print(f"WARNING: Egg moves file does not exist at {egg_file}")
            else:
                self.parse_egg_file(egg_file)
            
            # Parse tmlearnset.txt for TM moves
            tm_file = os.path.join(base_dir, 'armips', 'data', 'tmlearnset.txt')
            print(f"TM file path: {tm_file}")
            if not os.path.exists(tm_file):
                print(f"WARNING: TM file does not exist at {tm_file}")
            else:
                self.parse_tm_file(tm_file)
            
            # Parse tutordata.txt for tutor moves
            tutor_file = os.path.join(base_dir, 'armips', 'data', 'tutordata.txt')
            print(f"Tutor file path: {tutor_file}")
            if not os.path.exists(tutor_file):
                print(f"WARNING: Tutor file does not exist at {tutor_file}")
            else:
                self.parse_tutor_file(tutor_file)
                
            # Parse evodata.s for evolution data
            evo_file = os.path.join(base_dir, 'armips', 'data', 'evodata.s')
            print(f"Evolution file path: {evo_file}")
            if not os.path.exists(evo_file):
                print(f"WARNING: Evolution file does not exist at {evo_file}")
                # Initialize an empty evolution data dictionary
                self.evolution_data = {}
            else:
                self.parse_evolution_file(evo_file)
                
            # Parse mondata.s for abilities (this will get accurate abilities for all Pokémon)
            mondata_file = os.path.join(base_dir, 'armips', 'data', 'mondata.s')
            print(f"Mondata file path: {mondata_file}")
            if not os.path.exists(mondata_file):
                print(f"WARNING: Mondata file does not exist at {mondata_file}")
                # Fall back to hardcoded abilities if file not found
                self.setup_pokemon_abilities()
            else:
                # Use our enhanced parser to get accurate abilities directly from the source file
                self.parse_abilities_file(mondata_file)
            
            # Determine fully evolved, non-legendary Pokemon
            self.determine_fully_evolved_non_legendary()
            
            # Print some sample Pokemon from our list for verification
            print("\nSample of fully evolved Pokemon in dropdown:")
            for i, species in enumerate(self.pokemon_list[:10]):
                print(f"{i+1}. {species} ({self.all_pokemon_data[species]['name']})")
                
            # Print some sample base forms for verification
            print("\nSample of base forms:")
            for i, species in enumerate(list(self.base_forms.keys())[:5]):
                base = self.base_forms[species]
                print(f"{species} -> {base} ({self.all_pokemon_data[species]['name']} -> {self.all_pokemon_data[base]['name'] if base in self.all_pokemon_data else 'Unknown'})")
            
        except Exception as e:
            error_msg = f"Failed to load data: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)
    
    def parse_species_file(self, file_path):
        """Parse the species.inc file to get Pokemon IDs and names"""
        try:
            species_data = {}
            current_id = 0
            
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('.equ SPECIES_'):
                        parts = line.split(',')
                        if len(parts) == 2:
                            species_name = parts[0].replace('.equ ', '').strip()
                            id_value = parts[1].strip()
                            
                            # Skip if the ID is a complex expression
                            if id_value.startswith('(') or '+' in id_value or '-' in id_value or '*' in id_value or '/' in id_value:
                                print(f"Skipping complex ID expression for {species_name}: {id_value}")
                                continue
                                
                            try:
                                species_id = int(id_value)
                            except ValueError:
                                # If we can't parse it as an integer, skip this entry
                                print(f"Skipping unparseable ID for {species_name}: {id_value}")
                                continue
                            
                            # Skip special forms and non-standard Pokemon
                            if (not species_name.startswith('SPECIES_EGG') and 
                                not species_name == 'SPECIES_NONE' and 
                                not species_name == 'SPECIES_BAD_EGG' and
                                not '_FORM' in species_name and
                                not '_REGIONAL' in species_name and
                                not '_START' in species_name):
                                species_data[species_name] = {
                                    'id': species_id,
                                    'name': self.format_pokemon_name(species_name),
                                    'is_legendary': self.is_legendary(species_name),
                                    'pre_evolution': None,
                                    'evolves_to': []
                                }
            
            # Identify evolution chains (simplified approach)
            for species_name, data in species_data.items():
                # Try to identify pre-evolutions and evolutions based on name patterns
                for other_name, other_data in species_data.items():
                    # Skip comparing with itself
                    if species_name == other_name:
                        continue
                    
                    # Check for evolution relationships based on names
                    if self.is_evolution_of(species_name, other_name):
                        species_data[other_name]['evolves_to'].append(species_name)
                        species_data[species_name]['pre_evolution'] = other_name
            
            self.all_pokemon_data = species_data
            print(f"Successfully parsed {len(species_data)} Pokemon from species file.")
            
        except Exception as e:
            error_msg = f"Error parsing species file: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            raise Exception(error_msg)
    
    def parse_levelup_file(self, file_path):
        """Parse the levelupdata.s file to get level-up moves for each Pokemon"""
        try:
            current_pokemon = None
            moves = []
            lines_processed = 0
            pokemon_count = 0
            move_count = 0
            
            print(f"Starting to parse level-up file: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.readlines()
                print(f"Total lines in level-up file: {len(file_content)}")
                
                for line in file_content:
                    lines_processed += 1
                    line = line.strip()
                    
                    # Print sample lines to understand format (first 10 lines)
                    if lines_processed <= 20:
                        print(f"Line {lines_processed}: {line}")
                    
                    if 'levelup SPECIES_' in line:
                        # Save the previous Pokemon's moves if any
                        if current_pokemon and moves:
                            self.move_lists['level_up'][current_pokemon] = list(set(moves))
                            pokemon_count += 1
                        
                        # Start a new Pokemon
                        current_pokemon = line.replace('levelup ', '').strip()
                        moves = []
                        if lines_processed <= 30 or pokemon_count < 5:
                            print(f"Found Pokemon: {current_pokemon}")
                    
                    elif 'learnset MOVE_' in line:
                        # Add move to the current Pokemon's move list
                        move_line = line.strip()
                        if move_line.startswith('learnset '):
                            move_parts = move_line.replace('learnset ', '').split(',')
                        else:
                            move_parts = move_line.replace('    learnset ', '').split(',')
                        
                        if len(move_parts) >= 1:
                            move_name = move_parts[0].strip()
                            moves.append(move_name)
                            move_count += 1
                            
                            # Print some sample moves
                            if move_count <= 10:
                                print(f"  Move: {move_name}")
                    
                    elif 'terminatelearnset' in line and current_pokemon and moves:
                        # Save the current Pokemon's moves
                        self.move_lists['level_up'][current_pokemon] = list(set(moves))
                        moves = []
                        pokemon_count += 1
            
            # Handle the last Pokemon in the file if needed
            if current_pokemon and moves:
                self.move_lists['level_up'][current_pokemon] = list(set(moves))
                pokemon_count += 1
                
            print(f"Processed {lines_processed} lines")
            print(f"Found {pokemon_count} Pokemon with level-up moves")
            print(f"Found {move_count} total moves")
            print(f"Loaded level-up moves for {len(self.move_lists['level_up'])} Pokemon.")
        
        except Exception as e:
            error_msg = f"Error parsing level-up file: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            raise Exception(error_msg)
    
    def parse_egg_file(self, file_path):
        """Parse the eggmoves.s file to get egg moves for each Pokemon"""
        try:
            current_pokemon = None
            moves = []
            lines_processed = 0
            pokemon_count = 0
            move_count = 0
            
            print(f"Starting to parse egg moves file: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.readlines()
                print(f"Total lines in egg moves file: {len(file_content)}")
                
                for line in file_content:
                    lines_processed += 1
                    line = line.strip()
                    
                    # Print sample lines to understand format (first 10 lines)
                    if lines_processed <= 20:
                        print(f"Line {lines_processed}: {line}")
                    
                    if 'eggmoveentry SPECIES_' in line:
                        # Save the previous Pokemon's moves if any
                        if current_pokemon and moves:
                            self.move_lists['egg'][current_pokemon] = list(set(moves))
            
            with open(file_path, 'r') as f:
                content = f.readlines()
            
            print(f"Total lines in egg moves file: {len(content)}")
            
            current_pokemon = None
            line_count = 0
            pokemon_count = 0
            move_count = 0
            
            for i, line in enumerate(content):
                line_count += 1
                line = line.strip()
                
                # Debug output for the first 20 lines
                if i < 20:
                    print(f"Line {i+1}: {line}")
                
                if 'eggmoveentry SPECIES_' in line:
                    current_pokemon = line.replace('eggmoveentry ', '').strip()
                    print(f"Found Pokemon: {current_pokemon}")
                    self.move_lists['egg'][current_pokemon] = []
                    pokemon_count += 1
                elif current_pokemon and 'eggmove MOVE_' in line:
                    move = line.replace('eggmove ', '').strip()
                    if i < 20:
                        print(f"  Move: {move}")
                    self.move_lists['egg'][current_pokemon].append(move)
                    move_count += 1
            
            print(f"Processed {line_count} lines")
            print(f"Found {pokemon_count} Pokemon with egg moves")
            print(f"Found {move_count} total moves")
            print(f"Loaded egg moves for {len(self.move_lists['egg'])} Pokemon.")
            
        except Exception as e:
            error_msg = f"Failed to parse egg moves file: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            raise Exception(error_msg)
    
    def parse_tm_file(self, file_path):
        """Parse the tmlearnset.txt file to get TM moves for each Pokemon"""
        try:
            if not os.path.exists(file_path):
                print(f"WARNING: TM file not found at {file_path}")
                return
            
            print(f"Starting to parse TM/HM file: {file_path}")
            
            with open(file_path, 'r') as f:
                content = f.readlines()
            
            print(f"Total lines in TM/HM file: {len(content)}")
            
            current_tm = None
            current_tm_move = None
            line_count = 0
            pokemon_count = 0
            move_count = 0
            
            for i, line in enumerate(content):
                line_count += 1
                line = line.strip()
                
                # Debug output for the first 20 lines
                if i < 20:
                    print(f"Line {i+1}: {line}")
                
                # New TM/HM move
                if line.startswith('TM') or line.startswith('HM'):
                    current_tm = line.split(':')[0].strip()
                    current_tm_move = line.split(':')[1].strip()
                    print(f"Found TM/HM: {current_tm} = {current_tm_move}")
                
                # Pokemon that can learn the move
                elif line.startswith('SPECIES_') and current_tm and current_tm_move:
                    species_name = line.strip()
                    
                    # Initialize the Pokemon's TM move list if needed
                    if species_name not in self.move_lists['tm']:
                        self.move_lists['tm'][species_name] = []
                        pokemon_count += 1
                    
                    # Add the move
                    self.move_lists['tm'][species_name].append(current_tm_move)
                    move_count += 1
            
            print(f"Processed {line_count} lines")
            print(f"Found {pokemon_count} Pokemon with TM/HM moves")
            print(f"Found {move_count} total move-Pokemon combinations")
            print(f"Loaded TM/HM moves for {len(self.move_lists['tm'])} Pokemon.")
            
        except Exception as e:
            error_msg = f"Failed to parse TM file: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
    
    def parse_evolution_file(self, file_path):
        """Parse the evodata.s file to get evolution data for each Pokemon"""
        try:
            if not os.path.exists(file_path):
                print(f"WARNING: Evolution file not found at {file_path}")
                return
            
            print(f"Starting to parse evolution file: {file_path}")
            
            with open(file_path, 'r') as f:
                content = f.readlines()
            
            print(f"Total lines in evolution file: {len(content)}")
            
            current_pokemon = None
            evolution_chain = {}
            pre_evolutions = {}
            line_count = 0
            
            for i, line in enumerate(content):
                line_count += 1
                line = line.strip()
                
                # Debug output for the first 20 lines
                if i < 20:
                    print(f"Line {i+1}: {line}")
                
                if line.startswith('evodata SPECIES_'):
                    current_pokemon = line.replace('evodata ', '').strip()
                    evolution_chain[current_pokemon] = []
                    
                elif current_pokemon and line.startswith('evolution EVO_'):
                    parts = line.split(',')
                    if len(parts) >= 3 and 'SPECIES_NONE' not in parts[2]:
                        target_species = parts[2].strip()
                        evolution_chain[current_pokemon].append(target_species)
                        
                        # Record the pre-evolution relationship
                        pre_evolutions[target_species] = current_pokemon
            
            print(f"Processed {line_count} lines")
            print(f"Found evolution data for {len(evolution_chain)} Pokemon")
            
            # Build base forms by working backwards from each Pokemon
            for species in self.all_pokemon_data.keys():
                base_form = species
                current = species
                
                # Keep going back until we find a Pokemon with no pre-evolution
                while current in pre_evolutions:
                    base_form = pre_evolutions[current]
                    current = base_form
                
                self.base_forms[species] = base_form
            
            print(f"Determined base forms for {len(self.base_forms)} Pokemon")
            
        except Exception as e:
            error_msg = f"Failed to parse evolution file: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()

    def parse_tm_file(self, file_path):
        """Parse the tmlearnset.txt file to get TM moves for each Pokemon"""
        try:
            current_tm = None
            current_move = None
            lines_processed = 0
            pokemon_count = 0
            move_count = 0
            
            print(f"Starting to parse TM/HM file: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.readlines()
                print(f"Total lines in TM/HM file: {len(file_content)}")
                
                for line in file_content:
                    lines_processed += 1
                    line = line.strip()
                    
                    # Print sample lines to understand format (first 10 lines)
                    if lines_processed <= 20:
                        print(f"Line {lines_processed}: {line}")
                    
                    if (line.startswith('TM') or line.startswith('HM')) and ':' in line:
                        # New TM/HM definition
                        parts = line.split(':')
                        if len(parts) == 2:
                            current_tm = parts[0].strip()
                            current_move = parts[1].strip()
                            if lines_processed <= 30:
                                print(f"Found TM/HM: {current_tm} = {current_move}")
                    
                    elif 'SPECIES_' in line and current_tm and current_move:
                        # Pokemon that can learn this TM/HM
                        pokemon = line.strip()
                        
                        # Initialize moves list for this Pokemon if needed
                        if pokemon not in self.move_lists['tm']:
                            self.move_lists['tm'][pokemon] = []
                            pokemon_count += 1
                        
                        # Add move to Pokemon's TM move list
                        self.move_lists['tm'][pokemon].append(current_move)
                        move_count += 1
            
            # Deduplicate moves for each Pokemon
            for pokemon in self.move_lists['tm']:
                self.move_lists['tm'][pokemon] = list(set(self.move_lists['tm'][pokemon]))
                
            print(f"Processed {lines_processed} lines")
            print(f"Found {pokemon_count} Pokemon with TM/HM moves")
            print(f"Found {move_count} total move-Pokemon combinations")
            print(f"Loaded TM/HM moves for {len(self.move_lists['tm'])} Pokemon.")
        
        except Exception as e:
            error_msg = f"Error parsing TM file: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            raise Exception(error_msg)
    
    def parse_tutor_file(self, file_path):
        """Parse the tutordata.txt file to get tutor moves for each Pokemon"""
        try:
            current_tutor = None
            current_move = None
            lines_processed = 0
            pokemon_count = 0
            move_count = 0
            
            print(f"Starting to parse tutor moves file: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.readlines()
                print(f"Total lines in tutor moves file: {len(file_content)}")
                
                for line in file_content:
                    lines_processed += 1
                    line = line.strip()
                    
                    # Print sample lines to understand format (first 10 lines)
                    if lines_processed <= 20:
                        print(f"Line {lines_processed}: {line}")
                    
                    if 'TUTOR_' in line and ':' in line:
                        # New tutor move definition
                        parts = line.split(':')
                        if len(parts) == 2:
                            current_tutor = parts[0].strip()
                            move_parts = parts[1].strip().split()
                            if len(move_parts) >= 1:
                                current_move = move_parts[0].strip()
                                if lines_processed <= 30:
                                    print(f"Found tutor move: {current_tutor} = {current_move}")
                    
                    elif 'SPECIES_' in line and current_tutor and current_move:
                        # Pokemon that can learn this tutor move
                        pokemon = line.strip()
                        
                        # Initialize moves list for this Pokemon if needed
                        if pokemon not in self.move_lists['tutor']:
                            self.move_lists['tutor'][pokemon] = []
                            pokemon_count += 1
                        
                        # Add move to Pokemon's tutor move list
                        self.move_lists['tutor'][pokemon].append(current_move)
                        move_count += 1
            
            # Deduplicate moves for each Pokemon
            for pokemon in self.move_lists['tutor']:
                self.move_lists['tutor'][pokemon] = list(set(self.move_lists['tutor'][pokemon]))
                
            print(f"Processed {lines_processed} lines")
            print(f"Found {pokemon_count} Pokemon with tutor moves")
            print(f"Found {move_count} total move-Pokemon combinations")
            print(f"Loaded tutor moves for {len(self.move_lists['tutor'])} Pokemon.")
        
        except Exception as e:
            error_msg = f"Error parsing tutor file: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            raise Exception(error_msg)
    
    def setup_pokemon_abilities(self):
        """Set up Pokémon abilities using a hardcoded dictionary for reliability"""
        try:
            print("Setting up Pokémon abilities with hardcoded values")
            
            # Initialize dictionary to store Pokémon abilities
            self.pokemon_abilities = {}
            
            # Load ability names from abilities.inc file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            abilities_file = os.path.join(base_dir, 'asm', 'include', 'abilities.inc')
            print(f"Abilities file path: {abilities_file}")
            
            # Create a list of all ability names (we'll need this for the dropdown)
            self.ability_names = []
            if os.path.exists(abilities_file):
                try:
                    with open(abilities_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('.set ABILITY_'):
                                ability_name = line.split('.set ')[1].split(',')[0]
                                self.ability_names.append(ability_name)
                    print(f"Loaded {len(self.ability_names)} ability names from abilities.inc")
                except Exception as e:
                    print(f"Error reading abilities.inc: {str(e)}")
                    self.ability_names = [f"ABILITY_{i}" for i in range(1, 100)]
            else:
                print("WARNING: abilities.inc file not found, using generic ability names")
                self.ability_names = [f"ABILITY_{i}" for i in range(1, 100)]
            
            # Create a comprehensive dictionary of common Pokémon abilities
            # This will cover the most used Pokémon
            common_abilities = {
                # Kanto starters
                'SPECIES_BULBASAUR': ['ABILITY_OVERGROW', 'ABILITY_CHLOROPHYLL'],
                'SPECIES_IVYSAUR': ['ABILITY_OVERGROW', 'ABILITY_CHLOROPHYLL'],
                'SPECIES_VENUSAUR': ['ABILITY_OVERGROW', 'ABILITY_CHLOROPHYLL'],
                'SPECIES_CHARMANDER': ['ABILITY_BLAZE', 'ABILITY_SOLAR_POWER'],
                'SPECIES_CHARMELEON': ['ABILITY_BLAZE', 'ABILITY_SOLAR_POWER'],
                'SPECIES_CHARIZARD': ['ABILITY_BLAZE', 'ABILITY_SOLAR_POWER'],
                'SPECIES_SQUIRTLE': ['ABILITY_TORRENT', 'ABILITY_RAIN_DISH'],
                'SPECIES_WARTORTLE': ['ABILITY_TORRENT', 'ABILITY_RAIN_DISH'],
                'SPECIES_BLASTOISE': ['ABILITY_TORRENT', 'ABILITY_RAIN_DISH'],
                
                # Other popular Kanto Pokémon
                'SPECIES_PIKACHU': ['ABILITY_STATIC', 'ABILITY_LIGHTNING_ROD'],
                'SPECIES_RAICHU': ['ABILITY_STATIC', 'ABILITY_LIGHTNING_ROD'],
                'SPECIES_NIDOKING': ['ABILITY_POISON_POINT', 'ABILITY_RIVALRY', 'ABILITY_SHEER_FORCE'],
                'SPECIES_NIDOQUEEN': ['ABILITY_POISON_POINT', 'ABILITY_RIVALRY', 'ABILITY_SHEER_FORCE'],
                'SPECIES_ARCANINE': ['ABILITY_INTIMIDATE', 'ABILITY_FLASH_FIRE', 'ABILITY_JUSTIFIED'],
                'SPECIES_ALAKAZAM': ['ABILITY_SYNCHRONIZE', 'ABILITY_INNER_FOCUS', 'ABILITY_MAGIC_GUARD'],
                'SPECIES_MACHAMP': ['ABILITY_GUTS', 'ABILITY_NO_GUARD', 'ABILITY_STEADFAST'],
                'SPECIES_GENGAR': ['ABILITY_CURSED_BODY', 'ABILITY_LEVITATE'],
                'SPECIES_GYARADOS': ['ABILITY_INTIMIDATE', 'ABILITY_MOXIE'],
                'SPECIES_DRAGONITE': ['ABILITY_INNER_FOCUS', 'ABILITY_MULTISCALE'],
                'SPECIES_SNORLAX': ['ABILITY_IMMUNITY', 'ABILITY_THICK_FAT', 'ABILITY_GLUTTONY'],
                
                # Johto starters
                'SPECIES_CHIKORITA': ['ABILITY_OVERGROW', 'ABILITY_LEAF_GUARD'],
                'SPECIES_BAYLEEF': ['ABILITY_OVERGROW', 'ABILITY_LEAF_GUARD'],
                'SPECIES_MEGANIUM': ['ABILITY_OVERGROW', 'ABILITY_LEAF_GUARD'],
                'SPECIES_CYNDAQUIL': ['ABILITY_BLAZE', 'ABILITY_FLASH_FIRE'],
                'SPECIES_QUILAVA': ['ABILITY_BLAZE', 'ABILITY_FLASH_FIRE'],
                'SPECIES_TYPHLOSION': ['ABILITY_BLAZE', 'ABILITY_FLASH_FIRE'],
                'SPECIES_TOTODILE': ['ABILITY_TORRENT', 'ABILITY_SHEER_FORCE'],
                'SPECIES_CROCONAW': ['ABILITY_TORRENT', 'ABILITY_SHEER_FORCE'],
                'SPECIES_FERALIGATR': ['ABILITY_TORRENT', 'ABILITY_SHEER_FORCE'],
                
                # Other popular Johto Pokémon
                'SPECIES_AMPHAROS': ['ABILITY_STATIC', 'ABILITY_PLUS'],
                'SPECIES_SCIZOR': ['ABILITY_SWARM', 'ABILITY_TECHNICIAN', 'ABILITY_LIGHT_METAL'],
                'SPECIES_HERACROSS': ['ABILITY_SWARM', 'ABILITY_GUTS', 'ABILITY_MOXIE'],
                'SPECIES_TYRANITAR': ['ABILITY_SAND_STREAM', 'ABILITY_UNNERVE'],
                
                # Hoenn starters
                'SPECIES_TREECKO': ['ABILITY_OVERGROW', 'ABILITY_UNBURDEN'],
                'SPECIES_GROVYLE': ['ABILITY_OVERGROW', 'ABILITY_UNBURDEN'],
                'SPECIES_SCEPTILE': ['ABILITY_OVERGROW', 'ABILITY_UNBURDEN'],
                'SPECIES_TORCHIC': ['ABILITY_BLAZE', 'ABILITY_SPEED_BOOST'],
                'SPECIES_COMBUSKEN': ['ABILITY_BLAZE', 'ABILITY_SPEED_BOOST'],
                'SPECIES_BLAZIKEN': ['ABILITY_BLAZE', 'ABILITY_SPEED_BOOST'],
                'SPECIES_MUDKIP': ['ABILITY_TORRENT', 'ABILITY_DAMP'],
                'SPECIES_MARSHTOMP': ['ABILITY_TORRENT', 'ABILITY_DAMP'],
                'SPECIES_SWAMPERT': ['ABILITY_TORRENT', 'ABILITY_DAMP'],
                
                # Other popular Hoenn Pokémon
                'SPECIES_GARDEVOIR': ['ABILITY_SYNCHRONIZE', 'ABILITY_TRACE', 'ABILITY_TELEPATHY'],
                'SPECIES_BRELOOM': ['ABILITY_EFFECT_SPORE', 'ABILITY_POISON_HEAL', 'ABILITY_TECHNICIAN'],
                'SPECIES_AGGRON': ['ABILITY_STURDY', 'ABILITY_ROCK_HEAD', 'ABILITY_HEAVY_METAL'],
                'SPECIES_METAGROSS': ['ABILITY_CLEAR_BODY', 'ABILITY_LIGHT_METAL'],
                'SPECIES_SALAMENCE': ['ABILITY_INTIMIDATE', 'ABILITY_MOXIE'],
                
                # Sinnoh starters
                'SPECIES_TURTWIG': ['ABILITY_OVERGROW', 'ABILITY_SHELL_ARMOR'],
                'SPECIES_GROTLE': ['ABILITY_OVERGROW', 'ABILITY_SHELL_ARMOR'],
                'SPECIES_TORTERRA': ['ABILITY_OVERGROW', 'ABILITY_SHELL_ARMOR'],
                'SPECIES_CHIMCHAR': ['ABILITY_BLAZE', 'ABILITY_IRON_FIST'],
                'SPECIES_MONFERNO': ['ABILITY_BLAZE', 'ABILITY_IRON_FIST'],
                'SPECIES_INFERNAPE': ['ABILITY_BLAZE', 'ABILITY_IRON_FIST'],
                'SPECIES_PIPLUP': ['ABILITY_TORRENT', 'ABILITY_DEFIANT'],
                'SPECIES_PRINPLUP': ['ABILITY_TORRENT', 'ABILITY_DEFIANT'],
                'SPECIES_EMPOLEON': ['ABILITY_TORRENT', 'ABILITY_DEFIANT'],
                
                # Other popular Pokémon
                'SPECIES_LUCARIO': ['ABILITY_STEADFAST', 'ABILITY_INNER_FOCUS', 'ABILITY_JUSTIFIED'],
                'SPECIES_GARCHOMP': ['ABILITY_SAND_VEIL', 'ABILITY_ROUGH_SKIN'],
                
                # Eeveelutions
                'SPECIES_EEVEE': ['ABILITY_RUN_AWAY', 'ABILITY_ADAPTABILITY', 'ABILITY_ANTICIPATION'],
                'SPECIES_VAPOREON': ['ABILITY_WATER_ABSORB', 'ABILITY_HYDRATION'],
                'SPECIES_JOLTEON': ['ABILITY_VOLT_ABSORB', 'ABILITY_QUICK_FEET'],
                'SPECIES_FLAREON': ['ABILITY_FLASH_FIRE', 'ABILITY_GUTS'],
                'SPECIES_ESPEON': ['ABILITY_SYNCHRONIZE', 'ABILITY_MAGIC_BOUNCE'],
                'SPECIES_UMBREON': ['ABILITY_SYNCHRONIZE', 'ABILITY_INNER_FOCUS'],
                'SPECIES_LEAFEON': ['ABILITY_LEAF_GUARD', 'ABILITY_CHLOROPHYLL'],
                'SPECIES_GLACEON': ['ABILITY_SNOW_CLOAK', 'ABILITY_ICE_BODY'],
                'SPECIES_SYLVEON': ['ABILITY_CUTE_CHARM', 'ABILITY_PIXILATE']
            }
            
            # Assign the common abilities to our abilities dictionary
            self.pokemon_abilities = common_abilities
            
            # For any Pokémon not in our hardcoded list, give them some default abilities
            for species in self.all_pokemon_data.keys():
                if species not in self.pokemon_abilities:
                    # Give each Pokémon not in our list some reasonable default abilities
                    # This ensures every Pokémon has at least one ability in the dropdown
                    if 'type1' in self.all_pokemon_data[species]:
                        type1 = self.all_pokemon_data[species]['type1']
                        # Assign abilities based on Pokémon type
                        if type1 == 'NORMAL':
                            self.pokemon_abilities[species] = ['ABILITY_RUN_AWAY', 'ABILITY_LIMBER']
                        elif type1 == 'FIRE':
                            self.pokemon_abilities[species] = ['ABILITY_BLAZE', 'ABILITY_FLASH_FIRE']
                        elif type1 == 'WATER':
                            self.pokemon_abilities[species] = ['ABILITY_TORRENT', 'ABILITY_WATER_ABSORB']
                        elif type1 == 'GRASS':
                            self.pokemon_abilities[species] = ['ABILITY_OVERGROW', 'ABILITY_CHLOROPHYLL']
                        elif type1 == 'ELECTRIC':
                            self.pokemon_abilities[species] = ['ABILITY_STATIC', 'ABILITY_LIGHTNING_ROD']
                        elif type1 == 'ICE':
                            self.pokemon_abilities[species] = ['ABILITY_ICE_BODY', 'ABILITY_SNOW_CLOAK']
                        elif type1 == 'FIGHTING':
                            self.pokemon_abilities[species] = ['ABILITY_GUTS', 'ABILITY_INNER_FOCUS']
                        elif type1 == 'POISON':
                            self.pokemon_abilities[species] = ['ABILITY_POISON_POINT', 'ABILITY_LIQUID_OOZE']
                        elif type1 == 'GROUND':
                            self.pokemon_abilities[species] = ['ABILITY_SAND_VEIL', 'ABILITY_ARENA_TRAP']
                        elif type1 == 'FLYING':
                            self.pokemon_abilities[species] = ['ABILITY_KEEN_EYE', 'ABILITY_BIG_PECKS']
                        elif type1 == 'PSYCHIC':
                            self.pokemon_abilities[species] = ['ABILITY_SYNCHRONIZE', 'ABILITY_MAGIC_GUARD']
                        elif type1 == 'BUG':
                            self.pokemon_abilities[species] = ['ABILITY_SWARM', 'ABILITY_COMPOUND_EYES']
                        elif type1 == 'ROCK':
                            self.pokemon_abilities[species] = ['ABILITY_ROCK_HEAD', 'ABILITY_STURDY']
                        elif type1 == 'GHOST':
                            self.pokemon_abilities[species] = ['ABILITY_LEVITATE', 'ABILITY_CURSED_BODY']
                        elif type1 == 'DRAGON':
                            self.pokemon_abilities[species] = ['ABILITY_INTIMIDATE', 'ABILITY_MULTISCALE']
                        elif type1 == 'DARK':
                            self.pokemon_abilities[species] = ['ABILITY_INTIMIDATE', 'ABILITY_MOXIE']
                        elif type1 == 'STEEL':
                            self.pokemon_abilities[species] = ['ABILITY_CLEAR_BODY', 'ABILITY_STURDY']
                        elif type1 == 'FAIRY':
                            self.pokemon_abilities[species] = ['ABILITY_CUTE_CHARM', 'ABILITY_MAGIC_GUARD']
                        else:
                            # Generic fallback
                            self.pokemon_abilities[species] = ['ABILITY_LIMBER', 'ABILITY_KEEN_EYE']
                    else:
                        # If we don't have type data, just give generic abilities
                        self.pokemon_abilities[species] = ['ABILITY_LIMBER', 'ABILITY_KEEN_EYE']
            
            # Print summary
            print(f"Set up abilities for {len(self.pokemon_abilities)} Pokémon")
            
            # Print some sample abilities for verification
            print("\nSample of Pokémon abilities:")
            sample_count = 0
            for species in self.pokemon_abilities:
                if sample_count < 10:
                    abilities = self.pokemon_abilities.get(species, [])
                    ability_names = [ability.replace('ABILITY_', '').replace('_', ' ').title() for ability in abilities]
                    print(f"{species}: {', '.join(ability_names) if ability_names else 'No abilities found'}")
                    sample_count += 1
        
        except Exception as e:
            error_msg = f"Failed to set up abilities: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            
            # Create a minimal fallback for critical Pokémon
            print("Using minimal fallback abilities for basic functionality")
            self.pokemon_abilities = {
                'SPECIES_VENUSAUR': ['ABILITY_OVERGROW'],
                'SPECIES_CHARIZARD': ['ABILITY_BLAZE'],
                'SPECIES_BLASTOISE': ['ABILITY_TORRENT'],
                'SPECIES_PIKACHU': ['ABILITY_STATIC'],
                'SPECIES_GENGAR': ['ABILITY_LEVITATE'],
                'SPECIES_GYARADOS': ['ABILITY_INTIMIDATE'],
                'SPECIES_EEVEE': ['ABILITY_ADAPTABILITY'],
                'SPECIES_SNORLAX': ['ABILITY_IMMUNITY', 'ABILITY_THICK_FAT'],
                'SPECIES_TYPHLOSION': ['ABILITY_BLAZE'],
                'SPECIES_FERALIGATR': ['ABILITY_TORRENT'],
                'SPECIES_MEGANIUM': ['ABILITY_OVERGROW']
            }
            
    def parse_abilities_file(self, file_path):
        """Parse mondata.s file to get regular abilities for each Pokemon"""
        try:
            print(f"Starting to parse abilities from mondata.s: {file_path}")
            
            # Initialize dictionary to store Pokémon abilities
            self.pokemon_abilities = {}
            
            # Variables to track current Pokémon being processed
            current_pokemon = None
            pokemon_count = 0
            abilities_line_count = 0
            
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"ERROR: Abilities file not found at {file_path}")
                return
            
            # Read the entire file content first
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Split the content by Pokemon blocks (each starts with 'mondata SPECIES_')
            pokemon_blocks = content.split('mondata SPECIES_')
            
            # Skip the first block which is usually empty or contains headers
            if pokemon_blocks and not pokemon_blocks[0].strip().startswith('SPECIES_'):
                pokemon_blocks = pokemon_blocks[1:]
            
            # Process each Pokemon block
            for block in pokemon_blocks:
                lines = block.splitlines()
                
                if not lines:
                    continue
                
                # Get the species name from the first line
                # Format is typically: 'SPECIES_NAME, "DisplayName"'
                species_line = lines[0]
                species_parts = species_line.split(',')
                if not species_parts:
                    continue
                    
                # The species name is the first part before the comma
                current_pokemon = 'SPECIES_' + species_parts[0].strip()
                
                # Look for the abilities line in this block
                for line in lines:
                    line = line.strip()
                    
                    # The abilities line starts with 'abilities '
                    if line.startswith('abilities '):
                        abilities_line_count += 1
                        
                        # Extract abilities from the line
                        ability_part = line.replace('abilities ', '').strip()
                        abilities = [ability.strip() for ability in ability_part.split(',')]
                        
                        # Filter out ABILITY_NONE
                        abilities = [ability for ability in abilities if ability != 'ABILITY_NONE']
                        
                        # Add abilities to the dictionary if we found any
                        if abilities:
                            self.pokemon_abilities[current_pokemon] = abilities
                            pokemon_count += 1
                            
                            # Print debug for first few
                            if pokemon_count <= 5:
                                print(f"Found abilities for {current_pokemon}: {', '.join(abilities)}")
                            
                        # Move to the next Pokemon block after finding abilities
                        break
            
            # Print summary
            print(f"Found abilities for {pokemon_count} Pokémon (from {abilities_line_count} ability lines)")
            
            # Print some sample abilities for verification
            print("\nSample of Pokémon abilities:")
            sample_count = 0
            for species in list(self.pokemon_abilities.keys())[:10]:  # Show first 10 for sample
                abilities = self.pokemon_abilities.get(species, [])
                ability_names = [ability.replace('ABILITY_', '').replace('_', ' ').title() for ability in abilities]
                print(f"{species}: {', '.join(ability_names) if ability_names else 'No abilities found'}")
                sample_count += 1
            
            # Now parse hidden abilities and add them to our dictionary
            self.parse_hidden_abilities()
            
            # If we didn't find enough abilities, use our fallback dictionary
            if pokemon_count < 10:  # Arbitrary threshold - should find way more in practice
                print("WARNING: Found very few abilities, using fallback abilities.")
                self.setup_pokemon_abilities()  # Use our hardcoded abilities as backup
                
        except Exception as e:
            error_msg = f"Failed to parse abilities file: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            
            # Fall back to our hardcoded abilities
            print("Using fallback abilities due to parsing error.")
            self.setup_pokemon_abilities()
            
    def parse_hidden_abilities(self):
        """Parse HiddenAbilityTable.c to get hidden abilities for Pokemon"""
        try:
            # Find the path to the hidden abilities file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            hidden_ability_file = os.path.join(base_dir, 'data', 'HiddenAbilityTable.c')
            
            print(f"Starting to parse hidden abilities from: {hidden_ability_file}")
            
            # Check if file exists
            if not os.path.exists(hidden_ability_file):
                print(f"WARNING: Hidden ability file not found at {hidden_ability_file}")
                return
            
            # Variables to track
            hidden_ability_count = 0
            
            # Read the file and extract hidden abilities
            with open(hidden_ability_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    
                    # Look for lines with format [SPECIES_NAME] = ABILITY_NAME
                    if '[SPECIES_' in line and '] = ABILITY_' in line:
                        # Extract species and ability names
                        parts = line.split('[', 1)[1].split(']', 1)
                        if len(parts) != 2:
                            continue
                            
                        species_name = parts[0].strip()
                        ability_part = parts[1].strip()
                        
                        # Extract ability (after '= ' and before ',') 
                        ability_name = ability_part.split('= ', 1)[1].split(',', 1)[0].strip()
                        
                        # Skip ABILITY_NONE entries
                        if ability_name == 'ABILITY_NONE':
                            continue
                            
                        # Add hidden ability to our dictionary
                        if species_name in self.pokemon_abilities:
                            # Append to existing abilities if not already present
                            if ability_name not in self.pokemon_abilities[species_name]:
                                self.pokemon_abilities[species_name].append(ability_name)
                                hidden_ability_count += 1
                        else:
                            # Create new entry with just the hidden ability
                            self.pokemon_abilities[species_name] = [ability_name]
                            hidden_ability_count += 1
                        
                        # Print debug for first few
                        if hidden_ability_count <= 5:
                            print(f"Added hidden ability for {species_name}: {ability_name}")
            
            print(f"Added {hidden_ability_count} hidden abilities to Pokemon")
            
            # Print some updated samples with hidden abilities
            print("\nSample of Pokémon abilities including hidden abilities:")
            sample_count = 0
            for species in list(self.pokemon_abilities.keys())[:10]:  # Show first 10 for sample
                abilities = self.pokemon_abilities.get(species, [])
                ability_names = [ability.replace('ABILITY_', '').replace('_', ' ').title() for ability in abilities]
                print(f"{species}: {', '.join(ability_names) if ability_names else 'No abilities found'}")
                sample_count += 1
                
        except Exception as e:
            error_msg = f"Failed to parse hidden abilities file: {str(e)}"
            print(f"WARNING: {error_msg}")
            traceback.print_exc()
            
    def load_ability_names(self):
        """Load ability names from abilities.inc"""
        ability_names = {}
        try:
            # Get the base directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            abilities_file = os.path.join(base_dir, 'asm', 'include', 'abilities.inc')
            
            if os.path.exists(abilities_file):
                with open(abilities_file, 'r') as f:
                    lines = f.readlines()
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('.equ ABILITY_'):
                            parts = line.split(',')
                            if len(parts) == 2:
                                ability_const = parts[0].strip()
                                ability_id = parts[1].strip()
                                
                                # Convert constant to more readable name
                                ability_name = ability_const.replace('.equ ', '').replace('_', ' ').title()
                                ability_names[ability_const.replace('.equ ', '')] = ability_name
            
            return ability_names
        except Exception as e:
            print(f"Failed to load ability names: {str(e)}")
            traceback.print_exc()
            return {}
    
    def parse_evolution_file(self, file_path):
        """Parse the evodata.s file to extract evolution data and identify fully evolved Pokémon"""
        try:
            print(f"Starting to parse evolution file: {file_path}")
            
            # Initialize the dictionaries
            self.evolution_data = {}  # Stores what each Pokémon evolves into
            self.fully_evolved_pokemon = set()  # Pokémon that don't evolve further
            self.evolving_pokemon = set()  # Pokémon that can evolve
            
            # Variables to track current Pokémon and evolution state
            current_pokemon = None
            pokemon_count = 0
            fully_evolved_count = 0
            evolving_count = 0
            
            # Read the file content and parse it
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Split the content into blocks for each Pokémon
            # Each block starts with "evodata SPECIES_" and ends before the next "evodata"
            evo_blocks = []
            current_block = ""
            for line in content.splitlines():
                if line.startswith('evodata SPECIES_'):
                    if current_block:  # Save the previous block if it exists
                        evo_blocks.append(current_block)
                    current_block = line  # Start a new block
                elif current_block:  # If we're in a block, add the line to it
                    current_block += "\n" + line
            if current_block:  # Add the last block
                evo_blocks.append(current_block)
                
            # Process each evolution block
            for block in evo_blocks:
                lines = block.splitlines()
                if not lines:  # Skip empty blocks
                    continue
                    
                # Extract the species name from the first line
                species_line = lines[0]
                if not species_line.startswith('evodata SPECIES_'):
                    continue
                    
                current_pokemon = species_line.replace('evodata ', '').strip()
                pokemon_count += 1
                
                # Check if there are evolution entries
                has_evolutions = False
                for i in range(1, len(lines)):
                    line = lines[i].strip()
                    if line.startswith('evolution ') or line.startswith('    evolution '):
                        # Clean up the line and split it
                        clean_line = line.replace('evolution ', '').replace('    evolution ', '').strip()
                        parts = [part.strip() for part in clean_line.split(',')]
                        
                        if len(parts) >= 3:
                            evo_method = parts[0].strip()
                            evo_target = parts[2].strip()
                            
                            # Check if this is a valid evolution
                            if evo_method != 'EVO_NONE' and evo_target != 'SPECIES_NONE':
                                has_evolutions = True
                                
                                # Add to the evolving Pokémon set
                                self.evolving_pokemon.add(current_pokemon)
                                
                                # Add this evolution to our data
                                if current_pokemon not in self.evolution_data:
                                    self.evolution_data[current_pokemon] = []
                                self.evolution_data[current_pokemon].append((evo_method, evo_target))
                
                # If no valid evolutions were found, this Pokémon is fully evolved
                if not has_evolutions:
                    self.fully_evolved_pokemon.add(current_pokemon)
                    fully_evolved_count += 1
                else:
                    evolving_count += 1
            
            # Print statistics
            print(f"Parsed evolution data for {pokemon_count} Pokémon species")
            print(f"Found {fully_evolved_count} fully evolved Pokémon")
            print(f"Found {evolving_count} Pokémon that can evolve")
            
            # Print some samples for verification
            print("\nSample of fully evolved Pokémon:")
            sample = sorted(list(self.fully_evolved_pokemon))[:10]  # Get a sorted sample
            for i, species in enumerate(sample):
                if species in self.all_pokemon_data:
                    print(f"{i+1}. {species} ({self.all_pokemon_data.get(species, {}).get('name', species)})")
                else:
                    print(f"{i+1}. {species}")
                    
            print("\nSample of evolving Pokémon:")
            sample = sorted(list(self.evolving_pokemon))[:10]  # Get a sorted sample
            for i, species in enumerate(sample):
                if species in self.evolution_data:
                    evos = [f"{target}" for method, target in self.evolution_data[species]]
                    evo_text = ", ".join(evos)
                    print(f"{i+1}. {species} → {evo_text}")
                else:
                    print(f"{i+1}. {species}")
                    
        except Exception as e:
            error_msg = f"Failed to parse evolution file: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            
            # Initialize empty sets as fallback
            self.evolution_data = {}
            self.fully_evolved_pokemon = set()
            self.evolving_pokemon = set()
    
    def determine_fully_evolved_non_legendary(self):
        """Determine which Pokemon are fully evolved and non-legendary"""
        print("Starting to determine fully evolved, non-legendary Pokemon...")
        
        # First, make a list of valid Pokemon with level-up moves
        valid_pokemon = []
        for species_name, moves in self.move_lists['level_up'].items():
            if len(moves) > 0:
                # Only include species that have data in our all_pokemon_data dictionary
                if species_name in self.all_pokemon_data:
                    valid_pokemon.append(species_name)
        
        print(f"Found {len(valid_pokemon)} Pokemon with level-up moves and valid data.")
        
        # Filter out special cases like SPECIES_EGG and other invalid Pokémon
        filtered_pokemon = []
        special_species = ['SPECIES_EGG', 'SPECIES_BAD_EGG', 'SPECIES_NONE']
        
        for species_name in valid_pokemon:
            # Skip special Pokémon that aren't actual species
            if species_name in special_species:
                continue
            filtered_pokemon.append(species_name)
            
        # Sort by Pokédex number
        self.pokemon_list = sorted(filtered_pokemon, key=lambda x: self.all_pokemon_data.get(x, {}).get('id', 9999))
        
        # Create a complete list of all Pokémon for the dropdown
        self.setup_all_pokemon_list()
    
    def setup_all_pokemon_list(self):
        """Create a comprehensive list of all Pokemon for the dropdown"""
        print("Setting up complete Pokemon list including all generations...")
        
        # Identify fully evolved Pokémon - we'll need this list for filtering
        self.identify_fully_evolved_pokemon()
        
        # Count Pokemon by generation based on ID ranges
        gen_counts = {
            'Gen 1': 0,  # 1-151
            'Gen 2': 0,  # 152-251
            'Gen 3': 0,  # 252-386
            'Gen 4': 0,  # 387-493
            'Gen 5': 0,  # 494-649
            'Gen 6': 0,  # 650-721
            'Gen 7': 0,  # 722-809
            'Gen 8': 0,  # 810-898
            'Forms/Other': 0  # variants and special forms
        }
        
        # Count regular species vs. forms/variants
        regular_species = 0
        forms_variants = 0
        
        for species in self.pokemon_list:
            # Check if it's a form/variant
            is_form = any(form_marker in species for form_marker in [
                '_FORM', '_MEGA', 'ALOLAN', 'GALARIAN', 'HISUIAN', 
                '_REGIONAL', '_START', '_DIFFERENCE'
            ])
            
            if is_form:
                forms_variants += 1
            else:
                regular_species += 1
            
            # Categorize by generation
            if species in self.all_pokemon_data:
                pokemon_id = self.all_pokemon_data[species].get('id', 0)
                
                if 1 <= pokemon_id <= 151:
                    gen_counts['Gen 1'] += 1
                elif 152 <= pokemon_id <= 251:
                    gen_counts['Gen 2'] += 1
                elif 252 <= pokemon_id <= 386:
                    gen_counts['Gen 3'] += 1
                elif 387 <= pokemon_id <= 493:
                    gen_counts['Gen 4'] += 1
                elif 494 <= pokemon_id <= 649:
                    gen_counts['Gen 5'] += 1
                elif 650 <= pokemon_id <= 721:
                    gen_counts['Gen 6'] += 1
                elif 722 <= pokemon_id <= 809:
                    gen_counts['Gen 7'] += 1
                elif 810 <= pokemon_id <= 898:
                    gen_counts['Gen 8'] += 1
                else:
                    gen_counts['Forms/Other'] += 1
            else:
                gen_counts['Forms/Other'] += 1
                
        # Print detailed statistics
        print(f"\nTotal Pokémon in dropdown: {len(self.pokemon_list)}")
        print(f"Regular species: {regular_species}")
        print(f"Forms/variants: {forms_variants}")
        print(f"Fully evolved Pokémon: {len(self.fully_evolved_pokemon)}")
        
        # Print generation breakdown
        print("\nPokémon by generation:")
        for gen, count in gen_counts.items():
            print(f"{gen}: {count} Pokémon")
            
        # Print a sample of Pokémon from each generation for verification
        print("\nSample Pokémon from each generation:")
        gen_samples = {}
        
        # Collect samples from each generation
        for species in self.pokemon_list:
            if species not in self.all_pokemon_data:
                continue
                
            pokemon_id = self.all_pokemon_data[species].get('id', 0)
            
            if 1 <= pokemon_id <= 151 and 'Gen 1' not in gen_samples:
                gen_samples['Gen 1'] = species
            elif 152 <= pokemon_id <= 251 and 'Gen 2' not in gen_samples:
                gen_samples['Gen 2'] = species
            elif 252 <= pokemon_id <= 386 and 'Gen 3' not in gen_samples:
                gen_samples['Gen 3'] = species
            elif 387 <= pokemon_id <= 493 and 'Gen 4' not in gen_samples:
                gen_samples['Gen 4'] = species
            elif 494 <= pokemon_id <= 649 and 'Gen 5' not in gen_samples:
                gen_samples['Gen 5'] = species
            elif 650 <= pokemon_id <= 721 and 'Gen 6' not in gen_samples:
                gen_samples['Gen 6'] = species
            elif 722 <= pokemon_id <= 809 and 'Gen 7' not in gen_samples:
                gen_samples['Gen 7'] = species
            elif 810 <= pokemon_id <= 898 and 'Gen 8' not in gen_samples:
                gen_samples['Gen 8'] = species
                
            # Break if we have samples from all generations
            if len(gen_samples) == 8:
                break
                
        # Print the samples
        for gen, species in sorted(gen_samples.items()):
            print(f"{gen}: {species} ({self.all_pokemon_data[species]['name']})")
            
        # Also print a sample of form variants
        print("\nSample of form variants:")
        form_count = 0
        for species in self.pokemon_list:
            if any(form_marker in species for form_marker in [
                '_FORM', '_MEGA', 'ALOLAN', 'GALARIAN', 'HISUIAN'
            ]):
                if species in self.all_pokemon_data:
                    print(f"{species} ({self.all_pokemon_data[species]['name']})")
                else:
                    print(f"{species}")
                    
                form_count += 1
                if form_count >= 5:
                    break
                    
    def identify_fully_evolved_pokemon(self):
        """Identify which Pokémon are fully evolved"""
        print("Identifying fully evolved Pokémon...")
        
        # If we already have fully evolved Pokémon from the evolution file, use that
        if hasattr(self, 'fully_evolved_pokemon') and self.fully_evolved_pokemon:
            print(f"Using {len(self.fully_evolved_pokemon)} fully evolved Pokémon identified from evolution data file")
            return self.fully_evolved_pokemon
            
        # Otherwise, initialize the sets to track different evolution stages
        self.fully_evolved_pokemon = set()
        base_forms = set()
        middle_stages = set()
        
        # Create a comprehensive mapping of which Pokémon evolve into which others
        # This helps us find the final evolution in each chain
        evolves_into = {}
        evolves_from = {}
        
        # These are known evolution families (manually defined as a fallback)
        # Each entry represents a complete evolution chain with the base form as the key
        # and the evolved forms in order as the list values
        evolution_families = {
            # Gen 1 Starters
            'SPECIES_BULBASAUR': ['SPECIES_IVYSAUR', 'SPECIES_VENUSAUR'],
            'SPECIES_CHARMANDER': ['SPECIES_CHARMELEON', 'SPECIES_CHARIZARD'],
            'SPECIES_SQUIRTLE': ['SPECIES_WARTORTLE', 'SPECIES_BLASTOISE'],
            # Other Gen 1 examples
            'SPECIES_CATERPIE': ['SPECIES_METAPOD', 'SPECIES_BUTTERFREE'],
            'SPECIES_WEEDLE': ['SPECIES_KAKUNA', 'SPECIES_BEEDRILL'],
            'SPECIES_PIDGEY': ['SPECIES_PIDGEOTTO', 'SPECIES_PIDGEOT'],
            'SPECIES_RATTATA': ['SPECIES_RATICATE'],
            'SPECIES_SPEAROW': ['SPECIES_FEAROW'],
            'SPECIES_EKANS': ['SPECIES_ARBOK'],
            'SPECIES_PIKACHU': ['SPECIES_RAICHU'],
            'SPECIES_SANDSHREW': ['SPECIES_SANDSLASH'],
            'SPECIES_NIDORAN_F': ['SPECIES_NIDORINA', 'SPECIES_NIDOQUEEN'],
            'SPECIES_NIDORAN_M': ['SPECIES_NIDORINO', 'SPECIES_NIDOKING'],
            'SPECIES_CLEFAIRY': ['SPECIES_CLEFABLE'],
            'SPECIES_VULPIX': ['SPECIES_NINETALES'],
            'SPECIES_JIGGLYPUFF': ['SPECIES_WIGGLYTUFF'],
            'SPECIES_ZUBAT': ['SPECIES_GOLBAT', 'SPECIES_CROBAT'],
            'SPECIES_ODDISH': ['SPECIES_GLOOM', 'SPECIES_VILEPLUME'],
            'SPECIES_PARAS': ['SPECIES_PARASECT'],
            'SPECIES_VENONAT': ['SPECIES_VENOMOTH'],
            'SPECIES_DIGLETT': ['SPECIES_DUGTRIO'],
            'SPECIES_MEOWTH': ['SPECIES_PERSIAN'],
            'SPECIES_PSYDUCK': ['SPECIES_GOLDUCK'],
            'SPECIES_MANKEY': ['SPECIES_PRIMEAPE'],
            'SPECIES_GROWLITHE': ['SPECIES_ARCANINE'],
            'SPECIES_POLIWAG': ['SPECIES_POLIWHIRL', 'SPECIES_POLIWRATH'],
            'SPECIES_ABRA': ['SPECIES_KADABRA', 'SPECIES_ALAKAZAM'],
            'SPECIES_MACHOP': ['SPECIES_MACHOKE', 'SPECIES_MACHAMP'],
            'SPECIES_BELLSPROUT': ['SPECIES_WEEPINBELL', 'SPECIES_VICTREEBEL'],
            'SPECIES_TENTACOOL': ['SPECIES_TENTACRUEL'],
            'SPECIES_GEODUDE': ['SPECIES_GRAVELER', 'SPECIES_GOLEM'],
            'SPECIES_PONYTA': ['SPECIES_RAPIDASH'],
            'SPECIES_SLOWPOKE': ['SPECIES_SLOWBRO'],
            'SPECIES_MAGNEMITE': ['SPECIES_MAGNETON', 'SPECIES_MAGNEZONE'],
            'SPECIES_DODUO': ['SPECIES_DODRIO'],
            'SPECIES_SEEL': ['SPECIES_DEWGONG'],
            'SPECIES_GRIMER': ['SPECIES_MUK'],
            'SPECIES_SHELLDER': ['SPECIES_CLOYSTER'],
            'SPECIES_GASTLY': ['SPECIES_HAUNTER', 'SPECIES_GENGAR'],
            'SPECIES_ONIX': ['SPECIES_STEELIX'],
            'SPECIES_DROWZEE': ['SPECIES_HYPNO'],
            'SPECIES_KRABBY': ['SPECIES_KINGLER'],
            'SPECIES_VOLTORB': ['SPECIES_ELECTRODE'],
            'SPECIES_EXEGGCUTE': ['SPECIES_EXEGGUTOR'],
            'SPECIES_CUBONE': ['SPECIES_MAROWAK'],
            'SPECIES_KOFFING': ['SPECIES_WEEZING'],
            'SPECIES_RHYHORN': ['SPECIES_RHYDON', 'SPECIES_RHYPERIOR'],
            'SPECIES_HORSEA': ['SPECIES_SEADRA', 'SPECIES_KINGDRA'],
            'SPECIES_GOLDEEN': ['SPECIES_SEAKING'],
            'SPECIES_STARYU': ['SPECIES_STARMIE'],
            'SPECIES_MAGIKARP': ['SPECIES_GYARADOS'],
            'SPECIES_EEVEE': ['SPECIES_VAPOREON'], # Eevee has multiple evolutions
            'SPECIES_EEVEE2': ['SPECIES_JOLTEON'], # Separate entries for each Eeveelution
            'SPECIES_EEVEE3': ['SPECIES_FLAREON'],
            'SPECIES_EEVEE4': ['SPECIES_ESPEON'],
            'SPECIES_EEVEE5': ['SPECIES_UMBREON'],
            'SPECIES_EEVEE6': ['SPECIES_LEAFEON'],
            'SPECIES_EEVEE7': ['SPECIES_GLACEON'],
            'SPECIES_EEVEE8': ['SPECIES_SYLVEON'],
            'SPECIES_OMANYTE': ['SPECIES_OMASTAR'],
            'SPECIES_KABUTO': ['SPECIES_KABUTOPS'],
            'SPECIES_DRATINI': ['SPECIES_DRAGONAIR', 'SPECIES_DRAGONITE'],
            
            # Gen 2 Starters
            'SPECIES_CHIKORITA': ['SPECIES_BAYLEEF', 'SPECIES_MEGANIUM'],
            'SPECIES_CYNDAQUIL': ['SPECIES_QUILAVA', 'SPECIES_TYPHLOSION'],
            'SPECIES_TOTODILE': ['SPECIES_CROCONAW', 'SPECIES_FERALIGATR'],
            'SPECIES_SENTRET': ['SPECIES_FURRET'],
            'SPECIES_HOOTHOOT': ['SPECIES_NOCTOWL'],
            'SPECIES_LEDYBA': ['SPECIES_LEDIAN'],
            'SPECIES_SPINARAK': ['SPECIES_ARIADOS'],
            'SPECIES_CHINCHOU': ['SPECIES_LANTURN'],
            'SPECIES_PICHU': ['SPECIES_PIKACHU', 'SPECIES_RAICHU'],
            'SPECIES_CLEFFA': ['SPECIES_CLEFAIRY', 'SPECIES_CLEFABLE'],
            'SPECIES_IGGLYBUFF': ['SPECIES_JIGGLYPUFF', 'SPECIES_WIGGLYTUFF'],
            'SPECIES_TOGEPI': ['SPECIES_TOGETIC', 'SPECIES_TOGEKISS'],
            'SPECIES_MAREEP': ['SPECIES_FLAAFFY', 'SPECIES_AMPHAROS'],
            'SPECIES_MARILL': ['SPECIES_AZUMARILL'],
            'SPECIES_HOPPIP': ['SPECIES_SKIPLOOM', 'SPECIES_JUMPLUFF'],
            'SPECIES_SUNKERN': ['SPECIES_SUNFLORA'],
            
            # Gen 3 Starters
            'SPECIES_TREECKO': ['SPECIES_GROVYLE', 'SPECIES_SCEPTILE'],
            'SPECIES_TORCHIC': ['SPECIES_COMBUSKEN', 'SPECIES_BLAZIKEN'],
            'SPECIES_MUDKIP': ['SPECIES_MARSHTOMP', 'SPECIES_SWAMPERT'],
            'SPECIES_POOCHYENA': ['SPECIES_MIGHTYENA'],
            'SPECIES_ZIGZAGOON': ['SPECIES_LINOONE'],
            'SPECIES_WURMPLE': ['SPECIES_SILCOON', 'SPECIES_BEAUTIFLY'],
            'SPECIES_WURMPLE2': ['SPECIES_CASCOON', 'SPECIES_DUSTOX'],
            'SPECIES_LOTAD': ['SPECIES_LOMBRE', 'SPECIES_LUDICOLO'],
            'SPECIES_SEEDOT': ['SPECIES_NUZLEAF', 'SPECIES_SHIFTRY'],
            'SPECIES_RALTS': ['SPECIES_KIRLIA', 'SPECIES_GARDEVOIR'],
            'SPECIES_RALTS2': ['SPECIES_KIRLIA', 'SPECIES_GALLADE'],
            
            # Gen 4 Starters
            'SPECIES_TURTWIG': ['SPECIES_GROTLE', 'SPECIES_TORTERRA'],
            'SPECIES_CHIMCHAR': ['SPECIES_MONFERNO', 'SPECIES_INFERNAPE'],
            'SPECIES_PIPLUP': ['SPECIES_PRINPLUP', 'SPECIES_EMPOLEON'],
            'SPECIES_STARLY': ['SPECIES_STARAVIA', 'SPECIES_STARAPTOR'],
            'SPECIES_BIDOOF': ['SPECIES_BIBAREL'],
            'SPECIES_SHINX': ['SPECIES_LUXIO', 'SPECIES_LUXRAY'],
            'SPECIES_BUDEW': ['SPECIES_ROSELIA', 'SPECIES_ROSERADE'],
            'SPECIES_CRANIDOS': ['SPECIES_RAMPARDOS'],
            'SPECIES_SHIELDON': ['SPECIES_BASTIODON'],
            'SPECIES_BURMY': ['SPECIES_WORMADAM'],
            'SPECIES_BURMY2': ['SPECIES_MOTHIM'],
            'SPECIES_COMBEE': ['SPECIES_VESPIQUEN'],
            
            # Gen 5 (Unova) additions
            'SPECIES_LILLIPUP': ['SPECIES_HERDIER', 'SPECIES_STOUTLAND'],
            'SPECIES_PURRLOIN': ['SPECIES_LIEPARD'],
            'SPECIES_MUNNA': ['SPECIES_MUSHARNA'],
            'SPECIES_ROGGENROLA': ['SPECIES_BOLDORE', 'SPECIES_GIGALITH'],
            'SPECIES_WOOBAT': ['SPECIES_SWOOBAT'],
            'SPECIES_DRILBUR': ['SPECIES_EXCADRILL'],
            'SPECIES_TIMBURR': ['SPECIES_GURDURR', 'SPECIES_CONKELDURR'],
            'SPECIES_TYMPOLE': ['SPECIES_PALPITOAD', 'SPECIES_SEISMITOAD'],
            'SPECIES_SEWADDLE': ['SPECIES_SWADLOON', 'SPECIES_LEAVANNY'],
            'SPECIES_VENIPEDE': ['SPECIES_WHIRLIPEDE', 'SPECIES_SCOLIPEDE'],
            'SPECIES_SANDILE': ['SPECIES_KROKOROK', 'SPECIES_KROOKODILE'],
            'SPECIES_DARUMAKA': ['SPECIES_DARMANITAN'],
            'SPECIES_SCRAGGY': ['SPECIES_SCRAFTY'],
            'SPECIES_YAMASK': ['SPECIES_COFAGRIGUS'],
            'SPECIES_TIRTOUGA': ['SPECIES_CARRACOSTA'],
            'SPECIES_ARCHEN': ['SPECIES_ARCHEOPS'],
            'SPECIES_TRUBBISH': ['SPECIES_GARBODOR'],
            'SPECIES_ZORUA': ['SPECIES_ZOROARK'],
            'SPECIES_MINCCINO': ['SPECIES_CINCCINO'],
            'SPECIES_GOTHITA': ['SPECIES_GOTHORITA', 'SPECIES_GOTHITELLE'],
            'SPECIES_SOLOSIS': ['SPECIES_DUOSION', 'SPECIES_REUNICLUS'],
            'SPECIES_DUCKLETT': ['SPECIES_SWANNA'],
            'SPECIES_VANILLITE': ['SPECIES_VANILLISH', 'SPECIES_VANILLUXE'],
            'SPECIES_DEERLING': ['SPECIES_SAWSBUCK'],
            'SPECIES_JOLTIK': ['SPECIES_GALVANTULA'],
            'SPECIES_AXEW': ['SPECIES_FRAXURE', 'SPECIES_HAXORUS'],
            'SPECIES_CUBCHOO': ['SPECIES_BEARTIC'],
            'SPECIES_SHELMET': ['SPECIES_ACCELGOR'],
            'SPECIES_STUNFISK': ['SPECIES_STUNFISK'],
            'SPECIES_PAWNIARD': ['SPECIES_BISHARP', 'SPECIES_KINGAMBIT'],
            'SPECIES_RUFFLET': ['SPECIES_BRAVIARY'],
            'SPECIES_VULLABY': ['SPECIES_MANDIBUZZ'],
            'SPECIES_DEINO': ['SPECIES_ZWEILOUS', 'SPECIES_HYDREIGON'],
            'SPECIES_LARVESTA': ['SPECIES_VOLCARONA'],
            
            # Gen 6 (Kalos) additions
            'SPECIES_CHESPIN': ['SPECIES_QUILLADIN', 'SPECIES_CHESNAUGHT'],
            'SPECIES_FENNEKIN': ['SPECIES_BRAIXEN', 'SPECIES_DELPHOX'],
            'SPECIES_FROAKIE': ['SPECIES_FROGADIER', 'SPECIES_GRENINJA'],
            'SPECIES_BUNNELBY': ['SPECIES_DIGGERSBY'],
            'SPECIES_FLETCHLING': ['SPECIES_FLETCHINDER', 'SPECIES_TALONFLAME'],
            'SPECIES_SCATTERBUG': ['SPECIES_SPEWPA', 'SPECIES_VIVILLON'],
            'SPECIES_LITLEO': ['SPECIES_PYROAR'],
            'SPECIES_FLABEBE': ['SPECIES_FLOETTE', 'SPECIES_FLORGES'],
            'SPECIES_SKIDDO': ['SPECIES_GOGOAT'],
            'SPECIES_PANCHAM': ['SPECIES_PANGORO'],
            'SPECIES_ESPURR': ['SPECIES_MEOWSTIC'],
            'SPECIES_HONEDGE': ['SPECIES_DOUBLADE', 'SPECIES_AEGISLASH'],
            'SPECIES_SPRITZEE': ['SPECIES_AROMATISSE'],
            'SPECIES_SWIRLIX': ['SPECIES_SLURPUFF'],
            'SPECIES_INKAY': ['SPECIES_MALAMAR'],
            'SPECIES_BINACLE': ['SPECIES_BARBARACLE'],
            'SPECIES_SKRELP': ['SPECIES_DRAGALGE'],
            'SPECIES_CLAUNCHER': ['SPECIES_CLAWITZER'],
            'SPECIES_HELIOPTILE': ['SPECIES_HELIOLISK'],
            'SPECIES_TYRUNT': ['SPECIES_TYRANTRUM'],
            'SPECIES_AMAURA': ['SPECIES_AURORUS'],
            'SPECIES_HAWLUCHA': ['SPECIES_HAWLUCHA'],  # Single stage
            'SPECIES_DEDENNE': ['SPECIES_DEDENNE'],  # Single stage
            'SPECIES_CARBINK': ['SPECIES_CARBINK'],  # Single stage
            'SPECIES_GOOMY': ['SPECIES_SLIGGOO', 'SPECIES_GOODRA'],
            'SPECIES_KLEFKI': ['SPECIES_KLEFKI'],  # Single stage
            'SPECIES_PHANTUMP': ['SPECIES_TREVENANT'],
            'SPECIES_PUMPKABOO': ['SPECIES_GOURGEIST'],
            'SPECIES_BERGMITE': ['SPECIES_AVALUGG'],
            'SPECIES_NOIBAT': ['SPECIES_NOIVERN'],
            
            # Gen 7 (Alola) additions
            'SPECIES_ROWLET': ['SPECIES_DARTRIX', 'SPECIES_DECIDUEYE'],
            'SPECIES_LITTEN': ['SPECIES_TORRACAT', 'SPECIES_INCINEROAR'],
            'SPECIES_POPPLIO': ['SPECIES_BRIONNE', 'SPECIES_PRIMARINA'],
            'SPECIES_PIKIPEK': ['SPECIES_TRUMBEAK', 'SPECIES_TOUCANNON'],
            'SPECIES_YUNGOOS': ['SPECIES_GUMSHOOS'],
            'SPECIES_GRUBBIN': ['SPECIES_CHARJABUG', 'SPECIES_VIKAVOLT'],
            'SPECIES_CRABRAWLER': ['SPECIES_CRABOMINABLE'],
            'SPECIES_CUTIEFLY': ['SPECIES_RIBOMBEE'],
            'SPECIES_ROCKRUFF': ['SPECIES_LYCANROC'],
            'SPECIES_MAREANIE': ['SPECIES_TOXAPEX'],
            'SPECIES_MUDBRAY': ['SPECIES_MUDSDALE'],
            'SPECIES_DEWPIDER': ['SPECIES_ARAQUANID'],
            'SPECIES_FOMANTIS': ['SPECIES_LURANTIS'],
            'SPECIES_MORELULL': ['SPECIES_SHIINOTIC'],
            'SPECIES_SALANDIT': ['SPECIES_SALAZZLE'],
            'SPECIES_STUFFUL': ['SPECIES_BEWEAR'],
            'SPECIES_BOUNSWEET': ['SPECIES_STEENEE', 'SPECIES_TSAREENA'],
            'SPECIES_WIMPOD': ['SPECIES_GOLISOPOD'],
            'SPECIES_SANDYGAST': ['SPECIES_PALOSSAND'],
            'SPECIES_PYUKUMUKU': ['SPECIES_PYUKUMUKU'],  # Single stage
            'SPECIES_TYPE_NULL': ['SPECIES_SILVALLY'],
            'SPECIES_MINIOR': ['SPECIES_MINIOR'],  # Single stage
            'SPECIES_KOMALA': ['SPECIES_KOMALA'],  # Single stage
            'SPECIES_TURTONATOR': ['SPECIES_TURTONATOR'],  # Single stage
            'SPECIES_TOGEDEMARU': ['SPECIES_TOGEDEMARU'],  # Single stage
            'SPECIES_MIMIKYU': ['SPECIES_MIMIKYU'],  # Single stage
            'SPECIES_BRUXISH': ['SPECIES_BRUXISH'],  # Single stage
            'SPECIES_DRAMPA': ['SPECIES_DRAMPA'],  # Single stage
            'SPECIES_DHELMISE': ['SPECIES_DHELMISE'],  # Single stage
            'SPECIES_JANGMO_O': ['SPECIES_HAKAMO_O', 'SPECIES_KOMMO_O'],
            
            # Gen 8 (Galar) additions
            'SPECIES_GROOKEY': ['SPECIES_THWACKEY', 'SPECIES_RILLABOOM'],
            'SPECIES_SCORBUNNY': ['SPECIES_RABOOT', 'SPECIES_CINDERACE'],
            'SPECIES_SOBBLE': ['SPECIES_DRIZZILE', 'SPECIES_INTELEON'],
            'SPECIES_SKWOVET': ['SPECIES_GREEDENT'],
            'SPECIES_ROOKIDEE': ['SPECIES_CORVISQUIRE', 'SPECIES_CORVIKNIGHT'],
            'SPECIES_BLIPBUG': ['SPECIES_DOTTLER', 'SPECIES_ORBEETLE'],
            'SPECIES_NICKIT': ['SPECIES_THIEVUL'],
            'SPECIES_GOSSIFLEUR': ['SPECIES_ELDEGOSS'],
            'SPECIES_WOOLOO': ['SPECIES_DUBWOOL'],
            'SPECIES_CHEWTLE': ['SPECIES_DREDNAW'],
            'SPECIES_YAMPER': ['SPECIES_BOLTUND'],
            'SPECIES_ROLYCOLY': ['SPECIES_CARKOL', 'SPECIES_COALOSSAL'],
            'SPECIES_APPLIN': ['SPECIES_FLAPPLE'],
            'SPECIES_APPLIN2': ['SPECIES_APPLETUN'],
            'SPECIES_SILICOBRA': ['SPECIES_SANDACONDA'],
            'SPECIES_CRAMORANT': ['SPECIES_CRAMORANT'],  # Single stage
            'SPECIES_ARROKUDA': ['SPECIES_BARRASKEWDA'],
            'SPECIES_TOXEL': ['SPECIES_TOXTRICITY'],
            'SPECIES_SIZZLIPEDE': ['SPECIES_CENTISKORCH'],
            'SPECIES_CLOBBOPUS': ['SPECIES_GRAPPLOCT'],
            'SPECIES_SINISTEA': ['SPECIES_POLTEAGEIST'],
            'SPECIES_HATENNA': ['SPECIES_HATTREM', 'SPECIES_HATTERENE'],
            'SPECIES_IMPIDIMP': ['SPECIES_MORGREM', 'SPECIES_GRIMMSNARL'],
            'SPECIES_MILCERY': ['SPECIES_ALCREMIE'],
            'SPECIES_FALINKS': ['SPECIES_FALINKS'],  # Single stage
            'SPECIES_PINCURCHIN': ['SPECIES_PINCURCHIN'],  # Single stage
            'SPECIES_SNOM': ['SPECIES_FROSMOTH'],
            'SPECIES_STONJOURNER': ['SPECIES_STONJOURNER'],  # Single stage
            'SPECIES_EISCUE': ['SPECIES_EISCUE'],  # Single stage
            'SPECIES_INDEEDEE': ['SPECIES_INDEEDEE'],  # Single stage
            'SPECIES_MORPEKO': ['SPECIES_MORPEKO'],  # Single stage
            'SPECIES_CUFANT': ['SPECIES_COPPERAJAH'],
            'SPECIES_DRACOZOLT': ['SPECIES_DRACOZOLT'],  # Single stage
            'SPECIES_ARCTOZOLT': ['SPECIES_ARCTOZOLT'],  # Single stage
            'SPECIES_DRACOVISH': ['SPECIES_DRACOVISH'],  # Single stage
            'SPECIES_ARCTOVISH': ['SPECIES_ARCTOVISH'],  # Single stage
            'SPECIES_DURALUDON': ['SPECIES_DURALUDON'],  # Single stage
            'SPECIES_DREEPY': ['SPECIES_DRAKLOAK', 'SPECIES_DRAGAPULT'],
        }
        
        # Process all known evolution families to build our evolution maps
        for base_form, evolution_chain in evolution_families.items():
            # Add the base form to our set
            base_forms.add(base_form)
            
            # Add each step in the evolution chain to our maps
            if evolution_chain:  # If there are any evolutions
                # Track what the base form evolves into
                if base_form not in evolves_into:
                    evolves_into[base_form] = []
                evolves_into[base_form].append(evolution_chain[0])
                
                # Track what evolves from the base form
                if evolution_chain[0] not in evolves_from:
                    evolves_from[evolution_chain[0]] = []
                evolves_from[evolution_chain[0]].append(base_form)
                
                # If there are multiple stages, process them too
                for i in range(len(evolution_chain) - 1):
                    current = evolution_chain[i]
                    next_stage = evolution_chain[i + 1]
                    
                    # Add middle stages
                    middle_stages.add(current)
                    
                    # Track what this stage evolves into
                    if current not in evolves_into:
                        evolves_into[current] = []
                    evolves_into[current].append(next_stage)
                    
                    # Track what evolves from this stage
                    if next_stage not in evolves_from:
                        evolves_from[next_stage] = []
                    evolves_from[next_stage].append(current)
                
                # The last Pokémon in the chain is fully evolved
                self.fully_evolved_pokemon.add(evolution_chain[-1])
        
        # Identify fully evolved Pokémon (those that don't evolve into anything)
        for species in self.pokemon_list:
            # Skip species we've already categorized
            if (species in self.fully_evolved_pokemon or 
                species in middle_stages or 
                species in base_forms):
                continue
                
            # Skip alternate forms, variants, and special cases
            if any(form_marker in species for form_marker in [
                '_FORM', '_MEGA', 'ALOLAN', 'GALARIAN', 'HISUIAN',
                '_REGIONAL', '_START', '_DIFFERENCE', '_CAP', '_RIDE', '_STAR',
                '_BELLE', '_POP', '_PH', '_LIBRE', '_COSPLAY', '_UNBOUND',
                '_10', '_50', '_COMPLETE', '_PRIMAL', '_SHADOW'
            ]):
                continue
                
            # Check if this Pokémon evolves into anything
            if species in evolves_into and evolves_into[species]:
                # This species evolves into something, so it's not fully evolved
                continue
                
            # If we get here, the species doesn't evolve further
            self.fully_evolved_pokemon.add(species)
        
        # Print statistics and some examples
        print(f"Identified {len(self.fully_evolved_pokemon)} fully evolved Pokémon")
        print(f"Identified {len(middle_stages)} middle-stage Pokémon")
        print(f"Identified {len(base_forms)} base form Pokémon")
        
        print("\nExamples of fully evolved Pokémon:")
        fully_evolved_sample = sorted(list(self.fully_evolved_pokemon))[:15]  # Get a sorted sample
        for i, species in enumerate(fully_evolved_sample):
            if species in self.all_pokemon_data:
                print(f"{i+1}. {species} ({self.all_pokemon_data[species]['name']})")
            else:
                print(f"{i+1}. {species}")
        
        # Print some base forms and middle stages for verification
        print("\nExamples of base forms:")
        base_forms_sample = sorted(list(base_forms))[:8]  # Get a sorted sample
        for i, species in enumerate(base_forms_sample):
            if species in self.all_pokemon_data:
                print(f"{i+1}. {species} ({self.all_pokemon_data[species]['name']})")
            else:
                print(f"{i+1}. {species}")
        
        print("\nExamples of middle stage Pokémon:")
        middle_stages_sample = sorted(list(middle_stages))[:8]  # Get a sorted sample
        for i, species in enumerate(middle_stages_sample):
            if species in self.all_pokemon_data:
                print(f"{i+1}. {species} ({self.all_pokemon_data[species]['name']})")
            else:
                print(f"{i+1}. {species}")
        
        # Log any special cases for debugging
        print("\nNote: Special forms and variants are excluded from the evolution classification.")
        
        return self.fully_evolved_pokemon
        
    def setup_pokemon_dropdown(self):
        """Set up the Pokémon dropdown with all Pokémon or just fully evolved ones"""
        # Clear the dropdown first
        self.pokemon_dropdown.clear()
        
        # Add empty option as first item
        self.pokemon_dropdown.addItem("Select a Pokemon", None)
        
        # Determine whether to show all Pokémon or just fully evolved ones
        show_only_fully_evolved = self.show_fully_evolved_only.isChecked()
        
        # Get the list of Pokémon to display
        if show_only_fully_evolved:
            # Filter to only show fully evolved Pokémon
            pokemon_to_display = [p for p in self.pokemon_list if p in self.fully_evolved_pokemon]
            print(f"Added {len(pokemon_to_display)} Pokémon to dropdown (fully evolved only)")
        else:
            # Show all Pokémon
            pokemon_to_display = self.pokemon_list
            print(f"Added {len(pokemon_to_display)} Pokémon to dropdown (all Pokémon)")
        
        # Add each Pokémon to the dropdown
        for species_name in pokemon_to_display:
            # Skip Pokémon that don't have a valid display name
            if species_name not in self.all_pokemon_data:
                continue
                
            # Get the display name
            display_name = self.all_pokemon_data[species_name]['name']
            
            # Add to dropdown
            self.pokemon_dropdown.addItem(f"{display_name}", species_name)
    
    def on_filter_changed(self):
        """Handle changes to the Pokémon filter options"""
        # Remember the currently selected Pokémon if any
        current_pokemon = self.current_pokemon
        
        # Re-populate the dropdown with the new filter settings
        self.setup_pokemon_dropdown()
        
        # Try to re-select the previously selected Pokémon if it's still in the list
        if current_pokemon:
            for i in range(self.pokemon_dropdown.count()):
                if self.pokemon_dropdown.itemData(i) == current_pokemon:
                    self.pokemon_dropdown.setCurrentIndex(i)
                    return
                
        # If we couldn't find the previous selection, reset to index 0
        self.pokemon_dropdown.setCurrentIndex(0)
    
    def format_pokemon_name(self, species_name):
        """Format the Pokemon name from SPECIES_NAME to Name format"""
        if not species_name.startswith('SPECIES_'):
            return species_name
        
        name = species_name[8:].replace('_', ' ').title()
        
        # Handle special cases
        name = name.replace('Mr Mime', 'Mr. Mime')
        name = name.replace('Mime Jr', 'Mime Jr.')
        name = name.replace('Nidoran M', 'Nidoran♂')
        name = name.replace('Nidoran F', 'Nidoran♀')
        name = name.replace('Farfetchd', "Farfetch'd")
        
        return name
    
    def is_legendary(self, species_name):
        """Determine if a Pokemon is legendary based on its species name or ID"""
        legendary_ids = {
            144, 145, 146, 150, 151,  # Gen 1
            243, 244, 245, 249, 250, 251,  # Gen 2
            377, 378, 379, 380, 381, 382, 383, 384, 385, 386,  # Gen 3
            480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493,  # Gen 4
            494, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649,  # Gen 5
            716, 717, 718, 719, 720, 721,  # Gen 6
            785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807  # Gen 7
        }
        
        legendary_names = {
            'ARTICUNO', 'ZAPDOS', 'MOLTRES', 'MEWTWO', 'MEW',
            'RAIKOU', 'ENTEI', 'SUICUNE', 'LUGIA', 'HO_OH', 'CELEBI',
            'REGIROCK', 'REGICE', 'REGISTEEL', 'LATIAS', 'LATIOS', 
            'KYOGRE', 'GROUDON', 'RAYQUAZA', 'JIRACHI', 'DEOXYS',
            'UXIE', 'MESPRIT', 'AZELF', 'DIALGA', 'PALKIA', 'HEATRAN', 
            'REGIGIGAS', 'GIRATINA', 'CRESSELIA', 'PHIONE', 'MANAPHY', 
            'DARKRAI', 'SHAYMIN', 'ARCEUS'
        }
        
        # Check if it's in the legendary IDs list
        if 'id' in self.all_pokemon_data.get(species_name, {}) and self.all_pokemon_data[species_name]['id'] in legendary_ids:
            return True
        
        # Check if the name contains any legendary names
        for legendary in legendary_names:
            if legendary in species_name:
                return True
        
        return False
    
    def is_evolution_of(self, species1, species2):
        """Check if species1 is an evolution of species2 based on name patterns"""
        # This is a simplified approach and may not catch all cases
        name1 = species1.replace('SPECIES_', '')
        name2 = species2.replace('SPECIES_', '')
        
        # Common evolution patterns
        if name1.startswith(name2):
            return True
        
        # Known evolution pairs
        evolution_pairs = {
            'VENUSAUR': 'IVYSAUR',
            'CHARIZARD': 'CHARMELEON',
            'BLASTOISE': 'WARTORTLE',
            'BUTTERFREE': 'METAPOD',
            'BEEDRILL': 'KAKUNA',
            'PIDGEOT': 'PIDGEOTTO',
            'RATICATE': 'RATTATA',
            'FEAROW': 'SPEAROW',
            'ARBOK': 'EKANS',
            'RAICHU': 'PIKACHU',
            'SANDSLASH': 'SANDSHREW',
            'NIDOQUEEN': 'NIDORINA',
            'NIDOKING': 'NIDORINO',
            'CLEFABLE': 'CLEFAIRY',
            'NINETALES': 'VULPIX',
            'WIGGLYTUFF': 'JIGGLYPUFF',
            'GOLBAT': 'ZUBAT',
            'VILEPLUME': 'GLOOM',
            'PARASECT': 'PARAS',
            'VENOMOTH': 'VENONAT',
            'DUGTRIO': 'DIGLETT',
            'PERSIAN': 'MEOWTH',
            'GOLDUCK': 'PSYDUCK',
            'PRIMEAPE': 'MANKEY',
            'ARCANINE': 'GROWLITHE',
            'POLIWRATH': 'POLIWHIRL',
            'ALAKAZAM': 'KADABRA',
            'MACHAMP': 'MACHOKE',
            'VICTREEBEL': 'WEEPINBELL',
            'TENTACRUEL': 'TENTACOOL',
            'GOLEM': 'GRAVELER',
            'RAPIDASH': 'PONYTA',
            'SLOWBRO': 'SLOWPOKE',
            'MAGNETON': 'MAGNEMITE',
            'DODRIO': 'DODUO',
            'DEWGONG': 'SEEL',
            'MUK': 'GRIMER',
            'CLOYSTER': 'SHELLDER',
            'GENGAR': 'HAUNTER',
            'HYPNO': 'DROWZEE',
            'KINGLER': 'KRABBY',
            'ELECTRODE': 'VOLTORB',
            'EXEGGUTOR': 'EXEGGCUTE',
            'MAROWAK': 'CUBONE',
            'WEEZING': 'KOFFING',
            'RHYDON': 'RHYHORN',
            'KANGASKHAN': 'KANGASKHAN',  # No evolution
            'SEAKING': 'GOLDEEN',
            'STARMIE': 'STARYU',
            'MR_MIME': 'MR_MIME',  # No evolution in Gen 1-4
            'SCYTHER': 'SCYTHER',  # No evolution in Gen 1
            'JYNX': 'JYNX',  # No evolution
            'ELECTABUZZ': 'ELECTABUZZ',  # No evolution in Gen 1-3
            'MAGMAR': 'MAGMAR',  # No evolution in Gen 1-3
            'PINSIR': 'PINSIR',  # No evolution
            'TAUROS': 'TAUROS',  # No evolution
            'GYARADOS': 'MAGIKARP',
            'LAPRAS': 'LAPRAS',  # No evolution
            'DITTO': 'DITTO',  # No evolution
            'VAPOREON': 'EEVEE',
            'JOLTEON': 'EEVEE',
            'FLAREON': 'EEVEE',
            'OMASTAR': 'OMANYTE',
            'KABUTOPS': 'KABUTO',
            'AERODACTYL': 'AERODACTYL',  # No evolution
            'SNORLAX': 'SNORLAX',  # No evolution in Gen 1-3
            'DRAGONITE': 'DRAGONAIR'
        }
        
        if name1 in evolution_pairs and evolution_pairs[name1] == name2:
            return True
        
        return False
    
    def populate_pokemon_dropdown(self):
        """Populate the Pokemon dropdown"""
        self.pokemon_dropdown.clear()
        
        # Add empty option as first item
        self.pokemon_dropdown.addItem("Select a Pokemon", None)
        
        # Check if we should filter for fully evolved Pokémon only
        show_fully_evolved_only = self.show_fully_evolved_only.isChecked()
        
        # Add Pokémon to the dropdown based on filter settings
        pokemon_added = 0
        
        for species_name in self.pokemon_list:
            # Skip if we're only showing fully evolved Pokémon and this one isn't fully evolved
            if show_fully_evolved_only and hasattr(self, 'fully_evolved_pokemon') and species_name not in self.fully_evolved_pokemon:
                continue
                
            # Make sure this species has valid data
            if species_name in self.all_pokemon_data and 'name' in self.all_pokemon_data[species_name]:
                display_name = self.all_pokemon_data[species_name]['name']
                # Store the species name as the item data
                self.pokemon_dropdown.addItem(display_name, species_name)
                pokemon_added += 1
            else:
                # For species without display names, just show the internal name
                formatted_name = species_name.replace('SPECIES_', '').replace('_', ' ').title()
                self.pokemon_dropdown.addItem(formatted_name, species_name)
                pokemon_added += 1
                
        print(f"Added {pokemon_added} Pokémon to dropdown" + " (fully evolved only)" if show_fully_evolved_only else "")
    
    def on_pokemon_selected(self, index):
        """Handle selection of a Pokemon from the dropdown"""
        # Get the selected Pokemon
        self.current_pokemon = self.pokemon_dropdown.itemData(index)
        display_name = self.pokemon_dropdown.itemText(index)
        
        # Print debug information
        if self.current_pokemon is None:
            print(f"Selected Pokemon: None (Select a Pokemon)")
        else:
            print(f"Selected Pokemon: {self.current_pokemon} ({display_name})")
        
        # Clear current moves and ability
        self.clear_current_moves()
        self.current_ability = None
        
        # Populate the move dropdowns and ability dropdown
        self.populate_move_dropdowns(self.current_pokemon)
        self.populate_ability_dropdown(self.current_pokemon)
        
        # Reset move slots
        self.reset_moveset_display()
    
    def clear_current_moves(self):
        """Clear the current moves"""
        self.current_moves = [None, None, None, None]
        self.current_move_names = [None, None, None, None]
        
        # Update the display
        self.reset_moveset_display()
        
    def populate_ability_dropdown(self, species_name):
        """Populate the ability dropdown based on selected Pokemon"""
        # Clear the dropdown first
        self.ability_dropdown.clear()
        
        # Get abilities for the selected Pokemon
        abilities = self.get_abilities_for_pokemon(species_name)
        
        if not abilities:
            # No abilities found, add a default option
            print(f"No abilities found for {species_name}, using default ability")
            self.ability_dropdown.addItem("Limber", "ABILITY_LIMBER")
            return
        
        # Add abilities to dropdown
        print(f"Adding {len(abilities)} abilities for {species_name}: {', '.join(abilities)}")
        for ability in abilities:
            # Convert ability name from format like ABILITY_OVERGROW to "Overgrow"
            display_name = ability.replace('ABILITY_', '').replace('_', ' ').title()
            self.ability_dropdown.addItem(display_name, ability)  # Store original ability ID as item data
            
        # Select the first ability by default
        if self.ability_dropdown.count() > 0:
            self.ability_dropdown.setCurrentIndex(0)
            self.current_ability = self.ability_dropdown.currentData()
    
    def on_ability_selected(self, index):
        """Handle selection of an ability from the dropdown"""
        if index < 0:
            return
        
        # Get the selected ability
        ability = self.ability_dropdown.currentData()
        ability_name = self.ability_dropdown.currentText()
        
        # Update the current ability
        self.current_ability = ability
        
        print(f"Selected ability: {ability} ({ability_name})")
    
    def get_abilities_for_pokemon(self, species_name):
        """Get a list of possible abilities for a Pokémon
        
        This function retrieves the abilities for the specified Pokémon.
        It checks our abilities dictionary and returns a list of abilities.
        If no abilities are found, it returns a default list based on Pokémon type.
        """
        # Check if we have abilities for this Pokémon in our dictionary
        if species_name in self.pokemon_abilities and self.pokemon_abilities[species_name]:
            print(f"Found abilities for {species_name}: {', '.join(self.pokemon_abilities[species_name])}")
            return self.pokemon_abilities[species_name]
            
        # If the species doesn't exist in our abilities dictionary, return default abilities
        # based on the Pokémon's type if available
        if species_name in self.all_pokemon_data:
            type1 = self.all_pokemon_data[species_name].get('type1', '')
            print(f"No abilities found for {species_name}, using default based on type: {type1}")
            
            # Assign default abilities based on type
            if type1 == 'NORMAL':
                return ['ABILITY_RUN_AWAY', 'ABILITY_LIMBER']
            elif type1 == 'FIRE':
                return ['ABILITY_BLAZE', 'ABILITY_FLASH_FIRE']
            elif type1 == 'WATER':
                return ['ABILITY_TORRENT', 'ABILITY_WATER_ABSORB']
            elif type1 == 'GRASS':
                return ['ABILITY_OVERGROW', 'ABILITY_CHLOROPHYLL']
            elif type1 == 'ELECTRIC':
                return ['ABILITY_STATIC', 'ABILITY_LIGHTNING_ROD']
            elif type1 == 'ICE':
                return ['ABILITY_ICE_BODY', 'ABILITY_SNOW_CLOAK']
            elif type1 == 'FIGHTING':
                return ['ABILITY_GUTS', 'ABILITY_INNER_FOCUS']
            elif type1 == 'POISON':
                return ['ABILITY_POISON_POINT', 'ABILITY_LIQUID_OOZE']
            elif type1 == 'GROUND':
                return ['ABILITY_SAND_VEIL', 'ABILITY_ARENA_TRAP']
            elif type1 == 'FLYING':
                return ['ABILITY_KEEN_EYE', 'ABILITY_BIG_PECKS']
            elif type1 == 'PSYCHIC':
                return ['ABILITY_SYNCHRONIZE', 'ABILITY_MAGIC_GUARD']
            elif type1 == 'BUG':
                return ['ABILITY_SWARM', 'ABILITY_COMPOUND_EYES']
            elif type1 == 'ROCK':
                return ['ABILITY_ROCK_HEAD', 'ABILITY_STURDY']
            elif type1 == 'GHOST':
                return ['ABILITY_LEVITATE', 'ABILITY_CURSED_BODY']
            elif type1 == 'DRAGON':
                return ['ABILITY_INTIMIDATE', 'ABILITY_MULTISCALE']
            elif type1 == 'DARK':
                return ['ABILITY_INTIMIDATE', 'ABILITY_MOXIE']
            elif type1 == 'STEEL':
                return ['ABILITY_CLEAR_BODY', 'ABILITY_STURDY']
            elif type1 == 'FAIRY':
                return ['ABILITY_CUTE_CHARM', 'ABILITY_MAGIC_GUARD']
            else:
                # Generic fallback
                return ['ABILITY_LIMBER', 'ABILITY_KEEN_EYE']
        
        # If nothing else works, return a generic ability
        print(f"No abilities or type data found for {species_name}, using generic abilities")
        return ['ABILITY_LIMBER', 'ABILITY_KEEN_EYE']
    
    def on_move_selected(self, index, slot, dropdown_type):
        """Handle move selection from any dropdown
        
        Args:
            index: The index of the selected item in the dropdown
            slot: Which move slot (0-3) this selection is for
            dropdown_type: Which type of dropdown ('level_up', 'egg', 'tm', 'tutor')
        """
        # Get the correct dropdown list based on type and slot
        if dropdown_type == 'level_up':
            dropdown = self.level_up_dropdowns[slot]
        elif dropdown_type == 'egg':
            dropdown = self.egg_dropdowns[slot]
        elif dropdown_type == 'tm':
            dropdown = self.tm_dropdowns[slot]
        elif dropdown_type == 'tutor':
            dropdown = self.tutor_dropdowns[slot]
        else:
            return  # Invalid dropdown type
        
        # Skip if nothing is selected or first item ("Select a move") is selected
        if index <= 0:
            # Clear this move slot
            self.current_moves[slot] = None
            self.current_move_names[slot] = None
            self.move_displays[slot].setText("No Move Selected")
            return
        
        # Get the selected move
        move_data = dropdown.itemData(index)
        move_name = dropdown.itemText(index)
        
        # Store the selected move in our current set
        self.current_moves[slot] = move_data
        self.current_move_names[slot] = move_name
        
        # Update the move display
        self.move_displays[slot].setText(move_name)
        
        # Output what happened
        print(f"Selected {move_name} ({move_data}) for Move Slot {slot+1}")
        
        # Clear the other dropdowns on this tab to prevent multiple selections
        self.clear_other_dropdowns(slot, dropdown_type)
    
    def clear_other_dropdowns(self, slot, selected_type):
        """Clear other dropdowns on the same tab to prevent multiple selections"""
        if selected_type != 'level_up':
            self.level_up_dropdowns[slot].setCurrentIndex(0)
        if selected_type != 'egg':
            self.egg_dropdowns[slot].setCurrentIndex(0)
        if selected_type != 'tm':
            self.tm_dropdowns[slot].setCurrentIndex(0)
        if selected_type != 'tutor':
            self.tutor_dropdowns[slot].setCurrentIndex(0)
    
    def reset_moveset_display(self):
        """Reset the moveset display when a new Pokemon is selected"""
        for i in range(4):
            self.current_moves[i] = None
            self.current_move_names[i] = None
            self.move_displays[i].setText("No Move Selected")
    
    def clear_move_dropdowns(self):
        """Clear all move dropdowns across all tabs"""
        # Clear level-up dropdowns
        for dropdown in self.level_up_dropdowns:
            dropdown.clear()
        
        # Clear egg dropdowns
        for dropdown in self.egg_dropdowns:
            dropdown.clear()
        
        # Clear TM dropdowns
        for dropdown in self.tm_dropdowns:
            dropdown.clear()
        
        # Clear tutor dropdowns
        for dropdown in self.tutor_dropdowns:
            dropdown.clear()
    
    def populate_move_dropdowns(self, species_name):
        """Populate all move dropdowns across all tabs for the selected Pokemon"""
        # Clear all dropdowns first
        self.clear_move_dropdowns()
        
        print(f"Populating moves for {species_name}")
        
        # Get all the available moves for this Pokemon
        level_up_moves = []
        egg_moves = []
        tm_moves = []
        tutor_moves = []
        
        # Level-up moves
        if species_name in self.move_lists['level_up']:
            level_up_moves = sorted(self.move_lists['level_up'][species_name])
            print(f"Found {len(level_up_moves)} level-up moves for {species_name}")
        else:
            print(f"No level-up moves found for {species_name}")
        
        # Egg moves - use the base form's egg moves
        base_form = self.base_forms.get(species_name, species_name)
        if base_form in self.move_lists['egg']:
            egg_moves = sorted(self.move_lists['egg'][base_form])
            print(f"Found {len(egg_moves)} egg moves for {species_name}'s base form ({base_form})")
        else:
            print(f"No egg moves found for {species_name}'s base form ({base_form})")
        
        # TM moves
        if species_name in self.move_lists['tm']:
            tm_moves = sorted(self.move_lists['tm'][species_name])
            print(f"Found {len(tm_moves)} TM moves for {species_name}")
        else:
            print(f"No TM moves found for {species_name}")
        
        # Tutor moves
        if species_name in self.move_lists['tutor']:
            tutor_moves = sorted(self.move_lists['tutor'][species_name])
            print(f"Found {len(tutor_moves)} tutor moves for {species_name}")
        else:
            print(f"No tutor moves found for {species_name}")
        
        # Populate all the dropdowns across all tabs
        for i in range(4):  # For each of the 4 tabs
            # Add "Select a move" as the first item for each dropdown
            self.level_up_dropdowns[i].addItem("Select a move", None)
            self.egg_dropdowns[i].addItem("Select a move", None)
            self.tm_dropdowns[i].addItem("Select a move", None)
            self.tutor_dropdowns[i].addItem("Select a move", None)
            
            # Add level-up moves
            for move in level_up_moves:
                display_name = self.format_move_name(move)
                self.level_up_dropdowns[i].addItem(display_name, move)
            
            # Add egg moves
            for move in egg_moves:
                display_name = self.format_move_name(move)
                self.egg_dropdowns[i].addItem(display_name, move)
            
            # Add TM moves
            for move in tm_moves:
                display_name = self.format_move_name(move)
                self.tm_dropdowns[i].addItem(display_name, move)
            
            # Add tutor moves
            for move in tutor_moves:
                display_name = self.format_move_name(move)
                self.tutor_dropdowns[i].addItem(display_name, move)
    
    def format_move_name(self, move_name):
        """Format the move name from MOVE_NAME to Name format"""
        if not move_name.startswith('MOVE_'):
            return move_name
        
        return move_name[5:].replace('_', ' ').title()
    
    def save_pokemon_set(self):
        """Save the current Pokemon set"""
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
        
        # Add all the selected moves
        for i, move in enumerate(self.current_moves):
            if move:  # If there's a move in this slot
                # Determine the source of this move
                source = 'unknown'
                if move in self.move_lists['level_up'].get(self.current_pokemon, []):
                    source = 'level_up'
                elif move in self.move_lists['egg'].get(self.base_forms.get(self.current_pokemon, self.current_pokemon), []):
                    source = 'egg'
                elif move in self.move_lists['tm'].get(self.current_pokemon, []):
                    source = 'tm'
                elif move in self.move_lists['tutor'].get(self.current_pokemon, []):
                    source = 'tutor'
                
                # Add move to our set
                pokemon_set['moves'].append({
                    'name': move,
                    'source': source,
                    'display_name': self.current_move_names[i],
                    'slot': i+1  # 1-based slot number
                })
        
        # Save to file
        self.save_to_file(pokemon_set)
    
    def save_to_file(self, pokemon_set):
        """Save the Pokemon set to a collection file organized by generation and alphabetically"""
        try:
            # Create sets directory structure if it doesn't exist
            base_dir = os.path.dirname(os.path.abspath(__file__))
            sets_dir = os.path.join(base_dir, 'pokemon_sets')
            collections_dir = os.path.join(sets_dir, 'collections')
            randomizer_dir = os.path.join(base_dir, 'trainer_randomizer', 'sets')
            
            # Create all necessary directories
            os.makedirs(sets_dir, exist_ok=True)
            os.makedirs(collections_dir, exist_ok=True)
            os.makedirs(randomizer_dir, exist_ok=True)
            
            # Get current timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Determine which generation the Pokémon belongs to
            generation = self.get_pokemon_generation(pokemon_set['species'])
            
            # Create the simplified randomizer-friendly format
            move_list = []
            for move in pokemon_set['moves']:
                if move['name']:
                    move_list.append(move['name'])
            
            # Prepare the set data with timestamp
            set_data = {
                'species': pokemon_set['species'],
                'name': pokemon_set['name'],
                'moves': pokemon_set['moves'],
                'ability': pokemon_set.get('ability', {}),
                'generation': generation,
                'timestamp': timestamp
            }
            
            # Simplified set for randomizer
            randomizer_set = {
                'species': pokemon_set['species'],
                'moves': move_list,
                'ability': pokemon_set.get('ability', {}).get('name', None),
                'display_name': pokemon_set['name'],
                'generated_by': 'pokemon_set_builder',
                'timestamp': timestamp
            }
            
            # Collection filename based on generation
            collection_filename = f"gen{generation}_pokemon.json"
            collection_filepath = os.path.join(collections_dir, collection_filename)
            
            # Save or update the collection file
            self.update_collection_file(collection_filepath, set_data)
            
            # Update the randomizer collection as well
            randomizer_collection_filepath = os.path.join(randomizer_dir, f"randomizer_gen{generation}.json")
            self.update_randomizer_collection(randomizer_collection_filepath, randomizer_set)
            
            # Also save individual file for backup/reference
            pokemon_name = pokemon_set['name'].replace(' ', '_')
            individual_filepath = os.path.join(sets_dir, f"{pokemon_name}_{timestamp}.json")
            with open(individual_filepath, 'w') as f:
                json.dump(set_data, f, indent=4)
            
            QMessageBox.information(self, "Success", 
                f"Pokemon set saved to:\n- Collection: {collection_filepath}\n- Randomizer: {randomizer_collection_filepath}\n\nSets are organized by generation and alphabetically within each collection.")
            
        except Exception as e:
            error_msg = f"Failed to save Pokemon set: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)

    def get_pokemon_generation(self, species_name):
        """Determine which generation a Pokémon belongs to based on its species name/ID"""
        try:
            # Extract numeric ID if available
            species_id = None
            if species_name.isdigit():
                species_id = int(species_name)
            else:
                # Try to extract numeric ID from the species name (e.g., SPECIES_XXX)
                import re
                match = re.search(r'SPECIES_(\d+)', species_name)
                if match:
                    species_id = int(match.group(1))
            
            # Determine generation based on Pokémon ID ranges
            if species_id is not None:
                if 1 <= species_id <= 151:  # Gen 1: Bulbasaur to Mew
                    return 1
                elif 152 <= species_id <= 251:  # Gen 2: Chikorita to Celebi
                    return 2
                elif 252 <= species_id <= 386:  # Gen 3: Treecko to Deoxys
                    return 3
                elif 387 <= species_id <= 493:  # Gen 4: Turtwig to Arceus
                    return 4
                elif 494 <= species_id <= 649:  # Gen 5: Victini to Genesect
                    return 5
                elif 650 <= species_id <= 721:  # Gen 6: Chespin to Volcanion
                    return 6
                elif 722 <= species_id <= 809:  # Gen 7: Rowlet to Melmetal
                    return 7
                elif 810 <= species_id <= 905:  # Gen 8: Grookey to Enamorus
                    return 8
                elif 906 <= species_id <= 1025:  # Gen 9: Sprigatito to Pecharunt
                    return 9
                else:
                    return 9  # Default to the latest generation for unknown IDs
            
            # If ID couldn't be determined, use name-based approach
            gen1_starters = ['BULBASAUR', 'CHARMANDER', 'SQUIRTLE']
            gen2_starters = ['CHIKORITA', 'CYNDAQUIL', 'TOTODILE']
            gen3_starters = ['TREECKO', 'TORCHIC', 'MUDKIP']
            gen4_starters = ['TURTWIG', 'CHIMCHAR', 'PIPLUP']
            gen5_starters = ['SNIVY', 'TEPIG', 'OSHAWOTT']
            gen6_starters = ['CHESPIN', 'FENNEKIN', 'FROAKIE']
            gen7_starters = ['ROWLET', 'LITTEN', 'POPPLIO']
            gen8_starters = ['GROOKEY', 'SCORBUNNY', 'SOBBLE']
            gen9_starters = ['SPRIGATITO', 'FUECOCO', 'QUAXLY']
            
            species_simple = species_name.replace('SPECIES_', '').upper()
            
            for starter in gen1_starters:
                if starter in species_simple:
                    return 1
            for starter in gen2_starters:
                if starter in species_simple:
                    return 2
            for starter in gen3_starters:
                if starter in species_simple:
                    return 3
            for starter in gen4_starters:
                if starter in species_simple:
                    return 4
            for starter in gen5_starters:
                if starter in species_simple:
                    return 5
            for starter in gen6_starters:
                if starter in species_simple:
                    return 6
            for starter in gen7_starters:
                if starter in species_simple:
                    return 7
            for starter in gen8_starters:
                if starter in species_simple:
                    return 8
            for starter in gen9_starters:
                if starter in species_simple:
                    return 9
                
            # Default to Gen 1 if we couldn't determine the generation
            return 1
            
        except Exception as e:
            print(f"Error determining Pokémon generation: {str(e)}")
            return 1  # Default to Gen 1 for safety
    
    def update_collection_file(self, filepath, set_data):
        """Update a collection file with a new Pokémon set, organizing alphabetically"""
        try:
            # Initialize collection data structure
            collection = {
                'generation': set_data.get('generation', 1),
                'last_updated': set_data.get('timestamp', ''),
                'sets': []
            }
            
            # Load existing collection if available
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    try:
                        existing_collection = json.load(f)
                        if 'sets' in existing_collection:
                            collection['sets'] = existing_collection['sets']
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse existing collection file {filepath}. Creating new file.")
            
            # Check if this Pokémon already exists in the collection
            species_name = set_data['species']
            found = False
            
            for i, existing_set in enumerate(collection['sets']):
                if existing_set.get('species') == species_name:
                    # Replace the existing set with the new one
                    collection['sets'][i] = set_data
                    found = True
                    break
            
            # If not found, add the new set
            if not found:
                collection['sets'].append(set_data)
            
            # Sort sets alphabetically by Pokémon name
            collection['sets'] = sorted(collection['sets'], key=lambda x: x.get('name', ''))
            
            # Update the last_updated timestamp
            collection['last_updated'] = set_data.get('timestamp', '')
            
            # Save the updated collection
            with open(filepath, 'w') as f:
                json.dump(collection, f, indent=4)
                
        except Exception as e:
            print(f"Error updating collection file: {str(e)}")
            raise
    
    def update_randomizer_collection(self, filepath, set_data):
        """Update a randomizer collection file with a new Pokémon set"""
        try:
            # Initialize collection data structure
            collection = {
                'last_updated': set_data.get('timestamp', ''),
                'sets': []
            }
            
            # Load existing collection if available
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    try:
                        existing_collection = json.load(f)
                        if 'sets' in existing_collection:
                            collection['sets'] = existing_collection['sets']
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse existing randomizer collection file {filepath}. Creating new file.")
            
            # Check if this Pokémon already exists in the collection
            species_name = set_data['species']
            found = False
            
            for i, existing_set in enumerate(collection['sets']):
                if existing_set.get('species') == species_name:
                    # Replace the existing set with the new one
                    collection['sets'][i] = set_data
                    found = True
                    break
            
            # If not found, add the new set
            if not found:
                collection['sets'].append(set_data)
            
            # Sort sets alphabetically by Pokémon display name
            collection['sets'] = sorted(collection['sets'], key=lambda x: x.get('display_name', ''))
            
            # Update the last_updated timestamp
            collection['last_updated'] = set_data.get('timestamp', '')
            
            # Save the updated collection
            with open(filepath, 'w') as f:
                json.dump(collection, f, indent=4)
                
        except Exception as e:
            print(f"Error updating randomizer collection file: {str(e)}")
            raise


if __name__ == '__main__':
    try:
        print("Starting Pokemon Set Builder")
        print(f"Current working directory: {os.getcwd()}")
        app = QApplication(sys.argv)
        window = PokemonSetBuilder()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
