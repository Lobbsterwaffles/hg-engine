import json
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


class Levelups(NarcExtractor):
    """Extractor for Pokemon level-up learnsets.
    
    New binary format (from build_learnsets.py):
    - Each entry is a 32-bit value: (level << 16) | move_id
    - Each Pokemon has exactly MAX_LEVELUP_MOVES (46) entries
    - Terminator/padding entries use 0x0000FFFF (move_id=0xFFFF, level=0)
    - Indexed by species ID
    """
    
    MAX_LEVELUP_MOVES = 46  # From generated learnsets.h
    
    def __init__(self, context):
        super().__init__(context)
        moves = context.get(Moves).data

        # New format: 32-bit packed entry (level << 16 | move_id)
        # We decode it into move_id and level for compatibility with existing code
        learnset_entry = Struct(
            "raw" / Int32ul,
            "move_id" / Computed(lambda ctx: ctx.raw & 0xFFFF),
            "level" / Computed(lambda ctx: (ctx.raw >> 16) & 0xFFFF),
            "move" / Computed(lambda ctx: moves[ctx.move_id] if ctx.move_id < len(moves) else None),
        )
        
        # Giant file structure: GreedyRange of Arrays (46 entries each)
        self.struct = GreedyRange(Array(self.MAX_LEVELUP_MOVES, learnset_entry))
        
        # Filter out terminator entries (move_id == 0xFFFF)
        self.data = [[e for e in s if e.move_id != 0xFFFF] for s in self.load_narc()]
    
    def get_narc_path(self):
        return "a/0/3/3"
    
    def parse_narc(self, narc_data):
        # Parse the first file as the giant learnset structure
        return self.struct.parse(narc_data.files[0])
    
    def serialize_narc(self, data):
        # Serialize back to a single-file NARC
        narc_data = ndspy.narc.NARC()
        narc_data.files = [self.struct.build(data)]
        return narc_data
    
    def parse_file(self, file_data, index):
        # Not used in new format, but required by abstract base class
        return []
    
    def serialize_file(self, data, index):
        # Not used in new format, but required by abstract base class
        return b''


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
        
        # Store original raw file data for files we can't fully parse (e.g., nummons=0)
        self._original_file_data = {}
        
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
        # Store original data for files we might not fully parse
        self._original_file_data[index] = file_data
        
        if len(file_data) == 0:
            return []
        
        trainer = self.context.get(TrainerData).data[index]
        struct = self._build_trainer_pokemon_struct(trainer.trainermontype.data)
        
        return Array(trainer.nummons, struct).parse(file_data)
    
    def serialize_file(self, data, index):
        
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
            Padding(3),  # endentry macro adds 3 bytes of padding
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

