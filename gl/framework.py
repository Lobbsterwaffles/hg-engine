# -*- coding: utf-8 -*-
import sys
import os

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

from abc import ABC, abstractmethod
from enums import *
from trainer_data_editor import *
from typing import List
from collections import Counter
import ndspy.rom
import ndspy.narc
import os
import re
import random
from construct import Struct, Int8ul, Int16ul, Int32ul, Array, Padding, Computed, this, Enum, FlagsEnum, RawCopy, Container, GreedyRange, StopIf, Check, BitsSwapped, Bitwise, Flag

from enums import (
    Type,
    Split,
    Contest,
    MoveFlags,
    Target,
    TrainerDataType,
    BattleType,
    TrainerClass,
    EvolutionMethod,
    EvoParam,
    Tier
)
from pivots import pivots_type_data, HasAbility
from fulcrums import fulcrums_type_data


class PathHierMap:
    class Node:
        def __init__(self, value=None):
            self.value = value
            self.children = {}
    
    def __init__(self, mappings):
        self.root = self.Node()
        for path_list, value in mappings:
            node = self.root
            for element in path_list:
                if element not in node.children:
                    node.children[element] = self.Node()
                node = node.children[element]
            node.value = value
    
    def get(self, path):
        def go(node, path, best):
            best = best if node.value is None else node.value
            if not path or path[0] not in node.children:
                return best
            return go(node.children[path[0]], path[1:], best)
        
        path_lower = [str(e).lower() for e in path]
        return go(self.root, path_lower, None)


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
    def __init__(self, factor: float):
        self.factor = factor
    
    def check(self, context, original, candidate) -> bool:
        # For low-BST Pokémon (348 or below), allow all Pokémon with BST 348 or below
        if original.bst <= 348:
            return candidate.bst <= 348
        
        # For higher-BST Pokémon (349 and above), use the factor-based filtering
        return abs(candidate.bst - original.bst) <= original.bst * self.factor

    def __repr__(self):
        return f"BstWithinFactor({self.factor})"

class NotInSet(SimpleFilter):
    def __init__(self, excluded: set):
        self.excluded = excluded
    
    def check(self, context, original, candidate) -> bool:
        return candidate.pokemon_id not in self.excluded

class TypeMatches(SimpleFilter):
    """Filter Pokemon that have type1 or type2 matching any of the specified types."""
    def __init__(self, type_ids: List[int]):
        self.type_ids = set(type_ids)
    
    def check(self, context, original, candidate) -> bool:
        return (int(candidate.type1) in self.type_ids or int(candidate.type2) in self.type_ids)

    def __repr__(self):
        s = ","
        return f"TypeMatches({s.join([str(Type(t)) for t in self.type_ids])})"
    
class Stratified(Filter):
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
    """Base class for all context-managed objects."""
    def __init__(self, context):
        self.context = context
        self.rom = context.rom
    
    def write(self):
        """Write any changes back to ROM. Default is no-op."""
        pass


class NarcExtractor(Extractor):
    """Extractor that provides NARC parsing infrastructure"""
    
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


class Writeback:
    """Mixin that enables ROM writeback for NarcExtractor"""
    def write(self):
        self.write_to_rom()

class Step(ABC):
    """Base class for pipeline steps that run in order."""
    
    @abstractmethod
    def run(self, context):
        """Execute this step."""
        pass


class ObjectRegistry:
    """Mixin for managing singleton object instances with circular dependency detection."""
    
    def __init__(self):
        self._objects = {}
        self._creating = set()
    
    def get(self, obj_class):
        if obj_class in self._objects:
            return self._objects[obj_class]
        
        if obj_class in self._creating:
            raise RuntimeError(f"Circular dependency detected: {obj_class.__name__}")
        
        self._creating.add(obj_class)
        try:
            obj = obj_class(self)
            self._objects[obj_class] = obj
        finally:
            self._creating.remove(obj_class)
        
        return self._objects[obj_class]


class RandomizationContext(ObjectRegistry):
    """Manages ROM data, pipeline execution, and shared objects."""
    
    def __init__(self, rom, verbosity=0, verbosity_overrides=None):
        super().__init__()
        self.rom = rom
        self.verbosity_map = PathHierMap(verbosity_overrides or [([], verbosity)])
    
    def decide(self, path, original, candidates, filter):
        def n(e):
            return e.name if hasattr(e, "name") else repr(e)
    
        path_str = "/" + "/".join(str(p) for p in path)
        verbosity = self.verbosity_map.get(path) or 0
    
        if verbosity >= 3:
            print(f"{path_str:50} {len(candidates)} candidates")
        
        filtered = filter.filter_all(self, original, candidates)
    
        if verbosity >= 3:
            print(f"{path_str:50} {len(filtered)} candidates")
    
        if verbosity >= 5:
            print(f"{path_str:50} Filtered candidates:")
            for c in filtered:
                print(f"{path_str:50}     - {n(c)}")
    
        if not filtered:
            if verbosity >= 1:
                print(f"{path_str:50} [WARNING] No valid candidates, keeping original: {n(original)}")
                print(f"{path_str:50}           Filter: {repr(filter)}")
                
            return original
        
        selected = random.choice(filtered)
    
        if verbosity >= 2:
            print(f"{path_str:50} {n(original):20} -> {n(selected):20}")
    
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
        for obj in self._objects.values():
            obj.write()





class NameTableReader(Extractor):
    """Base class for reading name tables from text files."""
    filename = None  # Must be set by subclasses
    
    def __init__(self, context):
        super().__init__(context)
        with open(self.filename, "r", encoding="utf-8") as f:
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


class LoadPokemonNamesStep(NameTableReader):
    filename = "build/rawtext/237.txt"

        
class LoadMoveNamesStep(NameTableReader):
    filename = "build/rawtext/750.txt"

class LoadAbilityNames(NameTableReader):
    filename = "data/text/720.txt"

class Moves(NarcExtractor):
    def __init__(self, context):
        super().__init__(context)
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

        self.data = self.load_narc()

    def get_narc_path(self):
        return "a/0/1/1"
    
    def get_struct(self):
        return self.move_struct
    
    def parse_file(self, file_data, file_index):
        return self.move_struct.parse(file_data, narc_index=file_index)
    
    def serialize_file(self, data, index):
        return self.move_struct.build(data, narc_index=index)


class Learnsets(NarcExtractor):
    def __init__(self, context):
        super().__init__(context)
        moves = context.get(Moves).data

        self.struct = GreedyRange(Struct(
            "move_id" / Int16ul,
            "level" / Int16ul,
            Check(lambda ctx: ctx.move_id != 0xffff),
            "move" / Computed(lambda ctx: moves[ctx.move_id] if ctx.move_id < len(moves) else None),
        ))
        
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/3/3"
    
    def parse_file(self, file_data, index):
        return self.struct.parse(file_data, narc_index=index)
    
    def serialize_file(self, data, index):
        return self.struct.build(data, narc_index=index)


class EggMoves(NarcExtractor):
    """Extractor for Pokemon egg moves from ROM."""
    
    def __init__(self, context):
        super().__init__(context)
        moves = context.get(Moves).data
        
        # Egg moves are stored as a list of move IDs for each Pokemon
        # Format: species_id+20000 (marker), followed by move_ids, terminated by 0xFFFF
        self.struct = GreedyRange(Struct(
            "entry" / Int16ul,
            "is_species" / Computed(lambda ctx: ctx.entry >= 20000),
            "species_id" / Computed(lambda ctx: ctx.entry - 20000 if ctx.entry >= 20000 else None),
            "move_id" / Computed(lambda ctx: ctx.entry if ctx.entry < 20000 and ctx.entry != 0xFFFF else None),
            "is_terminator" / Computed(lambda ctx: ctx.entry == 0xFFFF),
            "move" / Computed(lambda ctx: moves[ctx.entry] if ctx.entry < len(moves) and ctx.entry < 20000 and ctx.entry != 0xFFFF else None),
            Check(lambda ctx: ctx.entry != 0xFFFF)  # Stop at terminator
        ))
        
        # Load raw data and parse into structured format
        raw_data = self.load_narc()
        self.data = self._parse_egg_moves(raw_data)
    
    def _parse_egg_moves(self, raw_data):
        """Parse raw egg move data into a dictionary by species."""
        egg_moves_by_species = {}
        
        # Process each file (should be just one file with all egg moves)
        for file_data in raw_data:
            current_species = None
            current_moves = []
            
            for entry in file_data:
                if entry.is_species:
                    # Save previous species data if exists
                    if current_species is not None:
                        egg_moves_by_species[current_species] = current_moves
                    
                    # Start new species
                    current_species = entry.species_id
                    current_moves = []
                
                elif entry.move_id is not None:
                    # Add move to current species
                    current_moves.append({
                        'move_id': entry.move_id,
                        'move': entry.move
                    })
            
            # Save last species
            if current_species is not None:
                egg_moves_by_species[current_species] = current_moves
        
        return egg_moves_by_species
    
    def get_narc_path(self):
        # Egg moves are stored at a/2/2/9 according to narcs.mk
        # EGGMOVES_TARGET := $(FILESYS)/a/2/2/9
        return "a/2/2/9"
    
    def parse_file(self, file_data, index):
        return self.struct.parse(file_data, narc_index=index)
    
    def serialize_file(self, data, index):
        return self.struct.build(data, narc_index=index)


class LoadTrainerNamesStep(Extractor):
    """Extractor that loads trainer names from assembly source."""
    
    def __init__(self, context):
        super().__init__(context)
        self.by_id = {}
        self.by_name = {}
        
        trainer_file = os.path.join("armips", "data", "trainers", "trainers.s")
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


class TrainerTeam(Writeback,NarcExtractor ):
    
    def __init__(self, context):
        mondata_extractor = context.get(Mons)
        move_extractor = context.get(Moves)

        # Base struct that all trainer Pokemon have
        self.struct_common = Struct(
            "ivs" / Int8ul,
            "abilityslot" / Int8ul,
            "level" / Int16ul,
            "species_id" / Int16ul,
        )
        
        super().__init__(context)
        self.data = self.load_narc()
    
    def _build_trainer_pokemon_struct(self, trainer_type_flags):
        
        # Convert bytes to int if needed
        if isinstance(trainer_type_flags, bytes):
            flags = int.from_bytes(trainer_type_flags, byteorder='little')
        else:
            flags = trainer_type_flags
        
        # Start with the common base structure
        struct_fields = []
        
        # Add conditional fields based on flags
        if flags & TrainerDataType.ITEMS:
            struct_fields.append("item" / Int16ul)
        
        if flags & TrainerDataType.MOVES:
            struct_fields.append("moves" / Array(4, Int16ul))
        
        if flags & TrainerDataType.ABILITY:
            struct_fields.append("ability" / Int16ul)
        
        if flags & TrainerDataType.BALL:
            struct_fields.append("ball" / Int16ul)
        
        if flags & TrainerDataType.IV_EV_SET:
            struct_fields.extend([
                "hp_iv" / Int8ul,
                "atk_iv" / Int8ul,
                "def_iv" / Int8ul,
                "speed_iv" / Int8ul,
                "spatk_iv" / Int8ul,
                "spdef_iv" / Int8ul,
                "hp_ev" / Int8ul,
                "atk_ev" / Int8ul,
                "def_ev" / Int8ul,
                "speed_ev" / Int8ul,
                "spatk_ev" / Int8ul,
                "spdef_ev" / Int8ul,
            ])
        
        if flags & TrainerDataType.NATURE_SET:
            struct_fields.append("nature" / Int8ul)
        
        if flags & TrainerDataType.SHINY_LOCK:
            struct_fields.append("shinylock" / Int8ul)
        
        if flags & TrainerDataType.ADDITIONAL_FLAGS:
            struct_fields.append("additionalflags" / Int32ul)
        
        # Always end with ballseal (present in all variants)
        struct_fields.append("ballseal" / Int16ul)
        
        # Build the complete struct
        return self.struct_common + Struct(*struct_fields)
    
    def get_narc_path(self):
        return "a/0/5/6"
    
    def parse_file(self, file_data, index):
        if len(file_data) == 0:
            return []
        
        trainer = self.context.get(TrainerData).data[index]
        struct = self._build_trainer_pokemon_struct(trainer.trainermontype.data)
        
        return Array(trainer.nummons, struct).parse(file_data)
    
    def serialize_file(self, data, index):
        if not data:
            return b''
        
        trainer = self.context.get(TrainerData).data[index]
        struct = self._build_trainer_pokemon_struct(trainer.trainermontype.data)
        
        return Array(trainer.nummons, struct).build(data)


class TrainerData(Writeback, NarcExtractor):
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
        return "a/0/5/5"
    
    def parse_file(self, file_data, index):
        return self.trainer_data_struct.parse(file_data, narc_index=index)
    
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

