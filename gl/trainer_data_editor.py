"""
Move Naelection logic for Pokemon ROM randomization.

This module contains classes and logic for determining appropriate movesets
for trainer Pokemon based on various criteria like attacker type, level, etc.
"""

from framework import Extractor, Step
from steps import Mons, Moves, EggMoves, Learnsets, TMHM, TrainerData, IdentifyTier, LoadPokemonNamesStep, LoadAbilityNames, LoadMoveNamesStep, Trainers, IdentifyBosses
from extractors import EvioliteUser
from enums import Split, Item, Type, Tier
from TypeEffectiveness import sup_eff, get_4x_weaknesses
from Trainer_mon_Classifier import TrainerMonClassifier
import json
import os
import glob
import random


#############
# Foe Pokemon Movesets
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
        self.move_name_to_id = {move.name: move.move_id for move in moves.data if move.name}
        
        # Add all moves from class attribute to the set
        for move_name in self.move_names:
            self.add_move_by_name(move_name)
    
    def add_move_by_name(self, move_name):
        """Add a move to this list by name."""
        for name, move_id in self.move_name_to_id.items():
            if name and name.lower() == move_name.lower():
                self.moves_set.add(move_id)
                return
    
    def contains(self, move_id):
        """Check if a move is in this list."""
        return move_id in self.moves_set


class MoveBlacklist(MoveList):
    """List of moves that should never be selected."""
    
    move_names = [
        "Focus Punch", "Feint", "Snore", "Dream Eater", "Razor Wind", "Electro Shot", "Meteor Beam", "Skull Bash", 
        "Sky Attack", "Sky Drop", "Solar Beam", "Solar Blade", "Spit Up", "Synchronoise", "Future Sight", "Belch",
        "First Impression", "Fake Out", "Last Resort", 
    ]
    
    def is_blacklisted(self, move_id):
        """Check if a move is blacklisted."""
        return self.contains(move_id)


class MoveWhitelist(MoveList):
    """List of moves that should always be considered good."""
    
    move_names = [
        # Add moves you want to always consider good here
        " Double Hit", "Double Kick", "Dragon Darts", "Bonemerang", "Dual Chop", "Dual Wingbeat", "Gear Grind", "Surging Strikes", 
        "Tachyon Cutter", "Triple Dive", "Twin Beam", "Water Shuriken", "Bone Rush", "Bullet Seed", "Icicle Spear", 
        "Pin Missile", "Rock Blast", "Scale Shot", "Tail Slap",        
    ]
    
    def is_whitelisted(self, move_id):
        """Check if a move is whitelisted."""
        return self.contains(move_id)


class IdentifyGoodMoves(Extractor):
    """Identifies moves that are considered 'good' based on specific criteria."""
    
    def __init__(self, context):
        super().__init__(context)
        moves = context.get(Moves)
        blacklist = context.get(MoveBlacklist)
        whitelist = context.get(MoveWhitelist)
        
        self.good_moves = set()
        
        # Analyze each move to determine if it's 'good'
        for move in moves.data:
            if move.move_id and move.name:  # Skip invalid moves
                if self._is_good_move(move, blacklist, whitelist):
                    self.good_moves.add(move.move_id)
    
    def _is_good_move(self, move, blacklist, whitelist):
        """Determine if a move is 'good' based on the criteria.
        
        A good move is:
        1) On the whitelist, OR
        2) Has base power 50-81, accuracy >79%, and not blacklisted
        """
        # Check if whitelisted (always good)
        if whitelist.is_whitelisted(move.move_id):
            return True
        
        # Check if blacklisted (never good)
        if blacklist.is_blacklisted(move.move_id):
            return False
        
        # Check power and accuracy criteria
        if (50 <= move.base_power <= 81 and move.accuracy > 79):
            return True
        
        return False
    
    def is_good_move(self, move_id):
        """Check if a move is considered 'good'."""
        return move_id in self.good_moves
    
    def is_good_move_no_power_limit(self, move_id):
        """Check if a move is 'good' using relaxed criteria (no upper power limit).
        
        This variant follows the same logic as is_good_move but removes the upper
        power limit (81), allowing powerful moves to be considered 'good' for
        preservation purposes.
        
        Args:
            move_id (int): Move ID to check
            
        Returns:
            bool: True if move meets relaxed good move criteria
        """
        if not move_id or move_id >= len(self.context.get(Moves).data):
            return False
        
        move = self.context.get(Moves).data[move_id]
        if not move or not move.name:
            return False
        
        blacklist = self.context.get(MoveBlacklist)
        whitelist = self.context.get(MoveWhitelist)
        
        # Check if whitelisted (always good)
        if whitelist.is_whitelisted(move_id):
            return True
        
        # Check if blacklisted (never good)
        if blacklist.is_blacklisted(move_id):
            return False
        
        # Relaxed criteria: base power >= 50 (no upper limit), accuracy >79%
        if (move.base_power >= 50 and move.accuracy > 79):
            return True
        
        return False
    
    def get_good_moves(self):
        """Get all move IDs that are considered good."""
        return self.good_moves.copy()


class FindEstPower(Extractor):
    """Calculates estimated power for moves based on Pokemon's offensive stats."""
    
    def __init__(self, context):
        super().__init__(context)
        self.moves = context.get(Moves)
        self.mons = context.get(Mons)
    
    def calculate_estimated_power(self, pokemon_id, move_id):
        """Calculate estimated power for a specific Pokemon using a specific move.
        
        Args:
            pokemon_id (int): Pokemon species ID
            move_id (int): Move ID
            
        Returns:
            int: Estimated power (base_power × relevant offensive stat)
        """
        # Get Pokemon and move data
        if pokemon_id >= len(self.mons.data) or move_id >= len(self.moves.data):
            return 0
        
        pokemon = self.mons[pokemon_id]
        move = self.moves.data[move_id]
        
        # If move has no base power, return 0
        if not move.base_power:
            return 0
        
        # Determine which offensive stat to use based on move's split
        if move.pss == Split.PHYSICAL:
            offensive_stat = pokemon.attack
        elif move.pss == Split.SPECIAL:
            offensive_stat = pokemon.sp_attack
        else:
            # Status moves or unknown split - return 0
            return 0
        
        # Calculate estimated power
        estimated_power = move.base_power * offensive_stat
        return estimated_power
    
    def get_best_moves_for_pokemon(self, pokemon_id, available_move_ids, count=4):
        """Get the best moves for a Pokemon based on estimated power.
        
        Args:
            pokemon_id (int): Pokemon species ID
            available_move_ids (list): List of move IDs to choose from
            count (int): Number of moves to return (default 4)
            
        Returns:
            list: List of move IDs sorted by estimated power (highest first)
        """
        # Calculate estimated power for each available move
        move_powers = []
        for move_id in available_move_ids:
            power = self.calculate_estimated_power(pokemon_id, move_id)
            move_powers.append((move_id, power))
        
        # Sort by estimated power (highest first)
        move_powers.sort(key=lambda x: x[1], reverse=True)
        
        # Return the top moves
        return [move_id for move_id, power in move_powers[:count]]


class GetAllAvailableMoves(Extractor):
    def __init__(self, context):
        super().__init__(context)
        self.learnsets = context.get(Learnsets)
        self.egg_moves = context.get(EggMoves)
        self.mons = context.get(Mons)
        self.tmhm = context.get(TMHM)
    
    def get_all_moves(self, pokemon_id, max_level=100):
        """Get all available moves (level-up + egg moves + TM/HM moves)."""
        if pokemon_id >= len(self.learnsets.data):
            return []
        
        # Level-up moves - handle both list and dict structures
        learnset = self.learnsets.data[pokemon_id]
        level_moves = [entry.move_id for entry in learnset if entry.level <= max_level]
        
        # Egg moves
        egg_moves = self.egg_moves.get_egg_move_ids(pokemon_id)
        
        # TM/HM moves - get moves this Pokemon can learn
        tm_hm_moves = []
        if pokemon_id < len(self.mons.data):
            pokemon = self.mons[pokemon_id]
            
            # Check TM compatibility (TM001-TM092)
            for tm_num in range(1, 93):  # TM001 to TM092
                if pokemon.tm[tm_num]:  # Can learn this TM
                    tm_move = self.tmhm.tm[tm_num]
                    if tm_move and hasattr(tm_move, 'move_id'):
                        tm_hm_moves.append(tm_move.move_id)
            
            # Check HM compatibility (HM001-HM008)
            for hm_num in range(1, 9):  # HM001 to HM008
                if pokemon.hm[hm_num]:  # Can learn this HM
                    hm_move = self.tmhm.hm[hm_num]
                    if hm_move and hasattr(hm_move, 'move_id'):
                        tm_hm_moves.append(hm_move.move_id)
        
        # Combine and remove duplicates
        return list(set(level_moves + egg_moves + tm_hm_moves))


