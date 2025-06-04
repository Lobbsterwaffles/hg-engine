#!/usr/bin/env python3
"""
Batch Scraper for Pokémon Egg Moves

This script runs the egg_move_scraper.py for a batch of Pokémon and saves all
their egg moves to a single JSON file that can be used by the hg-engine project.
"""
import subprocess
import time
import os
import argparse
import json

# This is our complete list of Pokémon to scrape.
# The names are all lowercase because that's how PokemonDB uses them in URLs.
# We've organized them by generation to make it easier to read.
pokemon_list = [
    # Gen 1 - Kanto
    "bulbasaur", "ivysaur", "venusaur", "charmander", "charmeleon", "charizard",
    "squirtle", "wartortle", "blastoise", "caterpie", "metapod", "butterfree",
    "weedle", "kakuna", "beedrill", "pidgey", "pidgeotto", "pidgeot",
    "rattata", "raticate", "spearow", "fearow", "ekans", "arbok",
    "pikachu", "raichu", "sandshrew", "sandslash", "nidoran-f", "nidorina",
    "nidoqueen", "nidoran-m", "nidorino", "nidoking", "clefairy", "clefable",
    "vulpix", "ninetales", "jigglypuff", "wigglytuff", "zubat", "golbat",
    "oddish", "gloom", "vileplume", "paras", "parasect", "venonat",
    "venomoth", "diglett", "dugtrio", "meowth", "persian", "psyduck",
    "golduck", "mankey", "primeape", "growlithe", "arcanine", "poliwag",
    "poliwhirl", "poliwrath", "abra", "kadabra", "alakazam", "machop",
    "machoke", "machamp", "bellsprout", "weepinbell", "victreebel", "tentacool",
    "tentacruel", "geodude", "graveler", "golem", "ponyta", "rapidash",
    "slowpoke", "slowbro", "magnemite", "magneton", "farfetchd", "doduo",
    "dodrio", "seel", "dewgong", "grimer", "muk", "shellder",
    "cloyster", "gastly", "haunter", "gengar", "onix", "drowzee",
    "hypno", "krabby", "kingler", "voltorb", "electrode", "exeggcute",
    "exeggutor", "cubone", "marowak", "hitmonlee", "hitmonchan", "lickitung",
    "koffing", "weezing", "rhyhorn", "rhydon", "chansey", "tangela",
    "kangaskhan", "horsea", "seadra", "goldeen", "seaking", "staryu",
    "starmie", "mr-mime", "scyther", "jynx", "electabuzz", "magmar",
    "pinsir", "tauros", "magikarp", "gyarados", "lapras", "ditto",
    "eevee", "vaporeon", "jolteon", "flareon", "porygon", "omanyte",
    "omastar", "kabuto", "kabutops", "aerodactyl", "snorlax", "articuno",
    "zapdos", "moltres", "dratini", "dragonair", "dragonite", "mewtwo", "mew",

    # Gen 2 - Johto
    "chikorita", "bayleef", "meganium", "cyndaquil", "quilava", "typhlosion",
    "totodile", "croconaw", "feraligatr", "sentret", "furret", "hoothoot",
    "noctowl", "ledyba", "ledian", "spinarak", "ariados", "crobat",
    "chinchou", "lanturn", "pichu", "cleffa", "igglybuff", "togepi",
    "togetic", "natu", "xatu", "mareep", "flaaffy", "ampharos",
    "bellossom", "marill", "azumarill", "sudowoodo", "politoed", "hoppip",
    "skiploom", "jumpluff", "aipom", "sunkern", "sunflora", "yanma",
    "wooper", "quagsire", "espeon", "umbreon", "murkrow", "slowking",
    "misdreavus", "unown", "wobbuffet", "girafarig", "pineco", "forretress",
    "dunsparce", "gligar", "steelix", "snubbull", "granbull", "qwilfish",
    "scizor", "shuckle", "heracross", "sneasel", "teddiursa", "ursaring",
    "slugma", "magcargo", "swinub", "piloswine", "corsola", "remoraid",
    "octillery", "delibird", "mantine", "skarmory", "houndour", "houndoom",
    "kingdra", "phanpy", "donphan", "porygon2", "stantler", "smeargle",
    "tyrogue", "hitmontop", "smoochum", "elekid", "magby", "miltank",
    "blissey", "raikou", "entei", "suicune", "larvitar", "pupitar",
    "tyranitar", "lugia", "ho-oh", "celebi",

    # Gen 3 - Hoenn
    "treecko", "grovyle", "sceptile", "torchic", "combusken", "blaziken",
    "mudkip", "marshtomp", "swampert", "poochyena", "mightyena", "zigzagoon",
    "linoone", "wurmple", "silcoon", "beautifly", "cascoon", "dustox",
    "lotad", "lombre", "ludicolo", "seedot", "nuzleaf", "shiftry",
    "taillow", "swellow", "wingull", "pelipper", "ralts", "kirlia",
    "gardevoir", "surskit", "masquerain", "shroomish", "breloom", "slakoth",
    "vigoroth", "slaking", "nincada", "ninjask", "shedinja", "whismur",
    "loudred", "exploud", "makuhita", "hariyama", "azurill", "nosepass",
    "skitty", "delcatty", "sableye", "mawile", "aron", "lairon",
    "aggron", "meditite", "medicham", "electrike", "manectric", "plusle",
    "minun", "volbeat", "illumise", "roselia", "gulpin", "swalot",
    "carvanha", "sharpedo", "wailmer", "wailord", "numel", "camerupt",
    "torkoal", "spoink", "grumpig", "spinda", "trapinch", "vibrava",
    "flygon", "cacnea", "cacturne", "swablu", "altaria", "zangoose",
    "seviper", "lunatone", "solrock", "barboach", "whiscash", "corphish",
    "crawdaunt", "baltoy", "claydol", "lileep", "cradily", "anorith",
    "armaldo", "feebas", "milotic", "castform", "kecleon", "shuppet",
    "banette", "duskull", "dusclops", "tropius", "chimecho", "absol",
    "wynaut", "snorunt", "glalie", "spheal", "sealeo", "walrein",
    "clamperl", "huntail", "gorebyss", "relicanth", "luvdisc", "bagon",
    "shelgon", "salamence", "beldum", "metang", "metagross", "regirock",
    "regice", "registeel", "latias", "latios", "kyogre", "groudon",
    "rayquaza", "jirachi", "deoxys",

    # Gen 4 - Sinnoh
    "turtwig", "grotle", "torterra", "chimchar", "monferno", "infernape",
    "piplup", "prinplup", "empoleon", "starly", "staravia", "staraptor",
    "bidoof", "bibarel", "kricketot", "kricketune", "shinx", "luxio",
    "luxray", "budew", "roserade", "cranidos", "rampardos", "shieldon",
    "bastiodon", "burmy", "wormadam", "mothim", "combee", "vespiquen",
    "pachirisu", "buizel", "floatzel", "cherubi", "cherrim", "shellos",
    "gastrodon", "ambipom", "drifloon", "drifblim", "buneary", "lopunny",
    "mismagius", "honchkrow", "glameow", "purugly", "chingling", "stunky",
    "skuntank", "bronzor", "bronzong", "bonsly", "mime-jr", "happiny",
    "chatot", "spiritomb", "gible", "gabite", "garchomp", "munchlax",
    "riolu", "lucario", "hippopotas", "hippowdon", "skorupi", "drapion",
    "croagunk", "toxicroak", "carnivine", "finneon", "lumineon", "mantyke",
    "snover", "abomasnow", "weavile", "magnezone", "lickilicky", "rhyperior",
    "tangrowth", "electivire", "magmortar", "togekiss", "yanmega", "leafeon",
    "glaceon", "gliscor", "mamoswine", "porygon-z", "gallade", "probopass",
    "dusknoir", "froslass", "rotom", "uxie", "mesprit", "azelf",
    "dialga", "palkia", "heatran", "regigigas", "giratina", "cresselia",
    "phione", "manaphy", "darkrai", "shaymin", "arceus",

    # Gen 5 - Unova
    "victini", "snivy", "servine", "serperior", "tepig", "pignite",
    "emboar", "oshawott", "dewott", "samurott", "patrat", "watchog",
    "lillipup", "herdier", "stoutland", "purrloin", "liepard", "pansage",
    "simisage", "pansear", "simisear", "panpour", "simipour", "munna",
    "musharna", "pidove", "tranquill", "unfezant", "blitzle", "zebstrika",
    "roggenrola", "boldore", "gigalith", "woobat", "swoobat", "drilbur",
    "excadrill", "audino", "timburr", "gurdurr", "conkeldurr", "tympole",
    "palpitoad", "seismitoad", "throh", "sawk", "sewaddle", "swadloon",
    "leavanny", "venipede", "whirlipede", "scolipede", "cottonee", "whimsicott",
    "petilil", "lilligant", "basculin", "sandile", "krokorok", "krookodile",
    "darumaka", "darmanitan", "maractus", "dwebble", "crustle", "scraggy",
    "scrafty", "sigilyph", "yamask", "cofagrigus", "tirtouga", "carracosta",
    "archen", "archeops", "trubbish", "garbodor", "zorua", "zoroark",
    "minccino", "cinccino", "gothita", "gothorita", "gothitelle", "solosis",
    "duosion", "reuniclus", "ducklett", "swanna", "vanillite", "vanillish",
    "vanilluxe", "deerling", "sawsbuck", "emolga", "karrablast", "escavalier",
    "foongus", "amoonguss", "frillish", "jellicent", "alomomola", "joltik",
    "galvantula", "ferroseed", "ferrothorn", "klink", "klang", "klinklang",
    "tynamo", "eelektrik", "eelektross", "elgyem", "beheeyem", "litwick",
    "lampent", "chandelure", "axew", "fraxure", "haxorus", "cubchoo",
    "beartic", "cryogonal", "shelmet", "accelgor", "stunfisk", "mienfoo",
    "mienshao", "druddigon", "golett", "golurk", "pawniard", "bisharp",
    "bouffalant", "rufflet", "braviary", "vullaby", "mandibuzz", "heatmor",
    "durant", "deino", "zweilous", "hydreigon", "larvesta", "volcarona",
    "cobalion", "terrakion", "virizion", "tornadus", "thundurus", "reshiram",
    "zekrom", "landorus", "kyurem", "keldeo", "meloetta", "genesect",

    # Gen 6 - Kalos
    "chespin", "quilladin", "chesnaught", "fennekin", "braixen", "delphox",
    "froakie", "frogadier", "greninja", "bunnelby", "diggersby", "fletchling",
    "fletchinder", "talonflame", "scatterbug", "spewpa", "vivillon", "litleo",
    "pyroar", "flabebe", "floette", "florges", "skiddo", "gogoat",
    "pancham", "pangoro", "furfrou", "espurr", "meowstic", "honedge",
    "doublade", "aegislash", "spritzee", "aromatisse", "swirlix", "slurpuff",
    "inkay", "malamar", "binacle", "barbaracle", "skrelp", "dragalge",
    "clauncher", "clawitzer", "helioptile", "heliolisk", "tyrunt", "tyrantrum",
    "amaura", "aurorus", "sylveon", "hawlucha", "dedenne", "carbink",
    "goomy", "sliggoo", "goodra", "klefki", "phantump", "trevenant",
    "pumpkaboo", "gourgeist", "bergmite", "avalugg", "noibat", "noivern",
    "xerneas", "yveltal", "zygarde", "diancie", "hoopa", "volcanion",

    # Gen 7 - Alola
    "rowlet", "dartrix", "decidueye", "litten", "torracat", "incineroar",
    "popplio", "brionne", "primarina", "pikipek", "trumbeak", "toucannon",
    "yungoos", "gumshoos", "grubbin", "charjabug", "vikavolt", "crabrawler",
    "crabominable", "oricorio", "cutiefly", "ribombee", "rockruff", "lycanroc",
    "wishiwashi", "mareanie", "toxapex", "mudbray", "mudsdale", "dewpider",
    "araquanid", "fomantis", "lurantis", "morelull", "shiinotic", "salandit",
    "salazzle", "stufful", "bewear", "bounsweet", "steenee", "tsareena",
    "comfey", "oranguru", "passimian", "wimpod", "golisopod", "sandygast",
    "palossand", "pyukumuku", "type-null", "silvally", "minior", "komala",
    "turtonator", "togedemaru", "mimikyu", "bruxish", "drampa", "dhelmise",
    "jangmo-o", "hakamo-o", "kommo-o", "tapu-koko", "tapu-lele", "tapu-bulu",
    "tapu-fini", "cosmog", "cosmoem", "solgaleo", "lunala", "nihilego",
    "buzzwole", "pheromosa", "xurkitree", "celesteela", "kartana", "guzzlord",
    "necrozma", "magearna", "marshadow", "poipole", "naganadel", "stakataka",
    "blacephalon", "zeraora", "meltan", "melmetal",

    # Gen 8 - Galar
    "grookey", "thwackey", "rillaboom", "scorbunny", "raboot", "cinderace",
    "sobble", "drizzile", "inteleon", "skwovet", "greedent", "rookidee",
    "corvisquire", "corviknight", "blipbug", "dottler", "orbeetle", "nickit",
    "thievul", "gossifleur", "eldegoss", "wooloo", "dubwool", "chewtle",
    "drednaw", "yamper", "boltund", "rolycoly", "carkol", "coalossal",
    "applin", "flapple", "appletun", "silicobra", "sandaconda", "cramorant",
    "arrokuda", "barraskewda", "toxel", "toxtricity", "sizzlipede", "centiskorch",
    "clobbopus", "grapploct", "sinistea", "polteageist", "hatenna", "hattrem",
    "hatterene", "impidimp", "morgrem", "grimmsnarl", "obstagoon", "perrserker",
    "cursola", "sirfetchd", "mr-rime", "runerigus", "milcery", "alcremie",
    "falinks", "pincurchin", "snom", "frosmoth", "stonjourner", "eiscue",
    "indeedee", "morpeko", "cufant", "copperajah", "dracozolt", "arctozolt",
    "dracovish", "arctovish", "duraludon", "dreepy", "drakloak", "dragapult",
    "zacian", "zamazenta", "eternatus", "kubfu", "urshifu", "zarude",
    "regieleki", "regidrago", "glastrier", "spectrier", "calyrex",

    # Gen 9 - Paldea
    "sprigatito", "floragato", "meowscarada", "fuecoco", "crocalor", "skeledirge",
    "quaxly", "quaxwell", "quaquaval", "lechonk", "oinkologne", "tarountula",
    "spidops", "nymble", "lokix", "pawmi", "pawmo", "pawmot",
    "tandemaus", "maushold", "fidough", "dachsbun", "smoliv", "dolliv",
    "arboliva", "squawkabilly", "nacli", "naclstack", "garganacl", "charcadet",
    "armarouge", "ceruledge", "tadbulb", "bellibolt", "wattrel", "kilowattrel",
    "maschiff", "mabosstiff", "shroodle", "grafaiai", "bramblin", "brambleghast",
    "toedscool", "toedscruel", "klawf", "capsakid", "scovillain", "rellor",
    "rabsca", "flittle", "espathra", "tinkatink", "tinkatuff", "tinkaton",
    "wiglett", "wugtrio", "bombirdier", "finizen", "palafin", "varoom",
    "revavroom", "cyclizar", "orthworm", "glimmet", "glimmora", "greavard",
    "houndstone", "flamigo", "cetoddle", "cetitan", "veluza", "dondozo",
    "tatsugiri", "annihilape", "clodsire", "farigiraf", "dudunsparce", "kingambit",
    "great-tusk", "scream-tail", "brute-bonnet", "flutter-mane", "slither-wing",
    "sandy-shocks", "iron-treads", "iron-bundle", "iron-hands", "iron-jugulis",
    "iron-moth", "iron-thorns", "baxcalibur", "gholdengo", "wo-chien",
    "chien-pao", "ting-lu", "chi-yu", "roaring-moon", "iron-valiant",
    "koraidon", "miraidon", "walking-wake", "iron-leaves", "dipplin",
    "poltchageist", "sinistcha", "okidogi", "munkidori", "fezandipiti",
    "ogerpon", "archaludon", "hydrapple", "vampeagus", "bloodmoon-ursaluna",
    "gouging-fire", "raging-bolt", "iron-boulder", "iron-crown", "terapagos",
    "pecharunt"
]

