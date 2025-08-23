#!/usr/bin/env python3
"""
Script to read and validate CustomSetsPokemon.json format.

This script can parse the custom Pokemon sets format and convert it into data
that can be used with our move selection tools.
"""

import json
import os
from typing import Dict, List, Any, Optional

class CustomSetsReader:
    """Reader for CustomSetsPokemon.json format."""
    
    def __init__(self, json_file_path: str):
        """Initialize the reader with a JSON file path.
        
        Args:
            json_file_path (str): Path to the CustomSetsPokemon.json file
        """
        self.json_file_path = json_file_path
        self.data = None
        self.sets = []
        
    def load_data(self) -> bool:
        """Load and parse the JSON data.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.json_file_path):
                print(f"Error: File not found: {self.json_file_path}")
                return False
                
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
                
            # Extract the sets array
            if 'sets' not in self.data:
                print("❌ Error: No 'sets' key found in JSON data")
                return False
                
            self.sets = self.data['sets']
            print(f"Successfully loaded {len(self.sets)} Pokemon sets")
            return True
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return False
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def validate_structure(self) -> bool:
        """Validate the structure of the loaded data.
        
        Returns:
            bool: True if structure is valid, False otherwise
        """
        if not self.data or not self.sets:
            print("No data loaded")
            return False
            
        print("Validating data structure...")
        
        # Check top-level structure
        required_top_keys = ['generation', 'last_updated', 'sets']
        for key in required_top_keys:
            if key not in self.data:
                print(f"❌ Missing top-level key: {key}")
                return False
        
        # Check each Pokemon set
        required_set_keys = ['species', 'name', 'moves', 'ability', 'generation', 'timestamp']
        required_move_keys = ['name', 'source', 'display_name', 'slot']
        required_ability_keys = ['name', 'display_name']
        
        for i, pokemon_set in enumerate(self.sets):
            # Check Pokemon set structure
            for key in required_set_keys:
                if key not in pokemon_set:
                    print(f"❌ Pokemon set {i}: Missing key '{key}'")
                    return False
            
            # Check moves structure
            moves = pokemon_set.get('moves', [])
            if len(moves) != 4:
                print(f"❌ Pokemon set {i} ({pokemon_set.get('name', 'Unknown')}): Expected 4 moves, got {len(moves)}")
                return False
                
            for j, move in enumerate(moves):
                for key in required_move_keys:
                    if key not in move:
                        print(f"❌ Pokemon set {i}, move {j}: Missing key '{key}'")
                        return False
                        
                # Validate slot numbers (should be 1-4)
                slot = move.get('slot')
                if not isinstance(slot, int) or slot < 1 or slot > 4:
                    print(f"❌ Pokemon set {i}, move {j}: Invalid slot number {slot}")
                    return False
            
            # Check ability structure
            ability = pokemon_set.get('ability', {})
            for key in required_ability_keys:
                if key not in ability:
                    print(f"❌ Pokemon set {i}: Missing ability key '{key}'")
                    return False
        
        print("✅ Data structure validation passed")
        return True
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about the loaded data.
        
        Returns:
            Dict containing summary statistics
        """
        if not self.sets:
            return {}
            
        stats = {
            'total_pokemon': len(self.sets),
            'generation': self.data.get('generation'),
            'last_updated': self.data.get('last_updated'),
            'move_sources': {},
            'species_list': [],
            'unique_moves': set(),
            'unique_abilities': set()
        }
        
        for pokemon_set in self.sets:
            # Collect species
            stats['species_list'].append({
                'species': pokemon_set['species'],
                'name': pokemon_set['name']
            })
            
            # Collect move sources
            for move in pokemon_set.get('moves', []):
                source = move.get('source', 'unknown')
                stats['move_sources'][source] = stats['move_sources'].get(source, 0) + 1
                stats['unique_moves'].add(move.get('name', ''))
            
            # Collect abilities
            ability = pokemon_set.get('ability', {})
            stats['unique_abilities'].add(ability.get('name', ''))
        
        # Convert sets to counts for JSON serialization
        stats['unique_moves_count'] = len(stats['unique_moves'])
        stats['unique_abilities_count'] = len(stats['unique_abilities'])
        stats['unique_moves'] = sorted(list(stats['unique_moves']))
        stats['unique_abilities'] = sorted(list(stats['unique_abilities']))
        
        return stats
    
    def print_summary(self):
        """Print a summary of the loaded data."""
        if not self.sets:
            print("❌ No data to summarize")
            return
            
        stats = self.get_summary_stats()
        
        print("\n📊 CUSTOM SETS SUMMARY")
        print("=" * 50)
        print(f"Total Pokemon: {stats['total_pokemon']}")
        print(f"Generation: {stats['generation']}")
        print(f"Last Updated: {stats['last_updated']}")
        print(f"Unique Moves: {stats['unique_moves_count']}")
        print(f"Unique Abilities: {stats['unique_abilities_count']}")
        
        print("\n📋 Move Sources:")
        for source, count in sorted(stats['move_sources'].items()):
            print(f"  {source}: {count} moves")
        
        print(f"\n🎯 First 10 Pokemon:")
        for i, pokemon in enumerate(stats['species_list'][:10]):
            print(f"  {i+1}. {pokemon['name']} ({pokemon['species']})")
        
        if len(stats['species_list']) > 10:
            print(f"  ... and {len(stats['species_list']) - 10} more")
    
    def get_pokemon_by_species(self, species_name: str) -> Optional[Dict[str, Any]]:
        """Get a Pokemon set by species name.
        
        Args:
            species_name (str): Species identifier (e.g., "SPECIES_ABSOL")
            
        Returns:
            Dict containing the Pokemon set, or None if not found
        """
        for pokemon_set in self.sets:
            if pokemon_set.get('species') == species_name:
                return pokemon_set
        return None
    
    def get_moves_for_pokemon(self, species_name: str) -> List[Dict[str, Any]]:
        """Get the moves for a specific Pokemon.
        
        Args:
            species_name (str): Species identifier
            
        Returns:
            List of move dictionaries
        """
        pokemon_set = self.get_pokemon_by_species(species_name)
        if pokemon_set:
            return pokemon_set.get('moves', [])
        return []


