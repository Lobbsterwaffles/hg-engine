from construct import *
import random
import re

import ndspy.rom
import ndspy.narc

# Import shared Pokemon data and utilities
from pokemon_shared import (
    SPECIAL_POKEMON,
    mondata_struct,
    parse_mondata,
    build_mondata,
    read_mondata,
    read_pokemon_names,
    find_replacements
)


EncounterSlot = Struct(
    "species" / Int16ul,
    "minlevel" / Int8ul,
    "maxlevel" / Int8ul,
)

encounter_struct = Struct(
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
)


def read_encounter_names(base_path):
    """Parse encounter names from assembly source file using regex pattern matching."""
    encounter_names = {}
    try:
        with open("armips/data/encounters.s", "r", encoding="utf-8") as f:
            for line in f:
                # Look for pattern: encounterdata <number> ... // <name>
                match = re.search(r"encounterdata\s+(\d+).*//\s+(.*)", line)
                if match:
                    idx = int(match.group(1))
                    name = match.group(2).strip()
                    encounter_names[idx] = name

        # Return as sorted dict (equivalent to Clojure's sorted-map)
        return dict(sorted(encounter_names.items()))
    except FileNotFoundError:
        # If file doesn't exist, return empty dict
        return {}


def randomize_slot_list(
    slot_list, time_name, location_id, location_name, mondata, log_function=None
):
    """Helper function to randomize a list of Pokemon slots and print progress"""
    for i, pokemon_id in enumerate(slot_list):
        mon = mondata[pokemon_id]

        # Skip replacing special Pokemon
        if pokemon_id in SPECIAL_POKEMON:
            replacements = [pokemon_id]
            notes = "SKIP"
        else:
            fac = 0.15
            replacements = find_replacements(mon, mondata, 1 - fac, 1 + fac)
            # Filter out special Pokemon from replacement candidates
            replacements = [r for r in replacements if r not in SPECIAL_POKEMON]
            if not replacements:  # Fallback if no suitable replacements found
                replacements = [pokemon_id]
            notes = ""

        rid = random.choice(replacements)
        rep = mondata[rid]

        if mon.bst == 0:
            percent_diff = float("inf")
        else:
            percent_diff = ((rep.bst - mon.bst) / mon.bst) * 100

        # Always use consistent tabular format
        # Truncate location name if too long
        if len(location_name) > 20:
            display_location = location_name[:17] + "..."
        else:
            display_location = location_name

        log_message = f"{location_id:<4} {display_location:<40} {time_name:<7} {i:<4} {mon.name:<15} {mon.bst:<4} {'→':<2} {rep.name:<15} {rep.bst:<4} {percent_diff:+5.1f}% {notes:<4}"
        if log_function:
            log_function(log_message)

        slot_list[i] = rid


def randomize_bytes(
    input_bytes, mondata, location_id, encounter_names, log_function=None
):
    my = encounter_struct.parse(input_bytes)

    # Get encounter name if available, otherwise use location ID
    location_name = encounter_names.get(location_id, f"Area {location_id}")

    randomize_slot_list(
        my.morning, "morning", location_id, location_name, mondata, log_function
    )
    randomize_slot_list(
        my.day, "day", location_id, location_name, mondata, log_function
    )
    randomize_slot_list(
        my.night, "night", location_id, location_name, mondata, log_function
    )
    return encounter_struct.build(my)


def randomize_encounters(rom, log_function=None, progress_callback=None):
    names = read_pokemon_names(".")
    mondata = read_mondata(rom, names)

    # Read encounter names from assembly source
    encounter_names = read_encounter_names(".")

    header_message = f"{'Loc':<4} {'Location':<40} {'Time':<7} {'Slot':<4} {'Original':<15} {'BST':<4} {'→':<2} {'Replacement':<15} {'BST':<4} {'Diff%':<6} {'Notes':<4}"
    separator_message = "-" * 120

    if log_function:
        log_function(header_message)
        log_function(separator_message)

    narc_file_id = rom.filenames.idOf("a/0/3/7")
    encounter_narc = rom.files[narc_file_id]
    narc_data = ndspy.narc.NARC(encounter_narc)

    total_files = len(narc_data.files)
    for i, data in enumerate(narc_data.files):
        narc_data.files[i] = randomize_bytes(
            bytearray(data), mondata, i, encounter_names, log_function
        )

        # Update progress bar
        if progress_callback:
            progress_percent = int((i + 1) * 100 / total_files)
            progress_callback(progress_percent)

    rom.files[narc_file_id] = narc_data.save()
