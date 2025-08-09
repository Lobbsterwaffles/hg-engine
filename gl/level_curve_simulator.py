# level_curve_simulator.py
import json
import re
import os
import sys
import argparse
import io

# Set console output to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Experience curve totals for each level (1-100) for all 6 growth types
# These values are from Bulbapedia's experience tables
EXP_REQUIREMENTS = {
    "erratic": [0, 15, 52, 122, 237, 406, 637, 942, 1326, 1800, 2369, 3041, 3822, 4719, 5737, 6881, 8155, 9564, 11111, 12800, 14632, 16610, 18737, 21012, 23437, 26012, 28737, 31610, 34632, 37800, 41111, 44564, 48155, 51881, 55737, 59719, 63822, 68041, 72369, 76800, 81326, 85942, 90637, 95406, 100237, 105122, 110052, 115015, 120001, 125000, 131324, 137795, 144410, 151165, 158056, 165079, 172229, 179503, 186894, 194400, 202013, 209728, 217540, 225443, 233431, 241496, 249633, 257834, 267406, 276458, 286328, 296358, 305767, 316074, 326531, 336255, 346965, 357812, 367807, 378880, 390077, 400293, 411686, 423190, 433572, 445239, 457001, 467489, 479378, 491346, 501878, 513934, 526049, 536557, 548720, 560922, 571333, 583539, 591882, 600000],
    "fast": [0, 6, 21, 51, 100, 172, 274, 409, 583, 800, 1064, 1382, 1757, 2195, 2700, 3276, 3930, 4665, 5487, 6400, 7408, 8518, 9733, 11059, 12500, 14060, 15746, 17561, 19511, 21600, 23832, 26214, 28749, 31443, 34300, 37324, 40522, 43897, 47455, 51200, 55136, 59270, 63605, 68147, 72900, 77868, 83058, 88473, 94119, 100000, 106120, 112486, 119101, 125971, 133100, 140492, 148154, 156089, 164303, 172800, 181584, 190662, 200037, 209715, 219700, 229996, 240610, 251545, 262807, 274400, 286328, 298598, 311213, 324179, 337500, 351180, 365226, 379641, 394431, 409600, 425152, 441094, 457429, 474163, 491300, 508844, 526802, 545177, 563975, 583200, 602856, 622950, 643485, 664467, 685900, 707788, 730138, 752953, 776239, 800000],
    "medium_fast": [0, 8, 27, 64, 125, 216, 343, 512, 729, 1000, 1331, 1728, 2197, 2744, 3375, 4096, 4913, 5832, 6859, 8000, 9261, 10648, 12167, 13824, 15625, 17576, 19683, 21952, 24389, 27000, 29791, 32768, 35937, 39304, 42875, 46656, 50653, 54872, 59319, 64000, 68921, 74088, 79507, 85184, 91125, 97336, 103823, 110592, 117649, 125000, 132651, 140608, 148877, 157464, 166375, 175616, 185193, 195112, 205379, 216000, 226981, 238328, 250047, 262144, 274625, 287496, 300763, 314432, 328509, 343000, 357911, 373248, 389017, 405224, 421875, 438976, 456533, 474552, 493039, 512000, 531441, 551368, 571787, 592704, 614125, 636056, 658503, 681472, 704969, 729000, 753571, 778688, 804357, 830584, 857375, 884736, 912673, 941192, 970299, 1000000],
    "medium_slow": [0, 9, 57, 96, 135, 179, 238, 314, 419, 560, 742, 973, 1261, 1612, 2035, 2535, 3120, 3798, 4575, 5460, 6458, 7577, 8825, 10208, 11735, 13411, 15244, 17242, 19411, 21760, 24294, 27021, 29949, 33084, 36435, 40007, 43808, 47846, 52127, 56660, 61450, 66505, 71833, 77440, 83335, 89523, 96012, 102810, 109923, 117360, 125126, 133229, 141677, 150476, 159635, 169159, 179056, 189334, 199999, 211060, 222522, 234393, 246681, 259392, 272535, 286115, 300140, 314618, 329555, 344960, 360838, 377197, 394045, 411388, 429235, 447591, 466464, 485862, 505791, 526260, 547274, 568841, 590969, 613664, 636935, 660787, 685228, 710266, 735907, 762160, 789030, 816525, 844653, 873420, 902835, 932903, 963632, 995030, 1027103, 1059860],
    "slow": [0, 10, 33, 80, 156, 270, 428, 640, 911, 1250, 1663, 2160, 2746, 3430, 4218, 5120, 6141, 7290, 8573, 10000, 11576, 13310, 15208, 17280, 19531, 21970, 24603, 27440, 30486, 33750, 37238, 40960, 44921, 49130, 53593, 58320, 63316, 68590, 74148, 80000, 86151, 92610, 99383, 106480, 113906, 121670, 129778, 138240, 147061, 156250, 165813, 175760, 186096, 196830, 207968, 219520, 231491, 243890, 256723, 270000, 283726, 297910, 312558, 327680, 343281, 359370, 375953, 393040, 410636, 428750, 447388, 466560, 486271, 506530, 527343, 548720, 570666, 593190, 616298, 640000, 664301, 689210, 714733, 740880, 767656, 795070, 823128, 851840, 881211, 911250, 941963, 973360, 1005446, 1038230, 1071718, 1105920, 1140841, 1176490, 1212873, 1250000],
    "fluctuating": [0, 4, 13, 32, 65, 112, 178, 276, 393, 540, 745, 967, 1230, 1591, 1957, 2457, 3046, 3732, 4526, 5440, 6482, 7666, 9003, 10506, 12187, 14060, 16140, 18439, 20974, 23760, 26811, 30146, 33780, 37731, 42017, 46656, 50653, 55969, 60505, 66560, 71677, 78533, 84277, 91998, 98415, 107069, 114205, 123863, 131766, 142500, 151222, 163105, 172697, 185807, 196322, 210739, 222231, 238036, 250562, 267840, 281456, 300293, 315059, 335544, 351520, 373744, 390991, 415050, 433631, 459620, 479600, 507617, 529063, 559209, 582187, 614566, 639146, 673863, 700115, 737280, 765275, 804997, 834809, 877201, 908905, 954084, 987754, 1035837, 1071552, 1122660, 1160499, 1214753, 1254796, 1312322, 1354652, 1415577, 1460276, 1524731, 1571884, 1640000]
}

