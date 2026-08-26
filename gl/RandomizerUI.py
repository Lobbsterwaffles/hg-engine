"""
Goldilockes Randomizer UI
A simple CustomTkinter interface for the Randomizer.

Requirements: pip install customtkinter pillow

Usage (from repo root):
    python gl/RandomizerUI.py
"""

import sys
import os
from pathlib import Path
import multiprocessing
from multiprocessing import Process, Queue
import traceback

# Determine script directory and add to path BEFORE other imports
# This allows running from repo root: python gl/RandomizerUI.py
SCRIPT_DIR = Path(__file__).parent.resolve()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import io
import json
import random
import shutil
from datetime import datetime
import subprocess
import difflib

import customtkinter as ctk
from PIL import Image
from tkinter import filedialog, messagebox
import tkinter as tk

import ndspy.rom

from steps import *
from trainer_data_editor import *
from trainer_held_items import TrainerHeldItem, AssignNatureStep
from print_eviolite_users_step import PrintEvioliteUsersStep
from script_extractor import *


# Set UTF-8 encoding for console output on Windows (only if we have a real stream).
# When running as a PyInstaller windowed app (--noconsole), stdout/stderr are None.
# We intentionally leave them as None so any stray prints will crash - this ensures
# we catch code that prints outside the StringIO capture block.
if sys.platform == 'win32' and sys.stdout is not None:
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())


# Paths - relative to repo root (where we run from)
CONFIG_FILE = Path('gl/randomizer_config.json')
SPOILER_DIR = Path('gl/Spoiler')
BADGE_ICON_PATH = Path('gl/PlainBadgeIcon.png')
TRACKER_DATA_DIR = Path('gl/tracker_data')
TRACKER_DATA_FILE = Path('gl/TrackerData.json')
TRACKER_ENCS_FILE = Path('gl/TrackerEncs.csv')
SPRITES_DIR = Path('data/graphics/sprites')
ITEM_TIER_FILE = Path('gl/Ground_Item_Tier.csv')
MART_ITEMS_FILE = Path('gl/MartItems.csv')
MACHINE_MOVES_FILE = Path('gl/machine_moves.json')
TIERS1_FILE = Path('gl/Tiers1.csv')
TIERS2_FILE = Path('gl/Tiers2.csv')
TIERS3_FILE = Path('gl/Tiers3.csv')
CHANGES_FROM_VANILLA_FILE = Path('gl/change_from_vanilla.json')
NUZLOCKE_RULES_FILE = Path('gl/nuzlocke_rules.json')

# Tooltip text for asterisked cells in the Tiers of Play tables.
# Keys are (table_title, row_label, column_header) tuples.
# For row label cells (first column), column_header is empty string "".
# Edit the values to customize what each tooltip displays.
TIER_CELL_TOOLTIPS = {
    # Trainers table - row label tooltip
    ("Trainers", "Boss Held Items*", ""): "% Chance of: no / useful / good held item",
    ("Trainers", "Trainer Held Items*", ""): "% Chance of: no / useful / good held item",
    # Trainers table - value cell tooltip (45/50/5* in Mid column)
    ("Trainers", "Boss Held Items*", "Mid"): "Mid Game Boss' Aces always have held item",
    
    # Item Rolls table - row label tooltip
    ("Item Rolls", "Ground Item Rarity*", ""): "% Chance of: Common / Uncommon / Rare / Master",
    ("Type Themes", "Boss Mimic*", ""): "Pokemon which is not a theme's type but fits its flavor.\n(e.g. Charizard -> Dragon Gym)",
    ("Type Themes", "Boss Pivot*", ""): "Pokemon with good Defensive matchup into Gym theme's weaknesses\n(e.g. Grass resists 2 of Fire's 3 weaknesses)",
    ("Type Themes", "Boss Fulcrum*", ""): "Pokemon with good Offensive matchup into Gym theme's weaknesses\n(e.g. Ground is super-effective against Flying's weaknesses)",
    ("Type Themes", "Gym Trainer Mimic*", ""): "Pokemon which is not a theme's type, but fits its flavor.\n(e.g. Charizard -> Dragon Gym)",
}


def load_tracker_data():
    """
    Load Pokemon, ability, move, and TM data from JSON files for the Tracker feature.
    
    Returns:
        tuple: (pokemon_list, ability_dict, moves_dict, tm_move_map, form_lookup)
            - pokemon_list: List of Pokemon dictionaries with name, stats, abilities, learnsets
            - ability_dict: Dictionary mapping ability ID to name and description
            - moves_dict: Dictionary mapping move constant to move data (type, category, power, etc.)
            - tm_move_map: Dictionary mapping move constant to TM/HM info (number, kind)
            - form_lookup: Dictionary mapping (base_species_const, form_number) to Pokemon dict
    """
    pokemon_file = TRACKER_DATA_DIR / 'pokemon.json'
    ability_file = TRACKER_DATA_DIR / 'abilities.json'
    moves_file = TRACKER_DATA_DIR / 'moves.json'
    machine_moves_file = Path('gl/machine_moves.json')
    
    pokemon_list = []
    ability_dict = {}
    moves_dict = {}
    tm_move_map = {}  # Maps move constant (e.g., "MOVE_PROTECT") to TM/HM info
    form_lookup = {}  # Maps (base_species_const, form_number) to Pokemon dict
    
    if pokemon_file.exists():
        with open(pokemon_file, 'r', encoding='utf-8') as f:
            pokemon_list = json.load(f)
    
    if ability_file.exists():
        with open(ability_file, 'r', encoding='utf-8') as f:
            # JSON keys are strings, convert to int
            raw_data = json.load(f)
            ability_dict = {int(k): v for k, v in raw_data.items()}
    
    if moves_file.exists():
        with open(moves_file, 'r', encoding='utf-8') as f:
            moves_dict = json.load(f)
    
    if machine_moves_file.exists():
        with open(machine_moves_file, 'r', encoding='utf-8') as f:
            machine_moves_list = json.load(f)
            # Create a map from move name to TM/HM info (skip TRs - not used in this project)
            for entry in machine_moves_list:
                kind = entry.get('kind', 'TM')
                if kind == 'TR':
                    continue  # Skip Technical Records
                move_name = entry.get('move_name', '')
                tm_move_map[move_name] = {
                    'kind': kind,  # "TM" or "HM"
                    'number': entry.get('number', 0)   # TM/HM number
                }
    
    # Build form lookup: maps (base_species_const, form_number) to Pokemon dict
    # This allows evolution display to find the correct form when form > 0
    form_lookup = build_form_lookup(pokemon_list)
    
    return pokemon_list, ability_dict, moves_dict, tm_move_map, form_lookup


def load_tm_number_to_name():
    """
    Load TM number to move name mapping from machine_moves.json.
    
    Returns:
        dict: Maps TM number (int) to move name (str), e.g., {21: "Pounce", 18: "Thief"}
    """
    tm_map = {}
    
    if MACHINE_MOVES_FILE.exists():
        with open(MACHINE_MOVES_FILE, 'r', encoding='utf-8') as f:
            machine_moves = json.load(f)
            for entry in machine_moves:
                kind = entry.get('kind', 'TM')
                if kind == 'TM':  # Only TMs, not HMs or TRs
                    number = entry.get('number', 0)
                    move_name = entry.get('move_name', '')
                    # Convert MOVE_POUNCE to "Pounce"
                    readable_name = move_name.replace('MOVE_', '').replace('_', ' ').title()
                    tm_map[number] = readable_name
    
    return tm_map


def load_item_tiers(tm_number_to_name):
    """
    Load item tier data from Ground_Item_Tier.csv.
    
    Args:
        tm_number_to_name: Dict mapping TM numbers to move names
    
    Returns:
        dict: Maps tier name (str) to list of item names (str).
              e.g., {'junk': ['White Herb', 'Mental Herb', ...], 'common': [...], ...}
    """
    tiers = {}
    
    if ITEM_TIER_FILE.exists():
        with open(ITEM_TIER_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(',')
                if len(parts) >= 2:
                    item_name = parts[0].strip()
                    tier = parts[1].strip().lower()  # Normalize tier names to lowercase
                    
                    # Check if item_name is a TM number (all digits)
                    if item_name.isdigit():
                        tm_num = int(item_name)
                        if tm_num in tm_number_to_name:
                            item_name = f"TM{tm_num:02d} {tm_number_to_name[tm_num]}"
                        else:
                            item_name = f"TM{tm_num:02d}"
                    
                    if tier not in tiers:
                        tiers[tier] = []
                    tiers[tier].append(item_name)
    
    return tiers


def load_mart_items():
    """
    Load mart items from MartItems.csv.
    
    Returns:
        dict: Maps mart location (str) to list of item names (str).
              e.g., {'Gold. 3F': ['Pomeg Berry', 'Kelpsy Berry', ...], ...}
    """
    marts = {}
    
    if MART_ITEMS_FILE.exists():
        with open(MART_ITEMS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(',')
                if len(parts) >= 2:
                    item_name = parts[0].strip()
                    location = parts[1].strip()
                    
                    if location not in marts:
                        marts[location] = []
                    marts[location].append(item_name)
    
    return marts


def build_form_lookup(pokemon_list):
    """
    Build a lookup dictionary for finding Pokemon forms by base species and form number.
    
    Evolution data stores target species like "SPECIES_RAICHU" with a form number (0, 1, 2...).
    Form 0 is the base form, form 1+ are alternate forms (Alolan, Galarian, etc.).
    
    This function builds a mapping so we can find:
    - ("SPECIES_RAICHU", 0) -> Raichu (base form)
    - ("SPECIES_RAICHU", 1) -> Raichu (Alolan)
    
    Args:
        pokemon_list: List of Pokemon dictionaries from pokemon.json
        
    Returns:
        dict: Maps (base_species_const, form_number) to Pokemon dict
    """
    form_lookup = {}
    
    # First pass: map all base Pokemon (form 0) by their species_const
    # Also build a dict of species_const to Pokemon for quick lookup
    species_to_pokemon = {}
    for poke in pokemon_list:
        species_const = poke.get('species_const', '')
        species_to_pokemon[species_const] = poke
        # Add base forms (form 0) - these have no parentheses in name
        if '(' not in poke.get('name', ''):
            form_lookup[(species_const, 0)] = poke
    
    # Second pass: find alternate forms and map them
    # Alternate forms have names like "Raichu (Alolan)" and species_const like "SPECIES_RAICHU_ALOLAN"
    # Group them by base name to determine form ordering
    base_to_forms = {}  # base_name -> list of (species_const, pokemon)
    
    for poke in pokemon_list:
        name = poke.get('name', '')
        species_const = poke.get('species_const', '')
        
        # Check if this is a form (has parentheses in name)
        if '(' in name and ')' in name:
            # Extract base name: "Raichu (Alolan)" -> "Raichu"
            base_name = name.split('(')[0].strip()
            
            if base_name not in base_to_forms:
                base_to_forms[base_name] = []
            base_to_forms[base_name].append((species_const, poke))
    
    # Third pass: assign form numbers based on order of appearance
    # Form numbers start at 1 for alternate forms (0 is reserved for base)
    for base_name, forms_list in base_to_forms.items():
        # Find the base species_const for this base_name
        # Convert name to species_const format: "Raichu" -> "SPECIES_RAICHU"
        # Handle special cases like "Mr. Mime" -> "SPECIES_MR_MIME"
        base_species_const = 'SPECIES_' + base_name.upper().replace(' ', '_').replace('.', '').replace("'", "").replace('-', '_')
        
        # Assign form numbers (1, 2, 3...) to alternate forms in order
        for form_num, (species_const, poke) in enumerate(forms_list, start=1):
            form_lookup[(base_species_const, form_num)] = poke
    
    return form_lookup


def fuzzy_match(query, name, max_diff=1):
    """
    Check if query fuzzy-matches the name (allowing up to max_diff character differences).
    
    This uses a simple approach: check if the query is a substring match,
    or if editing distance is within max_diff for short queries.
    
    Args:
        query: Search query (lowercase)
        name: Pokemon name to match against (will be lowercased)
        max_diff: Maximum allowed character differences (default 1)
        
    Returns:
        bool: True if the query matches the name within tolerance
    """
    name_lower = name.lower()
    query_lower = query.lower()
    
    # Exact substring match
    if query_lower in name_lower:
        return True
    
    # For short queries, also check prefix with fuzzy matching
    if len(query_lower) <= 3:
        # Just do substring check for very short queries
        return query_lower in name_lower
    
    # Use difflib to find close matches
    # Check if any substring of name_lower of similar length matches
    for i in range(len(name_lower) - len(query_lower) + 2):
        end = min(i + len(query_lower) + 1, len(name_lower))
        substring = name_lower[i:end]
        # Calculate simple edit distance approximation using SequenceMatcher
        ratio = difflib.SequenceMatcher(None, query_lower, substring).ratio()
        # Allow ~1 char diff means ratio should be high
        # For a string of length n, 1 diff means (n-1)/n match ratio
        threshold = (len(query_lower) - max_diff) / len(query_lower) if len(query_lower) > 0 else 0
        if ratio >= threshold:
            return True
    
    return False


def get_version_sha():
    """Return the git commit SHA this run is based on, for log traceability.

    Prefers a bundled 'version.txt' (written at build time, since the packaged
    app has no .git folder). Falls back to querying git directly when running
    from source. Returns 'unknown' if neither is available.
    """
    # 1) Bundled version file written by build_release.py (next to the exe).
    version_file = Path('version.txt')
    if version_file.exists():
        sha = version_file.read_text(encoding='utf-8').strip()
        if sha:
            return sha
    # 2) Running from source: ask git directly.
    try:
        sha = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=str(SCRIPT_DIR),
            stderr=subprocess.DEVNULL,
        ).decode('utf-8').strip()
        if sha:
            return sha
    except Exception:
        pass
    return 'unknown'


class ToolTip:
    """
    Simple tooltip that appears when hovering over a widget.
    
    A tooltip is a small popup box that shows helpful text when you
    move your mouse over a button or other element.
    
    Usage:
        tooltip = ToolTip(my_button)
        tooltip.set_text("This is helpful info")  # Call this to update text
    """
    
    def __init__(self, button):
        self.button = button
        self.text = ""
        self.tooltip_window = None
        
        # Bind to the button - use button's bind method
        self.button.configure(cursor="hand2")  # Ensure it acts like a button
        
        # Schedule-based approach: check if mouse is over button
        self._schedule_id = None
        self.button.bind("<Enter>", self._on_enter)
        self.button.bind("<Leave>", self._on_leave)
    
    def set_text(self, text):
        """Set the tooltip text. Call this whenever the text should change."""
        self.text = text
        # If tooltip is currently showing, hide it so stale text doesn't linger
        self._hide_now()
    
    def _on_enter(self, event=None):
        """Mouse entered the button area."""
        # Cancel any pending hide
        if self._schedule_id:
            self.button.after_cancel(self._schedule_id)
            self._schedule_id = None
        
        # Show tooltip after a tiny delay
        self._schedule_id = self.button.after(100, self._show_now)
    
    def _on_leave(self, event=None):
        """Mouse left the button area."""
        # Cancel any pending show
        if self._schedule_id:
            self.button.after_cancel(self._schedule_id)
            self._schedule_id = None
        
        # Hide immediately
        self._hide_now()
    
    def _show_now(self):
        """Actually show the tooltip."""
        self._schedule_id = None
        
        # Don't show if no text
        if not self.text:
            return
        
        # Hide any existing tooltip first
        self._hide_now()
        
        # Position tooltip below the button
        x = self.button.winfo_rootx() + 20
        y = self.button.winfo_rooty() + self.button.winfo_height() + 5
        
        # Create a new toplevel window for the tooltip
        self.tooltip_window = ctk.CTkToplevel(self.button)
        self.tooltip_window.wm_overrideredirect(True)  # No window decorations
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True)
        
        # Create the label with tooltip text
        label = ctk.CTkLabel(
            self.tooltip_window,
            text=self.text,
            font=ctk.CTkFont(size=11),
            fg_color=("#ffffe0", "#333333"),
            text_color=("black", "white"),
            corner_radius=4,
            padx=8,
            pady=4
        )
        label.pack()
    
    def _hide_now(self):
        """Actually hide the tooltip."""
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None


