"""
Move selection logic for Pokemon ROM randomization.

This module contains classes and logic for determining appropriate movesets
for trainer Pokemon based on various criteria like attacker type, level, etc.
"""

from framework import Extractor, Mons, Moves, EggMoves, Learnsets, TMHM
from enums import Split
import json
import os
import glob


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
        
        pokemon = self.mons.data[pokemon_id]
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
            pokemon = self.mons.data[pokemon_id]
            
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
            
        pokemon = self.mons.data[pokemon_id]
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
        
        pokemon = self.mons.data[pokemon_id]
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
        pokemon = self.mons.data[pokemon_id]
        
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
        
        pokemon = self.mons.data[pokemon_id]
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


class AssignCustomSet(Extractor):
    """Pipeline step to assign a Pokemon its custom competitive set.
    
    This step reads a Pokemon's custom set from JSON and assigns the moves
    to replace the current moveset. This is separate from STAB move logic
    and provides complete competitive movesets.
    """
    
    def __init__(self, context):
        super().__init__(context)
        self.custom_sets = context.get(CustomSetReader)
        self.moves = context.get(Moves)
        
        # Track assignment statistics
        self.assignments_made = 0
        self.sets_not_found = 0
        self.assignment_log = []
    
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


class GeneralEVAllocator:
    """Implements the GeneralEV allocation algorithm for trainer Pokemon.
    
    Algorithm:
    1. Set EV budget (default 510, max 510)
    2. Allocate 152 EVs to highest base stat (random if tie)
    3. Allocate 100 EVs to second highest stat (from remaining if tie)
    4. Allocate 50 EVs to random stat, 5 times (skip if >252)
    5. Allocate final 8 EVs to random stat (also respect 252 limit)
    """
    
    def __init__(self, context):
        self.context = context
        self.mons = context.get(Mons)
        import random
        self.random = random
        
        # Statistics tracking
        self.allocations_made = 0
        self.allocation_log = []
    
    def allocate_evs(self, pokemon, pokemon_id, ev_budget=510):
        """Allocate EVs using the GeneralEV algorithm.
        
        Args:
            pokemon: Pokemon object with EV fields
            pokemon_id (int): Pokemon species ID
            ev_budget (int): Total EV budget (default 510, max 510)
            
        Returns:
            dict: Final EV allocation {stat: value}
        """
        # Clamp EV budget to maximum
        ev_budget = min(ev_budget, 510)
        
        # Get Pokemon base stats
        mon_data = self._get_pokemon_data(pokemon_id)
        if not mon_data:
            return self._apply_fallback_evs(pokemon)
        
        # Initialize EV allocation
        ev_allocation = {
            'hp': 0, 'atk': 0, 'def': 0, 'speed': 0, 'spatk': 0, 'spdef': 0
        }
        remaining_budget = ev_budget
        
        # Get base stats for allocation decisions
        base_stats = {
            'hp': mon_data.hp,
            'atk': mon_data.attack,
            'def': mon_data.defense,
            'speed': mon_data.speed,
            'spatk': mon_data.sp_attack,
            'spdef': mon_data.sp_defense
        }
        
        # Step 1: Allocate 152 EVs to highest base stat
        highest_stats = self._get_highest_stats(base_stats)
        chosen_highest = self.random.choice(highest_stats)
        
        if remaining_budget >= 152:
            ev_allocation[chosen_highest] = 152
            remaining_budget -= 152
        else:
            ev_allocation[chosen_highest] = remaining_budget
            remaining_budget = 0
        
        # Step 2: Allocate 100 EVs to second highest stat (excluding the chosen highest)
        if remaining_budget >= 100:
            remaining_highest = [stat for stat in highest_stats if stat != chosen_highest]
            if remaining_highest:
                chosen_second = self.random.choice(remaining_highest)
            else:
                # If no remaining from highest tier, get next highest tier
                second_highest_stats = self._get_second_highest_stats(base_stats, highest_stats)
                if second_highest_stats:
                    chosen_second = self.random.choice(second_highest_stats)
                else:
                    # Fallback to any remaining stat
                    available_stats = [s for s in base_stats.keys() if s != chosen_highest]
                    chosen_second = self.random.choice(available_stats) if available_stats else chosen_highest
            
            ev_allocation[chosen_second] = 100
            remaining_budget -= 100
        
        # Step 3: Allocate 50 EVs to random stats, 5 times
        for _ in range(5):
            if remaining_budget < 50:
                break
            
            # Find stats that can accept 50 more EVs (won't exceed 252)
            available_stats = [stat for stat in ev_allocation.keys() 
                             if ev_allocation[stat] + 50 <= 252]
            
            if available_stats:
                chosen_stat = self.random.choice(available_stats)
                ev_allocation[chosen_stat] += 50
                remaining_budget -= 50
            else:
                # No stats can accept 50 EVs, skip this allocation
                break
        
        # Step 4: Allocate final 8 EVs to a random stat
        if remaining_budget >= 8:
            available_stats = [stat for stat in ev_allocation.keys() 
                             if ev_allocation[stat] + 8 <= 252]
            
            if available_stats:
                chosen_stat = self.random.choice(available_stats)
                ev_allocation[chosen_stat] += 8
                remaining_budget -= 8
        
        # Apply the EV allocation to the Pokemon
        pokemon.hp_ev = ev_allocation['hp']
        pokemon.atk_ev = ev_allocation['atk']
        pokemon.def_ev = ev_allocation['def']
        pokemon.speed_ev = ev_allocation['speed']
        pokemon.spatk_ev = ev_allocation['spatk']
        pokemon.spdef_ev = ev_allocation['spdef']
        
        return ev_allocation
    
    def _get_pokemon_data(self, pokemon_id):
        """Get Pokemon base stat data."""
        for mon in self.mons.data:
            if mon.pokemon_id == pokemon_id:
                return mon
        return None
    
    def _get_highest_stats(self, base_stats):
        """Get list of stats tied for highest value."""
        max_value = max(base_stats.values())
        return [stat for stat, value in base_stats.items() if value == max_value]
    
    def _get_second_highest_stats(self, base_stats, exclude_stats):
        """Get list of stats tied for second highest value, excluding specified stats."""
        remaining_stats = {stat: value for stat, value in base_stats.items() 
                         if stat not in exclude_stats}
        
        if not remaining_stats:
            return []
        
        max_value = max(remaining_stats.values())
        return [stat for stat, value in remaining_stats.items() if value == max_value]
    
    def _apply_fallback_evs(self, pokemon):
        """Apply fallback EV allocation if Pokemon data not found."""
        # Simple fallback: 85 EVs in each stat (510 total)
        fallback_ev = 85
        
        pokemon.hp_ev = fallback_ev
        pokemon.atk_ev = fallback_ev
        pokemon.def_ev = fallback_ev
        pokemon.speed_ev = fallback_ev
        pokemon.spatk_ev = fallback_ev
        pokemon.spdef_ev = fallback_ev
        
        return {
            'hp': fallback_ev, 'atk': fallback_ev, 'def': fallback_ev,
            'speed': fallback_ev, 'spatk': fallback_ev, 'spdef': fallback_ev
        }


