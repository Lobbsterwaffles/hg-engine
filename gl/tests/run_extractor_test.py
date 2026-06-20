# -*- coding: utf-8 -*-
"""
Minimal harness to instantiate a single extractor against a ROM.
  python gl/tests/run_extractor_test.py <rom_name> [ExtractorClass]

"""
import json
import os
import sys

GL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(GL_DIR)

sys.path.insert(0, GL_DIR)
os.chdir(REPO_ROOT)

import ndspy.rom

from framework import RandomizationContext
import steps
import extractors

def to_serializable(obj):
    """Convert construct Container/ListContainer to plain dict/list."""
    if hasattr(obj, 'items'):
        return {k: to_serializable(v) for k, v in obj.items() if not k.startswith('_')}
    if isinstance(obj, list):
        return [to_serializable(item) for item in obj]
    return obj


def main():
    # Parse --dump flag
    args = sys.argv[1:]
    dump_file = None
    if '--dump' in args:
        idx = args.index('--dump')
        if idx + 1 < len(args):
            dump_file = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        else:
            print("Error: --dump requires a filename")
            return 1

    if len(args) < 1:
        print(f"Usage: python {sys.argv[0]} <rom_name> [ExtractorClass] [species_id] [--dump file.json]")
        return 1

    rom_name = args[0]
    extractor_name = args[1] if len(args) > 1 else "RestrictedPokemon"

    extractor_class = getattr(steps, extractor_name, None)
    if extractor_class is None:
        extractor_class = getattr(extractors, extractor_name, None)
    if extractor_class is None:
        print(f"Error: no extractor named {extractor_name!r} in steps.py or extractors.py")
        return 1

    with open(rom_name, "rb") as f:
        rom = ndspy.rom.NintendoDSRom(f.read())

    ctx = RandomizationContext(rom)
    extractor = ctx.get(extractor_class)

    # Check for optional species_id argument (3rd positional)
    species_id = int(args[2]) if len(args) > 2 else None

    # Dump mode: write all data to file
    if dump_file and hasattr(extractor, 'data'):
        output = {i: to_serializable(entry) for i, entry in enumerate(extractor.data)}
        with open(dump_file, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Dumped {len(extractor.data)} entries to {dump_file}")
        return 0

    if species_id is not None and hasattr(extractor, 'data'):
        print(f"\nQuerying {extractor_name} for species ID {species_id}:")
        if species_id < len(extractor.data):
            print(f"  Data: {extractor.data[species_id]}")
        else:
            print(f"  Error: species_id {species_id} out of range (max {len(extractor.data)-1})")
    elif hasattr(extractor, 'by_id'):
        print(f"\nBuilt {extractor_name}: {len(extractor.by_id)} entries resolved")
    else:
        print(f"\nBuilt {extractor_name}: {len(extractor.data)} entries")
    return 0

if __name__ == "__main__":
    sys.exit(main())
