import enum

class Type(enum.IntEnum):
    NORMAL = 0
    FIGHTING = 1
    FLYING = 2
    POISON = 3
    GROUND = 4
    ROCK = 5
    BUG = 6
    GHOST = 7
    STEEL = 8
    FAIRY = 9
    FIRE = 10
    WATER = 11
    GRASS = 12
    ELECTRIC = 13
    PSYCHIC = 14
    ICE = 15
    DRAGON = 16
    DARK = 17

class Split(enum.IntEnum):
    PHYSICAL = 0
    SPECIAL = 1
    STATUS = 2

class Contest(enum.IntEnum):
    COOL = 0
    BEAUTY = 1
    CUTE = 2
    SMART = 3
    TOUGH = 4

class MoveFlags(enum.IntFlag):
    CONTACT = 0x01
    PROTECT = 0x02
    MAGIC_COAT = 0x04
    SNATCH = 0x08
    MIRROR_MOVE = 0x10
    KINGS_ROCK = 0x20
    KEEP_HP_BAR = 0x40
    HIDE_SHADOW = 0x80

class Target(enum.IntEnum):
    SINGLE_TARGET = 0
    SINGLE_TARGET_SPECIAL = 1
    RANDOM_OPPONENT = 2
    ADJACENT_OPPONENTS = 4
    ALL_ADJACENT = 8
    USER = 16
    USER_SIDE = 32
    FIELD = 64
    OPPONENT_SIDE = 128
    ALLY = 256
    SINGLE_TARGET_USER_SIDE = 512
    FRONT = 1024


class EvoParam(enum.Enum):
    """Enum to encode the meaning of evolution method parameters."""
    LEVEL = "level"      # Parameter represents a level requirement
    ITEM = "item"
    OTHER = "other"      # Parameter represents something else (item, move, etc.)


class EvolutionMethod(enum.IntEnum):
    """Evolution method constants from constants.s with parameter type information."""
    
    def __new__(cls, value, param_type=EvoParam.OTHER):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.param_type = param_type
        return obj
    
    # Evolution methods with their parameter types
    NONE = 0, EvoParam.OTHER
    FRIENDSHIP = 1, EvoParam.OTHER
    FRIENDSHIP_DAY = 2, EvoParam.OTHER
    FRIENDSHIP_NIGHT = 3, EvoParam.OTHER
    LEVEL = 4, EvoParam.LEVEL
    TRADE = 5, EvoParam.OTHER
    TRADE_ITEM = 6, EvoParam.OTHER
    STONE = 7, EvoParam.ITEM
    LEVEL_ATK_GT_DEF = 8, EvoParam.LEVEL
    LEVEL_ATK_EQ_DEF = 9, EvoParam.LEVEL
    LEVEL_ATK_LT_DEF = 10, EvoParam.LEVEL
    LEVEL_PID_LO = 11, EvoParam.LEVEL
    LEVEL_PID_HI = 12, EvoParam.LEVEL
    LEVEL_NINJASK = 13, EvoParam.LEVEL
    LEVEL_SHEDINJA = 14, EvoParam.LEVEL
    BEAUTY = 15, EvoParam.OTHER
    STONE_MALE = 16, EvoParam.ITEM
    STONE_FEMALE = 17, EvoParam.ITEM
    ITEM_DAY = 18, EvoParam.ITEM
    ITEM_NIGHT = 19, EvoParam.ITEM
    HAS_MOVE = 20, EvoParam.OTHER
    OTHER_PARTY_MON = 21, EvoParam.OTHER
    LEVEL_MALE = 22, EvoParam.LEVEL
    LEVEL_FEMALE = 23, EvoParam.LEVEL
    LEVEL_ELECTRIC_FIELD = 24, EvoParam.LEVEL
    LEVEL_MOSSY_STONE = 25, EvoParam.LEVEL
    LEVEL_ICY_STONE = 26, EvoParam.LEVEL
    LEVEL_DAY = 27, EvoParam.LEVEL
    LEVEL_NIGHT = 28, EvoParam.LEVEL
    LEVEL_DUSK = 29, EvoParam.LEVEL
    LEVEL_RAIN = 30, EvoParam.LEVEL
    HAS_MOVE_TYPE = 31, EvoParam.OTHER
    LEVEL_DARK_TYPE_MON_IN_PARTY = 32, EvoParam.LEVEL
    TRADE_SPECIFIC_MON = 33, EvoParam.OTHER
    LEVEL_NATURE_AMPED = 34, EvoParam.LEVEL
    LEVEL_NATURE_LOW_KEY = 35, EvoParam.LEVEL
    AMOUNT_OF_CRITICAL_HITS = 36, EvoParam.OTHER
    HURT_IN_BATTLE_AMOUNT = 37, EvoParam.OTHER

class Nature(enum.IntEnum):
    NATURE_HARDY = 0
    NATURE_LONELY = 1
    NATURE_BRAVE = 2
    NATURE_ADAMANT = 3
    NATURE_NAUGHTY = 4
    NATURE_BOLD = 5
    NATURE_DOCILE = 6
    NATURE_RELAXED = 7
    NATURE_IMPISH = 8
    NATURE_LAX = 9
    NATURE_TIMID = 10
    NATURE_HASTY = 11
    NATURE_SERIOUS = 12
    NATURE_JOLLY = 13
    NATURE_NAIVE = 14
    NATURE_MODEST = 15
    NATURE_MILD = 16
    NATURE_QUIET = 17
    NATURE_BASHFUL = 18
    NATURE_RASH = 19
    NATURE_CALM = 20
    NATURE_GENTLE = 21
    NATURE_SASSY = 22
    NATURE_CAREFUL = 23
    NATURE_QUIRKY = 24
 
class Stat(enum.IntEnum):
    """Pokemon battle stats that can be modified by natures."""
    HP = 0
    ATTACK = 1
    DEFENSE = 2
    SP_ATTACK = 3
    SP_DEFENSE = 4
    SPEED = 5


