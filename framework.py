"""
ROM data extraction and randomization framework.

Provides a flexible, extensible system for reading, modifying, and writing 
structured ROM data using context-managed extractor singletons and ordered 
processing steps.
"""

from abc import ABC, abstractmethod
import ndspy.rom
import ndspy.narc
import os
import re
import random
from construct import Struct, Int8ul, Int16ul, Array, Padding


class Extractor(ABC):
    """Base class for context-managed ROM data extractors."""
    
    def __init__(self, context):
        self.context = context
        self.rom = context.rom
    
    def write(self):
        """Write any changes back to ROM. Default is no-op."""
        pass


class ExtractorStep(Extractor):
    """Extractor that can write data back to ROM."""
    
    def write(self):
        self.write_to_rom()
    
    @abstractmethod
    def write_to_rom(self):
        """Write data back to ROM."""
        pass
    
    @abstractmethod
    def get_narc_path(self):
        """Return path to NARC file in ROM."""
        pass
    
    @abstractmethod
    def parse_file(self, file_data, index):
        """Parse individual file from NARC."""
        pass
    
    @abstractmethod
    def serialize_file(self, data, index):
        """Serialize individual file back to bytes."""
        pass
    
    def parse_narc(self, narc_data):
        """Parse all files in NARC."""
        return [self.parse_file(file_data, i) for i, file_data in enumerate(narc_data.files)]
    
    def serialize_narc(self, data_list):
        """Serialize data back to NARC."""
        narc_data = ndspy.narc.NARC()
        narc_data.files = [self.serialize_file(item, i) for i, item in enumerate(data_list)]
        return narc_data
    
    def load_narc(self):
        """Helper: load from single NARC using parse methods."""
        narc_file_id = self.rom.filenames.idOf(self.get_narc_path())
        narc_file = self.rom.files[narc_file_id]
        narc_data = ndspy.narc.NARC(narc_file)
        return self.parse_narc(narc_data)
    
    def write_to_rom(self):
        """Default: write to single NARC. Extra fields ignored by construct."""
        narc_data = self.serialize_narc(self.data)
        narc_file_id = self.rom.filenames.idOf(self.get_narc_path())
        self.rom.files[narc_file_id] = narc_data.save()


class Step(ABC):
    """Base class for pipeline steps that run in order."""
    
    def run(self, context):
        """Execute this step. Default is no-op."""
        pass


class RandomizationContext:
    """Manages ROM data, pipeline execution, and shared objects."""
    
    def __init__(self, rom):
        self.rom = rom
        self._objects = {}
        self._creating = set()
    
    def get(self, obj_class):
        """Get object instance (extractor or step), creating if needed."""
        if obj_class in self._objects:
            return self._objects[obj_class]
        
        if obj_class in self._creating:
            raise RuntimeError(f"Circular dependency detected: {obj_class.__name__}")
        
        if issubclass(obj_class, Extractor):
            self._creating.add(obj_class)
            try:
                obj = obj_class(self)
                self.register_step(obj)
            finally:
                self._creating.remove(obj_class)
        else:
            raise ValueError(f"Step {obj_class.__name__} not found. Make sure it runs before being accessed.")
        
        return self._objects[obj_class]
    
    def register_step(self, step):
        """Register step instance by its class. Throws if already present."""
        step_class = type(step)
        if step_class in self._objects:
            raise RuntimeError(f"Step {step_class.__name__} already registered")
        self._objects[step_class] = step
    
    def run_pipeline(self, steps, log_function=None, progress_callback=None):
        """Run all pipeline steps in order."""
        for i, step in enumerate(steps):
            if log_function:
                log_function(f"Running {step.__class__.__name__}...")
            
            step.run(self)
            
            if progress_callback:
                progress_percent = int((i + 1) * 100 / len(steps))
                progress_callback(progress_percent)
    
    def write_all(self, log_function=None):
        """Write all loaded extractors back to ROM."""
        if log_function:
            log_function("Writing all data to ROM...")
        
        for obj in self._objects.values():
            if isinstance(obj, Extractor):
                obj.write()


# Pokemon data constants
SPECIAL_POKEMON = {
    # Legendaries and special Pokémon that should not be replaced
    150, 151, 243, 244, 245, 249, 250, 251, 377, 378, 379, 380, 381, 382, 383, 384,
    385, 386, 483, 484, 487, 488, 489, 490, 491, 492, 493, 494
}

