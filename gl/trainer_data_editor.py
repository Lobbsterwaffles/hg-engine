"""
Move selection logic for Pokemon ROM randomization.

This module contains classes and logic for determining appropriate movesets
for trainer Pokemon based on various criteria like attacker type, level, etc.
"""

from framework import Extractor, Step
from steps import Mons, Moves, EggMoves, Levelups, TMHM, TrainerData, IdentifyTier, LoadPokemonNamesStep, LoadAbilityNames, LoadMoveNamesStep, Trainers, IdentifyBosses
from extractors import MachineLearnsets
from enums import Split, Tier
import json
import os
import glob
import random
import itertools


#############
# If Lunatone, a Rock/Psychic type Pokemon is in the party, it will start out with the last 4 moves it learned at its current
# level (piss). We want it to have a good damaging move of both Rock and Psychic. The other two moves it has will be
# 2 of the last 4 moves it would have learned at its current level.
#############



class IdentifyAttackerCategory(Extractor):
    """Categorizes Pokemon as Physical, Special, or Mixed attackers based on base stats."""
    
    def __init__(self, context):
        super().__init__(context)
        mons = context.get(Mons)
        
        self.data = {}
        
        # Categorize each Pokemon based on Attack vs Special Attack
        for pokemon in mons.data:
            if pokemon.name:  # Skip invalid Pokemon entries
                category = self._categorize_attacker(pokemon.attack, pokemon.sp_attack)
                self.data[pokemon.pokemon_id] = {
                    'name': pokemon.name,
                    'attack': pokemon.attack,
                    'sp_attack': pokemon.sp_attack,
                    'category': category
                }
    
    def _categorize_attacker(self, attack, sp_attack):
        """Categorize Pokemon as Physical, Special, or Mixed attacker.
        
        Args:
            attack (int): Physical Attack stat
            sp_attack (int): Special Attack stat
            
        Returns:
            str: 'Physical', 'Special', or 'Mixed'
        """
        # Calculate the difference as a percentage of the higher stat
        if attack > sp_attack:
            diff_percent = (attack - sp_attack) / attack * 100
            if diff_percent > 10:
                return 'Physical'
            else:
                return 'Mixed'
        elif sp_attack > attack:
            diff_percent = (sp_attack - attack) / sp_attack * 100
            if diff_percent > 10:
                return 'Special'
            else:
                return 'Mixed'
        else:
            # Equal stats
            return 'Mixed'
    
    def get_category(self, pokemon_id):
        """Get the attacker category for a Pokemon by ID.
        
        Args:
            pokemon_id (int): Pokemon species ID
            
        Returns:
            str: 'Physical', 'Special', 'Mixed', or 'Unknown'
        """
        return self.data.get(pokemon_id, {}).get('category', 'Unknown')
    
    def get_physical_attackers(self):
        """Get all Pokemon categorized as Physical attackers."""
        return {pid: data for pid, data in self.data.items() if data['category'] == 'Physical'}
    
    def get_special_attackers(self):
        """Get all Pokemon categorized as Special attackers."""
        return {pid: data for pid, data in self.data.items() if data['category'] == 'Special'}
    
    def get_mixed_attackers(self):
        """Get all Pokemon categorized as Mixed attackers."""
        return {pid: data for pid, data in self.data.items() if data['category'] == 'Mixed'}


class MoveList(Extractor):
    """Base class for move lists with common functionality."""
    
    move_names = []  # Override in subclasses
    
    def __init__(self, context):
        super().__init__(context)
        self.moves_set = set()
        moves = context.get(Moves)
        self.move_name_to_id = {move.name.lower(): move.move_id for move in moves.data if move.name}
        
        # Add all moves from class attribute to the set
        for move_name in self.move_names:
            self.moves_set.add(self.move_name_to_id[move_name.lower()])
    
    def contains(self, move_id):
        """Check if a move is in this list."""
        return move_id in self.moves_set


