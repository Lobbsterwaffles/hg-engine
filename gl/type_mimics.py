from enums import Type

# Type mimic data - Pokemon that thematically represent each type
# but don't actually have that type
type_mimics_data = {
        Type.BUG: [
            "Beartic", "Bewear", "Cubchoo", "Stufful", "Teddiursa", "Ursaring",
            "Clauncher", "Clawitzer", "Cloyster", "Corphish", "Crawdaunt", 
            "Krabby", "Kingler", "Shellder", "Cloyster", "Omanyte", "Omastar",
            "Drapion", "Skorupi", "Gligar", "Gliscor",
            "Flygon", "Trapinch", "Vibrava",
            "Munchlax", "Snorlax",
            "Orthworm",
            "Tangrowth",
            "Swirlix", "Slurpuff",
            "Hoppip", "Jumpluff", "Skiploom", "Roselia", "Budew", "Roserade",
            "Lurantis", "Fomantis",
            "Lanturn", "Chinchou", "Mareep", "Flaaffy", "Ampharos"
        ],
        
        Type.DARK: [
            "Accelgor", "Shelmet",
            "Carnivine",
            "Gastly", "Gengar", "Haunter", "Mimikyu",
            "Shinx", "Luxio", "Luxray",
            "Glalie", "Snorunt",
            "Gorebyss",
            "Lunatone",
            ("Lycanroc", "MIDNIGHT"),
            "Sandaconda", "Seviper", "Silicobra",
            "Noibat", "Noivern", "Swoobat", "Woobat", "Zubat", "Golbat", "Crobat",
            "Mareanie", "Toxapex",
            "Palossand", "Sandygast",
            "Volbeat", "Illumise",
            "Klefki",
            "Shroodle", "Grafaiai",
            "Girafarig", "Farigiraf", "Kecleon",
            "Pansage", "Pansear", "Panpour", "Simipour", "Simisear", "Simisage",
            "Whismur", "Loudred", "Exploud",
            ("Rattata", "ALOLAN"), ("Raticate", "ALOLAN"), 
        ],
        
        Type.DRAGON: [
            "Aerodactyl", "Amaura", "Aurorus", "Cranidos", "Rampardos",
            "Tyrantrum", "Tyrunt", "Archen", "Archeops",
            "Charizard", "Charmander", "Charmeleon",
            "Croconaw", "Feraligatr", "Totodile",
            "Grovyle", "Sceptile", "Treecko",
            "Gyarados", "Magikarp", "Seviper", "Arbok", "Ekans",
            "Sandaconda", "Silicobra", "Milotic",
            "Basclegion", "Dracovish", "Whiscash", "Barboach",
            "Lapras", "Relicanth",
            "Larvitar", "Pupitar", "Tyranitar",
            "Salandit", "Salazzle", "Scrafty", "Scraggy",
            "Onix", "Steelix",
            "Tropius",
            "Iron Neck", "IronThorns"
        ],
        
        Type.ELECTRIC: [
            "Archaludon", "Baltoy", "Claydol", "Klink", "Klang", "Klinklang",
            "Beldum", "Metang", "Metagross", "Genesect", "Celesteela",
            "Varoom", "Revavroom",
            "Carkol", "Coalossal", "Rolycoly",
            "Cryogonal",
            "Pelipper", "Politoed",
            "Porygon2", "Porygon-Z", "Porygon",
            "Castform",
            "Wooloo", "Dubwool", "Stufful", "Bewear",
            "Persian", ("Persian", "ALOLAN"), "Furfrou",
            "Greavard", "Houndstone",
            "Probopass", "Nosepass",
            "Cubone", "Marowak", ("Marowak", "ALOLAN"),
            "Rhyhorn", "Rhyperior", "Rhydon",
            "Goldeen", "Seaking"
        ],
        
        Type.FAIRY: [
            "Beldum", "Metagross", "Metang",
            "Bellossom", "Fomantis", "Lurantis", "Roserade",
            "Blissey", "Chansey", "Miltank",
            "Eldegoss", "Gossifleur", "Leavanny", "Sewaddle", "Swadloon",
            "Feebas", "Milotic", "Gallade",
            "Feebas", "Milotic", "Gallade",
            "Froslass", "Vanillish", "Vanilluxe", "Vanillite",
            "Minior",
            "Musharna",
            "Porygon2", "Porygon-Z",
            "Delibird"
        ],
        
        Type.FIGHTING: [
            "Ambipom",
            "Axew", "Fraxure", "Haxorus",
            "Croconaw", "Feraligatr", "Totodile",
            "Darmanitan", "Darumaka", "Incineroar", "Litten", "Torracat",
            "Dewott", "Oshawott", "Samurott",
            "Dusknoir", "Golett", "Golurk",
            "Kingambit",
            "Pinsir",
            "Sandshrew", "Sandslash",
            "Tauros", "Zangoose",
            "Elekid", "Electivire", "Electabuzz",
            "Slakoth", "Slaking", "Vigoroth"
        ],
        
        Type.FLYING: [
            "Baltoy", "Claydol",
            "Torchic", "Combusken", "Blaziken",
            "Piplup", "Prinplup", "Empoleon",
            "Charjabug", "Grubbin", "Vikavolt", "Larvesta", "Volcarona",
            "Venomoth", "Venonat",
            "Deino", "Hydreigon", "Zweilous", "Flygon", "Trapinch", "Vibrava",
            "Eiscue", "Frosmoth", "Snom",
            "Espathra", "Flittle",
            "Decidueye",
            ("Rotom", "FROST"), ("Rotom", "HEAT"), ("Rotom", "MOW"), ("Rotom", "WASH"),
            ("Farfetch’d", "GALARIAN"), "Sirfetch’d",
            "Porygon2", "Porygon-Z", "Porygon"
            
        ],
        
        Type.GHOST: [
            "Absol",
            "Baltoy", "Claydol", "Gothita", "Gothitelle", "Gothorita",
            "Hatenna", "Hatterene", "Hattrem",
            "Cacnea", "Cacturne",
            "Ninetales",
            "Paras", "Parasect", "Nincada", "Ninjask",
            "Seviper", "Toxel", "Toxtricity",
            "Weavile",
            "Zoroark", "Zorua", "Unown",
            "Chingling", "Chimecho", "Bronzor", "Bronzong",
            "Jynx", "Smoochum", 
        ],
        
        Type.GRASS: [
            "Beedrill", "Combee", "Vespiquen", "Weedle", "Kakuna",
            "Cutiefly", "Ribombee",
            "Comfey", "Florges",
            ("Farfetch’d", "GALARIAN"), "Sirfetch’d",
            "Oranguru",
            "Pyukumuku",
            "Sudowoodo",
            "Solrock",
            "Tauros", "Miltank", "Stantler", "Wyrdeer", "Bouffalant",
            "Helioptile", "Heliolisk", "Blitzle", "Zebstrika",
            "Torkoal", "Castform",
            "Mawile",
            "Azurill", "Azumarill", "Marill",
            "Goomy", "Sliggoo", "Goodra", ("Goodra", "HISUIAN"), ("Sliggoo", "HISUIAN"),
            "Drampa", "Girafarig", "Farigiraf"
        ],
        
        Type.GROUND: [
            "Amoonguss", "Foongus", "Shiinotic", "Morelull", "Shroomish", "Breloom",
            "Boldore", "Gigalith", "Roggenrola",
            "Copperajah", "Cufant", "Durant", "Orthworm",
            "Exeggutor", "Tropius", "Sudowoodo",
            "Greavard", "Houndstone",
            "Hitmontop", "Tyrogue",
            "Shiftry",
            "Dunsparce", "Dudunspars",
            "Wiglett", "Wugtrio",
            "Ninjask", "Shedinja",
            ("Sandslash", "ALOLAN"), ("Sandshrew", "ALOLAN"), ("Geodude", "ALOLAN"), ("Graveler", "ALOLAN"), ("Golem", "ALOLAN"),
            ("Marowak", "ALOLAN")
        ],
        
        Type.ICE: [
            "Altaria", "Swablu", "Tornadus", ("Tornadus", "THERIAN"),
            "Azumarill", "Azurill", "Marill", "Chinchou", "Lanturn",
            "Popplio", "Brionne", "Primarina",
            "Gorebyss", "Togekiss",
            "Grumpig", "Spoink",
            "Hariyama", "Makuhita", "Munchlax", "Snorlax", "Miltank",
            "Huntail", "Relicanth",
            "Kilowatrel", "Wattrel",
            "Gigalith", "Roggenrola", "Boldore",
            "Castform"
        ],
        
        Type.POISON: [
            "Breloom", "Shroomish", "Morelull", "Shiinotic",
            "Centskorch", "Cutiefly", "Ribombee", "Sizzlipede",
            "Froakie", "Frogadier", "Greninja", "Jellicent", "Octillery", "Remoraid",
            "Seismitoad",
            "Gliscor",
            "Munchlax", "Snorlax",
            "Paras", "Parasect",
            "Sandaconda", "Sandshrew", "Sandslash",
            "Serperior", "Servine", "Snivy",
            "Toedscool", "Toedscruel",
            "Zangoose", "Dunsparce", "Dudunspars",
            "Quagsire", "Wooper",
            "Horsea", "Seadra", "Kingdra",
            "Drowzee", "Hypno",
            "Bellossom",
            "Umbreon", "Shuckle", "Vespiquen", "Goomy", "Sliggoo", "Goodra", ("Goodra", "HISUIAN"), ("Sliggoo", "HISUIAN"),
           
        ],
        
        Type.PSYCHIC: [
            "Breloom", "Shroomish",
            ("Exeggutor", "ALOLAN"), "Florges",
            "Golduck", "Gorebyss", "Psyduck", "Poliwrath",
            "Hitmonlee", "Tyrogue",
            "Hoothoot", "Noctowl",
            "Mismagius",
            "Ninetales",
            "Venomoth", "Venonat", "Yanma", "Yanmega",
            "Porygon2", "Porygon-Z", "Porygon",
            "Sobble", "Drizzile", "Inteleon",
            "Gholdengo", "Gimmighoul",
            "Gumshoos", "Yungoos", "Persian", ("Persian", "ALOLAN"), "Meowth"
        ],
        
        Type.ROCK: [
            "Avalugg", "Bergmite", "Glalie", "Snorunt", "Cryogonal",
            "Beheeyem", "Elgyem",
            "Bombirdier",
            "Camerupt", "Darmanitan", "Darumaka", "Numel",
            "Conkeldurr", "Gurdurr", "Timburr",
            "Eevee", "Espeon",
            "Grotle", "Torterra", "Turtwig",
            "Grumpig", "Spoink",
            "Sableye", "Spiritomb",
            "Sandshrew", "Sandslash",
            "Starmie",
            "Steelix", "Cubone", "Marowak", ("Marowak", "ALOLAN"),
            "Bergmite", "Avalugg", ("Avalugg", "HISUIAN")
            
        ],
        
        Type.STEEL: [
            "Camerupt", "Numel",
            "Carkol", "Coalossal", "Rolycoly",
            "Charjabug", "Grubbin",
            "Conkeldurr", "Gurdurr", "Timburr",
            "Electrode", "Voltorb",
            "Grimer", "Koffing", "Muk", "Weezing",
            "Mudbray", "Mudsdale",
            "Porygon2", "Porygon-Z",
            "Rotom", ("Rotom", "FAN"), ("Rotom", "FROST"), ("Rotom", "HEAT"), ("Rotom", "MOW"), ("Rotom", "WASH"),
            "Geodude", ("Geodude", "ALOLAN"), ("Graveler", "ALOLAN"), ("Golem", "ALOLAN"),
            "Klawf",
            "Xurkitree"
        ],
        
        Type.FIRE: [
            "Bagon", "Salamence", "Shelgon",
            "Cyclizar", "Dachsbun", "Fidough",
            "Drifblim", "Drifloon",
            "Electrode", "Voltorb", "Luxio", "Luxray", "Shinx",
            "Heliolisk",
            "Koffing", "Weezing", ("Weezing", "GALARIAN"), "Skuntank", "Stunky",
            "Revavroom",
            "Solrock", "Bronzor", "Bronzong", "Polchgeist", "Sinistcha", "Frigibax", "Arctibax", "Baxcalibur",
            ("Ninetales", "ALOLAN"), ("Vulpix", "ALOLAN"), ("Ponyta", "GALARIAN"), ("Rapidash", "GALARIAN"),
            "Swellow", "Taillow",
            "Tyrantrum", "Tyrunt",
            "Eternatus", "WalkngWake", "RoarinMoon"
            
            
        ],
        
        Type.NORMAL: [
            "Azumarill", "Azurill", "Marill",
            "Blitzle", "Zebstrika",
            "Flechinder", "Fletchling", "Talonflame",
            "Gogoat", "Skiddo",
            "Liepard", "Purrloin", "Poochyena", "Mightyena",
            "Lycanroc",
            "Mienfoo", "Mienshao",
            "Mudbray", "Mudsdale",
            "Ponyta", "Rapidash", ("Ponyta", "GALARIAN"), ("Rapidash", "GALARIAN"),
            "Clefairy", "Clefable", "Cleffa", "Togepi", "Togetic", "Togekiss",
            "Snubbull", "Granbull",
            "Pachirisu", "Shinx", "Luxio", "Luxray",
            ("Meowth", "ALOLAN"), ("Persian", "ALOLAN")
        ],
        
        Type.WATER: [
            "Anorith", "Armaldo", "Cradily", "Lileep",
            "Bellibolt",
            "Klawf",
            "Clodsire", ("Corsola", "GALARIAN"), "Cursola", "Overqwil", ("Qwilfish", "HISUIAN"),
            "Crabomnabl",
            "Dhelmise",
            "Dragalge", "Skrelp",
            "Eelektross",
            "Inkay", "Malamar",
            "Pincurchin",
            "Serperior", "Servine", "Snivy",
            "Stunfisk",
            "Turtonator",
            ("Wooper", "PALDEAN"), ("Slowpoke", "PALDEAN"), ("Slowbro", "PALDEAN"), ("Slowking", "PALDEAN")
        ]
    }
    