# Type constants
TYPE_NORMAL = 0
TYPE_FIGHTING = 1
TYPE_FLYING = 2
TYPE_POISON = 3
TYPE_GROUND = 4
TYPE_ROCK = 5
TYPE_BUG = 6
TYPE_GHOST = 7
TYPE_STEEL = 8
TYPE_MYSTERY = 9
TYPE_FAIRY = 9
TYPE_FIRE = 10
TYPE_WATER = 11
TYPE_GRASS = 12
TYPE_ELECTRIC = 13
TYPE_PSYCHIC = 14
TYPE_ICE = 15
TYPE_DRAGON = 16
TYPE_DARK = 17

TYPE_NAMES = {
    0: "Normal", 1: "Fighting", 2: "Flying", 3: "Poison", 4: "Ground", 5: "Rock",
    6: "Bug", 7: "Ghost", 8: "Steel", 9: "Fairy", 10: "Fire", 11: "Water",
    12: "Grass", 13: "Electric", 14: "Psychic", 15: "Ice", 16: "Dragon", 17: "Dark"
}

# Physical/Special Split constants
SPLIT_PHYSICAL = 0
SPLIT_SPECIAL = 1
SPLIT_STATUS = 2

SPLIT_NAMES = {0: "Physical", 1: "Special", 2: "Status"}

# Contest type constants
CONTEST_COOL = 0
CONTEST_BEAUTY = 1
CONTEST_CUTE = 2
CONTEST_SMART = 3
CONTEST_TOUGH = 4

CONTEST_NAMES = {0: "Cool", 1: "Beauty", 2: "Cute", 3: "Smart", 4: "Tough"}

# Move flag constants
FLAG_CONTACT = 0x01
FLAG_PROTECT = 0x02
FLAG_MAGIC_COAT = 0x04
FLAG_SNATCH = 0x08
FLAG_MIRROR_MOVE = 0x10
FLAG_KINGS_ROCK = 0x20
FLAG_KEEP_HP_BAR = 0x40
FLAG_HIDE_SHADOW = 0x80

FLAG_NAMES = {
    0x01: "Contact", 0x02: "Protect", 0x04: "Magic Coat", 0x08: "Snatch",
    0x10: "Mirror Move", 0x20: "King's Rock", 0x40: "Keep HP Bar", 0x80: "Hide Shadow"
}

# Range/Target constants
RANGE_SINGLE_TARGET = 0
RANGE_SINGLE_TARGET_SPECIAL = 1
RANGE_RANDOM_OPPONENT = 2
RANGE_ADJACENT_OPPONENTS = 4
RANGE_ALL_ADJACENT = 8
RANGE_USER = 16
RANGE_USER_SIDE = 32
RANGE_FIELD = 64
RANGE_OPPONENT_SIDE = 128
RANGE_ALLY = 256
RANGE_SINGLE_TARGET_USER_SIDE = 512
RANGE_FRONT = 1024

RANGE_NAMES = {
    0: "Single Target", 1: "Single Target Special", 2: "Random Opponent",
    4: "Adjacent Opponents", 8: "All Adjacent", 16: "User", 32: "User Side",
    64: "Field", 128: "Opponent Side", 256: "Ally", 512: "Single Target User Side",
    1024: "Front"
}


class NameTableReader(Step):
    """Base class for reading name tables from text files."""
    
    def __init__(self, filename):
        # Load names from file
        with open(filename, "r", encoding="utf-8") as f:
            names_list = [line.strip() for line in f.readlines()]
        
        # Create bidirectional mapping
        self.by_id = {i: name for i, name in enumerate(names_list)}
        self.by_name = {name: i for i, name in self.by_id.items()}
    
    def run(self, context):
        context.register_step(self)


class LoadPokemonNamesStep(NameTableReader):
    def __init__(self, base_path="."):
        super().__init__("build/rawtext/237.txt")

class LoadMoveNamesStep(NameTableReader):
    def __init__(self):
        super().__init__("build/rawtext/750.txt")