class Trainers(Extractor):
    def __init__(self, context):
        super().__init__(context)
        
        trainer_data_extractor = context.get(TrainerData)
        trainer_team_extractor = context.get(TrainerTeam)
        
        self.data = [
            TrainerInfo(trainer_data_extractor.data[i], trainer_team_extractor.data[i])
            for i in range(len(trainer_data_extractor.data))
        ]


class UpdateTrainerTeamDataStep(Step):
    """Updates trainer Pokémon team data to include required fields for MOVES and ITEMS format.
    
    When trainers are changed to use MOVES and ITEMS format, their team data
    must include the required fields (item, moves) to prevent serialization errors.
    This step adds default values for missing fields.
    """
    
    def run(self, context):
        """Update trainer team data to match trainer types."""
        trainers = context.get(Trainers)
        updated_count = 0
        
        for trainer in trainers.data:
            # Check if trainer uses MOVES and ITEMS format
            trainer_type = trainer.info.trainermontype.data
            uses_moves_items = (trainer_type == bytes([TrainerDataType.MOVES | TrainerDataType.ITEMS]))
            
            if uses_moves_items and trainer.team:
                # Update each Pokémon in the team to include required fields
                for pokemon in trainer.team:
                    updated = False
                    
                    # Add default item if missing
                    if not hasattr(pokemon, 'item'):
                        pokemon.item = 0  # No item (0 = no item in the game)
                        updated = True
                    
                    # Add default moves if missing
                    if not hasattr(pokemon, 'moves'):
                        pokemon.moves = [0, 0, 0, 0]  # No moves (will be set by move selection)
                        updated = True
                    
                    if updated:
                        updated_count += 1
        
        return updated_count


class TrainerMult(Step):
    """Apply a multiplier to trainer Pokémon levels with special logic for bosses and aces."""
    
    def __init__(self, multiplier=1.0):
        self.multiplier = multiplier
    
    def _round_half_up(self, value):
        """Round to nearest integer, with .5 always rounding up."""
        import math
        return int(math.floor(value + 0.5))
    
    def run(self, context):
        trainers = context.get(Trainers)
        bosses = context.get(IdentifyBosses)
        
        # Create a set of boss trainer IDs for quick lookup
        boss_trainer_ids = set()
        for boss_category in bosses.data.values():
            for trainer in boss_category.trainers:
                boss_trainer_ids.add(trainer.info.trainer_id)
        
        for trainer in trainers.data:
            if trainer.info.trainer_id in boss_trainer_ids:
                self._apply_boss_multiplier(trainer)
            else:
                self._apply_regular_multiplier(trainer)
    
    def _apply_boss_multiplier(self, trainer):
        """Apply special boss multiplier logic with ace-based level scaling."""
        if not trainer.team:
            return
        
        if trainer.ace_index is not None:
            # Boss has an ace - apply special scaling
            # First, multiply the ace's level
            ace_pokemon = trainer.team[trainer.ace_index]
            new_ace_level = max(1, self._round_half_up(ace_pokemon.level * self.multiplier))
            new_ace_level = min(100, new_ace_level)  # Cap at 100
            ace_pokemon.level = new_ace_level
            
            # Special case: if ace is level 100, set all other Pokémon to level 100
            if new_ace_level == 100:
                for i, pokemon in enumerate(trainer.team):
                    if i != trainer.ace_index:
                        pokemon.level = 100
            else:
                # Normal case: set other Pokémon levels based on ace level
                for i, pokemon in enumerate(trainer.team):
                    if i == trainer.ace_index:
                        continue  # Skip the ace, already handled
                    
                    # Determine level based on slot position
                    if i in [1, 2]:  # Slots 2 & 3 (0-indexed: 1, 2)
                        target_level = max(1, new_ace_level - 1)
                    else:  # Slots 4-6 (0-indexed: 3, 4, 5)
                        target_level = max(1, new_ace_level - 2)
                    
                    pokemon.level = min(100, target_level)  # Cap at 100
        else:
            # Boss has no ace (tied levels) - multiply all Pokémon by multiplier
            self._apply_regular_multiplier(trainer)
    
    def _apply_regular_multiplier(self, trainer):
        """Apply regular multiplier to all Pokémon in the team."""
        if not trainer.team:
            return
        
        for pokemon in trainer.team:
            new_level = max(1, self._round_half_up(pokemon.level * self.multiplier))
            pokemon.level = min(100, new_level)  # Cap at 100


class PokemonListBase(Extractor):
    """Base class for categorized Pokémon lists."""
    
    # This should be overridden by subclasses
    pokemon_names = []
    
    def __init__(self, context):
        super().__init__(context)
        pokemon_names_step = context.get(LoadPokemonNamesStep)
        tm_hm_names = context.get(TMHM)
        self.by_id = set()
        
        # Add all Pokémon in the list
        for name in self.pokemon_names:
            self.by_id.add(pokemon_names_step.get_by_name(name))


class InvalidPokemon(PokemonListBase):
    """Handles invalid Pokémon entries (marked with dashes)."""
    
    def __init__(self, context):
        super().__init__(context)
        pokemon_names_step = context.get(LoadPokemonNamesStep)
        
        # Add any dashes (invalid Pokémon)
        for fid in pokemon_names_step.get_all_by_name("-----"):
            self.by_id.add(fid)
            

class RestrictedPokemon(PokemonListBase):
    """Restricted legendary Pokémon, aka Cover Legendaries."""
    
    pokemon_names = [
        "Mewtwo",
        "Lugia",
        "Ho-oh", 
        "Kyogre",
        "Groudon",
        "Rayquaza",
        "Dialga",
        "Palkia",
        "Giratina",
        "Reshiram",
        "Zekrom",
        "Kyurem",
        "Cosmog",
        "Cosmoem",
        "Solgaleo",
        "Lunala",
        "Necrozma",
        "Zacian",
        "Zamazenta",
        "Eternatus",
        "Calyrex",
        "Koraidon",
        "Miraidon",
        "Terapagos",
        "Xerneas",
        "Yveltal",
        "Zygarde",
        "Arceus"
    ]


class SubLegendaryPokemon(PokemonListBase):
    """Sub-legendary Pokémon, aka non-cover, non-ultra beast, non-mythical, non-paradox legendaries."""
    
    pokemon_names = [
        "Articuno",
        "Zapdos",
        "Moltres",
        "Raikou",
        "Entei",
        "Suicune",
        "Regirock",
        "Regice",
        "Registeel",
        "Regigigas",
        "Latios",
        "Latias",
        "Uxie",
        "Mesprit",
        "Azelf",
        "Heatran",
        "Cresselia",
        "Cobalion",
        "Terrakion",
        "Virizion",
        "Tornadus",
        "Thundurus",
        "Landorus",
        "Type: Null",
        "Silvally",
        "Tapu Koko",
        "Tapu Lele",
        "Tapu Bulu",
        "Tapu Fini",
        "Urshifu",
        "Kubfu",
        "Regieleki",
        "Regidrago",
        "Glastrier",
        "Spectrier",
        "Enamorus",
        "Wo-Chien",
        "Chien-Pao",
        "Ting-Lu",
        "Chi-Yu",
        "Okidogi",
        "Munkidori",
        "Fezanditi",
        "Ogerpon",

    ]


class MythicalPokemon(PokemonListBase):
    """Mythical Pokémon ft Dark Void"""
    
    pokemon_names = [
        "Mew",
        "Celebi",
        "Jirachi",
        "Deoxys",
        "Phione",
        "Manaphy",
        "Darkrai",
        "Shaymin",
        "Victini",
        "Genesect",
        "Keldeo",
        "Meloetta",
        "Diancie",
        "Hoopa",
        "Volcanion",
        "Magearna",
        "Marshadow",
        "Meltan",
        "Melmetal",
        "Zarude",
        "Pecharunt",
        "Zeraora"
    ]


class UltraBeastPokemon(PokemonListBase):
    """Ultra Beasts aka more than half of my Hear-me-out cake."""
    
    pokemon_names = [
        "Nihilego",
        "Buzzwole",
        "Pheromosa",
        "Xurkitree",
        "Celesteela",
        "Kartana",
        "Guzzlord",
        "Poipole",
        "Naganadel",
        "Stakataka",
        "Blacefalon"
    ]


class ParadoxPokemon(PokemonListBase):
    """Paradox Pokémon"""
    
    pokemon_names = [
        "Great Tusk",
        "ScreamTail",
        "BruteBonet",
        "FluttrMane",
        "SlithrWing",
        "SandyShock",
        "IronTreads",
        "IronBundle",
        "Iron Hands",
        "Iron Neck",
        "Iron Moth",
        "IronThorns",
        "RoarinMoon",
        "Iron Valor",
        "WalkngWake",
        "IronLeaves",
        "GouginFire",
        "RagingBolt",
        "IronBolder",
        "Iron Crown"
    ]


class LoadBlacklistStep(PokemonListBase):
    """Extractor that creates Pokémon blacklist with hardcoded data."""
    
    pokemon_names = [
        "Bad Egg",
        "Mewtwo"
    ]


class Mons(NarcExtractor):
    """Extractor for Pokemon data from ROM with full mondata structure."""
    
    # BST overrides for Pokemon whose power level is not accurately represented by raw BST
    BST_OVERRIDES = {
        "Wishiwashi": 550, 
        "Shedinja": 400,    
        "Slaking": 550,     
        "Regigigas": 580,   
        "Archeops": 550,    
    }
    
    def __init__(self, context):
        pokemon_names_step = context.get(LoadPokemonNamesStep)
        tm_hm_names = context.get(TMHM)
        
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
            Padding(2),  # Pad to offset 0x1C for TM bitmap
            "tm_bitmap" / BitsSwapped(Bitwise(Array(128, Flag))),
            "tm" / Computed(lambda ctx: [None] + ctx.tm_bitmap[:92]),  # tm[1] = TM001, tm[92] = TM092
            "hm" / Computed(lambda ctx: [None] + ctx.tm_bitmap[92:100]),  # hm[1] = HM001, hm[8] = HM008
            "bst" / Computed(lambda ctx: self._get_adjusted_bst(ctx)),
            "name" / Computed(lambda ctx: pokemon_names_step.get_by_id(ctx._.narc_index)),
            "pokemon_id" / Computed(lambda ctx: ctx._.narc_index)
        )
        
        super().__init__(context)
        
        self.data = self.load_narc()
    
    def _get_adjusted_bst(self, ctx):
        """Get adjusted BST for Pokemon, applying overrides for special cases."""
        # Get the Pokemon name
        pokemon_names_step = self.context.get(LoadPokemonNamesStep)
        pokemon_name = pokemon_names_step.get_by_id(ctx._.narc_index)
        
        # Check if this Pokemon has a BST override
        if pokemon_name in self.BST_OVERRIDES:
            return self.BST_OVERRIDES[pokemon_name]
        
        # Default: return raw BST calculation
        return ctx.hp + ctx.attack + ctx.defense + ctx.speed + ctx.sp_attack + ctx.sp_defense
    

    
    def get_narc_path(self):
        return "a/0/0/2"
    
    def parse_file(self, file_data, index):
        return self.mondata_struct.parse(file_data, narc_index=index)
    
    def serialize_file(self, data, index):
        return self.mondata_struct.build(data, narc_index=index)

class TMHM(Extractor):
    def __init__(self, context):
        super().__init__(context)
        moves = context.get(Moves)
        
        num_tms = 92
        num_hms = 8
        base_addr = 0x1000CC
        
        tm_hm_bytes = self.rom.arm9[base_addr:base_addr + (num_tms + num_hms) * 2]
        tm_hm_struct = Struct("move_ids" / Array(num_tms + num_hms, Int16ul))
        move_ids = tm_hm_struct.parse(tm_hm_bytes).move_ids
        
        self.tm = [None] + [moves.data[move_ids[i]] for i in range(num_tms)]
        self.hm = [None] + [moves.data[move_ids[i + num_tms]] for i in range(num_hms)]


class StarterExtractor(Extractor):
    """Extractor for starter Pokemon data from ARM9 binary.
    
    Reads/writes the three starter species stored at address 0x02108514 in ARM9.
    """
    
    def __init__(self, context):
        super().__init__(context)
        mons = context.get(Mons)
        
        # ARM9 is loaded at 0x02000000, starters are at 0x02108514
        self.starter_offset = 0x108514
        
        # Define the structure for just the starter data (3 × 4-byte integers)
        self.starter_struct = Struct(
            "starter_id" / Array(3, Int32ul),
            "starters" / Computed(lambda ctx: [mons.data[s] for s in ctx.starter_id])
        )
        
        # Read starter data from the specific offset in ARM9
        starter_bytes = self.rom.arm9[self.starter_offset:self.starter_offset + 12]
        self.data = self.starter_struct.parse(starter_bytes)
    
    def write(self):
        """Write starter data back to ARM9 binary."""
        # Build just the starter data
        starter_bytes = self.starter_struct.build(self.data)
        
        # Replace the 12 bytes at the starter offset in ARM9
        arm9_data = bytearray(self.rom.arm9)
        arm9_data[self.starter_offset:self.starter_offset + 12] = starter_bytes
        self.rom.arm9 = bytes(arm9_data)