# Define base experience yields for each Pokemon
# This is a simplified version for the simulation
# In a real implementation, you would use actual values from your game data
BASE_EXP_YIELDS = {
    # These are example values, adjust as needed
    "SPECIES_PIDGEY": 50,
    "SPECIES_RATTATA": 51,
    "SPECIES_ZUBAT": 49,
    "SPECIES_GEODUDE": 60,
    "SPECIES_BELLSPROUT": 84,
    "SPECIES_TENTACOOL": 67,
    # Default value for unknown species
    "DEFAULT": 100
}

class PokemonParty:
    def __init__(self, starting_level=5):
        # Initialize a party with one Pokemon of each growth rate
        self.pokemon = {
            "erratic": {"exp": EXP_REQUIREMENTS["erratic"][starting_level], "level": starting_level},
            "fast": {"exp": EXP_REQUIREMENTS["fast"][starting_level], "level": starting_level},
            "medium_fast": {"exp": EXP_REQUIREMENTS["medium_fast"][starting_level], "level": starting_level},
            "medium_slow": {"exp": EXP_REQUIREMENTS["medium_slow"][starting_level], "level": starting_level},
            "slow": {"exp": EXP_REQUIREMENTS["slow"][starting_level], "level": starting_level},
            "fluctuating": {"exp": EXP_REQUIREMENTS["fluctuating"][starting_level], "level": starting_level}
        }
        
    def update_levels(self):
        """Update the level of each Pokemon based on their current experience."""
        for growth_rate, data in self.pokemon.items():
            # Find the appropriate level for the current exp
            exp_table = EXP_REQUIREMENTS[growth_rate]
            for level in range(1, 100):
                if data["exp"] >= exp_table[level] and data["exp"] < exp_table[level + 1]:
                    self.pokemon[growth_rate]["level"] = level
                    break
                elif data["exp"] >= exp_table[99]:  # Level 100 exp is at index 99 (0-indexed)
                    self.pokemon[growth_rate]["level"] = 100
                    break
    
    def gain_experience(self, fainted_level, base_exp, trainer_owned=True):
        """Calculate experience gained from defeating a Pokemon."""
        # Scaled experience formula (Gen VII+)
        for growth_rate, data in self.pokemon.items():
            level = data["level"]
            
            # Implementation of the scaled formula
            # ΔEXP = (a × b × L × t × e × p) / (7 × s)
            
            # Base multipliers
            a = 1.5 if trainer_owned else 1  # Trainer owned multiplier
            b = base_exp  # Base experience
            e = 1  # Lucky Egg (not applying for simulation)
            f = 1  # Friendship/affection bonus (not applying)
            t = 1  # Traded Pokemon bonus (not applying)
            v = 1  # Evolution bonus (not applying)
            p = 1  # Exp boosts (not applying)
            s = 6  # Number of participating Pokemon
            
            # Calculate scaled experience (Gen VII formula)
            exp_gained = (a * b * fainted_level * t * e * p * v * f) 
            exp_gained = exp_gained * (2 * fainted_level + 10) ** 2.5
            exp_gained = exp_gained / ((fainted_level + level + 10) ** 2.5)
            exp_gained = exp_gained + 1
            exp_gained = exp_gained / s
            
            # Round to integer
            exp_gained = int(exp_gained)
            
            # Add experience to this Pokemon
            self.pokemon[growth_rate]["exp"] += exp_gained
        
        # Update levels after gaining experience
        self.update_levels()

