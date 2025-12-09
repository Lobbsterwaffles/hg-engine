import sys
from framework import *


class GiftPokemon(Writeback, NarcExtractor):
    """Extractor for GivePokemon script commands in NARC a/0/1/2
    
    Finds all GivePokemon (0x0089) commands across all script files.
    
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
        self.data = self.load_narc()  # Use self.data for compatibility with NarcExtractor.write_to_rom
        self.gifts = self._find_all_gifts()
        print(f"Found {len(self.gifts)} GivePokemon commands", file=sys.stderr)
    
    def get_narc_path(self):
        return "a/0/1/2"
    
    def parse_file(self, file_data, index):
        # Return raw bytes - we parse commands manually
        return file_data
    
    def serialize_file(self, data, index):
        return data
    
    def _find_all_gifts(self):
        """Scan all script files for GivePokemon commands"""
        gifts = []
        
        for file_idx, file_data in enumerate(self.data):
            if len(file_data) < self.COMMAND_SIZE:
                continue
            
            # Scan for command pattern
            for offset in range(len(file_data) - self.COMMAND_SIZE + 1):
                if file_data[offset] == 0x89 and file_data[offset + 1] == 0x00:
                    # Parse the command parameters
                    pokemon_id = file_data[offset + 2] | (file_data[offset + 3] << 8)
                    level = file_data[offset + 4] | (file_data[offset + 5] << 8)
                    item = file_data[offset + 6] | (file_data[offset + 7] << 8)
                    form = file_data[offset + 8] | (file_data[offset + 9] << 8)
                    ability = file_data[offset + 10] | (file_data[offset + 11] << 8)
                    result_var = file_data[offset + 12] | (file_data[offset + 13] << 8)
                    
                    # Validate: result_var should be in 0x8000+ range (script variable)
                    # and pokemon/level should be reasonable
                    if (result_var >= 0x8000 and 
                        1 <= pokemon_id <= 700 and 
                        1 <= level <= 100):
                        
                        gift = GiftPokemonEntry(
                            file_index=file_idx,
                            offset=offset,
                            pokemon_id=pokemon_id,
                            level=level,
                            item=item,
                            form=form,
                            ability=ability,
                            result_var=result_var,
                            data=self.data  # Reference for writes
                        )
                        gifts.append(gift)
        
        return gifts
    
    def write_to_rom(self):
        """Write all modified gift data back to ROM"""
        # First, apply any pending changes from GiftPokemonEntry objects
        for gift in self.gifts:
            gift._write_to_raw()
        
        # Then use parent class to write NARC back to ROM
        super().write_to_rom()


class GiftPokemonEntry:
    """Represents a single GivePokemon command that can be read/modified"""
    
    def __init__(self, file_index, offset, pokemon_id, level, item, form, ability, result_var, data):
        self.file_index = file_index
        self.offset = offset
        self._pokemon_id = pokemon_id
        self._level = level
        self._item = item
        self._form = form
        self._ability = ability
        self._result_var = result_var
        self._data = data  # Reference to the NARC file data list
        self._dirty = False
    
    @property
    def pokemon_id(self):
        return self._pokemon_id
    
    @pokemon_id.setter
    def pokemon_id(self, value):
        self._pokemon_id = value
        self._dirty = True
    
    @property
    def level(self):
        return self._level
    
    @level.setter
    def level(self, value):
        self._level = value
        self._dirty = True
    
    @property
    def item(self):
        return self._item
    
    @item.setter
    def item(self, value):
        self._item = value
        self._dirty = True
    
    @property
    def form(self):
        return self._form
    
    @form.setter
    def form(self, value):
        self._form = value
        self._dirty = True
    
    @property
    def ability(self):
        return self._ability
    
    @ability.setter
    def ability(self, value):
        self._ability = value
        self._dirty = True
    
    def _write_to_raw(self):
        """Write current values back to the data buffer"""
        if not self._dirty:
            return
        
        # Get the file data as a mutable bytearray
        file_data = bytearray(self._data[self.file_index])
        
        # Write each field (little-endian 16-bit)
        file_data[self.offset + 2] = self._pokemon_id & 0xFF
        file_data[self.offset + 3] = (self._pokemon_id >> 8) & 0xFF
        file_data[self.offset + 4] = self._level & 0xFF
        file_data[self.offset + 5] = (self._level >> 8) & 0xFF
        file_data[self.offset + 6] = self._item & 0xFF
        file_data[self.offset + 7] = (self._item >> 8) & 0xFF
        file_data[self.offset + 8] = self._form & 0xFF
        file_data[self.offset + 9] = (self._form >> 8) & 0xFF
        file_data[self.offset + 10] = self._ability & 0xFF
        file_data[self.offset + 11] = (self._ability >> 8) & 0xFF
        
        # Update the data reference
        self._data[self.file_index] = bytes(file_data)
        self._dirty = False
    
    def __repr__(self):
        return (f"GiftPokemonEntry(file={self.file_index}, offset=0x{self.offset:04X}, "
                f"pokemon={self._pokemon_id}, level={self._level}, item={self._item}, "
                f"form={self._form}, ability={self._ability})")


class ItemScript(Writeback, NarcExtractor):
    """Extractor for item script file in NARC a/0/1/2
    
    Use like: item_script[5] = 1004  # Set slot 5 to item ID 1004
    """
    
    ITEMSCRIPT_FILE = 141
    
    def __init__(self, context):
        super().__init__(context)
        
        # 18-byte entries: item_id + 16 bytes of other data
        item_entry = Struct(
            "item_id" / Int16ul,
            "other_data" / Bytes(16)
        )
        
        # Expanded structure: 589 slots (ground items, berries, caches, hidden items)
        # Header is 0x093C bytes (verified via bindiff: slot 1 item_id at offset 0x094E)
        self.script_struct = Struct(
            "header" / Bytes(0x093C),
            "slots" / Array(589, item_entry),
            "remaining_data" / GreedyRange(Int8ul)
        )
        
        self.data = self.load_narc()
        print(f"DEBUG: Loaded {len(self.data)} files from NARC", file=sys.stderr)
        if len(self.data) <= self.ITEMSCRIPT_FILE:
            print(f"ERROR: NARC only has {len(self.data)} files, but we need file {self.ITEMSCRIPT_FILE}", file=sys.stderr)
        
        # Direct access to the parsed construct data
        self.script_data = self.data[self.ITEMSCRIPT_FILE]
        #print(f"DEBUG: Script has {len(self.script_data.items)} item slots", file=sys.stderr)
    
    def get_narc_path(self):
        return "a/0/1/2"
    
    def parse_file(self, file_data, index):
        if index == self.ITEMSCRIPT_FILE:
            print(f"DEBUG: Parsing file {index}, data length: {len(file_data)}", file=sys.stderr)
            parsed = self.script_struct.parse(file_data)
            return parsed
        return file_data
    
    def serialize_file(self, data, index):
        if index == self.ITEMSCRIPT_FILE:
            return self.script_struct.build(data)
        return data


class OopsAllMasterBall(Step):
    """Changes all item IDs in the item script to Master Ball (item ID 1)"""
    
    def run(self, context):
        item_script = context.get(ItemScript)
        
        # Set all item slots to Master Ball (item ID 1)
        for slot in item_script.script_data.slots:
            slot.item_id = 1


class RandomizeGroundItems(Step):
    """Randomizes ground items based on area tiers and item rarities"""
    
    def __init__(self):
        # Area-based rarity probabilities: [Common, Uncommon, Rare, Master]
        self.area_probabilities = {
            1: [30, 45, 20, 5],
            2: [0, 50, 35, 15], 
            3: [0, 20, 50, 30],
            4: [0, 0, 55, 45]
        }
        
        # Load CSV data
        self.slot_to_area = self._load_slot_tier_mapping()
        self.item_pools = self._load_item_rarity_pools()
        self.item_name_to_id = self._create_item_name_to_id_mapping()
    
    def _load_slot_tier_mapping(self):
        """Load Item_Slot_tier.csv to map item slots to tiers/categories
        
        Returns dict mapping slot number to tier value:
        - 1, 2, 3, 4: Ground item tiers (will be randomized)
        - 'Berry': Berry piles (skipped, handled by separate step)
        - 'Cache': Rare candy caches (skipped, not touched)
        - 'hidden': Hidden items (will get junk tier items)
        """
        import os
        
        slot_to_tier = {}
        csv_path = os.path.join(os.path.dirname(__file__), 'Item_Slot_tier.csv')
        with open(csv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    slot, tier = line.split(',')
                    # Try to parse as int (tiers 1-4), otherwise keep as string
                    try:
                        slot_to_tier[int(slot)] = int(tier)
                    except ValueError:
                        slot_to_tier[int(slot)] = tier  # Berry, Cache, hidden
        return slot_to_tier
    
    def _load_item_rarity_pools(self):
        """Load Ground_Item_Tier.csv to create rarity-based item pools
        
        Includes junk pool for hidden items.
        """
        import os
        
        item_pools = {
            'junk': [],      # For hidden items
            'common': [],
            'uncommon': [],
            'rare': [],
            'master': []
        }
        
        csv_path = os.path.join(os.path.dirname(__file__), 'Ground_Item_Tier.csv')
        with open(csv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    item_name, rarity = line.split(',')
                    item_pools[rarity.lower()].append(item_name)
        
        return item_pools
    
    def _create_item_name_to_id_mapping(self):
        """Create mapping from item names to IDs using enums.py"""
        from enums import Item
        
        name_to_id = {}
        
        # Map enum names to IDs
        for item in Item:
            # Convert enum name to readable format (e.g., MASTER_BALL -> Master Ball)
            readable_name = item.name.replace('_', ' ').title()
            name_to_id[readable_name] = item.value
        
        # Handle TM numbers (bare numbers refer to TMs)
        # Extract TM mappings directly from the enum
        for item in Item:
            if item.name.startswith('TM'):
                # Extract TM number from name (e.g., TM001 -> 1, TM092 -> 92)
                tm_num_str = item.name[2:]  # Remove 'TM' prefix
                if tm_num_str.isdigit():
                    tm_num = int(tm_num_str)
                    name_to_id[str(tm_num)] = item.value
        
        return name_to_id
    
    def _get_item_id_from_name(self, item_name):
        """Convert item name to ID, handling TMs and special cases"""
        # Handle bare numbers (TMs)
        if item_name.isdigit():
            return self.item_name_to_id[item_name]
        
        # Handle regular item names
        if item_name in self.item_name_to_id:
            return self.item_name_to_id[item_name]
        
        # Try variations of the name
        variations = [
            item_name,
            item_name.title(),
            item_name.upper(),
            item_name.replace(' ', '_').upper(),
            item_name.replace('_', ' ').title()
        ]
        
        for variation in variations:
            if variation in self.item_name_to_id:
                return self.item_name_to_id[variation]
        
        # If not found, error out hard as requested
        raise ValueError(f"Item name '{item_name}' not found in item mapping")
    
    def _select_rarity_for_area(self, area):
        """Select a rarity based on area probabilities"""
        import random
        
        probabilities = self.area_probabilities[area]
        rand_val = random.randint(1, 100)
        
        cumulative = 0
        rarities = ['common', 'uncommon', 'rare', 'master']
        
        for i, prob in enumerate(probabilities):
            cumulative += prob
            if rand_val <= cumulative:
                return rarities[i]
        
        # Fallback to master if something goes wrong
        return 'master'
    
    def run(self, context):
        import random
        
        item_script = context.get(ItemScript)
        
        print(f"Processing {len(item_script.script_data.slots)} item slots...")
        
        ground_count = 0
        hidden_count = 0
        skipped_berry = 0
        skipped_cache = 0
        
        for i, slot in enumerate(item_script.script_data.slots):
            # Get tier for this slot
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
            
            # Handle hidden items - assign random junk item
            if tier == 'hidden':
                item_pool = self.item_pools['junk']
                if not item_pool:
                    raise ValueError("No items found for junk rarity pool")
                
                selected_item_name = random.choice(item_pool)
                selected_item_id = self._get_item_id_from_name(selected_item_name)
                slot.item_id = selected_item_id
                hidden_count += 1
                print(f"Slot {i} (hidden): junk -> {selected_item_name} (ID {selected_item_id})")
                continue
            
            # Handle ground items (tiers 1-4)
            # Select rarity based on area tier
            selected_rarity = self._select_rarity_for_area(tier)
            
            # Get item pool for selected rarity
            if selected_rarity not in self.item_pools:
                raise ValueError(f"Rarity '{selected_rarity}' not found in item pools")
            
            item_pool = self.item_pools[selected_rarity]
            if not item_pool:
                raise ValueError(f"No items found for rarity '{selected_rarity}'")
            
            # Select random item from pool
            selected_item_name = random.choice(item_pool)
            
            # Convert item name to ID
            selected_item_id = self._get_item_id_from_name(selected_item_name)
            
            # Assign to slot
            slot.item_id = selected_item_id
            ground_count += 1
            
            print(f"Slot {i} (Tier {tier}): {selected_rarity} -> {selected_item_name} (ID {selected_item_id})")
        
        print(f"\nRandomization complete!")
        print(f"  Ground items randomized: {ground_count}")
        print(f"  Hidden items (junk): {hidden_count}")
        print(f"  Berry slots skipped: {skipped_berry}")
        print(f"  Cache slots skipped: {skipped_cache}")


class RandomizeBerryPiles(Step):
    """Randomizes berry pile items with a shuffled selection of berries.
    
    Logic:
    1. Shuffle the berry pool (45 berries)
    2. Take the first 31 to assign to each Berry slot (no duplicates)
    3. Randomly replace 2 of those 31 with Lum Berry and Sitrus Berry
       to ensure they're always available in every seed
    """
    
    # Berry pool - item IDs from item.h
    BERRY_POOL = [
        # Type-resist berries (184-200)
        184,  # Occa Berry
        185,  # Passho Berry
        186,  # Wacan Berry
        187,  # Rindo Berry
        188,  # Yache Berry
        189,  # Chople Berry
        190,  # Kebia Berry
        191,  # Shuca Berry
        192,  # Coba Berry
        193,  # Payapa Berry
        194,  # Tanga Berry
        195,  # Charti Berry
        196,  # Kasib Berry
        197,  # Haban Berry
        198,  # Colbur Berry
        199,  # Babiri Berry
        200,  # Chilan Berry
        # Stat-boost berries (201-210)
        201,  # Liechi Berry
        202,  # Ganlon Berry
        203,  # Salac Berry
        204,  # Petaya Berry
        205,  # Apicot Berry
        206,  # Lansat Berry
        207,  # Starf Berry
        209,  # Micle Berry
        210,  # Custap Berry
        # Confusion berries (159-163)
        159,  # Figy Berry
        160,  # Wiki Berry
        161,  # Mago Berry
        162,  # Aguav Berry
        163,  # Iapapa Berry
        # Status cure berries (149-156)
        149,  # Cheri Berry
        150,  # Chesto Berry
        151,  # Pecha Berry
        152,  # Rawst Berry
        153,  # Aspear Berry
        154,  # Leppa Berry
        155,  # Oran Berry
        156,  # Persim Berry
        # Damage berries (211-212)
        211,  # Jaboca Berry
        212,  # Rowap Berry
        # Gen 6 berries (686-688)
        686,  # Roseli Berry
        687,  # Kee Berry
        688,  # Maranga Berry
        # Enigma Berry
        208,  # Enigma Berry
    ]
    
    # Guaranteed berries - always included in every seed
    LUM_BERRY = 157
    SITRUS_BERRY = 158
    
    NUM_BERRY_SLOTS = 31  # Number of Berry slots in the game
    
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
        shuffled_berries = self.BERRY_POOL.copy()
        random.shuffle(shuffled_berries)
        selected_berries = shuffled_berries[:len(berry_slots)]
        
        # Step 2: Pick 2 random different positions for Lum and Sitrus
        lum_position = random.randint(0, len(berry_slots) - 1)
        sitrus_position = random.randint(0, len(berry_slots) - 1)
        while sitrus_position == lum_position:
            sitrus_position = random.randint(0, len(berry_slots) - 1)
        
        # Step 3: Replace those positions with Lum and Sitrus
        selected_berries[lum_position] = self.LUM_BERRY
        selected_berries[sitrus_position] = self.SITRUS_BERRY
        
        # Step 4: Assign berries to slots
        for i, slot_num in enumerate(berry_slots):
            berry_id = selected_berries[i]
            item_script.script_data.slots[slot_num].item_id = berry_id
            print(f"Slot {slot_num}: Berry ID {berry_id}")
        
        print(f"\nBerry randomization complete!")
        print(f"  Lum Berry at position {lum_position} (slot {berry_slots[lum_position]})")
        print(f"  Sitrus Berry at position {sitrus_position} (slot {berry_slots[sitrus_position]})")

