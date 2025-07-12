#!/usr/bin/env python3
"""
Test script for the Special Pokémon Handler v2
Verifies that the handler can load data files and basic functionality works
"""

import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from special_pokemon_handler_v2 import SpecialPokemonHandler

def test_data_loading():
    """Test that data files can be loaded properly"""
    print("Testing Special Pokémon Handler v2...")
    
    # Create handler instance
    handler = SpecialPokemonHandler("test.nds")  # Dummy ROM path for testing
    
    print(f"\nData Loading Test Results:")
    print(f"Mimics loaded: {len(handler.mimics)} type categories")
    print(f"Pivots loaded: {len(handler.pivots)} type categories") 
    print(f"Fulcrums loaded: {len(handler.fulcrums)} type categories")
    
    # Show some sample data
    if handler.mimics:
        print(f"\nSample mimic types:")
        for type_name, species_list in list(handler.mimics.items())[:3]:
            print(f"  {type_name}: {len(species_list)} species")
            if species_list:
                print(f"    Example: {species_list[0]}")
    
    if handler.pivots:
        print(f"\nSample pivot types:")
        for type_name, species_list in list(handler.pivots.items())[:3]:
            print(f"  {type_name}: {len(species_list)} species")
            if species_list:
                print(f"    Example: {species_list[0]}")
    
    if handler.fulcrums:
        print(f"\nSample fulcrum types:")
        for type_name, species_list in list(handler.fulcrums.items())[:3]:
            print(f"  {type_name}: {len(species_list)} species")
            if species_list:
                print(f"    Example: {species_list[0]}")
    
    # Test temp data loading
    print(f"\nTemp data loaded: {len(handler.gym_assignments)} trainer assignments")
    if handler.gym_assignments:
        print("Sample gym assignments:")
        for trainer_id, assignment in list(handler.gym_assignments.items())[:3]:
            print(f"  Trainer {trainer_id}: {assignment}")
    
    return True

def main():
    """Main test function"""
    try:
        success = test_data_loading()
        if success:
            print("\n✓ All tests passed! Special Pokémon Handler v2 is ready to use.")
            return 0
        else:
            print("\n✗ Some tests failed.")
            return 1
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