class FindDamagingStab(Extractor):
    """Finds the best damaging STAB move for a Pokemon using tier-based selection.
    
    Tier 1: On-type GoodMove from level-up learnset (at or below current level)
    Tier 2: On-type GoodMove from egg moves
    Tier 3: On-type GoodMove from TM learnset
    Tier 4: On-type GoodMove from HM learnset
    Tier 5: Highest EstPower GoodMove from level-up learnset (at or below current level)
    """
    
    def __init__(self, context):
        super().__init__(context)
        self.mons = context.get(Mons)
        self.moves = context.get(Moves)
        self.learnsets = context.get(Learnsets)
        self.egg_moves = context.get(EggMoves)
        self.tmhm = context.get(TMHM)
        self.attacker_categories = context.get(IdentifyAttackerCategory)
        self.good_moves = context.get(IdentifyGoodMoves)
        self.est_power = context.get(FindEstPower)
    
    def find_stab_move(self, pokemon_id, current_level, current_moves=None):
        """Find the best STAB move for a Pokemon using tier-based selection.
        
        Args:
            pokemon_id (int): Pokemon species ID
            current_level (int): Pokemon's current level
            current_moves (list): List of current move IDs (optional)
            
        Returns:
            int: Move ID of selected STAB move, or None if no suitable move found or already has good STAB
        """
        import random
        
        if pokemon_id >= len(self.mons.data):
            return None
            
        pokemon = self.mons[pokemon_id]
        is_dual_type = pokemon.type2 != pokemon.type1
        
        # For dual-type Pokemon, use enhanced dual-type logic
        if is_dual_type and current_moves:
            return self._find_dual_type_stab_moves(pokemon_id, current_level, current_moves)
        
        # For single-type Pokemon or when no current moves provided, use original logic
        pokemon_types = [pokemon.type1]
        if is_dual_type:
            pokemon_types.append(pokemon.type2)
        
        # First, check if Pokemon already has a good STAB move
        if current_moves and self._has_good_stab_move(current_moves, pokemon_types):
            return None  # Already has good STAB, no replacement needed
        
        # Tier 1: On-type GoodMove from level-up learnset (at or below current level)
        tier1_moves = self._get_level_up_stab_moves(pokemon_id, current_level, pokemon_types)
        if tier1_moves:
            return random.choice(tier1_moves)
        
        # Tier 2: On-type GoodMove from egg moves
        tier2_moves = self._get_egg_stab_moves(pokemon_id, pokemon_types)
        if tier2_moves:
            return random.choice(tier2_moves)
        
        # Tier 3: On-type GoodMove from TM learnset
        tier3_moves = self._get_tm_stab_moves(pokemon_id, pokemon_types)
        if tier3_moves:
            return random.choice(tier3_moves)
        
        # Tier 4: On-type GoodMove from HM learnset
        tier4_moves = self._get_hm_stab_moves(pokemon_id, pokemon_types)
        if tier4_moves:
            return random.choice(tier4_moves)
        
        # Tier 5: Highest EstPower GoodMove from level-up learnset
        tier5_move = self._get_best_power_move(pokemon_id, current_level)
        if tier5_move:
            return tier5_move
        
        return None
    
    def _get_level_up_stab_moves(self, pokemon_id, current_level, pokemon_types):
        """Get on-type good moves from level-up learnset at or below current level."""
        if pokemon_id >= len(self.learnsets.data):
            return []
        
        learnset = self.learnsets.data[pokemon_id]
        stab_moves = []
        
        for entry in learnset:
            if (entry.level <= current_level and 
                self.good_moves.is_good_move(entry.move_id)):
                
                move = self.moves.data[entry.move_id] if entry.move_id < len(self.moves.data) else None
                if (move and move.type in pokemon_types and move.base_power > 0 and
                    self._move_matches_attacker_category(move, pokemon_id)):
                    stab_moves.append(entry.move_id)
        
        return stab_moves
    
    def _get_egg_stab_moves(self, pokemon_id, pokemon_types):
        """Get on-type good moves from egg moves."""
        stab_moves = []
        
        # Get egg moves for this Pokemon species
        if pokemon_id in self.egg_moves.data:
            egg_moves = self.egg_moves.data[pokemon_id]
            for egg_move in egg_moves:
                move_id = egg_move['move_id']
                move = self.moves.data[move_id] if move_id < len(self.moves.data) else None
                if (move and self.good_moves.is_good_move(move_id) and 
                    move.type in pokemon_types and move.base_power > 0 and
                    self._move_matches_attacker_category(move, pokemon_id)):
                    stab_moves.append(move_id)
        
        return stab_moves
    
    def _get_tm_stab_moves(self, pokemon_id, pokemon_types):
        """Get on-type good moves from TM learnset."""
        if pokemon_id >= len(self.mons.data):
            return []
        
        pokemon = self.mons[pokemon_id]
        stab_moves = []
        
        # Check TM compatibility (TM001-TM092)
        for tm_num in range(1, 93):  # TM001 to TM092
            if pokemon.tm[tm_num]:  # Can learn this TM
                tm_move = self.tmhm.tm[tm_num]
                if tm_move and hasattr(tm_move, 'move_id'):
                    move = self.moves.data[tm_move.move_id] if tm_move.move_id < len(self.moves.data) else None
                    if (move and self.good_moves.is_good_move(tm_move.move_id) and 
                        move.type in pokemon_types and move.base_power > 0 and
                        self._move_matches_attacker_category(move, pokemon_id)):
                        stab_moves.append(tm_move.move_id)
        
        return stab_moves
    
    def _get_hm_stab_moves(self, pokemon_id, pokemon_types):
        """Get on-type good moves from HM learnset."""
        if pokemon_id >= len(self.mons.data):
            return []
        
        stab_moves = []
        pokemon = self.mons[pokemon_id]
        
        for hm_num in range(1, 9):  # HM001 to HM008
            if pokemon.hm[hm_num]:  # Can learn this HM
                hm_move = self.tmhm.hm[hm_num]
                if hm_move and hasattr(hm_move, 'move_id'):
                    move = self.moves.data[hm_move.move_id] if hm_move.move_id < len(self.moves.data) else None
                    if (move and self.good_moves.is_good_move(hm_move.move_id) and 
                        move.type in pokemon_types and move.base_power > 0 and
                        self._move_matches_attacker_category(move, pokemon_id)):
                        stab_moves.append(hm_move.move_id)
        
        return stab_moves
    
    def _get_best_power_move(self, pokemon_id, current_level):
        """Get the highest EstPower good move from level-up learnset."""
        if pokemon_id >= len(self.learnsets.data):
            return None
        
        best_move = None
        best_power = 0
        learnset = self.learnsets.data[pokemon_id]
        
        for entry in learnset:
            if entry.level <= current_level and self.good_moves.is_good_move(entry.move_id):
                move = self.moves.data[entry.move_id] if entry.move_id < len(self.moves.data) else None
                if move and move.base_power > 0:
                    est_power = self.est_power.calculate_estimated_power(pokemon_id, entry.move_id)
                    if est_power > best_power:
                        best_power = est_power
                        best_move = entry.move_id
        
        return best_move
    
    def _has_good_stab_move(self, current_moves, pokemon_types):
        """Check if the Pokemon already has a good STAB move.
        
        Uses relaxed criteria (no upper power limit) to preserve existing powerful moves.
        
        Args:
            current_moves (list): List of current move IDs
            pokemon_types (list): List of Pokemon's types
            
        Returns:
            bool: True if Pokemon already has a good STAB move
        """
        for move_id in current_moves:
            if move_id and move_id > 0:  # Valid move ID
                move = self.moves.data[move_id] if move_id < len(self.moves.data) else None
                if (move and self.good_moves.is_good_move_no_power_limit(move_id) and 
                    move.type in pokemon_types and move.base_power > 0):
                    return True  # Found a good STAB move
        return False
    
    def _move_matches_attacker_category(self, move, pokemon_id):
        """Check if a move's category matches the Pokemon's attacker category.
        
        Args:
            move: Move object with pss (Physical/Special/Status) field
            pokemon_id (int): Pokemon species ID
            
        Returns:
            bool: True if move category matches Pokemon's attacker preference
        """
        if not move or not hasattr(move, 'pss'):
            return False
        
        # Get Pokemon's attacker category
        attacker_category = self.attacker_categories.get_category(pokemon_id)
        
        # Status moves don't match any attacker category for STAB purposes
        if str(move.pss) == 'STATUS':
            return False
        
        # Match move category to Pokemon's attacker preference
        if attacker_category == 'Physical':
            return str(move.pss) == 'PHYSICAL'
        elif attacker_category == 'Special':
            return str(move.pss) == 'SPECIAL'
        elif attacker_category == 'Mixed':
            # Mixed attackers can use both Physical and Special moves
            return str(move.pss) in ['PHYSICAL', 'SPECIAL']
        
        return False
    
    def _find_dual_type_stab_moves(self, pokemon_id, current_level, current_moves):
        """Enhanced STAB move selection for dual-type Pokemon with secondary type preservation.
        
        Args:
            pokemon_id (int): Pokemon species ID
            current_level (int): Pokemon's current level
            current_moves (list): List of current move IDs
            
        Returns:
            dict: Dictionary with 'primary_move' and 'secondary_move' keys, or None if no changes needed
        """
        import random
        
        pokemon = self.mons[pokemon_id]
        primary_type = pokemon.type1
        secondary_type = pokemon.type2
        
        # Step 1: Check existing moves for good STAB coverage
        existing_primary_stab = []
        existing_secondary_stab = []
        
        for i, move_id in enumerate(current_moves):
            if move_id and move_id > 0:
                move = self.moves.data[move_id] if move_id < len(self.moves.data) else None
                if (move and self.good_moves.is_good_move_no_power_limit(move_id) and move.base_power > 0):
                    if move.type == primary_type:
                        existing_primary_stab.append({'move_id': move_id, 'slot': i})
                    elif move.type == secondary_type:
                        existing_secondary_stab.append({'move_id': move_id, 'slot': i})
        
        # Step 2: Determine what needs to be added
        needs_primary = len(existing_primary_stab) == 0
        needs_secondary = len(existing_secondary_stab) == 0
        
        # If both types are well covered, no changes needed
        if not needs_primary and not needs_secondary:
            return None
        
        result = {}
        protected_slots = set()  # Slots we must not overwrite
        
        # Step 3: Protect existing secondary STAB moves (keep at least one)
        if existing_secondary_stab:
            # Protect the first good secondary STAB move
            protected_slots.add(existing_secondary_stab[0]['slot'])
        
        # Step 4: Find primary STAB move if needed
        if needs_primary:
            primary_move = self._find_stab_move_for_type(pokemon_id, current_level, primary_type)
            if primary_move:
                # Find a slot that's not protected
                available_slots = [i for i in range(len(current_moves)) if i not in protected_slots]
                if available_slots:
                    result['primary_move'] = {
                        'move_id': primary_move,
                        'slot': available_slots[0],
                        'type': primary_type
                    }
                    protected_slots.add(available_slots[0])
        
        # Step 5: Find secondary STAB move if needed
        if needs_secondary:
            secondary_move = self._find_stab_move_for_type(pokemon_id, current_level, secondary_type)
            if secondary_move:
                # Find a slot that's not protected
                available_slots = [i for i in range(len(current_moves)) if i not in protected_slots]
                if available_slots:
                    result['secondary_move'] = {
                        'move_id': secondary_move,
                        'slot': available_slots[0],
                        'type': secondary_type
                    }
        
        return result if result else None
    
    def _find_stab_move_for_type(self, pokemon_id, current_level, target_type):
        """Find the best STAB move for a specific type using tier-based selection.
        
        Args:
            pokemon_id (int): Pokemon species ID
            current_level (int): Pokemon's current level
            target_type: The specific type to find a STAB move for
            
        Returns:
            int: Move ID of selected STAB move, or None if no suitable move found
        """
        import random
        
        # Use the existing tier-based logic but for a single type
        target_types = [target_type]
        
        # Tier 1: On-type GoodMove from level-up learnset (at or below current level)
        tier1_moves = self._get_level_up_stab_moves(pokemon_id, current_level, target_types)
        if tier1_moves:
            return random.choice(tier1_moves)
        
        # Tier 2: On-type GoodMove from egg moves
        tier2_moves = self._get_egg_stab_moves(pokemon_id, target_types)
        if tier2_moves:
            return random.choice(tier2_moves)
        
        # Tier 3: On-type GoodMove from TM learnset
        tier3_moves = self._get_tm_stab_moves(pokemon_id, target_types)
        if tier3_moves:
            return random.choice(tier3_moves)
        
        # Tier 4: On-type GoodMove from HM learnset
        tier4_moves = self._get_hm_stab_moves(pokemon_id, target_types)
        if tier4_moves:
            return random.choice(tier4_moves)
        
        # Tier 5: Highest EstPower GoodMove from level-up learnset (at or below current level)
        tier5_move = self._get_best_power_move(pokemon_id, current_level, target_types)
        return tier5_move
    
    def _get_best_power_move(self, pokemon_id, current_level, target_types=None):
        """Get the highest estimated power move from level-up learnset, optionally filtered by type.
        
        Args:
            pokemon_id (int): Pokemon species ID
            current_level (int): Pokemon's current level
            target_types (list): Optional list of types to filter by
            
        Returns:
            int: Move ID of best power move, or None if no suitable move found
        """
        if pokemon_id >= len(self.learnsets.data):
            return None
        
        learnset = self.learnsets.data[pokemon_id]
        best_move = None
        best_power = 0
        
        for entry in learnset:
            if (entry.level <= current_level and 
                self.good_moves.is_good_move(entry.move_id)):
                
                move = self.moves.data[entry.move_id] if entry.move_id < len(self.moves.data) else None
                if move and move.base_power > 0:
                    # Filter by type if specified
                    if target_types and move.type not in target_types:
                        continue
                    
                    # Filter by attacker category
                    if not self._move_matches_attacker_category(move, pokemon_id):
                        continue
                    
                    est_power = self.est_power.get_estimated_power(pokemon_id, entry.move_id)
                    if est_power > best_power:
                        best_power = est_power
                        best_move = entry.move_id
        
        return best_move


