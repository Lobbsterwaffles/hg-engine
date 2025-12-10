import sys
from framework import *


class GiftPokemon(Writeback, NarcExtractor):
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
        # This is a 14-byte structure that appears within script files
        # file_index and offset are added as Computed fields for tracking location
        self.gift_struct = Struct(
            "command_id" / Int16ul,      # Should be 0x0089
            "pokemon_id" / Int16ul,       # Species ID
            "level" / Int16ul,            # Pokemon level
            "item" / Int16ul,             # Held item ID
            "form" / Int16ul,             # Form number
            "ability" / Int16ul,          # Ability slot
            "result_var" / Int16ul        # Script variable for result
        )
        
        self.data = self.load_narc()  # Use self.data for compatibility with NarcExtractor.write_to_rom
        self.gifts = self._find_all_gifts()  # List of Container objects with file_index/offset added
        print(f"Found {len(self.gifts)} GivePokemon commands", file=sys.stderr)
    
    def get_narc_path(self):
        return "a/0/1/2"
    
    def parse_file(self, file_data, index):
        # Return raw bytes - we scan for commands within the file
        return file_data
    
    def serialize_file(self, data, index):
        return data
    
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
    
    def write_to_rom(self):
        """Write all gift data back to ROM"""
        # Apply changes from each gift Container back to raw data
        for gift in self.gifts:
            command_bytes = self.gift_struct.build(gift)
            file_data = bytearray(self.data[gift.file_index])
            file_data[gift.offset:gift.offset + len(command_bytes)] = command_bytes
            self.data[gift.file_index] = bytes(file_data)
        
        # Then use parent class to write NARC back to ROM
        super().write_to_rom()


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