class NatureData(enum.IntEnum):
    """Nature stat modifications.
    
    Each nature has:
    - raised_stat: Which stat gets +10% (None for neutral natures)
    - lowered_stat: Which stat gets -10% (None for neutral natures)
    """
    
    def __new__(cls, value, raised_stat=None, lowered_stat=None):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.raised_stat = raised_stat
        obj.lowered_stat = lowered_stat
        return obj
    
    # Neutral natures (no stat changes)
    HARDY = 0, None, None
    DOCILE = 6, None, None
    SERIOUS = 12, None, None
    BASHFUL = 18, None, None
    QUIRKY = 24, None, None
    
    LONELY = 1, Stat.ATTACK, Stat.DEFENSE
    BRAVE = 2, Stat.ATTACK, Stat.SPEED
    ADAMANT = 3, Stat.ATTACK, Stat.SP_ATTACK
    NAUGHTY = 4, Stat.ATTACK, Stat.SP_DEFENSE
    
    BOLD = 5, Stat.DEFENSE, Stat.ATTACK
    RELAXED = 7, Stat.DEFENSE, Stat.SPEED
    IMPISH = 8, Stat.DEFENSE, Stat.SP_ATTACK
    LAX = 9, Stat.DEFENSE, Stat.SP_DEFENSE
    
    TIMID = 10, Stat.SPEED, Stat.ATTACK
    HASTY = 11, Stat.SPEED, Stat.DEFENSE
    JOLLY = 13, Stat.SPEED, Stat.SP_ATTACK
    NAIVE = 14, Stat.SPEED, Stat.SP_DEFENSE
    
    MODEST = 15, Stat.SP_ATTACK, Stat.ATTACK
    MILD = 16, Stat.SP_ATTACK, Stat.DEFENSE
    QUIET = 17, Stat.SP_ATTACK, Stat.SPEED
    RASH = 19, Stat.SP_ATTACK, Stat.SP_DEFENSE
    
    CALM = 20, Stat.SP_DEFENSE, Stat.ATTACK
    GENTLE = 21, Stat.SP_DEFENSE, Stat.DEFENSE
    SASSY = 22, Stat.SP_DEFENSE, Stat.SPEED
    CAREFUL = 23, Stat.SP_DEFENSE, Stat.SP_ATTACK
    
    @classmethod
    def get_helpful_natures(cls, mon_classes):
        """Get helpful natures based on MonClass flags.
        
        Args:
            mon_classes: Set of MonClass values
            
        Returns:
            list: List of helpful NatureData values
        """
        helpful = []
        
        if MonClass.DEFENSIVE in mon_classes:
            # Helpful: Increases Def or Sp Def, doesn't decrease Def or Sp Def
            # Doesn't reduce Speed if Fast
            for nature in cls:
                if nature.raised_stat in [Stat.DEFENSE, Stat.SP_DEFENSE]:
                    if nature.lowered_stat not in [Stat.DEFENSE, Stat.SP_DEFENSE]:
                        if not (MonClass.FAST in mon_classes and nature.lowered_stat == Stat.SPEED):
                            helpful.append(nature)
        
        if MonClass.OFFENSIVE in mon_classes:
            helpful.extend(cls._get_offensive_helpful_natures(mon_classes))
        
        if MonClass.BALANCED in mon_classes:
            # Helpful: Reduces opposite attacking stat
            for nature in cls:
                if MonClass.SPECIAL_ATTACKER in mon_classes and nature.lowered_stat == Stat.ATTACK:
                    helpful.append(nature)
                elif MonClass.PHYSICAL_ATTACKER in mon_classes and nature.lowered_stat == Stat.SP_ATTACK:
                    helpful.append(nature)
        
        return list(set(helpful))  # Remove duplicates
    
    @classmethod
    def get_harmful_natures(cls, mon_classes):
        """Get harmful natures based on MonClass flags.
        
        Args:
            mon_classes: Set of MonClass values
            
        Returns:
            list: List of harmful NatureData values
        """
        harmful = []
        
        # Harmful natures reduce key stats
        for nature in cls:
            if nature.lowered_stat is None:  # Skip neutral natures
                continue
                
            # Harmful if reduces defensive stats for defensive Pokemon
            if MonClass.DEFENSIVE in mon_classes:
                if nature.lowered_stat in [Stat.DEFENSE, Stat.SP_DEFENSE, Stat.HP]:
                    harmful.append(nature)
            
            # Harmful if reduces offensive stats for offensive Pokemon
            if MonClass.OFFENSIVE in mon_classes:
                if MonClass.PHYSICAL_ATTACKER in mon_classes and nature.lowered_stat == Stat.ATTACK:
                    harmful.append(nature)
                elif MonClass.SPECIAL_ATTACKER in mon_classes and nature.lowered_stat == Stat.SP_ATTACK:
                    harmful.append(nature)
                elif MonClass.FAST in mon_classes and nature.lowered_stat == Stat.SPEED:
                    harmful.append(nature)
        
        return list(set(harmful))  # Remove duplicates
    
    @classmethod
    def _get_offensive_helpful_natures(cls, mon_classes):
        """Get helpful natures for offensive Pokemon."""
        helpful = []
        
        for nature in cls:
            if MonClass.PHYSICAL_ATTACKER in mon_classes and MonClass.SPECIAL_ATTACKER not in mon_classes:
                # Pure physical attacker
                if MonClass.FAST in mon_classes or MonClass.MIDSPEED in mon_classes:
                    # Increases Attack or Speed, doesn't reduce Attack or Speed
                    if nature.raised_stat in [Stat.ATTACK, Stat.SPEED]:
                        if nature.lowered_stat not in [Stat.ATTACK, Stat.SPEED]:
                            helpful.append(nature)
                elif MonClass.SLOW in mon_classes:
                    # Increases Attack
                    if nature.raised_stat == Stat.ATTACK:
                        helpful.append(nature)
            
            elif MonClass.SPECIAL_ATTACKER in mon_classes and MonClass.PHYSICAL_ATTACKER not in mon_classes:
                # Pure special attacker
                if MonClass.FAST in mon_classes or MonClass.MIDSPEED in mon_classes:
                    # Increases Sp Attack or Speed, doesn't reduce Sp Attack or Speed
                    if nature.raised_stat in [Stat.SP_ATTACK, Stat.SPEED]:
                        if nature.lowered_stat not in [Stat.SP_ATTACK, Stat.SPEED]:
                            helpful.append(nature)
                elif MonClass.SLOW in mon_classes:
                    # Increases Sp Attack, Def, or Sp Def but doesn't reduce Sp Attack
                    if nature.raised_stat in [Stat.SP_ATTACK, Stat.DEFENSE, Stat.SP_DEFENSE]:
                        if nature.lowered_stat != Stat.SP_ATTACK:
                            helpful.append(nature)
            
            elif MonClass.PHYSICAL_ATTACKER in mon_classes and MonClass.SPECIAL_ATTACKER in mon_classes:
                # Mixed attacker
                if MonClass.FAST in mon_classes:
                    # Increases Attack, Sp Attack, or Speed and reduces Def or Sp Def
                    if nature.raised_stat in [Stat.ATTACK, Stat.SP_ATTACK, Stat.SPEED]:
                        if nature.lowered_stat in [Stat.DEFENSE, Stat.SP_DEFENSE]:
                            helpful.append(nature)
                else:  # MIDSPEED or SLOW
                    # Increases Attack or Sp Attack, doesn't reduce either
                    if nature.raised_stat in [Stat.ATTACK, Stat.SP_ATTACK]:
                        if nature.lowered_stat not in [Stat.ATTACK, Stat.SP_ATTACK]:
                            helpful.append(nature)
        
        return helpful

class TrainerDataType(enum.IntFlag):
    NOTHING = 0x00
    MOVES = 0x01
    ITEMS = 0x02
    ABILITY = 0x04
    BALL = 0x08
    IV_EV_SET = 0x10
    NATURE_SET = 0x20
    SHINY_LOCK = 0x40
    ADDITIONAL_FLAGS = 0x80

class BattleType(enum.IntEnum):
    SINGLE_BATTLE = 0
    DOUBLE_BATTLE = 1
    TRIPLE_BATTLE = 2
    ROTATION_BATTLE = 3

class TrainerClass(enum.IntEnum):
    PKMN_TRAINER_ETHAN = 0
    PKMN_TRAINER_LYRA = 1
    YOUNGSTER = 2
    LASS = 3
    CAMPER = 4
    PICNICKER = 5
    BUG_CATCHER = 6
    AROMA_LADY = 7
    TWINS = 8
    HIKER = 9
    BATTLE_GIRL = 10
    FISHERMAN = 11
    CYCLIST_M = 12
    CYCLIST_F = 13
    BLACK_BELT = 14
    ARTIST = 15
    PKMN_BREEDER_M = 16
    PKMN_BREEDER_F = 17
    COWGIRL = 18
    JOGGER = 19
    POKEFAN_M = 20
    POKEFAN = 21
    POKE_KID = 22
    RIVAL = 23
    ACE_TRAINER_M = 24
    ACE_TRAINER_F = 25
    WAITRESS = 26
    VETERAN = 27
    NINJA_BOY = 28
    DRAGON_TAMER = 29
    BIRD_KEEPER = 30
    JUGGLER = 31
    RICH_BOY = 32
    LADY = 33
    GENTLEMAN = 34
    SOCIALITE = 35
    BEAUTY = 36
    COLLECTOR = 37
    POLICEMAN = 38
    PKMN_RANGER_M = 39
    PKMN_RANGER_F = 40
    SCIENTIST = 41
    SWIMMER_M = 42
    SWIMMER_F = 43
    TUBER_M = 44
    TUBER_F = 45
    SAILOR = 46
    KIMONO_GIRL = 47
    RUIN_MANIAC = 48
    PSYCHIC_M = 49
    PSYCHIC_F = 50
    PI = 51
    GUITARIST = 52
    ACE_TRAINER_M_GS = 53
    ACE_TRAINER_F_GS = 54
    TEAM_ROCKET = 55
    SKIER = 56
    ROUGHNECK = 57
    CLOWN = 58
    WORKER = 59
    SCHOOL_KID_M = 60
    SCHOOL_KID_F = 61
    TEAM_ROCKET_F = 62
    BURGLAR = 63
    FIREBREATHER = 64
    BIKER = 65
    LEADER_FALKNER = 66
    LEADER_BUGSY = 67
    POKE_MANIAC = 68
    BIRD_KEEPER_GS = 69
    LEADER_WHITNEY = 70
    RANCHER = 71
    LEADER_MORTY = 72
    LEADER_PRYCE = 73
    LEADER_JASMINE = 74
    LEADER_CHUCK = 75
    LEADER_CLAIR = 76
    TEACHER = 77
    SUPER_NERD = 78
    SAGE = 79
    PARASOL_LADY = 80
    WAITER = 81
    MEDIUM = 82
    CAMERAMAN = 83
    REPORTER = 84
    IDOL = 85
    CHAMPION = 86
    ELITE_FOUR_WILL = 87
    ELITE_FOUR_KAREN = 88
    ELITE_FOUR_KOGA = 89
    PKMN_TRAINER_CHERYL = 90
    PKMN_TRAINER_RILEY = 91
    PKMN_TRAINER_BUCK = 92
    PKMN_TRAINER_MIRA = 93
    PKMN_TRAINER_MARLEY = 94
    PKMN_TRAINER_FTR_LUCAS = 95
    PKMN_TRAINER_FTR_DAWN = 96
    TOWER_TYCOON = 97
    LEADER_BROCK = 98
    HALL_MATRON = 99
    FACTORY_HEAD = 100
    ARCADE_STAR = 101
    CASTLE_VALET = 102
    LEADER_MISTY = 103
    LEADER_LT_SURGE = 104
    LEADER_ERIKA = 105
    LEADER_JANINE = 106
    LEADER_SABRINA = 107
    LEADER_BLAINE = 108
    PKMN_TRAINER_RED = 109
    LEADER_BLUE = 110
    ELDER = 111
    ELITE_FOUR_BRUNO = 112
    SCIENTIST_GS = 113
    EXECUTIVE_ARIANA = 114
    BOARDER = 115
    EXECUTIVE_ARCHER = 116
    EXECUTIVE_PROTON = 117
    EXECUTIVE_PETREL = 118
    PASSERBY = 119
    MYSTERY_MAN = 120
    DOUBLE_TEAM = 121
    YOUNG_COUPLE = 122
    PKMN_TRAINER_LANCE = 123
    ROCKET_BOSS = 124
    PKMN_TRAINER_LUCAS_DP = 125
    PKMN_TRAINER_DAWN_DP = 126
    PKMN_TRAINER_LUCAS_PT = 127
    PKMN_TRAINER_DAWN_PT = 128