class MoveDataExtractor(ExtractorStep):
    """Extractor for move data from ROM with full move structure."""
    
    def __init__(self, context):
        # Define move data structure (16 bytes total)
        self.move_struct = Struct(
            "battle_effect" / Int16ul,    # 2 bytes
            "pss" / Int8ul,               # 1 byte (physical/special/status split)
            "base_power" / Int8ul,        # 1 byte
            "type" / Int8ul,              # 1 byte
            "accuracy" / Int8ul,          # 1 byte
            "pp" / Int8ul,                # 1 byte  
            "effect_chance" / Int8ul,     # 1 byte
            "target" / Int16ul,           # 2 bytes
            "priority" / Int8ul,          # 1 byte (unsigned for now)
            "flags" / Int8ul,             # 1 byte
            "appeal" / Int8ul,            # 1 byte
            "contest_type" / Int8ul,      # 1 byte
            Padding(2)                    # 2 bytes (terminatedata)
        )
        
        super().__init__(context)
        self.data = self.load_narc()
        
        # Enrich with names and readable fields
        move_names_step = context.get(LoadMoveNamesStep)
        for i, move in enumerate(self.data):
            if i not in move_names_step.by_id:
                raise KeyError(f"No move name found for ID {i}")
            move.name = move_names_step.by_id[i]
            move.move_id = i
            
            # Add readable type name
            move.type_name = TYPE_NAMES.get(move.type, f"Unknown({move.type})")
            
            # Add readable split name
            move.split_name = SPLIT_NAMES.get(move.pss, f"Unknown({move.pss})")
            
            # Add readable contest type name
            move.contest_name = CONTEST_NAMES.get(move.contest_type, f"Unknown({move.contest_type})")
            
            # Add readable target name
            move.target_name = RANGE_NAMES.get(move.target, f"Unknown({move.target})")
            
            # Parse flags into list of flag names
            move.flag_names = [name for flag, name in FLAG_NAMES.items() if move.flags & flag]
    
    def get_narc_path(self):
        return "a/0/1/1"  # Move data NARC
    
    def get_struct(self):
        return self.move_struct
    
    def parse_file(self, file_data, file_index):
        """Parse a single move file into move data."""
        return self.move_struct.parse(file_data)
    
    def serialize_file(self, data):
        """Serialize move data back to binary format."""
        return self.move_struct.build(data)

class LoadBlacklistStep(Step):
    """Step that creates Pokemon blacklist with hardcoded data."""
    
    def __init__(self):
        # Explicit blacklist by name
        self.by_name = {
            "Bad Egg"
        }
        self.by_id = set()  # Will be populated in run()
                        
    def run(self, context):
        # Resolve any name-based blacklist entries
        names_step = context.get(LoadPokemonNamesStep)
        
        # Add Pokemon with "-----" names
        for pokemon_id, name in names_step.by_id.items():
            if name == "-----":
                self.by_id.add(pokemon_id)
        
        # Add Pokemon from explicit blacklist
        for name in self.by_name:
            if name in names_step.by_name:
                self.by_id.add(names_step.by_name[name])
            else:
                raise ValueError(name)
        
        context.register_step(self)


class MondataExtractor(ExtractorStep):
    """Extractor for Pokemon data from ROM with full mondata structure."""
    
    def __init__(self, context):
        # Define Pokemon mondata structure (26 bytes total)
        self.mondata_struct = Struct(
            # Base stats (6 bytes)
            "hp" / Int8ul,
            "attack" / Int8ul, 
            "defense" / Int8ul,
            "speed" / Int8ul,
            "sp_attack" / Int8ul,
            "sp_defense" / Int8ul,
            # Types (2 bytes)
            "type1" / Int8ul,
            "type2" / Int8ul,
            # Catch rate (1 byte)
            "catch_rate" / Int8ul,
            # Base experience (1 byte)
            "base_exp" / Int8ul,
            # EV yields (2 bytes)
            "ev_yields" / Int16ul,
            # Items (4 bytes)
            "item1" / Int16ul,
            "item2" / Int16ul,
            # Gender, egg cycles, friendship (3 bytes)
            "gender_ratio" / Int8ul,
            "egg_cycles" / Int8ul,
            "base_friendship" / Int8ul,
            # Growth and egg info (3 bytes)
            "growth_rate" / Int8ul,
            "egg_group1" / Int8ul,
            "egg_group2" / Int8ul,
            # Abilities (2 bytes)
            "ability1" / Int8ul,
            "ability2" / Int8ul,
            # Additional data (2 bytes)
            "additional1" / Int8ul,
            "additional2" / Int8ul
        )
        
        super().__init__(context)
        
        # Load ROM data
        self.data = self.load_narc()
        
        # Enrich with names from step
        pokemon_names_step = context.get(LoadPokemonNamesStep)
        for i, mon in enumerate(self.data):
            if i not in pokemon_names_step.by_id:
                raise KeyError(f"No Pokemon name found for ID {i}")
            mon.name = pokemon_names_step.by_id[i]
            mon.pokemon_id = i
    
    def get_narc_path(self):
        return "a/0/0/2"
    
    def parse_file(self, file_data, index):
        mon = self.mondata_struct.parse(file_data)
        # Add calculated BST field
        mon.bst = mon.hp + mon.attack + mon.defense + mon.speed + mon.sp_attack + mon.sp_defense
        return mon
    
    def serialize_file(self, data, index):
        return self.mondata_struct.build(data)
    
    def find_replacements(self, mon, bstrmin=0.9, bstrmax=1.1):
        """Find suitable replacement Pokemon within BST range."""
        # Get blacklist - fail if not available
        blacklist_step = self.context.get(LoadBlacklistStep)
        blacklist = blacklist_step.by_id
        
        # Combine special Pokemon and blacklist
        excluded = SPECIAL_POKEMON | blacklist
        
        # Find Pokemon within BST range
        target_bst = mon.bst
        min_bst = int(target_bst * bstrmin)
        max_bst = int(target_bst * bstrmax)
        
        candidates = []
        for i, candidate in enumerate(self.data):
            if (i not in excluded and 
                min_bst <= candidate.bst <= max_bst and 
                i != mon.pokemon_id):
                candidates.append(i)
        
        return candidates


