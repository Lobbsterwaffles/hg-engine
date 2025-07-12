# Trainer Data Parser Module
# Handles reading and parsing trainer data from ROM files
# Extracted from randomize_trainers.py for better code organization

from construct import *
import os
import re
import ndspy.rom
import ndspy.narc

# Debug switch - set to True to enable detailed hex debugging
DEBUG_TRAINER_PARSING = False

# Path constants
BASE_TRAINER_NARC_PATH = "a/0/5/6"

# Pokémon entry structure (each Pokémon is 8 bytes) - Fixed alignment
trainer_pokemon_struct = Struct(
    "ivs" / Int8ul,             # 1 byte - IVs
    "abilityslot" / Int8ul,     # 1 byte - Ability slot
    "level" / Int16ul,          # 2 bytes - Level (halfword)
    "species" / Int16ul,        # 2 bytes - Species ID (halfword)
    "ballseal" / Int16ul,       # 2 bytes - Ball seal (halfword, not byte!)
)

# Pokémon with moves structure (18 bytes total)
trainer_pokemon_moves_struct = Struct(
    "ivs" / Int8ul,             # 1 byte - IVs
    "abilityslot" / Int8ul,     # 1 byte - Ability slot
    "level" / Int16ul,          # 2 bytes - Level (halfword)
    "species" / Int16ul,        # 2 bytes - Species ID (halfword)
    "item" / Int16ul,           # 2 bytes - Held item
    "move1" / Int16ul,          # 2 bytes - Move 1
    "move2" / Int16ul,          # 2 bytes - Move 2
    "move3" / Int16ul,          # 2 bytes - Move 3
    "move4" / Int16ul,          # 2 bytes - Move 4
    "ballseal" / Int16ul,       # 2 bytes - Ball seal (halfword)
)

# Gym trainer data organized by location
GYM_TRAINERS = {
    "Violet City": ["Falkner", "Abe", "Rod"],
    "Azalea Town": ["Bugsy", "Al", "Benny", "Amy & Mimi"],
    "Goldenrod City": ["Victoria", "Samantha", "Carrie", "Cathy", "Whitney"],
    "Ecruteak City": ["Georgina", "Grace", "Edith", "Martha", "Morty"],
    "Cianwood City": ["Yoshi", "Lao", "Lung", "Nob", "Chuck"],
    "Olivine City": ["Jasmine"],
    "Mahogany Town": ["Pryce", "Diana", "Patton", "Deandre", "Jill", "Gerardo"],
    "Blackthorn City": ["Paulo", "Lola", "Cody", "Fran", "Mike", "Clair"],
    "Pewter City": ["Jerry", "Edwin", "Brock"],
    "Cerulean City": ["Parker", "Eddie", "Diana", "Joy", "Briana", "Misty"],
    "Vermillion City": ["Horton", "Vincent", "Gregory", "Lt. Surge"],
    "Celadon City": ["Jo & Zoe", "Michelle", "Tanya", "Julia", "Erika"],
    "Fuchsia City": ["Cindy", "Barry", "Alice", "Linda", "Janine"],
    "Saffron City": ["Rebecca", "Jared", "Darcy", "Franklin", "Sabrina"],
    "Seafoam Islands": ["Lowell", "Daniel", "Cary", "Linden", "Waldo", "Merle", "Blaine"],
    "Viridian City": ["Arabella", "Salma", "Bonita", "Elan & Ida", "Blue"],
    "Elite Four": ["Will", "Koga", "Bruno", "Karen", "Lance"]
}

# Override dictionary for duplicate trainer names
# Format: (location, trainer_name): trainer_id
GYM_TRAINER_OVERRIDES = {
    ("Mahogany Town", "Diana"): 480,  # Diana in Mahogany Town
    ("Cerulean City", "Diana"): 297,  # Diana in Cerulean City
    # Add more overrides here as needed
}

# Dictionary to store gym trainer name to ID mapping
GYM_TRAINER_IDS = {}