class Tier(enum.IntEnum):
    """Game progression tiers for trainer difficulty scaling."""
    EARLY_GAME = 1
    MID_GAME = 2
    LATE_GAME = 3
    END_GAME = 4

class MonClass(enum.IntEnum):
    """Pokemon classification flags for categorizing Pokemon by their battle roles and stats."""
    # Stat-based classifications
    OFFENSIVE = 1        # highest Offensive stat > 104
    DEFENSIVE = 2        # lowest Defensive stat > 95 or HP > 120
    PHYSICAL_ATTACKER = 3 # Atk > 105
    SPECIAL_ATTACKER = 4  # Sp Atk > 105
    FRAIL = 5            # highest Defensive stat < 86 and HP < 86 OR has a 4x weakness
    BALANCED = 6         # highest offensive stat and lowest defensive stat within 20%
    
    # Speed classifications
    FAST = 7             # Base Speed >= 100
    MIDSPEED = 8         # Base Speed 65-99
    SLOW = 9             # Base Speed < 65

class EggGroup(enum.IntEnum):
    """Egg group constants for categorizing Pokemon by their egg groups."""
    NONE = 0
    MONSTER = 1
    WATER_1 = 2
    BUG = 3
    FLYING = 4
    FIELD = 5
    FAIRY = 6
    GRASS = 7
    HUMAN_LIKE = 8
    WATER_3 = 9
    MINERAL = 10
    AMORPHOUS = 11
    WATER_2 = 12
    DITTO = 13
    DRAGON = 14
    UNDISCOVERED = 15

class ItemParam(enum.Enum):
    """Item parameter categories for classifying items by their usage and function."""
    HELD = "HELD"      # Items that can be held by Pokémon for battle effects
    MED = "MED"        # Medicine/healing items (Potions, Berries for healing, etc.)
    EVO = "EVO"        # Evolution items (Evolution stones, trade items, etc.)
    OBO = "OBO"        # Out of battle only items (Repel, Escape Rope, etc.)
    BAT = "BAT"        # In battle only items (X Items, Flutes, etc.)
    VAL = "VAL"        # Valuable items and items given to NPCs (Heart Scale, Fossils, etc.)
    BALL = "BALL"      # Poké Balls and variants
    BER = "BER"        # Berries (for held items and other uses)
    TM = "TM"          # Technical Machines
    HM = "HM"          # Hidden Machines
    KEY = "KEY"        # Key items
    MEGA = "MEGA"      # Mega stones
    UNIMPL = "UNIMPL"  # Unimplemented items (DO NOT assign manually)
    EXTRA = "EXTRA"    # Extraneous items with no practical use (Mulches, Mail, Contest items, Power items, Apricorns, etc.)
    GEM = "GEM"        # Gems


class Item(enum.IntEnum):
    """Item constants from asm/include/items.inc for use in assigning held items to trainer Pokémon."""
    
    def __new__(cls, value, item_param=None):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.item_param = item_param
        return obj
    
    # Balls
    NONE = 0
    MASTER_BALL = 1, ItemParam.BALL
    ULTRA_BALL = 2, ItemParam.BALL
    GREAT_BALL = 3, ItemParam.BALL
    POKE_BALL = 4, ItemParam.BALL
    SAFARI_BALL = 5, ItemParam.BALL
    NET_BALL = 6, ItemParam.BALL
    DIVE_BALL = 7, ItemParam.BALL
    NEST_BALL = 8, ItemParam.BALL
    REPEAT_BALL = 9, ItemParam.BALL
    TIMER_BALL = 10, ItemParam.BALL
    LUXURY_BALL = 11, ItemParam.BALL
    PREMIER_BALL = 12, ItemParam.BALL
    DUSK_BALL = 13, ItemParam.BALL
    HEAL_BALL = 14, ItemParam.BALL
    QUICK_BALL = 15, ItemParam.BALL
    CHERISH_BALL = 16, ItemParam.BALL
    
    # Healing items
    POTION = 17, ItemParam.MED
    ANTIDOTE = 18, ItemParam.MED
    BURN_HEAL = 19, ItemParam.MED
    ICE_HEAL = 20, ItemParam.MED
    AWAKENING = 21, ItemParam.MED
    PARALYZE_HEAL = 22, ItemParam.MED
    FULL_RESTORE = 23, ItemParam.MED
    MAX_POTION = 24, ItemParam.MED
    HYPER_POTION = 25, ItemParam.MED
    SUPER_POTION = 26, ItemParam.MED
    FULL_HEAL = 27, ItemParam.MED
    REVIVE = 28, ItemParam.MED
    MAX_REVIVE = 29, ItemParam.MED
    FRESH_WATER = 30, ItemParam.MED
    SODA_POP = 31, ItemParam.MED
    LEMONADE = 32, ItemParam.MED
    MOOMOO_MILK = 33, ItemParam.MED
    ENERGY_POWDER = 34, ItemParam.MED
    ENERGY_ROOT = 35, ItemParam.MED
    HEAL_POWDER = 36, ItemParam.MED
    REVIVAL_HERB = 37, ItemParam.MED
    ETHER = 38, ItemParam.MED
    MAX_ETHER = 39, ItemParam.MED
    ELIXIR = 40, ItemParam.MED
    MAX_ELIXIR = 41, ItemParam.MED
    LAVA_COOKIE = 42, ItemParam.MED
    BERRY_JUICE = 43, ItemParam.MED
    SACRED_ASH = 44, ItemParam.MED
    
    # Vitamins
    HP_UP = 45, ItemParam.OBO
    PROTEIN = 46, ItemParam.OBO
    IRON = 47, ItemParam.OBO
    CARBOS = 48, ItemParam.OBO
    CALCIUM = 49, ItemParam.OBO
    RARE_CANDY = 50, ItemParam.OBO
    PP_UP = 51, ItemParam.OBO
    ZINC = 52, ItemParam.OBO
    PP_MAX = 53, ItemParam.OBO
    
    # X items
    OLD_GATEAU = 54, ItemParam.MED
    GUARD_SPEC = 55, ItemParam.BAT
    DIRE_HIT = 56, ItemParam.BAT
    X_ATTACK = 57, ItemParam.BAT
    X_DEFENSE = 58, ItemParam.BAT
    X_SPEED = 59, ItemParam.BAT
    X_ACCURACY = 60, ItemParam.BAT
    X_SPECIAL = 61, ItemParam.BAT
    X_SP_DEF = 62, ItemParam.BAT
    POKE_DOLL = 63, ItemParam.BAT
    FLUFFY_TAIL = 64, ItemParam.BAT
    
    # Random Ish
    BLUE_FLUTE = 65, ItemParam.BAT
    YELLOW_FLUTE = 66, ItemParam.BAT
    RED_FLUTE = 67, ItemParam.BAT
    BLACK_FLUTE = 68, ItemParam.BAT
    WHITE_FLUTE = 69, ItemParam.BAT
    SHOAL_SALT = 70, ItemParam.EXTRA
    SHOAL_SHELL = 71, ItemParam.EXTRA
    RED_SHARD = 72, ItemParam.VAL
    BLUE_SHARD = 73, ItemParam.VAL
    YELLOW_SHARD = 74, ItemParam.VAL
    GREEN_SHARD = 75, ItemParam.VAL
    SUPER_REPEL = 76, ItemParam.OBO
    MAX_REPEL = 77, ItemParam.OBO
    ESCAPE_ROPE = 78, ItemParam.OBO
    REPEL = 79, ItemParam.OBO
    SUN_STONE = 80, ItemParam.EVO
    MOON_STONE = 81, ItemParam.EVO
    FIRE_STONE = 82, ItemParam.EVO
    THUNDER_STONE = 83, ItemParam.EVO
    WATER_STONE = 84, ItemParam.EVO
    LEAF_STONE = 85, ItemParam.EVO
    TINY_MUSHROOM = 86, ItemParam.VAL
    BIG_MUSHROOM = 87, ItemParam.VAL
    PEARL = 88, ItemParam.VAL
    BIG_PEARL = 89, ItemParam.VAL
    STARDUST = 90, ItemParam.VAL
    STAR_PIECE = 91, ItemParam.VAL
    NUGGET = 92, ItemParam.VAL
    HEART_SCALE = 93, ItemParam.VAL
    HONEY = 94, ItemParam.OBO
    GROWTH_MULCH = 95, ItemParam.OBO
    DAMP_MULCH = 96, ItemParam.OBO
    STABLE_MULCH = 97, ItemParam.OBO
    GOOEY_MULCH = 98, ItemParam.OBO
    ROOT_FOSSIL = 99, ItemParam.VAL
    CLAW_FOSSIL = 100, ItemParam.VAL
    HELIX_FOSSIL = 101, ItemParam.VAL
    DOME_FOSSIL = 102, ItemParam.VAL
    OLD_AMBER = 103, ItemParam.VAL
    ARMOR_FOSSIL = 104, ItemParam.VAL
    SKULL_FOSSIL = 105, ItemParam.VAL
    RARE_BONE = 106, ItemParam.VAL
    SHINY_STONE = 107, ItemParam.EVO
    DUSK_STONE = 108, ItemParam.EVO
    DAWN_STONE = 109, ItemParam.EVO
    OVAL_STONE = 110, ItemParam.EVO
    ODD_KEYSTONE = 111, ItemParam.EXTRA
    GRISEOUS_ORB = 112, ItemParam.HELD

    #UNKNOWN ITEMS
    ITEM_UNKNOWN_71 = 113, ItemParam.EXTRA
    ITEM_UNKNOWN_72 = 114, ItemParam.EXTRA
    ITEM_UNKNOWN_73 = 115, ItemParam.EXTRA
    ITEM_UNKNOWN_74 = 116, ItemParam.EXTRA
    ITEM_UNKNOWN_75 = 117, ItemParam.EXTRA
    ITEM_UNKNOWN_76 = 118, ItemParam.EXTRA
    ITEM_UNKNOWN_77 = 119, ItemParam.EXTRA
    ITEM_UNKNOWN_78 = 120, ItemParam.EXTRA
    ITEM_UNKNOWN_79 = 121, ItemParam.EXTRA
    ITEM_UNKNOWN_7A = 122, ItemParam.EXTRA
    ITEM_UNKNOWN_7B = 123, ItemParam.EXTRA
    ITEM_UNKNOWN_7C = 124, ItemParam.EXTRA
    ITEM_UNKNOWN_7D = 125, ItemParam.EXTRA
    ITEM_UNKNOWN_7E = 126, ItemParam.EXTRA
    ITEM_UNKNOWN_7F = 127, ItemParam.EXTRA
    ITEM_UNKNOWN_80 = 128, ItemParam.EXTRA
    ITEM_UNKNOWN_81 = 129, ItemParam.EXTRA
    ITEM_UNKNOWN_82 = 130, ItemParam.EXTRA
    ITEM_UNKNOWN_83 = 131, ItemParam.EXTRA
    ITEM_UNKNOWN_84 = 132, ItemParam.EXTRA
    ITEM_UNKNOWN_85 = 133, ItemParam.EXTRA
    ITEM_UNKNOWN_86 = 134, ItemParam.EXTRA

