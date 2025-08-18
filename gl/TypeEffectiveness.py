#!/usr/bin/env python3
"""
TypeEffectiveness.py

This file contains type effectiveness data as (attacker, defender) type tuples.
Each list represents a different effectiveness multiplier:
- not_eff: Not very effective (0.5x)
- sup_eff: Super effective (2x)
- no_eff: No effect (0x)

Using Type enum directly for clarity and maintainability.
"""

from enums import Type

# Not very effective (0.5x) - attacker does half damage to defender
not_eff = [
    # NORMAL attacking...
    (Type.NORMAL, Type.ROCK),
    (Type.NORMAL, Type.STEEL),
    
    # FIGHTING attacking...
    (Type.FIGHTING, Type.FLYING),
    (Type.FIGHTING, Type.POISON),
    (Type.FIGHTING, Type.BUG),
    (Type.FIGHTING, Type.PSYCHIC),
    (Type.FIGHTING, Type.FAIRY),  # if implemented
    
    # FLYING attacking...
    (Type.FLYING, Type.ROCK),
    (Type.FLYING, Type.STEEL),
    
    # POISON attacking...
    (Type.POISON, Type.POISON),
    (Type.POISON, Type.GROUND),
    (Type.POISON, Type.ROCK),
    (Type.POISON, Type.GHOST),
    
    # GROUND attacking...
    (Type.GROUND, Type.BUG),
    (Type.GROUND, Type.GRASS),
    
    # ROCK attacking...
    (Type.ROCK, Type.FIGHTING),
    (Type.ROCK, Type.GROUND),
    (Type.ROCK, Type.STEEL),
    
    # BUG attacking...
    (Type.BUG, Type.FIGHTING),
    (Type.BUG, Type.FLYING),
    (Type.BUG, Type.POISON),
    (Type.BUG, Type.GHOST),
    (Type.BUG, Type.STEEL),
    (Type.BUG, Type.FIRE),
    (Type.BUG, Type.FAIRY),  # if implemented
    
    # GHOST attacking...
    (Type.GHOST, Type.DARK),
    
    # STEEL attacking...
    (Type.STEEL, Type.STEEL),
    (Type.STEEL, Type.FIRE),
    (Type.STEEL, Type.WATER),
    (Type.STEEL, Type.ELECTRIC),
    
    # FAIRY attacking...
    (Type.FAIRY, Type.POISON),
    (Type.FAIRY, Type.STEEL),
    (Type.FAIRY, Type.FIRE),
    
    # FIRE attacking...
    (Type.FIRE, Type.ROCK),
    (Type.FIRE, Type.FIRE),
    (Type.FIRE, Type.WATER),
    (Type.FIRE, Type.DRAGON),
    
    # WATER attacking...
    (Type.WATER, Type.WATER),
    (Type.WATER, Type.GRASS),
    (Type.WATER, Type.DRAGON),
    
    # GRASS attacking...
    (Type.GRASS, Type.FLYING),
    (Type.GRASS, Type.POISON),
    (Type.GRASS, Type.BUG),
    (Type.GRASS, Type.STEEL),
    (Type.GRASS, Type.FIRE),
    (Type.GRASS, Type.GRASS),
    (Type.GRASS, Type.DRAGON),
    
    # ELECTRIC attacking...
    (Type.ELECTRIC, Type.GRASS),
    (Type.ELECTRIC, Type.ELECTRIC),
    (Type.ELECTRIC, Type.DRAGON),
    
    # PSYCHIC attacking...
    (Type.PSYCHIC, Type.STEEL),
    (Type.PSYCHIC, Type.PSYCHIC),
    
    # ICE attacking...
    (Type.ICE, Type.STEEL),
    (Type.ICE, Type.FIRE),
    (Type.ICE, Type.WATER),
    (Type.ICE, Type.ICE),
    
    # DRAGON attacking...
    (Type.DRAGON, Type.STEEL),
    
    # DARK attacking...
    (Type.DARK, Type.FIGHTING),
    (Type.DARK, Type.DARK),
]

