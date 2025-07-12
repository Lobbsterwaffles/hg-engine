#!/usr/bin/env python3
"""
Utility functions for saving and loading gym type data between randomization scripts.
This provides a consistent way for scripts in the pipeline to share gym type information.
"""

import json
import os
from datetime import datetime

def save_gym_type_data(rom_path, gym_types):
    """
    Save gym type assignments to a JSON file that other scripts can read.
    
    Args:
        rom_path (str): Path to the ROM file
        gym_types (dict): Dictionary mapping trainer IDs to their assigned gym types
        
    Returns:
        str: Path to the saved file
    """
    # Create temp directory if it doesn't exist
    rom_dir = os.path.dirname(rom_path)
    temp_dir = os.path.join(rom_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create the gym types data structure
    data = {
        "timestamp": datetime.now().isoformat(),
        "rom_path": rom_path,
        "gym_types": gym_types
    }
    
    # Save to a dedicated gym types file
    gym_types_file = os.path.join(temp_dir, "gym_types.json")
    with open(gym_types_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved gym type assignments to {gym_types_file}")
    return gym_types_file

def load_gym_type_data(rom_path):
    """
    Load gym type assignments from the JSON file.
    
    Args:
        rom_path (str): Path to the ROM file
        
    Returns:
        dict: Dictionary of gym type assignments or empty dict if not found
    """
    rom_dir = os.path.dirname(rom_path)
    temp_dir = os.path.join(rom_dir, "temp")
    gym_types_file = os.path.join(temp_dir, "gym_types.json")
    
    try:
        with open(gym_types_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("gym_types", {})
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: No gym type assignments found at {gym_types_file}")
        return {}

def cleanup_gym_type_data(rom_path):
    """
    Clean up the gym type data file.
    
    Args:
        rom_path (str): Path to the ROM file
    """
    rom_dir = os.path.dirname(rom_path)
    temp_dir = os.path.join(rom_dir, "temp")
    gym_types_file = os.path.join(temp_dir, "gym_types.json")
    
    try:
        os.remove(gym_types_file)
    except FileNotFoundError:
        pass
