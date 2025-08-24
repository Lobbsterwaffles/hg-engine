from framework import *
from enums import Type, Split
from form_mapping import FormMapping


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
            "priority" / Int8sl,
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
            struct_fields.append("held_item" / Int16ul)
        
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
            "battleitems" / Array(4, Int16ul),
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

class Mons(NarcExtractor):
    """Extractor for Pokemon data from ROM with full mondata structure."""
    
    # BST overrides for Pokemon whose power level is not accurately represented by raw BST
    BST_OVERRIDES = {
        "Wishiwashi": 550, 
        "Shedinja": 400,    
        "Slaking": 550,     
        "Regigigas": 580,   
        "Archeops": 550,    
        ("Greninja", "BATTLE_BOND"): 600,
        ("Floette", "ETERNAL_FLOWER"): 551,
        ("Rotom", "WASH"): 520,
        ("Rotom", "HEAT"): 520,
        ("Rotom", "FROST"): 520,
        ("Rotom", "FAN"): 520,
        ("Rotom", "MOW"): 520,
        ("Calyrex", "ICE_RIDER"): 680,
        ("Calyrex", "SHADOW_RIDER"): 680,
        
    }
    
    def __init__(self, context):
        pokemon_names_step = context.get(LoadPokemonNamesStep)
        tm_hm_names = context.get(TMHM)
        form_mapping = context.get(FormMapping)
        
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
            "is_form_of" / Computed(lambda ctx: form_mapping.get_base_species(ctx._.narc_index)),
            "forms" / Computed(lambda ctx: form_mapping.get_all_forms(ctx._.narc_index) if form_mapping.get_base_species(ctx._.narc_index) is None else None),
            "form_category" / Computed(lambda ctx: form_mapping.get_form_category(ctx._.narc_index)),
            "form_number" / Computed(lambda ctx: form_mapping.form_to_base_lookup[ctx._.narc_index][1] if ctx._.narc_index in form_mapping.form_to_base_lookup else None),
            "original_name" / Computed(lambda ctx: pokemon_names_step.get_by_id(ctx._.narc_index)),
            "name" / Computed(lambda ctx: form_mapping.get_display_name(ctx._.narc_index, pokemon_names_step)),
            "pokemon_id" / Computed(lambda ctx: ctx._.narc_index)
        )
        
        super().__init__(context)
        
        self.data = self.load_narc()
    
    def _get_adjusted_bst(self, ctx):
        """Get adjusted BST for Pokemon, applying overrides for special cases."""
        # Get the Pokemon names and form mapping
        pokemon_names_step = self.context.get(LoadPokemonNamesStep)
        form_mapping = self.context.get(FormMapping)
        
        # Get both the original name and the form-aware display name
        original_name = pokemon_names_step.get_by_id(ctx._.narc_index)
        
        # Check for tuple-based form override first (e.g., ("Greninja", "BATTLE_BOND"))
        base_species_id = form_mapping.get_base_species(ctx._.narc_index)
        if base_species_id is not None:  # This is a form
            base_name = pokemon_names_step.get_by_id(base_species_id)
            form_name = form_mapping.form_names_lookup[ctx._.narc_index]
            form_tuple = (base_name, form_name)
            if form_tuple in self.BST_OVERRIDES:
                return self.BST_OVERRIDES[form_tuple]
        
        # Check for string-based override (display name like "Greninja-BATTLE_BOND")
        display_name = form_mapping.get_display_name(ctx._.narc_index, pokemon_names_step)
        if display_name in self.BST_OVERRIDES:
            return self.BST_OVERRIDES[display_name]
        
        # Then check for base Pokemon override (e.g., "Deoxys")
        if original_name in self.BST_OVERRIDES:
            return self.BST_OVERRIDES[original_name]
        
        # Default: return raw BST calculation
        return ctx.hp + ctx.attack + ctx.defense + ctx.speed + ctx.sp_attack + ctx.sp_defense
    
    
    def get_narc_path(self):
        return "a/0/0/2"
    
    def parse_file(self, file_data, index):
        return self.mondata_struct.parse(file_data, narc_index=index)
    
    def serialize_file(self, data, index):
        return self.mondata_struct.build(data, narc_index=index)
    
    def get(self, species_id):
        """
        Get Pokemon data by species ID, handling binary-packed form encoding.
        
        The species_id may be binary-packed with form information:
        - High 5 bits (bits 11-15): form number (0 for base Pokemon)
        - Low 11 bits (bits 0-10): base species ID
        
        Args:
            species_id: Integer species ID, possibly with form encoding
            
        Returns:
            Pokemon data object from the data array
            
        Raises:
            IndexError: If the resolved data index is out of bounds
            ValueError: If form mapping fails
        """
        # Use FormMapping to resolve the encoded species ID to actual data index
        form_mapping = self.context.get(FormMapping)
        data_index = form_mapping.resolve_data_index(species_id)
        
        # Bounds check
        if data_index >= len(self.data):
            raise IndexError(f"Data index {data_index} is out of bounds (max: {len(self.data) - 1})")
        
        return self.data[data_index]
    
    def __getitem__(self, species_id):
        """
        Support bracket notation for accessing Pokemon data.
        
        This delegates to the get() method to handle form encoding.
        
        Args:
            species_id: Integer species ID, possibly with form encoding
            
        Returns:
            Pokemon data object from the data array
        """
        return self.get(species_id)

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
            "starters" / Computed(lambda ctx: [mons[s] for s in ctx.starter_id])
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
    
    This class provides:
    - Lists of Pokemon that can benefit from Eviolite
    - Special MonData objects with modified stats for randomization integration
    - Helper methods to check if a Pokemon is an Eviolite user
    """
    
    # Eviolite item ID - used when assigning the item to Eviolite users
    EVIOLITE_ITEM_ID = 113
    
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
        
        # Create modified MonData objects for randomization integration
        self.eviolite_mondata = self._create_eviolite_mondata_objects()
        
        # Map from eviolite mondata objects to original pokemon objects
        self.eviolite_map = {eviolite_mon: original_mon 
                           for eviolite_mon, original_mon in 
                           zip(self.eviolite_mondata, self.eviolite_users)}
    
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
    
    def _create_eviolite_mondata_objects(self):
        """Create copies of MonData objects with adjusted Eviolite stats.
        
        These objects can be used in randomization alongside normal Pokemon.
        When assigned to trainers, the randomizer can check if a Pokemon is an
        Eviolite user by reference equality.
        
        Returns:
            list: List of MonData-like objects with Eviolite-adjusted stats
        """
        eviolite_mondata = []
        
        for pokemon in self.eviolite_users:
            # Create a copy of the original Pokemon object
            # We use a simple object() to avoid potential reference issues
            eviolite_mon = type('EvioliteMonData', (object,), {})()
            
            # Copy all attributes from original Pokemon
            for attr_name in dir(pokemon):
                if not attr_name.startswith('_') and not callable(getattr(pokemon, attr_name)):
                    setattr(eviolite_mon, attr_name, getattr(pokemon, attr_name))
            
            # Apply Eviolite stats
            eviolite_stats = pokemon._eviolite_analysis['eviolite_stats']
            eviolite_bst = pokemon._eviolite_analysis['eviolite_bst']
            
            # Update stats with Eviolite values
            eviolite_mon.defense = eviolite_stats['defense']
            eviolite_mon.sp_defense = eviolite_stats['sp_defense']
            eviolite_mon.bst = eviolite_bst
            
            # Mark this as an Eviolite MonData object and preserve original ID
            eviolite_mon.is_eviolite_user = True
            eviolite_mon.original_pokemon_id = pokemon.pokemon_id
            
            # Give Eviolite version a unique pokemon_id to avoid conflicts with original
            # Use a high offset (10000+) to ensure no conflicts with regular Pokemon IDs
            eviolite_mon.pokemon_id = 10000 + pokemon.pokemon_id
            
            # Modify the name to indicate it's an Eviolite user
            eviolite_mon.name = f"{pokemon.name} (Eviolite)"
            
            eviolite_mondata.append(eviolite_mon)
        
        return eviolite_mondata
    
    def is_eviolite_mondata(self, pokemon):
        """Check if a Pokemon is one of our special Eviolite MonData objects.
        
        Args:
            pokemon: A Pokemon object to check
            
        Returns:
            bool: True if this is an Eviolite MonData object, False otherwise
        """
        return pokemon in self.eviolite_mondata