def run_egg_move_scraper(pokemon_list, skip_existing=True, output_file="data/modern_egg_moves.json"):
    """
    Run the egg move scraper for each Pokémon in the list.
    
    Args:
        pokemon_list: List of Pokémon names to process
        skip_existing: If True, skip Pokémon that already exist in the output file
        output_file: Path to the output JSON file
    """
    # First, let's check if we have existing data
    existing_data = {}
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            existing_data = json.load(f)
    
    # Count how many Pokémon we have in total
    total = len(pokemon_list)
    current = 0
    skipped = 0
    
    print(f"Starting egg move scraping for {total} Pokémon...")
    print(f"Output file: {output_file}")
    
    # Process each Pokémon one by one
    for pokemon in pokemon_list:
        current += 1
        
        # Format the Pokémon name for our data structure (SPECIES_NAME format)
        formatted_name = format_pokemon_name(pokemon)
        
        # Check if we can skip this Pokémon (if it's already in our data)
        if skip_existing and formatted_name in existing_data:
            print(f"\n[{current}/{total}] Skipping {pokemon} (already exists in output file)")
            skipped += 1
            continue
        
        print(f"\n[{current}/{total}] Processing {pokemon}...")
        
        try:
            # Run the egg move scraper for this Pokémon
            # The subprocess.run function lets us run another Python script
            print(f"Running egg move scraper for {pokemon}...")
            subprocess.run(["python", "egg_move_scraper.py", pokemon, "--output", output_file], 
                          check=True)
            
            # Wait a bit between requests to be polite to the server
            # This helps prevent getting blocked for making too many requests
            if current < total:
                sleep_time = 2  # seconds
                print(f"Waiting {sleep_time} seconds before next Pokémon...")
                time.sleep(sleep_time)
                
        except subprocess.CalledProcessError as e:
            # This catches errors if the scraper fails
            print(f"Error processing {pokemon}: {str(e)}")
        except KeyboardInterrupt:
            # This lets the user stop the script by pressing Ctrl+C
            print("\nProcess interrupted by user. Exiting...")
            break
    
    print(f"\nProcessed {current - skipped} Pokémon, skipped {skipped} existing Pokémon.")
    print(f"Batch scraping complete! Results saved to {output_file}")

