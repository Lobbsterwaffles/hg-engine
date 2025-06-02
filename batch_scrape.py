#!/usr/bin/env python
"""
Batch Scraper for Pokémon egg moves and TM moves
This script runs the egg_move_scraper.py and tm_move_scraper.py for a batch of Pokémon
"""
import subprocess
import time
import os

# List of popular fully evolved Pokémon from different generations
# Format is lowercase for scrapers to work with PokemonDB
pokemon_list = [
    # Gen 5 Legendaries
    "cobalion", "terrakion", "virizion", "tornadus", "thundurus",
    "reshiram", "zekrom", "landorus", "kyurem", "keldeo",
    "meloetta", "genesect",
    
    # Gen 6 Pokemon
    "chesnaught", "delphox", "greninja", "diggersby", "talonflame",
    "vivillon", "pyroar", "florges", "gogoat", "pangoro",
    "furfrou", "meowstic", "aegislash", "aromatisse", "slurpuff",
    "malamar", "barbaracle", "dragalge", "clawitzer", "heliolisk",
    "tyrantrum", "aurorus", "sylveon", "hawlucha", "dedenne",
    "carbink", "goodra", "klefki", "trevenant", "gourgeist",
    "avalugg", "noivern",
    
    # Gen 6 Legendaries
    "xerneas", "yveltal", "zygarde", "diancie", "hoopa", "volcanion",
    
    # Gen 7 Pokemon
    "decidueye", "incineroar", "primarina", "toucannon", "gumshoos",
    "vikavolt", "crabominable", "oricorio", "ribombee", "lycanroc",
    "wishiwashi", "toxapex", "mudsdale", "araquanid", "lurantis",
    "shiinotic", "salazzle", "bewear", "tsareena", "comfey",
    "oranguru", "passimian", "golisopod", "palossand", "silvally",
    "minior", "komala", "turtonator", "togedemaru", "mimikyu",
    "bruxish", "drampa", "dhelmise", "kommo-o",
    
    # Gen 7 Legendaries & Ultra Beasts
    "tapu-koko", "tapu-lele", "tapu-bulu", "tapu-fini",
    "cosmog", "cosmoem", "solgaleo", "lunala", "nihilego",
    "buzzwole", "pheromosa", "xurkitree", "celesteela", "kartana",
    "guzzlord", "necrozma", "magearna", "marshadow", "poipole",
    "naganadel", "stakataka", "blacephalon", "zeraora", "meltan", "melmetal",
    
    # Gen 8 Pokemon
    "rillaboom", "cinderace", "inteleon", "greedent", "corviknight",
    "orbeetle", "thievul", "eldegoss", "dubwool", "drednaw",
    "boltund", "coalossal", "flapple", "appletun", "sandaconda",
    "cramorant", "barraskewda", "toxtricity", "centiskorch", "grapploct",
    "polteageist", "hatterene", "grimmsnarl", "obstagoon", "perrserker",
    "cursola", "sirfetchd", "mr-rime", "runerigus", "alcremie",
    "falinks", "pincurchin", "frosmoth", "stonjourner", "eiscue",
    "indeedee", "morpeko", "copperajah", "dracozolt", "arctozolt",
    "dracovish", "arctovish", "duraludon", "dragapult",
    
    # Gen 8 Legendaries
    "zacian", "zamazenta", "eternatus", "kubfu", "urshifu",
    "zarude", "regieleki", "regidrago", "glastrier", "spectrier",
    "calyrex",
    
    # Gen 9 Pokemon
    "meowscarada", "skeledirge", "quaquaval", "oinkologne", "spidops",
    "lokix", "pawmot", "maushold", "dachsbun", "arboliva",
    "squawkabilly", "garganacl", "armarouge", "ceruledge", "bellibolt",
    "kilowattrel", "mabosstiff", "grafaiai", "brambleghast", "toedscruel",
    "klawf", "scovillain", "rabsca", "espathra", "tinkaton",
    "wugtrio", "bombirdier", "palafin", "revavroom", "cyclizar",
    "orthworm", "glimmora", "houndstone", "flamigo", "cetitan",
    "veluza", "dondozo", "tatsugiri", "annihilape", "clodsire",
    "farigiraf", "dudunsparce", "kingambit", "great-tusk", "scream-tail",
    "brute-bonnet", "flutter-mane", "slither-wing", "sandy-shocks",
    "iron-treads", "iron-bundle", "iron-hands", "iron-jugulis",
    "iron-moth", "iron-thorns", "baxcalibur", "gholdengo", "wo-chien",
    "chien-pao", "ting-lu", "chi-yu", "roaring-moon", "iron-valiant",
    "koraidon", "miraidon", "walking-wake", "iron-leaves", "dipplin",
    "poltchageist", "sinistcha", "okidogi", "munkidori", "fezandipiti",
    "ogerpon", "archaludon", "hydrapple", "vampeagus", "bloodmoon-ursaluna",
    "gouging-fire", "raging-bolt", "iron-boulder", "iron-crown", "terapagos",
    "pecharunt"
]

def run_scrapers():
    """Run both scrapers for each Pokémon in the list"""
    total = len(pokemon_list)
    current = 0
    
    for pokemon in pokemon_list:
        current += 1
        print(f"\n[{current}/{total}] Processing {pokemon}...")
        
        try:
            # Run egg move scraper
            print(f"Running egg move scraper for {pokemon}...")
            subprocess.run(["python", "egg_move_scraper.py", pokemon], 
                          check=True)
            
            # Wait between requests to be polite to the server
            time.sleep(2)
            
            # Run TM move scraper
            print(f"Running TM move scraper for {pokemon}...")
            subprocess.run(["python", "tm_move_scraper.py", pokemon], 
                          check=True)
            
            # Wait between Pokémon to be extra polite
            if current < total:
                print(f"Waiting 3 seconds before next Pokémon...")
                time.sleep(3)
                
        except subprocess.CalledProcessError as e:
            print(f"Error processing {pokemon}: {str(e)}")
        except KeyboardInterrupt:
            print("\nProcess interrupted by user. Exiting...")
            break

if __name__ == "__main__":
    print(f"Starting batch scraping for {len(pokemon_list)} Pokémon...")
    run_scrapers()
    print("\nBatch scraping complete!")
