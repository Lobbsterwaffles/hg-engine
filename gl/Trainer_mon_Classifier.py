# -*- coding: utf-8 -*-
"""
Trainer_mon_Classifier.py - Tools for analyzing enemy trainers' Pokémon and items

This module provides functionality to search through trainer data and classify 
their Pokémon for various purposes. It also includes utilities for examining
and working with items from the game's item constants.
"""

import os
import sys
import re
from framework import Step
from steps import Trainers, TrainerData, TrainerInfo, Mons, IdentifyTier, Moves, LoadAbilityNames
from enums import Type, TrainerClass, Tier, Item, MonClass
from TypeEffectiveness import get_all_weaknesses, get_4x_weaknesses, get_type_effectiveness



class TrainerMonClassifier:
    """
    A class to classify trainer Pokémon based on different criteria.
    """
    
    
    def __init__(self, context):
        """
        Initialize the classifier with randomization context.
        
        Args:
            context (RandomizationContext): The randomization context.
        """
        self.context = context
        self.trainers = context.get(Trainers)
        
        # We're using Item enum directly, no need to load item constants
        
        # Try to load required data
        self.pokemon_data = context.get(Mons)
        print(f"Loaded data for {len(self.pokemon_data.data)} Pokémon species")
            
        self.type_effectiveness = {}
        self._build_type_effectiveness_table()
        
    def _build_type_effectiveness_table(self):
        """
        Build a lookup dictionary for type effectiveness using TypeEffectiveness module.
        This allows for quick lookup of matchups for weakness detection.
        """
        # Get all standard types (excluding STELLAR)
        standard_types = list(Type)
        
        # Initialize all type combinations with normal effectiveness (1.0)
        for atk_type in standard_types:
            self.type_effectiveness[atk_type.value] = {}
            for def_type in standard_types:
                self.type_effectiveness[atk_type.value][def_type.value] = 1.0
        
        # Apply type effectiveness from TypeEffectiveness module
        for atk_type in standard_types:
            for def_type in standard_types:
                # Get effectiveness from TypeEffectiveness module
                effectiveness = get_type_effectiveness(atk_type, def_type)
                self.type_effectiveness[atk_type.value][def_type.value] = effectiveness
        
        # Load move data
        self.move_data = self.context.get(Moves)
        print(f"Loaded data for {len(self.move_data.data)} moves")
            
        # Load ability data
        self.ability_data = self.context.get(LoadAbilityNames)
        print(f"Loaded ability names")
    
    def find_pokemon_by_species(self, species_id):
        """
        Find all trainer Pokémon of a specific species.
        
        Args:
            species_id (int): The Pokémon species ID to search for.
            
        Returns:
            list: A list of (trainer, pokemon) tuples containing the matching Pokémon.
        """
        results = []
        
        for trainer in self.trainers.data:
            if not trainer.team:
                continue
                
            for pokemon in trainer.team:
                if pokemon.species_id == species_id:
                    results.append((trainer, pokemon))
        
        return results
    
    def find_pokemon_by_type(self, type_id):
        """
        Find all trainer Pokémon of a specific type.
        
        Args:
            type_id (int): The type ID to search for.
            
        Returns:
            list: A list of (trainer, pokemon) tuples containing Pokémon of that type.
        """
        results = []
        
        for trainer in self.trainers.data:
            if not trainer.team:
                continue
                
            for pokemon in trainer.team:
                mon = self.pokemon_data.data.get(pokemon.species_id)
                if not mon:
                    continue
                    
                if mon.type1 == type_id or mon.type2 == type_id:
                    results.append((trainer, pokemon))
        
        return results
    
    def find_pokemon_by_held_item(self, item_id):
        """
        Useful for Eviolite and Species-specific items like LIght ball/Thick Club
        
        Args:
            item_id (int): The item ID to search for.
            
        Returns:
            list: A list of (trainer, pokemon) tuples containing Pokémon holding that item.
        """
        results = []
        
        for trainer in self.trainers.data:
            if not trainer.team:
                continue
                
            for pokemon in trainer.team:
                if hasattr(pokemon, 'held_item') and pokemon.held_item == item_id:
                    results.append((trainer, pokemon))
        
        return results
    
    def find_trainers_by_class(self, trainer_class):
        return [trainer for trainer in self.trainers.data 
                if trainer.info.trainerclass == trainer_class]
    
    def find_trainers_by_tier(self, tier):
        """
        Find all trainers of a specific tier.
        
        Args:
            tier (Tier): The tier enum to search for.
            
        Returns:
            list: A list of trainers in that tier.
        """
        # Get the IdentifyTier step from context
        tier_step = self.context.get(IdentifyTier)
            
        # IdentifyTier stores tier data in its data dictionary
        # Each entry maps trainer_id -> tier
        return [trainer for trainer in self.trainers.data 
                if tier_step.data.get(trainer.info.trainer_id) == tier]
    
    def classify_pokemon(self, pokemon):
        """
        Classify a Pokémon according to various criteria.
        
        Args:
            pokemon: The Pokémon to classify.
            
        Returns:
            dict: A dictionary containing detailed classifications and a set of MonClass enum values.
        """
        classifications = {}
        
        # Get species data
        try:
            mon = self.pokemon_data[pokemon.species_id]
        except (KeyError, IndexError):
            print(f"Warning: No species data for Pokémon ID {pokemon.species_id}")
            return classifications
        
        # Stat-based classifications
        self._classify_by_stats(pokemon, mon, classifications)
        
        # Type-based classifications
        self._classify_by_types(pokemon, mon, classifications)
        
        # Move-based classifications
        if hasattr(pokemon, 'moves'):
            self._classify_by_moves(pokemon, classifications)
        
        # Ability-based classifications
        if hasattr(pokemon, 'ability'):
            self._classify_by_ability(pokemon, classifications)
        
        return classifications
    
    def _classify_by_stats(self, pokemon, mon, classifications):
        """
        Apply stat-based classifications.
        
        Args:
            pokemon: The Pokémon to classify.
            mon: The species data for this Pokémon.
            classifications: Dictionary to add classifications to.
        """
        # Initialize MonClass set if not present
        if 'MonClass' not in classifications:
            classifications['MonClass'] = set()
        
        # Calculate directly using mon attributes
        
        # Offensive: highest Offensive stat (atk or sp atk) > 104
        if max(mon.attack, mon.sp_attack) > 104:
            classifications['MonClass'].add(MonClass.OFFENSIVE)
            
        # Defensive: lowest Defensive stat (Def or sp Def) > 95 or HP > 120
        if min(mon.defense, mon.sp_defense) > 95 or mon.hp > 120:
            classifications['MonClass'].add(MonClass.DEFENSIVE)
            
        # Physical Attacker: Atk > 105
        if mon.attack > 105:
            classifications['MonClass'].add(MonClass.PHYSICAL_ATTACKER)
            
        # Special Attacker: Sp Atk > 105
        if mon.sp_attack > 105:
            classifications['MonClass'].add(MonClass.SPECIAL_ATTACKER)
            
        # Frail: highest Defensive stat (def or sp Def) < 86 and HP < 86
        # (The 4x weakness part is handled in _classify_by_types)
        if max(mon.defense, mon.sp_defense) < 86 and mon.hp < 86:
            classifications['MonClass'].add(MonClass.FRAIL)
            
        # Balanced: highest offensive stat and lowest defensive stat are within 20% of each other
        highest_offensive = max(mon.attack, mon.sp_attack)
        lowest_defensive = min(mon.defense, mon.sp_defense)
        
        ratio = highest_offensive / lowest_defensive
        if 0.8 <= ratio <= 1.2:  # Within 20% of each other
            classifications['MonClass'].add(MonClass.BALANCED)
        
        # Speed classifications
        if mon.speed >= 100:
            classifications['MonClass'].add(MonClass.FAST)
        elif mon.speed >= 65:
            classifications['MonClass'].add(MonClass.MIDSPEED)
        else:
            classifications['MonClass'].add(MonClass.SLOW)
    

    def _classify_by_moves(self, pokemon, classifications):
        """
        Apply move-based classifications.
        
        Args:
            pokemon: The Pokémon to classify.
            classifications: Dictionary to add classifications to.
        """
        has_moves = {}
        
        for move_id in pokemon.moves:
            if move_id == 0:
                continue  # Skip empty move slots
                
            # Moves.data is a list indexed by move_id
            if 0 <= move_id < len(self.move_data.data):
                move_data = self.move_data.data[move_id]
                move_name = getattr(move_data, 'name', None) or f"Move {move_id}"
                # Store move in the HasMove classification
                has_moves[move_name] = True
        
        if has_moves:
            classifications["HasMove"] = has_moves
    
    def _classify_by_ability(self, pokemon, classifications):
        """
        Apply ability-based classifications.
        
        Args:
            pokemon: The Pokémon to classify.
            classifications: Dictionary to add classifications to.
        """
        if not hasattr(pokemon, 'ability') or not self.ability_data:
            # No ability data available
            return
            
        ability_id = pokemon.ability
        if ability_id > 0 and ability_id in self.ability_data.id_to_name:
            ability_name = self.ability_data.id_to_name[ability_id]
            
            # Store ability in the HasAbility classification
            classifications["HasAbility"] = ability_name
    
    def get_weaknesses(self, pokemon, mon):
        """
        Calculate a Pokémon's type weaknesses using TypeEffectiveness module.
        
        Args:
            pokemon: The Pokémon to classify.
            mon: The species data for this Pokémon.
            
        Returns:
            dict: Dictionary of attacking_type -> effectiveness (multiplier).
        """
        # Extract types - mon.type1 and mon.type2 are already Type enum objects from Mons extractor
        type1 = mon.type1
        type2 = mon.type2
        
        if type1 is None:
            print(f"Warning: No primary type for Pokémon species {pokemon.species_id}")
            return {}
        
        try:
            # type1 and type2 are already Type enum objects from the Mons extractor
            # No isinstance checks needed - trust the high-level API
            
            # Calculate weaknesses using TypeEffectiveness module
            if type2 is None or type2 == type1:  # Single-type or same dual-type
                return get_all_weaknesses(type1)
            else:  # Dual-type
                return get_all_weaknesses(type1, type2)
                
        except (AttributeError, TypeError, ValueError) as e:
            print(f"Warning: Error calculating weaknesses for species {pokemon.species_id}: {e}")
            return {}
            
            
    def _classify_by_types(self, pokemon, mon, classifications):
        """
        Apply type-based classifications.
        
        Args:
            pokemon: The Pokémon to classify.
            mon: The species data for this Pokémon.
            classifications: Dictionary to add classifications to.
        """
        # Extract types - mon.type1 and mon.type2 are already Type enum objects from Mons extractor
        type1 = mon.type1
        type2 = mon.type2
        
        # For primary type
        if type1 is not None:
            classifications['Type1'] = {
                'id': type1,
                'name': str(type1)
            }
        # For secondary type
        if type2 is not None and type2 != type1:  # Avoid duplicate types
            classifications['Type2'] = {
                'id': type2,
                'name': str(type2)
            }
        
        # Calculate weaknesses using TypeEffectiveness module
        weaknesses = self.get_weaknesses(pokemon)
        
        if weaknesses:
            classifications['Weaknesses'] = {
                'normal': [],  # 1x weakness (not actually a weakness)
                'weak': [],    # 2x weakness
                'very_weak': [] # 4x weakness
            }
            
            # Organize weaknesses by effectiveness
            for attack_type, effectiveness in weaknesses.items():
                if effectiveness > 1.0:
                    if effectiveness >= 4.0:
                        classifications['Weaknesses']['very_weak'].append({
                            'type_id': attack_type,
                            'type_name': str(attack_type),
                            'effectiveness': effectiveness
                        })
                        # If a Pokémon has a 4x weakness, it's considered Frail
                        if 'MonClass' not in classifications:
                            classifications['MonClass'] = set()
                        classifications['MonClass'].add(MonClass.FRAIL)
                    elif effectiveness >= 2.0:
                        classifications['Weaknesses']['weak'].append({
                            'type_id': attack_type,
                            'type_name': str(attack_type),
                            'effectiveness': effectiveness
                        })
            
    
    def _classify_by_moves(self, pokemon, classifications):
        """
        Apply move-based classifications.
        
        Args:
            pokemon: The Pokémon to classify.
            classifications: Set to add MonClass classifications to.
        """
        if not hasattr(pokemon, 'moves') or not pokemon.moves:
            return
        
        move_ids = pokemon.moves
        classifications['Moves'] = []
        
        for move_id in move_ids:
            if move_id == 0:  # No move in this slot
                continue
                
            # Moves.data is a list indexed by move_id
            if self.move_data and 0 <= move_id < len(self.move_data.data):
                move = self.move_data.data[move_id]
                move_name = getattr(move, 'name', None) or f"Move {move_id}"
                classifications['Moves'].append(move_name)
            else:
                classifications['Moves'].append(f"Unknown Move {move_id}")
    
    def _classify_by_ability(self, pokemon, classifications):
        """
        Apply ability-based classifications.
        
        Args:
            pokemon: The Pokémon to classify.
            classifications: Dictionary to add classifications to.
        """
        if not hasattr(pokemon, 'ability') or pokemon.ability == 0:
            return
        
        ability_id = pokemon.ability
        
        if self.ability_data and ability_id in self.ability_data.id_to_name:
            ability_name = self.ability_data.id_to_name[ability_id]
            classifications['Ability'] = ability_name
        else:
            classifications['Ability'] = f"Unknown Ability {ability_id}"
    
    def classify_all_trainer_pokemon(self):
        """
        Classify all trainer Pokémon in the ROM.
        
        Returns:
            dict: A dictionary mapping trainer IDs to lists of classified Pokémon.
        """
        results = {}
        
        for trainer in self.trainers.data:
            if not trainer.team:
                continue
            
            trainer_id = trainer.info.trainer_id
            trainer_name = getattr(trainer.info, 'name', f"Trainer {trainer_id}")
            trainer_results = []
            
            for pokemon in trainer.team:
                species_id = pokemon.species_id
                species_name = "Unknown"
                
                if self.pokemon_data and species_id in self.pokemon_data.data:
                    species_name = getattr(self.pokemon_data[species_id], 'name', f"Species {species_id}")
                
                level = getattr(pokemon, 'level', 0)
                classifications = self.classify_pokemon(pokemon)
                
                trainer_results.append({
                    'species_id': species_id,
                    'species_name': species_name,
                    'level': level,
                    'classifications': classifications
                })
            
            results[trainer_id] = {
                'trainer_name': trainer_name,
                'pokemon': trainer_results
            }
        
        return results
    
    def has_type(self, pokemon, type_id):
        """
        Check if a Pokémon has a specific type.
        
        Args:
            pokemon: The Pokémon to check.
            type_id: The type ID to check for.
            
        Returns:
            bool: True if the Pokémon has the specified type, False otherwise.
        """
        if not self.pokemon_data or pokemon.species_id not in self.pokemon_data.data:
            return False
        
        mon = self.pokemon_data[pokemon.species_id]
        type1 = mon.type1
        type2 = mon.type2
        
        return type1 == type_id or type2 == type_id
    
    def has_move(self, pokemon, move_id):
        """
        Check if a Pokémon has a specific move.
        
        Args:
            pokemon: The Pokémon to check.
            move_id: The move ID to check for.
            
        Returns:
            bool: True if the Pokémon has the specified move, False otherwise.
        """
        if not hasattr(pokemon, 'moves') or not pokemon.moves:
            return False
        
        return move_id in pokemon.moves
    
    def has_ability(self, pokemon, ability_id):
        """
        Check if a Pokémon has a specific ability.
        
        Args:
            pokemon: The Pokémon to check.
            ability_id: The ability ID to check for.
            
        Returns:
            bool: True if the Pokémon has the specified ability, False otherwise.
        """
        if not hasattr(pokemon, 'ability'):
            return False
        
        return pokemon.ability == ability_id
    
    def get_type_id(self, type_value):
        """
        Get the numeric ID of a type from its value.
        
        Args:
            type_value: Type value (enum, string, or integer).
            
        Returns:
            int: ID of the type (0-17), or -1 if invalid.
        """
        # Type name to ID mapping
        type_map = {
            'NORMAL': Type.NORMAL,
            'FIGHTING': Type.FIGHTING,
            'FLYING': Type.FLYING,
            'POISON': Type.POISON,
            'GROUND': Type.GROUND,
            'ROCK': Type.ROCK,
            'BUG': Type.BUG,
            'GHOST': Type.GHOST,
            'STEEL': Type.STEEL,
            'FIRE': Type.FIRE,
            'WATER': Type.WATER,
            'GRASS': Type.GRASS,
            'ELECTRIC': Type.ELECTRIC,
            'PSYCHIC': Type.PSYCHIC,
            'ICE': Type.ICE,
            'DRAGON': Type.DRAGON,
            'DARK': Type.DARK,
            'FAIRY': Type.FAIRY
        }
        
        try:
            # Case 1: It's a string (like 'FIRE', 'WATER', etc.)
            if isinstance(type_value, str):
                return type_map.get(type_value.upper(), -1)
            
            # Case 2: It has a name attribute (like EnumIntegerString or Enum)
            elif hasattr(type_value, 'name'):
                type_name = str(type_value.name)
                return type_map.get(type_name, -1)
            
            # Case 3: It's already an integer between 0 and 17
            elif isinstance(type_value, int) and 0 <= type_value < 18:
                return type_value
            
            # Case 4: It's an unknown format but we can get a string representation
            else:
                type_str = str(type_value).upper()
                # Check if the string is a valid type name
                if type_str in type_map:
                    return type_map[type_str]
                # Check if it can be converted to an integer between 0-17
                elif type_str.isdigit() and 0 <= int(type_str) < 18:
                    return int(type_str)
        except Exception as e:
            pass
        
        # If we get here, we couldn't determine the type ID
        return -1

    def get_weaknesses(self, pokemon):
        """
        Get a Pokémon's type weaknesses, including 4x weaknesses.
        
        Args:
            pokemon: The Pokémon to check.
            
        Returns:
            dict: A dictionary of type IDs to weakness multipliers.
                  Or None if type effectiveness data is not available.
        """
        try:
            mon = self.pokemon_data[pokemon.species_id]
        except (KeyError, IndexError):
            print(f"Warning: No species data for Pokémon ID {pokemon.species_id}")
            return None
        type1 = mon.type1
        type2 = mon.type2
        
        if type1 is None:
            print(f"Warning: No type data for Pokémon ID {pokemon.species_id}")
            return None
        
        # Get the numeric type IDs
        type1_id = self.get_type_id(type1)
        type2_id = self.get_type_id(type2) if type2 is not None else -1
        
        if type1_id == -1:
            print(f"Warning: Invalid type1 {type1} for Pokémon ID {pokemon.species_id}")
            return None
            
        # If type2 is the same as type1 or invalid, treat the Pokémon as single-typed
        if type2_id == -1 or type1_id == type2_id:
            type2_id = None
        
        # Calculate weaknesses based on both types
        weaknesses = {}
        
        # Check effectiveness of all attack types against this Pokémon's type(s)
        for attack_type in range(18):  # 0-17 type IDs
            # Start with effectiveness against type1
            multiplier = self.type_effectiveness[attack_type].get(type1_id, 1.0)
            
            # If there's a second type, multiply by effectiveness against type2
            if type2_id is not None:
                multiplier *= self.type_effectiveness[attack_type].get(type2_id, 1.0)
            
            # Only include non-neutral effectiveness
            if multiplier != 1.0:
                weaknesses[attack_type] = multiplier
        
        return weaknesses
    
    def has_stat(self, pokemon, stat_name, condition):
        """
        Check if a Pokémon's stat meets a condition.
        
        Args:
            pokemon: The Pokémon to check.
            stat_name: The name of the stat (hp, attack, defense, sp_attack, sp_defense, speed).
            condition: A function that takes a stat value and returns a boolean.
            
        Returns:
            bool: True if the condition is met, False otherwise.
        """
        if not self.pokemon_data or pokemon.species_id not in self.pokemon_data.data:
            return False
        
        mon = self.pokemon_data[pokemon.species_id]
        
        # Access the stat directly by name
        try:
            stat_value = getattr(mon, stat_name)
        except AttributeError:
            return False
        return condition(stat_value)


class AssignItemsStep(Step):
    """
    Base class for steps that assign items to trainer Pokémon.
    """
    
    def __init__(self):
        super().__init__()
    
    def run(self, context):
        """
        Run the step to assign items to trainer Pokémon.
        
        Args:
            context (RandomizationContext): The randomization context.
            
        Returns:
            int: Number of Pokémon that were assigned items.
        """
        # This is a placeholder - specific item assignment steps will override this
        pass

