import sys
from framework import *


class ScriptNarc(Writeback, NarcExtractor):
    """Shared extractor for script NARC a/0/1/2.
    
    All extractors that modify this NARC should use this shared instance
    to avoid overwriting each other's changes.
    """
    
    def __init__(self, context):
        super().__init__(context)
        self.data = self.load_narc()
        print(f"ScriptNarc: Loaded {len(self.data)} script files", file=sys.stderr)
    
    def get_narc_path(self):
        return "a/0/1/2"
    
    def parse_file(self, file_data, index):
        return file_data  # Keep as raw bytes
    
    def serialize_file(self, data, index):
        return data


class GiftPokemon(Extractor):
    """Extractor for GivePokemon script commands in NARC a/0/1/2
    
    Finds all GivePokemon (0x0089) commands across all script files.
    Uses construct library for parsing/serializing the command structure.
    
    Command structure (14 bytes total):
        - Command ID: 0x0089 (2 bytes)
        - Pokemon ID: 2 bytes (little-endian)
        - Level: 2 bytes
        - Held Item: 2 bytes
        - Form: 2 bytes
        - Ability: 2 bytes (ability slot)
        - Result Variable: 2 bytes (0x8000+ range, stores success/failure)
    
    Usage:
        gift_pokemon = context.get(GiftPokemon)
        for gift in gift_pokemon.gifts:
            print(f"File {gift.file_index}: {gift.pokemon_id} at level {gift.level}")
            gift.pokemon_id = 25  # Change to Pikachu
    """
    
    COMMAND_ID = 0x0089  # GivePokemon command
    COMMAND_SIZE = 14    # 2 (cmd) + 12 (6 params * 2 bytes each)
    
    def __init__(self, context):
        super().__init__(context)
        
        # Define the GivePokemon command structure using construct
        self.gift_struct = Struct(
            "command_id" / Int16ul,      # Should be 0x0089
            "pokemon_id" / Int16ul,       # Species ID
            "level" / Int16ul,            # Pokemon level
            "item" / Int16ul,             # Held item ID
            "form" / Int16ul,             # Form number
            "ability" / Int16ul,          # Ability slot
            "result_var" / Int16ul        # Script variable for result
        )
        
        # Use shared ScriptNarc instead of loading our own copy
        self.script_narc = context.get(ScriptNarc)
        self.data = self.script_narc.data  # Reference to shared data
        self.gifts = self._find_all_gifts()
        print(f"Found {len(self.gifts)} GivePokemon commands", file=sys.stderr)
    
    def _find_all_gifts(self):
        """Scan all script files for GivePokemon commands.
        
        Returns list of construct Containers with file_index and offset added.
        """
        gifts = []
        
        for file_idx, file_data in enumerate(self.data):
            if len(file_data) < self.COMMAND_SIZE:
                continue
            
            # Scan for command pattern (0x0089 as little-endian)
            for offset in range(len(file_data) - self.COMMAND_SIZE + 1):
                if file_data[offset] == 0x89 and file_data[offset + 1] == 0x00:
                    # Parse using construct
                    try:
                        parsed = self.gift_struct.parse(file_data[offset:offset + self.COMMAND_SIZE])
                    except Exception:
                        continue
                    
                    # Validate: result_var should be in 0x8000+ range (script variable)
                    # and pokemon/level should be reasonable
                    if (parsed.result_var >= 0x8000 and 
                        1 <= parsed.pokemon_id <= 700 and 
                        1 <= parsed.level <= 100):
                        
                        # Add location metadata to the Container
                        parsed.file_index = file_idx
                        parsed.offset = offset
                        gifts.append(parsed)
        
        return gifts
    
    def apply_changes(self):
        """Apply gift changes to shared ScriptNarc data."""
        for gift in self.gifts:
            command_bytes = self.gift_struct.build(gift)
            file_data = bytearray(self.data[gift.file_index])
            file_data[gift.offset:gift.offset + len(command_bytes)] = command_bytes
            self.data[gift.file_index] = bytes(file_data)