def format_pokemon_name(name):
    """
    Convert a pokemon name from the URL format to our SPECIES_NAME format.
    
    Args:
        name: The Pokemon name in URL format (e.g. "mr-mime", "tapu-koko")
        
    Returns:
        The Pokemon name in SPECIES_NAME format
    """
    # Handle special cases with unusual formatting
    special_cases = {
        "nidoran-f": "NIDORAN_F",
        "nidoran-m": "NIDORAN_M",
        "mr-mime": "MR_MIME",
        "mime-jr": "MIME_JR",
        "tapu-koko": "TAPU_KOKO",
        "tapu-lele": "TAPU_LELE",
        "tapu-bulu": "TAPU_BULU",
        "tapu-fini": "TAPU_FINI",
        "type-null": "TYPE_NULL",
        "jangmo-o": "JANGMO_O",
        "hakamo-o": "HAKAMO_O",
        "kommo-o": "KOMMO_O",
        "wo-chien": "WO_CHIEN",
        "chien-pao": "CHIEN_PAO",
        "ting-lu": "TING_LU",
        "chi-yu": "CHI_YU",
    }
    
    if name.lower() in special_cases:
        return "SPECIES_" + special_cases[name.lower()]
    
    # For regular names, convert to uppercase and replace hyphens with underscores
    formatted_name = name.upper().replace('-', '_')
    
    return "SPECIES_" + formatted_name

