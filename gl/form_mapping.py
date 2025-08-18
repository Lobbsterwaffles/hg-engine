"""
Form mapping system for Pokemon randomizer.

This module provides form detection and mapping functionality for Pokemon forms.
Forms are Pokemon variants that have "-----" names in the mondata and use different
species IDs from the base Pokemon.

The system categorizes forms into 5 types:
- Discrete: Regional variants and other permanent forms
- Cosmetic: Visual-only changes
- Battle Only: Forms that only appear in battle
- Out of Battle Change: Forms that change outside battle
- Held Item: Forms triggered by held items
"""

from typing import Dict, Tuple, List, Optional, Set
from enum import Enum
from framework import Extractor, LoadPokemonNamesStep


class FormCategory(Enum):
    """Categories of Pokemon forms."""
    DISCRETE = "discrete"  # Regional variants and other permanent forms
    COSMETIC = "cosmetic"  # Visual-only changes
    BATTLE_ONLY = "battle_only"  # Forms that only appear in battle
    OUT_OF_BATTLE_CHANGE = "out_of_battle_change"  # Forms that change outside battle
    HELD_ITEM = "held_item"  # for brevity, this includes Keldeo/secret sword
    GENDER_DIMORPHISM = "gender_dimorphism"  # Forms with significant gender differences
    INVALID = "invalid"  # Forms that are not properly categorized or don't exist


# Helper functions for common form patterns
# These work when all forms of a Pokemon have the same category
def alolan(start_index: int) -> Tuple[int, List[Tuple[str, FormCategory]]]:
    """Helper for Alolan forms."""
    return (start_index, [("ALOLAN", FormCategory.DISCRETE)])

def galarian(start_index: int) -> Tuple[int, List[Tuple[str, FormCategory]]]:
    """Helper for Galarian forms."""
    return (start_index, [("GALARIAN", FormCategory.DISCRETE)])

def hisuian(start_index: int) -> Tuple[int, List[Tuple[str, FormCategory]]]:
    """Helper for Hisuian forms."""
    return (start_index, [("HISUIAN", FormCategory.DISCRETE)])

def discrete(start_index: int, forms: List[str]) -> Tuple[int, List[Tuple[str, FormCategory]]]:
    """Helper for discrete forms (all forms have same category)."""
    return (start_index, [(form, FormCategory.DISCRETE) for form in forms])

def cosmetic(start_index: int, forms: List[str]) -> Tuple[int, List[Tuple[str, FormCategory]]]:
    """Helper for cosmetic forms (all forms have same category)."""
    return (start_index, [(form, FormCategory.COSMETIC) for form in forms])

def battle_only(start_index: int, forms: List[str]) -> Tuple[int, List[Tuple[str, FormCategory]]]:
    """Helper for battle-only forms (all forms have same category)."""
    return (start_index, [(form, FormCategory.BATTLE_ONLY) for form in forms])

def out_of_battle(start_index: int, forms: List[str]) -> Tuple[int, List[Tuple[str, FormCategory]]]:
    """Helper for out-of-battle change forms (all forms have same category)."""
    return (start_index, [(form, FormCategory.OUT_OF_BATTLE_CHANGE) for form in forms])

def held_item(start_index: int, forms: List[str]) -> Tuple[int, List[Tuple[str, FormCategory]]]:
    """Helper for held item forms (all forms have same category)."""
    return (start_index, [(form, FormCategory.HELD_ITEM) for form in forms])

def gender_dimorphism(start_index: int, forms: List[str]) -> Tuple[int, List[Tuple[str, FormCategory]]]:
    """Helper for gender dimorphism forms (all forms have same category)."""
    return (start_index, [(form, FormCategory.GENDER_DIMORPHISM) for form in forms])

def invalid(start_index: int, forms: List[str]) -> Tuple[int, List[Tuple[str, FormCategory]]]:
    """Helper for invalid forms (all forms have same category)."""
    return (start_index, [(form, FormCategory.INVALID) for form in forms])