class WildBattle(Extractor):
    """Extractor for WildBattle script commands in NARC a/0/1/2
    
    Finds all WildBattle (0x00F9) commands across all script files.
    These are static/scripted wild encounters (e.g., Lapras in Union Cave).
    Also finds associated PlayCry (0x004C) commands within 20 bytes before.
    
    Command structure (6 bytes total):
        - Command ID: 0x00F9 (2 bytes)
        - Pokemon ID: 2 bytes (little-endian)
        - Level: 2 bytes
    
    PlayCry structure (6 bytes total):
        - Command ID: 0x004C (2 bytes)
        - Pokemon ID: 2 bytes (little-endian)
        - Unused: 2 bytes
    
    Usage:
        wild_battles = context.get(WildBattle)
        for battle in wild_battles.battles:
            print(f"File {battle.file_index}: {battle.pokemon_id} at level {battle.level}")
            battle.pokemon_id = 132  # Change to Ditto
            # If battle.playcry_offset is not None, the cry will also be updated
    """
    
    COMMAND_ID = 0x00F9  # WildBattle command
    COMMAND_SIZE = 6     # 2 (cmd) + 4 (2 params * 2 bytes each)
    PLAYCRY_CMD = 0x004C
    PLAYCRY_DISTANCES = [12, 17]  # Known distances between PlayCry and WildBattle
    
    def __init__(self, context):
        super().__init__(context)
        
        self.battle_struct = Struct(
            "command_id" / Int16ul,      # Should be 0x00F9
            "pokemon_id" / Int16ul,       # Species ID
            "level" / Int16ul,            # Pokemon level
        )
        
        # Use shared ScriptNarc
        self.script_narc = context.get(ScriptNarc)
        self.data = self.script_narc.data
        self.battles = self._find_all_battles()
        print(f"Found {len(self.battles)} WildBattle commands", file=sys.stderr)
    
    def _find_playcry_before(self, file_data, wildbattle_offset):
        """Search for PlayCry command at exactly 12 or 17 bytes before WildBattle."""
        for dist in self.PLAYCRY_DISTANCES:
            search_offset = wildbattle_offset - dist
            if search_offset >= 0 and search_offset + 1 < len(file_data):
                if file_data[search_offset] == 0x4C and file_data[search_offset + 1] == 0x00:
                    return search_offset
        return None
    
    def _find_all_battles(self):
        """Scan all script files for WildBattle commands."""
        battles = []
        
        for file_idx, file_data in enumerate(self.data):
            if len(file_data) < self.COMMAND_SIZE:
                continue
            
            # Scan for command pattern (0x00F9 as little-endian)
            for offset in range(len(file_data) - self.COMMAND_SIZE + 1):
                if file_data[offset] == 0xF9 and file_data[offset + 1] == 0x00:
                    try:
                        parsed = self.battle_struct.parse(file_data[offset:offset + self.COMMAND_SIZE])
                    except Exception:
                        continue
                    
                    # Validate: pokemon/level should be reasonable
                    if 1 <= parsed.pokemon_id <= 2000 and 1 <= parsed.level <= 100:
                        parsed.file_index = file_idx
                        parsed.offset = offset
                        # Find associated PlayCry command
                        parsed.playcry_offset = self._find_playcry_before(file_data, offset)
                        battles.append(parsed)
        
        return battles
    
    def apply_changes(self):
        """Apply battle changes to shared ScriptNarc data."""
        for battle in self.battles:
            file_data = bytearray(self.data[battle.file_index])
            
            # Write WildBattle command
            command_bytes = self.battle_struct.build(battle)
            file_data[battle.offset:battle.offset + len(command_bytes)] = command_bytes
            
            # Write PlayCry species if present (use base species for forms)
            if battle.playcry_offset is not None:
                base_species = battle.pokemon_id & 0x7FF
                file_data[battle.playcry_offset + 2] = base_species & 0xFF
                file_data[battle.playcry_offset + 3] = (base_species >> 8) & 0xFF
            
            self.data[battle.file_index] = bytes(file_data)