class GeneralEVStep:
    """Pipeline step to apply GeneralEV allocation to trainer Pokemon.
    
    This step uses the GeneralEV algorithm to allocate EVs based on Pokemon base stats.
    It requires the IV_EV_SET flag to be enabled in the trainer data type.
    """
    
    def __init__(self, ev_budget=510, trainer_filter=None):
        """Initialize the GeneralEV step.
        
        Args:
            ev_budget (int): Total EV budget per Pokemon (default 510, max 510)
            trainer_filter: Optional function to filter which trainers to modify
        """
        self.ev_budget = min(ev_budget, 510)  # Clamp to maximum
        self.trainer_filter = trainer_filter
        self.total_pokemon_processed = 0
        self.total_pokemon_allocated = 0
        self.allocation_log = []
    
    def run(self, context):
        """Run the GeneralEV allocation step."""
        from framework import TrainerData, Trainers, LoadPokemonNamesStep
        
        trainer_data = context.get(TrainerData)
        trainers = context.get(Trainers)
        
        # Ensure we have the required extractors
        try:
            pokemon_names = context.get(LoadPokemonNamesStep)
        except:
            pokemon_names = None
        
        # Initialize EV allocator
        ev_allocator = GeneralEVAllocator(context)
        
        print(f"Applying GeneralEV allocation with {self.ev_budget} EV budget...")
        
        for i, trainer in enumerate(trainer_data.data):
            # Apply filter if provided
            if self.trainer_filter and not self.trainer_filter(trainer, i):
                continue
            
            # Check if trainer has IV_EV_SET flag enabled
            trainer_flags = trainer.trainermontype.data[0]
            from enums import TrainerDataType
            if not (trainer_flags & TrainerDataType.IV_EV_SET):
                continue
            
            # Process each Pokemon in the trainer's team
            if i < len(trainers.data) and trainers.data[i].team:
                team = trainers.data[i].team
                trainer_name = getattr(trainer, 'name', f'Trainer {i}')
                
                for j, pokemon in enumerate(team):
                    self.total_pokemon_processed += 1
                    
                    # Get Pokemon species ID
                    species_id = getattr(pokemon, 'species_id', 0)
                    if species_id == 0:
                        continue
                    
                    # Get Pokemon name for logging
                    pokemon_name = f'Pokemon {species_id}'
                    if pokemon_names and hasattr(pokemon_names, 'data') and species_id < len(pokemon_names.data):
                        pokemon_name = pokemon_names.data[species_id] or pokemon_name
                    
                    # Apply GeneralEV allocation
                    ev_allocation = ev_allocator.allocate_evs(pokemon, species_id, self.ev_budget)
                    
                    self.total_pokemon_allocated += 1
                    
                    # Log the allocation
                    log_entry = {
                        'trainer': trainer_name,
                        'pokemon': pokemon_name,
                        'ev_allocation': ev_allocation,
                        'total_evs': sum(ev_allocation.values())
                    }
                    self.allocation_log.append(log_entry)
                    
                    # Print allocation details
                    total_evs = sum(ev_allocation.values())
                    ev_str = '/'.join([str(ev_allocation[stat]) for stat in ['hp', 'atk', 'def', 'spatk', 'spdef', 'speed']])
                    print(f"  {trainer_name} - {pokemon_name}: {ev_str} (Total: {total_evs})")
        
        print(f"\nGeneralEV Allocation Complete:")
        print(f"  Processed: {self.total_pokemon_processed} Pokemon")
        print(f"  Allocated: {self.total_pokemon_allocated} Pokemon")
        print(f"  EV Budget: {self.ev_budget}")
    
    def get_allocation_summary(self):
        """Get a summary of all EV allocations performed.
        
        Returns:
            dict: Summary statistics and detailed log
        """
        return {
            'total_processed': self.total_pokemon_processed,
            'total_allocated': self.total_pokemon_allocated,
            'ev_budget_used': self.ev_budget,
            'allocation_log': self.allocation_log
        }


