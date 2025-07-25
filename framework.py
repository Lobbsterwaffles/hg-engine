"""
ROM data extraction and randomization framework.

Provides a flexible, extensible system for reading, modifying, and writing 
structured ROM data using context-managed extractor singletons and ordered 
processing steps.
"""

from abc import ABC, abstractmethod
from typing import List
from collections import Counter
import ndspy.rom
import ndspy.narc
import os
import re
import random
import sys
from construct import Struct, Int8ul, Int16ul, Int32ul, Array, Padding, Computed, this, Enum, FlagsEnum, RawCopy, Container, GreedyRange, StopIf, Check

from enums import (
    Type,
    Split,
    Contest,
    MoveFlags,
    Target,
    TrainerDataType,
    BattleType,
    TrainerClass
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

class TypeMatches(SimpleFilter):
    """Filter Pokemon that have type1 or type2 matching any of the specified types."""
    def __init__(self, type_ids: List[int]):
        self.type_ids = set(type_ids)
    
    def check(self, context, original, candidate) -> bool:
        # print("TMC", self.type_ids, candidate.type1, candidate.type2)
        # import pdb
        # pdb.set_trace()
        return (int(candidate.type1) in self.type_ids or int(candidate.type2) in self.type_ids)

    def __repr__(self):
        s = ","
        return f"TypeMatches({s.join([repr(Type(t)) for t in self.type_ids])})"
    

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

    def __repr__(self):
        s = ","
        return f"AllFilters({s.join([repr(f) for f in self.filters])})"


class NoFilter(Filter):
    """Filter that passes all candidates unchanged."""
    def filter_all(self, context, original, candidates: List) -> List:
        return candidates


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
        narc_file_id = self.rom.filenames.idOf(self.get_narc_path())
        narc_file = self.rom.files[narc_file_id]
        narc_data = ndspy.narc.NARC(narc_file)
        return self.parse_narc(narc_data)
    
    def write_to_rom(self):
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
                on = original.name if hasattr(original, "name") else repr(original)
                print(f"{path_str:50} [WARNING] No valid candidates, keeping original: {on}")
                print(f"{path_str:50}           Filter: {repr(filter)}")
                
            return original
        
        # Select from filtered candidates
        selected = random.choice(filtered)
        
        # Log the decision
        if self.verbosity >= 2:
            sn = selected.name if hasattr(selected, "name") else repr(selected)
            on = original.name if hasattr(original, "name") else repr(original)
            print(f"{path_str:50} {on:20} -> {sn:20}")
        
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


SPECIAL_POKEMON = {
    150, 151, 243, 244, 245, 249, 250, 251, 377, 378, 379, 380, 381, 382, 383, 384,
    385, 386, 483, 484, 487, 488, 489, 490, 491, 492, 493, 494
}



class NameTableReader(Step):
    """Base class for reading name tables from text files."""
    
    def __init__(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            names_list = [line.strip() for line in f.readlines()]

        self.id_to_name = {}
        self.name_to_ids = {}

        for i, name in enumerate(names_list):
            self.id_to_name[i] = name
            if name not in self.name_to_ids:
                self.name_to_ids[name] = []
            self.name_to_ids[name].append(i)

    def get_by_id(self, i):
        return self.id_to_name[i]

    def get_by_name(self, n):
        ns = self.get_all_by_name(n)
        if len(ns) > 1:
            print(f"!!! Use of duplicate name: {repr(n)} => {repr(ns)}")
        return ns[0]

    def get_all_by_name(self, n):
        return self.name_to_ids[n]
    
    def run(self, context):
        context.register_step(self)


class LoadPokemonNamesStep(NameTableReader):
    def __init__(self, base_path="."):
        super().__init__("build/rawtext/237.txt")
        
class LoadMoveNamesStep(NameTableReader):
    def __init__(self):
        super().__init__("build/rawtext/750.txt")

class LoadAbilityNames(NameTableReader):
    def __init__(self):
        super().__init__("data/text/720.txt")

class MoveDataExtractor(ExtractorStep):
    """Extractor for move data from ROM with full move structure."""
    
    def __init__(self, context):
        move_names_step = context.get(LoadMoveNamesStep)
        
        self.move_struct = Struct(
            "battle_effect" / Int16ul,
            "pss" / Enum(Int8ul, Split),
            "base_power" / Int8ul,
            "type" / Enum(Int8ul, Type),
            "accuracy" / Int8ul,
            "pp" / Int8ul,
            "effect_chance" / Int8ul,
            "target" / Enum(Int16ul, Target),
            "priority" / Int8ul,
            "flags" / FlagsEnum(Int8ul, MoveFlags),
            "appeal" / Int8ul,
            "contest_type" / Enum(Int8ul, Contest),
            Padding(2),
            "move_id" / Computed(lambda ctx: ctx._.narc_index),
            "name" / Computed(lambda ctx: move_names_step.id_to_name.get(ctx._.narc_index, None))
        )
        
        super().__init__(context)
        self.data = self.load_narc()

    
    def get_narc_path(self):
        return "a/0/1/1"  # Move data NARC
    
    def get_struct(self):
        return self.move_struct
    
    def parse_file(self, file_data, file_index):
        return self.move_struct.parse(file_data, narc_index=file_index)
    
    def serialize_file(self, data, index):
        return self.move_struct.build(data, narc_index=index)


class Learnsets(ExtractorStep):
    def __init__(self, context):
        moves = context.get(MoveDataExtractor).data

        self.struct = GreedyRange(Struct(
            "move_id" / Int16ul,
            "level" / Int16ul,
            Check(lambda ctx: ctx.move_id != 0xffff),
            "move" / Computed(lambda ctx: moves[ctx.move_id] if ctx.move_id < len(moves) else None),
        ))
        
        super().__init__(context)
        
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/3/3"
    
    def parse_file(self, file_data, index):
        return self.struct.parse(file_data, narc_index=index)
    
    def serialize_file(self, data, index):
        return self.struct.build(data, narc_index=index)


class LoadTrainerNamesStep(Step):
    """Step that loads trainer names from assembly source."""
    
    def __init__(self, base_path="."):
        self.base_path = base_path
        self.by_id = {}
        self.by_name = {}
        
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
            pass
    
    def run(self, context):
        context.register_step(self)


class TrainerTeamExtractor(ExtractorStep):
    """Extractor for trainer team data from ROM."""
    
    def __init__(self, context):
        mondata_extractor = context.get(MondataExtractor)
        move_extractor = context.get(MoveDataExtractor)

        self.trainer_pokemon_basic = Struct(
            "ivs" / Int8ul,
            "abilityslot" / Int8ul,
            "level" / Int16ul,
            "species_id" / Int16ul,
            "ballseal" / Int16ul
        )
        
        self.trainer_pokemon_items = Struct(
            "ivs" / Int8ul,
            "abilityslot" / Int8ul,
            "level" / Int16ul,
            "species_id" / Int16ul,
            "item" / Int16ul,
            "ballseal" / Int16ul
        )
        
        self.trainer_pokemon_moves = Struct(
            "ivs" / Int8ul,
            "abilityslot" / Int8ul,
            "level" / Int16ul,
            "species_id" / Int16ul,
            "moves" / Array(4, Int16ul),
            "ballseal" / Int16ul
        )
        
        self.trainer_pokemon_full = Struct(
            "ivs" / Int8ul,
            "abilityslot" / Int8ul,
            "level" / Int16ul,
            "species_id" / Int16ul,
            "item" / Int16ul,
            "moves" / Array(4, Int16ul),
            "ballseal" / Int16ul
        )
        
        self.format_map = {
            bytes([TrainerDataType.NOTHING]): self.trainer_pokemon_basic,
            bytes([TrainerDataType.MOVES]): self.trainer_pokemon_moves,
            bytes([TrainerDataType.ITEMS]): self.trainer_pokemon_items,
            bytes([TrainerDataType.MOVES | TrainerDataType.ITEMS]): self.trainer_pokemon_full,
        }
        
        super().__init__(context)
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/5/6"  # Trainer team data NARC
    
    def parse_file(self, file_data, index):
        if len(file_data) == 0:
            return []
        
        trainer_data_extractor = self.context.get(TrainerDataExtractor)
        trainer_data = trainer_data_extractor.data[index]
        
        flags_bytes = trainer_data.trainermontype.data
        pokemon_struct = self.format_map[flags_bytes]
        
        return Array(trainer_data.nummons, pokemon_struct).parse(file_data)
    
    def serialize_file(self, data, index):
        if not data:
            return b''
        
        trainer_data_extractor = self.context.get(TrainerDataExtractor)
        trainer_data = trainer_data_extractor.data[index]
        
        flags_bytes = trainer_data.trainermontype.data
        pokemon_struct = self.format_map[flags_bytes]
        
        return Array(trainer_data.nummons, pokemon_struct).build(data)


class TrainerDataExtractor(ExtractorStep):
    """Extractor for trainer data from ROM."""
    
    def __init__(self, context):
        trainer_names_step = context.get(LoadTrainerNamesStep)
        
        self.trainer_data_struct = Struct(
            "trainermontype" / RawCopy(FlagsEnum(Int8ul, TrainerDataType)),
            "trainerclass" / Int16ul,
            "nummons" / Int8ul,
            "item1" / Int16ul,
            "item2" / Int16ul,
            "item3" / Int16ul,
            "item4" / Int16ul,
            "aiflags" / Int32ul,
            "battletype" / Enum(Int8ul, BattleType),
            Padding(2),
            "trainer_id" / Computed(lambda ctx: ctx._.narc_index),
            "name" / Computed(lambda ctx: trainer_names_step.by_id[ctx._.narc_index])
        )
        
        super().__init__(context)
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/5/5"  # Trainer data NARC
    
    def parse_file(self, file_data, index):
        trainer = self.trainer_data_struct.parse(file_data, narc_index=index)
        return trainer
    
    def serialize_file(self, data, index):
        return self.trainer_data_struct.build(data, narc_index=index)


class TrainerInfo:
    def __init__(self, trainer_data, team_data):
        self.info = trainer_data
        self.team = team_data
        self.ace_index = self._compute_ace_index() if self.team else None
        self.ace = self.team[self.ace_index] if self.ace_index else None
    
    def _compute_ace_index(self):
        maxlvl = max(pokemon.level for pokemon in self.team)
        imaxlvl = [i for i, pokemon in enumerate(self.team) if pokemon.level == maxlvl]
        return imaxlvl[0] if len(imaxlvl) == 1 else None

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
        self.by_id = set()
                        
    def run(self, context):
        names_step = context.get(LoadPokemonNamesStep)
        
        fixed = [
            "Bad Egg"
        ]

        for name in fixed:
            self.by_id.add(names_step.get_by_name(name))

        for fid in names_step.get_all_by_name("-----"):
            self.by_id.add(fid)
        
        context.register_step(self)


class MondataExtractor(ExtractorStep):
    """Extractor for Pokemon data from ROM with full mondata structure."""
    
    def __init__(self, context):
        pokemon_names_step = context.get(LoadPokemonNamesStep)
        
        self.mondata_struct = Struct(
            "hp" / Int8ul,
            "attack" / Int8ul, 
            "defense" / Int8ul,
            "speed" / Int8ul,
            "sp_attack" / Int8ul,
            "sp_defense" / Int8ul,
            "type1" / Enum(Int8ul, Type),
            "type2" / Enum(Int8ul, Type),
            "catch_rate" / Int8ul,
            "base_exp" / Int8ul,
            "ev_yields" / Int16ul,
            "item1" / Int16ul,
            "item2" / Int16ul,
            "gender_ratio" / Int8ul,
            "egg_cycles" / Int8ul,
            "base_friendship" / Int8ul,
            "growth_rate" / Int8ul,
            "egg_group1" / Int8ul,
            "egg_group2" / Int8ul,
            "ability1" / Int8ul,
            "ability2" / Int8ul,
            "additional1" / Int8ul,
            "additional2" / Int8ul,
            "bst" / Computed(lambda ctx: ctx.hp + ctx.attack + ctx.defense + ctx.speed + ctx.sp_attack + ctx.sp_defense),
            "name" / Computed(lambda ctx: pokemon_names_step.get_by_id(ctx._.narc_index)),
            "pokemon_id" / Computed(lambda ctx: ctx._.narc_index)
        )
        
        super().__init__(context)
        
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/0/2"
    
    def parse_file(self, file_data, index):
        return self.mondata_struct.parse(file_data, narc_index=index)
    
    def serialize_file(self, data, index):
        return self.mondata_struct.build(data, narc_index=index)
    
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
        encounter_file = os.path.join("armips", "data", "encounters.s")
        with open(encounter_file, "r", encoding="utf-8") as f:
            for line in f:
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
        location_names_step = context.get(LoadEncounterNamesStep)
        
        EncounterSlot = Struct(
            "species" / Int16ul,
            "minlevel" / Int8ul,
            "maxlevel" / Int8ul,
        )
        
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
        
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/3/7"
    
    def parse_file(self, file_data, index):
        encounter = self.encounter_struct.parse(file_data, narc_index=index)
        return encounter
    
    def serialize_file(self, data, index):
        return self.encounter_struct.build(data, narc_index=index)


class RandomizeEncountersStep(Step):
    
    def __init__(self, filter):
        self.filter = filter
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
                        filter=self.filter
                    )
                    
                    self.replacements[species_id] = new_species.pokemon_id
            
            slot_list[i] = self.replacements[species_id]


class IndexTrainers(Step):
    def __init__(self):
        self.data = {}

    def run(self, context):
        trainers = ctx.get(TrainerCombinedExtractor)
        for t in trainers.data:
            if t.info.name not in self.data:
                self.data[t.info.name] = []
            self.data[t.info.name].append((t.info.trainerclass, t.info.trainer_id))
        context.register_step(self)

    def find(self, name_or_tuple):
        if isinstance(name_or_tuple, tuple):
            (cls, name) = name_or_tuple
            return self._find(cls, name)
        return self._find(None, name_or_tuple)

    def _find(self, cls, name):
        rs = [tid for (tc, tid) in self.data[name] if cls is None or cls == tc]
        #if len(rs) != 1:
        #  This is fine
        #  print(f"Cannot find unique trainer {name}, class {cls} - {repr(rs)}")
        return rs[0] if len(rs) > 0 else None

class ExpandTrainerTeamsStep(Step):
    """Step to expand trainer teams to a specified size by duplicating the first Pokemon."""
    
    def __init__(self, target_size=6):
        if not (1 <= target_size <= 6):
            raise ValueError("Target team size must be between 1 and 6 inclusive")
        self.target_size = target_size
    
    def run(self, context):
        trainer_data_extractor = context.get(TrainerDataExtractor)
        trainer_team_extractor = context.get(TrainerTeamExtractor)
        
        for i in range(len(trainer_data_extractor.data)):
            self._expand_trainer_team(trainer_data_extractor.data[i], trainer_team_extractor.data[i])
    
    def _expand_trainer_team(self, trainer_data, team_data):
        """Expand a single trainer's team to target size."""
        current_size = len(team_data)
        
        # Skip if already at or above target size, or if team is empty
        if current_size >= self.target_size or current_size == 0:
            return
        
        # Create copies of the first Pokemon to fill remaining slots
        template_pokemon = team_data[0]
        
        for _ in range(self.target_size - current_size):
            new_pokemon = Container(template_pokemon)
            team_data.append(new_pokemon)
        
        # Update the trainer data's nummons field
        trainer_data.nummons = self.target_size


class IdentifyGymTrainers(Step):
    class Gym:
        def __init__(self, name, trainers, gym_type=None):
            self.name = name
            self.trainers = trainers
            self.type = gym_type
    
    def __init__(self):
        self.data = {}
    
    def _detect_gym_type(self, trainers):
        type_counts = Counter()
        
        mondata = self.context.get(MondataExtractor)
        
        for trainer in trainers:
            for pokemon in trainer.team:
                species = mondata.data[pokemon.species_id]
                type_counts[Type(int(species.type1))] += 1
                if species.type2 != species.type1:
                    type_counts[Type(int(species.type2))] += 1
        
        return type_counts.most_common(1)[0][0] if type_counts else None

    def run(self, context):
        self.context = context
        trainers = context.get(TrainerCombinedExtractor)
        index = context.get(IndexTrainers)
        
        gym_definitions = {
            "Violet City": ["Falkner", "Abe", "Rod"],
            "Azalea Town": ["Bugsy", "Al", "Benny", "Amy & Mimi"],
            "Goldenrod City": ["Victoria", "Samantha", "Carrie", "Cathy", "Whitney"],
            "Ecruteak City": ["Georgina", "Grace", "Edith", "Martha", "Morty"],
            "Cianwood City": ["Yoshi", "Lao", "Lung", "Nob", "Chuck"],
            "Olivine City": ["Jasmine"],
            "Mahogany Town": ["Pryce", (TrainerClass.SKIER, "Diana"), "Patton", "Deandre", "Jill", "Gerardo"],
            "Blackthorn City": ["Paulo", "Lola", "Cody", "Fran", "Mike", "Clair"],
            "Pewter City": ["Jerry", "Edwin", "Brock"],
            "Cerulean City": ["Parker", "Eddie", (TrainerClass.SWIMMER_F, "Diana"), "Joy", "Briana", "Misty"],
            "Vermillion City": ["Horton", "Vincent", "Gregory", "Lt. Surge"],
            "Celadon City": ["Jo & Zoe", "Michelle", "Tanya", "Julia", "Erika"],
            "Fuchsia City": ["Cindy", "Barry", "Alice", "Linda", "Janine"],
            "Saffron City": ["Rebecca", "Jared", "Darcy", "Franklin", "Sabrina"],
            "Seafoam Islands": ["Lowell", "Daniel", "Cary", "Linden", "Waldo", "Merle", "Blaine"],
            "Viridian City": ["Arabella", "Salma", "Bonita", "Elan & Ida", "Blue"],
            "Elite Four": ["Will", "Koga", "Bruno", "Karen", "Lance"]
        }
        
        for gym_name, trainer_specs in gym_definitions.items():
            trainer_ids = [index.find(spec) for spec in trainer_specs]
            gym_trainers = [trainers.data[tid] for tid in trainer_ids if tid is not None]
            
            gym_type = self._detect_gym_type(gym_trainers)
            self.data[gym_name] = self.Gym(gym_name, gym_trainers, gym_type)
        
        context.register_step(self)


class RandomizeGymTypesStep(Step):
    def run(self, context):
        gyms = context.get(IdentifyGymTrainers)
        
        for gym_name, gym in gyms.data.items():
            if gym.type is not None:
                gym.type = context.decide(
                    path=["gyms", gym_name, "type"],
                    original=gym.type,
                    candidates=list(Type),
                    filter=NoFilter()
                )


class RandomizeGymsStep(Step):
    def __init__(self, filter):
        self.filter = filter
    
    def run(self, context):
        gyms = context.get(IdentifyGymTrainers)
        mondata = context.get(MondataExtractor)
        
        for gym_name, gym in gyms.data.items():
            if gym.type is not None:
                self._randomize_gym_teams(context, gym, mondata)
    
    def _randomize_gym_teams(self, context, gym, mondata):
        filter = AllFilters([self.filter, TypeMatches([int(gym.type)])])
        for trainer in gym.trainers:
            self._randomize_trainer_team(context, trainer, mondata, filter)

    def _randomize_trainer_team(self, context, trainer, mondata, filter):
        """Randomize a single trainer's team."""
        for i, pokemon in enumerate(trainer.team):
            new_species = context.decide(
                path=["trainer", trainer.info.name, "team", i, "species"],
                original=mondata.data[pokemon.species_id],
                candidates=list(mondata.data),
                filter=filter
            )
            pokemon.species_id = new_species.pokemon_id


class MakePivots(Step):
    def __init__(self):
        self.pivots = {}

    def run(self, context):
        context.register_step(self)


    def make_pivots(self, context):
        mondata = context.get(MondataExtractor)
        abilities = context.get(LoadAbilityNames)
        type_data = {
            Type.NORMAL: [
                Type.GHOST

            ]
        }


        self.pivots[Type.NORMAL] = [
            m
            for m in mondata.data
            if set(m.type1, m.type2) in [
                    set([])
            ]
        ]
        
        
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test RandomizeGymsStep")
    parser.add_argument("--quiet", action="store_true", help="Run in quiet mode (no output)")
    parser.add_argument("--bst-factor", type=float, default=0.15, help="BST factor for filtering (default: 0.15)")
    parser.add_argument("--seed", type=int, help="rng seed")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(int(args.seed))
    
    # Load ROM
    with open("hgeLanceCanary.nds", "rb") as f:
        rom = ndspy.rom.NintendoDSRom(f.read())
    
    # Create context and load data
    ctx = RandomizationContext(rom, verbosity=0 if args.quiet else 2)
    
    # Load all required data
    ctx.run_pipeline([
        LoadPokemonNamesStep("."),
        LoadMoveNamesStep(),
        LoadTrainerNamesStep("."),
        LoadEncounterNamesStep("."),
        LoadAbilityNames(),
        LoadBlacklistStep(),
        IndexTrainers(),
        IdentifyGymTrainers(),
        
    ])


    levitate_id = ctx.get(LoadAbilityNames).get_by_name('Levitate')
    print([
        m.name
        for m in ctx.get(MondataExtractor).data
        if levitate_id in [m.ability1, m.ability2]
    ])


    # print(ctx.get(Learnsets).data[0])
    # print(ctx.get(Learnsets).data[1])

    # for (i, ls) in enumerate(ctx.get(Learnsets).data):
    #     if i == 0:
    #         continue
    #     if i > 10:
    #         break
    #     print(i, ctx.get(MondataExtractor).data[i].name)
    #     print([(e.level, e.move.name) for e in ls])
        
    # sys.exit(0)



    # Get initial gym data
    gyms = ctx.get(IdentifyGymTrainers)
    if not args.quiet:
        print(f"Identified {len(gyms.data)} gyms")
        for gym_name, gym in gyms.data.items():
            print(f"  {gym_name}: {len(gym.trainers)} trainers, type: {gym.type}")
    
    # Show gym teams before randomization
    if False:
        print("\n=== GYM TEAMS BEFORE RANDOMIZATION ===")
        for gym_name, gym in gyms.data.items():
            print(f"\n{gym_name} ({gym.type}):")
            for trainer in gym.trainers:
                print(f"  {trainer.info.name}:")
                for i, pokemon in enumerate(trainer.team):
                    species = ctx.get(MondataExtractor).data[pokemon.species_id]
                    print(f"    {i}: Lv{pokemon.level} {species.name} ({species.type1}/{species.type2})")
    
    # Create filter combining BST and blacklist constraints
    blacklist = ctx.get(LoadBlacklistStep)
    gym_filter = AllFilters([
        NotInSet(SPECIAL_POKEMON | blacklist.by_id),
        BstWithinFactor(args.bst_factor)
    ])
    
    # Run gym randomization
    if not args.quiet:
        print(f"\n=== RUNNING GYM RANDOMIZATION (BST factor: {args.bst_factor}) ===")
    ctx.run_pipeline([
        RandomizeGymTypesStep(),
        RandomizeGymsStep(gym_filter)
    ])
    
    # Show gym teams after randomization
    if False:
        print("\n=== GYM TEAMS AFTER RANDOMIZATION ===")
        for gym_name, gym in gyms.data.items():
            print(f"\n{gym_name} ({gym.type}):")
            for trainer in gym.trainers:
                print(f"  {trainer.info.name}:")
                for i, pokemon in enumerate(trainer.team):
                    species = ctx.get(MondataExtractor).data[pokemon.species_id]
                    print(f"    {i}: Lv{pokemon.level} {species.name} ({species.type1}/{species.type2})")
    
    # Write changes back to ROM
    if not args.quiet:
        print("\nWriting changes back to ROM...")
    ctx.write_all()
    
    # Save modified ROM
    modified_rom_path = "hgeLanceCanary_gym_randomized.nds"
    with open(modified_rom_path, "wb") as f:
        f.write(rom.save())
    if not args.quiet:
        print(f"Saved modified ROM to {modified_rom_path}")
    
    # Reload test - verify changes persisted
    if not args.quiet:
        print("\n=== RELOAD TEST - Reading back from saved ROM ===")
    
    # Load the modified ROM and create new context
    with open(modified_rom_path, "rb") as f:
        rom2 = ndspy.rom.NintendoDSRom(f.read())
    
    ctx2 = RandomizationContext(rom2, verbosity=0 if args.quiet else 1)
    
    # Load data from the modified ROM
    ctx2.run_pipeline([
        LoadPokemonNamesStep("."),
        LoadMoveNamesStep(), 
        LoadTrainerNamesStep("."),
        LoadEncounterNamesStep("."),
        LoadAbilityNames(),
        LoadBlacklistStep(),
        IndexTrainers(),
        IdentifyGymTrainers(),
    ])
    
    gyms2 = ctx2.get(IdentifyGymTrainers)
    
    if False:
        print("\n=== GYM TEAMS AFTER RELOAD ===")
        for gym_name, gym in gyms2.data.items():
            print(f"\n{gym_name} ({gym.type}):")
            for trainer in gym.trainers:
                print(f"  {trainer.info.name}:")
                for i, pokemon in enumerate(trainer.team):
                    species = ctx2.get(MondataExtractor).data[pokemon.species_id]
                    print(f"    {i}: Lv{pokemon.level} {species.name} ({species.type1}/{species.type2})")
    else:
        print("Gym randomization completed successfully")


        