class GiftEggs(Extractor):
    """Extractor for GivePokemonEgg script commands in NARC a/0/1/2
    
    Uses a whitelist of known egg locations from the base ROM.
    
    Command structure (6 bytes total):
        - Command ID: 0x008A (2 bytes)
        - Pokemon ID: 2 bytes (little-endian)
        - Location: 2 bytes (text slot at text bank #281)
    
    Known eggs in HGSS:
        - File 858: Togepi egg (species 175, location 0) - Mr. Pokemon
        - File 860: Mareep egg (species 179, location 1) - Primo
    
    Usage:
        gift_eggs = context.get(GiftEggs)
        for egg in gift_eggs.eggs:
            print(f"File {egg.file_index}: {egg.pokemon_id}")
            egg.pokemon_id = 25  # Change to Pikachu egg
    """
    
    COMMAND_ID = 0x008A  # GivePokemonEgg command
    COMMAND_SIZE = 6     # 2 (cmd) + 4 (2 params * 2 bytes each)
    
    # Known egg locations: (file_index, pokemon_id, location)
    # These are the base ROM values used to locate the commands
    KNOWN_EGGS = [
        (858, 175, 13),  # Togepi from Mr. Pokemon
        (860, 179, 14),  # Mareep from Primo
    ]
    
    def __init__(self, context):
        super().__init__(context)
        
        # Define the GivePokemonEgg command structure using construct
        self.egg_struct = Struct(
            "command_id" / Int16ul,      # Should be 0x008A
            "pokemon_id" / Int16ul,       # Species ID
            "location" / Int16ul,         # Location text slot
        )
        
        # Use shared ScriptNarc instead of loading our own copy
        self.script_narc = context.get(ScriptNarc)
        self.data = self.script_narc.data  # Reference to shared data
        self.eggs = self._find_all_eggs()
        print(f"Found {len(self.eggs)} GivePokemonEgg commands", file=sys.stderr)
    
    def _find_all_eggs(self):
        """Find GivePokemonEgg commands at known locations.
        
        Returns list of construct Containers with file_index and offset added.
        """
        eggs = []
        
        for file_idx, base_pokemon_id, base_location in self.KNOWN_EGGS:
            if file_idx >= len(self.data):
                print(f"GiftEggs: File {file_idx} not found in NARC", file=sys.stderr)
                continue
            
            file_data = self.data[file_idx]
            if len(file_data) < self.COMMAND_SIZE:
                continue
            
            # Scan for command pattern (0x008A as little-endian) with matching location
            for offset in range(len(file_data) - self.COMMAND_SIZE + 1):
                if file_data[offset] == 0x8A and file_data[offset + 1] == 0x00:
                    try:
                        parsed = self.egg_struct.parse(file_data[offset:offset + self.COMMAND_SIZE])
                    except Exception:
                        continue
                    
                    # Match by location field (stable across randomization)
                    if parsed.location == base_location:
                        parsed.file_index = file_idx
                        parsed.offset = offset
                        eggs.append(parsed)
                        print(f"GiftEggs: Found egg in file {file_idx} at offset 0x{offset:04X}: species={parsed.pokemon_id}, location={parsed.location}", file=sys.stderr)
                        break  # Only one egg per known location
        
        return eggs
    
    def apply_changes(self):
        """Apply egg changes to shared ScriptNarc data."""
        for egg in self.eggs:
            command_bytes = self.egg_struct.build(egg)
            file_data = bytearray(self.data[egg.file_index])
            file_data[egg.offset:egg.offset + len(command_bytes)] = command_bytes
            self.data[egg.file_index] = bytes(file_data)