if __name__ == "__main__":
    import ndspy.rom
    from framework import RandomizationContext, LoadPokemonNamesStep, LoadMoveNamesStep
    
    # Load the same ROM that framework uses
    rom_path = "recompiletest.nds"
    print(f"Loading ROM: {rom_path}")
    
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    ctx = RandomizationContext(rom)
    
    print("\n=== Testing Move Selection Classes ===")
        
    # Test IdentifyAttackerCategory
    print("\n1. Testing IdentifyAttackerCategory...")
    attacker_categories = ctx.get(IdentifyAttackerCategory)
        
    # Show some examples
    example_pokemon = [25, 150, 144]  # Pikachu, Mewtwo, Articuno
    for pid in example_pokemon:
        if pid < len(ctx.get(Mons).data):
            pokemon = ctx.get(Mons).data[pid]
            category = attacker_categories.get_category(pid)
            print(f"  {pokemon.name}: Attack={pokemon.attack}, Sp.Attack={pokemon.sp_attack} -> {category}")
        
            # Test MoveBlacklist and MoveWhitelist
    print("\n2. Testing MoveBlacklist and MoveWhitelist...")
    blacklist = ctx.get(MoveBlacklist)
    whitelist = ctx.get(MoveWhitelist)
        
    # Add some example moves
    blacklist.add_move_by_name("Splash")
    whitelist.add_move_by_name("Earthquake")
        
    print(f"  Added 'Splash' to blacklist")
    print(f"  Added 'Earthquake' to whitelist")
        
    # Test IdentifyGoodMoves
    print("\n3. Testing IdentifyGoodMoves...")
    good_moves = ctx.get(IdentifyGoodMoves)
    good_move_count = len(good_moves.get_good_moves())
    print(f"  Found {good_move_count} good moves total")
        
    # Show some examples of good moves
    moves = ctx.get(Moves)
    good_move_ids = list(good_moves.get_good_moves())[:10]  # First 10
    print("  Example good moves:")
    for move_id in good_move_ids:
        if move_id < len(moves.data):
            move = moves.data[move_id]
            if move.name:
                print(f"    {move.name}: Power={move.base_power}, Accuracy={move.accuracy}")
        
    # Test FindEstPower
    print("\n4. Testing FindEstPower...")
    est_power = ctx.get(FindEstPower)
        
    # Test with Pikachu (should prefer special moves)
    pikachu_id = 25
    test_moves = [85, 87, 129]  # Thunderbolt, Bubble Beam, Swift
    print(f"  Testing estimated power for Pikachu:")
    for move_id in test_moves:
        if move_id < len(moves.data):
                move = moves.data[move_id]
                power = est_power.calculate_estimated_power(pikachu_id, move_id)
                if move.name:
                    print(f"    {move.name}: {power} estimated power")
        
    # Test EggMoves
    print("\n5. Testing EggMoves...")
    egg_moves = ctx.get(EggMoves)
            
    # Test with some starter Pokemon
    test_pokemon = [1, 4, 7]  # Bulbasaur, Charmander, Squirtle
    for pid in test_pokemon:
            if pid < len(ctx.get(Mons).data):
                pokemon = ctx.get(Mons).data[pid]
                egg_move_ids = egg_moves.get_egg_move_ids(pid)
                print(f"  {pokemon.name}: {len(egg_move_ids)} egg moves")
                    
                # Show first few egg moves
                for move_id in egg_move_ids[:3]:  # First 3
                    if move_id < len(moves.data) and moves.data[move_id].name:
                        print(f"    - {moves.data[move_id].name}")
        
        
        