def parse_trainers_file(file_path):
    """Parse the trainers.s file to extract trainer data."""
    trainers = {}
    current_trainer_id = None
    current_trainer_name = None
    current_pokemon = []
    with open(file_path, 'r', encoding='utf-8') as f:
        in_party = False
        
        for line in f:
            line = line.strip()
            
            # Find trainer definition
            trainer_match = re.match(r'trainerdata\s+(\d+),\s*"([^"]+)"', line)
            if trainer_match:
                # If we were parsing a previous trainer, save it
                if current_trainer_id is not None:
                    if current_trainer_id not in trainers:
                        trainers[current_trainer_id] = []
                    trainers[current_trainer_id].append({
                        "name": current_trainer_name,
                        "pokemon": current_pokemon.copy()
                    })
                
                current_trainer_id = int(trainer_match.group(1))
                current_trainer_name = trainer_match.group(2)
                current_pokemon = []
                in_party = False
            
            # Find party section
            elif line.startswith('party'):
                in_party = True
            
            # End of party
            elif line == 'endparty':
                in_party = False
            
            # Extract Pokemon data
            elif in_party and 'level' in line:
                level_match = re.match(r'.*level\s+(\d+)', line)
                if level_match:
                    level = int(level_match.group(1))
                    # Look for the next pokemon line
                    continue
            
            # Find Pokemon species
            elif in_party and 'pokemon' in line:
                species_match = re.match(r'.*pokemon\s+(\w+)', line)
                if species_match:
                    species = species_match.group(1)
                    current_pokemon.append({
                        "species": species,
                        "level": level  # From the previous level line
                    })
    
    # Add the last trainer if there is one
    if current_trainer_id is not None:
        if current_trainer_id not in trainers:
            trainers[current_trainer_id] = []
        trainers[current_trainer_id].append({
            "name": current_trainer_name,
            "pokemon": current_pokemon.copy()
        })
    
    return trainers