class CustomSetReader(Extractor):
    """Reads competitive Pokemon sets from individual JSON files.
    
    This class can locate and read a Pokemon's custom competitive set
    from the pokemon_sets directory, converting move names to internal IDs.
    """
    
    def __init__(self, context):
        super().__init__(context)
        self.moves = context.get(Moves)
        self.mons = context.get(Mons)
        
        # Build lookup tables for efficient conversion
        self.move_name_to_id = {move.name: move.move_id for move in self.moves.data if move.name}
        # Note: Pokemon data structure uses 'name' field, not 'species_name'
        
        # Set the base directory for Pokemon sets
        self.pokemon_sets_dir = os.path.join(os.path.dirname(__file__), '..', 'pokemon_sets')
        
        print(f"CustomSetReader initialized with {len(self.move_name_to_id)} moves")
    
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
            
            return {
                'species_id': pokemon_id,
                'name': data['name'],
                'moves': converted_moves,
                'ability_name': data['ability'].get('name', 'Unknown'),
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


class AssignCustomSetsStep(Step):
    """Pipeline step to assign Pokemon their custom competitive sets.
    
    This step reads Pokemon's custom sets from JSON and assigns the moves
    to replace current movesets. This is separate from STAB move logic
    and provides complete competitive movesets.
    """
    
    def __init__(self):
        # Step classes don't need to call super().__init__()
        # Context will be provided during run()
        
        # Track assignment statistics
        self.assignments_made = 0
        self.sets_not_found = 0
        self.assignment_log = []
        
    def run(self, context):
        """Run the step to assign custom sets to trainer Pokemon.
        
        Args:
            context (RandomizationContext): Randomization context
        """
        # Get required extractors from context
        self.custom_sets = context.get(CustomSetReader)
        self.moves = context.get(Moves)
        trainers = context.get(TrainerData)
        
        print(f"AssignCustomSetsStep: Assigning custom sets to trainer Pokemon...")
        
        # Process all trainers
        for trainer in trainers.data:
            # Process each Pokemon in trainer's team
            for pokemon in trainer.team:
                # Try to assign a custom set if the pokemon has a species_id
                if hasattr(pokemon, 'species_id') and pokemon.species_id:
                    current_moves = [getattr(pokemon, f'move{i}', None) for i in range(1, 5)]
                    new_moves = self.assign_custom_set_to_pokemon(pokemon.species_id, current_moves)
                    
                    # If we got new moves, update the pokemon
                    if new_moves:
                        for i, move_id in enumerate(new_moves):
                            if move_id is not None:
                                setattr(pokemon, f'move{i+1}', move_id)
        
        # Print summary
        print(f"AssignCustomSetsStep: Completed {self.assignments_made} assignments, {self.sets_not_found} sets not found")
    
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


#############
# Held Items
#############




class TrainerHeldItem(Step):
    """Assigns held items to trainer Pokémon based on predicate evaluations and tier scaling.
    
    This step implements a tier-scaled probabilistic item assignment system with three item sets:
    - Set A: Primary competitive items (generally useful items like Choice items, Life Orb, etc.)
    - Set B: Premium specialized items (type-enhancing items, ability-specific items, etc.)
    - Set C: Common/universal items that can be added to any Pokémon (berries, etc.)
    
    Item assignment probabilities vary by trainer tier:
    - Tier 1 (EARLY_GAME): No items assigned
    - Tier 2 (MID_GAME): 50% chance from A+C, 5% from B+C, 45% no item
    - Tier 3 (LATE_GAME): 50% chance from either A+C or B+C
    - Tier 4 (END_GAME): Items from B+C only
    
    Additional modes:
    - Sensible Items: All trainers get items from A+C and B+C
    - Good Items: All trainers get items from B+C
    """
    
    def __init__(self, mode="default"):
        """Initialize the TrainerHeldItem step.
        
        Args:
            mode (str): Item assignment mode - 'default', 'sensible', or 'good'
        """
        self.mode = mode.lower()
    
    def get_item_set_a_for_pokemon(self, pokemon, classifications):
        """Build Set A items conditionally based on pokemon characteristics.
        
        Args:
            pokemon: Pokemon object
            classifications: Dict of classifications from TrainerMonClassifier
            
        Returns:
            List of Item enums eligible for this pokemon
        """
        item_set_a = self.base_item_set_a.copy()
        
        # WISE_GLASSES - only add to Set A if pokemon is a Special Attacker
        if self.classifier.SPECIAL_ATTACKER in classifications:
            item_set_a.append(Item.WISE_GLASSES)
            item_set_a.append(Item.PETAYA_BERRY)
            item_set_a.append(Item.ABSORB_BULB)
            item_set_a.append(Item.CELL_BATTERY)
        
        # MUSCLE_BAND - only add to Set A if pokemon is a Physical Attacker
        if self.classifier.PHYSICAL_ATTACKER in classifications:
            item_set_a.append(Item.MUSCLE_BAND)
            item_set_a.append(Item.LIECHI_BERRY)
            item_set_a.append(Item.PROTECTIVE_PADS)
        
        # Type-specific Plates - add based on pokemon's primary or secondary type
        # Get pokemon data from Mons to access actual Type enum objects
        mon_data = self.mons[pokemon.species_id]
        pokemon_types = [mon_data.type1]
        if mon_data.type2 != mon_data.type1:  # Avoid duplicate types
            pokemon_types.append(mon_data.type2)
        
        # Type to plate mapping
        type_to_plate = {
            Type.FIGHTING: Item.FIST_PLATE,
            Type.FLYING: Item.SKY_PLATE,
            Type.POISON: Item.TOXIC_PLATE,
            Type.GROUND: Item.EARTH_PLATE,
            Type.ROCK: Item.STONE_PLATE,
            Type.BUG: Item.INSECT_PLATE,
            Type.GHOST: Item.SPOOKY_PLATE,
            Type.STEEL: Item.IRON_PLATE,
            Type.FIRE: Item.FLAME_PLATE,
            Type.WATER: Item.SPLASH_PLATE,
            Type.GRASS: Item.MEADOW_PLATE,
            Type.ELECTRIC: Item.ZAP_PLATE,
            Type.PSYCHIC: Item.MIND_PLATE,
            Type.ICE: Item.ICICLE_PLATE,
            Type.DRAGON: Item.DRACO_PLATE,
            Type.DARK: Item.DREAD_PLATE,
            Type.FAIRY: Item.PIXIE_PLATE,
        }
        
        # Add plates based on pokemon types
        for poke_type in pokemon_types:
            if poke_type in type_to_plate:
                item_set_a.append(type_to_plate[poke_type])
        
        return item_set_a
    
    def get_obligate_items_for_pokemon(self, pokemon, classifications):
        """Build obligate items list - pokemon MUST get one of these if they qualify.
        
        Args:
            pokemon: Pokemon object with species_id and other attributes
            classifications: Dict mapping species_id to classification info
            
        Returns:
            List of Item enum values that this pokemon must have
        """
        obligate_items = self.base_obligate_items.copy()
        
        # Get shared data
        mon_data = self.mons[pokemon.species_id]
        pokemon_names = self.context.get(LoadPokemonNamesStep)
        pokemon_name = pokemon_names.id_to_name.get(pokemon.species_id, f"Pokemon_{pokemon.species_id}")
        
        # Check if this Pokemon is an Eviolite user
        try:
            eviolite_users = self.context.get(EvioliteUser)
            if pokemon.species_id in eviolite_users.by_id:
                obligate_items.append(Item.EVIOLITE)
        except:
            # EvioliteUser class doesn't exist or isn't available - continue without Eviolite
            pass
        
        if pokemon_name == "Marowak":
            obligate_items.append(Item.THICK_CLUB)
        if pokemon_name == "Zacian":
            obligate_items.append(Item.RUSTED_SWORD)
        if pokemon_name == "Zamazenta":
            obligate_items.append(Item.RUSTED_SHIELD)
        if pokemon_name == "Genesect":
            obligate_items+=[Item.DOUSE_DRIVE, Item.SHOCK_DRIVE, Item.BURN_DRIVE, Item.CHILL_DRIVE]
        # when memories implemented
        # if pokemon_name == "Silvally":
        #     obligate_items+=[Item.BUG_MEMORY, Item.DARK_MEMORY, Item.DRAGON_MEMORY, Item.ELECTRIC_MEMORY, Item. FIGHTING_MEMORY, Item.FIRE_MEMORY, 
        #     Item.FLYING_MEMORY, Item.GHOST_MEMORY, Item.GRASS_MEMORY, Item.GROUND_MEMORY, Item.ICE_MEMORY, Item.POISON_MEMORY, Item.PSYCHIC_MEMORY, Item.ROCK_MEMORY, 
        #     Item.STEEL_MEMORY, Item.WATER_MEMORY, Item.WIND_MEMORY, Item.FAIRY_MEMORY]
        return obligate_items
    
    def _has_4x_ground_weakness(self, pokemon):
        """Check if Pokemon has 4x weakness to Ground type."""
        mon_data = self.mons[pokemon.species_id]
        types = [mon_data.type1]
        if hasattr(mon_data, 'type2') and mon_data.type2 != mon_data.type1:
            types.append(mon_data.type2)
        
        # Check if both types are weak to Ground
        ground_weak_count = 0
        for ptype in types:
            if (Type.GROUND, ptype) in sup_eff:
                ground_weak_count += 1
        
        return ground_weak_count >= 2
    
    def _pokemon_knows_move(self, pokemon, move_name):
        """Check if Pokemon knows a specific move."""
        if not hasattr(pokemon, 'moves'):
            return False
        
        try:
            move_id = self.move_names.get_by_name(move_name)
            return move_id in pokemon.moves
        except:
            return False
    
    def _pokemon_has_ability(self, pokemon, ability_name):
        """Check if Pokemon has a specific ability."""
        if not hasattr(pokemon, 'ability'):
            return False
        
        try:
            ability_id = self.ability_names.get_by_name(ability_name)
            return pokemon.ability == ability_id
        except:
            return False
    
    def _is_pokemon_species(self, pokemon, species_name):
        """Check if Pokemon is a specific species."""
        try:
            species_id = self.pokemon_names.get_by_name(species_name)
            return pokemon.species_id == species_id
        except:
            return False
    
    def _pokemon_is_fire_type(self, pokemon):
        """Check if Pokemon is Fire type."""
        mon_data = self.mons[pokemon.species_id]
        return mon_data.type1 == Type.FIRE or (hasattr(mon_data, 'type2') and mon_data.type2 == Type.FIRE)
    
    def _pokemon_is_poison_type(self, pokemon):
        """Check if Pokemon is Poison type."""
        mon_data = self.mons[pokemon.species_id]
        return mon_data.type1 == Type.POISON or (hasattr(mon_data, 'type2') and mon_data.type2 == Type.POISON)
    
    def _pokemon_has_status_moves(self, pokemon):
        """Check if Pokemon has any status moves."""
        if not hasattr(pokemon, 'moves'):
            return False
        
        for move_id in pokemon.moves:
            if move_id < len(self.moves.data):
                move = self.moves.data[move_id]
                if move.pss == Split.STATUS:
                    return True
        return False
    
    def _count_moves_by_split(self, pokemon, split):
        """Count moves of a specific split (Physical/Special/Status)."""
        if not hasattr(pokemon, 'moves'):
            return 0
        
        count = 0
        for move_id in pokemon.moves:
            if move_id < len(self.moves.data):
                move = self.moves.data[move_id]
                if move.pss == split:
                    count += 1
        return count
    
    def _pokemon_has_low_accuracy_moves(self, pokemon):
        """Check if Pokemon has moves with accuracy < 86."""
        if not hasattr(pokemon, 'moves'):
            return False
        
        for move_id in pokemon.moves:
            if move_id < len(self.moves.data):
                move = self.moves.data[move_id]
                if move.accuracy < 86 and move.accuracy > 0:  # 0 means always hits
                    return True
        return False
    
    def _pokemon_has_4x_weakness(self, pokemon):
        """Check if Pokemon has any 4x weakness."""
        mon_data = self.mons[pokemon.species_id]
        type2 = mon_data.type2 if hasattr(mon_data, 'type2') and mon_data.type2 != mon_data.type1 else None
        weaknesses = get_4x_weaknesses(mon_data.type1, type2)
        return len(weaknesses) > 0
    
    def get_favored_items_for_pokemon(self, pokemon, classifications):
        """Build favored items list - pokemon have 50% chance to get one of these.
        
        Args:
            pokemon: Pokemon object with species_id and other attributes
            classifications: Dict mapping species_id to classification info
            
        Returns:
            List of Item enum values that this pokemon might favor
        """
        favored_items = self.base_favored_items.copy()
        
        # Life Orb - for pokemon with Sheer Force ability
        if self._pokemon_has_ability(pokemon, "Sheer Force"):
            favored_items.append(Item.LIFE_ORB)
        
        # Air Balloon - pokemon has 4x weakness to Ground
        if self._has_4x_ground_weakness(pokemon):
            favored_items.append(Item.AIR_BALLOON)
        
        # Chesto Berry - Pokemon knows Rest but doesn't have Sleep Talk or wake-up abilities
        if (self._pokemon_knows_move(pokemon, "Rest") and
            not self._pokemon_knows_move(pokemon, "Sleep Talk") and
            not self._pokemon_has_ability(pokemon, "Early Bird") and
            not self._pokemon_has_ability(pokemon, "Shed Skin")):
            favored_items.append(Item.CHESTO_BERRY)
        
        # Damp Rock - Has Drizzle ability or knows Rain Dance
        if (self._pokemon_has_ability(pokemon, "Drizzle") or 
            self._pokemon_knows_move(pokemon, "Rain Dance")):
            favored_items.append(Item.DAMP_ROCK)
        
        # Heat Rock - Has Drought ability or knows Sunny Day
        if (self._pokemon_has_ability(pokemon, "Drought") or 
            self._pokemon_knows_move(pokemon, "Sunny Day")):
            favored_items.append(Item.HEAT_ROCK)
        
        # Icy Rock - Has Snow Warning or knows Hail/Chilly Reception/Snowscape
        if (self._pokemon_has_ability(pokemon, "Snow Warning") or
            self._pokemon_knows_move(pokemon, "Hail") or
            self._pokemon_knows_move(pokemon, "Chilly Reception") or
            self._pokemon_knows_move(pokemon, "Snowscape")):
            favored_items.append(Item.ICY_ROCK)
       
        if (self._pokemon_has_ability(pokemon, "Sand Stream") or 
            self._pokemon_has_ability(pokemon, "Sand Spit") or 
            self._pokemon_knows_move(pokemon, "Sandstorm")):
            favored_items.append(Item.SMOOTH_ROCK)
        # Flame Orb - Has Guts ability and is not Fire-type
        if (self._pokemon_has_ability(pokemon, "Guts") and 
            not self._pokemon_is_fire_type(pokemon)):
            favored_items.append(Item.FLAME_ORB)
        
        # Toxic Orb - Has Guts ability and is Fire-type
        if (self._pokemon_has_ability(pokemon, "Guts") and 
            self._pokemon_is_fire_type(pokemon)):
            favored_items.append(Item.TOXIC_ORB)
        
        # White Herb - Knows Shell Smash
        if self._pokemon_knows_move(pokemon, "Shell Smash"):
            favored_items.append(Item.WHITE_HERB)
        
        # Shedinja items - Safety Goggles, Heavy Duty Boots, Focus Sash
        if self._is_pokemon_species(pokemon, "Shedinja"):
            favored_items.extend([Item.SAFETY_GOGGLES, Item.HEAVY_DUTY_BOOTS, Item.FOCUS_SASH])
        
        # Legendary signature items
        if self._is_pokemon_species(pokemon, "Dialga"):
            favored_items.extend([Item.ADAMANT_ORB, Item.ADAMANT_CRYSTAL])
        
        if self._is_pokemon_species(pokemon, "Palkia"):
            favored_items.extend([Item.LUSTROUS_ORB, Item.LUSTROUS_GLOBE])
        
        if self._is_pokemon_species(pokemon, "Giratina"):
            favored_items.extend([Item.GRISEOUS_ORB, Item.GRISEOUS_CORE])
        
        if (self._is_pokemon_species(pokemon, "Latios") or 
            self._is_pokemon_species(pokemon, "Latias")):
            favored_items.append(Item.SOUL_DEW)
        
        # Light Ball - Pikachu
        if self._is_pokemon_species(pokemon, "Pikachu"):
            favored_items.append(Item.LIGHT_BALL)
        
        return favored_items
    
    def get_item_set_b_for_pokemon(self, pokemon, classifications):
        """Build Set B items conditionally based on pokemon characteristics.
        
        Args:
            pokemon: Pokemon object
            classifications: Dict of classifications from TrainerMonClassifier
            
        Returns:
            List of Item enums eligible for this pokemon
        """
        item_set_b = self.item_set_b.copy()
        
        # Get shared data
        mon_data = self.mons[pokemon.species_id]
        
        # Assault Vest - Pokemon with no status moves
        if not self._pokemon_has_status_moves(pokemon):
            item_set_b.append(Item.ASSAULT_VEST)
        
        # Big Root - Has drain/heal moves
        drain_moves = ["Leech Seed", "Bitter Blade", "Bouncy Bubble", "Drain Punch", "Draining Kiss", 
                      "Dream Eater", "Giga Drain", "Horn Leech", "Leech Life", "Matcha Gotcha", 
                      "Mega Drain", "Oblivion Wing", "Parabolic Charge"]
        for move_name in drain_moves:
            if self._pokemon_knows_move(pokemon, move_name):
                item_set_b.append(Item.BIG_ROOT)
                break
        
        # Blunder Policy & Wide Lens - Has low accuracy moves
        if self._pokemon_has_low_accuracy_moves(pokemon):
            item_set_b.extend([Item.BLUNDER_POLICY, Item.WIDE_LENS])
        
        # Choice items based on stats and moves
        if self.classifier.SPECIAL_ATTACKER in classifications and self._count_moves_by_split(pokemon, Split.SPECIAL) > 2:
            item_set_b.append(Item.CHOICE_SPECS)
        
        if self.classifier.PHYSICAL_ATTACKER in classifications and self._count_moves_by_split(pokemon, Split.PHYSICAL) > 2:
            item_set_b.append(Item.CHOICE_BAND)
        
        if 59 < mon_data.speed < 91 and (self._count_moves_by_split(pokemon, Split.PHYSICAL) + self._count_moves_by_split(pokemon, Split.SPECIAL)) > 2:
            item_set_b.append(Item.CHOICE_SCARF)
        
        # Focus Sash - Frail Pokemon or 4x weakness
        if self.classifier.FRAIL in classifications or self._pokemon_has_4x_weakness(pokemon):
            item_set_b.append(Item.FOCUS_SASH)
        
        # Light Clay - Screen moves
        screen_moves = ["Light Screen", "Reflect", "Aurora Veil"]
        for move_name in screen_moves:
            if self._pokemon_knows_move(pokemon, move_name):
                item_set_b.append(Item.LIGHT_CLAY)
                break
        
        # Mental Herb - Multiple status moves
        if self._count_moves_by_split(pokemon, Split.STATUS) > 1:
            item_set_b.append(Item.MENTAL_HERB)
        
        # Punching Glove - Punch moves
        punch_moves = ["Mega Punch", "Fire Punch", "Comet Punch", "Dizzy Punch", "Ice Punch", 
                      "Thunder Punch", "Mach Punch", "Dynamic Punch", "Focus Punch", "Meteor Mash",
                      "Shadow Punch", "Sky Uppercut", "Hammer Arm", "Drain Punch", "Bullet Punch",
                      "Power-Up Punch", "Ice Hammer", "Plasma Fists", "Double Iron Bash", "Wicked Blow",
                      "Surging Strikes", "Headlong Rush", "Jet Punch", "Rage Fist"]
        for move_name in punch_moves:
            if self._pokemon_knows_move(pokemon, move_name):
                item_set_b.append(Item.PUNCHING_GLOVE)
                break
        
        # Razor Claw, Scope Lens - Critical hit moves/abilities
        crit_abilities = ["Sniper", "Super Luck"]
        crit_moves = ["Aeroblast", "Air Cutter", "Aqua Cutter", "Attack Order", "Blaze Kick", 
                     "Crabhammer", "Cross Chop", "Cross Poison", "Dire Claw", "Drill Run", 
                     "Esper Wing", "Ivy Cudgel", "Karate Chop", "Leaf Blade", "Night Slash",
                     "Poison Tail", "Psycho Cut", "Razor Leaf", "Razor Wind", "Sky Attack",
                     "Slash", "Snipe Shot", "Spacial Rend", "Stone Edge", "Triple Arrows"]
        
        has_crit_ability = any(self._pokemon_has_ability(pokemon, ability) for ability in crit_abilities)
        has_crit_move = any(self._pokemon_knows_move(pokemon, move) for move in crit_moves)
        
        if has_crit_ability or has_crit_move:
            item_set_b.extend([Item.RAZOR_CLAW, Item.SCOPE_LENS])
        
        # Rocky Helmet - Defensive Pokemon
        if self.classifier.DEFENSIVE in classifications:
            item_set_b.append(Item.ROCKY_HELMET)
        
        # Room Service - Trick Room
        if self._pokemon_knows_move(pokemon, "Trick Room"):
            item_set_b.append(Item.ROOM_SERVICE)
        
        # Terrain Extender - Terrain abilities/moves
        terrain_abilities = ["Psychic Surge", "Misty Surge", "Grassy Surge", "Electric Surge"]
        terrain_moves = ["Psychic Terrain", "Misty Terrain", "Electric Terrain", "Grassy Terrain"]
        
        has_terrain_ability = any(self._pokemon_has_ability(pokemon, ability) for ability in terrain_abilities)
        has_terrain_move = any(self._pokemon_knows_move(pokemon, move) for move in terrain_moves)
        
        if has_terrain_ability or has_terrain_move:
            item_set_b.append(Item.TERRAIN_EXTENDER)
        
        # Throat Spray - Special Attacker with sound moves
        if self.classifier.SPECIAL_ATTACKER in classifications:
            sound_moves = ["Growl", "Roar", "Sing", "Supersonic", "Screech", "Snore", "Perish Song",
                          "Heal Bell", "Uproar", "Hyper Voice", "Metal Sound", "Grass Whistle", "Howl",
                          "Bug Buzz", "Chatter", "Round", "Echoed Voice", "Relic Song", "Snarl",
                          "Noble Roar", "Disarming Voice", "Parting Shot", "Boomburst", "Confide",
                          "Sparkling Aria", "Clanging Scales", "Clangorous Soul", "Overdrive",
                          "Eerie Spell", "Torch Song", "Alluring Voice", "Psychic Noise"]
            
            for move_name in sound_moves:
                if self._pokemon_knows_move(pokemon, move_name):
                    item_set_b.append(Item.THROAT_SPRAY)
                    break
        
        # Black Sludge - Poison type
        if self._pokemon_is_poison_type(pokemon):
            item_set_b.append(Item.BLACK_SLUDGE)
        
        # Toxic Orb - Specific abilities
        toxic_orb_abilities = ["Toxic Boost", "Poison Heal", "Magic Guard", "Quick Feet"]
        if any(self._pokemon_has_ability(pokemon, ability) for ability in toxic_orb_abilities):
            item_set_b.append(Item.TOXIC_ORB)
        
        # Leftovers - Defensive or Balanced
        if (self.classifier.DEFENSIVE in classifications or 
            self.classifier.BALANCED in classifications):
            item_set_b.append(Item.LEFTOVERS)
        
        # Terrain Seeds
        if (self._pokemon_has_ability(pokemon, "Psychic Surge") or 
            self._pokemon_knows_move(pokemon, "Psychic Terrain")):
            item_set_b.append(Item.PSYCHIC_SEED)
        
        if (self._pokemon_has_ability(pokemon, "Grassy Surge") or 
            self._pokemon_knows_move(pokemon, "Grassy Terrain")):
            item_set_b.append(Item.GRASSY_SEED)
        
        if (self._pokemon_has_ability(pokemon, "Electric Surge") or 
            self._pokemon_knows_move(pokemon, "Electric Terrain")):
            item_set_b.append(Item.ELECTRIC_SEED)
        
        if (self._pokemon_has_ability(pokemon, "Misty Surge") or 
            self._pokemon_knows_move(pokemon, "Misty Terrain")):
            item_set_b.append(Item.MISTY_SEED)
        
        # Weakness Policy - Damage reduction abilities
        if (self._pokemon_has_ability(pokemon, "Filter") or 
            self._pokemon_has_ability(pokemon, "Solid Rock")):
            item_set_b.append(Item.WEAKNESS_POLICY)
        
        # KINGS_ROCK & RAZOR_FANG - Flinch criteria (existing logic)
        if mon_data.speed > 84:
            item_set_b.append(Item.KINGS_ROCK)
            item_set_b.append(Item.RAZOR_FANG)
        else:
            # Has a move with priority > 0 and power > 39
            for move_id in pokemon.moves:
                if move_id < len(self.moves.data):
                    move = self.moves.data[move_id]
                    if move.priority > 0 and move.base_power > 39:
                        item_set_b.append(Item.KINGS_ROCK)
                        item_set_b.append(Item.RAZOR_FANG)
                        break
        
        return item_set_b
    
    def get_item_set_c_for_pokemon(self, pokemon, classifications):
        """Build Set C items conditionally based on pokemon characteristics.
        
        Args:
            pokemon: Pokemon object with species_id and other attributes
            classifications: Dict mapping species_id to classification info
            
        Returns:
            List of Item enum values for this pokemon
        """
        item_set_c = []
        
        # Get shared data that might be used by multiple item checks
        mon_data = self.mons[pokemon.species_id]
        moves_data = self.context.get(Moves)
        pokemon_types = [mon_data.type1]
        if mon_data.type2 != mon_data.type1:  # Avoid duplicate types
            pokemon_types.append(mon_data.type2)
        
        type_to_enhancer = {
            Type.FIRE: Item.CHARCOAL,
            Type.WATER: Item.MYSTIC_WATER,
            Type.GRASS: Item.MIRACLE_SEED,
            Type.ELECTRIC: Item.MAGNET,
            Type.ICE: Item.NEVER_MELT_ICE,
            Type.FIGHTING: Item.BLACK_BELT,
            Type.POISON: Item.POISON_BARB,
            Type.GROUND: Item.SOFT_SAND,
            Type.FLYING: Item.SHARP_BEAK,
            Type.PSYCHIC: Item.TWISTED_SPOON,
            Type.BUG: Item.SILVER_POWDER,
            Type.ROCK: Item.HARD_STONE,
            Type.GHOST: Item.SPELL_TAG,
            Type.DRAGON: Item.DRAGON_FANG,
            Type.DARK: Item.BLACK_GLASSES,
            Type.STEEL: Item.METAL_COAT,
        }
        
        # Add type enhancers based on pokemon types
        for poke_type in pokemon_types:
            if poke_type in type_to_enhancer:
                item_set_c.append(type_to_enhancer[poke_type])
        
        return item_set_c
    
    
    def run(self, context):
        """Run the held item assignment step.
        
        For each trainer Pokémon, evaluates predicates and assigns held items
        based on tier-scaled probability.
        """
        # Get required extractors
        self.context = context
        self.trainers = context.get(Trainers)
        self.mons = context.get(Mons)
        self.moves = context.get(Moves)
        self.tiers = context.get(IdentifyTier)
        self.ability_names = context.get(LoadAbilityNames)
        self.move_names = context.get(LoadMoveNamesStep)
        self.pokemon_names = context.get(LoadPokemonNamesStep)
        self.bosses = context.get(IdentifyBosses)
        
        # Initialize TrainerMonClassifier for predicate evaluation
        self.classifier = TrainerMonClassifier(context)
        
        # Obligate Items - pokemon MUST get these if they qualify
        self.base_obligate_items = []
        
        # Favored Items - pokemon have 50% chance to get these if they qualify
        self.base_favored_items = []
        
        # Sensible Items plus Plates. No Custap. You're welcome.
        self.base_item_set_a = [
            Item.ASPEAR_BERRY,
            Item.PERSIM_BERRY,
            Item.PECHA_BERRY,
            Item.RAWST_BERRY,
            Item.CHESTO_BERRY,
            Item.KEE_BERRY,
            Item.CHILAN_BERRY,
            Item.APICOT_BERRY,
            Item.GANLON_BERRY,
            Item.MARANGA_BERRY,
            Item.SALAC_BERRY,
            Item.SHED_SHELL,
            Item.UTILITY_UMBRELLA,
            Item.LUMINOUS_MOSS,
            Item.METRONOME,
        ]
        
        # Set B: better items plus supereffective berries
        self.item_set_b = [
            # Type enhancers
            Item.MIRROR_HERB,
            Item.ABILITY_SHIELD,
            Item.CLEAR_AMULET,
            Item.COVERT_CLOAK,
            Item.SAFETY_GOGGLES,
            Item.EXPERT_BELT,
            Item.HEAVY_DUTY_BOOTS,
            Item.LUM_BERRY,
           
            # Special case items
            
            # Weather items#####################################################################
            
            
        ]
        
        # Set C: Common/universal items
        self.item_set_c = [
            # Berries
            Item.SITRUS_BERRY,    # Restore HP at 50%
        ]
        
        # Item assignment probabilities by tier (default mode)
        self.tier_probabilities = {
            # Tier: (prob_no_item, prob_set_a, prob_set_b)
            # Set C is always considered alongside A or B
            Tier.EARLY_GAME: (1.00, 0.00, 0.00),  # Early Game: No items
            Tier.MID_GAME: (0.45, 0.50, 0.05),    # Mid Game: Mostly A+C, rarely B+C
            Tier.LATE_GAME: (0.00, 0.50, 0.50),   # Late Game: Equal chance A+C or B+C
            Tier.END_GAME: (0.00, 0.00, 1.00),    # End Game: Only B+C
        }
        
        # needs to be even probability for all items on base lists plus an appended items
        if self.mode == "sensible":
            self.tier_probabilities = {
                Tier.EARLY_GAME: (0.00, 0.50, 0.50),  # All tiers get items, unweighted
                Tier.MID_GAME: (0.00, 0.50, 0.50),
                Tier.LATE_GAME: (0.00, 0.50, 0.50),
                Tier.END_GAME: (0.00, 0.50, 0.50),
            }
        elif self.mode == "good":
            self.tier_probabilities = {
                Tier.EARLY_GAME: (0.00, 0.00, 1.00),  # All tiers get items from B+C only
                Tier.MID_GAME: (0.00, 0.00, 1.00),
                Tier.LATE_GAME: (0.00, 0.00, 1.00),
                Tier.END_GAME: (0.00, 0.00, 1.00),
            }
        
        # Set up item sets for easy access
        self.item_set_a = self.base_item_set_a
        self.obligate_items = self.base_obligate_items
        self.favored_items = self.base_favored_items
        
        # Track statistics
        self.items_assigned = 0
        self.pokemon_processed = 0
        
        print(f"\n=== TrainerHeldItem: Running in {self.mode} mode ===")
        
        # Process each trainer
        for trainer in self.trainers.data:
            # Skip if trainer doesn't use items
            if not hasattr(trainer.info, 'trainermontype') or 'ITEMS' not in str(trainer.info.trainermontype):
                continue
            
            # Get trainer tier
            try:
                trainer_tier = self.tiers.get_tier_for_trainer(trainer.info.trainer_id)
                tier_num = int(trainer_tier)  # Convert Tier enum to int
            except (ValueError, KeyError):
                # Skip trainers without a defined tier
                print(f"Warning: Trainer {trainer.info.name} has no defined tier, skipping item assignment")
                continue
            
            # Process each Pokémon in the trainer's team
            for pokemon in trainer.team:
                self.pokemon_processed += 1
                
                # Clear existing held item so it can be reassigned
                if hasattr(pokemon, 'held_item') and pokemon.held_item > 0:
                    pokemon.held_item = 0
                
                # Ensure Pokémon has held_item attribute
                if not hasattr(pokemon, 'held_item'):
                    pokemon.held_item = 0
                
                # Get probabilities for this tier
                prob_no_item, prob_set_a, prob_set_b = self.tier_probabilities[tier_num]
                
                # Roll for item assignment
                roll = random.random()
                
                if roll < prob_no_item:
                    # No item assigned
                    pokemon.held_item = 0
                elif roll < prob_no_item + prob_set_a:
                    # Assign from Set A + C
                    pokemon.held_item = self._select_item_for_pokemon(pokemon, trainer=trainer, trainer_tier=trainer_tier, set_a=True, set_c=True)
                else:
                    # Assign from Set B + C
                    pokemon.held_item = self._select_item_for_pokemon(pokemon, trainer=trainer, trainer_tier=trainer_tier, set_b=True, set_c=True)
                
                if pokemon.held_item > 0:
                    self.items_assigned += 1
        
        # Ensure boss aces have held items
        self._ensure_boss_aces_have_items()
        
        # Print summary statistics
        print(f"=== TrainerHeldItem: Summary ===")
        print(f"Assigned items to {self.items_assigned}/{self.pokemon_processed} Pokémon ({(self.items_assigned/max(1, self.pokemon_processed))*100:.1f}%)")
        print(f"===========================\n")
    
    def _select_item_for_pokemon(self, pokemon, trainer=None, trainer_tier=None, set_a=False, set_b=False, set_c=False):
        """Select an appropriate held item for a Pokémon based on its attributes.
        
        Args:
            pokemon: The Pokémon object to assign an item to
            trainer: The trainer object (for name in decision path)
            trainer_tier: The tier of the trainer (Tier enum)
            set_a: Whether to consider items from Set A
            set_b: Whether to consider items from Set B
            set_c: Whether to consider items from Set C
            
        Returns:
            int: Item ID (from Item enum) or 0 if no suitable item found
        """
        # Get Pokemon species data
        if not hasattr(pokemon, 'species_id') or pokemon.species_id >= len(self.mons.data):
            return 0
        
        species = self.mons[pokemon.species_id]
        classifications = {}  # TODO: Get actual classifications if needed
        
        # Check obligate and favored items based on mode and tier
        should_check_obligate_favored = False
        
        if self.mode == "default":
            # Only check in LATE_GAME and END_GAME tiers
            if trainer_tier and trainer_tier in [Tier.LATE_GAME, Tier.END_GAME]:
                should_check_obligate_favored = True
        elif self.mode == "sensible":
            # Never check obligate/favored in sensible mode
            should_check_obligate_favored = False
        elif self.mode == "good":
            # Always check obligate/favored in good mode
            should_check_obligate_favored = True
        
        # Store favored items for potential fallback to Set B
        favored_items_for_set_b = []
        
        if should_check_obligate_favored:
            # Check obligate items first - pokemon MUST get one if they qualify
            obligate_items = self.get_obligate_items_for_pokemon(pokemon, classifications)
            if obligate_items:
                chosen_item = self.context.decide(
                    path=["trainer_items", "obligate", trainer.info.name, species.name],
                    original=None,
                    candidates=obligate_items
                )
                return chosen_item.value
            
            # Check favored items - 50% chance if they qualify
            favored_items = self.get_favored_items_for_pokemon(pokemon, classifications)
            if favored_items:
                if random.random() < 0.5:
                    chosen_item = self.context.decide(
                        path=["trainer_items", "favored", trainer.info.name, species.name],
                        original=None,
                        candidates=favored_items
                    )
                    return chosen_item.value
                else:
                    # Failed the roll - store for Set B fallback
                    favored_items_for_set_b = favored_items
        
        # Build candidate item pool from regular sets
        candidate_items = []
        
        # Add items from enabled sets
        if set_a and self.item_set_a:
            # For set A, consider attacker type
            if hasattr(species, 'attack') and hasattr(species, 'sp_attack'):
                if species.attack > species.sp_attack * 1.2:
                    # Physical attacker - prioritize physical items
                    physical_items = [Item.CHOICE_BAND.value, Item.MUSCLE_BAND.value, 
                                     Item.EXPERT_BELT.value, Item.LIFE_ORB.value]
                    candidate_items.extend(physical_items)
                elif species.sp_attack > species.attack * 1.2:
                    # Special attacker - prioritize special items
                    special_items = [Item.CHOICE_SPECS.value, Item.WISE_GLASSES.value, 
                                    Item.EXPERT_BELT.value, Item.LIFE_ORB.value]
                    candidate_items.extend(special_items)
                else:
                    # Mixed attacker or balanced
                    candidate_items.extend(self.item_set_a)
            else:
                candidate_items.extend(self.item_set_a)
        
        if set_b:
            # Get Set B items based on Pokemon characteristics
            set_b_items = self.get_item_set_b_for_pokemon(pokemon, classifications)
            candidate_items.extend([item.value for item in set_b_items])
            
            # Add favored items that failed their roll to Set B
            if favored_items_for_set_b:
                candidate_items.extend([item.value for item in favored_items_for_set_b])
        
        if set_c and self.item_set_c:
            # Add basic items
            candidate_items.extend(self.item_set_c)
            
            # Check for status move to add relevant berries
            if self._has_status_move(pokemon):
                status_berries = [
                    Item.LUM_BERRY.value,
                    Item.CHESTO_BERRY.value,
                    Item.PERSIM_BERRY.value
                ]
                candidate_items.extend(status_berries)
        
        # Remove duplicates while preserving order
        candidate_items = list(dict.fromkeys(candidate_items))
        
        # If no candidates, return no item
        if not candidate_items:
            return 0
        
        # Return a random item from the candidates
        if candidate_items:
            # Convert item IDs back to Item objects for context.decide
            item_objects = []
            for item_id in candidate_items:
                # Find the Item enum that matches this ID
                for item_enum in Item:
                    if item_enum.value == item_id:
                        item_objects.append(item_enum)
                        break
            
            if item_objects:
                chosen_item = self.context.decide(
                    path=["trainer_items", "general", trainer.info.name, species.name],
                    original=None,
                    candidates=item_objects
                )
                return chosen_item.value
        
        return 0
    
    def _get_special_case_item(self, species):
        """Check if this Pokemon should get a special species-specific item.
        
        Args:
            species: Pokemon species data
            
        Returns:
            int: Item ID for special case, or 0 if none applies
        """
        # Map of species names to their special items
        special_items = {
            "Pikachu": Item.LIGHT_BALL.value,
            "Cubone": Item.THICK_CLUB.value,
            "Marowak": Item.THICK_CLUB.value,
            "Latios": Item.SOUL_DEW.value,
            "Latias": Item.SOUL_DEW.value,
            "Clamperl": Item.DEEP_SEA_TOOTH.value,  # Could be either tooth or scale
            "Ditto": Item.QUICK_POWDER.value
        }
        
        if hasattr(species, 'name') and species.name in special_items:
            return special_items[species.name]
        
        return 0
    
    def _get_type_enhancing_item(self, type_id):
        """Get the type-enhancing item for a specific type.
        
        Args:
            type_id: Type ID
            
        Returns:
            int: Item ID for type enhancer, or 0 if none applies
        """
        # Map of types to their enhancing items
        type_items = {
            Type.FIRE.value: Item.CHARCOAL.value,
            Type.WATER.value: Item.MYSTIC_WATER.value,
            Type.GRASS.value: Item.MIRACLE_SEED.value,
            Type.ELECTRIC.value: Item.MAGNET.value,
            Type.ICE.value: Item.NEVER_MELT_ICE.value,
            Type.FIGHTING.value: Item.BLACK_BELT.value,
            Type.POISON.value: Item.POISON_BARB.value,
            Type.GROUND.value: Item.SOFT_SAND.value,
            Type.FLYING.value: Item.SHARP_BEAK.value,
            Type.PSYCHIC.value: Item.TWISTED_SPOON.value,
            Type.BUG.value: Item.SILVER_POWDER.value,
            Type.ROCK.value: Item.HARD_STONE.value,
            Type.GHOST.value: Item.SPELL_TAG.value,
            Type.DRAGON.value: Item.DRAGON_FANG.value,
            Type.DARK.value: Item.BLACK_GLASSES.value,
            Type.STEEL.value: Item.METAL_COAT.value,
            Type.NORMAL.value: Item.SILK_SCARF.value
        }
        
        return type_items.get(type_id, 0)
    
    def _can_evolve(self, species_id):
        """Check if a Pokémon can evolve.
        
        Args:
            species_id: The species ID to check
            
        Returns:
            bool: True if the Pokémon can evolve, False otherwise
        """
        # Try to get evolution data from context
        try:
            from gl.framework import EvolutionData
            evo_data = self.context.get(EvolutionData)
            
            # Check if this species has any evolution entries
            if species_id < len(evo_data.data) and evo_data.data[species_id]:
                # Filter out empty evolution entries
                valid_evos = [evo for evo in evo_data.data[species_id] if evo.method != 0]
                return len(valid_evos) > 0
        except:
            # If evolution data is not available, use a simpler approach with common unevolved Pokémon
            # These are some common unevolved Pokémon for demonstration
            unevolved_pokemon = [
                1, 4, 7, 10, 13, 16, 19, 21, 23, 25, 27, 29, 32, 35, 37, 39, 41, 
                43, 46, 48, 50, 52, 54, 56, 58, 60, 63, 66, 69, 72, 74, 77, 79, 
                81, 83, 84, 86, 88, 90, 92, 95, 96, 98, 100, 102, 104, 108, 109, 
                111, 114, 116, 118, 120, 122, 123, 124, 125, 126, 127, 128, 129, 
                131, 133, 138, 140, 142, 147
            ]
            return species_id in unevolved_pokemon
            
    def _has_status_move(self, pokemon):
        """Check if a Pokémon has status moves.
        
        Args:
            pokemon: The Pokémon object to check
            
        Returns:
            bool: True if the Pokémon has status moves, False otherwise
        """
        # Get the moves context
        moves = self.context.get(Moves)
        
        # Trainer Pokémon have move1, move2, etc. attributes (not a moves list)
        move_attrs = ['move1', 'move2', 'move3', 'move4']
        
        # Check each move attribute
        for move_attr in move_attrs:
            if hasattr(pokemon, move_attr):
                move_id = getattr(pokemon, move_attr)
                if move_id == 0:  # Skip empty move slots
                    continue
                
                # Check if move exists and is a status move
                if move_id < len(moves.data) and hasattr(moves.data[move_id], 'pss'):
                    if moves.data[move_id].pss == Split.STATUS:
                        return True
                        
        return False
    
    def _ensure_boss_aces_have_items(self):
        """Ensure all boss aces have held items based on their tier."""
        boss_aces_processed = 0
        boss_aces_given_items = 0
        
        # Create a set of boss trainer IDs for quick lookup
        boss_trainer_ids = set()
        for boss_category in self.bosses.data.values():
            for trainer in boss_category.trainers:
                boss_trainer_ids.add(trainer.info.trainer_id)
        
        # Process each trainer to find boss aces
        for trainer in self.trainers.data:
            # Skip if not a boss trainer
            if trainer.info.trainer_id not in boss_trainer_ids:
                continue
            
            # Skip if trainer has no ace
            if trainer.ace_index is None or not trainer.team:
                continue
            
            ace_pokemon = trainer.ace
            
            # Skip if ace is None (safety check)
            if ace_pokemon is None:
                continue
                
            boss_aces_processed += 1
            
            # Skip if ace already has an item
            if hasattr(ace_pokemon, 'held_item') and ace_pokemon.held_item > 0:
                continue
            
            # Get trainer tier
            try:
                trainer_tier = self.tiers.get_tier_for_trainer(trainer.info.trainer_id)
            except (ValueError, KeyError):
                print(f"Warning: Boss trainer {trainer.info.name} has no defined tier, skipping ace item assignment")
                continue
            
            # Ensure ace has held_item attribute
            if not hasattr(ace_pokemon, 'held_item'):
                ace_pokemon.held_item = 0
            
            # Assign item based on tier
            assigned_item = self._assign_boss_ace_item(ace_pokemon, trainer, trainer_tier)
            if assigned_item > 0:
                ace_pokemon.held_item = assigned_item
                boss_aces_given_items += 1
                self.items_assigned += 1
                
                # Get item name for logging
                item_name = Item(assigned_item).name if assigned_item < len(Item) else f"Item_{assigned_item}"
                species_name = self.mons[ace_pokemon.species_id].name
                print(f"Boss ace item: {trainer.info.name}'s {species_name} -> {item_name}")
        
        print(f"Boss ace items: {boss_aces_given_items}/{boss_aces_processed} boss aces given items")
    
    def _assign_boss_ace_item(self, pokemon, trainer, trainer_tier):
        """Assign an item to a boss ace based on tier rules that match regular item assignment."""
        species = self.mons[pokemon.species_id]
        classifications = {}  # TODO: Get actual classifications if needed
        
        # For Mid/Late/End game tiers, check obligate and favored items first
        if trainer_tier in [Tier.MID_GAME, Tier.LATE_GAME, Tier.END_GAME]:
            # Check obligate items first
            obligate_items = self.get_obligate_items_for_pokemon(pokemon, classifications)
            if obligate_items:
                chosen_item = self.context.decide(
                    path=["boss_ace_items", "obligate", trainer.info.name, species.name],
                    original=None,
                    candidates=obligate_items
                )
                return chosen_item.value
            
            # Check favored items
            favored_items = self.get_favored_items_for_pokemon(pokemon, classifications)
            if favored_items:
                chosen_item = self.context.decide(
                    path=["boss_ace_items", "favored", trainer.info.name, species.name],
                    original=None,
                    candidates=favored_items
                )
                return chosen_item.value
        
        # Get tier probabilities to determine item pool
        prob_no_item, prob_set_a, prob_set_b = self.tier_probabilities[trainer_tier]
        
        # Determine item sets based on tier probabilities
        if trainer_tier == Tier.EARLY_GAME:
            # Early game: Set A + C only (matches tier probabilities)
            return self._select_item_for_pokemon(pokemon, trainer=trainer, trainer_tier=trainer_tier, set_a=True, set_c=True)
        elif trainer_tier == Tier.MID_GAME:
            # Mid game: Roll between A+C and B+C based on probabilities
            roll = self.context.decide(
                path=["boss_ace_items", "mid_tier_roll", trainer.info.name, species.name],
                original=None,
                candidates=[0, 1]  # 0 = A+C, 1 = B+C
            )
            
            # Use probability ratio to decide: prob_set_a vs prob_set_b
            if roll == 0 or prob_set_b == 0:  # Choose A+C
                return self._select_item_for_pokemon(pokemon, trainer=trainer, trainer_tier=trainer_tier, set_a=True, set_c=True)
            else:  # Choose B+C
                return self._select_item_for_pokemon(pokemon, trainer=trainer, trainer_tier=trainer_tier, set_b=True, set_c=True)
        else:  # LATE_GAME or END_GAME
            # Late game: Equal A+C vs B+C, End game: B+C only
            if trainer_tier == Tier.END_GAME or prob_set_a == 0:
                # End game: Set B + C only
                return self._select_item_for_pokemon(pokemon, trainer=trainer, trainer_tier=trainer_tier, set_b=True, set_c=True)
            else:
                # Late game: Roll between A+C and B+C (equal probability)
                roll = self.context.decide(
                    path=["boss_ace_items", "late_tier_roll", trainer.info.name, species.name],
                    original=None,
                    candidates=[0, 1]  # 0 = A+C, 1 = B+C
                )
                
                if roll == 0:  # Choose A+C
                    return self._select_item_for_pokemon(pokemon, trainer=trainer, trainer_tier=trainer_tier, set_a=True, set_c=True)
                else:  # Choose B+C
                    return self._select_item_for_pokemon(pokemon, trainer=trainer, trainer_tier=trainer_tier, set_b=True, set_c=True)