def read_trainer_names(base_path):
    """
    Read trainer names from the assembly file if available.
    
    Args:
        base_path (str): Base directory path for finding the trainers file
        
    Returns:
        dict: Dictionary mapping trainer IDs to names
    """
    trainer_names = {}
    try:
        # Read trainer names from the assembly file using regex
        trainer_file = os.path.join(base_path, "armips/data/trainers/trainers.s")
        with open(trainer_file, "r", encoding="utf-8") as f:
            pattern = r"trainerdata\s+(\d+),\s+\"([^\"]+)\""
            for line in f:
                match = re.search(pattern, line)
                if match:
                    idx = int(match.group(1))
                    name = match.group(2)
                    trainer_names[idx] = name
        return trainer_names
    except FileNotFoundError:
        # If file doesn't exist, return empty dict
        return {}


def map_gym_trainer_names_to_ids(trainer_names):
    """
    Create a mapping from gym trainer names to their numeric IDs.
    
    Args:
        trainer_names (dict): Dictionary mapping trainer IDs to names (from read_trainer_names)
        
    Returns:
        dict: Dictionary mapping gym locations to lists of (trainer_name, trainer_id) tuples
        
    Raises:
        ValueError: If any gym trainer name cannot be matched to a trainer ID
    """
    # Create a reverse mapping from names to IDs
    name_to_id = {}
    for trainer_id, name in trainer_names.items():
        name_to_id[name] = trainer_id
    
    # Create a mapping for gym trainers
    gym_trainer_ids = {}
    missing_trainers = []
    
    # Track duplicate trainer names
    all_trainer_locations = {}  # Maps trainer_name to list of locations where it appears
    
    # First pass: gather all occurrences of each trainer name
    for location, trainers in GYM_TRAINERS.items():
        for trainer_name in trainers:
            if trainer_name not in all_trainer_locations:
                all_trainer_locations[trainer_name] = []
            all_trainer_locations[trainer_name].append(location)
    
    # Find duplicate trainer names (appear in more than one location)
    duplicate_trainers = []
    for trainer_name, locations in all_trainer_locations.items():
        if len(locations) > 1:
            duplicate_trainers.append((trainer_name, locations))
    
    # If we found duplicates that aren't in the override dictionary, warn the user
    unhandled_duplicates = []
    for trainer_name, locations in duplicate_trainers:
        has_override = all((location, trainer_name) in GYM_TRAINER_OVERRIDES 
                          for location in locations)
        if not has_override:
            unhandled_duplicates.append((trainer_name, locations))
    
    if unhandled_duplicates:
        error_msg = "Found duplicate trainer names without overrides:\n"
        for trainer_name, locations in unhandled_duplicates:
            error_msg += f"  - {trainer_name} appears in: {', '.join(locations)}\n"
        error_msg += "\nPlease add overrides for these trainers in the GYM_TRAINER_OVERRIDES dictionary."
        raise ValueError(error_msg)
    
    # Second pass: map trainer names to IDs using overrides where applicable
    for location, trainers in GYM_TRAINERS.items():
        gym_trainer_ids[location] = []
        for trainer_name in trainers:
            # Check if there's an override for this trainer
            if (location, trainer_name) in GYM_TRAINER_OVERRIDES:
                # Use the override ID
                trainer_id = GYM_TRAINER_OVERRIDES[(location, trainer_name)]
            else:
                # Try to find an exact match
                trainer_id = name_to_id.get(trainer_name)
                
                # If no exact match, try case-insensitive match
                if trainer_id is None:
                    for name, id in name_to_id.items():
                        if name.lower() == trainer_name.lower():
                            trainer_id = id
                            break
                
                # If still no match, try partial match (for names like "Lt. Surge" vs "LtSurge")
                if trainer_id is None:
                    for name, id in name_to_id.items():
                        # Remove spaces and punctuation for comparison
                        clean_name = ''.join(c for c in name if c.isalnum()).lower()
                        clean_trainer_name = ''.join(c for c in trainer_name if c.isalnum()).lower()
                        
                        if clean_name == clean_trainer_name or \
                           clean_name in clean_trainer_name or \
                           clean_trainer_name in clean_name:
                            trainer_id = id
                            break
            
            # If we still couldn't find a match, add to the list of missing trainers
            if trainer_id is None:
                missing_trainers.append((location, trainer_name))
            
            gym_trainer_ids[location].append((trainer_name, trainer_id))
    
    # If any trainers couldn't be found, raise an error
    if missing_trainers:
        error_msg = "Could not find the following gym trainers in the ROM:\n"
        for location, trainer in missing_trainers:
            error_msg += f"  - {trainer} (in {location})\n"
        error_msg += "\nPlease check the trainer names and make sure they match the names in the ROM."
        raise ValueError(error_msg)
    
    # Update the global dictionary
    global GYM_TRAINER_IDS
    GYM_TRAINER_IDS = gym_trainer_ids
    
    return gym_trainer_ids


