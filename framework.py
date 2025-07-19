"""
ROM data extraction and randomization framework.

Provides a flexible, extensible system for reading, modifying, and writing 
structured ROM data using context-managed extractor singletons and ordered 
processing steps.
"""

from abc import ABC, abstractmethod
from typing import List
import ndspy.rom
import ndspy.narc
import os
import re
import random
import sys
from construct import Struct, Int8ul, Int16ul, Int32ul, Array, Padding, Computed, this, Enum, FlagsEnum, RawCopy

from enums import (
    TypeEnum,
    SplitEnum,
    ContestEnum,
    MoveFlagsEnum,
    TargetEnum,
    TrainerDataTypeEnum,
    BattleTypeEnum
)


class Filter(ABC):
    @abstractmethod
    def filter_all(self, context, original, candidates: List) -> List:
        pass

class SimpleFilter(Filter):
    @abstractmethod
    def check(self, context, original, candidate) -> bool:
        pass
    
    def filter_all(self, context, original, candidates: List) -> List:
        return [c for c in candidates if self.check(context, original, c)]

class BstWithinFactor(SimpleFilter):
    """Filter Pokemon within a BST factor of the original."""
    def __init__(self, factor: float):
        self.factor = factor
    
    def check(self, context, original, candidate) -> bool:
        return abs(candidate.bst - original.bst) <= original.bst * self.factor

class InTypeList(SimpleFilter):
    """Filter Pokemon that are in a specific type list."""
    def __init__(self, type_ids: List[int]):
        self.type_ids = set(type_ids)
    
    def check(self, context, original, candidate) -> bool:
        return candidate.pokemon_id in self.type_ids

class NotInSet(SimpleFilter):
    """Filter out specific IDs."""
    def __init__(self, excluded: set):
        self.excluded = excluded
    
    def check(self, context, original, candidate) -> bool:
        return candidate.pokemon_id not in self.excluded

class Tiered(Filter):
    """Try filters in order until one produces results."""
    def __init__(self, filters: List[Filter]):
        self.filters = filters
    
    def filter_all(self, context, original, candidates: List) -> List:
        for f in self.filters:
            filtered = f.filter_all(context, original, candidates)
            if filtered:
                return filtered
        return []

class AllFilters(Filter):
    """Combine multiple filters with AND logic."""
    def __init__(self, filters: List[Filter]):
        self.filters = filters
    
    def filter_all(self, context, original, candidates: List) -> List:
        result = candidates
        for f in self.filters:
            result = f.filter_all(context, original, result)
            if not result:
                break
        return result


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


class ObjectRegistry:
    """Mixin for managing singleton object instances with circular dependency detection."""
    
    def __init__(self):
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


class RandomizationContext(ObjectRegistry):
    """Manages ROM data, pipeline execution, and shared objects."""
    
    def __init__(self, rom, verbosity=0):
        super().__init__()
        self.rom = rom
        self.verbosity = verbosity
    
    def decide(self, path, original, candidates, filter):
        """Make a decision by filtering candidates and selecting one.
        
        This is the central decision point that handles filtering, logging,
        and fallback behavior in a type-agnostic way.
        
        Args:
            path: Decision path as list for logging (e.g. ["trainers", "Falkner", "team", 2, "species"])
            original: Original item being replaced (any type)
            candidates: List of all possible replacements (any type)
            filter: Filter to apply
            
        Returns:
            Selected candidate, or original if no valid candidates
        """
        path_str = "/" + "/".join(str(p) for p in path)
        
        # Log what we're trying to do
        if self.verbosity >= 3:
            print(f"{path_str:50} {len(candidates)} candidates")
        
        # Log full candidate set if very verbose
        if self.verbosity >= 5:
            print(f"{path_str:50}   All candidates:")
            for c in candidates:
                print(f"{path_str:50}     - {c}")
        
        # Apply the filter
        filtered = filter.filter_all(self, original, candidates)
        
        # Log filter results
        if self.verbosity >= 3:
            print(f"{path_str:50} {len(filtered)} candidates")
        
        if self.verbosity >= 5:
            print(f"{path_str:50} Filtered candidates:")
            for c in filtered:
                print(f"{path_str:50}     - {c}")
        
        # Handle no valid candidates
        if not filtered:
            if self.verbosity >= 1:
                print(f"{path_str:50} [WARNING] No valid candidates, keeping original")
            return original
        
        # Select from filtered candidates
        selected = random.choice(filtered)
        
        # Log the decision
        if self.verbosity >= 2:
            sn = selected.name if hasattr(selected, "name") else repr(selected)
            print(f"{path_str:50} -> {sn}")
        
        return selected
    
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
        # Get dependencies first
        move_names_step = context.get(LoadMoveNamesStep)
        
        # Define move data structure (16 bytes total)
        self.move_struct = Struct(
            "battle_effect" / Int16ul,    # 2 bytes
            "pss" / Enum(Int8ul, SplitEnum),               # 1 byte (physical/special/status split)
            "base_power" / Int8ul,        # 1 byte
            "type" / Enum(Int8ul, TypeEnum),              # 1 byte
            "accuracy" / Int8ul,          # 1 byte
            "pp" / Int8ul,                # 1 byte  
            "effect_chance" / Int8ul,     # 1 byte
            "target" / Enum(Int16ul, TargetEnum),           # 2 bytes
            "priority" / Int8ul,          # 1 byte (unsigned for now)
            "flags" / FlagsEnum(Int8ul, MoveFlagsEnum),             # 1 byte
            "appeal" / Int8ul,            # 1 byte
            "contest_type" / Enum(Int8ul, ContestEnum),      # 1 byte
            Padding(2),                   # 2 bytes (terminatedata)
            "move_id" / Computed(lambda ctx: ctx._.narc_index),
            "name" / Computed(lambda ctx: move_names_step.by_id.get(ctx._.narc_index, None))
        )
        
        super().__init__(context)
        self.data = self.load_narc()

    
    def get_narc_path(self):
        return "a/0/1/1"  # Move data NARC
    
    def get_struct(self):
        return self.move_struct
    
    def parse_file(self, file_data, file_index):
        """Parse a single move file into move data."""
        return self.move_struct.parse(file_data, narc_index=file_index)
    
    def serialize_file(self, data):
        """Serialize move data back to binary format."""
        return self.move_struct.build(data)

