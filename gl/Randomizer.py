import sys
import os
import random
import ndspy.rom
from steps import *
from trainer_data_editor import *
from print_eviolite_users_step import PrintEvioliteUsersStep

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())



def parse_verbosity_overrides(verbosity_args):
    """Parse -v arguments into list of (path_list, level) tuples."""
    overrides = []
    for arg in verbosity_args:
        if '=' in arg:
            path_str, level = arg.split('=', 1)
            path_list = [p.lower() for p in path_str.split('/') if p]
            overrides.append((path_list, int(level)))
        else:
            # Global verbosity - empty path prefix
            overrides.append(([], int(arg)))
    return overrides


        
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test RandomizeGymsStep")
    parser.add_argument("--bst-factor", type=float, default=0.15, help="BST factor for filtering (default: 0.15)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Don't output details")
    parser.add_argument("--seed", "-s", type=str, help="Random seed")
    parser.add_argument("--verbosity", "-v", action="append", type=str, 
                       help="Verbosity: level (global) or path=level (path-specific)")
    
    # Options to control filtering of special Pokémon categories
    parser.add_argument("--allow-restricted", action="store_true", help="Allow restricted legendary Pokémon")
    parser.add_argument("--allow-mythical", action="store_true", help="Allow mythical Pokémon")
    parser.add_argument("--allow-ultra-beasts", action="store_true", help="Allow Ultra Beast Pokémon")
    parser.add_argument("--allow-paradox", action="store_true", help="Allow Paradox Pokémon")
    parser.add_argument("--allow-sublegendary", action="store_true", help="Allow SubLegendary Pokémon")
    parser.add_argument("--independent-encounters", action="store_true", help="Make encounter replacements independent by area")
    parser.add_argument("--expand-bosses-only", action="store_true", help="Only expand teams for boss trainers (gym leaders, Elite Four, etc.)")
    parser.add_argument("--wild-level-mult", type=float, default=1.0, help="Multiplier for wild Pokémon levels (default: 1.0)")
    parser.add_argument("--trainer-level-mult", type=float, default=1.0, help="Multiplier for trainer Pokémon levels with special boss/ace logic (default: 1.0)")
    parser.add_argument("--randomize-starters", action="store_true", help="Randomize starter Pokémon")
    parser.add_argument("--consistent-rival-starters", action="store_true", help="Update rival teams to use starters consistent with the player's randomized choice")
    parser.add_argument("--no-randomize-ordinary-trainers", action="store_false", 
                       dest="randomize_ordinary_trainers", default=True,
                       help="Disable randomization of ordinary trainers (default: enabled)")
    parser.add_argument("--no-enemy-battle-items", action="store_true", help="Remove all battle items from enemy trainers")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(int(args.seed))
    
    # Parse verbosity overrides
    vbase = 0 if args.quiet else 2
    verbosity_overrides = [([], vbase)] + parse_verbosity_overrides(args.verbosity or [])
    
    # Load ROM
    with open("recompiletest.nds", "rb") as f:
        rom = ndspy.rom.NintendoDSRom(f.read())
    
    # Create context and load data
    ctx = RandomizationContext(rom, verbosity_overrides=verbosity_overrides)

    # Create filters from options
    legendary_filters = [
        NotInSet(ctx.get(LoadBlacklistStep).by_id),
        NotInSet(ctx.get(InvalidPokemon).by_id),
        *([] if args.allow_restricted else [NotInSet(ctx.get(RestrictedPokemon).by_id)]),
        *([] if args.allow_mythical else [NotInSet(ctx.get(MythicalPokemon).by_id)]),
        *([] if args.allow_ultra_beasts else [NotInSet(ctx.get(UltraBeastPokemon).by_id)]),
        *([] if args.allow_paradox else [NotInSet(ctx.get(ParadoxPokemon).by_id)]),
        *([] if args.allow_sublegendary else [NotInSet(ctx.get(SubLegendaryPokemon).by_id)])
    ]
    
    gym_filter = AllFilters(legendary_filters + [BstWithinFactor(args.bst_factor)])
    encounter_filter = AllFilters(legendary_filters + [BstWithinFactor(args.bst_factor)])
    starter_filter = AllFilters(legendary_filters)
    trainer_filter = AllFilters(legendary_filters + [BstWithinFactor(args.bst_factor)])

    type_mimics = ctx.get(TypeMimics)
    # Do everything
    ctx.run_pipeline([
        TrainerMult(multiplier=args.trainer_level_mult),
        ExpandTrainerTeamsStep(bosses_only=args.expand_bosses_only),
        WildMult(multiplier=args.wild_level_mult),
        RandomizeGymTypesStep(),
        RandomizeGymsStep(gym_filter),
        RandomizeEncountersStep(encounter_filter, args.independent_encounters),
        *([] if not args.randomize_starters else [RandomizeStartersStep(starter_filter)]),
        *([] if not args.consistent_rival_starters else [ConsistentRivalStarter()]),
        *([] if not args.randomize_ordinary_trainers else [RandomizeOrdinaryTrainersStep(trainer_filter)]),
        ChangeTrainerDataTypeStep(target_flags = TrainerDataType.MOVES | TrainerDataType.ITEMS | TrainerDataType.IV_EV_SET),
        *([] if not args.no_enemy_battle_items else [NoEnemyBattleItems()]),
        GeneralEVStep(),
        GeneralIVStep(mode="ScalingIVs"),
        SetTrainerMovesStep(),
        RandomizeAbilitiesStep(mode="randomability_with_hidden"),
        TrainerHeldItem(),
        PrintEvioliteUsersStep()
        
    ])
    
    ctx.write_all()
    
    # Save modified ROM
    modified_rom_path = "hgeLanceCanary_gym_randomized.nds"
    with open(modified_rom_path, "wb") as f:
        s = rom.save()
        print(f"Writing {len(s)} bytes to {repr(modified_rom_path)} ...")
        f.write(s)

    print("Done")