class EvolutionData(NarcExtractor):
    
    def __init__(self, context):
        mons = context.get(Mons)
        
        EvolutionEntry = Struct(
            "method" / Int16ul,
            "parameter" / Int16ul, 
            "target_species" / Int16ul,
            "target" / Computed(lambda ctx: mons.data[ctx.target_species] if ctx.target_species > 0 and ctx.target_species < len(mons.data) else None)
        )
        
        self.evolution_struct = Struct(
            "evolutions" / Array(9, EvolutionEntry),
            "species_id" / Computed(lambda ctx: ctx._.narc_index),
            "species" / Computed(lambda ctx: mons.data[ctx._.narc_index] if ctx._.narc_index < len(mons.data) else None),
            "valid_evolutions" / Computed(lambda ctx: [evo for evo in ctx.evolutions if evo.method != 0])
        )
        
        super().__init__(context)
        self.data = self.load_narc()
    
    def get_evolution_paths(self, species_id):
        def walk_evolution_tree(current_species_id, current_path):
            current_pokemon = self.data[current_species_id]
            current_path = current_path + [current_pokemon.species]
            
            if not current_pokemon.valid_evolutions:
                return [current_path]
            
            all_paths = []
            for evolution in current_pokemon.valid_evolutions:
                if evolution.target and evolution.target.pokemon_id not in [p.pokemon_id for p in current_path]:
                    paths = walk_evolution_tree(evolution.target.pokemon_id, current_path)
                    all_paths.extend(paths)
            
            if not all_paths:
                return [current_path]
            
            return all_paths
        
        return walk_evolution_tree(species_id, [])
    
    def get_narc_path(self):
        return "a/0/3/4"
    
    def parse_file(self, file_data, index):
        return self.evolution_struct.parse(file_data, narc_index=index)
    
    def serialize_file(self, data, index):
        return self.evolution_struct.build(data, narc_index=index)


class EvioliteUser(Extractor):
    """Identifies Pokemon that are better with Eviolite than evolved.
    
    An Eviolite User is a Pokemon that:
    1. Can evolve once (including second stage of 3-stage lines)
    2. Has an Eviolite BST (with def/spdef multiplied by 1.5) > 500
    
    For beginners:
    - Eviolite is an item that boosts Defense and Special Defense by 50% for Pokemon that can still evolve
    - Some Pokemon are actually stronger with Eviolite than their evolved forms
    - BST = Base Stat Total (sum of all 6 base stats)
    """
    
    def __init__(self, context):
        super().__init__(context)
        self.pokemon_names_step = context.get(LoadPokemonNamesStep)
        self.mons = context.get(Mons)
        self.evolution_data = context.get(EvolutionData)
        
        # Find all Pokemon that can evolve once
        self.candidates = self._find_evolution_candidates()
        
        # Calculate Eviolite stats and identify users
        self.eviolite_users = self._identify_eviolite_users()
        
        # Create lookup sets for easy checking
        self.by_id = {pokemon.pokemon_id for pokemon in self.eviolite_users}
        self.by_name = {pokemon.name.lower(): pokemon for pokemon in self.eviolite_users}
    
    def _find_evolution_candidates(self):
        """Find all Pokemon that can evolve exactly once.
        
        This includes:
        - Base forms of 2-stage evolution lines (e.g., Charmander)
        - Middle forms of 3-stage evolution lines (e.g., Charmeleon)
        """
        candidates = []
        
        for pokemon_data in self.evolution_data.data:
            # Skip if no evolutions
            if not pokemon_data.valid_evolutions:
                continue
            
            # Get the Pokemon species
            pokemon = pokemon_data.species
            if not pokemon:
                continue
            
            # Check if this Pokemon can evolve exactly once
            # (has evolutions but none of its evolutions can evolve further)
            can_evolve_once = False
            
            for evolution in pokemon_data.valid_evolutions:
                if evolution.target:
                    # Check if the evolution target can also evolve
                    target_data = self.evolution_data.data[evolution.target.pokemon_id]
                    
                    # If target has no further evolutions, this is a candidate
                    if not target_data.valid_evolutions:
                        can_evolve_once = True
                        break
                    
                    # If target has evolutions, this is a middle stage (also a candidate)
                    # Example: Charmeleon can evolve to Charizard (which can't evolve further)
                    if target_data.valid_evolutions:
                        can_evolve_once = True
                        break
            
            if can_evolve_once:
                candidates.append(pokemon)
        
        return candidates
    
    def _calculate_eviolite_stats(self, pokemon):
        """Calculate a Pokemon's stats with Eviolite boost.
        
        Eviolite multiplies Defense and Special Defense by 1.5.
        
        Returns:
            dict: Individual stats with Eviolite adjustments
            int: Eviolite BST (sum of adjusted stats)
        """
        # Get base stats
        hp = pokemon.hp
        attack = pokemon.attack
        defense = pokemon.defense
        sp_attack = pokemon.sp_attack
        sp_defense = pokemon.sp_defense
        speed = pokemon.speed
        
        # Apply Eviolite boost to Defense and Special Defense
        eviolite_defense = int(defense * 1.5)
        eviolite_sp_defense = int(sp_defense * 1.5)
        
        # Calculate adjusted stats
        eviolite_stats = {
            'hp': hp,
            'attack': attack,
            'defense': eviolite_defense,
            'sp_attack': sp_attack,
            'sp_defense': eviolite_sp_defense,
            'speed': speed
        }
        
        # Calculate Eviolite BST
        eviolite_bst = sum(eviolite_stats.values())
        
        return eviolite_stats, eviolite_bst
    
    def _identify_eviolite_users(self):
        """Identify Pokemon with Eviolite BST > 500."""
        eviolite_users = []
        
        for pokemon in self.candidates:
            eviolite_stats, eviolite_bst = self._calculate_eviolite_stats(pokemon)
            
            # Store analysis data on the Pokemon object for printing
            pokemon._eviolite_analysis = {
                'original_bst': pokemon.bst,
                'eviolite_stats': eviolite_stats,
                'eviolite_bst': eviolite_bst
            }
            
            # Check if Eviolite BST > 500
            if eviolite_bst > 500:
                eviolite_users.append(pokemon)
        
        return eviolite_users
    



class RandomizeStartersStep(Step):
    
    def __init__(self, filter=NoFilter()):
        self.filter = filter
    
    def run(self, context):
        starter_extractor = context.get(StarterExtractor)
        evolution_data = context.get(EvolutionData)
        
        # Ultra slick list comprehension for 3-stage evolution candidates
        candidates = [pokemon_data.species for pokemon_data in evolution_data.data 
                     if pokemon_data.species and any(len(path) == 3 for path in evolution_data.get_evolution_paths(pokemon_data.species_id))]
        
        # Randomize each starter
        for i in range(3):
            original_starter = starter_extractor.data.starters[i]
            new_starter = context.decide(
                path=["starters", f"starter_{i}"],
                original=original_starter,
                candidates=candidates,
                filter=self.filter
            )
            starter_extractor.data.starter_id[i] = new_starter.pokemon_id
            


class LoadEncounterNamesStep(Extractor):
    """Extractor that loads encounter location names from assembly source."""
    
    def __init__(self, context):
        super().__init__(context)
        self.location_names = {}
        encounter_file = os.path.join("armips", "data", "encounters.s")
        with open(encounter_file, "r", encoding="utf-8") as f:
            for line in f:
                match = re.search(r"encounterdata\s+(\d+).*//\s+(.*)", line)
                if match:
                    encounter_id = int(match.group(1))
                    encounter_name = match.group(2).strip()
                    self.location_names[encounter_id] = encounter_name



class Encounters(Writeback,NarcExtractor):
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


class WildMult(Step):
    """Apply a multiplier to wild Pokémon levels in encounters."""
    
    def __init__(self, multiplier=1.0):
        self.multiplier = multiplier
    
    def _round_half_up(self, value):
        """Round to nearest integer, with .5 always rounding up."""
        import math
        return int(math.floor(value + 0.5))
    
    def run(self, context):
        encounters = context.get(Encounters)
        
        for encounter in encounters.data:
            # Apply multiplier to walklevels (grass encounters)
            if hasattr(encounter, 'walklevels'):
                for i in range(len(encounter.walklevels)):
                    # Apply multiplier and round to nearest integer (0.5 rounds up)
                    new_level = max(1, self._round_half_up(encounter.walklevels[i] * self.multiplier))
                    # Cap level at 100 (typical Pokémon level cap)
                    encounter.walklevels[i] = min(100, new_level)
            
            # Apply multiplier to encounter slots that have minlevel and maxlevel
            encounter_types = ['surf', 'rocksmash', 'oldrod', 'goodrod', 'superrod']
            
            for encounter_type in encounter_types:
                if hasattr(encounter, encounter_type):
                    slots = getattr(encounter, encounter_type)
                    for slot in slots:
                        if hasattr(slot, 'minlevel') and hasattr(slot, 'maxlevel'):
                            # Apply multiplier and round to nearest integer (0.5 rounds up)
                            slot.minlevel = max(1, self._round_half_up(slot.minlevel * self.multiplier))
                            slot.maxlevel = max(1, self._round_half_up(slot.maxlevel * self.multiplier))
                            
                            # Ensure maxlevel is at least as high as minlevel
                            if slot.maxlevel < slot.minlevel:
                                slot.maxlevel = slot.minlevel
                            
                            # Cap levels at 100 (typical Pokémon level cap)
                            slot.minlevel = min(100, slot.minlevel)
                            slot.maxlevel = min(100, slot.maxlevel)


class RandomizeEncountersStep(Step):
    
    def __init__(self, filter, independent_by_area=False):
        self.filter = filter
        self.independent_by_area = independent_by_area
        self.replacements = {}
    
    def run(self, context):
        self.mondata = context.get(Mons)
        self.encounters = context.get(Encounters)
        self.blacklist = context.get(LoadBlacklistStep)
        self.context = context
        
        for i, encounter in enumerate(self.encounters.data):
            self._randomize_encounter(encounter, i)
    
    def _randomize_encounter(self, encounter, location_id):
        self._randomize_slot_list(encounter.morning, location_id)
        self._randomize_slot_list(encounter.day, location_id)
        self._randomize_slot_list(encounter.night, location_id)
    
    def _randomize_slot_list(self, slot_list, location_id):
        for i, species_id in enumerate(slot_list):
            if species_id == 0:
                continue
            
            # Create replacement key based on whether we want area independence
            if self.independent_by_area:
                replacement_key = (species_id, location_id)
            else:
                replacement_key = species_id
            
            if replacement_key not in self.replacements:
                mon = self.mondata.data[species_id]
                
                # Use location-specific path for area-independent replacements
                if self.independent_by_area:
                    path = ["encounters", f"area_{location_id}", mon.name]
                else:
                    path = ["encounters", mon.name]
                
                new_species = self.context.decide(
                    path=path,
                    original=mon,
                    candidates=list(self.mondata.data),
                    filter=self.filter
                )
                
                self.replacements[replacement_key] = new_species.pokemon_id
            
            slot_list[i] = self.replacements[replacement_key]