class MoveBlacklist(MoveList):
    """List of moves that should never be selected."""
    
    move_names = [
        "Focus Punch", "Feint", "Snore", "Dream Eater", "Razor Wind", "Electro Shot", "Meteor Beam", "Skull Bash", 
        "Sky Attack", "Sky Drop", "Solar Beam", "Solar Blade", "Spit Up", "Synchronoise", "Future Sight", "Belch",
        "Fake Out", "Last Resort", "Spit Up", "Swallow", 
    ]
    
    def is_blacklisted(self, move_id):
        """Check if a move is blacklisted."""
        return self.contains(move_id)


class MoveWhitelist(MoveList):
    """List of moves that should always be considered good."""
    
    move_names = [
        # Add moves you want to always consider good here
        "Double Hit", "Double Kick", "Dragon Darts", "Bonemerang", "Dual Chop", "Dual Wingbeat", "Gear Grind", "Surging Strikes", 
        "Tachyon Cutter", "Triple Dive", "Twin Beam", "Water Shuriken", "Bone Rush", "Bullet Seed", "Icicle Spear", 
        "Pin Missile", "Rock Blast", "Scale Shot", "Tail Slap", "Water Spout", "Eruption",      
    ]
    
    def is_whitelisted(self, move_id):
        """Check if a move is whitelisted."""
        return self.contains(move_id)


class FindStabMoves(Extractor):
    """Extractor that finds STAB moves for Pokemon using a tiered priority system."""
    
    def __init__(self, context):
        super().__init__(context)
        self.moves = context.get(Moves)
        self.levelups = context.get(Levelups)
        self.machine_learnsets = context.get(MachineLearnsets)
        self.tmhm = context.get(TMHM)
        self.egg_moves = context.get(EggMoves)
        self.mons = context.get(Mons)
        self.blacklist = context.get(MoveBlacklist)
        self.whitelist = context.get(MoveWhitelist)
        
        # Initialize good moves set
        self.good_moves = set()
        for move in self.moves.data:
            if move.move_id and move.name and self._is_good_move(move):
                self.good_moves.add(move.move_id)
    
    def _is_good_move(self, move):
        if self.whitelist.is_whitelisted(move.move_id):
            return True
        if self.blacklist.is_blacklisted(move.move_id):
            return False
        return 50 <= move.base_power <= 81 and move.accuracy > 79
    
    def is_good_move(self, move_id):
        return move_id in self.good_moves
    
    def calculate_estimated_power(self, pokemon_id, move_id):
        if pokemon_id >= len(self.mons.data) or move_id >= len(self.moves.data):
            return 0
        pokemon = self.mons[pokemon_id]
        move = self.moves.data[move_id]
        if not move.base_power:
            return 0
        if move.pss == Split.PHYSICAL:
            return move.base_power * pokemon.attack
        elif move.pss == Split.SPECIAL:
            return move.base_power * pokemon.sp_attack
        return 0
    
    def get_best_moves_for_pokemon(self, pokemon_id, available_move_ids, count=4):
        move_powers = [(move_id, self.calculate_estimated_power(pokemon_id, move_id)) for move_id in available_move_ids]
        move_powers.sort(key=lambda x: x[1], reverse=True)
        return [move_id for move_id, power in move_powers[:count]]
    
    def _shuffle_generator(self, gen):
        moves = list(gen)
        random.shuffle(moves)
        yield from moves
    
    def get_stab_moves(self, species_id, level, move_type):
        def levelup_stab():
            if species_id < len(self.levelups.data):
                pokemon_learnset = self.levelups.data[species_id]
                for entry in pokemon_learnset:
                    if (entry.level <= level and entry.move and 
                        entry.move.type == move_type and 
                        self.is_good_move(entry.move_id)):
                        yield entry.move_id
        
        def egg_stab():
            if species_id in self.egg_moves.data:
                for egg_move_entry in self.egg_moves.data[species_id]:
                    move = egg_move_entry['move']
                    if (move and move.type == move_type and 
                        self.is_good_move(egg_move_entry['move_id'])):
                        yield egg_move_entry['move_id']
        
        def tm_stab():
            learnable_tms = self.machine_learnsets.get_learnable_tms(species_id)
            for tm_num in learnable_tms:
                tm_move = self.tmhm.get_move_for_tm(tm_num, self.moves)
                if (tm_move and tm_move.type == move_type and 
                    self.is_good_move(tm_move.move_id)):
                    yield tm_move.move_id
        
        def hm_stab():
            learnable_hms = self.machine_learnsets.get_learnable_hms(species_id)
            for hm_num in learnable_hms:
                hm_move = self.tmhm.get_move_for_hm(hm_num, self.moves)
                if (hm_move and hm_move.type == move_type and 
                    self.is_good_move(hm_move.move_id)):
                    yield hm_move.move_id
        
        def best_levelup():
            if species_id < len(self.levelups.data):
                pokemon_learnset = self.levelups.data[species_id]
                available_moves = []
                for entry in pokemon_learnset:
                    if (entry.level <= level and entry.move and 
                        self.is_good_move(entry.move_id)):
                        available_moves.append(entry.move_id)
                
                if available_moves:
                    best_moves = self.get_best_moves_for_pokemon(species_id, available_moves, len(available_moves))
                    yield from best_moves
        
        return itertools.chain(
            self._shuffle_generator(levelup_stab()),
            self._shuffle_generator(egg_stab()),
            self._shuffle_generator(tm_stab()),
            self._shuffle_generator(hm_stab()),
            self._shuffle_generator(best_levelup())
        )



