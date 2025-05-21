"""
Complete Pokémon data for the randomizer.
Includes names and Base Stat Totals (BST) for all Pokémon.
"""

# A more complete list of Pokémon with their Base Stat Totals (BST)
POKEMON_BST = {
    # Gen 1
    1: {"name": "BULBASAUR", "bst": 318},
    2: {"name": "IVYSAUR", "bst": 405},
    3: {"name": "VENUSAUR", "bst": 525},
    4: {"name": "CHARMANDER", "bst": 309},
    5: {"name": "CHARMELEON", "bst": 405},
    6: {"name": "CHARIZARD", "bst": 534},
    7: {"name": "SQUIRTLE", "bst": 314},
    8: {"name": "WARTORTLE", "bst": 405},
    9: {"name": "BLASTOISE", "bst": 530},
    10: {"name": "CATERPIE", "bst": 195},
    11: {"name": "METAPOD", "bst": 205},
    12: {"name": "BUTTERFREE", "bst": 395},
    13: {"name": "WEEDLE", "bst": 195},
    14: {"name": "KAKUNA", "bst": 205},
    15: {"name": "BEEDRILL", "bst": 395},
    16: {"name": "PIDGEY", "bst": 251},
    17: {"name": "PIDGEOTTO", "bst": 349},
    18: {"name": "PIDGEOT", "bst": 479},
    19: {"name": "RATTATA", "bst": 253},
    20: {"name": "RATICATE", "bst": 413},
    21: {"name": "SPEAROW", "bst": 262},
    22: {"name": "FEAROW", "bst": 442},
    23: {"name": "EKANS", "bst": 288},
    24: {"name": "ARBOK", "bst": 448},
    25: {"name": "PIKACHU", "bst": 320},
    26: {"name": "RAICHU", "bst": 485},
    27: {"name": "SANDSHREW", "bst": 300},
    28: {"name": "SANDSLASH", "bst": 450},
    29: {"name": "NIDORAN♀", "bst": 275},
    30: {"name": "NIDORINA", "bst": 365},
    31: {"name": "NIDOQUEEN", "bst": 505},
    32: {"name": "NIDORAN♂", "bst": 273},
    33: {"name": "NIDORINO", "bst": 365},
    34: {"name": "NIDOKING", "bst": 505},
    35: {"name": "CLEFAIRY", "bst": 323},
    36: {"name": "CLEFABLE", "bst": 483},
    37: {"name": "VULPIX", "bst": 299},
    38: {"name": "NINETALES", "bst": 505},
    39: {"name": "JIGGLYPUFF", "bst": 270},
    40: {"name": "WIGGLYTUFF", "bst": 435},
    41: {"name": "ZUBAT", "bst": 245},
    42: {"name": "GOLBAT", "bst": 455},
    43: {"name": "ODDISH", "bst": 320},
    44: {"name": "GLOOM", "bst": 395},
    45: {"name": "VILEPLUME", "bst": 490},
    46: {"name": "PARAS", "bst": 285},
    47: {"name": "PARASECT", "bst": 405},
    48: {"name": "VENONAT", "bst": 305},
    49: {"name": "VENOMOTH", "bst": 450},
    50: {"name": "DIGLETT", "bst": 265},
    51: {"name": "DUGTRIO", "bst": 425},
    52: {"name": "MEOWTH", "bst": 290},
    53: {"name": "PERSIAN", "bst": 440},
    54: {"name": "PSYDUCK", "bst": 320},
    55: {"name": "GOLDUCK", "bst": 500},
    56: {"name": "MANKEY", "bst": 305},
    57: {"name": "PRIMEAPE", "bst": 455},
    58: {"name": "GROWLITHE", "bst": 350},
    59: {"name": "ARCANINE", "bst": 555},
    60: {"name": "POLIWAG", "bst": 300},
    61: {"name": "POLIWHIRL", "bst": 385},
    62: {"name": "POLIWRATH", "bst": 510},
    63: {"name": "ABRA", "bst": 310},
    64: {"name": "KADABRA", "bst": 400},
    65: {"name": "ALAKAZAM", "bst": 500},
    66: {"name": "MACHOP", "bst": 305},
    67: {"name": "MACHOKE", "bst": 405},
    68: {"name": "MACHAMP", "bst": 505},
    69: {"name": "BELLSPROUT", "bst": 300},
    70: {"name": "WEEPINBELL", "bst": 390},
    71: {"name": "VICTREEBEL", "bst": 490},
    72: {"name": "TENTACOOL", "bst": 335},
    73: {"name": "TENTACRUEL", "bst": 515},
    74: {"name": "GEODUDE", "bst": 300},
    75: {"name": "GRAVELER", "bst": 390},
    76: {"name": "GOLEM", "bst": 495},
    77: {"name": "PONYTA", "bst": 410},
    78: {"name": "RAPIDASH", "bst": 500},
    79: {"name": "SLOWPOKE", "bst": 315},
    80: {"name": "SLOWBRO", "bst": 490},
    81: {"name": "MAGNEMITE", "bst": 325},
    82: {"name": "MAGNETON", "bst": 465},
    83: {"name": "FARFETCH'D", "bst": 377},
    84: {"name": "DODUO", "bst": 310},
    85: {"name": "DODRIO", "bst": 470},
    86: {"name": "SEEL", "bst": 325},
    87: {"name": "DEWGONG", "bst": 475},
    88: {"name": "GRIMER", "bst": 325},
    89: {"name": "MUK", "bst": 500},
    90: {"name": "SHELLDER", "bst": 305},
    91: {"name": "CLOYSTER", "bst": 525},
    92: {"name": "GASTLY", "bst": 310},
    93: {"name": "HAUNTER", "bst": 405},
    94: {"name": "GENGAR", "bst": 500},
    95: {"name": "ONIX", "bst": 385},
    96: {"name": "DROWZEE", "bst": 328},
    97: {"name": "HYPNO", "bst": 483},
    98: {"name": "KRABBY", "bst": 325},
    99: {"name": "KINGLER", "bst": 475},
    100: {"name": "VOLTORB", "bst": 330},
    
    # Gen 2
    152: {"name": "CHIKORITA", "bst": 318},
    153: {"name": "BAYLEEF", "bst": 410},
    154: {"name": "MEGANIUM", "bst": 525},
    155: {"name": "CYNDAQUIL", "bst": 309},
    156: {"name": "QUILAVA", "bst": 405},
    157: {"name": "TYPHLOSION", "bst": 534},
    158: {"name": "TOTODILE", "bst": 314},
    159: {"name": "CROCONAW", "bst": 405},
    160: {"name": "FERALIGATR", "bst": 530},
    161: {"name": "SENTRET", "bst": 215},
    162: {"name": "FURRET", "bst": 415},
    163: {"name": "HOOTHOOT", "bst": 262},
    164: {"name": "NOCTOWL", "bst": 442},
    165: {"name": "LEDYBA", "bst": 265},
    166: {"name": "LEDIAN", "bst": 390},
    167: {"name": "SPINARAK", "bst": 250},
    168: {"name": "ARIADOS", "bst": 390},
    169: {"name": "CROBAT", "bst": 535},
    170: {"name": "CHINCHOU", "bst": 330},
    
    # Gen 4 Starters
    387: {"name": "TURTWIG", "bst": 318},
    388: {"name": "GROTLE", "bst": 405},
    389: {"name": "TORTERRA", "bst": 525},
    390: {"name": "CHIMCHAR", "bst": 309},
    391: {"name": "MONFERNO", "bst": 405},
    392: {"name": "INFERNAPE", "bst": 534},
    393: {"name": "PIPLUP", "bst": 314},
    394: {"name": "PRINPLUP", "bst": 405},
    395: {"name": "EMPOLEON", "bst": 530},
    
    # Some legendaries (for the special list)
    144: {"name": "ARTICUNO", "bst": 580},
    145: {"name": "ZAPDOS", "bst": 580},
    146: {"name": "MOLTRES", "bst": 580},
    150: {"name": "MEWTWO", "bst": 680},
    151: {"name": "MEW", "bst": 600},
    243: {"name": "RAIKOU", "bst": 580},
    244: {"name": "ENTEI", "bst": 580},
    245: {"name": "SUICUNE", "bst": 580},
    249: {"name": "LUGIA", "bst": 680},
    250: {"name": "HO-OH", "bst": 680},
    251: {"name": "CELEBI", "bst": 600},
}

# Special Pokémon that won't be randomized
SPECIAL_POKEMON = [
    144,  # Articuno
    145,  # Zapdos
    146,  # Moltres
    150,  # Mewtwo
    151,  # Mew
    243,  # Raikou
    244,  # Entei
    245,  # Suicune
    249,  # Lugia
    250,  # Ho-Oh
    251,  # Celebi
    377,  # Regirock
    378,  # Regice
    379,  # Registeel
    380,  # Latias
    381,  # Latios
    382,  # Kyogre
    383,  # Groudon
    384,  # Rayquaza
    385,  # Jirachi
    386,  # Deoxys
    480,  # Uxie
    481,  # Mesprit
    482,  # Azelf
    483,  # Dialga
    484,  # Palkia
    485,  # Heatran
    486,  # Regigigas
    487,  # Giratina
    488,  # Cresselia
    489,  # Phione
    490,  # Manaphy
    491,  # Darkrai
    492,  # Shaymin
    493,  # Arceus
]