class MoveToolTip:
    """
    Tooltip for move buttons that shows formatted move info.
    
    Displays a box with:
    - Row 1: [Type] [Category]
    - Row 2: "BP" "Acc" "PP" (labels)
    - Row 3: [power] [accuracy] [pp] (values)
    """
    
    def __init__(self, button):
        self.button = button
        self.move_data = None  # Dict with type, category, power, accuracy, pp
        self.tooltip_window = None
        
        self.button.configure(cursor="hand2")
        self._schedule_id = None
        self.button.bind("<Enter>", self._on_enter)
        self.button.bind("<Leave>", self._on_leave)
    
    def set_move_data(self, move_data):
        """
        Set the move data for the tooltip.
        
        Args:
            move_data: Dict with keys 'type', 'category', 'power', 'accuracy', 'pp'
        """
        self.move_data = move_data
        self._hide_now()
    
    def _on_enter(self, event=None):
        if self._schedule_id:
            self.button.after_cancel(self._schedule_id)
            self._schedule_id = None
        self._schedule_id = self.button.after(100, self._show_now)
    
    def _on_leave(self, event=None):
        if self._schedule_id:
            self.button.after_cancel(self._schedule_id)
            self._schedule_id = None
        self._hide_now()
    
    def _show_now(self):
        self._schedule_id = None
        
        if not self.move_data:
            return
        
        self._hide_now()
        
        # Position tooltip below the button
        x = self.button.winfo_rootx() + 20
        y = self.button.winfo_rooty() + self.button.winfo_height() + 5
        
        self.tooltip_window = ctk.CTkToplevel(self.button)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True)
        
        # Main frame for the tooltip content
        main_frame = ctk.CTkFrame(
            self.tooltip_window,
            fg_color=("#ffffe0", "#333333"),
            corner_radius=4
        )
        main_frame.pack(padx=2, pady=2)
        
        # Row 1: Type and Category (2 columns)
        row1 = ctk.CTkFrame(main_frame, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(6, 2))
        row1.grid_columnconfigure(0, weight=1)
        row1.grid_columnconfigure(1, weight=1)
        
        type_label = ctk.CTkLabel(
            row1,
            text=self.move_data.get('type', 'Normal'),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("black", "white")
        )
        type_label.grid(row=0, column=0, padx=5)
        
        category_label = ctk.CTkLabel(
            row1,
            text=self.move_data.get('category', 'Status'),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("black", "white")
        )
        category_label.grid(row=0, column=1, padx=5)
        
        # Row 2: Labels (BP, Acc, PP) - 3 columns
        row2 = ctk.CTkFrame(main_frame, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(4, 0))
        row2.grid_columnconfigure(0, weight=1)
        row2.grid_columnconfigure(1, weight=1)
        row2.grid_columnconfigure(2, weight=1)
        
        for i, label_text in enumerate(["BP", "Acc", "PP"]):
            lbl = ctk.CTkLabel(
                row2,
                text=label_text,
                font=ctk.CTkFont(size=10),
                text_color=("gray40", "gray70")
            )
            lbl.grid(row=0, column=i, padx=5)
        
        # Row 3: Values (power, accuracy, pp) - 3 columns
        row3 = ctk.CTkFrame(main_frame, fg_color="transparent")
        row3.pack(fill="x", padx=8, pady=(0, 6))
        row3.grid_columnconfigure(0, weight=1)
        row3.grid_columnconfigure(1, weight=1)
        row3.grid_columnconfigure(2, weight=1)
        
        power = self.move_data.get('power', 0)
        accuracy = self.move_data.get('accuracy', 0)
        pp = self.move_data.get('pp', 0)
        
        # Display "-" for 0 power (status moves) or 0 accuracy (never-miss moves)
        power_text = str(power) if power > 0 else "-"
        acc_text = str(accuracy) if accuracy > 0 else "-"
        
        for i, value_text in enumerate([power_text, acc_text, str(pp)]):
            val = ctk.CTkLabel(
                row3,
                text=value_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("black", "white")
            )
            val.grid(row=0, column=i, padx=5)
        
        # Row 4: Description (if available)
        description = self.move_data.get('description', '')
        if description:
            desc_label = ctk.CTkLabel(
                main_frame,
                text=description,
                font=ctk.CTkFont(size=10),
                text_color=("gray30", "gray80"),
                wraplength=200,  # Wrap long descriptions
                justify="left"
            )
            desc_label.pack(fill="x", padx=8, pady=(4, 6))
    
    def _hide_now(self):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None


# Evolution method tooltip strings - customize these!
# Maps EVO_* method names to their display tooltip text
EVO_METHOD_TOOLTIPS = {
    "EVO_NONE": "",
    "EVO_FRIENDSHIP": "Level up with high friendship",
    "EVO_FRIENDSHIP_DAY": "Level up with high friendship during the day",
    "EVO_FRIENDSHIP_NIGHT": "Level up with high friendship at night",
    "EVO_LEVEL": "Level {param}",
    "EVO_TRADE": "Trade with another player",
    "EVO_TRADE_ITEM": "Trade while holding {param}",
    "EVO_STONE": "Use item {param}",
    "EVO_LEVEL_ATK_GT_DEF": "Level {param} with Attack > Defense",
    "EVO_LEVEL_ATK_EQ_DEF": "Level {param} with Attack = Defense",
    "EVO_LEVEL_ATK_LT_DEF": "Level {param} with Attack < Defense",
    "EVO_LEVEL_PID_LO": "Level {param} (Random)",
    "EVO_LEVEL_PID_HI": "Level {param} (Random)",
    "EVO_LEVEL_NINJASK": "Level {param}",
    "EVO_LEVEL_SHEDINJA": "Ninjask Level {param} with empty party slot + Poke Ball",
    "EVO_BEAUTY": "Level up with {param}+ Beauty",
    "EVO_STONE_MALE": "Use {param} (male)",
    "EVO_STONE_FEMALE": "Use {param} (female)",
    "EVO_ITEM_DAY": "Level up holding {param} during the day",
    "EVO_ITEM_NIGHT": "Level up holding {param} at night",
    "EVO_HAS_MOVE": "Level up knowing {param}",
    "EVO_OTHER_PARTY_MON": "Level up with {param} in party",
    "EVO_LEVEL_MALE": "Level {param} (male)",
    "EVO_LEVEL_FEMALE": "Level {param} (female)",
    "EVO_LEVEL_ELECTRIC_FIELD": "Level {param} in electric field area",
    "EVO_LEVEL_MOSSY_STONE": "Level {param} near mossy rock",
    "EVO_LEVEL_ICY_STONE": "Level {param} near icy rock",
    "EVO_LEVEL_DAY": "Level {param} during the day",
    "EVO_LEVEL_NIGHT": "Level {param} at night",
    "EVO_LEVEL_DUSK": "Level {param} at dusk",
    "EVO_LEVEL_RAIN": "Level {param} while raining",
    "EVO_HAS_MOVE_TYPE": "Level up knowing a {param}-type move",
    "EVO_LEVEL_DARK_TYPE_MON_IN_PARTY": "Level {param} with Dark-type in party",
    "EVO_TRADE_SPECIFIC_MON": "Trade for {param}",
    "EVO_LEVEL_NATURE_AMPED": "Level {param} with Amped nature",
    "EVO_LEVEL_NATURE_LOW_KEY": "Level {param} with Low Key nature",
    "EVO_AMOUNT_OF_CRITICAL_HITS": "Land {param} critical hits in battle",
    "EVO_HURT_IN_BATTLE_AMOUNT": "Take {param}+ damage and survive",
    "EVO_SPIN_CLOCKWISE_LESS_THAN_5_SECONDS_DAY": "Spin clockwise (<5s) during day",
    "EVO_SPIN_COUNTERCLOCKWISE_LESS_THAN_5_SECONDS_DAY": "Spin counterclockwise (<5s) during day",
    "EVO_SPIN_CLOCKWISE_LESS_THAN_5_SECONDS_NIGHT": "Spin clockwise (<5s) at night",
    "EVO_SPIN_COUNTERCLOCKWISE_MORE_THAN_5_SECONDS_NIGHT": "Spin counterclockwise (>5s) at night",
    "EVO_SPIN_CLOCKWISE_MORE_THAN_5_SECONDS_NIGHT": "Spin clockwise (>5s) at night",
    "EVO_SPIN_COUNTERCLOCKWISE_LESS_THAN_5_SECONDS_NIGHT": "Spin counterclockwise (<5s) at night",
    "EVO_SPIN_COUNTERCLOCKWISE_MORE_THAN_5_SECONDS_DAY": "Spin counterclockwise (>5s) during day",
    "EVO_SPIN_CLOCKWISE_MORE_THAN_5_SECONDS_DAY": "Spin clockwise (>5s) during day",
    "EVO_SPIN_MORE_THAN_10_SECONDS_EVENING": "Spin (>10s) in the evening",
    "EVO_FORM_ARGUMENT": "Special form change",
    "EVO_LETS_GO": "Walk 1000 steps in Let's Go mode",
    "EVO_DUMMY": "Placeholder evolution",
}


class EvoToolTip:
    """
    Tooltip for evolution method buttons.
    
    Shows the evolution method description when hovering.
    """
    
    def __init__(self, button):
        self.button = button
        self.text = ""
        self.tooltip_window = None
        
        self.button.configure(cursor="hand2")
        self._schedule_id = None
        self.button.bind("<Enter>", self._on_enter)
        self.button.bind("<Leave>", self._on_leave)
    
    def set_text(self, text):
        """Set the tooltip text."""
        self.text = text
        self._hide_now()
    
    def _on_enter(self, event=None):
        if self._schedule_id:
            self.button.after_cancel(self._schedule_id)
            self._schedule_id = None
        self._schedule_id = self.button.after(100, self._show_now)
    
    def _on_leave(self, event=None):
        if self._schedule_id:
            self.button.after_cancel(self._schedule_id)
            self._schedule_id = None
        self._hide_now()
    
    def _show_now(self):
        self._schedule_id = None
        
        if not self.text:
            return
        
        self._hide_now()
        
        # Position tooltip below the button
        x = self.button.winfo_rootx() + 20
        y = self.button.winfo_rooty() + self.button.winfo_height() + 5
        
        self.tooltip_window = ctk.CTkToplevel(self.button)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True)
        
        label = ctk.CTkLabel(
            self.tooltip_window,
            text=self.text,
            font=ctk.CTkFont(size=11),
            fg_color=("#ffffe0", "#333333"),
            text_color=("black", "white"),
            corner_radius=4,
            padx=8,
            pady=4
        )
        label.pack()
    
    def _hide_now(self):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None


# Type button colors - customize these hex codes for each Pokemon type!
# The background color of the type button. Fill in with your preferred hex codes.
TYPE_COLORS = {
    'Normal': '#A8A878',    # Fill in hex code
    'Fighting': '#C03028',  # Fill in hex code
    'Flying': '#A890F0',    # Fill in hex code
    'Poison': '#A040A0',    # Fill in hex code
    'Ground': '#E0C068',    # Fill in hex code
    'Rock': '#B8A038',      # Fill in hex code
    'Bug': '#A8B820',       # Fill in hex code
    'Ghost': '#705898',     # Fill in hex code
    'Steel': '#B8B8D0',     # Fill in hex code
    'Fire': '#F08030',      # Fill in hex code
    'Water': '#6890F0',     # Fill in hex code
    'Grass': '#78C850',     # Fill in hex code
    'Electric': '#F8D030',  # Fill in hex code
    'Psychic': '#F85888',   # Fill in hex code
    'Ice': '#98D8D8',       # Fill in hex code
    'Dragon': '#7038F8',    # Fill in hex code
    'Dark': '#705848',      # Fill in hex code
    'Fairy': '#EE99AC',     # Fill in hex code
}


class TypeButton(ctk.CTkFrame):
    """
    A button widget that displays a Pokemon type with colored background.
    
    The button shows the type name with the default font color and a black outline
    effect (created using multiple offset labels). The background color is determined
    by the TYPE_COLORS dictionary above.
    
    Usage:
        type_btn = TypeButton(parent, type_name="Fire")
        type_btn.pack()
    """
    
    def __init__(self, parent, type_name="Normal", width=80, height=24, **kwargs):
        """
        Create a new TypeButton.
        
        Args:
            parent: The parent widget
            type_name: The Pokemon type name (e.g., "Fire", "Water", "Grass")
            width: Button width in pixels
            height: Button height in pixels
        """
        # Get the background color for this type
        bg_color = TYPE_COLORS.get(type_name, '#808080')  # Default gray if type unknown
        
        super().__init__(parent, fg_color=bg_color, corner_radius=6, width=width, height=height, **kwargs)
        
        # Prevent frame from shrinking to fit contents
        self.grid_propagate(False)
        self.pack_propagate(False)
        
        # Create the text with black outline effect
        # We do this by placing multiple copies of the text slightly offset in black,
        # then placing the main text on top
        self._create_outlined_text(type_name, width, height)
    
    def _create_outlined_text(self, text, width, height):
        """
        Create text with a black outline effect.
        
        This is done by creating shadow labels in black at slight offsets,
        then the main text label on top.
        """
        # Container frame to hold all the labels (centered in the button)
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Create the "shadow" labels for the outline effect (black text at offsets)
        # We use a simple approach: 4 labels offset by 1 pixel in each direction
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Left, Right, Up, Down
        
        for dx, dy in offsets:
            shadow_label = ctk.CTkLabel(
                container,
                text=text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="black",
                fg_color="transparent"
            )
            # Place with slight offset
            shadow_label.place(x=dx, y=dy, anchor="center", relx=0.5, rely=0.5)
        
        # Main text label (on top, with default text color)
        # Using white text for good contrast on colored backgrounds
        main_label = ctk.CTkLabel(
            container,
            text=text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white",  # Default light color for visibility
            fg_color="transparent"
        )
        main_label.place(x=0, y=0, anchor="center", relx=0.5, rely=0.5)