class ShinyGyarados(Extractor):
    """Extractor for the Shiny Gyarados encounter at Lake of Rage.
    
    This is a special WildBattleSp command (0x024D) in file 938 at offset 0x0098.
    
    Command structure (7 bytes total):
        - Command ID: 0x024D (2 bytes)
        - Pokemon ID: 2 bytes (little-endian)
        - Level: 2 bytes
        - Shiny Flag: 1 byte (1 = shiny)
    
    Also tracks associated PlayCry command at 17 bytes before.
    """
    
    FILE_INDEX = 938
    COMMAND_OFFSET = 0x0098  # Known offset of WildBattleSp in file 938
    PLAYCRY_OFFSET = 0x0087  # PlayCry is 17 bytes before (0x0098 - 17 = 0x0087)
    
    def __init__(self, context):
        super().__init__(context)
        
        self.battle_struct = Struct(
            "command_id" / Int16ul,      # Should be 0x024D
            "pokemon_id" / Int16ul,       # Species ID
            "level" / Int16ul,            # Pokemon level
            "shiny" / Int8ul,             # Shiny flag (1 = shiny)
        )
        
        # Use shared ScriptNarc
        self.script_narc = context.get(ScriptNarc)
        self.data = self.script_narc.data
        self.encounter = self._parse_encounter()
        print(f"ShinyGyarados: Found encounter with species={self.encounter.pokemon_id}, level={self.encounter.level}, shiny={self.encounter.shiny}", file=sys.stderr)
    
    def _parse_encounter(self):
        """Parse the Shiny Gyarados encounter from file 938."""
        file_data = self.data[self.FILE_INDEX]
        parsed = self.battle_struct.parse(file_data[self.COMMAND_OFFSET:self.COMMAND_OFFSET + 7])
        parsed.file_index = self.FILE_INDEX
        parsed.offset = self.COMMAND_OFFSET
        parsed.playcry_offset = self.PLAYCRY_OFFSET
        return parsed
    
    def apply_changes(self):
        """Apply encounter changes to shared ScriptNarc data."""
        file_data = bytearray(self.data[self.FILE_INDEX])
        
        # Write WildBattleSp command
        command_bytes = self.battle_struct.build(self.encounter)
        file_data[self.COMMAND_OFFSET:self.COMMAND_OFFSET + len(command_bytes)] = command_bytes
        
        # Write PlayCry species (use base species for forms)
        base_species = self.encounter.pokemon_id & 0x7FF
        file_data[self.PLAYCRY_OFFSET + 2] = base_species & 0xFF
        file_data[self.PLAYCRY_OFFSET + 3] = (base_species >> 8) & 0xFF
        
        self.data[self.FILE_INDEX] = bytes(file_data)