class FormMapper(Extractor):
    """Maps Pokemon form IDs to their base species and form information."""
    
    # All forms in one unified dictionary
    # Format: form_id: ("BaseName", "form_name", FormCategory)
    ALL_FORMS = {
        # Alolan forms (1126-1143)
        1126: ("Rattata", "ALOLAN", FormCategory.DISCRETE),
        1127: ("Raticate", "ALOLAN", FormCategory.DISCRETE),
        1128: ("Raichu", "ALOLAN", FormCategory.DISCRETE),
        1129: ("Sandshrew", "ALOLAN", FormCategory.DISCRETE),
        1130: ("Sandslash", "ALOLAN", FormCategory.DISCRETE),
        1131: ("Vulpix", "ALOLAN", FormCategory.DISCRETE),
        1132: ("Ninetales", "ALOLAN", FormCategory.DISCRETE),
        1133: ("Diglett", "ALOLAN", FormCategory.DISCRETE),
        1134: ("Dugtrio", "ALOLAN", FormCategory.DISCRETE),
        1135: ("Meowth", "ALOLAN", FormCategory.DISCRETE),
        1136: ("Persian", "ALOLAN", FormCategory.DISCRETE),
        1137: ("Geodude", "ALOLAN", FormCategory.DISCRETE),
        1138: ("Graveler", "ALOLAN", FormCategory.DISCRETE),
        1139: ("Golem", "ALOLAN", FormCategory.DISCRETE),
        1140: ("Grimer", "ALOLAN", FormCategory.DISCRETE),
        1141: ("Muk", "ALOLAN", FormCategory.DISCRETE),
        1142: ("Exeggutor", "ALOLAN", FormCategory.DISCRETE),
        1143: ("Marowak", "ALOLAN", FormCategory.DISCRETE),
        
        # Galarian forms (1156-1174)
        1156: ("Meowth", "GALARIAN", FormCategory.DISCRETE),
        1157: ("Ponyta", "GALARIAN", FormCategory.DISCRETE),
        1158: ("Rapidash", "GALARIAN", FormCategory.DISCRETE),
        1159: ("Slowpoke", "GALARIAN", FormCategory.DISCRETE),
        1160: ("Slowbro", "GALARIAN", FormCategory.DISCRETE),
        1161: ("Farfetch’d", "GALARIAN", FormCategory.DISCRETE),
        1162: ("Weezing", "GALARIAN", FormCategory.DISCRETE),
        1163: ("Mr. Mime", "GALARIAN", FormCategory.DISCRETE),
        1164: ("Articuno", "GALARIAN", FormCategory.DISCRETE),
        1165: ("Zapdos", "GALARIAN", FormCategory.DISCRETE),
        1166: ("Moltres", "GALARIAN", FormCategory.DISCRETE),
        1167: ("Slowking", "GALARIAN", FormCategory.DISCRETE),
        1168: ("Corsola", "GALARIAN", FormCategory.DISCRETE),
        1169: ("Zigzagoon", "GALARIAN", FormCategory.DISCRETE),
        1170: ("Linoone", "GALARIAN", FormCategory.DISCRETE),
        1171: ("Darumaka", "GALARIAN", FormCategory.DISCRETE),
        1172: ("Darmanitan", "GALARIAN", FormCategory.DISCRETE),
        1173: ("Yamask", "GALARIAN", FormCategory.DISCRETE),
        1174: ("Stunfisk", "GALARIAN", FormCategory.DISCRETE),
        
        # Hisuian forms (1326-1341)
        1326: ("Growlithe", "HISUIAN", FormCategory.DISCRETE),
        1327: ("Arcanine", "HISUIAN", FormCategory.DISCRETE),
        1328: ("Voltorb", "HISUIAN", FormCategory.DISCRETE),
        1329: ("Electrode", "HISUIAN", FormCategory.DISCRETE),
        1330: ("Typhlosion", "HISUIAN", FormCategory.DISCRETE),
        1331: ("Qwilfish", "HISUIAN", FormCategory.DISCRETE),
        1332: ("Sneasel", "HISUIAN", FormCategory.DISCRETE),
        1333: ("Samurott", "HISUIAN", FormCategory.DISCRETE),
        1334: ("Lilligant", "HISUIAN", FormCategory.DISCRETE),
        1335: ("Zorua", "HISUIAN", FormCategory.DISCRETE),
        1336: ("Zoroark", "HISUIAN", FormCategory.DISCRETE),
        1337: ("Braviary", "HISUIAN", FormCategory.DISCRETE),
        1338: ("Sliggoo", "HISUIAN", FormCategory.DISCRETE),
        1339: ("Goodra", "HISUIAN", FormCategory.DISCRETE),
        1340: ("Avalugg", "HISUIAN", FormCategory.DISCRETE),
        1341: ("Decidueye", "HISUIAN", FormCategory.DISCRETE),
        
        # Other discrete forms from MISC_FORM_START (1175+)
        1175: ("Pikachu", "COSPLAY", FormCategory.DISCRETE),
        1176: ("Pikachu", "ROCK_STAR", FormCategory.DISCRETE),
        1177: ("Pikachu", "BELLE", FormCategory.OUT_OF_BATTLE_CHANGE),
        1178: ("Pikachu", "POP_STAR", FormCategory.OUT_OF_BATTLE_CHANGE),
        1179: ("Pikachu", "PH_D", FormCategory.OUT_OF_BATTLE_CHANGE),
        1180: ("Pikachu", "LIBRE", FormCategory.OUT_OF_BATTLE_CHANGE),
        1181: ("Pikachu", "ORIGINAL_CAP", FormCategory.COSMETIC),
        1182: ("Pikachu", "HOENN_CAP", FormCategory.COSMETIC),
        1183: ("Pikachu", "SINNOH_CAP", FormCategory.COSMETIC),
        1184: ("Pikachu", "UNOVA_CAP", FormCategory.COSMETIC),
        1185: ("Pikachu", "KALOS_CAP", FormCategory.COSMETIC),
        1186: ("Pikachu", "ALOLA_CAP", FormCategory.COSMETIC),
        1187: ("Pikachu", "PARTNER_CAP", FormCategory.COSMETIC),
        1188: ("Pikachu", "WORLD_CAP", FormCategory.COSMETIC),

        #Paldean Forms (PALDEAN_FORMS_START = 1354)
        1354: ("Maushold", "FAMILY_OF_THREE", FormCategory.COSMETIC),  # PALDEAN_FORMS_START + 0
        1355: ("Squawkbily", "BLUE_PLUMAGE", FormCategory.COSMETIC),  # PALDEAN_FORMS_START + 1
        1356: ("Squawkbily", "YELLOW_PLUMAGE", FormCategory.COSMETIC),  # PALDEAN_FORMS_START + 2
        1357: ("Squawkbily", "WHITE_PLUMAGE", FormCategory.COSMETIC),  # PALDEAN_FORMS_START + 3
        1358: ("Palafin", "HERO", FormCategory.BATTLE_ONLY),  # PALDEAN_FORMS_START + 4
        1359: ("Tatsugiri", "DROOPY", FormCategory.COSMETIC),  # PALDEAN_FORMS_START + 5
        1360: ("Tatsugiri", "STRETCHY", FormCategory.COSMETIC),  # PALDEAN_FORMS_START + 6
        1361: ("Dudunspars", "THREE_SEGMENT", FormCategory.COSMETIC),  # PALDEAN_FORMS_START + 7
        1362: ("Gimmighoul", "ROAMING", FormCategory.OUT_OF_BATTLE_CHANGE),  # PALDEAN_FORMS_START + 8
        1363: ("Wooper", "PALDEAN", FormCategory.DISCRETE),  # PALDEAN_FORMS_START + 9
        1364: ("Tauros", "COMBAT", FormCategory.DISCRETE),  # PALDEAN_FORMS_START + 10
        1365: ("Tauros", "BLAZE", FormCategory.DISCRETE),  # PALDEAN_FORMS_START + 11
        1366: ("Tauros", "AQUA", FormCategory.DISCRETE),  # PALDEAN_FORMS_START + 12
        
        1381: ("Polchgeist", "MASTERPIECE", FormCategory.COSMETIC),  # PALDEAN_FORMS_START + 27
        1382: ("Sinistcha", "MASTERPIECE", FormCategory.COSMETIC),  # PALDEAN_FORMS_START + 28
        
        1390: ("Ursaluna", "BLOODMOON", FormCategory.DISCRETE),  # PALDEAN_FORMS_START + 36
        
        # Ogerpon Terastal forms (PALDEAN_FORMS_START + 32 to 35)
        1386: ("Ogerpon", "TEAL_MASK_TERASTAL", FormCategory.BATTLE_ONLY),  # PALDEAN_FORMS_START + 32
        1387: ("Ogerpon", "WELLSPRING_MASK_TERASTAL", FormCategory.BATTLE_ONLY),  # PALDEAN_FORMS_START + 33
        1388: ("Ogerpon", "HEARTHFLAME_MASK_TERASTAL", FormCategory.BATTLE_ONLY),  # PALDEAN_FORMS_START + 34
        1389: ("Ogerpon", "CORNERSTONE_MASK_TERASTAL", FormCategory.BATTLE_ONLY),  # PALDEAN_FORMS_START + 35
        
        # Terapagos forms (PALDEAN_FORMS_START + 37, 38)
        1391: ("Terapagos", "TERASTAL", FormCategory.BATTLE_ONLY),  # PALDEAN_FORMS_START + 37
        1392: ("Terapagos", "STELLAR", FormCategory.BATTLE_ONLY),  # PALDEAN_FORMS_START + 38
        
        1189: ("Castform", "SUNNY", FormCategory.BATTLE_ONLY),
        1190: ("Castform", "RAINY", FormCategory.BATTLE_ONLY),
        1191: ("Castform", "SNOWY", FormCategory.BATTLE_ONLY),
        
        1192: ("Cherrim", "SUNSHINE", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 17
        1193: ("Shellos", "EAST_SEA", FormCategory.COSMETIC),  # MISC_FORM_START + 18
        1194: ("Gastrodon", "EAST_SEA", FormCategory.COSMETIC),  # MISC_FORM_START + 19
        
        1195: ("Dialga", "ORIGIN", FormCategory.HELD_ITEM),  # MISC_FORM_START + 20
        1196: ("Palkia", "ORIGIN", FormCategory.HELD_ITEM),  # MISC_FORM_START + 21
        
        # Deerling seasonal forms (MISC_FORM_START + 26 to 28)
        1201: ("Deerling", "SUMMER", FormCategory.COSMETIC),  # MISC_FORM_START + 26
        1202: ("Deerling", "AUTUMN", FormCategory.COSMETIC),  # MISC_FORM_START + 27
        1203: ("Deerling", "WINTER", FormCategory.COSMETIC),  # MISC_FORM_START + 28
        
        # Sawsbuck seasonal forms (MISC_FORM_START + 29 to 31)
        1204: ("Sawsbuck", "SUMMER", FormCategory.COSMETIC),  # MISC_FORM_START + 29
        1205: ("Sawsbuck", "AUTUMN", FormCategory.COSMETIC),  # MISC_FORM_START + 30
        1206: ("Sawsbuck", "WINTER", FormCategory.COSMETIC),  # MISC_FORM_START + 31
        
        1218: ("Greninja", "BATTLE_BOND", FormCategory.DISCRETE),  # MISC_FORM_START + 43
        1219: ("Greninja", "ASH", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 44
        
        # Vivillon patterns (MISC_FORM_START + 45 to 63)
        1220: ("Vivillon", "POLAR", FormCategory.COSMETIC),
        1221: ("Vivillon", "TUNDRA", FormCategory.COSMETIC),
        1222: ("Vivillon", "CONTINENTAL", FormCategory.COSMETIC),
        1223: ("Vivillon", "GARDEN", FormCategory.COSMETIC),
        1224: ("Vivillon", "ELEGANT", FormCategory.COSMETIC),
        1225: ("Vivillon", "MEADOW", FormCategory.COSMETIC),
        1226: ("Vivillon", "MODERN", FormCategory.COSMETIC),
        1227: ("Vivillon", "MARINE", FormCategory.COSMETIC),
        1228: ("Vivillon", "ARCHIPELAGO", FormCategory.COSMETIC),
        1229: ("Vivillon", "HIGH_PLAINS", FormCategory.COSMETIC),
        1230: ("Vivillon", "SANDSTORM", FormCategory.COSMETIC),
        1231: ("Vivillon", "RIVER", FormCategory.COSMETIC),
        1232: ("Vivillon", "MONSOON", FormCategory.COSMETIC),
        1233: ("Vivillon", "SAVANNA", FormCategory.COSMETIC),
        1234: ("Vivillon", "SUN", FormCategory.COSMETIC),
        1235: ("Vivillon", "OCEAN", FormCategory.COSMETIC),
        1236: ("Vivillon", "JUNGLE", FormCategory.COSMETIC),
        1237: ("Vivillon", "FANCY", FormCategory.COSMETIC),
        1238: ("Vivillon", "POKE_BALL", FormCategory.COSMETIC),
        
        # Flabébé flowers (MISC_FORM_START + 64 to 67)
        1239: ("Flabébé", "YELLOW_FLOWER", FormCategory.COSMETIC),
        1240: ("Flabébé", "ORANGE_FLOWER", FormCategory.COSMETIC),
        1241: ("Flabébé", "BLUE_FLOWER", FormCategory.COSMETIC),
        1242: ("Flabébé", "WHITE_FLOWER", FormCategory.COSMETIC),
        
        # Floette flowers (MISC_FORM_START + 68 to 71)
        1243: ("Floette", "YELLOW_FLOWER", FormCategory.COSMETIC),
        1244: ("Floette", "ORANGE_FLOWER", FormCategory.COSMETIC),
        1245: ("Floette", "BLUE_FLOWER", FormCategory.COSMETIC),
        1246: ("Floette", "WHITE_FLOWER", FormCategory.COSMETIC),
        
        1197: ("Basculin", "BLUE_STRIPED", FormCategory.COSMETIC),  # MISC_FORM_START + 22
        1198: ("Basculin", "WHITE_STRIPED", FormCategory.DISCRETE),  # MISC_FORM_START + 23
        
        # Battle-only forms
        1199: ("Darmanitan", "ZEN_MODE", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 24
        1200: ("Darmanitan", "ZEN_MODE_GALARIAN", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 25
        
        1247: ("Floette", "ETERNAL_FLOWER", FormCategory.DISCRETE),  # MISC_FORM_START + 72
        
        # Florges flowers (MISC_FORM_START + 73 to 76)
        1248: ("Florges", "YELLOW_FLOWER", FormCategory.COSMETIC),
        1249: ("Florges", "ORANGE_FLOWER", FormCategory.COSMETIC),
        1250: ("Florges", "BLUE_FLOWER", FormCategory.COSMETIC),
        1251: ("Florges", "WHITE_FLOWER", FormCategory.COSMETIC),
        
        # Furfrou trims (MISC_FORM_START + 77 to 85)
        1252: ("Furfrou", "HEART", FormCategory.COSMETIC),
        1253: ("Furfrou", "STAR", FormCategory.COSMETIC),
        1254: ("Furfrou", "DIAMOND", FormCategory.COSMETIC),
        1255: ("Furfrou", "DEBUTANTE", FormCategory.COSMETIC),
        1256: ("Furfrou", "MATRON", FormCategory.COSMETIC),
        1257: ("Furfrou", "DANDY", FormCategory.COSMETIC),
        1258: ("Furfrou", "LA_REINE", FormCategory.COSMETIC),
        1259: ("Furfrou", "KABUKI", FormCategory.COSMETIC),
        1260: ("Furfrou", "PHARAOH", FormCategory.COSMETIC),
        
        1261: ("Aegislash", "BLADE", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 86
        
        1262: ("Xerneas", "ACTIVE", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 93
        
        1269: ("Zygarde", "10", FormCategory.DISCRETE),  # MISC_FORM_START + 94
        1270: ("Zygarde", "10_POWER_CONSTRUCT", FormCategory.DISCRETE),  # MISC_FORM_START + 95
        1271: ("Zygarde", "50_POWER_CONSTRUCT", FormCategory.DISCRETE),  # MISC_FORM_START + 96
        1272: ("Zygarde", "10_COMPLETE", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 97
        1273: ("Zygarde", "50_COMPLETE", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 98
        
        1274: ("Hoopa", "UNBOUND", FormCategory.DISCRETE),  # MISC_FORM_START + 99
        
        # Kyurem forms (MISC_FORM_START + 35, 36)
        1210: ("Kyurem", "WHITE", FormCategory.DISCRETE),  # MISC_FORM_START + 35
        1211: ("Kyurem", "BLACK", FormCategory.DISCRETE),  # MISC_FORM_START + 36
        
        1212: ("Keldeo", "RESOLUTE", FormCategory.HELD_ITEM),  # MISC_FORM_START + 37
        1213: ("Meloetta", "PIROUETTE", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 38
        
        # Genesect drive forms (MISC_FORM_START + 39 to 42)
        1214: ("Genesect", "DOUSE_DRIVE", FormCategory.HELD_ITEM),  # MISC_FORM_START + 39
        1215: ("Genesect", "SHOCK_DRIVE", FormCategory.HELD_ITEM),  # MISC_FORM_START + 40
        1216: ("Genesect", "BURN_DRIVE", FormCategory.HELD_ITEM),  # MISC_FORM_START + 41
        1217: ("Genesect", "CHILL_DRIVE", FormCategory.HELD_ITEM),  # MISC_FORM_START + 42
        
        # Therian forms (MISC_FORM_START + 32 to 34, and 150)
        1207: ("Tornadus", "THERIAN", FormCategory.OUT_OF_BATTLE_CHANGE),  # MISC_FORM_START + 32
        1208: ("Thundurus", "THERIAN", FormCategory.OUT_OF_BATTLE_CHANGE),  # MISC_FORM_START + 33
        1209: ("Landorus", "THERIAN", FormCategory.OUT_OF_BATTLE_CHANGE),  # MISC_FORM_START + 34
        1325: ("Enamorus", "THERIAN", FormCategory.OUT_OF_BATTLE_CHANGE),  # MISC_FORM_START + 150
        
        # Rotom forms (species 503-507)
        503: ("Rotom", "HEAT", FormCategory.OUT_OF_BATTLE_CHANGE),
        504: ("Rotom", "WASH", FormCategory.OUT_OF_BATTLE_CHANGE),
        505: ("Rotom", "FROST", FormCategory.OUT_OF_BATTLE_CHANGE),
        506: ("Rotom", "FAN", FormCategory.OUT_OF_BATTLE_CHANGE),
        507: ("Rotom", "MOW", FormCategory.OUT_OF_BATTLE_CHANGE),
        
        # Deoxys forms (species 496-498)
        496: ("Deoxys", "ATTACK", FormCategory.OUT_OF_BATTLE_CHANGE),
        497: ("Deoxys", "DEFENSE", FormCategory.OUT_OF_BATTLE_CHANGE),
        498: ("Deoxys", "SPEED", FormCategory.OUT_OF_BATTLE_CHANGE),
        
        # Calyrex riders (MISC_FORM_START + 148, 149)
        1323: ("Calyrex", "ICE_RIDER", FormCategory.OUT_OF_BATTLE_CHANGE),  # MISC_FORM_START + 148
        1324: ("Calyrex", "SHADOW_RIDER", FormCategory.OUT_OF_BATTLE_CHANGE),  # MISC_FORM_START + 149
        
        1275: ("Oricorio", "POM_POM", FormCategory.DISCRETE),  # MISC_FORM_START + 100
        1276: ("Oricorio", "PAU", FormCategory.DISCRETE),  # MISC_FORM_START + 101
        1277: ("Oricorio", "SENSU", FormCategory.DISCRETE),  # MISC_FORM_START + 102
        
        1278: ("Rockruff", "OWN_TEMPO", FormCategory.DISCRETE),  # MISC_FORM_START + 103
        1279: ("Lycanroc", "MIDNIGHT", FormCategory.DISCRETE),  # MISC_FORM_START + 104
        1280: ("Lycanroc", "DUSK", FormCategory.DISCRETE),  # MISC_FORM_START + 105
        
        1281: ("Wishiwashi", "SCHOOL", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 106
        
        # Minior meteors and cores (MISC_FORM_START + 107 to 119)
        1282: ("Minior", "METEOR_ORANGE", FormCategory.COSMETIC),
        1283: ("Minior", "METEOR_YELLOW", FormCategory.COSMETIC),
        1284: ("Minior", "METEOR_GREEN", FormCategory.COSMETIC),
        1285: ("Minior", "METEOR_BLUE", FormCategory.COSMETIC),
        1286: ("Minior", "METEOR_INDIGO", FormCategory.COSMETIC),
        1287: ("Minior", "METEOR_VIOLET", FormCategory.COSMETIC),
        1288: ("Minior", "CORE_RED", FormCategory.BATTLE_ONLY),
        1289: ("Minior", "CORE_ORANGE", FormCategory.BATTLE_ONLY),
        1290: ("Minior", "CORE_YELLOW", FormCategory.BATTLE_ONLY),
        1291: ("Minior", "CORE_GREEN", FormCategory.BATTLE_ONLY),
        1292: ("Minior", "CORE_BLUE", FormCategory.BATTLE_ONLY),
        1293: ("Minior", "CORE_INDIGO", FormCategory.BATTLE_ONLY),
        1294: ("Minior", "CORE_VIOLET", FormCategory.BATTLE_ONLY),
        
        1295: ("Mimikyu", "BUSTED", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 120
        
        1296: ("Necrozma", "DUSK_MANE", FormCategory.OUT_OF_BATTLE_CHANGE),  # MISC_FORM_START + 121
        1297: ("Necrozma", "DAWN_WINGS", FormCategory.OUT_OF_BATTLE_CHANGE),  # MISC_FORM_START + 122
        1298: ("Necrozma", "ULTRA_DUSK_MANE", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 123
        1299: ("Necrozma", "ULTRA_DAWN_WINGS", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 124
        
        1300: ("Magearna", "ORIGINAL", FormCategory.COSMETIC),  # MISC_FORM_START + 125
        
        1301: ("Cramorant", "GULPING", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 128
        1302: ("Cramorant", "GORGING", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 129
        
        1305: ("Toxtricity", "LOW_KEY", FormCategory.DISCRETE),  # MISC_FORM_START + 130
        
        1306: ("Sinistea", "ANTIQUE", FormCategory.COSMETIC),  # MISC_FORM_START + 131
        1307: ("Poltegeist", "ANTIQUE", FormCategory.COSMETIC),  # MISC_FORM_START + 132
        
        # Alcremie sweets (MISC_FORM_START + 133 to 138)
        1308: ("Alcremie", "BERRY_SWEET", FormCategory.COSMETIC),
        1309: ("Alcremie", "LOVE_SWEET", FormCategory.COSMETIC),
        1310: ("Alcremie", "STAR_SWEET", FormCategory.COSMETIC),
        1311: ("Alcremie", "CLOVER_SWEET", FormCategory.COSMETIC),
        1312: ("Alcremie", "FLOWER_SWEET", FormCategory.COSMETIC),
        1313: ("Alcremie", "RIBBON_SWEET", FormCategory.COSMETIC),
        
        1321: ("Urshifu", "RAPID_STRIKE", FormCategory.DISCRETE),  # MISC_FORM_START + 146
        1322: ("Zarude", "DADA", FormCategory.COSMETIC),  # MISC_FORM_START + 147
        
        
        # Additional battle-only forms
        1316: ("Eiscue", "NOICE_FACE", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 141
        1317: ("Morpeko", "HANGRY", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 142
        1318: ("Zacian", "CROWNED", FormCategory.HELD_ITEM),  # MISC_FORM_START + 143
        1319: ("Zamazenta", "CROWNED", FormCategory.HELD_ITEM),  # MISC_FORM_START + 144
        1320: ("Eternatus", "ETERNAMAX", FormCategory.BATTLE_ONLY),  # MISC_FORM_START + 145
        
        # Note: Pumpkaboo and Gourgeist forms moved to avoid conflicts with gender dimorphism forms
        
        # Note: Floette Eternal Flower and Basculin White Striped already added above
        
        # TODO: Add other form categories below
        # Examples for cosmetic forms:
        # form_id: ("Unown", "B", FormCategory.COSMETIC),
        # form_id: ("Vivillon", "POLAR", FormCategory.COSMETIC),
        
        # Mega Evolution forms (SPECIES_MEGA_START = 1076)
        1076: ("Venusaur", "MEGA", FormCategory.BATTLE_ONLY),
        1077: ("Charizard", "MEGA_X", FormCategory.BATTLE_ONLY),
        1078: ("Charizard", "MEGA_Y", FormCategory.BATTLE_ONLY),
        1079: ("Blastoise", "MEGA", FormCategory.BATTLE_ONLY),
        1080: ("Beedrill", "MEGA", FormCategory.BATTLE_ONLY),
        1081: ("Pidgeot", "MEGA", FormCategory.BATTLE_ONLY),
        1082: ("Alakazam", "MEGA", FormCategory.BATTLE_ONLY),
        1083: ("Slowbro", "MEGA", FormCategory.BATTLE_ONLY),
        1084: ("Gengar", "MEGA", FormCategory.BATTLE_ONLY),
        1085: ("Kangaskhan", "MEGA", FormCategory.BATTLE_ONLY),
        1086: ("Pinsir", "MEGA", FormCategory.BATTLE_ONLY),
        1087: ("Gyarados", "MEGA", FormCategory.BATTLE_ONLY),
        1088: ("Aerodactyl", "MEGA", FormCategory.BATTLE_ONLY),
        1089: ("Mewtwo", "MEGA_X", FormCategory.BATTLE_ONLY),
        1090: ("Mewtwo", "MEGA_Y", FormCategory.BATTLE_ONLY),
        1091: ("Ampharos", "MEGA", FormCategory.BATTLE_ONLY),
        1092: ("Steelix", "MEGA", FormCategory.BATTLE_ONLY),
        1093: ("Scizor", "MEGA", FormCategory.BATTLE_ONLY),
        1094: ("Heracross", "MEGA", FormCategory.BATTLE_ONLY),
        1095: ("Houndoom", "MEGA", FormCategory.BATTLE_ONLY),
        1096: ("Tyranitar", "MEGA", FormCategory.BATTLE_ONLY),
        1097: ("Sceptile", "MEGA", FormCategory.BATTLE_ONLY),
        1098: ("Blaziken", "MEGA", FormCategory.BATTLE_ONLY),
        1099: ("Swampert", "MEGA", FormCategory.BATTLE_ONLY),
        1100: ("Gardevoir", "MEGA", FormCategory.BATTLE_ONLY),
        1101: ("Sableye", "MEGA", FormCategory.BATTLE_ONLY),
        1102: ("Mawile", "MEGA", FormCategory.BATTLE_ONLY),
        1103: ("Aggron", "MEGA", FormCategory.BATTLE_ONLY),
        1104: ("Medicham", "MEGA", FormCategory.BATTLE_ONLY),
        1105: ("Manectric", "MEGA", FormCategory.BATTLE_ONLY),
        1106: ("Sharpedo", "MEGA", FormCategory.BATTLE_ONLY),
        1107: ("Camerupt", "MEGA", FormCategory.BATTLE_ONLY),
        1108: ("Altaria", "MEGA", FormCategory.BATTLE_ONLY),
        1109: ("Banette", "MEGA", FormCategory.BATTLE_ONLY),
        1110: ("Absol", "MEGA", FormCategory.BATTLE_ONLY),
        1111: ("Glalie", "MEGA", FormCategory.BATTLE_ONLY),
        1112: ("Salamence", "MEGA", FormCategory.BATTLE_ONLY),
        1113: ("Metagross", "MEGA", FormCategory.BATTLE_ONLY),
        1114: ("Latias", "MEGA", FormCategory.BATTLE_ONLY),
        1115: ("Latios", "MEGA", FormCategory.BATTLE_ONLY),
        1116: ("Rayquaza", "MEGA", FormCategory.BATTLE_ONLY),
        1117: ("Lopunny", "MEGA", FormCategory.BATTLE_ONLY),
        1118: ("Garchomp", "MEGA", FormCategory.BATTLE_ONLY),
        1119: ("Lucario", "MEGA", FormCategory.BATTLE_ONLY),
        1120: ("Abomasnow", "MEGA", FormCategory.BATTLE_ONLY),
        1121: ("Gallade", "MEGA", FormCategory.BATTLE_ONLY),
        1122: ("Audino", "MEGA", FormCategory.BATTLE_ONLY),
        1123: ("Diancie", "MEGA", FormCategory.BATTLE_ONLY),
        
        # Primal forms (SPECIES_PRIMAL_START = 1124)
        1124: ("Kyogre", "PRIMAL", FormCategory.BATTLE_ONLY),
        1125: ("Groudon", "PRIMAL", FormCategory.BATTLE_ONLY),
        
        # Examples for out-of-battle change forms:
        # form_id: ("Deoxys", "ATTACK", FormCategory.OUT_OF_BATTLE_CHANGE),
        # form_id: ("Rotom", "HEAT", FormCategory.OUT_OF_BATTLE_CHANGE),
        
        # Examples for held item forms:
        # form_id: ("Arceus", "FIGHTING", FormCategory.HELD_ITEM),
        
        # Gender dimorphism forms (SPECIES_SIGNIFICANT_GENDER_DIFFERENCE_START = 1347)
        1347: ("Unfezant", "FEMALE", FormCategory.GENDER_DIMORPHISM),  # SPECIES_UNFEZANT_FEMALE
        1348: ("Frillish", "FEMALE", FormCategory.GENDER_DIMORPHISM),  # SPECIES_FRILLISH_FEMALE
        1349: ("Jellicent", "FEMALE", FormCategory.GENDER_DIMORPHISM),  # SPECIES_JELLICENT_FEMALE
        1350: ("Pyroar", "FEMALE", FormCategory.GENDER_DIMORPHISM),  # SPECIES_PYROAR_FEMALE
        1351: ("Meowstic", "FEMALE", FormCategory.GENDER_DIMORPHISM),  # SPECIES_MEOWSTIC_FEMALE
        1352: ("Indeedee", "FEMALE", FormCategory.GENDER_DIMORPHISM),  # SPECIES_INDEEDEE_FEMALE
        1353: ("Basclegion", "FEMALE", FormCategory.GENDER_DIMORPHISM),  # SPECIES_BASCULEGION_FEMALE
        1367: ("Oinkologne", "FEMALE", FormCategory.GENDER_DIMORPHISM),  # SPECIES_OINKOLOGNE_FEMALE
        
        # Pumpkaboo and Gourgeist size forms (moved here to avoid conflicts)
        1400: ("Pumpkaboo", "SMALL", FormCategory.DISCRETE),
        1401: ("Pumpkaboo", "LARGE", FormCategory.DISCRETE),
        1402: ("Pumpkaboo", "SUPER", FormCategory.DISCRETE),
        1403: ("Gourgeist", "SMALL", FormCategory.DISCRETE),
        1404: ("Gourgeist", "LARGE", FormCategory.DISCRETE),
        1405: ("Gourgeist", "SUPER", FormCategory.DISCRETE),
        
        # Invalid forms - forms that exist in species constants but are not properly categorized
        # Large Alolan forms (SPECIES_ALOLAN_REGIONAL_START + 18 to 29)
        1144: ("Raticate", "ALOLAN_LARGE", FormCategory.INVALID),  # SPECIES_RATICATE_ALOLAN_LARGE
        1145: ("Marowak", "ALOLAN_LARGE", FormCategory.INVALID),  # SPECIES_MAROWAK_ALOLAN_LARGE
        1146: ("Gumshoos", "LARGE", FormCategory.INVALID),  # SPECIES_GUMSHOOS_LARGE
        1147: ("Vikavolt", "LARGE", FormCategory.INVALID),  # SPECIES_VIKAVOLT_LARGE
        1148: ("Ribombee", "LARGE", FormCategory.INVALID),  # SPECIES_RIBOMBEE_LARGE
        1149: ("Araquanid", "LARGE", FormCategory.INVALID),  # SPECIES_ARAQUANID_LARGE
        1150: ("Lurantis", "LARGE", FormCategory.INVALID),  # SPECIES_LURANTIS_LARGE
        1151: ("Salazzle", "LARGE", FormCategory.INVALID),  # SPECIES_SALAZZLE_LARGE
        1152: ("Togedemaru", "LARGE", FormCategory.INVALID),  # SPECIES_TOGEDEMARU_LARGE
        1153: ("Mimikyu", "LARGE", FormCategory.INVALID),  # SPECIES_MIMIKYU_LARGE
        1154: ("Mimikyu", "BUSTED_LARGE", FormCategory.INVALID),  # SPECIES_MIMIKYU_BUSTED_LARGE
        1155: ("Kommo-o", "LARGE", FormCategory.INVALID),  # SPECIES_KOMMO_O_LARGE
        
        # Partner Pikachu and Eevee (SPECIES_MISC_FORM_START + 126, 127)
        1301: ("Pikachu", "PARTNER", FormCategory.INVALID),  # SPECIES_PIKACHU_PARTNER
        1302: ("Eevee", "PARTNER", FormCategory.INVALID),  # SPECIES_EEVEE_PARTNER
        
        # Hisuian noble forms (SPECIES_HISUIAN_REGIONAL_START + 16 to 20)
        1342: ("Kleavor", "LORD", FormCategory.INVALID),  # SPECIES_KLEAVOR_LORD
        1343: ("Lilligant", "LADY", FormCategory.INVALID),  # SPECIES_LILLIGANT_LADY
        1344: ("Arcanine", "LORD", FormCategory.INVALID),  # SPECIES_ARCANINE_LORD
        1345: ("Electrode", "LORD", FormCategory.INVALID),  # SPECIES_ELECTRODE_LORD
        1346: ("Avalugg", "LORD", FormCategory.INVALID),  # SPECIES_AVALUGG_LORD
        
        # Revavroom forms and legendary forms (PALDEAN_FORMS_START + 14 to 26)
        1368: ("Revavroom", "SEGIN", FormCategory.INVALID),  # SPECIES_REVAVROOM_SEGIN
        1369: ("Revavroom", "SCHEDAR", FormCategory.INVALID),  # SPECIES_REVAVROOM_SCHEDAR
        1370: ("Revavroom", "NAVI", FormCategory.INVALID),  # SPECIES_REVAVROOM_NAVI
        1371: ("Revavroom", "RUCHBAH", FormCategory.INVALID),  # SPECIES_REVAVROOM_RUCHBAH
        1372: ("Revavroom", "CAPH", FormCategory.INVALID),  # SPECIES_REVAVROOM_CAPH
        1373: ("Koraidon", "LIMITED_BUILD", FormCategory.INVALID),  # SPECIES_KORAIDON_LIMITED_BUILD
        1374: ("Koraidon", "SPRINTING_BUILD", FormCategory.INVALID),  # SPECIES_KORAIDON_SPRINTING_BUILD
        1375: ("Koraidon", "SWIMMING_BUILD", FormCategory.INVALID),  # SPECIES_KORAIDON_SWIMMING_BUILD
        1376: ("Koraidon", "GLIDING_BUILD", FormCategory.INVALID),  # SPECIES_KORAIDON_GLIDING_BUILD
        1377: ("Miraidon", "LOW_POWER_MODE", FormCategory.INVALID),  # SPECIES_MIRAIDON_LOW_POWER_MODE
        1378: ("Miraidon", "DRIVE_MODE", FormCategory.INVALID),  # SPECIES_MIRAIDON_DRIVE_MODE
        1379: ("Miraidon", "AQUATIC_MODE", FormCategory.INVALID),  # SPECIES_MIRAIDON_AQUATIC_MODE
        1380: ("Miraidon", "GLIDE_MODE", FormCategory.INVALID),  # SPECIES_MIRAIDON_GLIDE_MODE
        
        # Additional Paldean forms that are invalid
        1383: ("Ogerpon", "WELLSPRING_MASK", FormCategory.INVALID),  # SPECIES_OGERPON_WELLSPRING_MASK
        1384: ("Ogerpon", "HEARTHFLAME_MASK", FormCategory.INVALID),  # SPECIES_OGERPON_HEARTHFLAME_MASK
        1385: ("Ogerpon", "CORNERSTONE_MASK", FormCategory.INVALID),  # SPECIES_OGERPON_CORNERSTONE_MASK
    }
    
    def __init__(self, context):
        """Initialize the form mapper with Pokemon names from context."""
        super().__init__(context)
        self.pokemon_names_step = context.get(LoadPokemonNamesStep)
        self._form_to_base_cache = None
        self._base_to_forms_cache = None
        
    def _build_form_lookup(self) -> Dict[int, Tuple[int, int]]:
        """
        Build the mondata_index -> (base_species_id, form_number) lookup table.
        
        This method processes all form categories and creates a unified lookup
        that maps form IDs to their base species and form number.
        
        Returns:
            Dict mapping form_id -> (base_species_id, form_number)
        """
        if self._form_to_base_cache is not None:
            return self._form_to_base_cache
            
        form_lookup = {}
        
        # Process all forms from the unified dictionary
        base_species_cache = {}  # Cache for base species lookups
        form_counters = {}  # Track form numbers per base species
        
        for form_id, (base_name, form_name, form_category) in self.ALL_FORMS.items():
            # Look up base species ID by name (with caching)
            if base_name not in base_species_cache:
                base_species_ids = self.pokemon_names_step.get_all_by_name(base_name)
                if not base_species_ids:
                    raise ValueError(f"Base species '{base_name}' not found in Pokemon names")
                if len(base_species_ids) > 1:
                    raise ValueError(f"Multiple Pokemon found with name '{base_name}': {base_species_ids}")
                base_species_cache[base_name] = base_species_ids[0]
            
            base_species_id = base_species_cache[base_name]
            
            # Assign form numbers sequentially per base species
            if base_species_id not in form_counters:
                form_counters[base_species_id] = 0
            form_counters[base_species_id] += 1
            form_number = form_counters[base_species_id]
            
            form_lookup[form_id] = (base_species_id, form_number)
        
        self._form_to_base_cache = form_lookup
        return form_lookup
    
    def _build_base_to_forms_lookup(self) -> Dict[int, List[int]]:
        """
        Build the base_species_id -> [form_ids] lookup table.
        
        Returns:
            Dict mapping base_species_id -> list of form_ids
        """
        if self._base_to_forms_cache is not None:
            return self._base_to_forms_cache
            
        form_lookup = self._build_form_lookup()
        base_to_forms = {}
        
        for form_id, (base_species_id, form_number) in form_lookup.items():
            if base_species_id not in base_to_forms:
                base_to_forms[base_species_id] = []
            base_to_forms[base_species_id].append(form_id)
        
        # Sort form lists for consistent ordering
        for form_list in base_to_forms.values():
            form_list.sort()
            
        self._base_to_forms_cache = base_to_forms
        return base_to_forms
    
    def is_form(self, pokemon_id: int) -> bool:
        """
        Check if a Pokemon ID represents a form (exists in our form mapping).
        
        Args:
            pokemon_id: The Pokemon species ID to check
            
        Returns:
            True if this Pokemon is a form, False otherwise
        """
        return pokemon_id in self.ALL_FORMS
    
    def get_base_species(self, pokemon_id: int) -> int:
        """
        Get the base species ID for any Pokemon (form or base).
        
        Args:
            pokemon_id: The Pokemon species ID (form or base)
            
        Returns:
            The base species ID
        """
        form_lookup = self._build_form_lookup()
        
        if pokemon_id in form_lookup:
            return form_lookup[pokemon_id][0]
        else:
            # Not a form, return the ID itself
            return pokemon_id
    
    def get_form_number(self, pokemon_id: int) -> int:
        """
        Get the form number for a Pokemon.
        
        Args:
            pokemon_id: The Pokemon species ID
            
        Returns:
            0 for base forms, 1+ for alternate forms
        """
        form_lookup = self._build_form_lookup()
        
        if pokemon_id in form_lookup:
            return form_lookup[pokemon_id][1]
        else:
            return 0  # Base form
    
    def get_form_name(self, pokemon_id: int) -> str:
        """
        Get the form name for a Pokemon.
        
        Args:
            pokemon_id: The Pokemon species ID
            
        Returns:
            "Base" for base forms, or the specific form name
        """
        if not self.is_form(pokemon_id):
            return "Base"
            
        if pokemon_id in self.ALL_FORMS:
            return self.ALL_FORMS[pokemon_id][1]  # form_name
        else:
            return f"Form_{self.get_form_number(pokemon_id)}"
    
    def get_form_info(self, pokemon_id: int) -> Dict:
        """
        Get complete form information for a Pokemon.
        
        Args:
            pokemon_id: The Pokemon species ID
            
        Returns:
            Dictionary with form information
        """
        base_species = self.get_base_species(pokemon_id)
        form_number = self.get_form_number(pokemon_id)
        form_name = self.get_form_name(pokemon_id)
        is_form = self.is_form(pokemon_id)
        form_category = None
        
        if pokemon_id in self.ALL_FORMS:
            form_category = self.ALL_FORMS[pokemon_id][2]  # FormCategory
        
        return {
            "pokemon_id": pokemon_id,
            "base_species_id": base_species,
            "form_number": form_number,
            "form_name": form_name,
            "form_category": form_category,
            "is_form": is_form,
            "base_name": self.pokemon_names_step.get_by_id(base_species)
        }
    
    def get_all_forms(self, base_species_id: int) -> List[int]:
        """
        Get all form IDs for a base species.
        
        Args:
            base_species_id: The base Pokemon species ID
            
        Returns:
            List of all form IDs for this base species (not including base)
        """
        base_to_forms = self._build_base_to_forms_lookup()
        return base_to_forms.get(base_species_id, [])
    
    def get_all_variants(self, base_species_id: int) -> List[int]:
        """
        Get all variants (base + forms) for a base species.
        
        Args:
            base_species_id: The base Pokemon species ID
            
        Returns:
            List of all IDs (base + forms) for this species
        """
        variants = [base_species_id]
        variants.extend(self.get_all_forms(base_species_id))
        return variants
    
    def get_forms_by_category(self, category) -> List[Tuple[int, str, str]]:
        """
        Get all forms that belong to a specific category.
        
        Args:
            category: FormCategory enum value
            
        Returns:
            List of (pokemon_id, base_name, form_name) tuples
        """
        forms = []
        for pokemon_id, (base_name, form_name, form_category) in self.ALL_FORMS.items():
            if form_category == category:
                forms.append((pokemon_id, base_name, form_name))
        return forms
    
    def get_form_category(self, pokemon_id: int):
        """
        Get the form category for a Pokemon.
        
        Args:
            pokemon_id: The Pokemon species ID
            
        Returns:
            FormCategory enum value or None if not a form
        """
        if pokemon_id in self.ALL_FORMS:
            return self.ALL_FORMS[pokemon_id][2]  # FormCategory
        return None