# Evolution method sprite paths - customize these!
# Maps EVO_* method names to their sprite image paths (all Rare Candy as placeholder)
EVO_METHOD_SPRITES = {
    "EVO_NONE": Path('data/graphics/item/rare_candy.png'),
    "EVO_FRIENDSHIP": Path('data/graphics/item/rare_candy.png'),
    "EVO_FRIENDSHIP_DAY": Path('data/graphics/item/rare_candy.png'),
    "EVO_FRIENDSHIP_NIGHT": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL": Path('data/graphics/item/rare_candy.png'),
    "EVO_TRADE": Path('data/graphics/item/rare_candy.png'),
    "EVO_TRADE_ITEM": Path('data/graphics/item/rare_candy.png'),
    "EVO_STONE": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_ATK_GT_DEF": Path('data/graphics/item/muscle_band.png'),
    "EVO_LEVEL_ATK_EQ_DEF": Path('data/graphics/item/binding_band.png'),
    "EVO_LEVEL_ATK_LT_DEF": Path('data/graphics/item/focus_band.png'),
    "EVO_LEVEL_PID_LO": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_PID_HI": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_NINJASK": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_SHEDINJA": Path('data/graphics/item/poke_ball.png'),
    "EVO_BEAUTY": Path('data/graphics/item/rare_candy.png'),
    "EVO_STONE_MALE": Path('data/graphics/item/rare_candy.png'),
    "EVO_STONE_FEMALE": Path('data/graphics/item/rare_candy.png'),
    "EVO_ITEM_DAY": Path('data/graphics/item/rare_candy.png'),
    "EVO_ITEM_NIGHT": Path('data/graphics/item/rare_candy.png'),
    "EVO_HAS_MOVE": Path('data/graphics/item/tm001.png'),
    "EVO_OTHER_PARTY_MON": Path('data/graphics/item/friend_ball.png'),
    "EVO_LEVEL_MALE": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_FEMALE": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_ELECTRIC_FIELD": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_MOSSY_STONE": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_ICY_STONE": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_DAY": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_NIGHT": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_DUSK": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_RAIN": Path('data/graphics/item/damp_rock.png'),
    "EVO_HAS_MOVE_TYPE": Path('data/graphics/item/tm125.png'),
    "EVO_LEVEL_DARK_TYPE_MON_IN_PARTY": Path('data/graphics/item/black_glasses.png'),
    "EVO_TRADE_SPECIFIC_MON": Path('data/graphics/item/rare_candy.png'),
    "EVO_LEVEL_NATURE_AMPED": Path('data/graphics/item/naughty_mint.png'),
    "EVO_LEVEL_NATURE_LOW_KEY": Path('data/graphics/item/modest_mint.png'),
    "EVO_AMOUNT_OF_CRITICAL_HITS": Path('data/graphics/item/scope_lens.png'),
    "EVO_HURT_IN_BATTLE_AMOUNT": Path('data/graphics/item/focus_sash.png'),
    "EVO_SPIN_CLOCKWISE_LESS_THAN_5_SECONDS_DAY": Path('data/graphics/item/rare_candy.png'),
    "EVO_SPIN_COUNTERCLOCKWISE_LESS_THAN_5_SECONDS_DAY": Path('data/graphics/item/rare_candy.png'),
    "EVO_SPIN_CLOCKWISE_LESS_THAN_5_SECONDS_NIGHT": Path('data/graphics/item/rare_candy.png'),
    "EVO_SPIN_COUNTERCLOCKWISE_MORE_THAN_5_SECONDS_NIGHT": Path('data/graphics/item/rare_candy.png'),
    "EVO_SPIN_CLOCKWISE_MORE_THAN_5_SECONDS_NIGHT": Path('data/graphics/item/rare_candy.png'),
    "EVO_SPIN_COUNTERCLOCKWISE_LESS_THAN_5_SECONDS_NIGHT": Path('data/graphics/item/rare_candy.png'),
    "EVO_SPIN_COUNTERCLOCKWISE_MORE_THAN_5_SECONDS_DAY": Path('data/graphics/item/rare_candy.png'),
    "EVO_SPIN_CLOCKWISE_MORE_THAN_5_SECONDS_DAY": Path('data/graphics/item/rare_candy.png'),
    "EVO_SPIN_MORE_THAN_10_SECONDS_EVENING": Path('data/graphics/item/rare_candy.png'),
    "EVO_FORM_ARGUMENT": Path('data/graphics/item/rare_candy.png'),
    "EVO_LETS_GO": Path('data/graphics/item/rare_candy.png'),
    "EVO_DUMMY": Path('data/graphics/item/rare_candy.png'),
}

# Default sprite path for unknown methods
EVO_METHOD_SPRITE_DEFAULT = Path('data/graphics/item/rare_candy.png')


def tint_image(image, color):
    """
    Tint an image by multiplying it with a color.
    
    Args:
        image: PIL Image to tint
        color: Tuple of (r, g, b) multipliers, each 0.0 to 1.0+
               e.g., (1.0, 0.3, 0.3) for red tint
               
    Returns:
        New tinted PIL Image
    """
    # Ensure image is in RGBA mode
    img = image.convert("RGBA")
    
    # Split into channels
    r, g, b, a = img.split()
    
    # Apply color multipliers to each channel
    r = r.point(lambda x: min(255, int(x * color[0])))
    g = g.point(lambda x: min(255, int(x * color[1])))
    b = b.point(lambda x: min(255, int(x * color[2])))
    
    # Merge back together
    return Image.merge("RGBA", (r, g, b, a))


def load_config():
    """Load configuration from JSON file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"save_location": ""}


def save_config(config):
    """Save configuration to JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def run_randomizer(seed=None, cwd=None):
    """
    Run the randomizer and capture all output.
    
    Args:
        seed: Optional seed value. If None, a random seed is generated.
        cwd: Working directory to run from (needed for subprocess).
        
    Returns:
        tuple: (seed_used, log_output)
    """
    # Change to correct working directory if specified (for subprocess)
    if cwd:
        os.chdir(cwd)
    
    # Generate seed if not provided
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    else:
        seed = int(seed)
    
    random.seed(seed)
    
    # Capture stdout
    old_stdout = sys.stdout
    captured_output = io.StringIO()
    sys.stdout = captured_output
    
    try:
        print(f"Randomizer version (git SHA): {get_version_sha()}")
        print(f"Random seed: {seed}")
        
        # Load ROM (from current working directory)
        rom_path = Path("raw.nds")
        with open(rom_path, "rb") as f:
            rom = ndspy.rom.NintendoDSRom(f.read())
        
        # Create context with default verbosity
        verbosity_overrides = [([], 2)]  # Default verbosity level
        ctx = RandomizationContext(rom, verbosity_overrides=verbosity_overrides)
        
        # Create filters (all default options - no legendaries allowed)
        legendary_filters = [
            NotInSet(ctx.get(LoadBlacklistStep).by_id),
            NotInSet(ctx.get(InvalidPokemon).by_id),
            NotInSet(ctx.get(RestrictedPokemon).by_id),
            NotInSet(ctx.get(MythicalPokemon).by_id),
            NotInSet(ctx.get(UltraBeastPokemon).by_id),
            NotInSet(ctx.get(ParadoxPokemon).by_id),
            NotInSet(ctx.get(SubLegendaryPokemon).by_id)
        ]
        
        bst_factor = 0.15  # Default
        gym_filter = AllFilters(legendary_filters + [BstWithinFactor(bst_factor)])
        encounter_filter = AllFilters(legendary_filters + [BstWithinFactor(bst_factor)])
        starter_filter = AllFilters(legendary_filters)
        trainer_filter = AllFilters(legendary_filters + [BstWithinFactor(bst_factor)])
        champion_filter = AllFilters(legendary_filters)
        kanto_boss_filter = AllFilters([
            NotInSet(ctx.get(LoadBlacklistStep).by_id),
            NotInSet(ctx.get(InvalidPokemon).by_id),
        ])
        
        # Default multipliers
        trainer_level_mult = 1.15
        wild_level_mult = 1.5
        gift_level_mult = wild_level_mult
        
        # Run pipeline with all default options
        ctx.run_pipeline([
            TrainerMult(multiplier=trainer_level_mult, gauntlet_mode=True),
            ExpandTrainerTeamsStep(bosses_only=False),
            WildMult(multiplier=wild_level_mult),
            RandomizeGymTypesStep(),
            RandomizeGymsStep(gym_filter),
            RandomizeEncountersStep(encounter_filter, True),
            RandomizeWildItemsStep(),
            RandomizeStartersStep(starter_filter),
            SyncStarterVariables(),
            RandomizeOrdinaryTrainersStep(trainer_filter),
            RandomizeChampion(champion_filter),
            ConsistentRivalStarter(),
            ChangeTrainerDataTypeStep(target_flags=TrainerDataType.MOVES | TrainerDataType.ITEMS | TrainerDataType.IV_EV_SET),
            AddPivotStep(gym_filter),
            AddFulcrumStep(gym_filter),
            AddTypeMimicStep(gym_filter),
            RandomizeKantoBossesStep(kanto_boss_filter),
            GeneralEVStep(),
            GeneralIVStep(mode="ScalingIVs"),
            SetTrainerMovesStep(),
            RandomizeTrainerAbilities(mode="randomability_with_hidden"),
            AddStabMovesStep(),
            AssignCustomSetsStep(mode="late_game_bosses"),
            AssignNatureStep(),
            TrainerHeldItem(),
            ApplyBossMegaStonesStep(),
            RandomizeGiftItem(),
            RandomizeGroundItems(),
            RandomizeBerryPiles(),
            RandomizeGiftPokemonStep(encounter_filter, wild_level_mult=gift_level_mult),
            RandomizeStaticPokemonStep(encounter_filter, wild_level_mult=gift_level_mult),
            StaticCries(),
            RandomizeShinyStatic(encounter_filter, wild_level_mult=gift_level_mult),
            RandomizeGiftEggsStep(encounter_filter),
            BillGiftMegaStep(),
            RandomizeStaticLegendaryStep(),
            RandomizeRestrictedLegendaryStep(),
            RandomizeSuicuneStep(),
            UpdateStaticOverworldSprites(),
            SyncLevelCapsWithBosses(),
        ])
        
        ctx.write_all()
        
        # Save modified ROM (to current working directory)
        modified_rom_path = Path("goldilockes.nds")
        with open(modified_rom_path, "wb") as f:
            s = rom.save()
            print(f"Writing {len(s)} bytes to {repr(str(modified_rom_path))} ...")
            f.write(s)
        
        print("Done")
        
    finally:
        # Restore stdout
        sys.stdout = old_stdout
    
    return seed, captured_output.getvalue()


def _randomizer_worker(seed, cwd, result_queue):
    """
    Worker function that runs the randomizer in a separate process.
    
    This function is the entry point for the subprocess. It runs the
    randomization and sends results back through a Queue.
    
    Args:
        seed: The random seed to use (or None for random).
        cwd: The working directory to run from.
        result_queue: A multiprocessing.Queue to send results back.
    """
    try:
        used_seed, log_output = run_randomizer(seed, cwd=cwd)
        result_queue.put({
            'status': 'success',
            'seed': used_seed,
            'log': log_output
        })
    except Exception as e:
        result_queue.put({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        })