class LoadTrainerNamesStep(Step):
    """Step that loads trainer names from assembly source."""
    
    def __init__(self, base_path="."):
        self.base_path = base_path
        self.by_id = {}
        self.by_name = {}
        
        # Parse trainer names from assembly source file
        trainer_file = os.path.join(base_path, "armips", "data", "trainers", "trainers.s")
        try:
            with open(trainer_file, "r", encoding="utf-8") as f:
                pattern = r"trainerdata\s+(\d+),\s+\"([^\"]+)\""
                for line in f:
                    match = re.search(pattern, line)
                    if match:
                        trainer_id = int(match.group(1))
                        name = match.group(2)
                        self.by_id[trainer_id] = name
                        self.by_name[name] = trainer_id
        except FileNotFoundError:
            # If file doesn't exist, use empty mappings
            pass
    
    def run(self, context):
        context.register_step(self)


class TrainerTeamExtractor(ExtractorStep):
    """Extractor for trainer team data from ROM."""
    
    def __init__(self, context):
        # Get dependencies first so we can close over them in computed fields
        mondata_extractor = context.get(MondataExtractor)
        move_extractor = context.get(MoveDataExtractor)

        def c_species(ctx):
            return mondata_extractor.data[ctx.species_id]
        
        # Define 4 Pokemon data formats based on trainer flags
        self.trainer_pokemon_basic = Struct(
            "ivs" / Int8ul,             # 1 byte - IVs
            "abilityslot" / Int8ul,     # 1 byte - Ability slot
            "level" / Int16ul,          # 2 bytes - Level
            "species_id" / Int16ul,     # 2 bytes - Species ID
            "ballseal" / Int16ul,       # 2 bytes - Ball seal
            "species" / Computed(c_species)
        )
        
        self.trainer_pokemon_items = Struct(
            "ivs" / Int8ul,             # 1 byte - IVs
            "abilityslot" / Int8ul,     # 1 byte - Ability slot
            "level" / Int16ul,          # 2 bytes - Level
            "species_id" / Int16ul,     # 2 bytes - Species ID
            "item" / Int16ul,           # 2 bytes - Held item
            "ballseal" / Int16ul,       # 2 bytes - Ball seal
            "species" / Computed(c_species)
        )
        
        self.trainer_pokemon_moves = Struct(
            "ivs" / Int8ul,             # 1 byte - IVs
            "abilityslot" / Int8ul,     # 1 byte - Ability slot
            "level" / Int16ul,          # 2 bytes - Level
            "species_id" / Int16ul,     # 2 bytes - Species ID
            "moves" / Array(4, Int16ul), # 8 bytes - Move IDs
            "ballseal" / Int16ul,       # 2 bytes - Ball seal
            "species" / Computed(c_species)
        )
        
        self.trainer_pokemon_full = Struct(
            "ivs" / Int8ul,             # 1 byte - IVs
            "abilityslot" / Int8ul,     # 1 byte - Ability slot
            "level" / Int16ul,          # 2 bytes - Level
            "species_id" / Int16ul,     # 2 bytes - Species ID
            "item" / Int16ul,           # 2 bytes - Held item
            "moves" / Array(4, Int16ul), # 8 bytes - Move IDs
            "ballseal" / Int16ul,       # 2 bytes - Ball seal
            "species" / Computed(c_species)
        )
        
        # Create format lookup table using bytestring keys
        from enums import TrainerDataTypeEnum
        self.format_map = {
            bytes([TrainerDataTypeEnum.NOTHING]): self.trainer_pokemon_basic,
            bytes([TrainerDataTypeEnum.MOVES]): self.trainer_pokemon_moves,
            bytes([TrainerDataTypeEnum.ITEMS]): self.trainer_pokemon_items,
            bytes([TrainerDataTypeEnum.MOVES | TrainerDataTypeEnum.ITEMS]): self.trainer_pokemon_full,
        }
        
        super().__init__(context)
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/5/6"  # Trainer team data NARC
    
    def parse_file(self, file_data, index):
        """Parse trainer team data using trainer data flags to determine format."""
        if len(file_data) == 0:
            return {"pokemon": [], "has_moves": False}
        
        # Get trainer data to determine format
        trainer_data_extractor = self.context.get(TrainerDataExtractor)
        trainer_data = trainer_data_extractor.data[index]
        
        # Get Pokemon struct based on trainer flags
        flags_bytes = trainer_data.trainermontype.data
        pokemon_struct = self.format_map[flags_bytes]
        
        # Parse pokemon data using construct Array
        pokemon_list = Array(trainer_data.nummons, pokemon_struct).parse(file_data)
        
        from construct import Container
        trainer = Container()
        trainer.pokemon = pokemon_list
        trainer.num_pokemon = trainer_data.nummons
        
        return trainer
    
    def serialize_file(self, data, index):
        """Serialize trainer team data back to binary format."""
        if not data.pokemon:
            return b''
        
        # Get trainer data to determine format
        trainer_data_extractor = self.context.get(TrainerDataExtractor)
        trainer_data = trainer_data_extractor.data[index]
        
        # Get Pokemon struct based on trainer flags
        flags_bytes = trainer_data.trainermontype.data
        pokemon_struct = self.format_map[flags_bytes]
        
        # Serialize pokemon data using construct Array
        return Array(trainer_data.nummons, pokemon_struct).build(data.pokemon)