class LoadEncounterNamesStep(Step):
    """Step that loads encounter location names from assembly source."""
    
    def __init__(self, base_path="."):
        self.base_path = base_path
        self.location_names = {}
        # Parse encounter names from assembly source file
        encounter_file = os.path.join("armips", "data", "encounters.s")
        with open(encounter_file, "r", encoding="utf-8") as f:
            for line in f:
                # Look for pattern: encounterdata <number> ... // <n>
                match = re.search(r"encounterdata\s+(\d+).*//\s+(.*)", line)
                if match:
                    encounter_id = int(match.group(1))
                    encounter_name = match.group(2).strip()
                    self.location_names[encounter_id] = encounter_name
        
    def run(self, context):
        context.register_step(self)


class EncounterExtractor(ExtractorStep):
    """Extractor for encounter data from ROM."""
    
    def __init__(self, context):
        # Define encounter slot structure
        EncounterSlot = Struct(
            "species" / Int16ul,
            "minlevel" / Int8ul,
            "maxlevel" / Int8ul,
        )
        
        # Define complete encounter structure from ROM analysis
        self.encounter_struct = Struct(
            "walkrate" / Int8ul,
            "surfrate" / Int8ul,
            "rocksmashrate" / Int8ul,
            "oldrodrate" / Int8ul,
            "goodrodrate" / Int8ul,
            "superrodrate" / Int8ul,
            Padding(2),
            "walklevels" / Array(12, Int8ul),
            "morning" / Array(12, Int16ul),
            "day" / Array(12, Int16ul),
            "night" / Array(12, Int16ul),
            "hoenn" / Array(2, Int16ul),
            "sinnoh" / Array(2, Int16ul),
            "surf" / Array(5, EncounterSlot),
            "rocksmash" / Array(2, EncounterSlot),
            "oldrod" / Array(5, EncounterSlot),
            "goodrod" / Array(5, EncounterSlot),
            "superrod" / Array(5, EncounterSlot),
            "swarm_grass" / Int16ul,
            "swarm_surf" / Int16ul,
            "swarm_goodrod" / Int16ul,
            "swarm_superrod" / Int16ul,
        )
        
        super().__init__(context)
        
        # Load ROM data
        self.data = self.load_narc()
        
        # Enrich with location names - fail if not available
        location_names_step = context.get(LoadEncounterNamesStep)
        for i, encounter in enumerate(self.data):
            if i not in location_names_step.location_names:
                raise KeyError(f"No location name found for encounter {i}")
            encounter.location_name = location_names_step.location_names[i]
            encounter.location_id = i
    
    def get_narc_path(self):
        return "a/0/3/7"
    
    def parse_file(self, file_data, index):
        encounter = self.encounter_struct.parse(file_data)
        return encounter
    
    def serialize_file(self, data, index):
        return self.encounter_struct.build(data)


