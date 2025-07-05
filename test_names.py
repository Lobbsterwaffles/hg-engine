"""
Test script to check if we can read Pokémon names correctly
"""

# First, try to read names directly from the file
print("Trying to read Pokémon names from build/rawtext/237.txt...")

try:
    # This is the approach used in pokemon_shared.py
    with open("build/rawtext/237.txt", "r", encoding="utf-8") as f:
        names = [line.strip() for line in f.readlines()]
        
    print(f"Successfully read {len(names)} Pokémon names!")
    print(f"First 10 Pokémon: {names[:10]}")
    
    # Let's count how many non-empty names we have
    non_empty = [name for name in names if name.strip()]
    print(f"Found {len(non_empty)} non-empty names")
    
except Exception as e:
    print(f"Error reading names: {e}")

# Now try to import the function from pokemon_shared
print("\nTrying to use read_pokemon_names from pokemon_shared.py...")

try:
    from pokemon_shared import read_pokemon_names
    
    names = read_pokemon_names(".")
    print(f"Successfully read {len(names)} Pokémon names!")
    print(f"First 10 Pokémon: {names[:10]}")
    
except Exception as e:
    print(f"Error using read_pokemon_names: {e}")
