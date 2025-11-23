import sys
from framework import *

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
        
        # Only define structure for the item script file
        self.script_struct = Struct(
            "header" / Bytes(0x0406),
            "slots" / Array(255, item_entry),
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
        """Load Item_Slot_tier.csv to map item slots to areas"""
        import os
        
        slot_to_area = {}
        csv_path = os.path.join(os.path.dirname(__file__), 'Item_Slot_tier.csv')
        with open(csv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    slot, area = line.split(',')
                    slot_to_area[int(slot)] = int(area)
        return slot_to_area
    
    def _load_item_rarity_pools(self):
        """Load Ground_Item_Tier.csv to create rarity-based item pools"""
        import os
        
        item_pools = {
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
                    if rarity.lower() != 'junk':  # Skip junk items as specified
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
        
        print(f"Randomizing {len(item_script.script_data.slots)} ground items...")
        
        for i, slot in enumerate(item_script.script_data.slots):
            # Get area for this slot
            if i not in self.slot_to_area:
                raise ValueError(f"Slot {i} not found in Item_Slot_tier.csv")
            
            area = self.slot_to_area[i]
            
            # Select rarity based on area
            selected_rarity = self._select_rarity_for_area(area)
            
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
            
            print(f"Slot {i} (Area {area}): {selected_rarity} -> {selected_item_name} (ID {selected_item_id})")
        
        print("Ground item randomization complete!")