class TrainerDataExtractor(ExtractorStep):
    """Extractor for trainer data from ROM."""
    
    def __init__(self, context):
        # Get dependencies first
        trainer_names_step = context.get(LoadTrainerNamesStep)
        
        # Define trainer data structure (20 bytes total) - corrected order from assembly
        self.trainer_data_struct = Struct(
            "trainermontype" / RawCopy(FlagsEnum(Int8ul, TrainerDataTypeEnum)),  # 1 byte
            "trainerclass" / Int16ul,      # 2 bytes
            "nummons" / Int8ul,            # 1 byte
            "item1" / Int16ul,             # 2 bytes
            "item2" / Int16ul,             # 2 bytes
            "item3" / Int16ul,             # 2 bytes
            "item4" / Int16ul,             # 2 bytes
            "aiflags" / Int32ul,           # 4 bytes
            "battletype" / Enum(Int8ul, BattleTypeEnum),  # 1 byte
            Padding(2),                    # 2 bytes padding
            "name" / Computed(lambda ctx: trainer_names_step.by_id[ctx._.narc_index])
        )
        
        super().__init__(context)
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/5/5"  # Trainer data NARC
    
    def parse_file(self, file_data, index):
        """Parse trainer data and add index for team linking."""
        trainer = self.trainer_data_struct.parse(file_data, narc_index=index)
        return trainer
    
    def serialize_file(self, data, index):
        """Serialize trainer data back to binary format."""
        return self.trainer_data_struct.build(data)


class TrainerInfo:
    def __init__(self, trainer_data, team_data):
        self.info = trainer_data
        self.team = team_data


class TrainerCombinedExtractor(Extractor):
    def __init__(self, context):
        super().__init__(context)
        
        trainer_data_extractor = context.get(TrainerDataExtractor)
        trainer_team_extractor = context.get(TrainerTeamExtractor)
        
        self.data = [
            TrainerInfo(trainer_data_extractor.data[i], trainer_team_extractor.data[i])
            for i in range(len(trainer_data_extractor.data))
        ]


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
            self.by_id.add(names_step.by_name[name])
        
        context.register_step(self)