def get_trainer_poke_count_from_rom(rom, trainer_id):
    """
    Get the actual poke_count value from trainer data NARC (the authoritative source).
    This is the field that the boss team adjuster updates when adding Pokémon.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        
    Returns:
        int: The poke_count value from offset 3 in trainer data
    """
    try:
        # Get the trainer data NARC (a/0/5/5) - contains poke_count field
        narc_file_id = rom.filenames.idOf("a/0/5/5")
        trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
        
        # Check if trainer exists
        if trainer_id >= len(trainer_data_narc.files):
            return 0
        
        # Get trainer's data
        trainer_data = trainer_data_narc.files[trainer_id]
        
        # poke_count is at offset 3 (this is what boss team adjuster updates)
        if len(trainer_data) > 3:
            poke_count = trainer_data[3]
            return poke_count
        else:
            return 0
    except Exception as e:
        if DEBUG_TRAINER_PARSING:
            print(f"Error reading trainer {trainer_id} poke_count: {e}")
        return 0


def update_trainer_poke_count_field(rom, trainer_id, actual_count):
    """
    Update a trainer's poke_count field to match the actual Pokemon data count.
    This ensures the game loads the correct number of Pokemon for each trainer.
    
    Args:
        rom: The ROM object
        trainer_id: The trainer ID
        actual_count: The actual number of Pokemon in the trainer's data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the trainer data NARC (a/0/5/5) - contains poke_count field
        narc_file_id = rom.filenames.idOf("a/0/5/5")
        trainer_data_narc = ndspy.narc.NARC(rom.files[narc_file_id])
        
        # Check if trainer exists
        if trainer_id >= len(trainer_data_narc.files):
            return False
        
        # Get trainer's data
        trainer_data = bytearray(trainer_data_narc.files[trainer_id])
        
        # Update poke_count at offset 3
        if len(trainer_data) > 3:
            trainer_data[3] = actual_count
            
            # Save back to NARC
            trainer_data_narc.files[trainer_id] = bytes(trainer_data)
            rom.files[narc_file_id] = trainer_data_narc.save()
            
            if DEBUG_TRAINER_PARSING:
                print(f"Updated trainer {trainer_id} poke_count field to {actual_count}")
            return True
        else:
            return False
    except Exception as e:
        if DEBUG_TRAINER_PARSING:
            print(f"Error updating trainer {trainer_id} poke_count: {e}")
        return False


def read_trainer_data(rom):
    """
    Read all trainer data from ROM.
    
    Args:
        rom: The ROM object containing trainer data
        
    Returns:
        tuple: (trainers_list, trainer_narc_data) where:
               - trainers_list is a list of (trainer_id, trainer_object) tuples
               - trainer_narc_data is the NARC data structure
    """
    narc_file_id = rom.filenames.idOf("a/0/5/6")
    trainer_narc = rom.files[narc_file_id]
    trainer_narc_data = ndspy.narc.NARC(trainer_narc)
    
    # Load the trainers.s file to get the expected number of Pokémon for each trainer
    trainer_pokemon_counts = {}
    try:
        with open("armips/data/trainers/trainers.s", "r", encoding="utf-8") as f:
            current_trainer = None
            for line in f:
                # Look for trainerdata lines to get trainer ID
                if "trainerdata" in line and "," in line:
                    try:
                        trainer_id = int(line.split("trainerdata")[1].split(",")[0].strip())
                        current_trainer = trainer_id
                    except:
                        pass
                # Look for nummons to get the number of Pokémon
                elif current_trainer is not None and "nummons" in line:
                    try:
                        num = int(line.split("nummons")[1].strip())
                        trainer_pokemon_counts[current_trainer] = num
                    except:
                        pass
        print(f"Loaded Pokémon counts for {len(trainer_pokemon_counts)} trainers from trainers.s")
    except Exception as e:
        print(f"Error loading trainer.s file: {e}")
        print("Will try to auto-detect Pokémon count from binary data")
    
    trainers = []
    for i, data in enumerate(trainer_narc_data.files):
        # Create a Container object to store trainer data
        from construct import Container
        trainer = Container()
        
        # For HG Engine, we need to parse the data differently
        # Each trainer entry seems to be just a list of Pokémon
        
        # First, set some default values
        trainer.trainerdata = 0  # Assume standard type
        trainer.trainerclass = 0
        trainer.battletype = 0
        trainer.nummons = 0
        trainer.items = [0, 0, 0, 0]
        trainer.ai_flags = 0
        trainer.padding = 0
        trainer.pokemon = []
        
        # Get the AUTHORITATIVE Pokémon count from trainer data NARC (offset 3)
        # This is the field that boss_team_adjuster.py updates when adding Pokémon
        authoritative_pokemon_count = get_trainer_poke_count_from_rom(rom, i)
        
        # Get the expected number of Pokémon for this trainer from trainers.s (fallback)
        expected_pokemon = trainer_pokemon_counts.get(i, 0)
        
        # Detect if this trainer has Pokémon with moves based on data length
        # Each Pokémon with moves takes 18 bytes, without moves takes 8 bytes
        has_moves = False
        pokemon_size = 8  # Default size without moves
        
        if len(data) == 0:
            # Empty trainer, but check if poke_count says otherwise
            if authoritative_pokemon_count > 0:
                if DEBUG_TRAINER_PARSING:
                    print(f"Warning: Trainer {i} has empty Pokémon data but poke_count={authoritative_pokemon_count}")
            trainer.nummons = authoritative_pokemon_count
            trainers.append((i, trainer))
            continue
        
        # Detect format based on binary data analysis
        # First, try to detect based on data length divisibility
        if len(data) % 18 == 0 and len(data) > 0:
            has_moves = True
            pokemon_size = 18
        elif len(data) % 8 == 0 and len(data) > 0:
            has_moves = False
            pokemon_size = 8
        else:
            # If data doesn't divide evenly, use authoritative count or fallback
            target_count = authoritative_pokemon_count if authoritative_pokemon_count > 0 else expected_pokemon
            if target_count > 0:
                # Check if the data size matches target count with moves (18 bytes each)
                if len(data) == target_count * 18:
                    has_moves = True
                    pokemon_size = 18
                # Check if data size matches target count without moves (8 bytes each)
                elif len(data) == target_count * 8:
                    has_moves = False
                    pokemon_size = 8
                # If data doesn't match exactly, prefer moves format if closer to target*18
                else:
                    diff_with_moves = abs(len(data) - (target_count * 18))
                    diff_without_moves = abs(len(data) - (target_count * 8))
                    if diff_with_moves <= diff_without_moves:
                        has_moves = True
                        pokemon_size = 18
                    else:
                        has_moves = False
                        pokemon_size = 8
            else:
                # Default to no moves if unclear
                has_moves = False
                pokemon_size = 8
        
        # Use actual Pokemon data length as the primary source (most reliable)
        # The data doesn't lie - if there are 4 Pokemon entries, there are 4 Pokemon
        num_pokemon = len(data) // pokemon_size
        trainer.nummons = num_pokemon
        
        # Check for consistency with poke_count field and warn if there's a mismatch
        if authoritative_pokemon_count != num_pokemon and authoritative_pokemon_count > 0:
            if DEBUG_TRAINER_PARSING:
                print(f"Warning: Trainer {i} poke_count={authoritative_pokemon_count} but data shows {num_pokemon} Pokemon")
                print(f"Using actual data count ({num_pokemon}) as authoritative source")
        
        # Debug: Print information about trainer parsing
        if DEBUG_TRAINER_PARSING:
            print(f"\n=== TRAINER {i} DEBUG ===")
            print(f"Data length: {len(data)} bytes")
            print(f"poke_count field: {authoritative_pokemon_count}")
            print(f"Expected from trainers.s: {expected_pokemon}")
            print(f"Detected format: {'with moves' if has_moves else 'without moves'} ({pokemon_size} bytes per Pokémon)")
            print(f"Actual Pokémon count (from data): {trainer.nummons}")
            if authoritative_pokemon_count != (len(data) // pokemon_size):
                print(f"** INCONSISTENCY: poke_count={authoritative_pokemon_count} vs actual_data={len(data) // pokemon_size}")
            if len(data) <= 50:  # Only show hex for short data
                hex_data = ' '.join(f'{b:02X}' for b in data)
                print(f"Raw data: {hex_data}")
            else:
                print(f"Raw data: {data[:20].hex()} ... (truncated, {len(data)} bytes total)")
        
        # Now parse each Pokémon entry
        for j in range(num_pokemon):
            offset = j * pokemon_size
            
            # Parse the Pokémon data
            if has_moves:
                # Pokémon with moves (18 bytes)
                pokemon_data = data[offset:offset+pokemon_size]
                pokemon = trainer_pokemon_moves_struct.parse(pokemon_data)
            else:
                # Standard Pokémon (8 bytes)
                pokemon_data = data[offset:offset+pokemon_size]
                pokemon = trainer_pokemon_struct.parse(pokemon_data)
            
            # Debug: Print parsed data for all trainers
            if DEBUG_TRAINER_PARSING:
                if has_moves:
                    print(f"Pokemon {j}: IVs={pokemon.ivs}, Ability={pokemon.abilityslot}, Level={pokemon.level}, Species={pokemon.species}, Item={pokemon.item}, Moves=[{pokemon.move1},{pokemon.move2},{pokemon.move3},{pokemon.move4}], Ballseal={pokemon.ballseal}")
                else:
                    print(f"Pokemon {j}: IVs={pokemon.ivs}, Ability={pokemon.abilityslot}, Level={pokemon.level}, Species={pokemon.species}, Ballseal={pokemon.ballseal}")
            
            # Add to trainer's team
            trainer.pokemon.append(pokemon)
        
        # If we found Pokémon, flag this trainer as having moves if needed
        if has_moves and len(trainer.pokemon) > 0:
            trainer.trainerdata = 2  # Set flag for having moves
        
        trainers.append((i, trainer))
        if DEBUG_TRAINER_PARSING:
            print(f"Trainer {i}: Parsed {len(trainer.pokemon)} Pokémon" + (" with moves" if has_moves else ""))
    
    print(f"Total trainers processed: {len(trainers)}")
    return trainers, trainer_narc_data


def rebuild_trainer_data(trainer):
    """
    Rebuild trainer data from trainer object back to binary format.
    
    Args:
        trainer: Trainer object containing Pokemon data
        
    Returns:
        bytes: Binary data representing the trainer
    """
    if not hasattr(trainer, 'pokemon') or not trainer.pokemon:
        return b''
    
    # Determine if we need to include moves
    has_moves = any(hasattr(p, 'move1') for p in trainer.pokemon)
    
    data = b''
    for pokemon in trainer.pokemon:
        if has_moves:
            # Build with moves (18 bytes)
            pokemon_data = trainer_pokemon_moves_struct.build(pokemon)
        else:
            # Build without moves (8 bytes)
            pokemon_data = trainer_pokemon_struct.build(pokemon)
        data += pokemon_data
    
    return data
