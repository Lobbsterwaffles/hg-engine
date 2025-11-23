# -*- coding: utf-8 -*-
import sys
import os


from abc import ABC, abstractmethod
from enums import *
from typing import List
from collections import Counter
import ndspy.rom
import ndspy.narc
import os
import re
import random
from construct import Struct, Int8ul, Int8sl, Int16ul, Int32ul, Array, Padding, Computed, this, Enum, FlagsEnum, RawCopy, Container, GreedyRange, StopIf, Check, BitsSwapped, Bitwise, Flag, Bytes

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
from type_mimics import type_mimics_data


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
    
    def decide(self, path, original, candidates, filter=NoFilter()):
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


#########################
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




    

        
