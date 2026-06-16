# -*- coding: utf-8 -*-
"""
Minimal harness to instantiate a single extractor against a ROM.
  python gl/tests/run_extractor_test.py <rom_name> [ExtractorClass]

"""
import os
import sys

GL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(GL_DIR)

sys.path.insert(0, GL_DIR)
os.chdir(REPO_ROOT)

import ndspy.rom

from framework import RandomizationContext
import steps

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <rom_name> [ExtractorClass]")
        return 1

    rom_name = sys.argv[1]
    extractor_name = sys.argv[2] if len(sys.argv) > 2 else "RestrictedPokemon"

    extractor_class = getattr(steps, extractor_name, None)
    if extractor_class is None:
        print(f"Error: no extractor named {extractor_name!r} in steps.py")
        return 1

    with open(rom_name, "rb") as f:
        rom = ndspy.rom.NintendoDSRom(f.read())

    ctx = RandomizationContext(rom)
    extractor = ctx.get(extractor_class)

    print(f"\nBuilt {extractor_name}: {len(extractor.by_id)} entries resolved")
    return 0

if __name__ == "__main__":
    sys.exit(main())