def load_trainer_locations(json_file):
    """Load trainer locations from the JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def simulate_level_curve(trainers_data, trainer_locations, trainer_multiplier=1.0):
    """Simulate the level curve through the game.
    
    Args:
        trainers_data: Dictionary of trainer data from trainers.s
        trainer_locations: List of trainer locations from JSON
        trainer_multiplier: Multiplier for trainer Pokemon levels (default: 1.0)
    """
    party = PokemonParty(starting_level=5)
    results = []
    
    # Dictionary to track which trainer variations we've seen
    trainer_variations = {}
    
    # Special handling for Rival battles - map Rival entries to specific trainer IDs in order
    rival_trainer_ids = [2, 1, 263, 288, 264, 285]  # Provided by user
    rival_battle_count = 0
    
    # Go through trainers in order from the JSON
    for trainer_info in trainer_locations:
        full_trainer_name = trainer_info["trainer"]
        area = trainer_info["area"]
        
        # Special handling for Rival battles - use specific trainer IDs in sequence
        if full_trainer_name == "Rival" and rival_battle_count < len(rival_trainer_ids):
            # Use the next Rival trainer ID from the list
            rival_id = rival_trainer_ids[rival_battle_count]
            rival_battle_count += 1
            print(f"Processing Rival battle #{rival_battle_count} (ID: {rival_id}) in {area}")
            
            # Get the trainer's Pokemon
            if rival_id in trainers_data:
                trainer_data = trainers_data[rival_id][0]  # Use first variation
                pokemon = trainer_data["pokemon"]
                
                # Battle each Pokemon
                for mon in pokemon:
                    species = mon["species"]
                    # Apply trainer multiplier to the level
                    original_level = mon["level"]
                    level = round(original_level * trainer_multiplier)
                    # Ensure level is at least 1 and at most 100
                    level = max(1, min(100, level))
                    
                    if trainer_multiplier != 1.0 and original_level != level:
                        print(f"  - {species} level adjusted: {original_level} → {level} (multiplier: {trainer_multiplier}x)")
                    
                    # Get base exp yield for this species
                    base_exp = BASE_EXP_YIELDS.get(species, BASE_EXP_YIELDS["DEFAULT"])
                    
                    # Gain experience from defeating this Pokemon
                    party.gain_experience(level, base_exp, trainer_owned=True)
                
                # Add result to our level curve data
                result = {
                    "trainer": f"Rival (#{rival_battle_count})",
                    "area": area,
                    "trainer_id": rival_id,
                    "levels": {
                        "erratic": party.pokemon["erratic"]["level"],
                        "fast": party.pokemon["fast"]["level"],
                        "medium_fast": party.pokemon["medium_fast"]["level"],
                        "medium_slow": party.pokemon["medium_slow"]["level"],
                        "slow": party.pokemon["slow"]["level"],
                        "fluctuating": party.pokemon["fluctuating"]["level"]
                    }
                }
                results.append(result)
                continue
            else:
                print(f"Error: Could not find Rival trainer ID {rival_id} in trainers.s")
                # Fall through to normal processing as a fallback
        
        # Extract just the trainer's first name from the full name
        # Format in JSON is usually "Class Name" (e.g., "Bug Catcher Don")
        # The trainer's actual name is the last word
        
        # Special cases first - map full trainer names to how they appear in trainers.s
        special_cases = {
            "Leader Lt. Surge": "Lt. Surge",
            "Lt. Surge": "Lt. Surge",
            "Rival": "Silver",  # In trainers.s, rivals are named Silver
            "Executive Proton": "Proton",
            "Executive Petrel": "Petrel",
            "Executive Ariana": "Ariana",
            "Executive Archer": "Archer",
            "Kimono Girl Zuki": "Zuki",
            "Kimono Girl Naoko": "Naoko",
            "Kimono Girl Sayo": "Sayo",
            "Kimono Girl Kuni": "Kuni",
            "Kimono Girl Miki": "Miki",
            "Twins Kay & Tia": "Kay & Tia",
            "Twins Jo & Zoe": "Jo & Zoe",
            "Twins Amy & Mimi": "Amy & Mimi",
            "Twins Meg & Peg": "Meg & Peg",
            "Double Team Zac & Jen": "Zac & Jen",
            "Young Couple Tim & Sue": "Tim & Sue",
            "Young Couple Duff & Eda": "Duff & Eda",
            "Black Belt Ander": "Ander"
        }
        
        # If it's a special case, use the predefined mapping
        if full_trainer_name in special_cases:
            trainer_name = special_cases[full_trainer_name]
        else:
            # Handle multi-word names and duo trainers
            if "&" in full_trainer_name or "and" in full_trainer_name.lower():
                # For pairs like "Amy & May" or "Jo & Zoe", use the full name
                trainer_name = full_trainer_name
            else:
                # For normal trainers, take the last word as their name
                name_parts = full_trainer_name.split()
                if len(name_parts) > 0:
                    trainer_name = name_parts[-1]
                else:
                    trainer_name = full_trainer_name
                    
        # Debug info
        print(f"Looking for trainer: '{full_trainer_name}' -> using name: '{trainer_name}'")
        
        # Find this trainer in our trainers_data
        found = False
        trainer_ids = []
        
        # Search by name
        for trainer_id, variations in trainers_data.items():
            for variation in variations:
                # Check if the name contains the trainer's name we're looking for
                # This handles cases where the trainer name might be a partial match
                if variation["name"] == trainer_name:
                    trainer_ids.append(trainer_id)
        
        if not trainer_ids:
            print(f"Error: Trainer '{trainer_name}' (from '{full_trainer_name}') not found in trainers.s")
            continue
        
        # If we have multiple matches, track and use the next one
        if len(trainer_ids) > 1:
            print(f"Warning: Multiple entries found for trainer '{trainer_name}'")
            if trainer_name not in trainer_variations:
                trainer_variations[trainer_name] = 0
            else:
                trainer_variations[trainer_name] += 1
            
            variation_index = trainer_variations[trainer_name]
            if variation_index >= len(trainer_ids):
                print(f"Error: Requested variation {variation_index} for '{trainer_name}' but only have {len(trainer_ids)} variations")
                continue
            
            trainer_id = trainer_ids[variation_index]
        else:
            trainer_id = trainer_ids[0]

        # Get the trainer's Pokemon
        trainer_data = trainers_data[trainer_id][0]  # Use first variation as default
        pokemon = trainer_data["pokemon"]

        # Battle each Pokemon
        for mon in pokemon:
            species = mon["species"]
            # Apply trainer multiplier to the level
            original_level = mon["level"]
            level = round(original_level * trainer_multiplier)
            # Ensure level is at least 1 and at most 100
            level = max(1, min(100, level))

            if trainer_multiplier != 1.0 and original_level != level:
                print(f"  - {species} level adjusted: {original_level} → {level} (multiplier: {trainer_multiplier}x)")

            # Get base exp yield for this species
            base_exp = BASE_EXP_YIELDS.get(species, BASE_EXP_YIELDS["DEFAULT"])

            # Gain experience from defeating this Pokemon
            party.gain_experience(level, base_exp, trainer_owned=True)

        # Record the party's levels after this battle
        results.append({
            "trainer": trainer_name,
            "area": area,
            "trainer_id": trainer_id,
            "levels": {
                growth_rate: data["level"]
                for growth_rate, data in party.pokemon.items()
            }
        })

    return results

def main():
    # Set UTF-8 encoding for stdout and stderr
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Simulate Pokemon level curve progression through trainer battles')
    parser.add_argument('--trainer-multiplier', '-m', type=float, default=1.0,
                      help='Multiplier for trainer Pokemon levels (default: 1.0)')
    args = parser.parse_args()

    # Get the current directory (where this script is)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define file paths (adjust these as needed)
    trainers_file = os.path.join(script_dir, "trainers.s")
    trainer_locations_file = os.path.join(script_dir, "trainers_location_data.json")
    output_file = os.path.join(script_dir, "level_curve.json")

    # Check if files exist
    if not os.path.exists(trainers_file):
        print(f"Error: {trainers_file} not found")
        return

    if not os.path.exists(trainer_locations_file):
        print(f"Error: {trainer_locations_file} not found")
        return

    # Parse trainers file
    print(f"Parsing trainers file: {trainers_file}")
    trainers_data = parse_trainers_file(trainers_file)
    print(f"Found {len(trainers_data)} unique trainers")

    # Load trainer locations
    print(f"Loading trainer locations from: {trainer_locations_file}")
    trainer_locations = load_trainer_locations(trainer_locations_file)
    print(f"Found {len(trainer_locations)} trainers in progression order")

    # Simulate level curve
    print("Simulating level curve...")
    level_curve = simulate_level_curve(trainers_data, trainer_locations, trainer_multiplier=args.trainer_multiplier)

    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(level_curve, f, indent=2)
    print(f"Level curve data saved to: {output_file}")
    if args.trainer_multiplier != 1.0:
        print(f"Note: Trainer Pokemon levels were adjusted by a factor of {args.trainer_multiplier}x")

    # Print summary
    print("\nLevel Curve Summary:")
    print("-" * 80)
    print(f"{'Trainer':<20} {'Area':<20} {'Fast':<5} {'Med-F':<5} {'Med-S':<5} {'Slow':<5} {'Erratic':<5} {'Fluct':<5}")
    print("-" * 80)

    
    for entry in level_curve:
        levels = entry["levels"]
        print(f"{entry['trainer']:<20} {entry['area']:<20} {levels['fast']:<5} {levels['medium_fast']:<5} {levels['medium_slow']:<5} {levels['slow']:<5} {levels['erratic']:<5} {levels['fluctuating']:<5}")

if __name__ == "__main__":
    main()