def main():
    """Main function to test the CustomSetsReader."""
    # Path to the CustomSetsPokemon.json file
    json_file = r"c:\Users\Russell\Documents\GitHub\hg-engine\pokemon_sets\collections\CustomSetsPokemon.json"
    
    print("🎯 CUSTOM SETS READER - VALIDATION TEST")
    print("=" * 60)
    
    # Create reader and load data
    reader = CustomSetsReader(json_file)
    
    if not reader.load_data():
        print("❌ Failed to load data")
        return
    
    if not reader.validate_structure():
        print("❌ Data structure validation failed")
        return
    
    # Print summary
    reader.print_summary()
    
    # Test specific Pokemon lookup
    print("\n🔍 TESTING POKEMON LOOKUP")
    print("=" * 30)
    
    test_species = ["SPECIES_ABSOL", "SPECIES_AERODACTYL", "SPECIES_ALAKAZAM"]
    
    for species in test_species:
        pokemon_set = reader.get_pokemon_by_species(species)
        if pokemon_set:
            print(f"\n✅ Found {pokemon_set['name']} ({species}):")
            moves = pokemon_set.get('moves', [])
            for move in moves:
                print(f"  Slot {move['slot']}: {move['display_name']} ({move['source']})")
            ability = pokemon_set.get('ability', {})
            print(f"  Ability: {ability.get('display_name', 'Unknown')}")
        else:
            print(f"❌ {species} not found")
    
    print("\n✅ Validation complete! The CustomSetsPokemon.json format is readable.")


if __name__ == "__main__":
    main()
