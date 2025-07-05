#!/usr/bin/env python3
"""
Handles type-themed gyms for the Pokémon Trainer Randomizer.

This module provides functions to:
- Read gym type information from a JSON file
- Find trainers associated with gyms
- Select Pokémon of appropriate types for gym trainers
"""

import json
import os
import random


def read_gym_types(base_path=".", randomize_types=True, seed=None):
    """
    Read the gym type definitions from the JSON file and optionally randomize their types.
    
    Args:
        base_path: Base directory path for finding the gym_types.json file
        randomize_types: If True, randomly assign a type to each gym
        seed: Random seed for consistent results
        
    Returns:
        Dictionary of gym type information
    """
    # List of all Pokémon types
    all_types = [
        "Normal", "Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", 
        "Steel", "Fire", "Water", "Grass", "Electric", "Psychic", "Ice", "Dragon", "Dark", "Fairy"
    ]
    
    gym_types_path = os.path.join(base_path, "data", "gym_types.json")
    
    try:
        with open(gym_types_path, "r") as f:
            gym_types = json.load(f)
            
        # If randomize_types is enabled, assign a random type to each gym
        if randomize_types:
            # Set seed if provided
            if seed is not None:
                random.seed(seed)
                
            # Keep track of assigned types to avoid duplicates if possible
            assigned_types = []
            available_types = all_types.copy()
            
            print("Randomly assigning types to gyms:")
            for gym_location in gym_types:
                # If we've used all types, refill the available types
                if not available_types:
                    available_types = [t for t in all_types if t not in assigned_types[-3:]]  # Avoid recent duplicates
                
                # Choose a random type from available types
                random_type = random.choice(available_types)
                available_types.remove(random_type)  # Remove to avoid immediate duplicates
                assigned_types.append(random_type)
                
                # Update the gym's type
                original_type = gym_types[gym_location]["type"]
                gym_types[gym_location]["type"] = random_type
                print(f"  {gym_location}: {original_type} -> {random_type}")
                
        return gym_types
    except FileNotFoundError:
        print(f"Warning: Gym types file not found at {gym_types_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Warning: Error parsing gym types file at {gym_types_path}")
        return {}


def get_trainer_gym_type(trainer_name, gym_types):
    """
    Find which gym a trainer belongs to and get the associated type.
    
    Args:
        trainer_name: The name of the trainer
        gym_types: Dictionary of gym type information
        
    Returns:
        Tuple of (type_name, is_gym_leader) or (None, False) if not found
    """
    # Check if trainer is a gym leader
    for gym_location, gym_info in gym_types.items():
        if gym_info.get("leader", "").lower() == trainer_name.lower():
            return gym_info.get("type"), True
            
        # Check if trainer is a gym trainer
        for gym_trainer in gym_info.get("trainers", []):
            if gym_trainer.lower() == trainer_name.lower():
                return gym_info.get("type"), False
                
    # Not a gym trainer or leader
    return None, False


def get_pokemon_by_type(type_name, mondata, excluded_pokemon=None, secondary_type=False):
    """
    Get all Pokémon of a specific type.
    
    Args:
        type_name: Name of the Pokémon type to filter by
        mondata: List of all Pokémon data
        excluded_pokemon: Set of Pokémon IDs to exclude
        secondary_type: Whether to include Pokémon with this type as their secondary type
        
    Returns:
        List of Pokémon IDs matching the type criteria
    """
    if excluded_pokemon is None:
        excluded_pokemon = set()
        
    # Map type names to type IDs
    type_map = {
        "Normal": 0,
        "Fighting": 1,
        "Flying": 2,
        "Poison": 3,
        "Ground": 4,
        "Rock": 5,
        "Bug": 6,
        "Ghost": 7,
        "Steel": 8,
        "Fire": 9,
        "Water": 10,
        "Grass": 11,
        "Electric": 12,
        "Psychic": 13,
        "Ice": 14,
        "Dragon": 15,
        "Dark": 16,
        "Fairy": 17
    }
    
    # Get type ID from name
    type_id = type_map.get(type_name)
    if type_id is None:
        print(f"Warning: Unknown type '{type_name}'")
        return []
        
    # Find all Pokémon of the specified type
    pokemon_of_type = []
    
    for i, mon in enumerate(mondata):
        # Skip if in excluded list
        if i in excluded_pokemon:
            continue
            
        # Skip if name is placeholder
        if mon.name == "-----":
            continue
            
        # Check if primary type matches
        if mon.type1 == type_id:
            pokemon_of_type.append(i)
        # Check secondary type if requested
        elif secondary_type and mon.type2 == type_id:
            pokemon_of_type.append(i)
            
    return pokemon_of_type


def select_themed_replacement(original_mon, mondata, type_name, excluded_pokemon=None, bst_range=0.2):
    """
    Select a replacement Pokémon of the specified type with similar BST.
    
    Args:
        original_mon: The original Pokémon data
        mondata: List of all Pokémon data
        type_name: Type to use for replacement
        excluded_pokemon: Set of Pokémon IDs to exclude
        bst_range: The acceptable BST range as a percentage (e.g., 0.2 for ±20%)
        
    Returns:
        ID of a suitable replacement Pokémon, or None if none found
    """
    if excluded_pokemon is None:
        excluded_pokemon = set()
        
    # Get primary type Pokémon
    primary_type_pokemon = get_pokemon_by_type(type_name, mondata, excluded_pokemon, False)
    
    # If there aren't enough primary type Pokémon, include secondary type
    if len(primary_type_pokemon) < 5:
        primary_type_pokemon = get_pokemon_by_type(type_name, mondata, excluded_pokemon, True)
    
    if not primary_type_pokemon:
        return None
        
    # Calculate BST range
    target_bst = original_mon.bst
    min_bst = target_bst * (1 - bst_range)
    max_bst = target_bst * (1 + bst_range)
    
    # Find Pokémon within BST range
    in_range_pokemon = [
        i for i in primary_type_pokemon
        if min_bst <= mondata[i].bst <= max_bst
    ]
    
    # If no Pokémon in BST range, use any of the correct type
    if not in_range_pokemon:
        return random.choice(primary_type_pokemon)
    
    # Otherwise, choose from type + BST range
    return random.choice(in_range_pokemon)