class MondataExtractor(ExtractorStep):
    """Extractor for Pokemon data from ROM with full mondata structure."""
    
    def __init__(self, context):
        # Get dependencies first
        pokemon_names_step = context.get(LoadPokemonNamesStep)
        
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
            "type1" / Enum(Int8ul, TypeEnum),
            "type2" / Enum(Int8ul, TypeEnum),
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
            "additional2" / Int8ul,
            # Computed fields
            "bst" / Computed(lambda ctx: ctx.hp + ctx.attack + ctx.defense + ctx.speed + ctx.sp_attack + ctx.sp_defense),
            "name" / Computed(lambda ctx: pokemon_names_step.by_id[ctx._.narc_index]),
            "pokemon_id" / Computed(lambda ctx: ctx._.narc_index)
        )
        
        super().__init__(context)
        
        # Load ROM data
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/0/2"
    
    def parse_file(self, file_data, index):
        return self.mondata_struct.parse(file_data, narc_index=index)
    
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
        # Get dependencies first
        location_names_step = context.get(LoadEncounterNamesStep)
        
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
            "location_name" / Computed(lambda ctx: location_names_step.location_names[ctx._.narc_index]),
            "location_id" / Computed(lambda ctx: ctx._.narc_index)
        )
        
        super().__init__(context)
        
        # Load ROM data
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/3/7"
    
    def parse_file(self, file_data, index):
        encounter = self.encounter_struct.parse(file_data, narc_index=index)
        return encounter
    
    def serialize_file(self, data, index):
        return self.encounter_struct.build(data)


class RandomizeEncountersStep(Step):
    
    def __init__(self, bst_factor=0.15):
        self.bst_factor = bst_factor
        self.replacements = {}
    
    def run(self, context):
        self.mondata = context.get(MondataExtractor)
        self.encounters = context.get(EncounterExtractor)
        self.blacklist = context.get(LoadBlacklistStep)
        self.context = context
        
        for i, encounter in enumerate(self.encounters.data):
            self._randomize_encounter(encounter, i)
    
    def _randomize_encounter(self, encounter, location_id):
        self._randomize_slot_list(encounter.morning)
        self._randomize_slot_list(encounter.day)
        self._randomize_slot_list(encounter.night)
    
    def _randomize_slot_list(self, slot_list):
        for i, species_id in enumerate(slot_list):
            if species_id == 0:
                continue
            
            if species_id not in self.replacements:
                if species_id in SPECIAL_POKEMON or species_id in self.blacklist.by_id:
                    self.replacements[species_id] = species_id
                else:
                    mon = self.mondata.data[species_id]
                    
                    new_species = self.context.decide(
                        path=["encounters", mon.name],
                        original=mon,
                        candidates=list(self.mondata.data),
                        filter=AllFilters([NotInSet(SPECIAL_POKEMON | self.blacklist.by_id), BstWithinFactor(self.bst_factor)])
                    )
                    
                    self.replacements[species_id] = new_species.pokemon_id
            
            slot_list[i] = self.replacements[species_id]


if __name__ == "__main__":
    
    # Load ROM
    with open("hgeLanceCanary.nds", "rb") as f:
        rom = ndspy.rom.NintendoDSRom(f.read())
    
    # Create context and load data
    ctx = RandomizationContext(rom, verbosity=3)
    
    # Load data but don't randomize yet
    ctx.run_pipeline([
        LoadPokemonNamesStep("."),
        LoadMoveNamesStep(),
        LoadBlacklistStep(),
        LoadEncounterNamesStep("."),
        LoadTrainerNamesStep(".")
    ])
    
    # Get encounter data BEFORE randomization
    mondata = ctx.get(MondataExtractor)
    encounters = ctx.get(EncounterExtractor)
    moves = ctx.get(MoveDataExtractor)
    trainers = ctx.get(TrainerCombinedExtractor)
    print(f"Loaded {len(mondata.data)} Pokemon")
    print(f"Loaded {len(encounters.data)} encounter locations")
    print(f"Loaded {len(moves.data)} moves")
    print(f"Loaded {len(trainers.data)} trainers")
    
    # Print first 10 trainers with details
    for i in range(len(trainers.data)):
        trainer = trainers.data[i]
        #team_info = f"{trainer.info.nummons} Pokemon ({trainer.info.trainermontype})"
        pokemon_names = [p.species.name for p in trainer.team.pokemon]
        print(i, trainer.info.name, trainer.info.nummons, [f"lv {m.level} {m.species.name}" for m in trainer.team.pokemon])
        # print(f"  {i:3}: {trainer.info.name:20} | {team_info} | Pokemon: {pokemon_names}")
    
    sys.exit()

    # Print first 10 moves with details
    print("\nFirst 10 moves:")
    for i in range(min(10, len(moves.data))):
        move = moves.data[i]
        # flags_str = ", ".join(str(flag) for flag in move.flags) if move.flags else "None"
        print(f"  {i:3}: {move.name:15} | {move.base_power:3} BP | {move.type:8} | {move.pss:8} | Acc: {move.accuracy:3} | PP: {move.pp:2} | Flags: {repr(move.flags)}")
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