class RandomizeEncountersStep(Step):
    """Step that randomizes encounter data using global replacement mapping."""
    
    def __init__(self, bst_factor=0.15):
        self.bst_factor = bst_factor
        self.global_replacements = {}
    
    def run(self, context):
        mondata = context.get(MondataExtractor)
        encounters = context.get(EncounterExtractor)
        blacklist = context.get(LoadBlacklistStep)
        
        # Create a global mapping of Pokemon to their replacements
        # This ensures that the same Pokemon species is always replaced by the same species
        self.global_replacements = {}
        
        # For each Pokemon, determine its replacement once
        for pokemon_id in range(1, len(mondata.data)):
            # Skip special Pokemon
            if pokemon_id in SPECIAL_POKEMON or pokemon_id in blacklist.by_id:
                self.global_replacements[pokemon_id] = pokemon_id
                continue
                
            mon = mondata.data[pokemon_id]
            replacements = mondata.find_replacements(mon, 1 - self.bst_factor, 1 + self.bst_factor)
            # Filter out already used replacements
            # replacements = [r for r in replacements if r not in self.global_replacements.values()]
            
            if not replacements:
                raise RuntimeError(f"No suitable replacements found for Pokemon {pokemon_id} ({mon.name}) with BST {mon.bst}")
                
            self.global_replacements[pokemon_id] = random.choice(replacements)
        
        # Randomize each encounter location
        for i, encounter in enumerate(encounters.data):
            self._randomize_encounter(encounter, i, mondata.data)
    
    def _randomize_encounter(self, encounter, location_id, mondata):
        """Randomize a single encounter location."""
        # Randomize morning, day, and night encounter slots
        self._randomize_slot_list(encounter.morning, mondata)
        self._randomize_slot_list(encounter.day, mondata)
        self._randomize_slot_list(encounter.night, mondata)
    
    def _randomize_slot_list(self, slot_list, mondata):
        """Randomize a list of Pokemon encounter slots."""
        for i, species_id in enumerate(slot_list):
            if species_id == 0:  # Empty slot
                continue
                
            if species_id not in self.global_replacements:
                raise KeyError(f"No replacement mapping found for Pokemon species {species_id}")
                
            # Get replacement from global mapping
            replacement_id = self.global_replacements[species_id]
            slot_list[i] = replacement_id


if __name__ == "__main__":
    
    # Load ROM
    with open("rom.nds", "rb") as f:
        rom = ndspy.rom.NintendoDSRom(f.read())
    
    # Create context and load data
    ctx = RandomizationContext(rom)
    
    # Load data but don't randomize yet
    ctx.run_pipeline([
        LoadPokemonNamesStep("."),
        LoadMoveNamesStep(),
        LoadBlacklistStep(),
        LoadEncounterNamesStep(".")
    ])
    
    # Get encounter data BEFORE randomization
    mondata = ctx.get(MondataExtractor)
    encounters = ctx.get(EncounterExtractor)
    moves = ctx.get(MoveDataExtractor)
    print(f"Loaded {len(mondata.data)} Pokemon")
    print(f"Loaded {len(encounters.data)} encounter locations")
    print(f"Loaded {len(moves.data)} moves")
    
    # Print first 10 moves with details
    print("\nFirst 10 moves:")
    for i in range(min(10, len(moves.data))):
        move = moves.data[i]
        flags_str = ", ".join(move.flag_names) if move.flag_names else "None"
        print(f"  {i:3}: {move.name:15} | {move.base_power:3} BP | {move.type_name:8} | {move.split_name:8} | Acc: {move.accuracy:3} | PP: {move.pp:2} | Flags: {flags_str}")
    print("\n=== ENCOUNTER DATA BEFORE RANDOMIZATION ===\n")
    
    def print_encounter_slots(encounter, mondata):
        """Helper to print encounter slot details"""
        print(f"  Morning: {[f'{slot}:{mondata.data[slot].name}' if slot > 0 else 'Empty' for slot in encounter.morning[:5]]}")
        print(f"  Day:     {[f'{slot}:{mondata.data[slot].name}' if slot > 0 else 'Empty' for slot in encounter.day[:5]]}")
        print(f"  Night:   {[f'{slot}:{mondata.data[slot].name}' if slot > 0 else 'Empty' for slot in encounter.night[:5]]}")
    
    # Show first 5 encounters before randomization
    for i in range(min(5, len(encounters.data))):
        encounter = encounters.data[i]
        print(f"{i:3d}: {encounter.location_name}")
        print_encounter_slots(encounter, mondata)
        print()
    
    # Now run randomization
    print("\n=== RUNNING RANDOMIZATION ===\n")
    ctx.run_pipeline([RandomizeEncountersStep()])
    
    # Show same encounters after randomization
    print("\n=== ENCOUNTER DATA AFTER RANDOMIZATION ===\n")
    for i in range(min(5, len(encounters.data))):
        encounter = encounters.data[i]
        print(f"{i:3d}: {encounter.location_name}")
        print_encounter_slots(encounter, mondata)
        print()