class IndexTrainers(Extractor):
    "Store mapping of name to trainer_id.  Queryable using `find`, by name or (trainerclass, name)"
    def __init__(self, context):
        super().__init__(context)
        self.data = {}

        trainers = context.get(Trainers)
        for t in trainers.data:
            if t.info.name not in self.data:
                self.data[t.info.name] = []
            self.data[t.info.name].append((t.info.trainerclass, t.info.trainer_id))

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
    """Expand trainer teams with tier-based sizing options.
    
    Supports both scaling (tier-based) and fixed team size modes for regular trainers and bosses.
    ScalingTrainerTeamSize is the default mode, providing progressive team sizes based on game tiers.
    """
    
    def __init__(self, 
                 # Tier-based team sizing options
                 mode="ScalingTrainerTeamSize",  # "ScalingTrainerTeamSize" or "FixedTrainerTeamSize"
                 boss_mode="ScalingBossTeamSize",  # "ScalingBossTeamSize" or "FixedBossTeamSize"
                 bosses_only=False,  # Only expand boss teams if True
                 # Scaling mode parameters - tier-based minimum team sizes
                 tier1_trainer_team_size=2,
                 tier2_trainer_team_size=3, 
                 tier3_trainer_team_size=4,
                 tier4_trainer_team_size=5,
                 tier1_boss_team_size=4,
                 tier2_boss_team_size=6,
                 tier3_boss_team_size=6,
                 tier4_boss_team_size=6,
                 # Fixed mode parameters - global minimum team sizes
                 fixed_trainer_team_size=3,
                 fixed_boss_team_size=6):
        
        # Validate parameters
        if mode not in ["ScalingTrainerTeamSize", "FixedTrainerTeamSize"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'ScalingTrainerTeamSize' or 'FixedTrainerTeamSize'")
        if boss_mode not in ["ScalingBossTeamSize", "FixedBossTeamSize"]:
            raise ValueError(f"Invalid boss_mode: {boss_mode}. Must be 'ScalingBossTeamSize' or 'FixedBossTeamSize'")
        
        # Core parameters
        self.bosses_only = bosses_only
        
        # New tier-based parameters
        self.mode = mode
        self.boss_mode = boss_mode
        
        # Scaling mode - tier-based minimum team sizes
        self.tier_trainer_sizes = {
            Tier.EARLY_GAME: tier1_trainer_team_size,
            Tier.MID_GAME: tier2_trainer_team_size,
            Tier.LATE_GAME: tier3_trainer_team_size,
            Tier.END_GAME: tier4_trainer_team_size
        }
        
        self.tier_boss_sizes = {
            Tier.EARLY_GAME: tier1_boss_team_size,
            Tier.MID_GAME: tier2_boss_team_size,
            Tier.LATE_GAME: tier3_boss_team_size,
            Tier.END_GAME: tier4_boss_team_size
        }
        
        # Fixed mode - global minimum team sizes
        self.fixed_trainer_team_size = fixed_trainer_team_size
        self.fixed_boss_team_size = fixed_boss_team_size
    
    def run(self, context):
        # Get required extractors
        trainers = context.get(Trainers)
        bosses = context.get(IdentifyBosses)
        identify_tier = context.get(IdentifyTier)
        
        # Create a set of boss trainer IDs for quick lookup
        boss_trainer_ids = set()
        for boss_category in bosses.data.values():
            for trainer in boss_category.trainers:
                boss_trainer_ids.add(trainer.info.trainer_id)
        
        print(f"Expanding trainer teams with {self.mode} (regular) and {self.boss_mode} (bosses)...")
        
        # Process all trainers with tier-based team sizing
        for trainer in trainers.data:
            is_boss = trainer.info.trainer_id in boss_trainer_ids
            
            # Skip if bosses_only is True and this isn't a boss
            if self.bosses_only and not is_boss:
                continue
            
            # Get trainer tier
            trainer_tier = identify_tier.get_tier_for_trainer(trainer.info.trainer_id)
            
            # Determine target team size based on mode and tier
            if is_boss:
                target_size = self._get_boss_target_size(trainer_tier)
            else:
                target_size = self._get_trainer_target_size(trainer_tier)
            
            # Expand team to target size (only if current size is smaller)
            self._expand_trainer_team(context, trainer, target_size)
    
    def _get_trainer_target_size(self, trainer_tier):
        """Get target team size for regular trainers based on mode and tier."""
        if self.mode == "ScalingTrainerTeamSize":
            return self.tier_trainer_sizes[trainer_tier]
        else:  # FixedTrainerTeamSize
            return self.fixed_trainer_team_size
    
    def _get_boss_target_size(self, trainer_tier):
        """Get target team size for boss trainers based on mode and tier."""
        if self.boss_mode == "ScalingBossTeamSize":
            return self.tier_boss_sizes[trainer_tier]
        else:  # FixedBossTeamSize
            return self.fixed_boss_team_size
    
    def _expand_trainer_team(self, context, trainer, target_size):
        """Expand trainer team to target size (only if current size is smaller)."""
        if trainer.info.nummons != len(trainer.team):
            raise RuntimeError(f"team size mismatch! {trainer.info.trainer_id}")

        current_size = len(trainer.team)
        
        # Only expand if current size is smaller than target (never shrink teams)
        if current_size >= target_size or current_size == 0:
            return
        
        # Calculate average BST of existing team
        mondata = context.get(Mons)
        total_bst = 0
        for pokemon in trainer.team:
            species = mondata.data[pokemon.species_id]
            total_bst += species.bst
        
        average_bst = total_bst / current_size
        
        # Find a Pokemon with BST closest to the average
        best_pokemon = None
        best_bst_diff = float('inf')
        
        for species in mondata.data:
            bst_diff = abs(species.bst - average_bst)
            if bst_diff < best_bst_diff:
                best_bst_diff = bst_diff
                best_pokemon = species
        
        if best_pokemon is None:
            # Fallback to duplicating first Pokemon if no suitable match found
            template_pokemon = trainer.team[0]
        else:
            # Create a template Pokemon based on the first Pokemon but with the new species
            template_pokemon = Container(trainer.team[0])
            template_pokemon.species_id = best_pokemon.pokemon_id
        
        # Fill remaining slots with the selected Pokemon
        for _ in range(target_size - current_size):
            trainer.team.append(Container(template_pokemon))
        
        trainer.info.nummons = len(trainer.team)


class ChangeTrainerDataTypeStep(Step):
    """Step to change trainers' data type to support various TrainerDataType flags."""
    
    def __init__(self, target_flags=None, trainer_filter=None):
        """
        Initialize the step with configurable trainer data type flags.
        
        Args:
            target_flags: TrainerDataType flags to set (default: MOVES | ITEMS)
            trainer_filter: Optional function to filter which trainers to modify
        """
        self.target_flags = target_flags if target_flags is not None else (TrainerDataType.MOVES | TrainerDataType.ITEMS)
        self.trainer_filter = trainer_filter
    
    def run(self, context):
        trainer_data = context.get(TrainerData)
        trainers = context.get(Trainers)
        
        modified_count = 0
        
        # Change trainers to the specified data type and update their team data
        for i, trainer in enumerate(trainer_data.data):
            # Apply filter if provided
            if self.trainer_filter and not self.trainer_filter(trainer, i):
                continue
                
            # Update trainer data type
            trainer.trainermontype.value = self.target_flags
            trainer.trainermontype.data = bytes([self.target_flags])
            
            # Update team data to include required fields based on flags
            if i < len(trainers.data):
                for pokemon in trainers.data[i].team:
                    self._update_pokemon_data(pokemon, self.target_flags)
            
            modified_count += 1
        
        print(f"Modified {modified_count} trainers to use flags: {self._flags_to_string(self.target_flags)}")
    
    def _update_pokemon_data(self, pokemon, flags):
        """Update Pokemon data structure to match the specified flags."""
        
        # Add item field if ITEMS flag is set
        if flags & TrainerDataType.ITEMS:
            if not hasattr(pokemon, 'item'):
                pokemon.item = 0  # Default to no item
        
        # Add moves array if MOVES flag is set
        if flags & TrainerDataType.MOVES:
            if not hasattr(pokemon, 'moves'):
                pokemon.moves = [0, 0, 0, 0]  # Default to no moves (will be set later)
        
        # Add ability field if ABILITY flag is set
        if flags & TrainerDataType.ABILITY:
            if not hasattr(pokemon, 'ability'):
                pokemon.ability = 0  # Default to first ability
        
        # Add ball field if BALL flag is set
        if flags & TrainerDataType.BALL:
            if not hasattr(pokemon, 'ball'):
                pokemon.ball = 4  # Default to Poke Ball
        
        # Add IV/EV fields if IV_EV_SET flag is set
        if flags & TrainerDataType.IV_EV_SET:
            iv_fields = ['hp_iv', 'atk_iv', 'def_iv', 'speed_iv', 'spatk_iv', 'spdef_iv']
            ev_fields = ['hp_ev', 'atk_ev', 'def_ev', 'speed_ev', 'spatk_ev', 'spdef_ev']
            
            for field in iv_fields:
                if not hasattr(pokemon, field):
                    setattr(pokemon, field, 31)  # Default to max IVs
            
            for field in ev_fields:
                if not hasattr(pokemon, field):
                    setattr(pokemon, field, 0)  # Default to no EVs
        
        # Add nature field if NATURE_SET flag is set
        if flags & TrainerDataType.NATURE_SET:
            if not hasattr(pokemon, 'nature'):
                pokemon.nature = 0  # Default to Hardy (neutral nature)
        
        # Add shinylock field if SHINY_LOCK flag is set
        if flags & TrainerDataType.SHINY_LOCK:
            if not hasattr(pokemon, 'shinylock'):
                pokemon.shinylock = 0  # Default to no shiny lock
        
        # Add additionalflags field if ADDITIONAL_FLAGS flag is set
        if flags & TrainerDataType.ADDITIONAL_FLAGS:
            if not hasattr(pokemon, 'additionalflags'):
                pokemon.additionalflags = 0  # Default to no additional flags
    
    def _flags_to_string(self, flags):
        """Convert TrainerDataType flags to a readable string."""
        flag_names = []
        
        if flags & TrainerDataType.MOVES:
            flag_names.append('MOVES')
        if flags & TrainerDataType.ITEMS:
            flag_names.append('ITEMS')
        if flags & TrainerDataType.ABILITY:
            flag_names.append('ABILITY')
        if flags & TrainerDataType.BALL:
            flag_names.append('BALL')
        if flags & TrainerDataType.IV_EV_SET:
            flag_names.append('IV_EV_SET')
        if flags & TrainerDataType.NATURE_SET:
            flag_names.append('NATURE_SET')
        if flags & TrainerDataType.SHINY_LOCK:
            flag_names.append('SHINY_LOCK')
        if flags & TrainerDataType.ADDITIONAL_FLAGS:
            flag_names.append('ADDITIONAL_FLAGS')
        
        if not flag_names:
            return 'NOTHING'
        
        return ' | '.join(flag_names)


class GeneralEVStep(Step):
    """Pipeline step to apply GeneralEV allocation to trainer Pokemon.
    
    This step uses the GeneralEV algorithm to allocate EVs based on Pokemon base stats.
    It requires the IV_EV_SET flag to be enabled in the trainer data type.
    Supports tier-based EV budgets for progressive difficulty scaling.
    """
    
    def __init__(self, ev_budget=510, tier_budgets=None, trainer_filter=None):
        """Initialize the GeneralEV step.
        
        Args:
            ev_budget (int): Default EV budget per Pokemon (default 510, max 510)
            tier_budgets (dict): Optional tier-specific EV budgets {tier_name: budget}
                                Default: Tier.EARLY_GAME=252, Tier.MID_GAME=510, Tier.LATE_GAME=510, Tier.END_GAME=510
            trainer_filter: Optional function to filter which trainers to modify
        """
        self.default_ev_budget = min(ev_budget, 510)  # Clamp to maximum
        
        self.tier_budgets = tier_budgets or {
            Tier.EARLY_GAME: 252,
            Tier.MID_GAME: 510,
            Tier.LATE_GAME: 510,
            Tier.END_GAME: 510
        }
        
        self.trainer_filter = trainer_filter
        self.total_pokemon_processed = 0
        self.total_pokemon_allocated = 0
        self.allocation_log = []
        self.tier_stats = {}  # Track allocations per tier
    
    def run(self, context):
        """Run the GeneralEV allocation step."""
        trainer_data = context.get(TrainerData)
        trainers = context.get(Trainers)
        mons = context.get(Mons)
        
        # Get tier information for progressive EV budgets
        try:
            identify_tier = context.get(IdentifyTier)
        except:
            identify_tier = None
            print("Warning: IdentifyTier not available, using default EV budget for all trainers")
        
        # Ensure we have the required extractors
        try:
            pokemon_names = context.get(LoadPokemonNamesStep)
        except:
            pokemon_names = None
        
        print(f"Applying GeneralEV allocation with tier-based EV budgets...")
        if identify_tier:
            print(f"Tier budgets: {self.tier_budgets}")
        else:
            print(f"Default budget: {self.default_ev_budget}")
        
        for i, trainer in enumerate(trainer_data.data):
            # Apply filter if provided
            if self.trainer_filter and not self.trainer_filter(trainer, i):
                continue
            
            # Check if trainer has IV_EV_SET flag enabled
            trainer_flags = trainer.trainermontype.data[0]
            if not (trainer_flags & TrainerDataType.IV_EV_SET):
                continue
            
            # Determine EV budget based on trainer tier
            if not identify_tier:
                raise ValueError("IdentifyTier extractor is required! Every trainer must have a tier!")
            
            if i >= len(trainers.data):
                raise ValueError(f"Trainer index {i} out of range! Trainers data length: {len(trainers.data)}")
            
            trainer_info = trainers.data[i].info
            if not hasattr(trainer_info, 'trainer_id'):
                raise ValueError(f"Trainer {i} has no trainer_id! All trainers must have IDs!")
            
            trainer_tier = identify_tier.get_tier_for_trainer(trainer_info.trainer_id)
            ev_budget = self.tier_budgets[trainer_tier]
            
            # Track tier statistics
            if trainer_tier not in self.tier_stats:
                self.tier_stats[trainer_tier] = {'trainers': 0, 'pokemon': 0}
            self.tier_stats[trainer_tier]['trainers'] += 1
            
            # Process each Pokemon in the trainer's team
            if i < len(trainers.data) and trainers.data[i].team:
                team = trainers.data[i].team
                trainer_name = getattr(trainer, 'name', f'Trainer {i}')
                
                for j, pokemon in enumerate(team):
                    self.total_pokemon_processed += 1
                    self.tier_stats[trainer_tier]['pokemon'] += 1
                    
                    # Get Pokemon species ID
                    species_id = getattr(pokemon, 'species_id', 0)
                    if species_id == 0:
                        continue
                    
                    # Get Pokemon name for logging
                    pokemon_name = f'Pokemon {species_id}'
                    if pokemon_names and hasattr(pokemon_names, 'data') and species_id < len(pokemon_names.data):
                        pokemon_name = pokemon_names.data[species_id] or pokemon_name
                    
                    # Apply GeneralEV allocation with tier-specific budget
                    ev_allocation = self._allocate_evs(pokemon, species_id, mons, ev_budget)
                    
                    self.total_pokemon_allocated += 1
                    
                    # Log the allocation with tier information
                    log_entry = {
                        'trainer': trainer_name,
                        'trainer_tier': trainer_tier,
                        'pokemon': pokemon_name,
                        'ev_allocation': ev_allocation,
                        'ev_budget': ev_budget,
                        'total_evs': sum(ev_allocation.values())
                    }
                    self.allocation_log.append(log_entry)
                    
                    # Print allocation details with tier info
                    total_evs = sum(ev_allocation.values())
                    ev_str = '/'.join([str(ev_allocation[stat]) for stat in ['hp', 'atk', 'def', 'spatk', 'spdef', 'speed']])
                    print(f"  {trainer_name} ({trainer_tier}) - {pokemon_name}: {ev_str} (Total: {total_evs}/{ev_budget})")
        
        print(f"\nGeneralEV Allocation Complete:")
        print(f"  Processed: {self.total_pokemon_processed} Pokemon")
        print(f"  Allocated: {self.total_pokemon_allocated} Pokemon")
        
        # Print tier statistics
        if self.tier_stats:
            print(f"\n  Tier Statistics:")
            for tier, stats in sorted(self.tier_stats.items(), key=lambda x: x[0].value):
                budget = self.tier_budgets.get(tier, self.default_ev_budget)
                print(f"    {tier}: {stats['trainers']} trainers, {stats['pokemon']} Pokemon (Budget: {budget} EVs)")
        else:
            print(f"  Default EV Budget: {self.default_ev_budget}")
    
    def _allocate_evs(self, pokemon, pokemon_id, mons, ev_budget=510):
        """Allocate EVs using the GeneralEV algorithm.
        
        Args:
            pokemon: Pokemon object to allocate EVs for
            pokemon_id: Pokemon species ID
            mons: Mons extractor with base stats
            ev_budget: Total EV budget to allocate (default 510)
        """
        import random
        
        # Get base stats for the Pokemon
        if pokemon_id >= len(mons.data):
            return {'hp': 0, 'atk': 0, 'def': 0, 'spatk': 0, 'spdef': 0, 'speed': 0}
        
        base_stats = mons.data[pokemon_id]
        
        # Initialize EV allocation
        ev_allocation = {'hp': 0, 'atk': 0, 'def': 0, 'spatk': 0, 'spdef': 0, 'speed': 0}
        remaining_budget = ev_budget
        
        # Get base stats for allocation decisions
        stats = {
            'hp': base_stats.hp,
            'atk': base_stats.attack,
            'def': base_stats.defense,
            'spatk': base_stats.sp_attack,
            'spdef': base_stats.sp_defense,
            'speed': base_stats.speed
        }
        
        # Step 1: Allocate 152 EVs to highest base stat
        highest_stats = self._get_highest_stats(stats)
        chosen_highest = random.choice(highest_stats)
        
        if remaining_budget >= 152:
            ev_allocation[chosen_highest] = 152
            remaining_budget -= 152
        else:
            ev_allocation[chosen_highest] = remaining_budget
            remaining_budget = 0
        
        # Step 2: Allocate 100 EVs to second highest stat
        if remaining_budget >= 100:
            remaining_highest = [stat for stat in highest_stats if stat != chosen_highest]
            if remaining_highest:
                chosen_second = random.choice(remaining_highest)
            else:
                # Get next highest tier
                second_highest_stats = self._get_second_highest_stats(stats, highest_stats)
                if second_highest_stats:
                    chosen_second = random.choice(second_highest_stats)
                else:
                    # Fallback to any remaining stat
                    available_stats = [s for s in stats.keys() if s != chosen_highest]
                    chosen_second = random.choice(available_stats) if available_stats else chosen_highest
            
            ev_allocation[chosen_second] = 100
            remaining_budget -= 100
        
        # Step 3: Allocate 50 EVs to random stats, 5 times
        for _ in range(5):
            if remaining_budget < 50:
                break
            
            # Find stats that can accept 50 more EVs (won't exceed 252)
            available_stats = [stat for stat in ev_allocation.keys() 
                             if ev_allocation[stat] + 50 <= 252]
            
            if available_stats:
                chosen_stat = random.choice(available_stats)
                ev_allocation[chosen_stat] += 50
                remaining_budget -= 50
            else:
                break
        
        # Step 4: Allocate final 8 EVs to a random stat
        if remaining_budget >= 8:
            available_stats = [stat for stat in ev_allocation.keys() 
                             if ev_allocation[stat] + 8 <= 252]
            
            if available_stats:
                chosen_stat = random.choice(available_stats)
                ev_allocation[chosen_stat] += 8
                remaining_budget -= 8
        
        # Apply the EV allocation to the Pokemon
        pokemon.hp_ev = ev_allocation['hp']
        pokemon.atk_ev = ev_allocation['atk']
        pokemon.def_ev = ev_allocation['def']
        pokemon.speed_ev = ev_allocation['speed']
        pokemon.spatk_ev = ev_allocation['spatk']
        pokemon.spdef_ev = ev_allocation['spdef']
        
        return ev_allocation
    
    def _get_highest_stats(self, base_stats):
        """Get list of stats tied for highest value."""
        max_value = max(base_stats.values())
        return [stat for stat, value in base_stats.items() if value == max_value]
    
    def _get_second_highest_stats(self, base_stats, exclude_stats):
        """Get list of stats tied for second highest value, excluding specified stats."""
        remaining_stats = {stat: value for stat, value in base_stats.items() 
                         if stat not in exclude_stats}
        
        if not remaining_stats:
            return []
        
        max_value = max(remaining_stats.values())
        return [stat for stat, value in remaining_stats.items() if value == max_value]
    
    def _apply_fallback_evs(self, pokemon):
        """Apply fallback EV allocation if Pokemon data not found."""
        # Simple fallback: 85 EVs in each stat (510 total)
        fallback_ev = 85
        
        pokemon.hp_ev = fallback_ev
        pokemon.atk_ev = fallback_ev
        pokemon.def_ev = fallback_ev
        pokemon.speed_ev = fallback_ev
        pokemon.spatk_ev = fallback_ev
        pokemon.spdef_ev = fallback_ev
        
        return {
            'hp': fallback_ev, 'atk': fallback_ev, 'def': fallback_ev,
            'speed': fallback_ev, 'spatk': fallback_ev, 'spdef': fallback_ev
        }


class GeneralIVStep(Step):
    """Pipeline step to apply tier-based IV allocation to trainer Pokemon.
    
    Supports two modes:
    - ScalingIVs: Progressive IV quality based on trainer tier
    - MaxIVs: All IVs set to 31
    """
    
    def __init__(self, mode="ScalingIVs", trainer_filter=None):
        """Initialize the GeneralIV step.
        
        Args:
            mode (str): "ScalingIVs" or "MaxIVs"
            trainer_filter: Optional function to filter which trainers to modify
        """
        self.mode = mode
        self.trainer_filter = trainer_filter
        self.total_pokemon_processed = 0
        self.total_pokemon_allocated = 0
        self.tier_stats = {}
    
    def run(self, context):
        """Run the GeneralIV allocation step."""
        trainer_data = context.get(TrainerData)
        trainers = context.get(Trainers)
        
        # Get tier information for scaling IVs
        identify_tier = None
        if self.mode == "ScalingIVs":
            try:
                identify_tier = context.get(IdentifyTier)
            except:
                print("Warning: IdentifyTier not available, using Tier 1 for all trainers")
        
        # Get Pokemon names for logging
        try:
            pokemon_names = context.get(LoadPokemonNamesStep)
        except:
            pokemon_names = None
        
        print(f"Applying {self.mode} IV allocation...")
        
        for i, trainer in enumerate(trainer_data.data):
            # Apply filter if provided
            if self.trainer_filter and not self.trainer_filter(trainer, i):
                continue
            
            # Check if trainer has IV_EV_SET flag enabled
            trainer_flags = trainer.trainermontype.data[0]
            if not (trainer_flags & TrainerDataType.IV_EV_SET):
                continue
            
            # Determine trainer tier for ScalingIVs
            if self.mode == "ScalingIVs":
                if not identify_tier:
                    raise ValueError("IdentifyTier extractor is required for ScalingIVs mode! Every trainer must have a tier!")
                
                if i >= len(trainers.data):
                    raise ValueError(f"Trainer index {i} out of range! Trainers data length: {len(trainers.data)}")
                
                trainer_info = trainers.data[i].info
                if not hasattr(trainer_info, 'trainer_id'):
                    raise ValueError(f"Trainer {i} has no trainer_id! All trainers must have IDs!")
                
                trainer_tier = identify_tier.get_tier_for_trainer(trainer_info.trainer_id)
            else:
                trainer_tier = None  # MaxIVs mode doesn't need tiers
            
            # Track tier statistics
            if trainer_tier not in self.tier_stats:
                self.tier_stats[trainer_tier] = {'trainers': 0, 'pokemon': 0}
            self.tier_stats[trainer_tier]['trainers'] += 1
            
            # Process each Pokemon in the trainer's team
            if i < len(trainers.data) and trainers.data[i].team:
                team = trainers.data[i].team
                trainer_name = getattr(trainer, 'name', f'Trainer {i}')
                
                for j, pokemon in enumerate(team):
                    self.total_pokemon_processed += 1
                    self.tier_stats[trainer_tier]['pokemon'] += 1
                    
                    # Get Pokemon species ID and name
                    species_id = getattr(pokemon, 'species_id', 0)
                    pokemon_name = f'Pokemon {species_id}'
                    if pokemon_names and hasattr(pokemon_names, 'data') and species_id < len(pokemon_names.data):
                        pokemon_name = pokemon_names.data[species_id] or pokemon_name
                    
                    # Apply IV allocation based on mode
                    if self.mode == "MaxIVs":
                        iv_allocation = self._allocate_max_ivs(pokemon)
                    else:  # ScalingIVs
                        iv_allocation = self._allocate_scaling_ivs(pokemon, trainer_tier)
                    
                    self.total_pokemon_allocated += 1
                    
                    # Log the allocation
                    iv_str = '/'.join([str(iv_allocation[stat]) for stat in ['hp', 'atk', 'def', 'spatk', 'spdef', 'speed']])
                    print(f"  {trainer_name} ({trainer_tier}) - {pokemon_name}: {iv_str}")
        
        print(f"\n{self.mode} IV Allocation Complete:")
        print(f"  Processed: {self.total_pokemon_processed} Pokemon")
        print(f"  Allocated: {self.total_pokemon_allocated} Pokemon")
        
        # Print tier statistics for ScalingIVs
        if self.mode == "ScalingIVs" and self.tier_stats:
            print(f"\n  Tier Statistics:")
            for tier, stats in sorted(self.tier_stats.items(), key=lambda x: x[0].value if x[0] else ""):
                tier_num = self._get_tier_number(tier)
                max_ivs = self._get_max_ivs_for_tier(tier_num)
                print(f"    {tier} (Tier {tier_num}): {stats['trainers']} trainers, {stats['pokemon']} Pokemon (Max IVs: {max_ivs})")
    
    def _allocate_max_ivs(self, pokemon):
        """Set all IVs to 31."""
        pokemon.hp_iv = 31
        pokemon.atk_iv = 31
        pokemon.def_iv = 31
        pokemon.speed_iv = 31
        pokemon.spatk_iv = 31
        pokemon.spdef_iv = 31
        
        return {'hp': 31, 'atk': 31, 'def': 31, 'spatk': 31, 'spdef': 31, 'speed': 31}
    
    def _allocate_scaling_ivs(self, pokemon, trainer_tier):
        """Allocate IVs based on trainer tier."""
        import random
        
        tier_num = self._get_tier_number(trainer_tier)
        max_ivs_count = self._get_max_ivs_for_tier(tier_num)
        
        # Start with all IVs in range 16-31
        iv_allocation = {
            'hp': random.randint(16, 31),
            'atk': random.randint(16, 31),
            'def': random.randint(16, 31),
            'spatk': random.randint(16, 31),
            'spdef': random.randint(16, 31),
            'speed': random.randint(16, 31)
        }
        
        # Randomly select stats to set to 31 based on tier
        if max_ivs_count > 0:
            stats_to_max = random.sample(list(iv_allocation.keys()), min(max_ivs_count, 6))
            for stat in stats_to_max:
                iv_allocation[stat] = 31
        
        # Apply to Pokemon object
        pokemon.hp_iv = iv_allocation['hp']
        pokemon.atk_iv = iv_allocation['atk']
        pokemon.def_iv = iv_allocation['def']
        pokemon.speed_iv = iv_allocation['speed']
        pokemon.spatk_iv = iv_allocation['spatk']
        pokemon.spdef_iv = iv_allocation['spdef']
        
        return iv_allocation
    
    def _get_tier_number(self, trainer_tier):
        """Convert tier name to tier number."""
        tier_map = {
            Tier.EARLY_GAME: 1,
            Tier.MID_GAME: 2,
            Tier.LATE_GAME: 3,
            Tier.END_GAME: 4
        }
        if trainer_tier not in tier_map:
            raise ValueError(f"Invalid tier: {trainer_tier}! Valid tiers: {list(tier_map.keys())}")
        return tier_map[trainer_tier]
    
    def _get_max_ivs_for_tier(self, tier_num):
        """Get number of IVs to set to 31 for each tier."""
        tier_max_ivs = {
            1: 0,  # Tier 1: All random 16-31
            2: 2,  # Tier 2: 2 IVs at 31
            3: 4,  # Tier 3: 4 IVs at 31
            4: 6   # Tier 4: All IVs at 31
        }
        return tier_max_ivs.get(tier_num, 0)


class SetTrainerMovesStep(Step):
    """Step to set each trainer Pokemon's moves to the last four moves learned at their current level."""
    
    def __init__(self):
        pass
    
    def run(self, context):
        trainers = context.get(Trainers)
        learnsets = context.get(Learnsets)
        
        for trainer in trainers.data:
            for pokemon in trainer.team:
                # Get the learnset for this Pokemon species
                if pokemon.species_id < len(learnsets.data):
                    learnset = learnsets.data[pokemon.species_id]
                    
                    # Find all moves this Pokemon can learn up to its current level
                    available_moves = []
                    for learn_entry in learnset:
                        if learn_entry.level <= pokemon.level:
                            available_moves.append(learn_entry.move_id)
                    
                    # Get the last four moves (or all available if less than 4)
                    if available_moves:
                        last_four_moves = available_moves[-4:]
                        
                        # Pad with 0 if we have fewer than 4 moves
                        while len(last_four_moves) < 4:
                            last_four_moves.insert(0, 0)
                        
                        # Set the moves if this Pokemon has a moves array
                        if hasattr(pokemon, 'moves'):
                            pokemon.moves = last_four_moves


class IdentifyGymTrainers(Extractor):
    class Gym:
        def __init__(self, name, trainers, gym_type=None):
            self.name = name
            self.trainers = trainers
            self.type = gym_type
    
    def __init__(self, context):
        super().__init__(context)
        self.data = {}
        
        trainers = context.get(Trainers)
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
            "Will": ["Will",],
            "Koga": ["Koga",],
            "Bruno": ["Bruno",],
            "Karen": ["Karen",],
            "Lance": ["Lance",],
            
            #champion should be separate entity that we can modify without touching "gyms", as should rival fights
            
        }
        
        for gym_name, trainer_specs in gym_definitions.items():
            trainer_ids = [index.find(spec) for spec in trainer_specs]
            gym_trainers = [trainers.data[tid] for tid in trainer_ids if tid is not None]
            
            gym_type = self._detect_gym_type(gym_trainers)
            self.data[gym_name] = self.Gym(gym_name, gym_trainers, gym_type)
    
    def _detect_gym_type(self, trainers):
        type_counts = Counter()
        
        mondata = self.context.get(Mons)
        
        for trainer in trainers:
            for pokemon in trainer.team:
                species = mondata.data[pokemon.species_id]
                type_counts[Type(int(species.type1))] += 1
                if species.type2 != species.type1:
                    type_counts[Type(int(species.type2))] += 1
        
        return type_counts.most_common(1)[0][0] if type_counts else None