def main():
    # Parse command line arguments (this lets us customize how the script runs)
    parser = argparse.ArgumentParser(description='Batch scrape egg moves for multiple Pokémon')
    parser.add_argument('--output', default='data/modern_egg_moves.json', 
                        help='Output JSON file (default: data/modern_egg_moves.json)')
    parser.add_argument('--no-skip', action='store_true', 
                        help='Do not skip Pokémon that already exist in the output file')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit how many Pokémon to process in this run')
    parser.add_argument('--start', type=int, default=0,
                        help='Start processing from this position in the Pokémon list (0-based)')
    parser.add_argument('--generation', type=int, choices=range(1, 10),
                        help='Only process Pokémon from this generation (1-9)')
    parser.add_argument('--pokemon', nargs='+',
                        help='Only process these specific Pokémon names')
    
    args = parser.parse_args()
    
    # Make sure the output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Select which Pokémon to process based on command line arguments
    selected_pokemon = pokemon_list
    
    # If specific Pokémon were requested, only process those
    if args.pokemon:
        selected_pokemon = [p for p in args.pokemon if p in pokemon_list]
        if not selected_pokemon:
            print("Warning: None of the specified Pokémon were found in the list.")
            return
    
    # If a generation was specified, filter by generation
    elif args.generation:
        # Define the start and end indices for each generation
        generation_ranges = {
            1: (0, 151),     # Gen 1: 151 Pokémon
            2: (151, 251),   # Gen 2: 100 Pokémon 
            3: (251, 386),   # Gen 3: 135 Pokémon
            4: (386, 493),   # Gen 4: 107 Pokémon
            5: (493, 649),   # Gen 5: 156 Pokémon
            6: (649, 721),   # Gen 6: 72 Pokémon
            7: (721, 809),   # Gen 7: 88 Pokémon
            8: (809, 905),   # Gen 8: 96 Pokémon
            9: (905, 1025)   # Gen 9: 120 Pokémon (or however many there are)
        }
        
        start_idx, end_idx = generation_ranges.get(args.generation, (0, len(pokemon_list)))
        selected_pokemon = pokemon_list[start_idx:end_idx]
        print(f"Selected {len(selected_pokemon)} Pokémon from Generation {args.generation}")
    
    # Apply start position if provided
    if args.start > 0:
        if args.start >= len(selected_pokemon):
            print(f"Start position {args.start} is beyond the end of the selected Pokémon list.")
            return
        selected_pokemon = selected_pokemon[args.start:]
        print(f"Starting from position {args.start} in the list")
    
    # Apply limit if provided
    if args.limit is not None and args.limit > 0:
        selected_pokemon = selected_pokemon[:args.limit]
        print(f"Limited to processing {args.limit} Pokémon")
    
    print(f"Will process {len(selected_pokemon)} Pokémon in this run")
    
    # Run the scraper with our settings
    run_egg_move_scraper(
        selected_pokemon, 
        skip_existing=not args.no_skip,
        output_file=args.output
    )

if __name__ == "__main__":
    main()