class CustomSetReader(Extractor):
    """Reads competitive Pokemon sets from individual JSON files.
    
    This class can locate and read a Pokemon's custom competitive set
    from the pokemon_sets directory, converting move names to internal IDs.
    """
    
    def __init__(self, context):
        super().__init__(context)
        self.moves = context.get(Moves)
        self.mons = context.get(Mons)
        self.ability_names = context.get(LoadAbilityNames)
        
        # Build lookup tables for efficient conversion
        self.move_name_to_id = {move.name: move.move_id for move in self.moves.data if move.name}
        self.ability_name_to_id = {name: ability_id for ability_id, name in self.ability_names.id_to_name.items()}
        # Note: Pokemon data structure uses 'name' field, not 'species_name'
        
        # Set the base directory for Pokemon sets
        self.pokemon_sets_dir = os.path.join(os.path.dirname(__file__), '..', 'pokemon_sets')
        
        print(f"CustomSetReader initialized with {len(self.move_name_to_id)} moves and {len(self.ability_name_to_id)} abilities")
    
    def find_pokemon_json_file(self, pokemon_id):
        """Find the JSON file for a given Pokemon ID.
        
        Args:
            pokemon_id (int): Pokemon species ID
            
        Returns:
            str: Path to JSON file, or None if not found
        """
        # Get the Pokemon's species name
        pokemon = next((mon for mon in self.mons.data if mon.pokemon_id == pokemon_id), None)
        if not pokemon or not pokemon.name:
            return None
        
        pokemon_name = pokemon.name
        
        # Search for JSON files matching this Pokemon
        # Pattern: PokemonName_timestamp.json
        pattern = os.path.join(self.pokemon_sets_dir, f"{pokemon_name}_*.json")
        matching_files = glob.glob(pattern)
        
        if not matching_files:
            # Try alternative patterns (spaces, hyphens, etc.)
            alt_patterns = [
                f"{pokemon_name.replace(' ', '_')}_*.json",
                f"{pokemon_name.replace('-', '_')}_*.json",
                f"{pokemon_name.replace(' ', '')}_*.json"
            ]
            
            for alt_pattern in alt_patterns:
                alt_path = os.path.join(self.pokemon_sets_dir, alt_pattern)
                matching_files = glob.glob(alt_path)
                if matching_files:
                    break
        
        if not matching_files:
            return None
        
        # If multiple files found, use the newest one (by filename timestamp)
        return max(matching_files)
    
    def read_custom_set(self, pokemon_id):
        """Read a Pokemon's custom competitive set from JSON.
        
        Args:
            pokemon_id (int): Pokemon species ID
            
        Returns:
            dict: Custom set data with move IDs, or None if not found
            {
                'species_id': int,
                'name': str,
                'moves': [{'move_id': int, 'slot': int, 'source': str}, ...],
                'ability_name': str,
                'filename': str
            }
        """
        json_file = self.find_pokemon_json_file(pokemon_id)
        if not json_file:
            return None
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            if not all(field in data for field in ['species', 'name', 'moves', 'ability']):
                print(f"Warning: Invalid JSON structure in {os.path.basename(json_file)}")
                return None
            
            # Convert moves from display names to IDs
            converted_moves = []
            for move_data in data['moves']:
                display_name = move_data.get('display_name', '')
                move_id = self._find_move_by_display_name(display_name, os.path.basename(json_file))
                
                if move_id is not None:
                    converted_moves.append({
                        'move_id': move_id,
                        'slot': move_data.get('slot', len(converted_moves) + 1),
                        'source': move_data.get('source', 'unknown'),
                        'display_name': display_name
                    })
            
            # Convert ability from name to ID
            ability_name = data['ability'].get('name', '')
            ability_id = self._find_ability_by_name(ability_name, os.path.basename(json_file))
            
            return {
                'species_id': pokemon_id,
                'name': data['name'],
                'moves': converted_moves,
                'ability_name': ability_name,
                'ability_id': ability_id,
                'filename': os.path.basename(json_file)
            }
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading {os.path.basename(json_file)}: {e}")
            return None
    
    def has_custom_set(self, pokemon_id):
        """Check if a Pokemon has a custom set available.
        
        Args:
            pokemon_id (int): Pokemon species ID
            
        Returns:
            bool: True if custom set is available
        """
        return self.find_pokemon_json_file(pokemon_id) is not None
    
    def _find_move_by_display_name(self, display_name, filename):
        """Find a move by its display name, with edit distance fallback.
        
        Args:
            display_name (str): Display name from JSON (e.g., 'Leech Seed')
            filename (str): JSON filename for error reporting
            
        Returns:
            int: Move ID, or None if not found
        """
        if not display_name:
            return None
        
        # Try exact match first (case-sensitive)
        if display_name in self.move_name_to_id:
            return self.move_name_to_id[display_name]
        
        # Try case-insensitive match
        display_name_lower = display_name.lower()
        for rom_name, move_id in self.move_name_to_id.items():
            if rom_name and rom_name.lower() == display_name_lower:
                return move_id
        
        # Move not found - find closest match by edit distance
        closest_match = self._find_closest_move_name(display_name)
        print(f"Warning: Unknown move '{display_name}' in {filename}")
        if closest_match:
            print(f"  Closest match: '{closest_match[0]}' (edit distance: {closest_match[1]})")
        
        return None
    
    def _find_closest_move_name(self, target_name):
        """Find the closest move name by edit distance.
        
        Args:
            target_name (str): Target move name to find closest match for
            
        Returns:
            tuple: (closest_name, edit_distance) or None if no moves available
        """
        if not target_name:
            return None
        
        min_distance = float('inf')
        closest_name = None
        
        # Check all known move names
        for rom_name in self.move_name_to_id.keys():
            if rom_name and rom_name != '-':  # Skip empty/invalid names
                distance = self._edit_distance(target_name.lower(), rom_name.lower())
                if distance < min_distance:
                    min_distance = distance
                    closest_name = rom_name
        
        return (closest_name, min_distance) if closest_name else None
    
    def _edit_distance(self, s1, s2):
        """Calculate Levenshtein edit distance between two strings.
        
        Args:
            s1 (str): First string
            s2 (str): Second string
            
        Returns:
            int: Edit distance
        """
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _find_ability_by_name(self, ability_name, filename):
        """Find an ability by its name.
        
        Args:
            ability_name (str): Ability name from JSON (e.g., 'ABILITY_HYDRATION')
            filename (str): JSON filename for error reporting
            
        Returns:
            int: Ability ID, or None if not found
        """
        if not ability_name:
            return None
        
        # Try exact match first
        if ability_name in self.ability_name_to_id:
            return self.ability_name_to_id[ability_name]
        
        # Try without ABILITY_ prefix if present
        if ability_name.startswith('ABILITY_'):
            clean_name = ability_name[8:]  # Remove 'ABILITY_' prefix
            
            # Try direct match with clean name
            if clean_name in self.ability_name_to_id:
                return self.ability_name_to_id[clean_name]
            
            # Try converting underscores to spaces and proper case
            formatted_name = clean_name.replace('_', ' ').title()
            if formatted_name in self.ability_name_to_id:
                return self.ability_name_to_id[formatted_name]
            
            # Try converting underscores to nothing (CompoundEyes style)
            no_underscore_name = clean_name.replace('_', '').title()
            if no_underscore_name in self.ability_name_to_id:
                return self.ability_name_to_id[no_underscore_name]
        
        print(f"Warning: Ability '{ability_name}' not found in {filename}")
        return None