# Super effective (2x) - attacker does double damage to defender
sup_eff = [
    # FIGHTING attacking...
    (Type.FIGHTING, Type.NORMAL),
    (Type.FIGHTING, Type.ROCK),
    (Type.FIGHTING, Type.STEEL),
    (Type.FIGHTING, Type.ICE),
    (Type.FIGHTING, Type.DARK),
    
    # FLYING attacking...
    (Type.FLYING, Type.FIGHTING),
    (Type.FLYING, Type.BUG),
    (Type.FLYING, Type.GRASS),
    
    # POISON attacking...
    (Type.POISON, Type.GRASS),
    (Type.POISON, Type.FAIRY),  # if implemented
    
    # GROUND attacking...
    (Type.GROUND, Type.POISON),
    (Type.GROUND, Type.ROCK),
    (Type.GROUND, Type.STEEL),
    (Type.GROUND, Type.FIRE),
    (Type.GROUND, Type.ELECTRIC),
    
    # ROCK attacking...
    (Type.ROCK, Type.FLYING),
    (Type.ROCK, Type.BUG),
    (Type.ROCK, Type.FIRE),
    (Type.ROCK, Type.ICE),
    
    # BUG attacking...
    (Type.BUG, Type.GRASS),
    (Type.BUG, Type.PSYCHIC),
    (Type.BUG, Type.DARK),
    
    # GHOST attacking...
    (Type.GHOST, Type.GHOST),
    (Type.GHOST, Type.PSYCHIC),
    
    # STEEL attacking...
    (Type.STEEL, Type.ROCK),
    (Type.STEEL, Type.ICE),
    (Type.STEEL, Type.FAIRY),  # if implemented
    
    # FAIRY attacking...
    (Type.FAIRY, Type.FIGHTING),
    (Type.FAIRY, Type.DRAGON),
    (Type.FAIRY, Type.DARK),
    
    # FIRE attacking...
    (Type.FIRE, Type.BUG),
    (Type.FIRE, Type.STEEL),
    (Type.FIRE, Type.GRASS),
    (Type.FIRE, Type.ICE),
    
    # WATER attacking...
    (Type.WATER, Type.GROUND),
    (Type.WATER, Type.ROCK),
    (Type.WATER, Type.FIRE),
    
    # GRASS attacking...
    (Type.GRASS, Type.GROUND),
    (Type.GRASS, Type.ROCK),
    (Type.GRASS, Type.WATER),
    
    # ELECTRIC attacking...
    (Type.ELECTRIC, Type.FLYING),
    (Type.ELECTRIC, Type.WATER),
    
    # PSYCHIC attacking...
    (Type.PSYCHIC, Type.FIGHTING),
    (Type.PSYCHIC, Type.POISON),
    
    # ICE attacking...
    (Type.ICE, Type.FLYING),
    (Type.ICE, Type.GROUND),
    (Type.ICE, Type.GRASS),
    (Type.ICE, Type.DRAGON),
    
    # DRAGON attacking...
    (Type.DRAGON, Type.DRAGON),
    
    # DARK attacking...
    (Type.DARK, Type.GHOST),
    (Type.DARK, Type.PSYCHIC),
]

# No effect (0x) - attacker does no damage to defender
no_eff = [
    (Type.NORMAL, Type.GHOST),
    (Type.FIGHTING, Type.GHOST),
    (Type.POISON, Type.STEEL),
    (Type.GROUND, Type.FLYING),
    (Type.GHOST, Type.NORMAL),
    (Type.ELECTRIC, Type.GROUND),
    (Type.PSYCHIC, Type.DARK),
    (Type.DRAGON, Type.FAIRY),  # if implemented
]

def get_type_effectiveness(attack_type, defend_type):
    """
    Calculate effectiveness multiplier of an attack type against a defending type.
    
    Args:
        attack_type: Type enum of the attacking move
        defend_type: Type enum of the defending Pokémon
        
    Returns:
        float: Effectiveness multiplier (0.0, 0.5, 1.0, or 2.0)
    """
    # Default effectiveness is neutral (1.0x)
    effectiveness = 1.0
    
    # Check if attack has no effect (0x)
    if (attack_type, defend_type) in no_eff:
        return 0.0
    
    # Check if attack is not very effective (0.5x)
    if (attack_type, defend_type) in not_eff:
        effectiveness *= 0.5
    
    # Check if attack is super effective (2x)
    if (attack_type, defend_type) in sup_eff:
        effectiveness *= 2.0
    
    return effectiveness

def get_dual_type_effectiveness(attack_type, defend_type1, defend_type2=None):
    """
    Calculate effectiveness multiplier of an attack type against a dual-typed Pokémon.
    
    Args:
        attack_type: Type enum of the attacking move
        defend_type1: Primary Type enum of the defending Pokémon
        defend_type2: Secondary Type enum of the defending Pokémon (if any)
        
    Returns:
        float: Effectiveness multiplier (0.0, 0.25, 0.5, 1.0, 2.0, or 4.0)
    """
    # If there's only one defending type, use simple effectiveness
    if defend_type2 is None or defend_type1 == defend_type2:
        return get_type_effectiveness(attack_type, defend_type1)
    
    # For dual-type, multiply the effectiveness against each type
    type1_effectiveness = get_type_effectiveness(attack_type, defend_type1)
    type2_effectiveness = get_type_effectiveness(attack_type, defend_type2)
    
    return type1_effectiveness * type2_effectiveness

def get_all_weaknesses(defend_type1, defend_type2=None):
    """
    Get all type weaknesses for a Pokémon with given type(s).
    
    Args:
        defend_type1: Primary Type enum of the Pokémon
        defend_type2: Secondary Type enum of the Pokémon (if any)
        
    Returns:
        dict: Dictionary mapping attacking Type enum to effectiveness multiplier
    """
    weaknesses = {}
    
    # Check effectiveness of each attack type against the defending type(s)
    for attack_type in Type:
            
        effectiveness = get_dual_type_effectiveness(attack_type, defend_type1, defend_type2)
        
        # Only include non-neutral effectiveness
        if effectiveness != 1.0:
            weaknesses[attack_type] = effectiveness
    
    return weaknesses

def get_4x_weaknesses(defend_type1, defend_type2=None):
    """
    Get only the 4x weaknesses for a Pokémon with given type(s).
    
    Args:
        defend_type1: Primary Type enum of the Pokémon
        defend_type2: Secondary Type enum of the Pokémon (if any)
        
    Returns:
        list: List of Type enums that the Pokémon is 4x weak to
    """
    weaknesses = get_all_weaknesses(defend_type1, defend_type2)
    return [attack_type for attack_type, effectiveness in weaknesses.items() if effectiveness >= 4.0]
