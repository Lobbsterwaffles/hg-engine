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
        moves = context.get(MoveDataExtractor).data

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

        self.struct_common = Struct(
            "ivs" / Int8ul,
            "abilityslot" / Int8ul,
            "level" / Int16ul,
            "species_id" / Int16ul,
        )
        
        self.trainer_pokemon_basic = self.struct_common + Struct(
            "ballseal" / Int16ul
        )
        
        self.struct_items = self.struct_common + Struct(
            "item" / Int16ul,
            "ballseal" / Int16ul
        )
        
        self.struct_moves = self.struct_common + Struct(
            "moves" / Array(4, Int16ul),
            "ballseal" / Int16ul
        )
        
        self.struct_movesitems = self.struct_common + Struct(
            "item" / Int16ul,
            "moves" / Array(4, Int16ul),
            "ballseal" / Int16ul
        )
        
        self.format_map = {
            bytes([TrainerDataType.NOTHING]): self.trainer_pokemon_basic,
            bytes([TrainerDataType.MOVES]): self.struct_moves,
            bytes([TrainerDataType.ITEMS]): self.struct_items,
            bytes([TrainerDataType.MOVES | TrainerDataType.ITEMS]): self.struct_movesitems,
        }
        
        super().__init__(context)
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/5/6"
    
    def parse_file(self, file_data, index):
        if len(file_data) == 0:
            return []
        
        trainer = self.context.get(TrainerData).data[index]
        struct = self.format_map[trainer.trainermontype.data]
        
        return Array(trainer.nummons, struct).parse(file_data)
    
    def serialize_file(self, data, index):
        if not data:
            return b''
        
        trainer = self.context.get(TrainerData).data[index]
        struct = self.format_map[trainer.trainermontype.data]
       

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
        self.names_step = context.get(LoadPokemonNamesStep)
        self.by_id = set()
        
        # Add all Pokémon in the list
        for name in self.pokemon_names:
            self.by_id.add(self.names_step.get_by_name(name))


class InvalidPokemon(PokemonListBase):
    """Handles invalid Pokémon entries (marked with dashes)."""
    
    def __init__(self, context):
        super().__init__(context)
        
        # Add any dashes (invalid Pokémon)
        for fid in self.names_step.get_all_by_name("-----"):
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
    
    def get_narc_path(self):
        return "a/0/3/4"
    
    def parse_file(self, file_data, index):
        return self.evolution_struct.parse(file_data, narc_index=index)
    
    def serialize_file(self, data, index):
        return self.evolution_struct.build(data, narc_index=index)


class RandomizeStartersStep(Step):
    """Randomization step that randomizes starter Pokemon choices."""
    
    def __init__(self, filter_obj=None):
        self.filter = filter_obj
    
    def run(self, context):
        """Execute starter randomization."""
        starter_extractor = context.get(StarterExtractor)
        
        # TODO: Implement starter randomization logic
        # For now, just log current starters
        current_names = [s.name for s in starter_extractor.data.starters]
        
        if context.verbosity_map.get(['RandomizeStartersStep']) >= 1:
            print(f"Current starters: {', '.join(current_names)}")


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
    """expand trainer teams to a specified size by adding Pokemon with similar BST to team average."""
    
    def __init__(self, target_size=6, bosses_only=False):
        if not (1 <= target_size <= 6):
            raise ValueError(f"bad size: {target_size}")
        self.target_size = target_size
        self.bosses_only = bosses_only
    
    def run(self, context):
        if self.bosses_only:
            # Only expand teams for trainers designated as bosses
            bosses = context.get(IdentifyBosses)
            boss_trainer_ids = set()
            
            # Collect all trainer IDs from all boss categories
            for boss_category in bosses.data.values():
                for trainer in boss_category.trainers:
                    boss_trainer_ids.add(trainer.info.trainer_id)
            
            # Only expand teams for boss trainers
            for t in context.get(Trainers).data:
                if t.info.trainer_id in boss_trainer_ids:
                    self._expand_trainer_team(context, t)
        else:
            # Original behavior: expand all trainer teams
            for t in context.get(Trainers).data:
                self._expand_trainer_team(context, t)
    
    def _expand_trainer_team(self, context, trainer):
        if trainer.info.nummons != len(trainer.team):
            raise RuntimeError(f"team size mismatch! {trainer.info.trainer_id}")

        current_size = len(trainer.team)
        
        if current_size >= self.target_size or current_size == 0:
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
        for _ in range(self.target_size - current_size):
            trainer.team.append(Container(template_pokemon))
        
        trainer.info.nummons = len(trainer.team)


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
                path=["trainer", trainer.info.name, "team", i, "species"],
                original=mondata.data[pokemon.species_id],
                candidates=list(mondata.data),
                filter=filter
            )
            pokemon.species_id = new_species.pokemon_id


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

    # Create filters for both gym and encounter randomization
    legendary_filters = (
        [NotInSet(ctx.get(LoadBlacklistStep).by_id),
        NotInSet(ctx.get(InvalidPokemon).by_id)] +
        
        ([] if args.allow_restricted else [NotInSet(ctx.get(RestrictedPokemon).by_id)]) +
        
        ([] if args.allow_mythical else [NotInSet(ctx.get(MythicalPokemon).by_id)]) +
        
        ([] if args.allow_ultra_beasts else [NotInSet(ctx.get(UltraBeastPokemon).by_id)]) +
        
        ([] if args.allow_paradox else [NotInSet(ctx.get(ParadoxPokemon).by_id)]) +
        
        ([] if args.allow_sublegendary else [NotInSet(ctx.get(SubLegendaryPokemon).by_id)])
    )
    
    gym_filter = AllFilters(legendary_filters + [BstWithinFactor(args.bst_factor)])
    encounter_filter = AllFilters(legendary_filters + [BstWithinFactor(args.bst_factor)])


    # Build pipeline steps
    pipeline_steps = [
        ExpandTrainerTeamsStep(bosses_only=args.expand_bosses_only),
        WildMult(multiplier=args.wild_level_mult),
        TrainerMult(multiplier=args.trainer_level_mult),
        RandomizeGymTypesStep(),
        RandomizeGymsStep(gym_filter),
        RandomizeEncountersStep(encounter_filter, args.independent_encounters)
    ]
    
    # Add starter randomization if requested
    if args.randomize_starters:
        pipeline_steps.append(RandomizeStartersStep())
    
    # Run randomization pipeline
    ctx.run_pipeline(pipeline_steps)
    
    ctx.write_all()
    
    # Save modified ROM
    modified_rom_path = "hgeLanceCanary_gym_randomized.nds"
    with open(modified_rom_path, "wb") as f:
        s = rom.save()
        print(f"Writing {len(s)} bytes to {repr(modified_rom_path)} ...")
        f.write(s)

    print("Done")
    

        