class AssignCustomSetsStep(Step):
    """Pipeline step to assign Pokemon their custom competitive sets.
    
    This step reads Pokemon's custom sets from JSON and assigns the moves
    to replace current movesets. This is separate from STAB move logic
    and provides complete competitive movesets.
    """
    
    def __init__(self, mode="all"):
        """Initialize the AssignCustomSets step.
        
        Args:
            mode (str): "all" to apply to all trainers with custom sets,
                       "late_game_bosses" to apply only to EndGame tier bosses
        """
        # Step classes don't need to call super().__init__()
        # Context will be provided during run()
        
        if mode not in ["all", "late_game_bosses"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'all' or 'late_game_bosses'")
        
        self.mode = mode
        
        # Track assignment statistics
        self.assignments_made = 0
        self.sets_not_found = 0
        self.assignment_log = []
        self.missing_sets = set()  # Track Pokemon species without custom sets
        
    def run(self, context):
        """Run the step to assign custom sets to trainer Pokemon.
        
        Args:
            context (RandomizationContext): Randomization context
        """
        # Get required extractors from context
        self.custom_sets = context.get(CustomSetReader)
        self.moves = context.get(Moves)
        trainers = context.get(Trainers)
        
        # Get filtering data based on mode
        if self.mode == "late_game_bosses":
            tier_data = context.get(IdentifyTier)
            boss_data = context.get(IdentifyBosses)
            
            # Create a set of boss trainer IDs for quick lookup
            boss_trainer_ids = set()
            for boss_category in boss_data.data.values():
                for trainer in boss_category.trainers:
                    boss_trainer_ids.add(trainer.info.trainer_id)
            
            print(f"AssignCustomSetsStep: Assigning custom sets to EndGame tier bosses only...")
        else:
            print(f"AssignCustomSetsStep: Assigning custom sets to all trainer Pokemon...")
        
        # Process trainers based on mode
        for trainer_id, trainer in enumerate(trainers.data):
            # Check if we should process this trainer based on mode
            if self.mode == "late_game_bosses":
                # Only process if trainer is both a boss AND in end game tier
                trainer_tier = tier_data.data.get(trainer_id)
                is_boss = trainer_id in boss_trainer_ids
                
                if not (is_boss and trainer_tier == Tier.END_GAME):
                    continue
                
                # Print trainer name when we identify an end game boss
                trainer_name = getattr(trainer.info, 'name', f'Trainer {trainer_id}')
                print(f"  Processing EndGame boss: {trainer_name} (ID: {trainer_id})")
            
            # Process each Pokemon in trainer's team
            for pokemon in trainer.team:
                # Try to assign a custom set if the pokemon has a species_id
                if hasattr(pokemon, 'species_id') and pokemon.species_id:
                    current_moves = [getattr(pokemon, f'move{i}', None) for i in range(1, 5)]
                    custom_set = self.custom_sets.read_custom_set(pokemon.species_id)
                    
                    if custom_set:
                        # Apply moves from custom set
                        new_moves = self.assign_custom_set_to_pokemon(pokemon.species_id, current_moves)
                        if new_moves:
                            for i, move_id in enumerate(new_moves):
                                if move_id is not None:
                                    setattr(pokemon, f'move{i+1}', move_id)
                        
                        # Apply ability from custom set if available
                        if custom_set.get('ability_id') is not None:
                            # Set ability slot to 3 (hidden ability slot) to use the custom ability
                            pokemon.abilityslot = 3
                            # Note: The actual ability ID will be looked up from the hidden ability table
                            # This is handled by the game engine based on the ability slot
        
        # Print summary
        mode_desc = "EndGame tier bosses" if self.mode == "late_game_bosses" else "all trainers"
        print(f"AssignCustomSetsStep: Completed {self.assignments_made} assignments to {mode_desc}, {self.sets_not_found} sets not found")
        
        # Print Pokemon species that don't have custom sets
        if self.missing_sets:
            print(f"Pokemon species without custom sets:")
            mons = context.get(Mons)
            for species_id in sorted(self.missing_sets):
                if species_id < len(mons.data):
                    pokemon_name = mons[species_id].name
                    print(f"  Species {species_id}: {pokemon_name}")
                else:
                    print(f"  Species {species_id}: Unknown")
    
    def assign_custom_set_to_pokemon(self, pokemon_id, current_moves=None):
        """Assign a custom set to a Pokemon.
        
        Args:
            pokemon_id (int): Pokemon species ID
            current_moves (list): Current move IDs (optional, for logging)
            
        Returns:
            list: List of new move IDs, or None if no custom set available
        """
        custom_set = self.custom_sets.read_custom_set(pokemon_id)
        
        if not custom_set:
            self.sets_not_found += 1
            self.missing_sets.add(pokemon_id)  # Track this species as missing a custom set
            return None
        
        # Extract move IDs from custom set
        new_moves = [move['move_id'] for move in custom_set['moves']]
        
        # Pad with None if fewer than 4 moves (for special cases like Ditto)
        while len(new_moves) < 4:
            new_moves.append(None)
        
        # Log the assignment
        self.assignments_made += 1
        log_entry = {
            'pokemon_name': custom_set['name'],
            'filename': custom_set['filename'],
            'old_moves': current_moves or [],
            'new_moves': new_moves,
            'move_count': len([m for m in new_moves if m is not None])
        }
        self.assignment_log.append(log_entry)
        
        print(f"Assigned custom set to {custom_set['name']}: {len([m for m in new_moves if m is not None])} moves from {custom_set['filename']}")
        
        return new_moves
    
    def get_assignment_summary(self):
        """Get a summary of all custom set assignments made.
        
        Returns:
            dict: Summary statistics and log
        """
        return {
            'assignments_made': self.assignments_made,
            'sets_not_found': self.sets_not_found,
            'assignment_log': self.assignment_log
        }


class AddStabMovesStep(Step):
    """Step that adds STAB moves to trainer Pokemon teams.
    
    Only applies to trainers in MID_GAME, LATE_GAME, END_GAME, and POST_GAME tiers.
    EARLY_GAME trainers are skipped.
    """
    
    def __init__(self):
        super().__init__()
        self.processed_trainers = 0
        
    def run(self, context):
        trainers = context.get(Trainers)
        mons = context.get(Mons)
        stab_finder = context.get(FindStabMoves)
        tier_data = context.get(IdentifyTier)
        
        # Tiers that should receive STAB moves
        allowed_tiers = {Tier.EARLY_GAME, Tier.MID_GAME, Tier.LATE_GAME, Tier.END_GAME, Tier.POST_GAME}
        
        print(f"Adding STAB moves to trainer teams (MID_GAME+ tiers only)...")
        
        for trainer_id, trainer in enumerate(trainers.data):
            # Filter by tier - only process MID_GAME and above
            trainer_tier = tier_data.data.get(trainer_id)
            if trainer_tier not in allowed_tiers:
                continue
                
            print(f"Processing trainer: {trainer.info.name} (Tier: {trainer_tier.name})")
            self.processed_trainers += 1
            
            for entry in trainer.team:
                pokemon = mons[entry.species_id]
                new_moves = []
                for t in set([pokemon.type1, pokemon.type2]):
                    has_good_stab = any(move and stab_finder.moves.data[move].type == t and 
                                      stab_finder.is_good_move(move) for move in entry.moves if move)
                    if not has_good_stab:
                        try:
                            new_moves.append(next(stab_finder.get_stab_moves(entry.species_id, entry.level, t)))
                        except StopIteration:
                            pass
                

                if new_moves:
                    old_move_ids = [move for move in entry.moves if move]
                    random.shuffle(old_move_ids)
                    final_move_ids = (new_moves + old_move_ids)[:4]
                    entry.moves[:] = (final_move_ids + [0] * 4)[:4]
                    
                    move_names = [stab_finder.moves.data[move_id].name for move_id in new_moves]
                    print(f"  {pokemon.name} (Lv{entry.level}): Added STAB moves: {', '.join(move_names)}")
        
        print(f"STAB moves step completed. Processed {self.processed_trainers} trainers.")
        return context