#CONT'D
    ADAMANT_ORB = 135, ItemParam.HELD
    LUSTROUS_ORB = 136, ItemParam.HELD

    
    # Mail
    GRASS_MAIL = 137, ItemParam.EXTRA
    FLAME_MAIL = 138, ItemParam.EXTRA
    BUBBLE_MAIL = 139, ItemParam.EXTRA
    BLOOM_MAIL = 140, ItemParam.EXTRA
    TUNNEL_MAIL = 141, ItemParam.EXTRA
    STEEL_MAIL = 142, ItemParam.EXTRA
    HEART_MAIL = 143, ItemParam.EXTRA
    SNOW_MAIL = 144, ItemParam.EXTRA
    SPACE_MAIL = 145, ItemParam.EXTRA
    AIR_MAIL = 146, ItemParam.EXTRA
    MOSAIC_MAIL = 147, ItemParam.EXTRA
    BRICK_MAIL = 148, ItemParam.EXTRA
    
    # BERRY
    CHERI_BERRY = 149, ItemParam.BER
    CHESTO_BERRY = 150, ItemParam.BER
    PECHA_BERRY = 151, ItemParam.BER
    RAWST_BERRY = 152, ItemParam.BER
    ASPEAR_BERRY = 153, ItemParam.BER
    LEPPA_BERRY = 154, ItemParam.BER
    ORAN_BERRY = 155, ItemParam.BER
    PERSIM_BERRY = 156, ItemParam.BER
    LUM_BERRY = 157, ItemParam.BER
    SITRUS_BERRY = 158, ItemParam.BER
    FIGY_BERRY = 159, ItemParam.BER
    WIKI_BERRY = 160, ItemParam.BER
    MAGO_BERRY = 161, ItemParam.BER
    AGUAV_BERRY = 162, ItemParam.BER
    IAPAPA_BERRY = 163, ItemParam.BER
    RAZZ_BERRY = 164, ItemParam.BER
    BLUK_BERRY = 165, ItemParam.BER
    NANAB_BERRY = 166, ItemParam.BER
    WEPEAR_BERRY = 167, ItemParam.BER
    PINAP_BERRY = 168, ItemParam.BER
    POMEG_BERRY = 169, ItemParam.BER
    KELPSY_BERRY = 170, ItemParam.BER
    QUALOT_BERRY = 171, ItemParam.BER
    HONDEW_BERRY = 172, ItemParam.BER
    GREPA_BERRY = 173, ItemParam.BER
    TAMATO_BERRY = 174, ItemParam.BER
    CORNN_BERRY = 175, ItemParam.BER
    MAGOST_BERRY = 176, ItemParam.BER
    RABUTA_BERRY = 177, ItemParam.BER
    NOMEL_BERRY = 178, ItemParam.BER
    SPELON_BERRY = 179, ItemParam.BER
    PAMTRE_BERRY = 180, ItemParam.BER
    WATMEL_BERRY = 181, ItemParam.BER
    DURIN_BERRY = 182, ItemParam.BER
    BELUE_BERRY = 183, ItemParam.BER
    OCCA_BERRY = 184, ItemParam.BER
    PASSHO_BERRY = 185, ItemParam.BER
    WACAN_BERRY = 186, ItemParam.BER
    RINDO_BERRY = 187, ItemParam.BER
    YACHE_BERRY = 188, ItemParam.BER
    CHOPLE_BERRY = 189, ItemParam.BER
    KEBIA_BERRY = 190, ItemParam.BER
    SHUCA_BERRY = 191, ItemParam.BER
    COBA_BERRY = 192, ItemParam.BER
    PAYAPA_BERRY = 193, ItemParam.BER
    TANGA_BERRY = 194, ItemParam.BER
    CHARTI_BERRY = 195, ItemParam.BER
    KASIB_BERRY = 196, ItemParam.BER
    HABAN_BERRY = 197, ItemParam.BER
    COLBUR_BERRY = 198, ItemParam.BER
    BABIRI_BERRY = 199, ItemParam.BER
    CHILAN_BERRY = 200, ItemParam.BER
    LIECHI_BERRY = 201, ItemParam.BER
    GANLON_BERRY = 202, ItemParam.BER
    SALAC_BERRY = 203, ItemParam.BER
    PETAYA_BERRY = 204, ItemParam.BER
    APICOT_BERRY = 205, ItemParam.BER
    LANSAT_BERRY = 206, ItemParam.BER
    STARF_BERRY = 207, ItemParam.BER
    ENIGMA_BERRY = 208, ItemParam.BER
    MICLE_BERRY = 209, ItemParam.BER
    CUSTAP_BERRY = 210, ItemParam.BER
    JABOCA_BERRY = 211, ItemParam.BER
    ROWAP_BERRY = 212, ItemParam.BER
    BRIGHTPOWDER = 213, ItemParam.HELD
    WHITE_HERB = 214, ItemParam.HELD
    MACHO_BRACE = 215, ItemParam.EXTRA
    EXP_SHARE = 216, ItemParam.HELD
    QUICK_CLAW = 217, ItemParam.HELD
    SOOTHE_BELL = 218, ItemParam.HELD
    MENTAL_HERB = 219, ItemParam.HELD
    CHOICE_BAND = 220, ItemParam.HELD
    KINGS_ROCK = 221, ItemParam.HELD
    SILVER_POWDER = 222, ItemParam.HELD
    AMULET_COIN = 223, ItemParam.HELD
    CLEANSE_TAG = 224, ItemParam.HELD
    SOUL_DEW = 225, ItemParam.HELD
    DEEP_SEA_TOOTH = 226, ItemParam.EVO
    DEEP_SEA_SCALE = 227, ItemParam.EVO
    SMOKE_BALL = 228, ItemParam.HELD
    EVERSTONE = 229, ItemParam.HELD
    FOCUS_BAND = 230, ItemParam.HELD
    LUCKY_EGG = 231, ItemParam.HELD
    SCOPE_LENS = 232, ItemParam.HELD
    METAL_COAT = 233, ItemParam.HELD
    LEFTOVERS = 234, ItemParam.HELD
    DRAGON_SCALE = 235, ItemParam.EVO
    LIGHT_BALL = 236, ItemParam.HELD
    SOFT_SAND = 237, ItemParam.HELD
    HARD_STONE = 238, ItemParam.HELD
    MIRACLE_SEED = 239, ItemParam.HELD
    BLACK_GLASSES = 240, ItemParam.HELD
    BLACK_BELT = 241, ItemParam.HELD
    MAGNET = 242, ItemParam.HELD
    MYSTIC_WATER = 243, ItemParam.HELD
    SHARP_BEAK = 244, ItemParam.HELD
    POISON_BARB = 245, ItemParam.HELD
    NEVER_MELT_ICE = 246, ItemParam.HELD
    SPELL_TAG = 247, ItemParam.HELD
    TWISTED_SPOON = 248, ItemParam.HELD
    CHARCOAL = 249, ItemParam.HELD
    DRAGON_FANG = 250, ItemParam.HELD
    SILK_SCARF = 251, ItemParam.HELD
    UP_GRADE = 252, ItemParam.EVO
    SHELL_BELL = 253, ItemParam.HELD
    SEA_INCENSE = 254, ItemParam.HELD
    LAX_INCENSE = 255, ItemParam.HELD
    LUCKY_PUNCH = 256, ItemParam.HELD
    METAL_POWDER = 257, ItemParam.HELD
    THICK_CLUB = 258, ItemParam.HELD
    STICK = 259, ItemParam.HELD
    RED_SCARF = 260, ItemParam.EXTRA   
    BLUE_SCARF = 261, ItemParam.EXTRA
    PINK_SCARF = 262, ItemParam.EXTRA
    GREEN_SCARF = 263, ItemParam.EXTRA
    YELLOW_SCARF = 264, ItemParam.EXTRA
    WIDE_LENS = 265, ItemParam.HELD
    MUSCLE_BAND = 266, ItemParam.HELD
    WISE_GLASSES = 267, ItemParam.HELD
    EXPERT_BELT = 268, ItemParam.HELD
    LIGHT_CLAY = 269, ItemParam.HELD
    LIFE_ORB = 270, ItemParam.HELD
    POWER_HERB = 271, ItemParam.HELD
    TOXIC_ORB = 272, ItemParam.HELD
    FLAME_ORB = 273, ItemParam.HELD
    QUICK_POWDER = 274, ItemParam.HELD
    FOCUS_SASH = 275, ItemParam.HELD
    ZOOM_LENS = 276, ItemParam.HELD
    METRONOME = 277, ItemParam.HELD
    IRON_BALL = 278, ItemParam.HELD
    LAGGING_TAIL = 279, ItemParam.HELD
    DESTINY_KNOT = 280, ItemParam.HELD
    BLACK_SLUDGE = 281, ItemParam.HELD
    ICY_ROCK = 282, ItemParam.HELD
    SMOOTH_ROCK = 283, ItemParam.HELD
    HEAT_ROCK = 284, ItemParam.HELD
    DAMP_ROCK = 285, ItemParam.HELD
    GRIP_CLAW = 286, ItemParam.HELD
    CHOICE_SCARF = 287, ItemParam.HELD
    STICKY_BARB = 288, ItemParam.HELD
    POWER_BRACER = 289, ItemParam.EXTRA
    POWER_BELT = 290, ItemParam.EXTRA
    POWER_LENS = 291, ItemParam.EXTRA
    POWER_BAND = 292, ItemParam.EXTRA
    POWER_ANKLET = 293, ItemParam.EXTRA
    POWER_WEIGHT = 294, ItemParam.EXTRA
    SHED_SHELL = 295, ItemParam.HELD
    BIG_ROOT = 296, ItemParam.HELD
    CHOICE_SPECS = 297, ItemParam.HELD
    FLAME_PLATE = 298, ItemParam.HELD
    SPLASH_PLATE = 299, ItemParam.HELD
    ZAP_PLATE = 300, ItemParam.HELD
    MEADOW_PLATE = 301, ItemParam.HELD
    ICICLE_PLATE = 302, ItemParam.HELD
    FIST_PLATE = 303, ItemParam.HELD
    TOXIC_PLATE = 304, ItemParam.HELD
    EARTH_PLATE = 305, ItemParam.HELD
    SKY_PLATE = 306, ItemParam.HELD
    MIND_PLATE = 307, ItemParam.HELD
    INSECT_PLATE = 308, ItemParam.HELD
    STONE_PLATE = 309, ItemParam.HELD
    SPOOKY_PLATE = 310, ItemParam.HELD
    DRACO_PLATE = 311, ItemParam.HELD
    DREAD_PLATE = 312, ItemParam.HELD
    IRON_PLATE = 313, ItemParam.HELD
    ODD_INCENSE = 314, ItemParam.HELD
    ROCK_INCENSE = 315, ItemParam.HELD
    FULL_INCENSE = 316, ItemParam.HELD
    WAVE_INCENSE = 317, ItemParam.HELD
    ROSE_INCENSE = 318, ItemParam.HELD
    LUCK_INCENSE = 319, ItemParam.HELD
    PURE_INCENSE = 320, ItemParam.HELD
    PROTECTOR = 321, ItemParam.EVO
    ELECTIRIZER = 322, ItemParam.EVO
    MAGMARIZER = 323, ItemParam.EVO
    DUBIOUS_DISC = 324, ItemParam.EVO
    REAPER_CLOTH = 325, ItemParam.EVO
    RAZOR_CLAW = 326, ItemParam.EVO
    RAZOR_FANG = 327, ItemParam.EVO
   
   
    # TMs
    TM01 = 328, ItemParam.TM
    TM02 = 329, ItemParam.TM
    TM03 = 330, ItemParam.TM
    TM04 = 331, ItemParam.TM
    TM05 = 332, ItemParam.TM
    TM06 = 333, ItemParam.TM
    TM07 = 334, ItemParam.TM
    TM08 = 335, ItemParam.TM
    TM09 = 336, ItemParam.TM
    TM10 = 337, ItemParam.TM
    TM11 = 338, ItemParam.TM
    TM12 = 339, ItemParam.TM
    TM13 = 340, ItemParam.TM
    TM14 = 341, ItemParam.TM
    TM15 = 342, ItemParam.TM
    TM16 = 343, ItemParam.TM
    TM17 = 344, ItemParam.TM
    TM18 = 345, ItemParam.TM
    TM19 = 346, ItemParam.TM
    TM20 = 347, ItemParam.TM
    TM21 = 348, ItemParam.TM
    TM22 = 349, ItemParam.TM
    TM23 = 350, ItemParam.TM
    TM24 = 351, ItemParam.TM
    TM25 = 352, ItemParam.TM
    TM26 = 353, ItemParam.TM
    TM27 = 354, ItemParam.TM
    TM28 = 355, ItemParam.TM
    TM29 = 356, ItemParam.TM
    TM30 = 357, ItemParam.TM
    TM31 = 358, ItemParam.TM
    TM32 = 359, ItemParam.TM
    TM33 = 360, ItemParam.TM
    TM34 = 361, ItemParam.TM
    TM35 = 362, ItemParam.TM
    TM36 = 363, ItemParam.TM
    TM37 = 364, ItemParam.TM
    TM38 = 365, ItemParam.TM
    TM39 = 366, ItemParam.TM
    TM40 = 367, ItemParam.TM
    TM41 = 368, ItemParam.TM
    TM42 = 369, ItemParam.TM
    TM43 = 370, ItemParam.TM
    TM44 = 371, ItemParam.TM
    TM45 = 372, ItemParam.TM
    TM46 = 373, ItemParam.TM
    TM47 = 374, ItemParam.TM
    TM48 = 375, ItemParam.TM
    TM49 = 376, ItemParam.TM
    TM50 = 377, ItemParam.TM
    TM51 = 378, ItemParam.TM
    TM52 = 379, ItemParam.TM
    TM53 = 380, ItemParam.TM
    TM54 = 381, ItemParam.TM
    TM55 = 382, ItemParam.TM
    TM56 = 383, ItemParam.TM
    TM57 = 384, ItemParam.TM
    TM58 = 385, ItemParam.TM
    TM59 = 386, ItemParam.TM
    TM60 = 387, ItemParam.TM
    TM61 = 388, ItemParam.TM
    TM62 = 389, ItemParam.TM
    TM63 = 390, ItemParam.TM
    TM64 = 391, ItemParam.TM
    TM65 = 392, ItemParam.TM
    TM66 = 393, ItemParam.TM
    TM67 = 394, ItemParam.TM
    TM68 = 395, ItemParam.TM
    TM69 = 396, ItemParam.TM
    TM70 = 397, ItemParam.TM
    TM71 = 398, ItemParam.TM
    TM72 = 399, ItemParam.TM
    TM73 = 400, ItemParam.TM
    TM74 = 401, ItemParam.TM
    TM75 = 402, ItemParam.TM
    TM76 = 403, ItemParam.TM
    TM77 = 404, ItemParam.TM
    TM78 = 405, ItemParam.TM
    TM79 = 406, ItemParam.TM
    TM80 = 407, ItemParam.TM
    TM81 = 408, ItemParam.TM
    TM82 = 409, ItemParam.TM
    TM83 = 410, ItemParam.TM
    TM84 = 411, ItemParam.TM
    TM85 = 412, ItemParam.TM
    TM86 = 413, ItemParam.TM
    TM87 = 414, ItemParam.TM
    TM88 = 415, ItemParam.TM
    TM89 = 416, ItemParam.TM
    TM90 = 417, ItemParam.TM
    TM91 = 418, ItemParam.TM
    TM92 = 419, ItemParam.TM
    
    # HMs
    HM01 = 420, ItemParam.HM
    HM02 = 421, ItemParam.HM
    HM03 = 422, ItemParam.HM
    HM04 = 423, ItemParam.HM
    HM05 = 424, ItemParam.HM
    HM06 = 425, ItemParam.HM
    HM07 = 426, ItemParam.HM
    HM08 = 427, ItemParam.HM
    
    # Key items
    EXPLORER_KIT = 428, ItemParam.KEY
    LOOT_SACK = 429, ItemParam.KEY
    RULE_BOOK = 430, ItemParam.KEY
    POKE_RADAR = 431, ItemParam.KEY
    POINT_CARD = 432, ItemParam.KEY
    JOURNAL = 433, ItemParam.KEY
    SEAL_CASE = 434, ItemParam.KEY
    FASHION_CASE = 435, ItemParam.KEY
    SEAL_BAG = 436, ItemParam.KEY
    PAL_PAD = 437, ItemParam.KEY
    WORKS_KEY = 438, ItemParam.KEY
    OLD_CHARM = 439, ItemParam.KEY
    GALACTIC_KEY = 440, ItemParam.KEY
    RED_CHAIN = 441, ItemParam.KEY
    TOWN_MAP = 442, ItemParam.KEY
    VS_SEEKER = 443, ItemParam.KEY
    COIN_CASE = 444, ItemParam.KEY
    OLD_ROD = 445, ItemParam.KEY
    GOOD_ROD = 446, ItemParam.KEY
    SUPER_ROD = 447, ItemParam.KEY
    SPRAYDUCK = 448, ItemParam.KEY
    POFFIN_CASE = 449, ItemParam.KEY
    BICYCLE = 450, ItemParam.KEY
    SUITE_KEY = 451, ItemParam.KEY
    OAKS_LETTER = 452, ItemParam.KEY
    LUNAR_WING = 453, ItemParam.KEY
    MEMBER_CARD = 454, ItemParam.KEY
    AZURE_FLUTE = 455, ItemParam.KEY
    SS_TICKET = 456, ItemParam.KEY
    CONTEST_PASS = 457, ItemParam.KEY
    MAGMA_STONE = 458, ItemParam.KEY
    PARCEL = 459, ItemParam.KEY
    COUPON_1 = 460, ItemParam.KEY
    COUPON_2 = 461, ItemParam.KEY
    COUPON_3 = 462, ItemParam.KEY
    STORAGE_KEY = 463, ItemParam.KEY
    SECRET_MEDICINE = 464, ItemParam.KEY
    VS_RECORDER = 465, ItemParam.KEY
    GRACIDEA = 466, ItemParam.KEY
    SECRET_KEY = 467, ItemParam.KEY
    APRICORN_BOX = 468, ItemParam.KEY
    UNOWN_REPORT = 469, ItemParam.KEY
    BERRY_POTS = 470, ItemParam.KEY
    DOWSING_MCHN = 471, ItemParam.KEY
    BLUE_CARD = 472, ItemParam.KEY
    SLOWPOKE_TAIL = 473, ItemParam.KEY
    CLEAR_BELL = 474, ItemParam.KEY
    CARD_KEY = 475, ItemParam.KEY
    BASEMENT_KEY = 476, ItemParam.KEY
    SQUIRT_BOTTLE = 477, ItemParam.KEY
    RED_SCALE = 478, ItemParam.KEY
    LOST_ITEM = 479, ItemParam.KEY
    PASS = 480, ItemParam.KEY
    MACHINE_PART = 481, ItemParam.KEY
    SILVER_WING = 482, ItemParam.KEY
    RAINBOW_WING = 483, ItemParam.KEY
    MYSTERY_EGG = 484, ItemParam.KEY
    
    # Apricorns
    RED_APRICORN = 485, ItemParam.EXTRA
    YELLOW_APRICORN = 486, ItemParam.EXTRA
    BLUE_APRICORN = 487, ItemParam.EXTRA
    GREEN_APRICORN = 488, ItemParam.EXTRA
    PINK_APRICORN = 489, ItemParam.EXTRA
    WHITE_APRICORN = 490, ItemParam.EXTRA
    BLACK_APRICORN = 491, ItemParam.EXTRA
    
    # Kurt Balls
    FAST_BALL = 492, ItemParam.BALL
    LEVEL_BALL = 493, ItemParam.BALL
    LURE_BALL = 494, ItemParam.BALL
    HEAVY_BALL = 495, ItemParam.BALL
    LOVE_BALL = 496, ItemParam.BALL
    FRIEND_BALL = 497, ItemParam.BALL
    MOON_BALL = 498, ItemParam.BALL
    SPORT_BALL = 499, ItemParam.BALL
    PARK_BALL = 500, ItemParam.BALL
    
    # Key Items Continued
    PHOTO_ALBUM = 501, ItemParam.KEY    
    GB_SOUNDS = 502, ItemParam.KEY
    TIDAL_BELL = 503, ItemParam.KEY
    RAGE_CANDY_BAR = 504, ItemParam.KEY
    DATA_CARD_01 = 505, ItemParam.KEY
    DATA_CARD_02 = 506, ItemParam.KEY
    DATA_CARD_03 = 507, ItemParam.KEY
    DATA_CARD_04 = 508, ItemParam.KEY
    DATA_CARD_05 = 509, ItemParam.KEY
    DATA_CARD_06 = 510, ItemParam.KEY
    DATA_CARD_07 = 511, ItemParam.KEY
    DATA_CARD_08 = 512, ItemParam.KEY
    DATA_CARD_09 = 513, ItemParam.KEY
    DATA_CARD_10 = 514, ItemParam.KEY
    DATA_CARD_11 = 515, ItemParam.KEY
    DATA_CARD_12 = 516, ItemParam.KEY
    DATA_CARD_13 = 517, ItemParam.KEY
    DATA_CARD_14 = 518, ItemParam.KEY
    DATA_CARD_15 = 519, ItemParam.KEY
    DATA_CARD_16 = 520, ItemParam.KEY
    DATA_CARD_17 = 521, ItemParam.KEY
    DATA_CARD_18 = 522, ItemParam.KEY
    DATA_CARD_19 = 523, ItemParam.KEY
    DATA_CARD_20 = 524, ItemParam.KEY
    DATA_CARD_21 = 525, ItemParam.KEY
    DATA_CARD_22 = 526, ItemParam.KEY
    DATA_CARD_23 = 527, ItemParam.KEY
    DATA_CARD_24 = 528, ItemParam.KEY
    DATA_CARD_25 = 529, ItemParam.KEY
    DATA_CARD_26 = 530, ItemParam.KEY
    DATA_CARD_27 = 531, ItemParam.KEY
    JADE_ORB = 532, ItemParam.KEY
    LOCK_CAPSULE = 533, ItemParam.KEY
    RED_ORB = 534, ItemParam.KEY
    BLUE_ORB = 535, ItemParam.KEY
    ENIGMA_STONE = 536, ItemParam.KEY
    
    # Mega stones
    VENUSAURITE = 537, ItemParam.MEGA
    CHARIZARDITE_X = 538, ItemParam.MEGA
    CHARIZARDITE_Y = 539, ItemParam.MEGA
    BLASTOISINITE = 540, ItemParam.MEGA
    BEEDRILLITE = 541, ItemParam.MEGA
    PIDGEOTITE = 542, ItemParam.MEGA
    ALAKAZITE = 543, ItemParam.MEGA
    SLOWBRONITE = 544, ItemParam.MEGA
    GENGARITE = 545, ItemParam.MEGA
    KANGASKHANITE = 546, ItemParam.MEGA
    PINSIRITE = 547, ItemParam.MEGA
    GYARADOSITE = 548, ItemParam.MEGA
    AERODACTYLITE = 549, ItemParam.MEGA
    MEWTWONITE_X = 550, ItemParam.MEGA
    MEWTWONITE_Y = 551, ItemParam.MEGA
    AMPHAROSITE = 552, ItemParam.MEGA
    STEELIXITE = 553, ItemParam.MEGA
    SCIZORITE = 554, ItemParam.MEGA
    HERACRONITE = 555, ItemParam.MEGA
    HOUNDOOMINITE = 556, ItemParam.MEGA
    TYRANITARITE = 557, ItemParam.MEGA
    SCEPTILITE = 558, ItemParam.MEGA
    BLAZIKENITE = 559, ItemParam.MEGA
    SWAMPERTITE = 560, ItemParam.MEGA
    GARDEVOIRITE = 561, ItemParam.MEGA
    SABLENITE = 562, ItemParam.MEGA
    MAWILITE = 563, ItemParam.MEGA
    AGGRONITE = 564, ItemParam.MEGA
    MEDICHAMITE = 565, ItemParam.MEGA
    MANECTITE = 566, ItemParam.MEGA
    SHARPEDONITE = 567, ItemParam.MEGA
    CAMERUPTITE = 568, ItemParam.MEGA
    ALTARIANITE = 569, ItemParam.MEGA
    BANETTITE = 570, ItemParam.MEGA
    ABSOLITE = 571, ItemParam.MEGA
    GLALITITE = 572, ItemParam.MEGA
    SALAMENCITE = 573, ItemParam.MEGA
    METAGROSSITE = 574, ItemParam.MEGA
    LATIASITE = 575, ItemParam.MEGA
    LATIOSITE = 576, ItemParam.MEGA
    LOPUNNITE = 577, ItemParam.MEGA
    GARCHOMPITE = 578, ItemParam.MEGA
    LUCARIONITE = 579, ItemParam.MEGA
    ABOMASITE = 580, ItemParam.MEGA
    GALLADITE = 581, ItemParam.MEGA
    AUDINITE = 582, ItemParam.MEGA
    DIANCITE = 583, ItemParam.MEGA
    
    # Pixie plate lol
    PIXIE_PLATE = 584, ItemParam.HELD
    
    # Gen V Items
    ABSORB_BULB = 585, ItemParam.HELD
    AIR_BALLOON = 586, ItemParam.HELD
    BALM_MUSHROOM = 587, ItemParam.VAL
    BIG_NUGGET = 588, ItemParam.VAL
    BINDING_BAND = 589, ItemParam.HELD
    CASTELIACONE = 590, ItemParam.MED
    CELL_BATTERY = 591, ItemParam.HELD
    COMET_SHARD = 592, ItemParam.VAL
    DREAM_BALL = 593, ItemParam.BALL
    EJECT_BUTTON = 594, ItemParam.HELD
    EVIOLITE = 595, ItemParam.HELD
    FLOAT_STONE = 596, ItemParam.HELD
    PEARL_STRING = 597, ItemParam.VAL
    PRISM_SCALE = 598, ItemParam.EVO
    RED_CARD = 599, ItemParam.HELD
    RING_TARGET = 600, ItemParam.HELD
    ROCKY_HELMET = 601, ItemParam.HELD
    SWEET_HEART = 602, ItemParam.EXTRA
    
    # Generation VI items
    ABILITY_CAPSULE = 603, ItemParam.OBO
    ASSAULT_VEST = 604, ItemParam.HELD
    LUMINOUS_MOSS = 605, ItemParam.HELD
    LUMIOSE_GALETTE = 606, ItemParam.MED
    SACHET = 607, ItemParam.EVO
    SAFETY_GOGGLES = 608, ItemParam.HELD
    SHALOUR_SABLE = 609, ItemParam.MED
    SNOWBALL = 610, ItemParam.HELD
    WEAKNESS_POLICY = 611, ItemParam.HELD
    WHIPPED_DREAM = 612, ItemParam.EVO
    
    # Generation VII items
    ADRENALINE_ORB = 613, ItemParam.HELD
    BEAST_BALL = 614, ItemParam.BALL
    BIG_MALASADA = 615, ItemParam.MED
    BOTTLE_CAP = 616, ItemParam.OBO
    GOLD_BOTTLE_CAP = 617, ItemParam.OBO
    ELECTRIC_SEED = 618, ItemParam.HELD
    GRASSY_SEED = 619, ItemParam.HELD
    MISTY_SEED = 620, ItemParam.HELD
    PSYCHIC_SEED = 621, ItemParam.HELD
    ICE_STONE = 622, ItemParam.EVO
    PROTECTIVE_PADS = 623, ItemParam.HELD
    TERRAIN_EXTENDER = 624, ItemParam.HELD
    
    # Generation VIII items
    ABILITY_PATCH = 625, ItemParam.OBO
    BLACK_AUGURITE = 626, ItemParam.EVO
    BERRY_SWEET = 627, ItemParam.EVO
    CLOVER_SWEET = 628, ItemParam.EVO
    FLOWER_SWEET = 629, ItemParam.EVO
    LOVE_SWEET = 630, ItemParam.EVO
    RIBBON_SWEET = 631, ItemParam.EVO
    STAR_SWEET = 632, ItemParam.EVO
    STRAWBERRY_SWEET = 633, ItemParam.EVO
    BLUNDER_POLICY = 634, ItemParam.HELD
    CHIPPED_POT = 635, ItemParam.EVO
    CRACKED_POT = 636, ItemParam.EVO
    EJECT_PACK = 637, ItemParam.HELD
    EXP_CANDY_S = 638, ItemParam.UNIMPL
    EXP_CANDY_M = 639, ItemParam.UNIMPL
    EXP_CANDY_L = 640, ItemParam.UNIMPL
    EXP_CANDY_XS = 641, ItemParam.UNIMPL
    EXP_CANDY_XL = 642, ItemParam.UNIMPL
    GALARICA_CUFF = 643, ItemParam.EVO
    GALARICA_TWIG = 644, ItemParam.EXTRA
    GALARICA_WREATH = 645, ItemParam.EVO
    HEAVY_DUTY_BOOTS = 646, ItemParam.HELD
    LINKING_CORD = 647, ItemParam.EVO
    MOOMOO_CHEESE = 648, ItemParam.EXTRA
    PEAT_BLOCK = 649, ItemParam.EVO
    ROOM_SERVICE = 650, ItemParam.HELD
    RUSTED_SHIELD = 651, ItemParam.HELD
    RUSTED_SWORD = 652, ItemParam.HELD
    SWEET_APPLE = 653, ItemParam.EVO
    TART_APPLE = 654, ItemParam.EVO
    THROAT_SPRAY = 655, ItemParam.HELD
    UTILITY_UMBRELLA = 656, ItemParam.HELD
    
    # Generation IX items
    ABILITY_SHIELD = 657, ItemParam.HELD
    AUSPICIOUS_ARMOR = 658, ItemParam.EVO
    BOOSTER_ENERGY = 659, ItemParam.UNIMPL
    CLEAR_AMULET = 660, ItemParam.HELD
    COVERT_CLOAK = 661, ItemParam.HELD
    GIMMIGHOUL_COIN = 662, ItemParam.UNIMPL
    LEADERS_CREST = 663, ItemParam.UNIMPL
    LOADED_DICE = 664, ItemParam.HELD
    MALICIOUS_ARMOR = 665, ItemParam.EVO
    MIRROR_HERB = 666, ItemParam.HELD
    PUNCHING_GLOVE = 667, ItemParam.HELD
    
    # Additional berries
    ROSELI_BERRY = 668, ItemParam.BER
    KEE_BERRY = 669, ItemParam.BER
    MARANGA_BERRY = 670, ItemParam.BER
    
    # Drives
    BURN_DRIVE = 671, ItemParam.HELD
    CHILL_DRIVE = 672, ItemParam.HELD
    DOUSE_DRIVE = 673, ItemParam.HELD
    SHOCK_DRIVE = 674, ItemParam.HELD
    
    # Fossils
    COVER_FOSSIL = 675, ItemParam.VAL
    PLUME_FOSSIL = 676, ItemParam.VAL
    JAW_FOSSIL = 677, ItemParam.VAL
    SAIL_FOSSIL = 678, ItemParam.VAL
    FOSSILIZED_BIRD = 679, ItemParam.VAL
    FOSSILIZED_DINO = 680, ItemParam.VAL
    FOSSILIZED_DRAKE = 681, ItemParam.VAL
    FOSSILIZED_FISH = 682, ItemParam.VAL

    #GEMS

    NORMAL_GEM = 683, ItemParam.GEM
    FIGHTING_GEM = 684, ItemParam.GEM
    FLYING_GEM = 685, ItemParam.GEM
    POISON_GEM = 686, ItemParam.GEM
    GROUND_GEM = 687, ItemParam.GEM
    ROCK_GEM = 688, ItemParam.GEM
    BUG_GEM = 689, ItemParam.GEM
    GHOST_GEM = 690, ItemParam.GEM
    STEEL_GEM = 691, ItemParam.GEM
    FIRE_GEM = 692, ItemParam.GEM
    WATER_GEM = 693, ItemParam.GEM
    GRASS_GEM = 694, ItemParam.GEM
    ELECTRIC_GEM = 695, ItemParam.GEM
    PSYCHIC_GEM = 696, ItemParam.GEM
    ICE_GEM = 697, ItemParam.GEM
    DRAGON_GEM = 698, ItemParam.GEM
    DARK_GEM = 699, ItemParam.GEM
    FAIRY_GEM = 700, ItemParam.GEM

    #memories

    FIGHTING_MEMORY = 701, ItemParam.HELD
    FLYING_MEMORY = 702, ItemParam.HELD
    POISON_MEMORY = 703, ItemParam.HELD
    GROUND_MEMORY = 704, ItemParam.HELD
    ROCK_MEMORY = 705, ItemParam.HELD
    BUG_MEMORY = 706, ItemParam.HELD
    GHOST_MEMORY = 707, ItemParam.HELD
    STEEL_MEMORY = 708, ItemParam.HELD
    FIRE_MEMORY = 709, ItemParam.HELD
    WATER_MEMORY = 710, ItemParam.HELD
    GRASS_MEMORY = 711, ItemParam.HELD
    ELECTRIC_MEMORY = 712, ItemParam.HELD
    PSYCHIC_MEMORY = 713, ItemParam.HELD
    ICE_MEMORY = 714, ItemParam.HELD
    DRAGON_MEMORY = 715, ItemParam.HELD
    DARK_MEMORY = 716, ItemParam.HELD
    FAIRY_MEMORY = 717, ItemParam.HELD

    #NECTAR

    RED_NECTAR = 718, ItemParam.OBO
    YELLOW_NECTAR = 719, ItemParam.OBO
    PINK_NECTAR = 720, ItemParam.OBO
    PURPLE_NECTAR = 721, ItemParam.OBO

    #NEW PLATES
    BLANK_PLATE = 722, ItemParam.KEY
    LEGEND_PLATE = 723, ItemParam.KEY

    #RELIC ITEMS
    RELIC_COPPER = 724, ItemParam.KEY
    RELIC_SILVER = 725, ItemParam.KEY
    RELIC_GOLD = 726, ItemParam.KEY
    RELIC_VASE = 727, ItemParam.KEY
    RELIC_BAND = 728, ItemParam.KEY
    RELIC_STATUE = 729, ItemParam.KEY
    RELIC_CROWN = 730, ItemParam.KEY

    #WINGS

    HEALTH_FEATHER = 731, ItemParam.OBO
    MUSCLE_FEATHER = 732, ItemParam.OBO
    RESIST_FEATHER = 733, ItemParam.OBO
    GENIUS_FEATHER = 734, ItemParam.OBO
    CLEVER_FEATHER = 735, ItemParam.OBO
    SWIFT_FEATHER = 736, ItemParam.OBO
    PRETTY_FEATHER = 737, ItemParam.VAL

    #NEW KEY ITEMS
    DNA_SPLICERS = 738, ItemParam.KEY
    REVEAL_GLASS = 739, ItemParam.KEY
    PRISON_BOTTLE = 740, ItemParam.KEY
    CATCHING_CHARM = 741, ItemParam.KEY
    EXP_CHARM = 742, ItemParam.KEY
    OVAL_CHARM = 743, ItemParam.KEY
    SHINY_CHARM = 744, ItemParam.KEY
    N_SOLARIZER = 745, ItemParam.KEY
    N_LUNARIZER = 746, ItemParam.KEY
    POKEMON_BOX_LINK = 747, ItemParam.KEY
    ZYGARDE_CUBE = 748, ItemParam.KEY
    SUN_FLUTE = 749, ItemParam.KEY
    MOON_FLUTE = 750, ItemParam.KEY
    LIGHT_STONE = 751, ItemParam.KEY
    DARK_STONE = 752, ItemParam.KEY
    ICEROOT_CARROT = 753, ItemParam.KEY
    SHADEROOT_CARROT = 754, ItemParam.KEY
    REINS_OF_UNITY = 755, ItemParam.KEY
    WOODEN_CROWN = 756, ItemParam.KEY
    ROTOM_CATALOG = 757, ItemParam.KEY
    ADAMANT_CRYSTAL = 758, ItemParam.KEY
    LUSTROUS_GLOBE = 759, ItemParam.KEY
    GRISOUS_CORE = 760, ItemParam.KEY  
    SCROLL_OF_DARKNESS = 761, ItemParam.KEY
    SCROLL_OF_WATERS = 762, ItemParam.KEY
    MEGA_RING = 763, ItemParam.KEY

    #LET'S GO ITEMS

    AUTOGRAPH = 764, ItemParam.KEY
    GOLD_TEETH = 765, ItemParam.KEY
    KEY_STONE = 766, ItemParam.KEY
    LIFT_KEY = 767, ItemParam.KEY
    PEWTER_CRUNCHIES = 768, ItemParam.KEY
    SYLPH_SCOPE = 769, ItemParam.KEY
    TEA = 770, ItemParam.KEY

    #MINTS
    LONELY_MINT = 771, ItemParam.OBO
    ADAMANT_MINT = 772, ItemParam.OBO
    NAUGHTY_MINT = 773, ItemParam.OBO
    BRAVE_MINT = 774, ItemParam.OBO
    BOLD_MINT = 775, ItemParam.OBO
    IMPISH_MINT = 776, ItemParam.OBO
    LAX_MINT = 777, ItemParam.OBO
    RELAXED_MINT = 778, ItemParam.OBO
    MODEST_MINT = 779, ItemParam.OBO
    MILD_MINT = 780, ItemParam.OBO
    RASH_MINT = 781, ItemParam.OBO
    QUIET_MINT = 782, ItemParam.OBO
    CALM_MINT = 783, ItemParam.OBO
    GENTLE_MINT = 784, ItemParam.OBO
    CAREFUL_MINT = 785, ItemParam.OBO
    SASSY_MINT = 786, ItemParam.OBO
    TIMID_MINT = 787, ItemParam.OBO
    HASTY_MINT = 788, ItemParam.OBO
    JOLLY_MINT = 789, ItemParam.OBO
    NAIVE_MINT = 790, ItemParam.OBO
    SERIOUS_MINT = 791, ItemParam.OBO

    #GEN IX DLC

    FAIRY_FEATHER = 792, ItemParam.HELD
    SYRUPY_APPLE = 793, ItemParam.EVO
    UNREMARKABLE_TEACUP = 794, ItemParam.EVO
    MASTERPIECE_TEACUP = 795, ItemParam.EVO
    CORNERSTONE_MASK = 796, ItemParam.HELD
    WELLSPRING_MASK = 797, ItemParam.HELD
    HEARTHFLAME_MASK = 798, ItemParam.HELD
    METAL_ALLOY = 799, ItemParam.EVO