class Mons(Writeback, NarcExtractor):
    """Extractor for Pokemon data from ROM with full mondata structure."""
    
    
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
        "Diggersby" : 479,
        "Azumarill" : 470,
        "Medicham" : 470,
        
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
            "ability1" / Int16ul,  # 0x16-0x17 (halfword)
            "runchance" / Int8ul,  # 0x18
            "colorflip" / Int8ul,  # 0x19
            "ability2" / Int16ul,  # 0x1A-0x1B (halfword)
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
    """Extractor for TM/HM/TR data from machine_moves.json.
    
    Reads the pre-generated machine_moves.json file which maps item IDs to moves and types.
    This file is generated by scripts/update_machine_moves.py --export.
    
    Provides:
        - self.data: List of all machine move entries (dicts with item_id, move_type, etc.)
        - self.by_item_id: Dict mapping item_id -> entry
        - self.tms_by_type: Dict mapping Type enum -> list of TM item_ids of that type
    """
    def __init__(self, context):
        super().__init__(context)
        import json
        import os
        
        json_path = os.path.join(os.path.dirname(__file__), 'machine_moves.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        # Build lookup by item_id
        self.by_item_id = {entry['item_id']: entry for entry in self.data}
        
        # Build lookup by type (for gym TM matching)
        # Convert TYPE_* strings to Type enum values
        from enums import Type
        self.tms_by_type = {t: [] for t in Type}
        
        for entry in self.data:
            if entry['kind'] in ('TM', 'TR'):  # Only TMs and TRs, not HMs
                type_str = entry['move_type']  # e.g., "TYPE_FIRE"
                type_name = type_str.replace('TYPE_', '')  # e.g., "FIRE"
                try:
                    type_enum = Type[type_name]
                    self.tms_by_type[type_enum].append(entry['item_id'])
                except KeyError:
                    pass  # Unknown type, skip
        
        print(f"TMHM: Loaded {len(self.data)} machine moves from machine_moves.json", file=sys.stderr)
    
    def get_move_for_tm(self, tm_number, moves):
        """Get move data for a TM number.
        
        Args:
            tm_number: TM number (1-based)
            moves: Moves extractor instance
            
        Returns:
            Move data object or None if not found
        """
        for entry in self.data:
            if entry['kind'] == 'TM' and entry['number'] == tm_number:
                move_name = entry['move_name'].replace('MOVE_', '')
                for m in moves.data:
                    # Normalize both names: uppercase, replace spaces and hyphens with underscores
                    if m.name and m.name.upper().replace(' ', '_').replace('-', '_') == move_name:
                        return m
        return None
    
    def get_move_for_hm(self, hm_number, moves):
        """Get move data for an HM number.
        
        Args:
            hm_number: HM number (1-based)
            moves: Moves extractor instance
            
        Returns:
            Move data object or None if not found
        """
        for entry in self.data:
            if entry['kind'] == 'HM' and entry['number'] == hm_number:
                move_name = entry['move_name'].replace('MOVE_', '')
                for m in moves.data:
                    # Normalize both names: uppercase, replace spaces and hyphens with underscores
                    if m.name and m.name.upper().replace(' ', '_').replace('-', '_') == move_name:
                        return m
        return None


class ItemPool(Extractor):
    """Stateful item pool (deck of cards) for randomization.
    
    Manages a pool of items organized by rarity tier. When an item is drawn:
    - Regular items are returned to the deck and reshuffled
    - TMs/TRs are removed from the pool (one-time use)
    
    This ensures each TM appears at most once in the final ROM.
    
    Tiers: 1 (common), 2 (uncommon), 3 (rare), 4 (master)
    """
    
    def __init__(self, context):
        super().__init__(context)
        import os
        import random
        
        self.random = random
        self.tmhm = context.get(TMHM)
        
        # Load item pools from Ground_Item_Tier.csv
        # Format: item_name,rarity (common/uncommon/rare/master)
        self.pools = {
            1: [],  # common
            2: [],  # uncommon
            3: [],  # rare
            4: []   # master
        }
        
        # Map rarity names to tier numbers
        rarity_to_tier = {
            'common': 1,
            'uncommon': 2,
            'rare': 3,
            'master': 4
        }
        
        # Build item name to ID mapping
        from enums import Item
        self.item_name_to_id = {}
        for item in Item:
            readable_name = item.name.replace('_', ' ').title()
            self.item_name_to_id[readable_name] = item.value
            # Also map TM numbers
            if item.name.startswith('TM'):
                tm_num_str = item.name[2:]
                if tm_num_str.isdigit():
                    self.item_name_to_id[str(int(tm_num_str))] = item.value
        
        # Track all TM/TR item IDs for removal logic
        self.tm_item_ids = set(entry['item_id'] for entry in self.tmhm.data if entry['kind'] in ('TM', 'TR'))
        
        # Load items from CSV
        csv_path = os.path.join(os.path.dirname(__file__), 'Ground_Item_Tier.csv')
        with open(csv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) < 2:
                    continue
                item_name, rarity = parts[0], parts[1].lower()
                tier = rarity_to_tier.get(rarity)
                if tier is None:
                    continue
                
                try:
                    item_id = self._get_item_id(item_name)
                    self.pools[tier].append(item_id)
                except ValueError:
                    print(f"ItemPool: WARNING - Could not find item '{item_name}'", file=sys.stderr)
        
        # Shuffle all pools initially
        for tier in self.pools:
            self.random.shuffle(self.pools[tier])
        
        total = sum(len(p) for p in self.pools.values())
        print(f"ItemPool: Loaded {total} items across 4 tiers", file=sys.stderr)
    
    def _get_item_id(self, item_name):
        """Convert item name to ID."""
        # Handle bare numbers (TMs)
        if item_name.isdigit():
            return self.item_name_to_id[item_name]
        
        # Try various name formats
        variations = [
            item_name,
            item_name.title(),
            item_name.replace('_', ' ').title(),
        ]
        
        for var in variations:
            if var in self.item_name_to_id:
                return self.item_name_to_id[var]
        
        raise ValueError(f"Item '{item_name}' not found")
    
    def draw(self, tier, context=None, path=None):
        """Draw an item from the specified tier.
        
        Args:
            tier: 1-4 for rarity tier
            context: Optional RandomizationContext for deterministic selection
            path: Optional path for context.decide
            
        Returns:
            item_id of the drawn item
            
        If the pool for this tier is empty, falls back to adjacent tiers.
        TMs are removed from the pool after being drawn.
        Regular items are returned and reshuffled.
        """
        # Try the requested tier first, then expand to adjacent tiers
        tiers_to_try = [tier]
        if tier > 1:
            tiers_to_try.append(tier - 1)
        if tier < 4:
            tiers_to_try.append(tier + 1)
        # Add remaining tiers
        for t in [1, 2, 3, 4]:
            if t not in tiers_to_try:
                tiers_to_try.append(t)
        
        for try_tier in tiers_to_try:
            if self.pools[try_tier]:
                pool = self.pools[try_tier]
                
                # Use context.decide if available for determinism
                if context and path:
                    idx = context.decide(
                        path=path,
                        original=0,
                        candidates=list(range(len(pool))),
                        filter=NoFilter()
                    )
                else:
                    idx = self.random.randint(0, len(pool) - 1)
                
                item_id = pool[idx]
                
                # Remove TMs permanently, reshuffle regular items
                if item_id in self.tm_item_ids:
                    pool.pop(idx)
                else:
                    # Return to deck and shuffle
                    self.random.shuffle(pool)
                
                return item_id
        
        # All pools empty - shouldn't happen
        raise ValueError("All item pools are empty!")
    
    def draw_tm_by_type(self, type_enum, tier=None, context=None, path=None):
        """Draw a TM of a specific type, optionally filtered by tier.
        
        Args:
            type_enum: Type enum value to match
            tier: Optional tier to prefer (will expand +/- 1 if needed)
            context: Optional RandomizationContext for determinism
            path: Optional path for context.decide
            
        Returns:
            item_id of the drawn TM, or None if no matching TM available
        """
        # Get all TMs of this type that are still in the pool
        available_tms = []
        for t, pool in self.pools.items():
            for item_id in pool:
                if item_id in self.tm_item_ids:
                    # Check if this TM is of the requested type
                    entry = self.tmhm.by_item_id.get(item_id)
                    if entry:
                        type_str = entry['move_type']
                        type_name = type_str.replace('TYPE_', '')
                        from enums import Type
                        try:
                            tm_type = Type[type_name]
                            if tm_type == type_enum:
                                available_tms.append((t, item_id))
                        except KeyError:
                            pass
        
        if not available_tms:
            return None
        
        # If tier specified, prefer TMs from that tier or adjacent
        if tier is not None:
            # Sort by distance from preferred tier
            available_tms.sort(key=lambda x: abs(x[0] - tier))
        
        # Select from available
        if context and path:
            idx = context.decide(
                path=path,
                original=0,
                candidates=list(range(len(available_tms))),
                filter=NoFilter()
            )
        else:
            idx = self.random.randint(0, len(available_tms) - 1)
        
        selected_tier, item_id = available_tms[idx]
        
        # Remove from pool
        self.pools[selected_tier].remove(item_id)
        
        return item_id


class StarterExtractor(Writeback, Extractor):
    """Extractor for starter Pokemon data from ARM9 binary.
    
    Reads/writes the three starter species stored at address 0x02108514 in ARM9.
    """
    
    def __init__(self, context):
        super().__init__(context)
        mons = context.get(Mons)
        self.arm9_manager = context.get(ARM9Manager)
        
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
        """Write starter data back to ARM9 binary via ARM9Manager."""
        # Build just the starter data
        starter_bytes = self.starter_struct.build(self.data)
        
        # Register modification with ARM9Manager and apply immediately
        self.arm9_manager.register_modification(self.starter_offset, starter_bytes)
        self.arm9_manager.apply_modifications()


class ARM9Manager(Extractor):
    """Centralized manager for ARM9 binary modifications.
    
    Prevents conflicts between multiple extractors that need to modify ARM9.
    Collects all modifications and applies them atomically.
    """
    
    def __init__(self, context):
        super().__init__(context)
        self.modifications = {}  # offset -> bytes mapping
    
    def register_modification(self, offset, data):
        """Register a modification to be applied to ARM9 at the given offset."""
        if isinstance(data, bytes):
            self.modifications[offset] = data
        else:
            # Convert to bytes if needed
            self.modifications[offset] = bytes(data)
    
    def apply_modifications(self):
        """Apply all registered modifications to ARM9."""
        if not self.modifications:
            return
        
        arm9_data = bytearray(self.rom.arm9)
        
        for offset, data in self.modifications.items():
            arm9_data[offset:offset + len(data)] = data
        
        self.rom.arm9 = bytes(arm9_data)
        self.modifications.clear()
    
    def write(self):
        """Write method called by framework - applies all modifications."""
        self.apply_modifications()


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


class MachineLearnsets(Extractor):
    def __init__(self, context):
        super().__init__(context)
        
        mons = context.get(Mons)
        tmhm = context.get(TMHM)
        
        # Calculate bitfield size based on TMHM data (same as build_learnsets.py)
        # Count TMs and HMs from the new JSON-based TMHM extractor
        num_tms = sum(1 for entry in tmhm.data if entry['kind'] == 'TM')
        num_hms = sum(1 for entry in tmhm.data if entry['kind'] == 'HM')
        num_machine_moves = num_tms + num_hms
        print(f"Number of TMs: {num_tms}, Number of HMs: {num_hms}, Total machine moves: {num_machine_moves}", file=sys.stderr)  
        bitfield_word_count = (num_machine_moves + 31) // 32
        bitfield_bit_count = bitfield_word_count * 32
        
        narc_file_id = self.rom.filenames.idOf("a/0/2/8")
        narc_file = self.rom.files[narc_file_id]
        narc_data = ndspy.narc.NARC(narc_file)
        file_14_data = narc_data.files[14]
        print(f"File 14 size: {len(file_14_data)}")

        # Will crash naturally if size mismatch
        struct = Struct("pokemon_data" / Array(len(mons.data), 
            Struct("tm_bitmap" / BitsSwapped(Bitwise(Array(bitfield_bit_count, Flag))))
        ))
        
        parsed_data = struct.parse(file_14_data)
        self.data = [[None] + p.tm_bitmap for p in parsed_data.pokemon_data]
        
        # Store machine move counts for API methods
        self.num_tms = num_tms
        self.num_hms = num_hms
        self.num_machine_moves = num_machine_moves
        
    def can_learn_tm(self, species_id, tm_number):
        """Check if a Pokemon species can learn a specific TM.
        
        Args:
            species_id: Pokemon species ID (1-based, 1 = Bulbasaur)
            tm_number: TM number (1-based, 1 = TM01)
            
        Returns:
            bool: True if Pokemon can learn the TM
        """
        if species_id < 1 or species_id >= len(self.data):
            return False
        if tm_number < 1 or tm_number > self.num_tms:  # Dynamic TM count
            return False
            
        # Convert to 0-based indexing for internal array access
        machine_index = tm_number - 1  # TMs are 0-91 internally
        return self.data[species_id][machine_index + 1]  # +1 because data[0] is None
        
    def can_learn_hm(self, species_id, hm_number):
        """Check if a Pokemon species can learn a specific HM.
        
        Args:
            species_id: Pokemon species ID (1-based, 1 = Bulbasaur)
            hm_number: HM number (1-based, 1 = HM01)
            
        Returns:
            bool: True if Pokemon can learn the HM
        """
        if species_id < 1 or species_id >= len(self.data):
            return False
        if hm_number < 1 or hm_number > self.num_hms:  # Dynamic HM count
            return False
            
        # Convert to 0-based indexing for internal array access
        machine_index = self.num_tms + hm_number - 1  # HMs start after TMs
        return self.data[species_id][machine_index + 1]  # +1 because data[0] is None
        
    def get_learnable_tms(self, species_id):
        """Get list of TM numbers that a Pokemon species can learn.
        
        Args:
            species_id: Pokemon species ID (1-based, 1 = Bulbasaur)
            
        Returns:
            list: List of TM numbers (1-based) that the Pokemon can learn
        """
        if species_id < 1 or species_id >= len(self.data):
            return []
            
        learnable_tms = []
        for tm_num in range(1, self.num_tms + 1):  # Dynamic TM range
            if self.can_learn_tm(species_id, tm_num):
                learnable_tms.append(tm_num)
        return learnable_tms
        
    def get_learnable_hms(self, species_id):
        """Get list of HM numbers that a Pokemon species can learn.
        
        Args:
            species_id: Pokemon species ID (1-based, 1 = Bulbasaur)
            
        Returns:
            list: List of HM numbers (1-based) that the Pokemon can learn
        """
        if species_id < 1 or species_id >= len(self.data):
            return []
            
        learnable_hms = []
        for hm_num in range(1, self.num_hms + 1):  # Dynamic HM range
            if self.can_learn_hm(species_id, hm_num):
                learnable_hms.append(hm_num)
        return learnable_hms


class HiddenAbilityTable(NarcExtractor):
    """Extractor for hidden ability data from ROM."""
    
    def __init__(self, context):
        # Hidden ability data is stored as an array of 16-bit ability IDs
        # One entry per Pokemon species (indexed by species ID)
        self.hidden_ability_struct = Struct(
            "abilities" / GreedyRange(Int16ul)
        )
        
        super().__init__(context)
        # Load ONLY file 7 from the NARC (more efficient than parsing all files)
        narc_file_id = self.rom.filenames.idOf(self.get_narc_path())
        narc_file = self.rom.files[narc_file_id]
        narc_data = ndspy.narc.NARC(narc_file)
        
        # Parse only file 7 which contains the hidden ability table
        file_7_data = narc_data.files[7]
        parsed_data = self.hidden_ability_struct.parse(file_7_data)
        self.data = parsed_data.abilities
    
    def get_narc_path(self):
        return "a/0/2/8"
    
    def parse_file(self, file_data, index):
        return self.hidden_ability_struct.parse(file_data)
    
    def serialize_file(self, data, index):
        return self.hidden_ability_struct.build(data)
    
    def get_hidden_ability(self, species_id):
        """Get hidden ability ID for a Pokemon species.
        
        Args:
            species_id: Pokemon species ID (0-based index)
            
        Returns:
            int: Hidden ability ID, or 0 if no hidden ability
        """
        if species_id < 0 or species_id >= len(self.data):
            return 0
        return self.data[species_id]
    
    def has_hidden_ability(self, species_id):
        """Check if a Pokemon species has a hidden ability.
        
        Args:
            species_id: Pokemon species ID (0-based index)
            
        Returns:
            bool: True if Pokemon has a hidden ability (ability_id != 0)
        """
        return self.get_hidden_ability(species_id) != 0


class OverworldTags(Extractor):
    """Loads the species_id -> overworld_tag mapping from overworld_tags.json.
    
    This mapping is generated by parse_overworld_table.py from the source files.
    Used to update overworld sprites when randomizing static Pokemon.
    """
    
    def __init__(self, context):
        super().__init__(context)
        
        # Load the JSON mapping
        json_path = os.path.join(os.path.dirname(__file__), 'overworld_tags.json')
        with open(json_path, 'r') as f:
            entries = json.load(f)
        
        # Build species_id -> tag mapping
        self.species_to_tag = {}
        for entry in entries:
            self.species_to_tag[entry['species_id']] = entry['overworld_tag']
    
    def get_tag(self, species_id):
        """Get the overworld tag for a species ID.
        
        Args:
            species_id: Pokemon species ID
            
        Returns:
            int: Overworld tag, or None if not found
        """
        return self.species_to_tag.get(species_id)


class EventFiles(Writeback, NarcExtractor):
    """Extractor for event files (NARC a/0/3/2).
    
    Event files contain overworld entries that define NPCs and Pokemon sprites.
    Each overworld entry has an overlayTableEntry field that references the
    overworld sprite tag.
    
    Structure (per DSPRE EventFile.cs):
    - spawnable_count (uint32)
    - spawnables (0x14 bytes each)
    - overworld_count (uint32)
    - overworlds (0x20 bytes each)
    - warp_count (uint32)
    - warps (0x0C bytes each)
    - trigger_count (uint32)
    - triggers (0x10 bytes each)
    
    Each section has its own 4-byte count prefix.
    """
    
    SPAWNABLE_SIZE = 0x14  # 20 bytes
    OVERWORLD_SIZE = 0x20  # 32 bytes
    WARP_SIZE = 0x0C       # 12 bytes
    TRIGGER_SIZE = 0x10    # 16 bytes
    
    def __init__(self, context):
        super().__init__(context)
        
        # Overworld entry structure (32 bytes) based on DSPRE's EventFile.cs
        self.overworld_struct = Struct(
            "ow_id" / Int16ul,              # 0x00: Overworld ID
            "overlay_table_entry" / Int16ul, # 0x02: Sprite tag (overlayTableEntry)
            "movement" / Int16ul,            # 0x04: Movement type
            "type" / Int16ul,                # 0x06: Type
            "flag" / Int16ul,                # 0x08: Flag
            "script_id" / Int16ul,           # 0x0A: Script ID
            "flag_id" / Int16ul,             # 0x0C: Flag ID
            "x_range" / Int16ul,             # 0x0E: X range
            "y_range" / Int16ul,             # 0x10: Y range
            "z_range" / Int16ul,             # 0x12: Z range
            "x_pos" / Int16ul,               # 0x14: X position
            "y_pos" / Int16ul,               # 0x16: Y position
            "z_pos" / Int32ul,               # 0x18: Z position
            "facing" / Int16ul,              # 0x1C: Facing direction
            "sight_range" / Int16ul,         # 0x1E: Sight range
        )
        
        self.data = self.load_narc()
    
    def get_narc_path(self):
        return "a/0/3/2"
    
    def parse_file(self, file_data, file_index):
        """Parse an event file into its components."""
        if len(file_data) < 4:
            return {'spawnables_raw': b'', 'overworlds': [], 
                    'warps_raw': b'', 'triggers_raw': b'',
                    'spawnable_count': 0, 'overworld_count': 0, 'warp_count': 0, 'trigger_count': 0}
        
        offset = 0
        
        # Read spawnable count (uint32) and spawnables
        spawnable_count = int.from_bytes(file_data[offset:offset+4], 'little')
        offset += 4
        spawnables_raw = file_data[offset:offset + spawnable_count * self.SPAWNABLE_SIZE]
        offset += spawnable_count * self.SPAWNABLE_SIZE
        
        # Read overworld count (uint32) and overworlds
        overworld_count = int.from_bytes(file_data[offset:offset+4], 'little')
        offset += 4
        overworlds = []
        for i in range(overworld_count):
            ow_data = file_data[offset:offset + self.OVERWORLD_SIZE]
            if len(ow_data) == self.OVERWORLD_SIZE:
                overworlds.append(self.overworld_struct.parse(ow_data))
            offset += self.OVERWORLD_SIZE
        
        # Read warp count (uint32) and warps
        warp_count = int.from_bytes(file_data[offset:offset+4], 'little')
        offset += 4
        warps_raw = file_data[offset:offset + warp_count * self.WARP_SIZE]
        offset += warp_count * self.WARP_SIZE
        
        # Read trigger count (uint32) and triggers
        trigger_count = int.from_bytes(file_data[offset:offset+4], 'little')
        offset += 4
        triggers_raw = file_data[offset:offset + trigger_count * self.TRIGGER_SIZE]
        
        return {
            'spawnable_count': spawnable_count,
            'overworld_count': overworld_count,
            'warp_count': warp_count,
            'trigger_count': trigger_count,
            'spawnables_raw': spawnables_raw,
            'overworlds': overworlds,
            'warps_raw': warps_raw,
            'triggers_raw': triggers_raw,
        }
    
    def serialize_file(self, data, index):
        """Serialize an event file back to bytes."""
        result = bytearray()
        
        # Spawnable count + spawnables
        result.extend(data['spawnable_count'].to_bytes(4, 'little'))
        result.extend(data['spawnables_raw'])
        
        # Overworld count + overworlds
        result.extend(len(data['overworlds']).to_bytes(4, 'little'))
        for ow in data['overworlds']:
            result.extend(self.overworld_struct.build(ow))
        
        # Warp count + warps
        result.extend(data['warp_count'].to_bytes(4, 'little'))
        result.extend(data['warps_raw'])
        
        # Trigger count + triggers
        result.extend(data['trigger_count'].to_bytes(4, 'little'))
        result.extend(data['triggers_raw'])
        
        return bytes(result)
    
    def get_overworlds(self, file_index):
        """Get all overworld entries for a specific event file."""
        if file_index < 0 or file_index >= len(self.data):
            return []
        return self.data[file_index].get('overworlds', [])
    
    def set_overworld_tag(self, file_index, overworld_index, new_tag):
        """Set the overlay_table_entry (sprite tag) for an overworld.
        
        Args:
            file_index: Event file index
            overworld_index: Index of overworld within the file
            new_tag: New sprite tag value
        """
        if file_index < 0 or file_index >= len(self.data):
            return False
        
        overworlds = self.data[file_index].get('overworlds', [])
        if overworld_index < 0 or overworld_index >= len(overworlds):
            return False
        
        overworlds[overworld_index].overlay_table_entry = new_tag
        return True