class NpcGiftItems(Extractor):
    """Extractor for NPC gift items based on gifttiers.csv.
    
    NPC gift items use SetVar commands:
        SetVar 0x8004 <item_id>   (6 bytes: 0x0029 + var + value)
        SetVar 0x8005 <quantity>  (6 bytes: 0x0029 + var + value)
    
    The item ID is at offset +4 from the first SetVar command.
    We locate gifts by searching for the expected item_id from gifttiers.csv
    in the specified script file.
    
    gifttiers.csv format: script_file, item_id, gift_class, tier
    """
    
    SETVAR_CMD = 0x0029
    VAR_ITEM = 0x8004
    VAR_QUANTITY = 0x8005
    
    def __init__(self, context):
        super().__init__(context)
        
        # Use shared ScriptNarc
        self.script_narc = context.get(ScriptNarc)
        self.data = self.script_narc.data
        self.gifts = self._load_gifts_from_csv()
        print(f"NpcGiftItems: Found {len(self.gifts)} gift items from gifttiers.csv", file=sys.stderr)
    
    def _load_gifts_from_csv(self):
        """Load gift item locations from gifttiers.csv and find their offsets."""
        import os
        
        gifts = []
        seen = set()  # Track (file_index, item_id) to avoid duplicates
        csv_path = os.path.join(os.path.dirname(__file__), 'gifttiers.csv')
        
        with open(csv_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(',')
                if len(parts) < 4:
                    continue
                
                try:
                    file_index = int(parts[0])
                    item_id = int(parts[1])
                    gift_class = parts[2]
                    tier = int(parts[3])
                except ValueError:
                    continue
                
                # Skip duplicates (same file and item_id)
                key = (file_index, item_id)
                if key in seen:
                    continue
                seen.add(key)
                
                # Find ALL SetVar patterns in the file (for branching paths)
                offsets = self._find_all_gift_offsets(file_index, item_id)
                
                if offsets:
                    gifts.append({
                        'file_index': file_index,
                        'item_id': item_id,
                        'gift_class': gift_class,
                        'tier': tier,
                        'offsets': offsets,  # List of offsets for all instances
                        'line_num': line_num
                    })
                else:
                    print(f"NpcGiftItems: WARNING - Could not find item {item_id} in file {file_index} (line {line_num})", file=sys.stderr)
        
        return gifts
    
    def _find_all_gift_offsets(self, file_index, expected_item_id):
        """Find ALL offsets of a gift item's SetVar command in a script file.
        
        Searches for pattern: SetVar(0x8004, item_id) followed by SetVar(0x8005, quantity)
        Returns list of offsets of the item_id value (SetVar command offset + 4).
        
        Multiple offsets can exist due to branching paths in the script.
        """
        if file_index >= len(self.data):
            return []
        
        file_data = self.data[file_index]
        offsets = []
        
        # Search for SetVar 0x8004 with the expected item_id
        for offset in range(len(file_data) - 12):  # Need at least 12 bytes for both SetVars
            # Check for SetVar command (0x0029)
            if file_data[offset] != 0x29 or file_data[offset + 1] != 0x00:
                continue
            
            # Check for var 0x8004
            var = file_data[offset + 2] | (file_data[offset + 3] << 8)
            if var != self.VAR_ITEM:
                continue
            
            # Check item_id matches
            item_id = file_data[offset + 4] | (file_data[offset + 5] << 8)
            if item_id != expected_item_id:
                continue
            
            # Verify next command is SetVar 0x8005 (quantity)
            next_offset = offset + 6
            if next_offset + 6 > len(file_data):
                continue
            
            if file_data[next_offset] != 0x29 or file_data[next_offset + 1] != 0x00:
                continue
            
            next_var = file_data[next_offset + 2] | (file_data[next_offset + 3] << 8)
            if next_var != self.VAR_QUANTITY:
                continue
            
            # Found the pattern - add offset of item_id value
            offsets.append(offset + 4)
        
        return offsets
    
    def apply_changes(self):
        """Apply gift item changes to shared ScriptNarc data."""
        for gift in self.gifts:
            file_data = bytearray(self.data[gift['file_index']])
            
            # Write item_id at ALL stored offsets (for branching paths)
            for offset in gift['offsets']:
                file_data[offset] = gift['item_id'] & 0xFF
                file_data[offset + 1] = (gift['item_id'] >> 8) & 0xFF
            
            self.data[gift['file_index']] = bytes(file_data)


class ItemScript(Extractor):
    """Extractor for ground item scripts in file 141 of NARC a/0/1/2.
    
    Ground items use SetVar commands:
        SetVar 0x8008 <item_id>   (6 bytes: 0x0029 + var + value)
        SetVar 0x8009 <quantity>  (6 bytes: 0x0029 + var + value)
        CommonScript 2033
    
    File 141 contains 594 scripts total:
    - First 593 are item scripts (some at the end are unused buffer)
    - 594th is common script invocation (ignored)
    
    Scans for all SetVar 0x8008 patterns and stores their offsets.
    Slots are indexed in order of appearance in the file.
    """
    
    ITEMSCRIPT_FILE = 141
    SETVAR_CMD = 0x0029
    VAR_ITEM = 0x8008      # Item ID variable for ground items
    VAR_QUANTITY = 0x8009  # Quantity variable for ground items
    NUM_ITEM_SCRIPTS = 593 # First 593 scripts are items, 594th is common script
    
    def __init__(self, context):
        super().__init__(context)
        
        # Use shared ScriptNarc
        self.script_narc = context.get(ScriptNarc)
        self.data = self.script_narc.data
        
        # Find all item slots in file 141
        self.slots = self._find_all_item_slots()
        print(f"ItemScript: Found {len(self.slots)} item slots in file 141", file=sys.stderr)
    
    def _find_all_item_slots(self):
        """Find all SetVar 0x8004 patterns in file 141.
        
        Returns list of dicts with 'offset' (of item_id value) and 'item_id'.
        """
        file_data = self.data[self.ITEMSCRIPT_FILE]
        slots = []
        
        # Search for SetVar 0x8004 followed by SetVar 0x8005
        for offset in range(len(file_data) - 12):
            # Check for SetVar command (0x0029)
            if file_data[offset] != 0x29 or file_data[offset + 1] != 0x00:
                continue
            
            # Check for var 0x8004
            var = file_data[offset + 2] | (file_data[offset + 3] << 8)
            if var != self.VAR_ITEM:
                continue
            
            # Get item_id
            item_id = file_data[offset + 4] | (file_data[offset + 5] << 8)
            
            # Verify next command is SetVar 0x8005 (quantity)
            next_offset = offset + 6
            if next_offset + 6 > len(file_data):
                continue
            
            if file_data[next_offset] != 0x29 or file_data[next_offset + 1] != 0x00:
                continue
            
            next_var = file_data[next_offset + 2] | (file_data[next_offset + 3] << 8)
            if next_var != self.VAR_QUANTITY:
                continue
            
            # Found valid item slot - store offset of item_id value
            slots.append({
                'offset': offset + 4,
                'item_id': item_id
            })
        
        return slots
    
    def apply_changes(self):
        """Apply item changes to shared ScriptNarc data."""
        file_data = bytearray(self.data[self.ITEMSCRIPT_FILE])
        
        for slot in self.slots:
            offset = slot['offset']
            item_id = slot['item_id']
            file_data[offset] = item_id & 0xFF
            file_data[offset + 1] = (item_id >> 8) & 0xFF
        
        self.data[self.ITEMSCRIPT_FILE] = bytes(file_data)


class OopsAllMasterBall(Step):
    """Changes all item IDs in the item script to Master Ball (item ID 1)"""
    
    def run(self, context):
        item_script = context.get(ItemScript)
        
        # Set all item slots to Master Ball (item ID 1)
        for slot in item_script.slots:
            slot['item_id'] = 1
        
        item_script.apply_changes()


class RandomizeGroundItems(Step):
    """Randomizes ground items based on area tiers using the shared ItemPool.
    
    Uses the ItemPool extractor to ensure TMs are only given once across
    all item sources (ground items, gift items, etc.).
    """
    
    def __init__(self):
        # Area-based tier selection probabilities: [Tier1, Tier2, Tier3, Tier4]
        # These determine which tier to draw from based on area tier
        self.area_probabilities = {
            1: [30, 45, 20, 5],
            2: [0, 50, 35, 15], 
            3: [0, 20, 50, 30],
            4: [0, 0, 55, 45]
        }
        
        # Load slot tier mapping
        self.slot_to_area = self._load_slot_tier_mapping()
        
        # Load junk items for hidden slots (these don't use ItemPool)
        self.junk_items = self._load_junk_items()
    
    def _load_slot_tier_mapping(self):
        """Load Item_Slot_tier.csv to map item slots to tiers/categories"""
        import os
        
        slot_to_tier = {}
        csv_path = os.path.join(os.path.dirname(__file__), 'Item_Slot_tier.csv')
        with open(csv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    slot, tier = line.split(',')
                    try:
                        slot_to_tier[int(slot)] = int(tier)
                    except ValueError:
                        slot_to_tier[int(slot)] = tier  # Berry, Cache, hidden
        return slot_to_tier
    
    def _load_junk_items(self):
        """Load junk items from Ground_Item_Tier.csv for hidden slots."""
        import os
        from enums import Item
        
        junk_ids = []
        name_to_id = {item.name.replace('_', ' ').title(): item.value for item in Item}
        
        csv_path = os.path.join(os.path.dirname(__file__), 'Ground_Item_Tier.csv')
        with open(csv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(',')
                    if len(parts) >= 2 and parts[1].lower() == 'junk':
                        item_name = parts[0]
                        # Try to find item ID
                        for var in [item_name, item_name.title(), item_name.replace('_', ' ').title()]:
                            if var in name_to_id:
                                junk_ids.append(name_to_id[var])
                                break
        return junk_ids
    
    def _select_tier_for_area(self, area, context, path):
        """Select a tier based on area probabilities using context.decide."""
        probabilities = self.area_probabilities[area]
        
        # Build weighted candidates
        candidates = []
        for tier_idx, prob in enumerate(probabilities):
            candidates.extend([tier_idx + 1] * prob)  # tier 1-4
        
        if not candidates:
            return 4  # Fallback to master tier
        
        # Use context.decide for determinism
        selected = context.decide(
            path=path + ["tier_selection"],
            original=candidates[0],
            candidates=candidates,
            filter=NoFilter()
        )
        return selected
    
    def run(self, context):
        import random
        from extractors import ItemPool
        
        item_script = context.get(ItemScript)
        item_pool = context.get(ItemPool)
        
        print(f"Processing {len(item_script.slots)} item slots...")
        
        ground_count = 0
        hidden_count = 0
        skipped_berry = 0
        skipped_cache = 0
        
        for i, slot in enumerate(item_script.slots):
            if i not in self.slot_to_area:
                raise ValueError(f"Slot {i} not found in Item_Slot_tier.csv")
            
            tier = self.slot_to_area[i]
            
            # Skip Berry and Cache slots
            if tier == 'Berry':
                skipped_berry += 1
                continue
            if tier == 'Cache':
                skipped_cache += 1
                continue
            
            # Handle hidden items - assign random junk item (not from ItemPool)
            if tier == 'hidden':
                if not self.junk_items:
                    raise ValueError("No junk items found")
                selected_item_id = random.choice(self.junk_items)
                slot['item_id'] = selected_item_id
                hidden_count += 1
                continue
            
            # Handle ground items (tiers 1-4) using ItemPool
            selected_tier = self._select_tier_for_area(tier, context, ["ground_item", f"slot_{i}"])
            
            selected_item_id = item_pool.draw(
                selected_tier,
                context=context,
                path=["ground_item", f"slot_{i}", "item"]
            )
            
            slot['item_id'] = selected_item_id
            ground_count += 1
        
        print(f"RandomizeGroundItems: {ground_count} ground, {hidden_count} hidden, {skipped_berry} berry, {skipped_cache} cache skipped")
        
        # Apply changes to shared ScriptNarc data
        item_script.apply_changes()


class RandomizeBerryPiles(Step):
    """Randomizes berry pile items with a shuffled selection of berries.
    
    Logic:
    1. Shuffle the berry pool (45 berries)
    2. Take the first 31 to assign to each Berry slot (no duplicates)
    3. Randomly replace 2 of those 31 with Lum Berry and Sitrus Berry
       to ensure they're always available in every seed
    """
    
    NUM_BERRY_SLOTS = 31  # Number of Berry slots in the game
    
    def _get_berry_pool(self):
        """Get berry pool using Item enum values."""
        from enums import Item
        return [
            # Type-resist berries
            Item.OCCA_BERRY.value,
            Item.PASSHO_BERRY.value,
            Item.WACAN_BERRY.value,
            Item.RINDO_BERRY.value,
            Item.YACHE_BERRY.value,
            Item.CHOPLE_BERRY.value,
            Item.KEBIA_BERRY.value,
            Item.SHUCA_BERRY.value,
            Item.COBA_BERRY.value,
            Item.PAYAPA_BERRY.value,
            Item.TANGA_BERRY.value,
            Item.CHARTI_BERRY.value,
            Item.KASIB_BERRY.value,
            Item.HABAN_BERRY.value,
            Item.COLBUR_BERRY.value,
            Item.BABIRI_BERRY.value,
            Item.CHILAN_BERRY.value,
            # Stat-boost berries
            Item.LIECHI_BERRY.value,
            Item.GANLON_BERRY.value,
            Item.SALAC_BERRY.value,
            Item.PETAYA_BERRY.value,
            Item.APICOT_BERRY.value,
            Item.LANSAT_BERRY.value,
            Item.STARF_BERRY.value,
            Item.MICLE_BERRY.value,
            Item.CUSTAP_BERRY.value,
            # Confusion berries
            Item.FIGY_BERRY.value,
            Item.WIKI_BERRY.value,
            Item.MAGO_BERRY.value,
            Item.AGUAV_BERRY.value,
            Item.IAPAPA_BERRY.value,
            # Status cure berries
            Item.CHERI_BERRY.value,
            Item.CHESTO_BERRY.value,
            Item.PECHA_BERRY.value,
            Item.RAWST_BERRY.value,
            Item.ASPEAR_BERRY.value,
            Item.LEPPA_BERRY.value,
            Item.ORAN_BERRY.value,
            Item.PERSIM_BERRY.value,
            # Damage berries
            Item.JABOCA_BERRY.value,
            Item.ROWAP_BERRY.value,
            # Gen 6 berries
            Item.ROSELI_BERRY.value,
            Item.KEE_BERRY.value,
            Item.MARANGA_BERRY.value,
            # Enigma Berry
            Item.ENIGMA_BERRY.value,
        ]
    
    def _get_lum_berry(self):
        from enums import Item
        return Item.LUM_BERRY.value
    
    def _get_sitrus_berry(self):
        from enums import Item
        return Item.SITRUS_BERRY.value
    
    def __init__(self):
        self.slot_to_tier = self._load_slot_tier_mapping()
    
    def _load_slot_tier_mapping(self):
        """Load Item_Slot_tier.csv to find Berry slots"""
        import os
        
        slot_to_tier = {}
        csv_path = os.path.join(os.path.dirname(__file__), 'Item_Slot_tier.csv')
        with open(csv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    slot, tier = line.split(',')
                    slot_to_tier[int(slot)] = tier
        return slot_to_tier
    
    def run(self, context):
        import random
        
        item_script = context.get(ItemScript)
        
        # Find all Berry slots
        berry_slots = [slot_num for slot_num, tier in self.slot_to_tier.items() 
                       if tier == 'Berry']
        berry_slots.sort()
        
        if len(berry_slots) != self.NUM_BERRY_SLOTS:
            print(f"WARNING: Expected {self.NUM_BERRY_SLOTS} berry slots, found {len(berry_slots)}")
        
        print(f"Randomizing {len(berry_slots)} berry pile slots...")
        
        # Step 1: Shuffle the berry pool and take first 31
        berry_pool = self._get_berry_pool()
        shuffled_berries = berry_pool.copy()
        random.shuffle(shuffled_berries)
        selected_berries = shuffled_berries[:len(berry_slots)]
        
        # Step 2: Pick 2 random different positions for Lum and Sitrus
        lum_position = random.randint(0, len(berry_slots) - 1)
        sitrus_position = random.randint(0, len(berry_slots) - 1)
        while sitrus_position == lum_position:
            sitrus_position = random.randint(0, len(berry_slots) - 1)
        
        # Step 3: Replace those positions with Lum and Sitrus
        selected_berries[lum_position] = self._get_lum_berry()
        selected_berries[sitrus_position] = self._get_sitrus_berry()
        
        # Step 4: Assign berries to slots
        for i, slot_num in enumerate(berry_slots):
            berry_id = selected_berries[i]
            item_script.slots[slot_num]['item_id'] = berry_id
            print(f"Slot {slot_num}: Berry ID {berry_id}")
        
        print(f"\nBerry randomization complete!")
        print(f"  Lum Berry at position {lum_position} (slot {berry_slots[lum_position]})")
        print(f"  Sitrus Berry at position {sitrus_position} (slot {berry_slots[sitrus_position]})")
        
        # Apply changes to shared ScriptNarc data
        item_script.apply_changes()