class IdentifyBosses(Extractor):
    class Boss:
        def __init__(self, name, trainers):
            self.name = name
            self.trainers = trainers
    
    def __init__(self, context):
        super().__init__(context)
        self.data = {}
        
        trainers = context.get(Trainers)
        index = context.get(IndexTrainers)
        
        # Editable list of boss trainers - these are significant battles separate from gyms
        boss_definitions = {
            "Gym leaders" : ["Falkner", "Bugsy", "Whitney", "Morty", "Chuck", "Jasmine", "Pryce", "Clair", "Brock", "Misty", "Sabrina", "Blaine", "Janine", "Lt. Surge", "Erika", "Blue",],
            "Team Rocket Executives": ["Archer", "Ariana", "Petrel", "Proton"],
            "Giovanni": ["Giovanni"],
            "Red": ["Red"],
            "Rival": ["Silver"],  # Main rival battles
            "Champion": ["Lance"],  # Final champion battle
            "Elite Four": ["Will", "Koga", "Bruno", "Karen"],  # Elite Four 
            
            
           
        }
        
        for boss_name, trainer_specs in boss_definitions.items():
            trainer_ids = [index.find(spec) for spec in trainer_specs]
            boss_trainers = [trainers.data[tid] for tid in trainer_ids if tid is not None]
            
            self.data[boss_name] = self.Boss(boss_name, boss_trainers)



