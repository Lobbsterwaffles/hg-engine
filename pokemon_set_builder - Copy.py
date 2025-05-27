import sys
import os
import json
import traceback
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QComboBox, QPushButton, QLabel, 
                           QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt

class PokemonSetBuilder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = "Pokemon Set Builder"
        self.setWindowTitle(self.title)
        self.resize(600, 500)
        
        # Initialize data structures
        self.all_pokemon_data = {}
        self.move_lists = {
            'level_up': {},
            'egg': {},
            'tm': {},
            'tutor': {}
        }
        self.pokemon_list = []
        self.base_forms = {}  # Maps Pokemon to their base forms
        
        # Initialize UI
        self.init_ui()
        
        # Load data
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
        
        # Pokemon selection section
        pokemon_group = QGroupBox("Select Pokemon")
        pokemon_layout = QVBoxLayout()
        
        # Pokemon dropdown
        self.pokemon_label = QLabel("Fully Evolved, Non-Legendary Pokemon:")
        self.pokemon_dropdown = QComboBox()
        self.pokemon_dropdown.setMinimumWidth(200)
        self.pokemon_dropdown.currentIndexChanged.connect(self.on_pokemon_selected)
        
        pokemon_layout.addWidget(self.pokemon_label)
        pokemon_layout.addWidget(self.pokemon_dropdown)
        pokemon_group.setLayout(pokemon_layout)
        
        # Move selection section
        moves_group = QGroupBox("Select Moves")
        moves_layout = QVBoxLayout()
        
        # Level-up moves
        self.level_up_label = QLabel("Level-up Moves:")
        self.level_up_dropdown = QComboBox()
        self.level_up_dropdown.setMinimumWidth(200)
        
        # Egg moves
        self.egg_label = QLabel("Egg Moves:")
        self.egg_dropdown = QComboBox()
        self.egg_dropdown.setMinimumWidth(200)
        
        # TM moves
        self.tm_label = QLabel("TM Moves:")
        self.tm_dropdown = QComboBox()
        self.tm_dropdown.setMinimumWidth(200)
        
        # Tutor moves
        self.tutor_label = QLabel("Tutor Moves:")
        self.tutor_dropdown = QComboBox()
        self.tutor_dropdown.setMinimumWidth(200)
        
        moves_layout.addWidget(self.level_up_label)
        moves_layout.addWidget(self.level_up_dropdown)
        moves_layout.addWidget(self.egg_label)
        moves_layout.addWidget(self.egg_dropdown)
        moves_layout.addWidget(self.tm_label)
        moves_layout.addWidget(self.tm_dropdown)
        moves_layout.addWidget(self.tutor_label)
        moves_layout.addWidget(self.tutor_dropdown)
        
        moves_group.setLayout(moves_layout)
        
        # Save button
        self.save_button = QPushButton("Save Pokemon Set")
        self.save_button.clicked.connect(self.save_pokemon_set)
        
        # Add widgets to main layout
        main_layout.addWidget(pokemon_group)
        main_layout.addWidget(moves_group)
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
            
            # Parse evodata.s for evolution data
            evo_file = os.path.join(base_dir, 'armips', 'data', 'evodata.s')
            print(f"Evolution file path: {evo_file}")
            if not os.path.exists(evo_file):
                print(f"WARNING: Evolution file does not exist at {evo_file}")
            else:
                self.parse_evolution_file(evo_file)
            
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
    
    def determine_fully_evolved_non_legendary(self):
        """Determine which Pokemon are fully evolved and non-legendary"""
        print("Starting to determine fully evolved, non-legendary Pokemon...")
        
        # First, build a more accurate evolution tree based on the level-up data
        # A Pokemon that appears in the levelup data is a valid Pokemon to consider
        valid_pokemon = set(self.move_lists['level_up'].keys())
        print(f"Found {len(valid_pokemon)} Pokemon with level-up moves.")
        
        # This more comprehensive list contains all known fully evolved Pokemon
        fully_evolved_species = [
            # Gen 1
            'SPECIES_VENUSAUR', 'SPECIES_CHARIZARD', 'SPECIES_BLASTOISE', 'SPECIES_BUTTERFREE', 
            'SPECIES_BEEDRILL', 'SPECIES_PIDGEOT', 'SPECIES_RATICATE', 'SPECIES_FEAROW', 
            'SPECIES_ARBOK', 'SPECIES_RAICHU', 'SPECIES_SANDSLASH', 'SPECIES_NIDOQUEEN', 
            'SPECIES_NIDOKING', 'SPECIES_CLEFABLE', 'SPECIES_NINETALES', 'SPECIES_WIGGLYTUFF', 
            'SPECIES_VILEPLUME', 'SPECIES_PARASECT', 'SPECIES_VENOMOTH', 'SPECIES_DUGTRIO', 
            'SPECIES_PERSIAN', 'SPECIES_GOLDUCK', 'SPECIES_PRIMEAPE', 'SPECIES_ARCANINE', 
            'SPECIES_POLIWRATH', 'SPECIES_ALAKAZAM', 'SPECIES_MACHAMP', 'SPECIES_VICTREEBEL', 
            'SPECIES_TENTACRUEL', 'SPECIES_GOLEM', 'SPECIES_RAPIDASH', 'SPECIES_SLOWBRO', 
            'SPECIES_MAGNETON', 'SPECIES_FARFETCHD', 'SPECIES_DODRIO', 'SPECIES_DEWGONG', 
            'SPECIES_MUK', 'SPECIES_CLOYSTER', 'SPECIES_GENGAR', 'SPECIES_ONIX', 
            'SPECIES_HYPNO', 'SPECIES_KINGLER', 'SPECIES_ELECTRODE', 'SPECIES_EXEGGUTOR', 
            'SPECIES_MAROWAK', 'SPECIES_HITMONLEE', 'SPECIES_HITMONCHAN', 'SPECIES_LICKITUNG', 
            'SPECIES_WEEZING', 'SPECIES_RHYDON', 'SPECIES_CHANSEY', 'SPECIES_TANGELA', 
            'SPECIES_KANGASKHAN', 'SPECIES_SEAKING', 'SPECIES_STARMIE', 'SPECIES_MR_MIME', 
            'SPECIES_SCYTHER', 'SPECIES_JYNX', 'SPECIES_ELECTABUZZ', 'SPECIES_MAGMAR', 
            'SPECIES_PINSIR', 'SPECIES_TAUROS', 'SPECIES_GYARADOS', 'SPECIES_LAPRAS', 
            'SPECIES_DITTO', 'SPECIES_VAPOREON', 'SPECIES_JOLTEON', 'SPECIES_FLAREON', 
            'SPECIES_PORYGON', 'SPECIES_OMASTAR', 'SPECIES_KABUTOPS', 'SPECIES_AERODACTYL', 
            'SPECIES_SNORLAX', 'SPECIES_DRAGONITE',
            # Gen 2
            'SPECIES_MEGANIUM', 'SPECIES_TYPHLOSION', 'SPECIES_FERALIGATR', 'SPECIES_FURRET', 
            'SPECIES_NOCTOWL', 'SPECIES_LEDIAN', 'SPECIES_ARIADOS', 'SPECIES_CROBAT', 
            'SPECIES_LANTURN', 'SPECIES_TOGETIC', 'SPECIES_XATU', 'SPECIES_AMPHAROS', 
            'SPECIES_BELLOSSOM', 'SPECIES_AZUMARILL', 'SPECIES_SUDOWOODO', 'SPECIES_POLITOED', 
            'SPECIES_JUMPLUFF', 'SPECIES_AIPOM', 'SPECIES_SUNFLORA', 'SPECIES_QUAGSIRE', 
            'SPECIES_ESPEON', 'SPECIES_UMBREON', 'SPECIES_SLOWKING', 'SPECIES_UNOWN', 
            'SPECIES_WOBBUFFET', 'SPECIES_GIRAFARIG', 'SPECIES_FORRETRESS', 'SPECIES_DUNSPARCE', 
            'SPECIES_GLIGAR', 'SPECIES_STEELIX', 'SPECIES_GRANBULL', 'SPECIES_QWILFISH', 
            'SPECIES_SCIZOR', 'SPECIES_SHUCKLE', 'SPECIES_HERACROSS', 'SPECIES_SNEASEL', 
            'SPECIES_URSARING', 'SPECIES_MAGCARGO', 'SPECIES_CORSOLA', 'SPECIES_OCTILLERY', 
            'SPECIES_DELIBIRD', 'SPECIES_MANTINE', 'SPECIES_SKARMORY', 'SPECIES_HOUNDOOM', 
            'SPECIES_KINGDRA', 'SPECIES_DONPHAN', 'SPECIES_PORYGON2', 'SPECIES_STANTLER', 
            'SPECIES_SMEARGLE', 'SPECIES_HITMONTOP', 'SPECIES_MILTANK', 'SPECIES_BLISSEY',
            # Gen 3+
            'SPECIES_SCEPTILE', 'SPECIES_BLAZIKEN', 'SPECIES_SWAMPERT'
        ]
        
        # Create a set for faster lookups
        fully_evolved_set = set(fully_evolved_species)
        
        # Filter for fully evolved, non-legendary Pokemon
        fully_evolved = []
        for species_name in valid_pokemon:
            # Skip if not in our Pokemon data (might be a variant or form)
            if species_name not in self.all_pokemon_data:
                continue
                
            # Skip legendaries and special forms
            data = self.all_pokemon_data[species_name]
            if (data['is_legendary'] or 
                '_FORM' in species_name or 
                '_MEGA' in species_name or 
                'ALOLAN' in species_name or 
                'GALARIAN' in species_name or
                'HISUIAN' in species_name or
                '_REGIONAL' in species_name or
                '_START' in species_name or
                '_DIFFERENCE' in species_name):
                continue
            
            # Add if it's in our fully evolved list
            if species_name in fully_evolved_set:
                fully_evolved.append(species_name)
        
        self.pokemon_list = sorted(fully_evolved, key=lambda x: self.all_pokemon_data[x]['id'])
        print(f"Found {len(fully_evolved)} fully evolved, non-legendary Pokemon.")
    
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
        """Populate the Pokemon dropdown with fully evolved, non-legendary Pokemon"""
        self.pokemon_dropdown.clear()
        
        # Add "Select a Pokemon" as the first item
        self.pokemon_dropdown.addItem("Select a Pokemon", None)
        
        # Add each Pokemon to the dropdown
        for species_name in self.pokemon_list:
            display_name = self.all_pokemon_data[species_name]['name']
            self.pokemon_dropdown.addItem(display_name, species_name)
    
    def on_pokemon_selected(self, index):
        """Handle Pokemon selection from dropdown"""
        if index <= 0:
            # Clear all move dropdowns
            self.clear_move_dropdowns()
            self.current_pokemon = None
            return
        
        # Get the selected Pokemon
        species_name = self.pokemon_dropdown.itemData(index)
        self.current_pokemon = species_name
        
        print(f"Selected Pokemon: {species_name} ({self.all_pokemon_data[species_name]['name']})")
        
        # Populate move dropdowns
        self.populate_move_dropdowns(species_name)
    
    def clear_move_dropdowns(self):
        """Clear all move dropdowns"""
        self.level_up_dropdown.clear()
        self.egg_dropdown.clear()
        self.tm_dropdown.clear()
        self.tutor_dropdown.clear()
    
    def populate_move_dropdowns(self, species_name):
        """Populate all move dropdowns for the selected Pokemon"""
        # Clear all dropdowns first
        self.clear_move_dropdowns()
        
        # Add "Select a move" as the first item for each dropdown
        self.level_up_dropdown.addItem("Select a move", None)
        self.egg_dropdown.addItem("Select a move", None)
        self.tm_dropdown.addItem("Select a move", None)
        self.tutor_dropdown.addItem("Select a move", None)
        
        print(f"Populating moves for {species_name}")
        
        # Level-up moves
        if species_name in self.move_lists['level_up']:
            moves = self.move_lists['level_up'][species_name]
            print(f"Found {len(moves)} level-up moves for {species_name}")
            for move in sorted(moves):
                display_name = self.format_move_name(move)
                self.level_up_dropdown.addItem(display_name, move)
        else:
            print(f"No level-up moves found for {species_name}")
        
        # Egg moves - use the base form's egg moves
        base_form = self.base_forms.get(species_name, species_name)
        if base_form in self.move_lists['egg']:
            moves = self.move_lists['egg'][base_form]
            print(f"Found {len(moves)} egg moves for {species_name}'s base form ({base_form})")
            for move in sorted(moves):
                display_name = self.format_move_name(move)
                self.egg_dropdown.addItem(display_name, move)
        else:
            print(f"No egg moves found for {species_name}'s base form ({base_form})")
        
        # TM moves
        if species_name in self.move_lists['tm']:
            moves = self.move_lists['tm'][species_name]
            print(f"Found {len(moves)} TM moves for {species_name}")
            for move in sorted(moves):
                display_name = self.format_move_name(move)
                self.tm_dropdown.addItem(display_name, move)
        else:
            print(f"No TM moves found for {species_name}")
        
        # Tutor moves
        if species_name in self.move_lists['tutor']:
            moves = self.move_lists['tutor'][species_name]
            print(f"Found {len(moves)} tutor moves for {species_name}")
            for move in sorted(moves):
                display_name = self.format_move_name(move)
                self.tutor_dropdown.addItem(display_name, move)
        else:
            print(f"No tutor moves found for {species_name}")


        
        # Tutor moves
        if species_name in self.move_lists['tutor']:
            moves = self.move_lists['tutor'][species_name]
            print(f"Found {len(moves)} tutor moves for {species_name}")
            for move in sorted(moves):
                display_name = self.format_move_name(move)
                self.tutor_dropdown.addItem(display_name, move)
        else:
            print(f"No tutor moves found for {species_name}")
    
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
        
        # Get selected moves
        level_up_move = self.level_up_dropdown.currentData()
        egg_move = self.egg_dropdown.currentData()
        tm_move = self.tm_dropdown.currentData()
        tutor_move = self.tutor_dropdown.currentData()
        
        # Check if at least one move is selected
        if not any([level_up_move, egg_move, tm_move, tutor_move]):
            QMessageBox.warning(self, "Warning", "Please select at least one move.")
            return
        
        # Create the Pokemon set data
        pokemon_set = {
            'species': self.current_pokemon,
            'name': self.all_pokemon_data[self.current_pokemon]['name'],
            'moves': []
        }
        
        # Add selected moves
        if level_up_move:
            pokemon_set['moves'].append({
                'name': level_up_move,
                'source': 'level_up',
                'display_name': self.format_move_name(level_up_move)
            })
        
        if egg_move:
            pokemon_set['moves'].append({
                'name': egg_move,
                'source': 'egg',
                'display_name': self.format_move_name(egg_move)
            })
        
        if tm_move:
            pokemon_set['moves'].append({
                'name': tm_move,
                'source': 'tm',
                'display_name': self.format_move_name(tm_move)
            })
        
        if tutor_move:
            pokemon_set['moves'].append({
                'name': tutor_move,
                'source': 'tutor',
                'display_name': self.format_move_name(tutor_move)
            })
        
        # Save to file
        self.save_to_file(pokemon_set)
    
    def save_to_file(self, pokemon_set):
        """Save the Pokemon set to a file"""
        try:
            # Create sets directory if it doesn't exist
            sets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pokemon_sets')
            os.makedirs(sets_dir, exist_ok=True)
            
            # Generate a unique filename
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{pokemon_set['name'].replace(' ', '_')}_{timestamp}.json"
            filepath = os.path.join(sets_dir, filename)
            
            # Save the data
            with open(filepath, 'w') as f:
                json.dump(pokemon_set, f, indent=4)
            
            QMessageBox.information(self, "Success", f"Pokemon set saved to {filepath}")
            
        except Exception as e:
            error_msg = f"Failed to save Pokemon set: {str(e)}"
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)


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