class RandomizerApp(ctk.CTk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("Goldilockes Randomizer")
        self.geometry("800x750")
        self.resizable(True, True)
        self.minsize(800, 700)  # Minimum size ensures BST is always visible
        
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Load config
        self.config = load_config()
        
        # Track interactive widgets for disabling during randomization
        self._interactive_widgets = []
        
        # Subprocess state
        self._randomizer_process = None
        self._result_queue = None
        
        # Load tracker data
        self.pokemon_list, self.ability_dict, self.moves_dict, self.tm_move_map, self.form_lookup = load_tracker_data()
        self.filtered_pokemon = self.pokemon_list.copy()
        self.selected_pokemon = None
        
        # Load item data for Items tab
        self.tm_number_to_name = load_tm_number_to_name()
        self.item_tiers = load_item_tiers(self.tm_number_to_name)
        self.mart_items = load_mart_items()
        
        # Load badge image and create tinted versions
        self.badge_image = None
        self.badge_image_red = None
        self.badge_image_green = None
        
        if BADGE_ICON_PATH.exists():
            pil_image = Image.open(BADGE_ICON_PATH)
            # Resize to a reasonable button size
            pil_image = pil_image.resize((150, 150), Image.Resampling.LANCZOS)
            self.pil_badge_original = pil_image  # Keep original for reference
            
            # Create normal, red-tinted, and green-tinted versions
            self.badge_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(150, 150))
            
            # Red tint: boost red, reduce green/blue
            red_tinted = tint_image(pil_image, (1.2, 0.4, 0.4))
            self.badge_image_red = ctk.CTkImage(light_image=red_tinted, dark_image=red_tinted, size=(150, 150))
            
            # Green tint: reduce red, boost green, reduce blue
            green_tinted = tint_image(pil_image, (0.5, 1.3, 0.5))
            self.badge_image_green = ctk.CTkImage(light_image=green_tinted, dark_image=green_tinted, size=(150, 150))
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all UI widgets."""
        
        # Main tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self.tabview.add("Randomizer")
        self.tabview.add("Pokedex")
        self.tabview.add("Items")
        self.tabview.add("Tracker")
        self.tabview.add("Information")
        
        # Build each tab
        self._create_randomizer_tab()
        self._create_pokedex_tab()
        self._create_items_tab()
        self._create_encounter_tracker_tab()
        self._create_information_tab()
    
    def _create_randomizer_tab(self):
        """Create the Randomizer tab with the original UI."""
        tab = self.tabview.tab("Randomizer")
        
        # Main frame with padding
        main_frame = ctk.CTkFrame(tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame, 
            text="Goldilockes Randomizer",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Big badge button
        if self.badge_image:
            self.randomize_btn = ctk.CTkButton(
                main_frame,
                image=self.badge_image,
                text="",
                width=160,
                height=160,
                fg_color="transparent",
                hover_color=("#3a3a3a", "#3a3a3a"),
                command=self._on_randomize
            )
        else:
            # Fallback if image not found
            self.randomize_btn = ctk.CTkButton(
                main_frame,
                text="RANDOMIZE",
                width=160,
                height=160,
                font=ctk.CTkFont(size=18, weight="bold"),
                command=self._on_randomize
            )
        self.randomize_btn.pack(pady=20)
        self._interactive_widgets.append(self.randomize_btn)
        
        # Subtitle under button (hidden during randomization)
        self.subtitle = ctk.CTkLabel(
            main_frame,
            text="Click the badge to randomize!",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.subtitle.pack(pady=(0, 20))
        
        # Small buttons frame (vertical stack)
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=10)
        
        # Choose Save Location (top)
        self.choose_save_btn = ctk.CTkButton(
            buttons_frame,
            text="Choose Save Location",
            width=250,
            command=self._on_choose_save
        )
        self.choose_save_btn.pack(pady=(0, 5))
        self._interactive_widgets.append(self.choose_save_btn)
        
        # Save location display (right under the button)
        self.save_location_label = ctk.CTkLabel(
            buttons_frame,
            text=self._get_save_location_display(),
            font=ctk.CTkFont(size=10),
            text_color="gray",
            wraplength=360
        )
        self.save_location_label.pack(pady=(0, 10))
        
        # Make Backup Save (middle)
        self.backup_btn = ctk.CTkButton(
            buttons_frame,
            text="Make Backup Save",
            width=250,
            command=self._on_backup_save
        )
        self.backup_btn.pack(pady=(0, 2))
        self._interactive_widgets.append(self.backup_btn)
        self._update_backup_button_state()
        
        # Description text below backup button
        backup_desc = ctk.CTkLabel(
            buttons_frame,
            text="creates a duplicate of your current save file\njust in case you get softlocked later",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            justify="center"
        )
        backup_desc.pack(pady=(0, 10))
        
        # Open Goldilockes File Location (bottom)
        self.open_folder_btn = ctk.CTkButton(
            buttons_frame,
            text="Open Goldilockes File Location",
            width=250,
            command=self._on_open_folder
        )
        self.open_folder_btn.pack(pady=(0, 5))
        self._interactive_widgets.append(self.open_folder_btn)
        
        # Options for Nerds - Expandable panel
        self.options_frame = ctk.CTkFrame(main_frame)
        self.options_frame.pack(fill="x", pady=10)
        
        # Header button for expanding/collapsing
        self.options_expanded = False
        self.options_header = ctk.CTkButton(
            self.options_frame,
            text="▶ Options for Nerds",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color=("gray10", "gray90"),  # Dark mode / light mode text colors
            hover_color=("#3a3a3a", "#3a3a3a"),
            anchor="w",
            command=self._toggle_options
        )
        self.options_header.pack(fill="x", padx=5, pady=5)
        self._interactive_widgets.append(self.options_header)
        
        # Options content (initially hidden)
        self.options_content = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        
        # Seed row
        seed_row = ctk.CTkFrame(self.options_content, fg_color="transparent")
        seed_row.pack(fill="x", pady=5, padx=10)
        
        self.use_seed_var = ctk.BooleanVar(value=False)
        self.use_seed_checkbox = ctk.CTkCheckBox(
            seed_row,
            text="Generate from Seed",
            variable=self.use_seed_var,
            command=self._on_seed_checkbox_toggle
        )
        self.use_seed_checkbox.pack(side="left")
        self._interactive_widgets.append(self.use_seed_checkbox)
        
        # Seed entry (initially disabled)
        seed_entry_frame = ctk.CTkFrame(seed_row, fg_color="transparent")
        seed_entry_frame.pack(side="right")
        
        seed_label = ctk.CTkLabel(seed_entry_frame, text="Seed:", font=ctk.CTkFont(size=11))
        seed_label.pack(side="left", padx=(0, 5))
        
        self.seed_entry = ctk.CTkEntry(
            seed_entry_frame,
            width=150,
            state="disabled",
            placeholder_text="Enter seed..."
        )
        self.seed_entry.pack(side="left")
        self._interactive_widgets.append(self.seed_entry)
        
        # Status label at bottom
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="green"
        )
        self.status_label.pack(pady=(10, 0), side="bottom")
    
    def _create_pokedex_tab(self):
        """
        Create the Pokedex tab with Pokemon search and info display.
        
        Layout:
        - Left half: Search bar at top, scrollable Pokemon list below
        - Right half: Tabbed info display (Info, more tabs later)
        """
        tab = self.tabview.tab("Pokedex")
        
        # Main container with two halves
        main_frame = ctk.CTkFrame(tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)  # Left side expands
        main_frame.grid_columnconfigure(1, weight=0, minsize=350)  # Right side fixed width
        main_frame.grid_rowconfigure(0, weight=1)
        
        # === LEFT HALF: Search and Pokemon List ===
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Search bar
        search_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search Pokemon...",
            height=35
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)
        self.search_entry.bind("<Return>", self._on_search_enter)
        
        # Pokemon list - using tkinter Listbox for performance (1000+ items)
        list_frame = ctk.CTkFrame(left_frame)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 10))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Listbox with scrollbar - much faster than 1000+ buttons
        self.pokemon_listbox = tk.Listbox(
            list_frame,
            bg="#2b2b2b",  # Dark background to match theme
            fg="white",
            selectbackground="#1f6aa5",  # CTk blue selection
            selectforeground="white",
            font=("Segoe UI", 11),
            borderwidth=0,
            highlightthickness=0,
            activestyle="none"
        )
        self.pokemon_listbox.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar for the listbox
        listbox_scrollbar = ctk.CTkScrollbar(list_frame, command=self.pokemon_listbox.yview)
        listbox_scrollbar.grid(row=0, column=1, sticky="ns")
        self.pokemon_listbox.configure(yscrollcommand=listbox_scrollbar.set)
        
        # Bind selection event
        self.pokemon_listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        
        # Populate the list
        self._populate_pokemon_list()
        
        # === RIGHT HALF: Pokemon Info Display (fixed width) ===
        right_frame = ctk.CTkFrame(main_frame, width=350)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_frame.grid_propagate(False)  # Prevent frame from shrinking to fit contents
        right_frame.grid_rowconfigure(1, weight=1)  # Tabview row expands
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Header section (sprite, types, and name) - above tabs, always visible
        header_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        # Top row: sprite on left, types on right
        sprite_types_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        sprite_types_frame.pack(pady=(10, 5))
        
        # Pokemon sprite (left side)
        self.sprite_label = ctk.CTkLabel(
            sprite_types_frame,
            text="",  # No text, just image
            image=None
        )
        self.sprite_label.pack(side="left", padx=(0, 10))
        self.current_sprite_image = None  # Keep reference to prevent garbage collection
        
        # Type buttons container (right side, stacked vertically)
        self.types_frame = ctk.CTkFrame(sprite_types_frame, fg_color="transparent")
        self.types_frame.pack(side="left", padx=(10, 0))
        
        # Create placeholder type button widgets (will be updated when Pokemon is selected)
        self.type1_button = None
        self.type2_button = None
        
        # Pokemon name (below sprite and types)
        self.info_name_label = ctk.CTkLabel(
            header_frame,
            text="Select a Pokemon",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.info_name_label.pack(pady=(5, 10))
        
        # Inner tabview for Info/Moves tabs
        self.info_tabview = ctk.CTkTabview(right_frame)
        self.info_tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Create the tabs
        self.info_tabview.add("Info")
        self.info_tabview.add("Moves")
        self.info_tabview.add("Evolution")
        self._create_info_tab()
        self._create_moves_tab()
        self._create_evolution_tab()
        
        # Select first Pokemon by default if available
        if self.pokemon_list:
            self.pokemon_listbox.selection_set(0)
            self._select_pokemon(self.pokemon_list[0])
    
    def _create_items_tab(self):
        """
        Create the Items tab with two subtabs: Item Rarity and Marts.
        
        Item Rarity shows items grouped by tier (Junk, Common, Uncommon, Rare, Master).
        Marts shows items grouped by mart location.
        Both subtabs have hoverable buttons that show item descriptions.
        Both tabs have search filters with fuzzy matching (1 character tolerance).
        """
        tab = self.tabview.tab("Items")
        
        # Store item button references for search filtering
        self.item_rarity_buttons = []  # List of (button, item_name, row_widget) tuples
        self.mart_buttons = []  # List of (button, item_name, location) tuples
        self.mart_sections = {}  # Dict of location -> (header_widget, items_frame_widget)
        
        # Main tabview for subtabs
        self.items_tabview = ctk.CTkTabview(tab)
        self.items_tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create subtabs
        self.items_tabview.add("Item Rarity")
        self.items_tabview.add("Marts")
        
        # Build each subtab
        self._create_item_rarity_tab()
        self._create_marts_tab()
    
    def _create_item_rarity_tab(self):
        """
        Create the Item Rarity subtab with columns for each tier.
        
        Each item is displayed as a hoverable button that shows
        the item's description when hovered over.
        Includes a search bar with fuzzy matching (1 character tolerance).
        """
        tab = self.items_tabview.tab("Item Rarity")
        
        # Search bar at top
        search_frame = ctk.CTkFrame(tab, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.item_rarity_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search items...",
            height=30
        )
        self.item_rarity_search.pack(fill="x")
        self.item_rarity_search.bind("<KeyRelease>", self._on_item_rarity_search)
        
        # Main scrollable frame for the content
        self.item_rarity_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.item_rarity_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Define tier order and display names
        self.tier_order = ['junk', 'common', 'uncommon', 'rare', 'master']
        self.tier_display_names = {
            'junk': 'Junk',
            'common': 'Common',
            'uncommon': 'Uncommon',
            'rare': 'Rare',
            'master': 'Master'
        }
        
        # Configure grid columns for each tier
        for i in range(len(self.tier_order)):
            self.item_rarity_scroll.grid_columnconfigure(i, weight=1)
        
        # Store header labels for reference
        self.tier_headers = {}
        
        # Add tier headers
        for col, tier in enumerate(self.tier_order):
            header = ctk.CTkLabel(
                self.item_rarity_scroll,
                text=self.tier_display_names.get(tier, tier.title()),
                font=ctk.CTkFont(size=14, weight="bold")
            )
            header.grid(row=0, column=col, padx=5, pady=(5, 10), sticky="n")
            self.tier_headers[tier] = header
        
        # Add items to each column
        for col, tier in enumerate(self.tier_order):
            items = self.item_tiers.get(tier, [])
            
            for row, item_name in enumerate(items, start=1):
                # Create item button
                btn = ctk.CTkButton(
                    self.item_rarity_scroll,
                    text=item_name,
                    font=ctk.CTkFont(size=10),
                    fg_color="gray30",
                    hover_color="gray40",
                    height=24,
                    width=120,
                    anchor="w",
                    command=lambda: None  # No action on click
                )
                btn.grid(row=row, column=col, padx=3, pady=1, sticky="ew")
                
                # Store button reference with item name and tier for filtering
                self.item_rarity_buttons.append((btn, item_name, tier, col))
    
    def _on_item_rarity_search(self, event=None):
        """
        Handle search in Item Rarity tab with fuzzy matching.
        
        Shows/hides items based on the search query with 1 character tolerance.
        """
        query = self.item_rarity_search.get().strip().lower()
        
        # Track visible items per tier for re-gridding
        tier_visible_rows = {tier: 1 for tier in self.tier_order}  # Start at row 1 (after header)
        
        for btn, item_name, tier, col in self.item_rarity_buttons:
            if not query or fuzzy_match(query, item_name, max_diff=1):
                # Show this item
                btn.grid(row=tier_visible_rows[tier], column=col, padx=3, pady=1, sticky="ew")
                tier_visible_rows[tier] += 1
            else:
                # Hide this item
                btn.grid_remove()
    
    def _create_marts_tab(self):
        """
        Create the Marts subtab with sections for each mart location.
        
        Each mart is displayed as a section with its items listed below.
        Items are hoverable buttons that show descriptions.
        Includes a search bar with fuzzy matching (1 character tolerance).
        Locations appear in the order they first appear in the CSV.
        """
        tab = self.items_tabview.tab("Marts")
        
        # Search bar at top
        search_frame = ctk.CTkFrame(tab, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.mart_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search items...",
            height=30
        )
        self.mart_search.pack(fill="x")
        self.mart_search.bind("<KeyRelease>", self._on_mart_search)
        
        # Main scrollable frame for the content
        self.mart_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.mart_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configure grid column
        self.mart_scroll.grid_columnconfigure(0, weight=1)
        
        row_idx = 0
        
        # Preserve order from CSV (Python 3.7+ dicts maintain insertion order)
        # Use the mart_items dict directly - load_mart_items() already preserves order
        for location in self.mart_items.keys():
            items = self.mart_items[location]
            
            # Section header for this mart
            header = ctk.CTkLabel(
                self.mart_scroll,
                text=location,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            header.grid(row=row_idx, column=0, padx=5, pady=(15, 5), sticky="w")
            row_idx += 1
            
            # Create a frame to hold items in a grid (multiple columns)
            items_frame = ctk.CTkFrame(self.mart_scroll, fg_color="transparent")
            items_frame.grid(row=row_idx, column=0, sticky="ew", padx=5)
            row_idx += 1
            
            # Store section references for search filtering
            self.mart_sections[location] = (header, items_frame)
            
            # Configure columns in items frame (3 columns)
            for i in range(3):
                items_frame.grid_columnconfigure(i, weight=1)
            
            # Add items to the frame
            for i, item_name in enumerate(items):
                item_row = i // 3
                item_col = i % 3
                
                # Create item button
                btn = ctk.CTkButton(
                    items_frame,
                    text=item_name,
                    font=ctk.CTkFont(size=10),
                    fg_color="gray30",
                    hover_color="gray40",
                    height=24,
                    width=120,
                    anchor="w",
                    command=lambda: None  # No action on click
                )
                btn.grid(row=item_row, column=item_col, padx=3, pady=1, sticky="ew")
                
                # Store button reference with item name and location for filtering
                self.mart_buttons.append((btn, item_name, location, items_frame))
    
    def _on_mart_search(self, event=None):
        """
        Handle search in Marts tab with fuzzy matching.
        
        Shows/hides items based on the search query with 1 character tolerance.
        Also hides section headers if no items in that section match.
        """
        query = self.mart_search.get().strip().lower()
        
        # Track visible items per location for re-gridding
        location_visible = {loc: [] for loc in self.mart_items.keys()}
        
        for btn, item_name, location, items_frame in self.mart_buttons:
            if not query or fuzzy_match(query, item_name, max_diff=1):
                # Mark this item as visible
                location_visible[location].append((btn, item_name))
            else:
                # Hide this item
                btn.grid_remove()
        
        # Re-grid visible items and update section visibility
        for location, visible_items in location_visible.items():
            header, items_frame = self.mart_sections[location]
            
            if visible_items:
                # Show header and re-grid items
                header.grid()
                items_frame.grid()
                
                for i, (btn, item_name) in enumerate(visible_items):
                    item_row = i // 3
                    item_col = i % 3
                    btn.grid(row=item_row, column=item_col, padx=3, pady=1, sticky="ew")
            else:
                # Hide entire section if no items match
                header.grid_remove()
                items_frame.grid_remove()
    
    def _create_info_tab(self):
        """Create the Info sub-tab inside the Pokedex's right panel."""
        tab = self.info_tabview.tab("Info")
        
        # Main scrollable container to ensure all content (including BST) is always accessible
        info_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        info_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Abilities section
        abilities_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        abilities_frame.pack(fill="x", pady=5)
        
        # Non-hidden abilities row
        self.abilities_label = ctk.CTkLabel(
            abilities_frame,
            text="Abilities:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.abilities_label.pack(anchor="w")
        
        self.abilities_row = ctk.CTkFrame(abilities_frame, fg_color="transparent")
        self.abilities_row.pack(fill="x", pady=5)
        
        # Ability buttons
        self.ability1_btn = ctk.CTkButton(
            self.abilities_row,
            text="---",
            fg_color="gray30",
            hover_color="gray40",
            width=150
        )
        self.ability1_btn.pack(side="left", padx=5)
        
        self.ability2_btn = ctk.CTkButton(
            self.abilities_row,
            text="---",
            fg_color="gray30",
            hover_color="gray40",
            width=150
        )
        self.ability2_btn.pack(side="left", padx=5)
        
        # Hidden ability row
        self.hidden_ability_label = ctk.CTkLabel(
            abilities_frame,
            text="Hidden Ability:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.hidden_ability_label.pack(anchor="w", pady=(10, 0))
        
        self.hidden_ability_row = ctk.CTkFrame(abilities_frame, fg_color="transparent")
        self.hidden_ability_row.pack(fill="x", pady=5)
        
        self.hidden_ability_btn = ctk.CTkButton(
            self.hidden_ability_row,
            text="No Hidden Ability",
            fg_color="gray30",
            hover_color="gray40",
            width=150
        )
        self.hidden_ability_btn.pack(side="left", padx=5)
        
        # Create tooltips for ability buttons (created once, text updated when Pokemon changes)
        self.ability1_tooltip = ToolTip(self.ability1_btn)
        self.ability2_tooltip = ToolTip(self.ability2_btn)
        self.hidden_ability_tooltip = ToolTip(self.hidden_ability_btn)
        
        # Base stats section (2x3 grid)
        stats_label = ctk.CTkLabel(
            info_frame,
            text="Base Stats:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        stats_label.pack(anchor="w", pady=(10, 5))
        
        stats_grid = ctk.CTkFrame(info_frame, fg_color="transparent")
        stats_grid.pack(fill="x", pady=5)
        
        # Configure grid columns
        for i in range(3):
            stats_grid.grid_columnconfigure(i, weight=1)
        
        # Create stat labels (2 rows x 3 columns)
        # Row 1: HP, Atk, Def
        # Row 2: Sp.Atk, Sp.Def, Speed
        self.stat_labels = {}
        stat_names = [
            ('hp', 'HP'), ('atk', 'Atk'), ('def', 'Def'),
            ('sp_atk', 'Sp. Atk'), ('sp_def', 'Sp. Def'), ('speed', 'Speed')
        ]
        
        for i, (key, display_name) in enumerate(stat_names):
            row = i // 3
            col = i % 3
            
            stat_frame = ctk.CTkFrame(stats_grid, fg_color="gray25")
            stat_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            
            name_label = ctk.CTkLabel(
                stat_frame,
                text=display_name,
                font=ctk.CTkFont(size=11)
            )
            name_label.pack(pady=(5, 0))
            
            value_label = ctk.CTkLabel(
                stat_frame,
                text="---",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            value_label.pack(pady=(0, 5))
            
            self.stat_labels[key] = value_label
        
        # BST (base stat total) - larger at bottom center
        # Use a minimum width to ensure consistent sizing
        bst_frame = ctk.CTkFrame(info_frame, fg_color="gray20")
        bst_frame.pack(pady=(10, 5), ipadx=30, ipady=5)
        
        bst_title = ctk.CTkLabel(
            bst_frame,
            text="BST",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        bst_title.pack(pady=(5, 0))
        
        self.bst_label = ctk.CTkLabel(
            bst_frame,
            text="---",
            font=ctk.CTkFont(size=28, weight="bold"),
            width=80  # Minimum width to fit 3-digit numbers comfortably
        )
        self.bst_label.pack(pady=(0, 5))
    
    def _create_moves_tab(self):
        """Create the Moves sub-tab inside the Pokedex's right panel."""
        tab = self.info_tabview.tab("Moves")
        
        # Main container with scrollable frame for the moves list
        self.moves_scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.moves_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configure grid columns: Level (narrow) | Move Name (wider)
        self.moves_scroll_frame.grid_columnconfigure(0, weight=0, minsize=40)  # Level column
        self.moves_scroll_frame.grid_columnconfigure(1, weight=1)  # Move name column
        
        # Store move button tooltips to keep them alive
        self.move_tooltips = []
    
    def _update_moves_display(self, pokemon):
        """Update the Moves tab to show the selected Pokemon's level-up and machine moves."""
        # Clear existing move widgets
        for widget in self.moves_scroll_frame.winfo_children():
            widget.destroy()
        self.move_tooltips.clear()
        
        # Get level moves and machine moves for this Pokemon
        level_moves = pokemon.get('level_moves', [])
        machine_moves = pokemon.get('machine_moves', [])
        
        row_index = 0  # Track current row for grid placement
        
        # === Level-up Moves Section ===
        if level_moves:
            # Create a row for each level-up move
            for move_entry in level_moves:
                level = move_entry.get('level', 0)
                move_const = move_entry.get('move', '')
                
                # Get move data from moves_dict
                move_data = self.moves_dict.get(move_const, {})
                move_name = move_data.get('name', move_const.replace('MOVE_', '').replace('_', ' ').title())
                
                # Level label (left column)
                level_text = str(level) if level > 0 else "Evo"  # Level 0 = evolution move
                level_label = ctk.CTkLabel(
                    self.moves_scroll_frame,
                    text=level_text,
                    font=ctk.CTkFont(size=11),
                    width=35,
                    anchor="e"
                )
                level_label.grid(row=row_index, column=0, padx=(5, 10), pady=2, sticky="e")
                
                # Move name button (right column) with tooltip
                move_btn = ctk.CTkButton(
                    self.moves_scroll_frame,
                    text=move_name,
                    font=ctk.CTkFont(size=11),
                    fg_color="gray30",
                    hover_color="gray40",
                    height=28,
                    anchor="w",
                    command=lambda: None  # No action on click, just for tooltip
                )
                move_btn.grid(row=row_index, column=1, padx=(0, 5), pady=2, sticky="ew")
                
                # Create tooltip for this move button
                tooltip = MoveToolTip(move_btn)
                tooltip.set_move_data(move_data)
                self.move_tooltips.append(tooltip)
                
                row_index += 1
        
        # === Machine Moves Section ===
        if machine_moves:
            # Add separator and header if there were level moves
            if level_moves:
                separator = ctk.CTkFrame(self.moves_scroll_frame, height=2, fg_color="gray50")
                separator.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=(15, 5), padx=5)
                row_index += 1
            
            # Section header
            tm_header = ctk.CTkLabel(
                self.moves_scroll_frame,
                text="TM/HM Moves",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="gray70"
            )
            tm_header.grid(row=row_index, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 10))
            row_index += 1
            
            # Build list of machine moves with their TM numbers, then sort by TM number
            tm_entries = []
            for move_const in machine_moves:
                tm_info = self.tm_move_map.get(move_const, None)
                if tm_info:
                    tm_entries.append((tm_info['kind'], tm_info['number'], move_const))
            
            # Sort by kind (TM before HM) then by number
            tm_entries.sort(key=lambda x: (0 if x[0] == 'TM' else 1, x[1]))
            
            # Create a row for each machine move
            for kind, number, move_const in tm_entries:
                # Get move data from moves_dict
                move_data = self.moves_dict.get(move_const, {})
                move_name = move_data.get('name', move_const.replace('MOVE_', '').replace('_', ' ').title())
                
                # TM/HM number label (left column)
                tm_text = f"{kind}{number:02d}"  # e.g., "TM07" or "HM01"
                tm_label = ctk.CTkLabel(
                    self.moves_scroll_frame,
                    text=tm_text,
                    font=ctk.CTkFont(size=11),
                    width=45,
                    anchor="e"
                )
                tm_label.grid(row=row_index, column=0, padx=(5, 10), pady=2, sticky="e")
                
                # Move name button (right column) with tooltip
                move_btn = ctk.CTkButton(
                    self.moves_scroll_frame,
                    text=move_name,
                    font=ctk.CTkFont(size=11),
                    fg_color="gray30",
                    hover_color="gray40",
                    height=28,
                    anchor="w",
                    command=lambda: None  # No action on click, just for tooltip
                )
                move_btn.grid(row=row_index, column=1, padx=(0, 5), pady=2, sticky="ew")
                
                # Create tooltip for this move button
                tooltip = MoveToolTip(move_btn)
                tooltip.set_move_data(move_data)
                self.move_tooltips.append(tooltip)
                
                row_index += 1
        
        # If no moves at all, show a message
        if not level_moves and not machine_moves:
            no_moves_label = ctk.CTkLabel(
                self.moves_scroll_frame,
                text="No moves data available",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            no_moves_label.grid(row=0, column=0, columnspan=2, pady=20)
    
    def _create_evolution_tab(self):
        """Create the Evolution sub-tab inside the Pokedex's right panel."""
        tab = self.info_tabview.tab("Evolution")
        
        # Main container with scrollable frame for the evolution list
        self.evo_scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.evo_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configure grid columns: Method sprite | Evolved form sprite
        self.evo_scroll_frame.grid_columnconfigure(0, weight=0, minsize=50)  # Method sprite column
        self.evo_scroll_frame.grid_columnconfigure(1, weight=1)  # Evolved form column
        
        # Store evolution tooltips to keep them alive
        self.evo_tooltips = []
        
        # Load all evolution method sprites into a dictionary
        self.evo_method_sprites = {}
        for method, sprite_path in EVO_METHOD_SPRITES.items():
            if sprite_path.exists():
                try:
                    pil_image = Image.open(sprite_path)
                    # Scale to reasonable button size
                    pil_image = pil_image.resize((32, 32), Image.Resampling.LANCZOS)
                    self.evo_method_sprites[method] = ctk.CTkImage(
                        light_image=pil_image,
                        dark_image=pil_image,
                        size=(32, 32)
                    )
                except Exception:
                    pass
        
        # Load default sprite for unknown methods
        self.evo_method_sprite_default = None
        if EVO_METHOD_SPRITE_DEFAULT.exists():
            try:
                pil_image = Image.open(EVO_METHOD_SPRITE_DEFAULT)
                pil_image = pil_image.resize((32, 32), Image.Resampling.LANCZOS)
                self.evo_method_sprite_default = ctk.CTkImage(
                    light_image=pil_image,
                    dark_image=pil_image,
                    size=(32, 32)
                )
            except Exception:
                pass
    
    def _update_evolutions_display(self, pokemon):
        """Update the Evolution tab to show the selected Pokemon's evolutions."""
        # Clear existing evolution widgets
        for widget in self.evo_scroll_frame.winfo_children():
            widget.destroy()
        self.evo_tooltips.clear()
        
        # Get evolutions for this Pokemon
        evolutions = pokemon.get('evolutions', [])
        
        if not evolutions:
            # Show a message if no evolutions
            no_evo_label = ctk.CTkLabel(
                self.evo_scroll_frame,
                text="No evolutions",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            no_evo_label.grid(row=0, column=0, columnspan=2, pady=20)
            return
        
        # Create a row for each evolution
        for row_index, evo in enumerate(evolutions):
            method = evo.get('method', 'EVO_NONE')
            parameter = evo.get('parameter', '')
            target_species = evo.get('target', 'SPECIES_NONE')
            target_form = evo.get('form')  # None, 0, 1, 2, etc.
            
            # Create row frame
            row_frame = ctk.CTkFrame(self.evo_scroll_frame, fg_color="transparent")
            row_frame.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=5)
            row_frame.grid_columnconfigure(0, weight=0)
            row_frame.grid_columnconfigure(1, weight=1)
            
            # === Left button: Evolution method sprite with tooltip ===
            # Check if this evolution uses an item parameter - if so, show the item sprite
            method_sprite = None
            if parameter.startswith('ITEM_'):
                # Try to load the item's sprite
                item_name = parameter.replace('ITEM_', '').lower()
                item_sprite_path = Path('data/graphics/item') / f'{item_name}.png'
                if item_sprite_path.exists():
                    try:
                        pil_image = Image.open(item_sprite_path)
                        pil_image = pil_image.resize((32, 32), Image.Resampling.LANCZOS)
                        method_sprite = ctk.CTkImage(
                            light_image=pil_image,
                            dark_image=pil_image,
                            size=(32, 32)
                        )
                    except Exception:
                        pass
            
            # Fall back to the method sprite if no item sprite was loaded
            if method_sprite is None:
                method_sprite = self.evo_method_sprites.get(method, self.evo_method_sprite_default)
            
            method_btn = ctk.CTkButton(
                row_frame,
                text="",
                image=method_sprite,
                width=40,
                height=40,
                fg_color="gray30",
                hover_color="gray40",
                command=lambda: None  # No action on click
            )
            method_btn.grid(row=0, column=0, padx=(5, 10))
            
            # Format tooltip text - replace {param} with actual parameter
            tooltip_template = EVO_METHOD_TOOLTIPS.get(method, f"Unknown method: {method}")
            # Format the parameter nicely (remove ITEM_ or MOVE_ prefixes)
            param_display = parameter
            if param_display.startswith('ITEM_'):
                param_display = param_display.replace('ITEM_', '').replace('_', ' ').title()
            elif param_display.startswith('MOVE_'):
                param_display = param_display.replace('MOVE_', '').replace('_', ' ').title()
            elif param_display.startswith('SPECIES_'):
                param_display = param_display.replace('SPECIES_', '').replace('_', ' ').title()
            elif param_display.startswith('TYPE_'):
                param_display = param_display.replace('TYPE_', '').title()
            tooltip_text = tooltip_template.replace('{param}', param_display)
            
            # Create tooltip for method button
            method_tooltip = EvoToolTip(method_btn)
            method_tooltip.set_text(tooltip_text)
            self.evo_tooltips.append(method_tooltip)
            
            # === Right button: Evolved form sprite with tooltip and navigation ===
            # Find the evolved Pokemon in our list to get its sprite
            # Use form_lookup when form > 0 to get the correct alternate form
            evolved_pokemon = None
            evolved_sprite = None
            evolved_name = target_species.replace('SPECIES_', '').replace('_', ' ').title()
            
            # Try to find the evolved Pokemon using form_lookup first
            # form_lookup maps (base_species_const, form_number) to the actual Pokemon
            form_num = target_form if target_form is not None else 0
            lookup_key = (target_species, form_num)
            
            if lookup_key in self.form_lookup:
                # Found in form_lookup - this handles both base forms and alternate forms
                evolved_pokemon = self.form_lookup[lookup_key]
                evolved_name = evolved_pokemon.get('name', evolved_name)
            else:
                # Fall back to direct species_const match (for Pokemon not in form_lookup)
                for poke in self.pokemon_list:
                    if poke.get('species_const') == target_species:
                        evolved_pokemon = poke
                        evolved_name = poke.get('name', evolved_name)
                        break
            
            # Load evolved form sprite if we found the Pokemon
            if evolved_pokemon:
                sprite_name = evolved_pokemon.get('sprite_name', '')
                sprite_path = SPRITES_DIR / sprite_name / 'icon.png'
                
                if sprite_path.exists():
                    try:
                        pil_image = Image.open(sprite_path)
                        # Crop to first frame if it's a sprite sheet
                        width, height = pil_image.size
                        if height > width:
                            pil_image = pil_image.crop((0, 0, width, height // 2))
                        # Scale up for visibility
                        new_width = pil_image.width * 2
                        new_height = pil_image.height * 2
                        pil_image = pil_image.resize((new_width, new_height), Image.Resampling.NEAREST)
                        evolved_sprite = ctk.CTkImage(
                            light_image=pil_image,
                            dark_image=pil_image,
                            size=(new_width, new_height)
                        )
                    except Exception:
                        pass
            
            # Create the evolved form button
            # Capture evolved_pokemon in the lambda's default argument to avoid closure issue
            evo_btn = ctk.CTkButton(
                row_frame,
                text=evolved_name if not evolved_sprite else "",
                image=evolved_sprite,
                width=120,
                height=64,
                fg_color="gray30",
                hover_color="gray40",
                anchor="center",
                command=lambda p=evolved_pokemon: self._navigate_to_pokemon(p) if p else None
            )
            evo_btn.grid(row=0, column=1, padx=(0, 5), sticky="w")
            
            # Create simple tooltip showing evolved form name
            evo_name_tooltip = ToolTip(evo_btn)
            evo_name_tooltip.set_text(evolved_name)
            self.evo_tooltips.append(evo_name_tooltip)
    
    def _create_encounter_tracker_tab(self):
        """
        Create the Tracker tab for tracking Pokemon encounters during a run.
        
        Layout:
        - Left half: Wild Encounters with Area/Pokemon/button columns
        - Right half: Gift, Static, and ??? (Legendary) sections
        - Top right: New Run, Past Runs, Back to Current Run buttons
        """
        tab = self.tabview.tab("Tracker")
        
        # Load tracker encounters from CSV
        self.tracker_encounters = self._load_tracker_encounters()
        
        # Load tracker data from JSON
        self.tracker_data = self._load_tracker_json()
        
        # Track read-only mode state
        self.tracker_read_only = False
        self.tracker_viewing_file = None  # Which past run file we're viewing
        
        # Store references to Pokemon buttons for updating
        self.tracker_pokemon_buttons = {}
        
        # Main container
        main_frame = ctk.CTkFrame(tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)  # Left side
        main_frame.grid_columnconfigure(1, weight=1)  # Right side
        main_frame.grid_rowconfigure(0, weight=1)
        
        # === LEFT HALF: Wild Encounters ===
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_frame.grid_rowconfigure(2, weight=1)  # Scrollable frame row expands
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Title for Wild Encounters
        wild_title = ctk.CTkLabel(
            left_frame,
            text="Wild Encounters",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        wild_title.grid(row=0, column=0, pady=(10, 5))
        
        # Column headers
        header_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        header_frame.grid(row=1, column=0, sticky="ew", padx=10)
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=2)
        header_frame.grid_columnconfigure(2, weight=0, minsize=40)
        
        ctk.CTkLabel(header_frame, text="Area", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", padx=5)
        ctk.CTkLabel(header_frame, text="Pokemon", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=1, sticky="w", padx=5)
        
        # Scrollable frame for wild encounters
        wild_scroll = ctk.CTkScrollableFrame(left_frame)
        wild_scroll.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        wild_scroll.grid_columnconfigure(0, weight=1)
        wild_scroll.grid_columnconfigure(1, weight=2)
        wild_scroll.grid_columnconfigure(2, weight=0, minsize=40)
        
        self.wild_scroll_frame = wild_scroll
        
        # === RIGHT HALF: Gift, Static, Legendary + Buttons ===
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Top right buttons frame
        buttons_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        buttons_frame.grid(row=0, column=0, sticky="ne", padx=10, pady=10)
        
        # New Run button
        self.new_run_btn = ctk.CTkButton(
            buttons_frame,
            text="New Run",
            width=120,
            command=self._on_new_run
        )
        self.new_run_btn.pack(pady=(0, 5))
        
        # Past Runs dropdown
        self.past_runs_var = ctk.StringVar(value="Past Runs")
        self.past_runs_dropdown = ctk.CTkOptionMenu(
            buttons_frame,
            variable=self.past_runs_var,
            values=["Past Runs"],
            width=120,
            command=self._on_past_run_selected
        )
        self.past_runs_dropdown.pack(pady=(0, 5))
        self._refresh_past_runs_dropdown()
        
        # Back to Current Run button (hidden initially)
        self.back_to_current_btn = ctk.CTkButton(
            buttons_frame,
            text="Back to Current Run",
            width=120,
            fg_color="green",
            hover_color="darkgreen",
            command=self._on_back_to_current_run
        )
        # Don't pack initially - shown only in read-only mode
        
        # Scrollable frame for right side encounters
        right_scroll = ctk.CTkScrollableFrame(right_frame)
        right_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        right_scroll.grid_columnconfigure(0, weight=1)
        right_scroll.grid_columnconfigure(1, weight=2)
        right_scroll.grid_columnconfigure(2, weight=0, minsize=40)
        
        self.right_scroll_frame = right_scroll
        
        # Populate encounter lists
        self._populate_tracker_encounters()
    
    def _load_tracker_encounters(self):
        """
        Load encounter locations from TrackerEncs.csv.
        
        Returns:
            dict: Categorized encounters - 'wild', 'gift', 'static', 'legendary'
        """
        encounters = {'wild': [], 'gift': [], 'static': [], 'legendary': []}
        
        if not TRACKER_ENCS_FILE.exists():
            return encounters
        
        with open(TRACKER_ENCS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Parse: "AreaName,Category" format (e.g., "29,Wild" or "Starter,Gift")
                parts = line.split(',')
                if len(parts) >= 2:
                    area_name = parts[0].strip()
                    category = parts[1].strip().lower()
                    if category in encounters:
                        encounters[category].append(area_name)
        
        return encounters
    
    def _load_tracker_json(self):
        """
        Load tracker data from TrackerData.json.
        
        Returns:
            dict: The tracker data with wild, gift, static, legendary sections
        """
        if TRACKER_DATA_FILE.exists():
            try:
                with open(TRACKER_DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Return default empty structure
        return {'wild': {}, 'gift': {}, 'static': {}, 'legendary': {}}
    
    def _save_tracker_json(self, data=None):
        """
        Save tracker data to TrackerData.json.
        
        Args:
            data: The data to save. If None, saves self.tracker_data.
        """
        if data is None:
            data = self.tracker_data
        
        with open(TRACKER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def _populate_tracker_encounters(self):
        """Populate both encounter scrollable frames with buttons."""
        # Clear existing widgets
        for widget in self.wild_scroll_frame.winfo_children():
            widget.destroy()
        for widget in self.right_scroll_frame.winfo_children():
            widget.destroy()
        self.tracker_pokemon_buttons.clear()
        
        # Populate wild encounters (left side)
        for row_idx, area in enumerate(self.tracker_encounters.get('wild', [])):
            self._create_encounter_row(self.wild_scroll_frame, row_idx, area, 'wild')
        
        # Populate right side (Gift, Static, Legendary)
        row_idx = 0
        
        # Gift section header
        gift_header = ctk.CTkLabel(
            self.right_scroll_frame,
            text="Gift Pokemon",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        gift_header.grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=5, pady=(10, 5))
        row_idx += 1
        
        for area in self.tracker_encounters.get('gift', []):
            self._create_encounter_row(self.right_scroll_frame, row_idx, area, 'gift')
            row_idx += 1
        
        # Static section header
        static_header = ctk.CTkLabel(
            self.right_scroll_frame,
            text="Static Pokemon",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        static_header.grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=5, pady=(15, 5))
        row_idx += 1
        
        for area in self.tracker_encounters.get('static', []):
            self._create_encounter_row(self.right_scroll_frame, row_idx, area, 'static')
            row_idx += 1
        
        # Legendary section header (labeled "???")
        legend_header = ctk.CTkLabel(
            self.right_scroll_frame,
            text="???",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        legend_header.grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=5, pady=(15, 5))
        row_idx += 1
        
        for area in self.tracker_encounters.get('legendary', []):
            self._create_encounter_row(self.right_scroll_frame, row_idx, area, 'legendary')
            row_idx += 1
    
    def _create_encounter_row(self, parent, row_idx, area, category):
        """
        Create a single encounter row with area label and Pokemon button.
        
        Args:
            parent: Parent frame to add widgets to
            row_idx: Row index in the grid
            area: Area name string
            category: 'wild', 'gift', 'static', or 'legendary'
        """
        # Area label (show "????" for legendary encounters)
        display_area = "????" if category == "legendary" else area
        area_label = ctk.CTkLabel(
            parent,
            text=display_area,
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        area_label.grid(row=row_idx, column=0, sticky="w", padx=5, pady=2)
        
        # Get current Pokemon for this slot
        pokemon_name = self.tracker_data.get(category, {}).get(area, None)
        display_text = pokemon_name if pokemon_name else "---"
        
        # Pokemon button (clickable to change)
        pokemon_btn = ctk.CTkButton(
            parent,
            text=display_text,
            font=ctk.CTkFont(size=11),
            fg_color="gray30" if not self.tracker_read_only else "gray20",
            hover_color="gray40" if not self.tracker_read_only else "gray20",
            height=28,
            anchor="w",
            command=lambda a=area, c=category: self._on_pokemon_slot_click(a, c)
        )
        pokemon_btn.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=2)
        
        # Store reference for later updates
        self.tracker_pokemon_buttons[(category, area)] = pokemon_btn
        
        # Disable button in read-only mode
        if self.tracker_read_only:
            pokemon_btn.configure(state="disabled")
    
    def _on_pokemon_slot_click(self, area, category):
        """
        Handle click on a Pokemon slot button - opens search popup.
        
        Args:
            area: The area name for this slot
            category: 'wild', 'gift', 'static', or 'legendary'
        """
        if self.tracker_read_only:
            return
        
        # Create popup window for Pokemon search
        self._open_pokemon_search_popup(area, category)
    
    def _open_pokemon_search_popup(self, area, category):
        """
        Open a popup window with Pokemon search similar to Pokedex tab.
        
        Args:
            area: The area name for this slot
            category: 'wild', 'gift', 'static', or 'legendary'
        """
        popup = ctk.CTkToplevel(self)
        popup.title(f"Select Pokemon - {area}")
        popup.geometry("300x400")
        popup.transient(self)  # Stay on top of main window
        popup.grab_set()  # Modal - block interaction with main window
        
        # Center the popup on the main window
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 300) // 2
        y = self.winfo_y() + (self.winfo_height() - 400) // 2
        popup.geometry(f"300x400+{x}+{y}")
        
        # Search entry
        search_frame = ctk.CTkFrame(popup, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=10)
        
        search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search Pokemon...",
            height=35
        )
        search_entry.pack(fill="x")
        search_entry.focus()
        
        # Pokemon listbox
        list_frame = ctk.CTkFrame(popup)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        pokemon_listbox = tk.Listbox(
            list_frame,
            bg="#2b2b2b",
            fg="white",
            selectbackground="#1f6aa5",
            selectforeground="white",
            font=("Segoe UI", 11),
            borderwidth=0,
            highlightthickness=0,
            activestyle="none"
        )
        pokemon_listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = ctk.CTkScrollbar(list_frame, command=pokemon_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        pokemon_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Local filtered list
        popup_filtered = self.pokemon_list.copy()
        
        def populate_list(filtered_list):
            pokemon_listbox.delete(0, tk.END)
            for poke in filtered_list:
                name = poke['name']
                if len(name) > 20:
                    name = name[:20] + "..."
                pokemon_listbox.insert(tk.END, name)
        
        def on_search_changed(event=None):
            nonlocal popup_filtered
            query = search_entry.get().strip()
            if not query:
                popup_filtered = self.pokemon_list.copy()
            else:
                popup_filtered = [
                    poke for poke in self.pokemon_list
                    if fuzzy_match(query, poke['name'])
                ]
            populate_list(popup_filtered)
        
        def on_select(event=None):
            selection = pokemon_listbox.curselection()
            if selection and selection[0] < len(popup_filtered):
                selected_pokemon = popup_filtered[selection[0]]
                self._set_tracker_pokemon(area, category, selected_pokemon['name'])
                popup.destroy()
        
        def on_enter(event=None):
            if popup_filtered:
                # Select first item
                self._set_tracker_pokemon(area, category, popup_filtered[0]['name'])
                popup.destroy()
        
        # Bind events
        search_entry.bind("<KeyRelease>", on_search_changed)
        search_entry.bind("<Return>", on_enter)
        pokemon_listbox.bind("<Double-Button-1>", on_select)
        pokemon_listbox.bind("<Return>", on_select)
        
        # Populate initial list
        populate_list(popup_filtered)
    
    def _set_tracker_pokemon(self, area, category, pokemon_name):
        """
        Set a Pokemon for a tracker slot and update the UI.
        
        Args:
            area: The area name
            category: 'wild', 'gift', 'static', or 'legendary'
            pokemon_name: The name of the Pokemon to set
        """
        # Update data
        if category not in self.tracker_data:
            self.tracker_data[category] = {}
        self.tracker_data[category][area] = pokemon_name
        
        # Save to JSON
        self._save_tracker_json()
        
        # Update button text
        btn_key = (category, area)
        if btn_key in self.tracker_pokemon_buttons:
            self.tracker_pokemon_buttons[btn_key].configure(text=pokemon_name)
    
    def _on_new_run(self):
        """
        Handle New Run button - save current tracker and start fresh.
        
        1. Save current tracker with timestamp filename
        2. Delete oldest if more than 10 tracker files exist
        3. Clear current tracker data
        """
        if self.tracker_read_only:
            # If viewing past run, exit that mode first
            self._on_back_to_current_run()
        
        # Generate timestamp filename
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        backup_name = f"TrackerData_{timestamp}.json"
        backup_path = Path('gl') / backup_name
        
        # Save current tracker as backup
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(self.tracker_data, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save tracker backup:\n{e}")
            return
        
        # Check for excess tracker files (delete oldest if > 10)
        self._cleanup_old_tracker_files()
        
        # Clear current tracker
        for category in self.tracker_data:
            for area in self.tracker_data[category]:
                self.tracker_data[category][area] = None
        
        # Save cleared tracker
        self._save_tracker_json()
        
        # Refresh UI
        self._populate_tracker_encounters()
        self._refresh_past_runs_dropdown()
    
    def _cleanup_old_tracker_files(self):
        """Delete oldest tracker backup files if there are more than 10."""
        gl_dir = Path('gl')
        tracker_files = sorted(
            gl_dir.glob("TrackerData_*.json"),
            key=lambda f: f.stat().st_mtime
        )
        
        # Keep only the 10 most recent
        while len(tracker_files) > 10:
            oldest = tracker_files.pop(0)
            try:
                oldest.unlink()
            except Exception:
                pass
    
    def _refresh_past_runs_dropdown(self):
        """Refresh the Past Runs dropdown with available tracker files."""
        gl_dir = Path('gl')
        tracker_files = sorted(
            gl_dir.glob("TrackerData_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True  # Most recent first
        )
        
        if tracker_files:
            # Format display names nicely
            display_names = []
            for f in tracker_files:
                # Extract timestamp from filename: TrackerData_2026-08-17T13-05-30.json
                name = f.stem.replace("TrackerData_", "")
                display_names.append(name)
            
            self.past_runs_dropdown.configure(values=["Past Runs"] + display_names)
        else:
            self.past_runs_dropdown.configure(values=["Past Runs"])
        
        self.past_runs_var.set("Past Runs")
    
    def _on_past_run_selected(self, choice):
        """
        Handle selection of a past run from dropdown.
        
        Args:
            choice: The selected dropdown value
        """
        if choice == "Past Runs":
            return
        
        # Load the selected tracker file
        filename = f"TrackerData_{choice}.json"
        filepath = Path('gl') / filename
        
        if not filepath.exists():
            messagebox.showerror("Error", f"Tracker file not found:\n{filename}")
            self.past_runs_var.set("Past Runs")
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                past_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tracker file:\n{e}")
            self.past_runs_var.set("Past Runs")
            return
        
        # Enter read-only mode
        self.tracker_read_only = True
        self.tracker_viewing_file = choice
        
        # Temporarily replace tracker data for display
        self._original_tracker_data = self.tracker_data
        self.tracker_data = past_data
        
        # Refresh UI with past data (buttons will be disabled)
        self._populate_tracker_encounters()
        
        # Show Back to Current Run button
        self.back_to_current_btn.pack(pady=(0, 5))
        
        # Disable New Run button
        self.new_run_btn.configure(state="disabled")
    
    def _on_back_to_current_run(self):
        """Exit read-only mode and return to current tracker."""
        if not self.tracker_read_only:
            return
        
        # Restore original tracker data
        self.tracker_data = self._original_tracker_data
        self._original_tracker_data = None
        
        # Exit read-only mode
        self.tracker_read_only = False
        self.tracker_viewing_file = None
        
        # Hide Back to Current Run button
        self.back_to_current_btn.pack_forget()
        
        # Re-enable New Run button
        self.new_run_btn.configure(state="normal")
        
        # Reset dropdown
        self.past_runs_var.set("Past Runs")
        
        # Refresh UI with current data
        self._populate_tracker_encounters()
    
    def _navigate_to_pokemon(self, pokemon):
        """Navigate to a Pokemon in the Pokedex list and select it."""
        if not pokemon:
            return
        
        # Find this Pokemon in the full list
        target_name = pokemon.get('name', '')
        
        # Reset search to show all Pokemon
        self.search_entry.delete(0, tk.END)
        self.filtered_pokemon = self.pokemon_list.copy()
        self._populate_pokemon_list()
        
        # Find the index of the target Pokemon in the list
        for i, poke in enumerate(self.filtered_pokemon):
            if poke.get('name') == target_name:
                # Select this Pokemon in the listbox
                self.pokemon_listbox.selection_clear(0, tk.END)
                self.pokemon_listbox.selection_set(i)
                self.pokemon_listbox.see(i)  # Scroll to make it visible
                self._select_pokemon(poke)
                break
    
    def _populate_pokemon_list(self):
        """Populate the Pokemon listbox with filtered Pokemon names."""
        # Clear existing items
        self.pokemon_listbox.delete(0, tk.END)
        
        # Add filtered Pokemon names (truncate to 14 chars with ellipsis if needed)
        for poke in self.filtered_pokemon:
            name = poke['name']
            if len(name) > 14:
                name = name[:14] + "..."
            self.pokemon_listbox.insert(tk.END, name)
    
    def _on_listbox_select(self, event=None):
        """Handle Pokemon selection from the listbox."""
        selection = self.pokemon_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.filtered_pokemon):
                self._select_pokemon(self.filtered_pokemon[index])
    
    def _on_search_changed(self, event=None):
        """Handle search entry text changes."""
        query = self.search_entry.get().strip()
        
        if not query:
            # Show all Pokemon
            self.filtered_pokemon = self.pokemon_list.copy()
        else:
            # Filter Pokemon by name using fuzzy matching
            self.filtered_pokemon = [
                poke for poke in self.pokemon_list
                if fuzzy_match(query, poke['name'])
            ]
        
        self._populate_pokemon_list()
    
    def _on_search_enter(self, event=None):
        """Handle Enter key in search - select first filtered Pokemon."""
        if self.filtered_pokemon:
            # Select first item in listbox visually
            self.pokemon_listbox.selection_clear(0, tk.END)
            self.pokemon_listbox.selection_set(0)
            self.pokemon_listbox.see(0)  # Scroll to make it visible
            self._select_pokemon(self.filtered_pokemon[0])
    
    def _select_pokemon(self, pokemon):
        """Update the info display for the selected Pokemon."""
        self.selected_pokemon = pokemon
        
        # Update sprite
        sprite_name = pokemon.get('sprite_name', '')
        sprite_path = SPRITES_DIR / sprite_name / 'icon.png'
        
        if sprite_path.exists():
            try:
                # Load the icon sprite (it's a sprite sheet, we'll use just the first frame)
                pil_image = Image.open(sprite_path)
                
                # The icon is typically 32x64 with 2 frames stacked vertically
                # Crop to just the first frame (top half)
                width, height = pil_image.size
                if height > width:
                    # Crop to top frame only
                    pil_image = pil_image.crop((0, 0, width, height // 2))
                
                # Scale up for better visibility (2x)
                new_width = pil_image.width * 2
                new_height = pil_image.height * 2
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.NEAREST)
                
                # Create CTkImage
                self.current_sprite_image = ctk.CTkImage(
                    light_image=pil_image,
                    dark_image=pil_image,
                    size=(new_width, new_height)
                )
                self.sprite_label.configure(image=self.current_sprite_image)
            except Exception as e:
                # If loading fails, clear the sprite
                self.sprite_label.configure(image=None)
                self.current_sprite_image = None
        else:
            # No sprite found, clear the label
            self.sprite_label.configure(image=None)
            self.current_sprite_image = None
        
        # Update type buttons
        # First, destroy any existing type buttons
        if self.type1_button:
            self.type1_button.destroy()
            self.type1_button = None
        if self.type2_button:
            self.type2_button.destroy()
            self.type2_button = None
        
        # Get type data from the Pokemon
        type1 = pokemon.get('type1', 'Normal')
        type2 = pokemon.get('type2')  # None for single-type Pokemon
        
        # Create type 1 button (always present)
        self.type1_button = TypeButton(self.types_frame, type_name=type1, width=80, height=24)
        self.type1_button.pack(pady=(0, 4))
        
        # Create type 2 button (only if Pokemon has a second type)
        if type2:
            self.type2_button = TypeButton(self.types_frame, type_name=type2, width=80, height=24)
            self.type2_button.pack(pady=(0, 0))
        
        # Update name (truncate to 14 chars with ellipsis if needed)
        display_name = pokemon['name']
        if len(display_name) > 14:
            display_name = display_name[:14] + "..."
        self.info_name_label.configure(text=display_name)
        
        # Update abilities
        ability1_id = pokemon.get('ability1', 0)
        ability2_id = pokemon.get('ability2', 0)
        hidden_ability_id = pokemon.get('hidden_ability', 0)
        
        # Get ability info
        ability1_info = self.ability_dict.get(ability1_id, {'name': 'None', 'description': '-'})
        ability2_info = self.ability_dict.get(ability2_id, {'name': 'None', 'description': '-'})
        hidden_info = self.ability_dict.get(hidden_ability_id, {'name': 'None', 'description': '-'})
        
        # Update ability 1 button and tooltip
        if ability1_id != 0:
            self.ability1_btn.configure(text=ability1_info['name'])
            self.ability1_tooltip.set_text(ability1_info['description'])
        else:
            self.ability1_btn.configure(text="---")
            self.ability1_tooltip.set_text("")  # Empty text = no tooltip shown
        
        # Update ability 2 button and tooltip
        if ability2_id != 0:
            self.ability2_btn.configure(text=ability2_info['name'])
            self.ability2_tooltip.set_text(ability2_info['description'])
        else:
            self.ability2_btn.configure(text="---")
            self.ability2_tooltip.set_text("")
        
        # Update hidden ability button and tooltip
        if hidden_ability_id != 0:
            self.hidden_ability_btn.configure(text=hidden_info['name'])
            self.hidden_ability_tooltip.set_text(hidden_info['description'])
        else:
            self.hidden_ability_btn.configure(text="No Hidden Ability")
            self.hidden_ability_tooltip.set_text("")
        
        # Update stats
        stats = pokemon.get('stats', {})
        for key in ['hp', 'atk', 'def', 'sp_atk', 'sp_def', 'speed']:
            value = stats.get(key, 0)
            self.stat_labels[key].configure(text=str(value))
        
        # Update BST
        bst = pokemon.get('bst', 0)
        self.bst_label.configure(text=str(bst))
        
        # Update moves display
        self._update_moves_display(pokemon)
        
        # Update evolutions display
        self._update_evolutions_display(pokemon)
    
    def _get_save_location_display(self):
        """Get display text for save location."""
        loc = self.config.get("save_location", "")
        if loc:
            return f"Save: {loc}"
        return "select your goldilockes.sav file. This will only appear once you've saved in-game"
    
    def _update_backup_button_state(self):
        """Gray out the backup button until a save location has been chosen."""
        if self.config.get("save_location", ""):
            self.backup_btn.configure(state="normal")
        else:
            self.backup_btn.configure(state="disabled")
    
    def _toggle_options(self):
        """Toggle the options panel visibility."""
        self.options_expanded = not self.options_expanded
        
        if self.options_expanded:
            self.options_header.configure(text="▼ Options for Nerds")
            self.options_content.pack(fill="x", pady=(0, 10))
        else:
            self.options_header.configure(text="▶ Options for Nerds")
            self.options_content.pack_forget()
    
    def _on_seed_checkbox_toggle(self):
        """Handle seed checkbox toggle."""
        if self.use_seed_var.get():
            self.seed_entry.configure(state="normal")
        else:
            self.seed_entry.configure(state="disabled")
    
    def _on_choose_save(self):
        """Handle Choose Save Location button."""
        filepath = filedialog.askopenfilename(
            title="Select your save file (goldilockes.sav)",
            filetypes=[("Save files", "*.sav"), ("All files", "*.*")],
            initialfile="goldilockes.sav"
        )
        if filepath:
            self.config["save_location"] = filepath
            save_config(self.config)
            self.save_location_label.configure(text=self._get_save_location_display())
            self._update_backup_button_state()
            self._set_status("Save location set!", "green")
    
    def _on_backup_save(self):
        """Handle Make Backup Save button."""
        save_path = self.config.get("save_location", "")
        
        if not save_path:
            messagebox.showerror("Error", "Please set a save location first using 'Choose Save Location'.")
            return
        
        save_path = Path(save_path)
        if not save_path.exists():
            messagebox.showerror("Error", f"Save file not found:\n{save_path}")
            return
        
        # Create backup with ISO8601 timestamp
        # Format: goldilockes-2026-06-19T15-05-30.sav
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        backup_name = f"{save_path.stem}-{timestamp}{save_path.suffix}"
        backup_path = save_path.parent / backup_name
        
        try:
            shutil.copy2(save_path, backup_path)
            self._set_status(f"Backup created: {backup_name}", "green")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create backup:\n{e}")
    
    def _on_open_folder(self):
        """Open the gl/ folder in the file explorer."""
        # os.startfile is Windows-specific; this opens the folder in Explorer
        gl_folder = Path('gl').resolve()
        if sys.platform == 'win32':
            os.startfile(gl_folder)
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', str(gl_folder)])
        else:  # Linux
            subprocess.run(['xdg-open', str(gl_folder)])
    
    def _set_ui_enabled(self, enabled):
        """
        Enable or disable all interactive widgets.
        
        Args:
            enabled: True to enable widgets, False to disable them.
        """
        state = "normal" if enabled else "disabled"
        for widget in self._interactive_widgets:
            try:
                widget.configure(state=state)
            except Exception:
                pass  # Some widgets may not support state changes
        
        # Special handling for seed entry - only enable if checkbox is checked
        if enabled and not self.use_seed_var.get():
            self.seed_entry.configure(state="disabled")
        
        # Special handling for backup button - only enable if a save location is set
        if enabled:
            self._update_backup_button_state()
    
    def _on_randomize(self):
        """Handle the main Randomize button click."""
        # Validate seed if specified
        seed = None
        if self.use_seed_var.get():
            seed_text = self.seed_entry.get().strip()
            if seed_text:
                try:
                    seed = int(seed_text)
                except ValueError:
                    messagebox.showerror("Error", "Seed must be a valid number.")
                    return
        
        # Disable all UI and show red badge (in progress)
        self._set_ui_enabled(False)
        self.subtitle.pack_forget()  # Hide "Click the badge" text
        if self.badge_image_red:
            self.randomize_btn.configure(image=self.badge_image_red)
        self._set_status("Randomizing... This may take a few seconds...", "orange")
        self.update()  # Force UI update
        
        # Start the randomizer in a separate process
        self._result_queue = Queue()
        self._randomizer_process = Process(
            target=_randomizer_worker,
            args=(seed, os.getcwd(), self._result_queue)
        )
        self._randomizer_process.start()
        
        # Start polling for completion (check every 100ms)
        self.after(100, self._check_randomizer_status)
    
    def _check_randomizer_status(self):
        """
        Poll the randomizer subprocess for completion.
        
        This method is called repeatedly via after() until the
        subprocess finishes. Uses a Queue to get results without
        blocking the UI.
        """
        try:
            # Try to get result without blocking
            result = self._result_queue.get_nowait()
            
            # Process finished - handle result
            self._handle_randomizer_result(result)
            
        except Exception:
            # Queue empty, process still running - poll again
            if self._randomizer_process and self._randomizer_process.is_alive():
                self.after(100, self._check_randomizer_status)
            else:
                # Process died without putting result in queue
                self._handle_randomizer_error("Process terminated unexpectedly")
    
    def _handle_randomizer_result(self, result):
        """
        Handle the result from the randomizer subprocess.
        
        Args:
            result: Dictionary with 'status', and either 'seed'/'log' 
                    for success or 'message'/'traceback' for error.
        """
        try:
            if result['status'] == 'success':
                used_seed = result['seed']
                log_output = result['log']
                
                # Create Spoiler folder if needed
                SPOILER_DIR.mkdir(exist_ok=True)
                
                # Save log file
                log_path = SPOILER_DIR / f"{used_seed}.txt"
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(log_output)
                
                # Show green badge (success!)
                if self.badge_image_green:
                    self.randomize_btn.configure(image=self.badge_image_green)
                    self.update()
                
                self._set_status("Done! Run goldilockes.nds on MelonDS", "green")
            else:
                # Error occurred
                error_msg = result.get('message', 'Unknown error')
                tb = result.get('traceback', '')
                self._handle_randomizer_error(f"{error_msg}\n\n{tb}", do_cleanup=False)
                
        finally:
            self._cleanup_randomizer_ui()
    
    def _handle_randomizer_error(self, error_msg, do_cleanup=True):
        """
        Handle an error from the randomizer subprocess.
        
        Args:
            error_msg: The error message to display.
            do_cleanup: Whether to clean up UI (False when called from _handle_randomizer_result).
        """
        self._set_status("Error during randomization!", "red")
        messagebox.showerror("Error", f"Randomization failed:\n{error_msg}")
        if do_cleanup:
            self._cleanup_randomizer_ui()
    
    def _cleanup_randomizer_ui(self):
        """
        Clean up UI state after randomization completes (success or failure).
        
        Restores the badge image and re-enables all interactive widgets.
        """
        # Restore original badge and subtitle
        if self.badge_image:
            self.randomize_btn.configure(image=self.badge_image)
        self.subtitle.pack(after=self.randomize_btn, pady=(0, 20))  # Show "Click the badge" text again
        
        # Re-enable all UI
        self._set_ui_enabled(True)
        
        # Clean up process references
        if self._randomizer_process:
            self._randomizer_process.join(timeout=1)  # Wait briefly for cleanup
            self._randomizer_process = None
        self._result_queue = None
    
    def _set_status(self, text, color="gray"):
        """Update the status label."""
        self.status_label.configure(text=text, text_color=color)
    
    def _create_information_tab(self):
        """
        Create the Information tab with subtabs for various reference info.
        
        The first subtab is "Tiers of Play" which shows game progression tables.
        """
        tab = self.tabview.tab("Information")
        
        # Main tabview for subtabs
        self.info_subtabview = ctk.CTkTabview(tab)
        self.info_subtabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create subtabs
        self.info_subtabview.add("Changes from Vanilla")
        self.info_subtabview.add("Nuzlocke Rules")
        self.info_subtabview.add("Difficulty Scaling")
        
        # Build each subtab
        self._create_changes_from_vanilla_tab()
        self._create_nuzlocke_rules_tab()
        self._create_tiers_of_play_tab()
    
    def _create_changes_from_vanilla_tab(self):
        """
        Create the Changes from Vanilla subtab with collapsible sections.
        
        Each section is a dropdown that expands to show bullet points
        describing changes from the vanilla game.
        """
        tab = self.info_subtabview.tab("Changes from Vanilla")
        
        # Store section state (expanded/collapsed) and widgets
        self.vanilla_sections = {}
        
        # Scrollable frame for the content
        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Load the JSON data
        try:
            with open(CHANGES_FROM_VANILLA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            error_label = ctk.CTkLabel(
                scroll_frame,
                text=f"Error loading changes data: {e}",
                text_color="red"
            )
            error_label.pack(pady=20)
            return
        
        # Create each collapsible section
        for section in data.get("sections", []):
            title = section.get("title", "Untitled")
            items = section.get("items", [])
            
            self._create_collapsible_section(scroll_frame, title, items, self.vanilla_sections)
    
    def _create_nuzlocke_rules_tab(self):
        """
        Create the Nuzlocke Rules subtab with collapsible sections.
        
        Each section is a dropdown that expands to show bullet points
        explaining nuzlocke rules and clauses.
        """
        tab = self.info_subtabview.tab("Nuzlocke Rules")
        
        # Store section state (expanded/collapsed) and widgets
        self.nuzlocke_sections = {}
        
        # Scrollable frame for the content
        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Load the JSON data
        try:
            with open(NUZLOCKE_RULES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            error_label = ctk.CTkLabel(
                scroll_frame,
                text=f"Error loading nuzlocke rules: {e}",
                text_color="red"
            )
            error_label.pack(pady=20)
            return
        
        # Create each collapsible section
        for section in data.get("sections", []):
            title = section.get("title", "Untitled")
            items = section.get("items", [])
            
            self._create_collapsible_section(scroll_frame, title, items, self.nuzlocke_sections)
    
    def _create_collapsible_section(self, parent, title, items, sections_dict):
        """
        Create a single collapsible section with a header and bullet points.
        
        Args:
            parent: The parent frame to add the section to
            title: The section title (shown in the header button)
            items: List of strings (or nested lists) to display as bullet points
            sections_dict: Dictionary to store section state for toggling
        """
        # Container frame for this section
        section_frame = ctk.CTkFrame(parent, fg_color="transparent")
        section_frame.pack(fill="x", pady=5)
        
        # Track expanded state
        sections_dict[title] = {"expanded": False}
        
        # Header button for expanding/collapsing
        header_btn = ctk.CTkButton(
            section_frame,
            text=f"▶ {title}",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#d0d0d0", "#404040"),
            text_color=("gray10", "gray90"),
            hover_color=("#b0b0b0", "#505050"),
            anchor="w",
            height=35,
            command=lambda t=title, d=sections_dict: self._toggle_info_section(t, d)
        )
        header_btn.pack(fill="x", padx=5)
        
        # Content frame (initially hidden) - holds the bullet points
        content_frame = ctk.CTkFrame(section_frame, fg_color=("#e8e8e8", "#2a2a2a"))
        
        # Add each bullet point as a label
        for item in items:
            # Handle nested lists (sub-bullets)
            if isinstance(item, list):
                for sub_item in item:
                    if sub_item.strip():
                        sub_bullet_label = ctk.CTkLabel(
                            content_frame,
                            text=f"      ◦  {sub_item}",
                            font=ctk.CTkFont(size=11),
                            anchor="w",
                            justify="left",
                            wraplength=620
                        )
                        sub_bullet_label.pack(fill="x", padx=25, pady=2, anchor="w")
            elif isinstance(item, str) and item.strip():  # Skip empty items
                bullet_label = ctk.CTkLabel(
                    content_frame,
                    text=f"  •  {item}",
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                    justify="left",
                    wraplength=650
                )
                bullet_label.pack(fill="x", padx=15, pady=3, anchor="w")
        
        # Store references for toggling
        sections_dict[title]["header"] = header_btn
        sections_dict[title]["content"] = content_frame
    
    def _toggle_info_section(self, title, sections_dict):
        """
        Toggle a collapsible section's visibility.
        
        Args:
            title: The section title to toggle
            sections_dict: The dictionary containing section state
        """
        section = sections_dict.get(title)
        if not section:
            return
        
        section["expanded"] = not section["expanded"]
        
        if section["expanded"]:
            section["header"].configure(text=f"▼ {title}")
            section["content"].pack(fill="x", padx=5, pady=(0, 5))
        else:
            section["header"].configure(text=f"▶ {title}")
            section["content"].pack_forget()
    
    def _load_tiers_csv(self, filepath):
        """
        Load a tiers CSV file and return the data as a list of rows.
        
        Each row is a list of cell values. The first row contains headers.
        
        Args:
            filepath: Path to the CSV file
            
        Returns:
            list: List of rows, where each row is a list of cell values
        """
        rows = []
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    # Split by comma, preserving empty cells
                    cells = line.rstrip('\n').split(',')
                    rows.append(cells)
        return rows
    
    def _create_tiers_of_play_tab(self):
        """
        Create the Tiers of Play subtab with game progression tables.
        
        Shows a note about game phases at the top, followed by 3 tables
        from the Tiers CSV files. Cells with asterisks have tooltips.
        """
        tab = self.info_subtabview.tab("Difficulty Scaling")
        
        # Store tooltips to keep them alive
        self.tier_tooltips = []
        
        # Scrollable frame for the content
        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Note at top center about game phases
        note_label = ctk.CTkLabel(
            scroll_frame,
            text="Mid Game begins at Whitney. Late Game begins at Jasmine. End Game begins at Will. Post Game begins at Surge.",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
            wraplength=700,
            justify="center"
        )
        note_label.pack(pady=(10, 20))
        
        # Load the three CSV files
        tiers1_data = self._load_tiers_csv(TIERS1_FILE)
        tiers2_data = self._load_tiers_csv(TIERS2_FILE)
        tiers3_data = self._load_tiers_csv(TIERS3_FILE)
        
        # Create the three tables
        if tiers1_data:
            self._create_tier_table(scroll_frame, tiers1_data, "Trainers")
        
        if tiers2_data:
            self._create_tier_table(scroll_frame, tiers2_data, "Item Rolls")
        
        if tiers3_data:
            self._create_tier_table(scroll_frame, tiers3_data, "Type Themes")
    
    def _create_tier_table(self, parent, data, title):
        """
        Create a table from tier data.
        
        Args:
            parent: Parent frame to add the table to
            data: List of rows from the CSV file
            title: Title for the table section
        """
        if not data:
            return
        
        # Section title
        title_label = ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.pack(pady=(15, 5))
        
        # Table frame
        table_frame = ctk.CTkFrame(parent, fg_color="gray20")
        table_frame.pack(fill="x", padx=10, pady=5)
        
        # Get number of columns from header row
        num_cols = len(data[0]) if data else 0
        
        # Configure columns - first column wider for row labels
        for col in range(num_cols):
            weight = 2 if col == 0 else 1
            table_frame.grid_columnconfigure(col, weight=weight, uniform="col")
        
        # Get header row for column names (used for tooltip lookup)
        header_row = [c.strip() for c in data[0]] if data else []
        
        # Create cells for each row
        display_row = 0  # Track actual grid row (skipping empty rows)
        for row_idx, row in enumerate(data):
            # Skip empty rows (just commas)
            if row_idx > 0 and all(c.strip() == '' for c in row):
                continue
            
            # Get the row label (first column) for tooltip lookup
            row_label = row[0].strip() if row else ""
            
            for col_idx, cell_value in enumerate(row):
                # Determine styling
                is_header = (display_row == 0)
                is_row_label = (col_idx == 0)
                
                # Check if cell has an asterisk (needs tooltip)
                has_asterisk = '*' in cell_value
                
                # Cell text (keep asterisk visible)
                cell_text = cell_value.strip()
                
                # Style the cell
                if is_header:
                    font = ctk.CTkFont(size=11, weight="bold")
                    fg_color = "gray30"
                elif is_row_label:
                    font = ctk.CTkFont(size=10, weight="bold")
                    fg_color = "gray25"
                else:
                    font = ctk.CTkFont(size=10)
                    fg_color = "transparent"
                
                # Create cell as a label (or button if it has tooltip)
                if has_asterisk:
                    # Create as button for tooltip functionality
                    cell = ctk.CTkButton(
                        table_frame,
                        text=cell_text,
                        font=font,
                        fg_color=fg_color,
                        hover_color="gray40",
                        height=28,
                        corner_radius=0,
                        command=lambda: None  # No action on click
                    )
                    cell.grid(row=display_row, column=col_idx, padx=1, pady=1, sticky="nsew")
                    
                    # Look up unique tooltip text using (table, row_label, column_header)
                    column_header = header_row[col_idx] if col_idx < len(header_row) else ""
                    # For row labels (col 0), use the cell text itself as the lookup key
                    lookup_row = cell_text if is_row_label else row_label
                    tooltip_key = (title, lookup_row, column_header)
                    tooltip_text = TIER_CELL_TOOLTIPS.get(tooltip_key, cell_text)
                    
                    tooltip = ToolTip(cell)
                    tooltip.set_text(tooltip_text)
                    self.tier_tooltips.append(tooltip)
                else:
                    # Create as label (no tooltip needed)
                    cell = ctk.CTkLabel(
                        table_frame,
                        text=cell_text,
                        font=font,
                        fg_color=fg_color,
                        height=28,
                        corner_radius=0
                    )
                    cell.grid(row=display_row, column=col_idx, padx=1, pady=1, sticky="nsew")
            
            # Increment display row after processing all columns in this row
            display_row += 1


def main():
    app = RandomizerApp()
    app.mainloop()


if __name__ == "__main__":
    # Required for PyInstaller to work with multiprocessing
    # Must be called before any other code runs
    multiprocessing.freeze_support()
    main()