class IdentifyRivals(Extractor):
    """Identifies rival trainers for special handling."""
    
    class Rival:
        def __init__(self, name, trainers):
            self.name = name
            self.trainers = trainers
    
    # Define starter group trainer IDs as class properties
    @property
    def chikorita_group_ids(self):
        """Trainer IDs for rivals who originally had Chikorita-line starters (Starter slot 0)."""
        return [1, 263, 264, 265, 285, 288, 489, 495, 735]
    
    @property
    def cyndaquil_group_ids(self):
        """Trainer IDs for rivals who originally had Cyndaquil-line starters (Starter slot 1)."""
        return [2, 266, 267, 268, 286, 289, 490, 496, 736]
    
    @property
    def totodile_group_ids(self):
        """Trainer IDs for rivals who originally had Totodile-line starters (Starter slot 2)."""
        return [3, 269, 270, 271, 272, 287, 491, 497, 737]
    
    @property
    def all_rival_trainer_ids(self):
        """All rival trainer IDs across all starter groups."""
        return self.chikorita_group_ids + self.cyndaquil_group_ids + self.totodile_group_ids
    
    def __init__(self, context):
        super().__init__(context)
        self.data = {}
        
        trainers = context.get(Trainers)
        
        # Collect all rival trainers using the hardcoded IDs
        rival_trainers = []
        for trainer_id in self.all_rival_trainer_ids:
            if trainer_id < len(trainers.data):
                rival_trainers.append(trainers.data[trainer_id])
            else:
                print(f"Warning: Trainer ID {trainer_id} not found in trainers data")
        
        self.data["Silver"] = self.Rival("Silver", rival_trainers)
        print(f"Found {len(rival_trainers)} Silver rival trainers using hardcoded IDs")
    
    def get_rival_trainers(self, rival_name):
        """Get all trainer instances for a specific rival name."""
        rival = self.data.get(rival_name)
        return rival.trainers if rival else []
    
    def get_all_rival_trainers(self):
        """Get all rival trainers as a flat list."""
        all_rivals = []
        for rival in self.data.values():
            all_rivals.extend(rival.trainers)
        return all_rivals
    
    def get_rival_trainer_ids(self):
        """Get all rival trainer IDs as a set for quick lookup."""
        rival_ids = set()
        for rival in self.data.values():
            for trainer in rival.trainers:
                rival_ids.add(trainer.info.trainer_id)
        return rival_ids
    
    def get_trainers_by_starter_group(self, starter_slot, trainers_data):
        """Get trainer objects for a specific starter group (0=Chikorita, 1=Cyndaquil, 2=Totodile)."""
        group_ids = {
            0: self.chikorita_group_ids,
            1: self.cyndaquil_group_ids,
            2: self.totodile_group_ids
        }
        
        if starter_slot not in group_ids:
            raise ValueError(f"Invalid starter slot {starter_slot}. Must be 0, 1, or 2.")
        
        group_trainers = []
        for trainer_id in group_ids[starter_slot]:
            if trainer_id < len(trainers_data):
                group_trainers.append(trainers_data[trainer_id])
        
        return group_trainers
    
    def get_starter_group_name(self, starter_slot):
        """Get the name of a starter group."""
        group_names = {0: "Chikorita", 1: "Cyndaquil", 2: "Totodile"}
        return group_names.get(starter_slot, "Unknown")


class IdentifyTier(Extractor):
    """Assigns trainers to game progression tiers based on their highest level Pokémon.
    
    Tiers are defined by specific trainer ace levels:
    - EarlyGame: Level 1 to Whitney's ace level
    - MidGame: Whitney's ace level to Jasmine's ace level  
    - Tier.LATE_GAME: Jasmine's ace level to Will's ace level
    - EndGame: Will's ace level to Level 100
    """
    
    def __init__(self, context):
        super().__init__(context)
        self.data = {}  # trainer_id -> tier_name
        
        trainers = context.get(Trainers)
        index = context.get(IndexTrainers)
        
        # Find the lowest ace levels for tier boundary trainers
        whitney_ace_level = self._find_lowest_ace_level(trainers, index, "Whitney")
        jasmine_ace_level = self._find_lowest_ace_level(trainers, index, "Jasmine")
        will_ace_level = self._find_lowest_ace_level(trainers, index, "Will")
        
        # Define tier boundaries
        self.tier_boundaries = {
            Tier.EARLY_GAME: (1, whitney_ace_level),
            Tier.MID_GAME: (whitney_ace_level, jasmine_ace_level),
            Tier.LATE_GAME: (jasmine_ace_level, will_ace_level),
            Tier.END_GAME: (will_ace_level, 100)
        }
        
        # Assign each trainer to a tier
        for trainer in trainers.data:
            highest_level = self._get_highest_level(trainer)
            tier = self._determine_tier(highest_level)
            self.data[trainer.info.trainer_id] = tier
            print(f"{trainer.info.name}: {tier}{highest_level}")
    
    
    def _find_lowest_ace_level(self, trainers, index, trainer_name):
        """Find the lowest ace level among all instances of a trainer."""
        trainer_ids = []
        
        # Handle potential multiple instances of the trainer
        if trainer_name in index.data:
            for trainer_class, trainer_id in index.data[trainer_name]:
                trainer_ids.append(trainer_id)
        
        if not trainer_ids:
            # Fallback values if trainer not found
            fallback_levels = {"Whitney": 20, "Jasmine": 35, "Will": 50}
            return fallback_levels.get(trainer_name, 50)
        
        lowest_ace_level = float('inf')
        
        for trainer_id in trainer_ids:
            trainer = trainers.data[trainer_id]
            if trainer.ace_index is not None:
                ace_level = trainer.team[trainer.ace_index].level
                lowest_ace_level = min(lowest_ace_level, ace_level)
            else:
                # If no ace, use highest level in team
                highest_level = self._get_highest_level(trainer)
                lowest_ace_level = min(lowest_ace_level, highest_level)
        
        return int(lowest_ace_level) if lowest_ace_level != float('inf') else 50
    
    def _get_highest_level(self, trainer):
        """Get the highest level Pokémon in a trainer's team."""
        if not trainer.team:
            return 1
        return max(pokemon.level for pokemon in trainer.team)
    
    def _determine_tier(self, level):
        """Determine which tier a level falls into."""
        for tier_name, (min_level, max_level) in self.tier_boundaries.items():
            if min_level <= level < max_level:
                return tier_name
        
        # Handle edge case for level 100
        if level >= self.tier_boundaries[Tier.END_GAME][0]:
            return Tier.END_GAME
        
        # NO FALLBACKS! Every trainer must have a tier!
        raise ValueError(f"No tier found for level {level}! Tier boundaries: {self.tier_boundaries}")
    
    def get_tier_for_trainer(self, trainer_id):
        """Get the tier for a specific trainer ID."""
        if trainer_id not in self.data:
            raise ValueError(f"No tier found for trainer_id {trainer_id}! All trainers must have a tier!")
        return self.data[trainer_id]
    
    def get_trainers_by_tier(self, tier_name):
        """Get all trainer IDs in a specific tier."""
        return [tid for tid, tier in self.data.items() if tier == tier_name]
    
    def get_tier_boundaries(self):
        """Get the level boundaries for each tier."""
        return self.tier_boundaries.copy()


class RandomizeGymTypesStep(Step):
    
    def run(self, context):
        gyms = context.get(IdentifyGymTrainers)
        
        # Count how many times each type has been used
        type_usage = {t: 0 for t in Type}
        
        # First pass: Count number of gyms with types for planning
        total_gyms_with_types = sum(1 for gym in gyms.data.values() if gym.type is not None)
        
        # Calculate how many of each type we need to ensure all types are used at least once
        num_types = len(Type)
        min_usage_per_type = 1
        
        if total_gyms_with_types < num_types:
            # Not enough gyms to use each type once
            raise ValueError(f"Cannot satisfy type distribution requirements: Only {total_gyms_with_types} gyms available, but {num_types} types exist.")
        
        # Randomize gyms in a way that ensures type distribution constraints
        for gym_name, gym in gyms.data.items():
            if gym.type is not None:
                # Create a filter that respects our type distribution rules
                valid_types = []
                
                # First priority: Types that haven't been used the minimum number of times yet
                unused_types = [t for t in Type if type_usage[t] < min_usage_per_type]
                if unused_types:
                    valid_types = unused_types
                else:
                    # Second priority: Types that haven't been used twice yet
                    valid_types = [t for t in Type if type_usage[t] < 2]
                    
                    # If we've used all types twice already, we can't meet the requirement
                    if not valid_types:
                        raise ValueError(f"Cannot satisfy type distribution requirements: All types used twice already at gym {gym_name}.")
                
                # Make sure we have valid types to choose from
                if not valid_types:
                    raise ValueError(f"No valid types available for gym {gym_name}.")
                    
                # Choose a type from our valid options
                original_type = gym.type
                gym.type = context.decide(
                    path=["gyms", gym_name, "type"],
                    original=original_type,
                    candidates=valid_types,
                    filter=NoFilter()
                )
                
                # Update our type usage counter
                type_usage[gym.type] += 1


class RandomizeGymsStep(Step):
    def __init__(self, filter):
        self.filter = filter
    
    def run(self, context):
        gyms = context.get(IdentifyGymTrainers)
        mondata = context.get(Mons)
        
        for gym_name, gym in gyms.data.items():
            if gym.type is not None:
                self._randomize_gym_teams(context, gym, mondata)
    
    def _randomize_gym_teams(self, context, gym, mondata):
        filter = AllFilters([self.filter, TypeMatches([int(gym.type)])])
        for trainer in gym.trainers:
            self._randomize_trainer_team(context, trainer, mondata, filter)

    def _randomize_trainer_team(self, context, trainer, mondata, filter):
        for i, pokemon in enumerate(trainer.team):
            new_species = context.decide(
                path=["gymtrainer", trainer.info.name, "team", i, "species"],
                original=mondata.data[pokemon.species_id],
                candidates=list(mondata.data),
                filter=filter
            )
            pokemon.species_id = new_species.pokemon_id


class RandomizeOrdinaryTrainersStep(Step):
    """Randomize all ordinary trainers (no gym leaders, rivals, E4, possibly Rocket Leaders if I ever get around to it)."""
    
    def __init__(self, filter):
        self.filter = filter
    
    def run(self, context):
        trainers = context.get(Trainers)
        gyms = context.get(IdentifyGymTrainers)
        rivals = context.get(IdentifyRivals)
        mondata = context.get(Mons)
        
        # Create a set of trainer IDs to exclude (gym trainers and rivals)
        excluded_trainer_ids = set()
        
        # Add gym trainer IDs
        for gym in gyms.data.values():
            for trainer in gym.trainers:
                excluded_trainer_ids.add(trainer.info.trainer_id)
        
        # Add rival trainer IDs
        rival_ids = rivals.get_rival_trainer_ids()
        excluded_trainer_ids.update(rival_ids)
        print(f"Excluding {len(rival_ids)} rival trainer IDs: {sorted(rival_ids)}")
        
        # Randomize all ordinary trainers (excluding gyms and rivals)
        for trainer in trainers.data:
            if trainer.info.trainer_id not in excluded_trainer_ids:
                self._randomize_trainer_team(context, trainer, mondata, self.filter)
    
    def _randomize_trainer_team(self, context, trainer, mondata, filter):
        """Randomize a trainer's team using the provided filter."""
        for i, pokemon in enumerate(trainer.team):
            new_species = context.decide(
                path=["trainer", trainer.info.name, "team", i, "species"],
                original=mondata.data[pokemon.species_id],
                candidates=list(mondata.data),
                filter=filter
            )
            pokemon.species_id = new_species.pokemon_id


class ConsistentRivalStarter(Step):
    """Updates rival teams to use starters consistent with the player's randomized choice."""
    
    def run(self, context):
        starters = context.get(StarterExtractor)
        trainers = context.get(Trainers)
        evolution_data = context.get(EvolutionData)
        mons = context.get(Mons)
        rivals = context.get(IdentifyRivals)
        
        # Rival starter logic: rival gets the starter that's strong against the player's choice
        rival_battle_groups = {
            0: (rivals.chikorita_group_ids, 2),  #I dont know why this needs to be offset. I've searched and I just don't know.
            1: (rivals.cyndaquil_group_ids, 0),  
            2: (rivals.totodile_group_ids, 1),   
        }
        
        
        # Get the current starter Pokemon (use the updated starter_id values)
        current_starters = [mons.data[starter_id] for starter_id in starters.data.starter_id]
        
        # Print the new starters being used
        print("\n=== ConsistentRivalStarter: New Starter Assignments ===")
        print(f"Starter Slot 0 (Chikorita group): {current_starters[0].name}")
        print(f"Starter Slot 1 (Cyndaquil group): {current_starters[1].name}")
        print(f"Starter Slot 2 (Totodile group): {current_starters[2].name}")
        print("================================================\n")
        
        # Process all rival battle groups
        total_updated = 0
        
        for original_starter_slot, (trainer_ids, rival_starter_slot) in rival_battle_groups.items():
            # Get the new starter Pokemon for the rival (the one that's strong against the original)
            new_starter = current_starters[rival_starter_slot]
            original_starter_name = ["Chikorita", "Cyndaquil", "Totodile"][original_starter_slot]
            group_updated = 0
            
            print(f"\nProcessing {original_starter_name} group (gets {new_starter.name}) - {len(trainer_ids)} battles:")
            
            for trainer_id in trainer_ids:
                if trainer_id < len(trainers.data):
                    trainer = trainers.data[trainer_id]
                    
                    # Determine which Pokemon to replace (ace, last, or only)
                    target_pokemon = self._get_target_pokemon(trainer)
                    
                    if target_pokemon:
                        pokemon_level = target_pokemon.level
                        
                        # Determine the appropriate evolution stage
                        final_species = self._get_evolved_form(
                            new_starter, pokemon_level, evolution_data
                        )
                        
                        # Update the Pokemon
                        old_name = mons.data[target_pokemon.species_id].name
                        target_pokemon.species_id = final_species.pokemon_id
                        group_updated += 1
                        total_updated += 1
                        
                        print(f"  ID {trainer_id}: {old_name} (Lv{pokemon_level}) -> {final_species.name}")
                else:
                    print(f"  ID {trainer_id}: Trainer not found (ID too high)")
            
            print(f"  Updated {group_updated}/{len(trainer_ids)} battles in this group")
        
        print(f"\nTotal: Updated {total_updated} rival starter Pokemon across all groups")
    
    def _get_target_pokemon(self, trainer):
        """Get the target Pokemon to replace (ace, last, or only Pokemon)."""
        if len(trainer.team) == 1:
            # Only one Pokemon, replace it
            return trainer.team[0]
        elif trainer.ace:
            # Has an ace, replace the ace
            return trainer.ace
        else:
            # No ace, replace the last Pokemon in the party
            return trainer.team[-1]
    
    def _get_evolved_form(self, base_starter, level, evolution_data):
        """Get the appropriate evolved form based on level and evolution data."""
        
        current_species = base_starter
        evolution_path = evolution_data.get_evolution_paths(base_starter.pokemon_id)
        
        if not evolution_path or len(evolution_path[0]) == 1:
            # No evolution path, return the base starter
            return current_species
        
        full_path = evolution_path[0]  # Get the first (main) evolution path
        
        # Check each evolution in the path
        for i in range(len(full_path) - 1):
            current_pokemon_id = full_path[i].pokemon_id
            next_pokemon = full_path[i + 1]
            
            # Get evolution data for current Pokemon
            current_evo_data = evolution_data.data[current_pokemon_id]
            
            # Find the evolution that leads to the next Pokemon in the path
            evolution_to_next = None
            for evo in current_evo_data.valid_evolutions:
                if evo.target and evo.target.pokemon_id == next_pokemon.pokemon_id:
                    evolution_to_next = evo
                    break
            
            if not evolution_to_next:
                break
            
            # Check if we should evolve based on method and level
            should_evolve = False
            
            if EvolutionMethod(evolution_to_next.method).param_type == EvoParam.LEVEL:
                # Level-based evolution: evolve if level >= parameter
                if level >= evolution_to_next.parameter:
                    should_evolve = True
            else:
                # Non-level evolution: use fallback level ranges
                if i == 0:  # First evolution (base -> stage 1)
                    should_evolve = level >= 22
                elif i == 1:  # Second evolution (stage 1 -> stage 2)
                    should_evolve = level >= 36
            
            if should_evolve:
                current_species = next_pokemon
            else:
                break
        
        return current_species


class ForceEvolvedTrainerPokemon(Step):
    """Pipeline step to evolve trainer Pokemon based on configurable evolution thresholds.
    
    Supports both level-based and tier-based evolution logic with configurable targeting
    (bosses only vs all trainers). Allows easy editing of should_evolve levels.
    """
    
    def __init__(self,
                 # Targeting options
                 target_mode="all",  # "all", "bosses_only"
                 # Evolution threshold mode
                 evolution_mode="level_based",  # "level_based", "tier_based"
                 # Level-based evolution thresholds (fallback for non-level evolutions)
                 stage1_evolution_level=22,  # Base -> Stage 1 evolution level
                 stage2_evolution_level=36,  # Stage 1 -> Stage 2 evolution level
                 # Trainer filter
                 trainer_filter=None):
        
        # Validate parameters
        if target_mode not in ["all", "bosses_only"]:
            raise ValueError(f"Invalid target_mode: {target_mode}. Must be 'all' or 'bosses_only'")
        if evolution_mode not in ["level_based", "tier_based"]:
            raise ValueError(f"Invalid evolution_mode: {evolution_mode}. Must be 'level_based' or 'tier_based'")
        
        self.target_mode = target_mode
        self.evolution_mode = evolution_mode
        self.trainer_filter = trainer_filter
        
        # Level-based thresholds
        self.stage1_evolution_level = stage1_evolution_level
        self.stage2_evolution_level = stage2_evolution_level
        
        # Statistics tracking
        self.total_pokemon_processed = 0
        self.total_pokemon_evolved = 0
        self.evolution_log = []
    
    def run(self, context):
        """Run the Pokemon evolution step."""
        # Get required extractors
        trainers = context.get(Trainers)
        evolution_data = context.get(EvolutionData)
        mons = context.get(Mons)
        
        # Get optional extractors based on mode
        bosses = None
        identify_tier = None
        
        if self.target_mode == "bosses_only":
            bosses = context.get(IdentifyBosses)
            boss_trainer_ids = set()
            for boss_category in bosses.data.values():
                for trainer in boss_category.trainers:
                    boss_trainer_ids.add(trainer.info.trainer_id)
        
        if self.evolution_mode == "tier_based":
            identify_tier = context.get(IdentifyTier)
        
        print(f"Evolving trainer Pokemon with {self.evolution_mode} thresholds (target: {self.target_mode})...")
        
        # Process all trainers
        for trainer in trainers.data:
            # Apply targeting filter
            if self.target_mode == "bosses_only":
                if trainer.info.trainer_id not in boss_trainer_ids:
                    continue
            
            # Apply custom trainer filter if provided
            if self.trainer_filter and not self.trainer_filter(trainer):
                continue
            
            # Get trainer tier if using tier-based evolution
            trainer_tier = None
            if self.evolution_mode == "tier_based":
                trainer_tier = identify_tier.get_tier_for_trainer(trainer.info.trainer_id)
            
            # Process each Pokemon in the trainer's team
            for i, pokemon in enumerate(trainer.team):
                self.total_pokemon_processed += 1
                
                # Get current species data
                current_species = self._get_pokemon_data(mons, pokemon.species_id)
                if not current_species:
                    continue
                
                # Check if this Pokemon is an EvioliteUser - if so, don't evolve it
                if self._is_eviolite_user(context, current_species):
                    continue
                
                # Attempt to evolve the Pokemon
                evolved_species = self._get_evolved_form(
                    current_species, pokemon.level, evolution_data, trainer_tier
                )
                
                # Update Pokemon if it evolved
                if evolved_species.pokemon_id != current_species.pokemon_id:
                    old_species_id = pokemon.species_id
                    pokemon.species_id = evolved_species.pokemon_id
                    self.total_pokemon_evolved += 1
                    
                    # Log the evolution
                    trainer_name = getattr(trainer.info, 'name', f'Trainer {trainer.info.trainer_id}')
                    self.evolution_log.append({
                        'trainer': trainer_name,
                        'pokemon_slot': i,
                        'level': pokemon.level,
                        'old_species': old_species_id,
                        'new_species': evolved_species.pokemon_id,
                        'tier': trainer_tier
                    })
        
        print(f"\nEvolution Complete:")
        print(f"  Processed: {self.total_pokemon_processed} Pokemon")
        print(f"  Evolved: {self.total_pokemon_evolved} Pokemon")
        
        # Print evolution statistics by tier if using tier-based mode
        if self.evolution_mode == "tier_based" and self.evolution_log:
            tier_stats = {}
            for entry in self.evolution_log:
                tier = entry['tier']
                if tier not in tier_stats:
                    tier_stats[tier] = 0
                tier_stats[tier] += 1
            
            print(f"\n  Evolution Statistics by Tier:")
            for tier, count in sorted(tier_stats.items(), key=lambda x: x[0].value):
                print(f"    {tier}: {count} Pokemon evolved")
    
    def _get_pokemon_data(self, mons, pokemon_id):
        """Get Pokemon data by species ID."""
        for mon in mons.data:
            if mon.pokemon_id == pokemon_id:
                return mon
        return None
    
    def _is_eviolite_user(self, context, pokemon_species):
        """Check if a Pokemon is an EvioliteUser and should not be evolved.
        
        Returns True if the Pokemon should use Eviolite and not evolve.
        Returns False if EvioliteUser class is not available or Pokemon is not an EvioliteUser.
        """
        try:
            # Try to get the EvioliteUser extractor
            eviolite_users = context.get(EvioliteUser)
            return pokemon_species.pokemon_id in eviolite_users.by_id
        except:
            # EvioliteUser class doesn't exist yet or isn't available
            # Return False to allow normal evolution
            return False
    
    def _get_evolved_form(self, base_species, level, evolution_data, trainer_tier=None):
        """Get the appropriate evolved form based on level and evolution thresholds."""
        current_species = base_species
        evolution_path = evolution_data.get_evolution_paths(base_species.pokemon_id)
        
        if not evolution_path or len(evolution_path[0]) == 1:
            # No evolution path, return the base species
            return current_species
        
        full_path = evolution_path[0]  # Get the first (main) evolution path
        
        # For tier-based mode, use simplified evolution logic
        if self.evolution_mode == "tier_based" and trainer_tier is not None:
            return self._get_tier_based_evolution(full_path, trainer_tier)
        
        # For level-based mode, check each evolution in the path
        for i in range(len(full_path) - 1):
            current_pokemon_id = full_path[i].pokemon_id
            next_pokemon = full_path[i + 1]
            
            # Get evolution data for current Pokemon
            current_evo_data = evolution_data.data[current_pokemon_id]
            
            # Find the evolution that leads to the next Pokemon in the path
            evolution_to_next = None
            for evo in current_evo_data.valid_evolutions:
                if evo.target and evo.target.pokemon_id == next_pokemon.pokemon_id:
                    evolution_to_next = evo
                    break
            
            if not evolution_to_next:
                break
            
            # Check if we should evolve based on method and level
            should_evolve = self._should_evolve(evolution_to_next, level, i, trainer_tier)
            
            if should_evolve:
                current_species = next_pokemon
            else:
                break
        
        return current_species
    
    def _get_tier_based_evolution(self, full_path, trainer_tier):
        """Get evolved form based on simplified tier-based logic.
        
        Tier 2 (Mid Game): All 2-stage evolution families should be fully evolved
        Tier 3 & 4 (Late/End Game): All 3-stage evolution families should be fully evolved
        """
        path_length = len(full_path)
        
        if trainer_tier == Tier.EARLY_GAME:
            # Tier 1: No evolution
            return full_path[0]
        elif trainer_tier == Tier.MID_GAME:
            # Tier 2: Evolve 2-stage families to final form, 3-stage families to stage 1
            if path_length == 2:
                # 2-stage family: evolve to final form
                return full_path[1]
            elif path_length >= 3:
                # 3-stage family: evolve to stage 1 only
                return full_path[1]
            else:
                # No evolution possible
                return full_path[0]
        elif trainer_tier in [Tier.LATE_GAME, Tier.END_GAME]:
            # Tier 3 & 4: Evolve all families to final form
            return full_path[-1]  # Final evolution
        else:
            # Fallback: no evolution
            return full_path[0]
    
    def _should_evolve(self, evolution, level, evolution_stage, trainer_tier=None):
        """Determine if Pokemon should evolve based on evolution method and thresholds."""
        if EvolutionMethod(evolution.method).param_type == EvoParam.LEVEL:
            # Level-based evolution: evolve if level >= parameter
            return level >= evolution.parameter
        else:
            # Non-level evolution: use configured thresholds (level-based mode only)
            if evolution_stage == 0:  # First evolution (base -> stage 1)
                return level >= self.stage1_evolution_level
            elif evolution_stage == 1:  # Second evolution (stage 1 -> stage 2)
                return level >= self.stage2_evolution_level
        
        return False
    
    def get_evolution_summary(self):
        """Get a summary of all evolutions performed.
        
        Returns:
            dict: Summary statistics and detailed log
        """
        return {
            'total_processed': self.total_pokemon_processed,
            'total_evolved': self.total_pokemon_evolved,
            'evolution_mode': self.evolution_mode,
            'target_mode': self.target_mode,
            'evolution_log': self.evolution_log
        }


class ReadTypeMapping(Extractor):
    # set in subclass
    type_data = None
    
    def __init__(self, context):
        super().__init__(context)
        self.mons = context.get(Mons)
        self.ability_names = context.get(LoadAbilityNames)
        self.typeset_to_mons = self._build_index()
        self.data = self._process_data()
    
    def _build_index(self):
        typeset_to_mons = {}
        for pokemon in self.mons.data:
            typeset = frozenset({int(pokemon.type1), int(pokemon.type2)})
            if typeset not in typeset_to_mons:
                typeset_to_mons[typeset] = []
            typeset_to_mons[typeset].append(pokemon)
        return typeset_to_mons
    
    def _process_data(self):
        data = {}
        for (t, ts) in self.type_data.items():
            data[t] = []
            for entry in ts:
                data[t].extend(self._handle_entry(entry))
        return data
    
    def _handle_entry(self, entry):
        if isinstance(entry, tuple):
            typeset = frozenset({int(t) for t in entry})
            return self.typeset_to_mons.get(typeset, [])
        elif isinstance(entry, HasAbility):
            ability_id = self.ability_names.get_by_name(entry.ability_name)
            return [
                pokemon for pokemon in self.mons.data
                if ability_id in [pokemon.ability1, pokemon.ability2]
            ]


class Pivots(ReadTypeMapping):
    type_data = pivots_type_data


class Fulcrums(ReadTypeMapping):
    type_data = fulcrums_type_data

#add class for champion only
#add class for rival fights
#add class for red
#####################################################################################################

def parse_verbosity_overrides(verbosity_args):
    """Parse -v arguments into list of (path_list, level) tuples."""
    overrides = []
    for arg in verbosity_args:
        if '=' in arg:
            path_str, level = arg.split('=', 1)
            path_list = [p.lower() for p in path_str.split('/') if p]
            overrides.append((path_list, int(level)))
        else:
            # Global verbosity - empty path prefix
            overrides.append(([], int(arg)))
    return overrides


        
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test RandomizeGymsStep")
    parser.add_argument("--bst-factor", type=float, default=0.15, help="BST factor for filtering (default: 0.15)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Don't output details")
    parser.add_argument("--seed", "-s", type=str, help="Random seed")
    parser.add_argument("--verbosity", "-v", action="append", type=str, 
                       help="Verbosity: level (global) or path=level (path-specific)")
    
    # Options to control filtering of special Pokémon categories
    parser.add_argument("--allow-restricted", action="store_true", help="Allow restricted legendary Pokémon")
    parser.add_argument("--allow-mythical", action="store_true", help="Allow mythical Pokémon")
    parser.add_argument("--allow-ultra-beasts", action="store_true", help="Allow Ultra Beast Pokémon")
    parser.add_argument("--allow-paradox", action="store_true", help="Allow Paradox Pokémon")
    parser.add_argument("--allow-sublegendary", action="store_true", help="Allow SubLegendary Pokémon")
    parser.add_argument("--independent-encounters", action="store_true", help="Make encounter replacements independent by area")
    parser.add_argument("--expand-bosses-only", action="store_true", help="Only expand teams for boss trainers (gym leaders, Elite Four, etc.)")
    parser.add_argument("--wild-level-mult", type=float, default=1.0, help="Multiplier for wild Pokémon levels (default: 1.0)")
    parser.add_argument("--trainer-level-mult", type=float, default=1.0, help="Multiplier for trainer Pokémon levels with special boss/ace logic (default: 1.0)")
    parser.add_argument("--randomize-starters", action="store_true", help="Randomize starter Pokémon")
    parser.add_argument("--consistent-rival-starters", action="store_true", help="Update rival teams to use starters consistent with the player's randomized choice")
    parser.add_argument("--randomize-ordinary-trainers", action="store_true", help="Randomize all ordinary trainers (rivals, Team Rocket, etc.)")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(int(args.seed))
    
    # Parse verbosity overrides
    vbase = 0 if args.quiet else 2
    verbosity_overrides = [([], vbase)] + parse_verbosity_overrides(args.verbosity or [])
    
    # Load ROM
    with open("recompiletest.nds", "rb") as f:
        rom = ndspy.rom.NintendoDSRom(f.read())
    
    # Create context and load data
    ctx = RandomizationContext(rom, verbosity_overrides=verbosity_overrides)

    # Create filters from options
    legendary_filters = [
        NotInSet(ctx.get(LoadBlacklistStep).by_id),
        NotInSet(ctx.get(InvalidPokemon).by_id),
        *([] if args.allow_restricted else [NotInSet(ctx.get(RestrictedPokemon).by_id)]),
        *([] if args.allow_mythical else [NotInSet(ctx.get(MythicalPokemon).by_id)]),
        *([] if args.allow_ultra_beasts else [NotInSet(ctx.get(UltraBeastPokemon).by_id)]),
        *([] if args.allow_paradox else [NotInSet(ctx.get(ParadoxPokemon).by_id)]),
        *([] if args.allow_sublegendary else [NotInSet(ctx.get(SubLegendaryPokemon).by_id)])
    ]
    
    gym_filter = AllFilters(legendary_filters + [BstWithinFactor(args.bst_factor)])
    encounter_filter = AllFilters(legendary_filters + [BstWithinFactor(args.bst_factor)])
    starter_filter = AllFilters(legendary_filters)
    trainer_filter = AllFilters(legendary_filters + [BstWithinFactor(args.bst_factor)])

    # Do everything
    ctx.run_pipeline([
        TrainerMult(multiplier=args.trainer_level_mult),
        ExpandTrainerTeamsStep(bosses_only=args.expand_bosses_only),
        WildMult(multiplier=args.wild_level_mult),
        RandomizeGymTypesStep(),
        RandomizeGymsStep(gym_filter),
        RandomizeEncountersStep(encounter_filter, args.independent_encounters),
        *([] if not args.randomize_starters else [RandomizeStartersStep(starter_filter)]),
        *([] if not args.consistent_rival_starters else [ConsistentRivalStarter()]),
        *([] if not args.randomize_ordinary_trainers else [RandomizeOrdinaryTrainersStep(trainer_filter)]),
        ChangeTrainerDataTypeStep(target_flags = TrainerDataType.MOVES | TrainerDataType.ITEMS | TrainerDataType.IV_EV_SET),
        GeneralEVStep(),
        GeneralIVStep(mode="ScalingIVs"),
        SetTrainerMovesStep()
        
    ])
    
    ctx.write_all()
    
    # Save modified ROM
    modified_rom_path = "hgeLanceCanary_gym_randomized.nds"
    with open(modified_rom_path, "wb") as f:
        s = rom.save()
        print(f"Writing {len(s)} bytes to {repr(modified_rom_path)} ...")
        f.write(s)

    print("Done")
    

        
