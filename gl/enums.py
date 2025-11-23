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
    POST_GAME = 5

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
    TEA = 113, ItemParam.KEY
    AUTOGRAPH = 114, ItemParam.EXTRA
    DOUSE_DRIVE = 115, ItemParam.UNIMPL
    SHOCK_DRIVE = 116, ItemParam.UNIMPL
    BURN_DRIVE = 117, ItemParam.UNIMPL
    CHILL_DRIVE = 118, ItemParam.UNIMPL
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
    TM001 = 328, ItemParam.TM
    TM002 = 329, ItemParam.TM
    TM003 = 330, ItemParam.TM
    TM004 = 331, ItemParam.TM
    TM005 = 332, ItemParam.TM
    TM006 = 333, ItemParam.TM
    TM007 = 334, ItemParam.TM
    TM008 = 335, ItemParam.TM
    TM009 = 336, ItemParam.TM
    TM010 = 337, ItemParam.TM
    TM011 = 338, ItemParam.TM
    TM012 = 339, ItemParam.TM
    TM013 = 340, ItemParam.TM
    TM014 = 341, ItemParam.TM
    TM015 = 342, ItemParam.TM
    TM016 = 343, ItemParam.TM
    TM017 = 344, ItemParam.TM
    TM018 = 345, ItemParam.TM
    TM019 = 346, ItemParam.TM
    TM020 = 347, ItemParam.TM
    TM021 = 348, ItemParam.TM
    TM022 = 349, ItemParam.TM
    TM023 = 350, ItemParam.TM
    TM024 = 351, ItemParam.TM
    TM025 = 352, ItemParam.TM
    TM026 = 353, ItemParam.TM
    TM027 = 354, ItemParam.TM
    TM028 = 355, ItemParam.TM
    TM029 = 356, ItemParam.TM
    TM030 = 357, ItemParam.TM
    TM031 = 358, ItemParam.TM
    TM032 = 359, ItemParam.TM
    TM033 = 360, ItemParam.TM
    TM034 = 361, ItemParam.TM
    TM035 = 362, ItemParam.TM
    TM036 = 363, ItemParam.TM
    TM037 = 364, ItemParam.TM
    TM038 = 365, ItemParam.TM
    TM039 = 366, ItemParam.TM
    TM040 = 367, ItemParam.TM
    TM041 = 368, ItemParam.TM
    TM042 = 369, ItemParam.TM
    TM043 = 370, ItemParam.TM
    TM044 = 371, ItemParam.TM
    TM045 = 372, ItemParam.TM
    TM046 = 373, ItemParam.TM
    TM047 = 374, ItemParam.TM
    TM048 = 375, ItemParam.TM
    TM049 = 376, ItemParam.TM
    TM050 = 377, ItemParam.TM
    TM051 = 378, ItemParam.TM
    TM052 = 379, ItemParam.TM
    TM053 = 380, ItemParam.TM
    TM054 = 381, ItemParam.TM
    TM055 = 382, ItemParam.TM
    TM056 = 383, ItemParam.TM
    TM057 = 384, ItemParam.TM
    TM058 = 385, ItemParam.TM
    TM059 = 386, ItemParam.TM
    TM060 = 387, ItemParam.TM
    TM061 = 388, ItemParam.TM
    TM062 = 389, ItemParam.TM
    TM063 = 390, ItemParam.TM
    TM064 = 391, ItemParam.TM
    TM065 = 392, ItemParam.TM
    TM066 = 393, ItemParam.TM
    TM067 = 394, ItemParam.TM
    TM068 = 395, ItemParam.TM
    TM069 = 396, ItemParam.TM
    TM070 = 397, ItemParam.TM
    TM071 = 398, ItemParam.TM
    TM072 = 399, ItemParam.TM
    TM073 = 400, ItemParam.TM
    TM074 = 401, ItemParam.TM
    TM075 = 402, ItemParam.TM
    TM076 = 403, ItemParam.TM
    TM077 = 404, ItemParam.TM
    TM078 = 405, ItemParam.TM
    TM079 = 406, ItemParam.TM
    TM080 = 407, ItemParam.TM
    TM081 = 408, ItemParam.TM
    TM082 = 409, ItemParam.TM
    TM083 = 410, ItemParam.TM
    TM084 = 411, ItemParam.TM
    TM085 = 412, ItemParam.TM
    TM086 = 413, ItemParam.TM
    TM087 = 414, ItemParam.TM
    TM088 = 415, ItemParam.TM
    TM089 = 416, ItemParam.TM
    TM090 = 417, ItemParam.TM
    TM091 = 418, ItemParam.TM
    TM092 = 419, ItemParam.TM
    
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
    GUIDEBOOK = 433, ItemParam.KEY
    SEAL_CASE = 434, ItemParam.KEY
    FASHION_CASE = 435, ItemParam.KEY
    STICKER_BAG = 436, ItemParam.KEY
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
    BIKE = 450, ItemParam.KEY
    SUITE_KEY = 451, ItemParam.KEY
    OAKS_LETTER = 452, ItemParam.KEY
    LUNAR_FEATHER = 453, ItemParam.KEY
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
    DOWSING_MACHINE = 471, ItemParam.KEY
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
    SILVER_FEATHER = 482, ItemParam.KEY
    RAINBOW_FEATHER = 483, ItemParam.KEY
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

    #GEN V ADDITIONS (reordered :D)
    PRISM_SCALE = 537, ItemParam.EVO
    EVIOLITE = 538, ItemParam.HELD
    FLOAT_STONE = 539, ItemParam.HELD
    ROCKY_HELMET = 540, ItemParam.HELD
    AIR_BALLOON = 541, ItemParam.HELD
    RED_CARD = 542, ItemParam.HELD
    RING_TARGET = 543, ItemParam.HELD
    BINDING_BAND = 544, ItemParam.HELD
    ABSORB_BULB = 545, ItemParam.HELD
    CELL_BATTERY = 546, ItemParam.HELD
    EJECT_BUTTON = 547, ItemParam.HELD
    FIRE_GEM = 548, ItemParam.GEM
    WATER_GEM = 549, ItemParam.GEM
    ELECTRIC_GEM = 550, ItemParam.GEM
    GRASS_GEM = 551, ItemParam.GEM
    ICE_GEM = 552, ItemParam.GEM
    FIGHTING_GEM = 553, ItemParam.GEM
    POISON_GEM = 554, ItemParam.GEM
    GROUND_GEM = 555, ItemParam.GEM
    FLYING_GEM = 556, ItemParam.GEM
    PSYCHIC_GEM = 557, ItemParam.GEM
    BUG_GEM = 558, ItemParam.GEM
    ROCK_GEM = 559, ItemParam.GEM
    GHOST_GEM = 560, ItemParam.GEM
    DRAGON_GEM = 561, ItemParam.GEM
    DARK_GEM = 562, ItemParam.GEM
    STEEL_GEM = 563, ItemParam.GEM
    NORMAL_GEM = 564, ItemParam.GEM

    HEALTH_FEATHER = 565, ItemParam.OBO
    MUSCLE_FEATHER = 566, ItemParam.OBO
    RESIST_FEATHER = 567, ItemParam.OBO
    GENIUS_FEATHER = 568, ItemParam.OBO
    CLEVER_FEATHER = 569, ItemParam.OBO
    SWIFT_FEATHER = 570, ItemParam.OBO
    PRETTY_FEATHER = 571, ItemParam.VAL

    COVER_FOSSIL = 572, ItemParam.VAL
    PLUME_FOSSIL = 573, ItemParam.VAL
    LIBERTY_PASS = 574, ItemParam.VAL
    PASS_ORB = 575, ItemParam.KEY
    DREAM_BALL = 576, ItemParam.BALL
    POKE_TOY = 577, ItemParam.BAT
    PROP_CASE = 578, ItemParam.KEY
    DRAGON_SKULL = 579, ItemParam.KEY
    BALM_MUSHROOM = 580, ItemParam.VAL
    BIG_NUGGET = 581, ItemParam.VAL
    PEARL_STRING = 582, ItemParam.VAL
    COMET_SHARD = 583, ItemParam.VAL
    RELIC_COPPER = 584, ItemParam.VAL
    RELIC_SILVER = 585, ItemParam.VAL
    RELIC_GOLD = 586, ItemParam.VAL
    RELIC_VASE = 587, ItemParam.VAL
    RELIC_BAND = 588, ItemParam.VAL
    RELIC_STATUE = 589, ItemParam.VAL
    RELIC_CROWN = 590, ItemParam.VAL
    CASTELIACONE = 591, ItemParam.MED
   
   #GEN V GARBAGE

    DIRE_HIT_2 = 592, ItemParam.UNIMPL
    X_SPEED_2 = 593, ItemParam.UNIMPL
    X_SP_ATK_2 = 594, ItemParam.UNIMPL
    X_SP_DEF_2 = 595, ItemParam.UNIMPL
    X_DEFENSE_2 = 596, ItemParam.UNIMPL
    X_ATTACK_2 = 597, ItemParam.UNIMPL
    X_ACCURACY_2 = 598, ItemParam.UNIMPL
    X_SPEED_3 = 599, ItemParam.UNIMPL
    X_SP_ATK_3 = 600, ItemParam.UNIMPL
    X_SP_DEF_3 = 601, ItemParam.UNIMPL
    X_DEFENSE_3 = 602, ItemParam.UNIMPL
    X_ATTACK_3 = 603, ItemParam.UNIMPL
    X_ACCURACY_3 = 604, ItemParam.UNIMPL
    X_SPEED_6 = 605, ItemParam.UNIMPL
    X_SP_ATK_6 = 606, ItemParam.UNIMPL
    X_SP_DEF_6 = 607, ItemParam.UNIMPL
    X_DEFENSE_6 = 608, ItemParam.UNIMPL
    X_ATTACK_6 = 609, ItemParam.UNIMPL
    X_ACCURACY_6 = 610, ItemParam.UNIMPL
    ABILITY_URGE = 611, ItemParam.UNIMPL
    ITEM_DROP = 612, ItemParam.UNIMPL
    ITEM_URGE = 613, ItemParam.UNIMPL
    RESET_URGE = 614, ItemParam.UNIMPL
    DIRE_HIT_3 = 615, ItemParam.UNIMPL
    LIGHT_STONE = 616, ItemParam.KEY
    DARK_STONE = 617, ItemParam.KEY
    TM093 = 618, ItemParam.TM
    TM094 = 619, ItemParam.TM
    TM095 = 620, ItemParam.TM
    XTRANSCEIVER_BW = 621, ItemParam.KEY
    UNKNOWN_622 = 622, ItemParam.UNIMPL
    GRAM_1 = 623, ItemParam.KEY
    GRAM_2 = 624, ItemParam.KEY
    GRAM_3 = 625, ItemParam.KEY
    XTRANSCEIVER_BW2 = 626, ItemParam.KEY
    MEDAL_BOX = 627, ItemParam.KEY
    DNA_SPLICERS_FUSE = 628, ItemParam.KEY
    DNA_SPLICERS_UNFUSE = 629, ItemParam.KEY
    PERMIT = 630, ItemParam.KEY
    OVAL_CHARM = 631, ItemParam.KEY
    SHINY_CHARM = 632, ItemParam.KEY
    PLASMA_CARD = 633, ItemParam.KEY
    GRUBBY_HANKY = 634, ItemParam.KEY
    COLRESS_MACHINE = 635, ItemParam.KEY
    DROPPED_ITEM_CURTIS = 636, ItemParam.KEY
    DROPPED_ITEM_YANCY = 637, ItemParam.KEY
    
    REVEAL_GLASS = 638, ItemParam.KEY

    WEAKNESS_POLICY = 639, ItemParam.HELD
    ASSAULT_VEST = 640, ItemParam.HELD
    HOLO_CASTER_MALE = 641, ItemParam.KEY
    PROFS_LETTER = 642, ItemParam.KEY
    ROLLER_SKATES = 643, ItemParam.KEY
    PIXIE_PLATE = 644, ItemParam.HELD
    ABILITY_CAPSULE = 645, ItemParam.OBO
    WHIPPED_DREAM = 646, ItemParam.MED
    SACHET = 647, ItemParam.EVO
    LUMINOUS_MOSS = 648, ItemParam.HELD
    SNOWBALL = 649, ItemParam.HELD
    SAFETY_GOGGLES = 650, ItemParam.HELD
    POKE_FLUTE = 651, ItemParam.KEY
    RICH_MULCH = 652, ItemParam.UNIMPL
    SURPRISE_MULCH = 653, ItemParam.UNIMPL
    BOOST_MULCH = 654, ItemParam.UNIMPL
    AMAZE_MULCH = 655, ItemParam.UNIMPL

    # mega stones 1
    GENGARITE = 656, ItemParam.MEGA
    GARDEVOIRITE = 657, ItemParam.MEGA
    AMPHAROSITE = 658, ItemParam.MEGA
    VENUSAURITE = 659, ItemParam.MEGA
    CHARIZARDITE_X = 660, ItemParam.MEGA
    BLASTOISINITE = 661, ItemParam.MEGA
    MEWTWONITE_X = 662, ItemParam.MEGA
    MEWTWONITE_Y = 663, ItemParam.MEGA
    BLAZIKENITE = 664, ItemParam.MEGA
    MEDICHAMITE = 665, ItemParam.MEGA
    HOUNDOOMINITE = 666, ItemParam.MEGA
    AGGRONITE = 667, ItemParam.MEGA
    BANETTITE = 668, ItemParam.MEGA
    TYRANITARITE = 669, ItemParam.MEGA
    SCIZORITE = 670, ItemParam.MEGA
    PINSIRITE = 671, ItemParam.MEGA
    AERODACTYLITE = 672, ItemParam.MEGA
    LUCARIONITE = 673, ItemParam.MEGA
    ABOMASITE = 674, ItemParam.MEGA
    KANGASKHANITE = 675, ItemParam.MEGA
    GYARADOSITE = 676, ItemParam.MEGA
    ABSOLITE = 677, ItemParam.MEGA
    CHARIZARDITE_Y = 678, ItemParam.MEGA
    ALAKAZITE = 679, ItemParam.MEGA
    HERACRONITE = 680, ItemParam.MEGA
    MAWILITE = 681, ItemParam.MEGA
    MANECTITE = 682, ItemParam.MEGA
    GARCHOMPITE = 683, ItemParam.MEGA
    LATIASITE = 684, ItemParam.MEGA
    LATIOSITE = 685, ItemParam.MEGA

    ROSELI_BERRY = 686, ItemParam.BER
    KEE_BERRY = 687, ItemParam.BER
    MARANGA_BERRY = 688, ItemParam.BER
    SPRINKLOTAD = 689, ItemParam.KEY
    TM096 = 690, ItemParam.TM
    TM097 = 691, ItemParam.TM
    TM098 = 692, ItemParam.TM
    TM099 = 693, ItemParam.TM
    TM100 = 694, ItemParam.TM
    
#GEN VI RANDOM ISH

    POWER_PLANT_PASS = 695, ItemParam.KEY
    MEGA_RING = 696, ItemParam.KEY
    INTRIGUING_STONE = 697, ItemParam.KEY
    COMMON_STONE = 698, ItemParam.KEY
    DISCOUNT_COUPON = 699, ItemParam.KEY
    ELEVATOR_KEY = 700, ItemParam.KEY
    TMV_PASS = 701, ItemParam.KEY
    HONOR_OF_KALOS = 702, ItemParam.KEY
    ADVENTURE_GUIDE = 703, ItemParam.KEY
    STRANGE_SOUVENIR = 704, ItemParam.KEY
    LENS_CASE = 705, ItemParam.KEY
    MAKEUP_BAG = 706, ItemParam.KEY
    TRAVEL_TRUNK = 707, ItemParam.KEY
    LUMIOSE_GALETTE = 708, ItemParam.MED
    SHALOUR_SABLE = 709, ItemParam.MED
    JAW_FOSSIL = 710, ItemParam.VAL
    SAIL_FOSSIL = 711, ItemParam.VAL
    LOOKER_TICKET = 712, ItemParam.KEY
    BIKE_XY = 713, ItemParam.UNIMPL
    HOLO_CASTER_FEMALE = 714, ItemParam.UNIMPL

    FAIRY_GEM = 715, ItemParam.GEM

    MEGA_CHARM = 716, ItemParam.KEY
    MEGA_GLOVE = 717, ItemParam.KEY
    MACH_BIKE = 718, ItemParam.UNIMPL
    ACRO_BIKE = 719, ItemParam.UNIMPL
    WAILMER_PAIL = 720, ItemParam.UNIMPL
    DEVON_PARTS = 721, ItemParam.UNIMPL
    SOOT_SACK = 722, ItemParam.UNIMPL
    BASEMENT_KEY_ORAS = 723, ItemParam.UNIMPL
    POKEBLOCK_KIT = 724, ItemParam.UNIMPL
    LETTER = 725, ItemParam.KEY
    EON_TICKET = 726, ItemParam.KEY
    SCANNER = 727, ItemParam.KEY
    GO_GOGGLES = 728, ItemParam.KEY
    METEORITE_ORAS_DEFAULT = 729, ItemParam.KEY
    KEY_TO_ROOM_1 = 730, ItemParam.KEY
    KEY_TO_ROOM_2 = 731, ItemParam.KEY
    KEY_TO_ROOM_4 = 732, ItemParam.KEY
    KEY_TO_ROOM_6 = 733, ItemParam.KEY
    STORAGE_KEY_HOENN = 734, ItemParam.KEY
    DEVON_SCOPE = 735, ItemParam.KEY
    SS_TICKET_ORAS = 736, ItemParam.KEY
    HM07_ORAS = 737, ItemParam.UNIMPL
    DEVON_SCUBA_GEAR = 738, ItemParam.KEY
    CONTEST_COSTUME_MALE = 739, ItemParam.KEY
    CONTEST_COSTUME_FEMALE = 740, ItemParam.KEY
    MAGMA_SUIT = 741, ItemParam.KEY
    AQUA_SUIT = 742, ItemParam.KEY
    PAIR_OF_TICKETS = 743, ItemParam.KEY
    MEGA_BRACELET = 744, ItemParam.KEY
    MEGA_PENDANT = 745, ItemParam.KEY
    MEGA_GLASSES = 746, ItemParam.KEY
    MEGA_ANCHOR = 747, ItemParam.KEY
    MEGA_STICKPIN = 748, ItemParam.KEY
    MEGA_TIARA = 749, ItemParam.KEY
    MEGA_ANKLET = 750, ItemParam.KEY
    METEORITE_ORAS_SECOND = 751, ItemParam.KEY

# MEGA STONES 2 

    SWAMPERTITE = 752, ItemParam.MEGA
    SCEPTILITE = 753, ItemParam.MEGA
    SABLENITE = 754, ItemParam.MEGA
    ALTARIANITE = 755, ItemParam.MEGA
    GALLADITE = 756, ItemParam.MEGA
    AUDINITE = 757, ItemParam.MEGA
    METAGROSSITE = 758, ItemParam.MEGA
    SHARPEDONITE = 759, ItemParam.MEGA
    SLOWBRONITE = 760, ItemParam.MEGA
    STEELIXITE = 761, ItemParam.MEGA
    PIDGEOTITE = 762, ItemParam.MEGA
    GLALITITE = 763, ItemParam.MEGA
    DIANCITE = 764, ItemParam.MEGA

    PRISON_BOTTLE = 765, ItemParam.KEY
    MEGA_CUFF = 766, ItemParam.KEY

#MEGA STONES 3

    CAMERUPTITE = 767, ItemParam.MEGA
    LOPUNNITE = 768, ItemParam.MEGA
    SALAMENCITE = 769, ItemParam.MEGA
    BEEDRILLITE = 770, ItemParam.MEGA

    METEORITE_ORAS_THIRD = 771, ItemParam.KEY
    METEORITE_ORAS_FINAL = 772, ItemParam.KEY
    KEY_STONE = 773, ItemParam.KEY
    METEORITE_SHARD = 774, ItemParam.KEY
    EON_FLUTE = 775, ItemParam.KEY
    NORMALIUM_Z_HELD = 776, ItemParam.UNIMPL
    FIRIUM_Z_HELD = 777, ItemParam.UNIMPL
    WATERIUM_Z_HELD = 778, ItemParam.UNIMPL
    ELECTRIUM_Z_HELD = 779, ItemParam.UNIMPL
    GRASSIUM_Z_HELD = 780, ItemParam.UNIMPL
    ICIUM_Z_HELD = 781, ItemParam.UNIMPL
    FIGHTINIUM_Z_HELD = 782, ItemParam.UNIMPL
    POISONIUM_Z_HELD = 783, ItemParam.UNIMPL
    GROUNDIUM_Z_HELD = 784, ItemParam.UNIMPL
    FLYINIUM_Z_HELD = 785, ItemParam.UNIMPL
    PSYCHIUM_Z_HELD = 786, ItemParam.UNIMPL
    BUGINIUM_Z_HELD = 787, ItemParam.UNIMPL
    ROCKIUM_Z_HELD = 788, ItemParam.UNIMPL
    GHOSTIUM_Z_HELD = 789, ItemParam.UNIMPL
    DRAGONIUM_Z_HELD = 790, ItemParam.UNIMPL
    DARKINIUM_Z_HELD = 791, ItemParam.UNIMPL
    STEELIUM_Z_HELD = 792, ItemParam.UNIMPL
    FAIRIUM_Z_HELD = 793, ItemParam.UNIMPL
    PIKANIUM_Z_HELD = 794, ItemParam.UNIMPL

    BOTTLE_CAP = 795, ItemParam.OBO
    GOLD_BOTTLE_CAP = 796, ItemParam.OBO

#gen VII stuff

    Z_RING = 797, ItemParam.UNIMPL
    DECIDIUM_Z_HELD = 798, ItemParam.UNIMPL
    INCINIUM_Z_HELD = 799, ItemParam.UNIMPL
    PRIMARIUM_Z_HELD = 800, ItemParam.UNIMPL
    TAPUNIUM_Z_HELD = 801, ItemParam.UNIMPL
    MARSHADIUM_Z_HELD = 802, ItemParam.UNIMPL
    ALORAICHIUM_Z_HELD = 803, ItemParam.UNIMPL
    SNORLIUM_Z_HELD = 804, ItemParam.UNIMPL
    EEVIUM_Z_HELD = 805, ItemParam.UNIMPL
    MEWNIUM_Z_HELD = 806, ItemParam.UNIMPL
    NORMALIUM_Z_BAG = 807, ItemParam.UNIMPL
    FIRIUM_Z_BAG = 808, ItemParam.UNIMPL
    WATERIUM_Z_BAG = 809, ItemParam.UNIMPL
    ELECTRIUM_Z_BAG = 810, ItemParam.UNIMPL
    GRASSIUM_Z_BAG = 811, ItemParam.UNIMPL
    ICIUM_Z_BAG = 812, ItemParam.UNIMPL
    FIGHTINIUM_Z_BAG = 813, ItemParam.UNIMPL
    POISONIUM_Z_BAG = 814, ItemParam.UNIMPL
    GROUNDIUM_Z_BAG = 815, ItemParam.UNIMPL
    FLYINIUM_Z_BAG = 816, ItemParam.UNIMPL
    PSYCHIUM_Z_BAG = 817, ItemParam.UNIMPL
    BUGINIUM_Z_BAG = 818, ItemParam.UNIMPL
    ROCKIUM_Z_BAG = 819, ItemParam.UNIMPL
    GHOSTIUM_Z_BAG = 820, ItemParam.UNIMPL
    DRAGONIUM_Z_BAG = 821, ItemParam.UNIMPL
    DARKINIUM_Z_BAG = 822, ItemParam.UNIMPL
    STEELIUM_Z_BAG = 823, ItemParam.UNIMPL
    FAIRIUM_Z_BAG = 824, ItemParam.UNIMPL
    PIKANIUM_Z_BAG = 825, ItemParam.UNIMPL
    DECIDIUM_Z_BAG = 826, ItemParam.UNIMPL
    INCINIUM_Z_BAG = 827, ItemParam.UNIMPL
    PRIMARIUM_Z_BAG = 828, ItemParam.UNIMPL
    TAPUNIUM_Z_BAG = 829, ItemParam.UNIMPL
    MARSHADIUM_Z_BAG = 830, ItemParam.UNIMPL
    ALORAICHIUM_Z_BAG = 831, ItemParam.UNIMPL
    SNORLIUM_Z_BAG = 832, ItemParam.UNIMPL
    EEVIUM_Z_BAG = 833, ItemParam.UNIMPL
    MEWNIUM_Z_BAG = 834, ItemParam.UNIMPL
    PIKASHUNIUM_Z_HELD = 835, ItemParam.UNIMPL
    PIKASHUNIUM_Z_BAG = 836, ItemParam.UNIMPL
    
    UNKNOWN_837 = 837, ItemParam.UNIMPL
    UNKNOWN_838 = 838, ItemParam.UNIMPL
    UNKNOWN_839 = 839, ItemParam.UNIMPL
    UNKNOWN_840 = 840, ItemParam.UNIMPL

    FORAGE_BAG = 841, ItemParam.UNIMPL
    FISHING_ROD_SM = 842, ItemParam.UNIMPL
    PROFESSORS_MASK = 843, ItemParam.UNIMPL
    FESTIVAL_TICKET = 844, ItemParam.UNIMPL
    SPARKLING_STONE = 845, ItemParam.UNIMPL

    ADRENALINE_ORB = 846, ItemParam.HELD
    
    ZYGARDE_CUBE = 847, ItemParam.UNIMPL
    UNKNOWN_848 = 848, ItemParam.UNIMPL

    ICE_STONE = 849, ItemParam.EVO
    RIDE_PAGER = 850, ItemParam.KEY
    BEAST_BALL = 851, ItemParam.EXTRA

    BIG_MALASADA = 852, ItemParam.MED

    RED_NECTAR = 853, ItemParam.OBO
    YELLOW_NECTAR = 854, ItemParam.OBO
    PINK_NECTAR = 855, ItemParam.OBO
    PURPLE_NECTAR = 856, ItemParam.OBO

    SUN_FLUTE = 857, ItemParam.KEY
    MOON_FLUTE = 858, ItemParam.KEY
    ENIGMATIC_CARD = 859, ItemParam.KEY


#HERE is where I stopped porting over every single item and started cherry-picking the ones that are actually in our game

#SM items

    TERRAIN_EXTENDER = 879, ItemParam.HELD
    PROTECTIVE_PADS = 880, ItemParam.HELD
    ELECTRIC_SEED = 881, ItemParam.HELD
    PSYCHIC_SEED = 882, ItemParam.HELD
    MISTY_SEED = 883, ItemParam.HELD
    GRASSY_SEED = 884, ItemParam.HELD

#lets go items

    FIGHTING_MEMORY = 904, ItemParam.UNIMPL
    FLYING_MEMORY = 905, ItemParam.UNIMPL
    POISON_MEMORY = 906, ItemParam.UNIMPL
    GROUND_MEMORY = 907, ItemParam.UNIMPL
    ROCK_MEMORY = 908, ItemParam.UNIMPL
    BUG_MEMORY = 909, ItemParam.UNIMPL
    GHOST_MEMORY = 910, ItemParam.UNIMPL
    STEEL_MEMORY = 911, ItemParam.UNIMPL
    FIRE_MEMORY = 912, ItemParam.UNIMPL
    WATER_MEMORY = 913, ItemParam.UNIMPL
    GRASS_MEMORY = 914, ItemParam.UNIMPL
    ELECTRIC_MEMORY = 915, ItemParam.UNIMPL
    PSYCHIC_MEMORY = 916, ItemParam.UNIMPL
    ICE_MEMORY = 917, ItemParam.UNIMPL
    DRAGON_MEMORY = 918, ItemParam.UNIMPL
    DARK_MEMORY = 919, ItemParam.UNIMPL
    FAIRY_MEMORY = 920, ItemParam.UNIMPL

#Some other z crystals, SM stuff, GO stuff

#GEn VIII stuff


    BERRY_SWEET = 1111, ItemParam.EVO
    CLOVER_SWEET = 1112, ItemParam.EVO
    FLOWER_SWEET = 1113, ItemParam.EVO
    LOVE_SWEET = 1110, ItemParam.EVO
    RIBBON_SWEET = 1115, ItemParam.EVO
    STAR_SWEET = 1114, ItemParam.EVO
    STRAWBERRY_SWEET = 1109, ItemParam.EVO
    SWEET_APPLE = 1116, ItemParam.EVO
    TART_APPLE = 1117, ItemParam.EVO
    THROAT_SPRAY = 1118, ItemParam.HELD
    EJECT_PACK = 1119, ItemParam.HELD
    HEAVY_DUTY_BOOTS = 1120, ItemParam.HELD
    BLUNDER_POLICY = 1121, ItemParam.HELD
    ROOM_SERVICE = 1122, ItemParam.HELD

    UTILITY_UMBRELLA = 1123, ItemParam.HELD

# TRs and other Gen VIII stuff
#Mints
    LONELY_MINT = 1231, ItemParam.OBO
    ADAMANT_MINT = 1232, ItemParam.OBO
    NAUGHTY_MINT = 1233, ItemParam.OBO
    BRAVE_MINT = 1234, ItemParam.OBO
    BOLD_MINT = 1235, ItemParam.OBO
    IMPISH_MINT = 1236, ItemParam.OBO
    LAX_MINT = 1237, ItemParam.OBO
    RELAXED_MINT = 1238, ItemParam.OBO
    MODEST_MINT = 1239, ItemParam.OBO
    MILD_MINT = 1240, ItemParam.OBO
    RASH_MINT = 1241, ItemParam.OBO
    QUIET_MINT = 1242, ItemParam.OBO
    CALM_MINT = 1243, ItemParam.OBO
    GENTLE_MINT = 1244, ItemParam.OBO
    CAREFUL_MINT = 1245, ItemParam.OBO
    SASSY_MINT = 1246, ItemParam.OBO
    TIMID_MINT = 1247, ItemParam.OBO
    HASTY_MINT = 1248, ItemParam.OBO
    JOLLY_MINT = 1249, ItemParam.OBO
    NAIVE_MINT = 1250, ItemParam.OBO
    SERIOUS_MINT = 1251, ItemParam.OBO
  





    CHIPPED_POT = 1254, ItemParam.EVO
    CRACKED_POT = 1253, ItemParam.EVO

    ROTOM_CATALOG = 1278, ItemParam.KEY

    GALARICA_CUFF = 1581, ItemParam.EVO
    GALARICA_WREATH = 1592, ItemParam.EVO

    ABILITY_PATCH = 1606, ItemParam.HELD

    LINKING_CORD = 1611, ItemParam.EVO

    #RECIPES GEN VIII, PLA STUFF
    
    #GEN VII CONT'D

    BLACK_AUGURITE = 1691, ItemParam.EVO
    PEAT_BLOCK = 1692, ItemParam.EVO

    ADAMANT_CRYSTAL = 1777, ItemParam.HELD
    LUSTROUS_GLOBE = 1778, ItemParam.HELD    
    GRISEOUS_CORE = 1779, ItemParam.HELD
 
 #GEN IX STUFF, TERA SHARDS ETC

 #GEN IX ITEMS INCL

    BOOSTER_ENERGY = 1880, ItemParam.HELD
    ABILITY_SHIELD = 1881, ItemParam.HELD
    CLEAR_AMULET = 1882, ItemParam.HELD
    MIRROR_HERB = 1883, ItemParam.HELD
    PUNCHING_GLOVE = 1884, ItemParam.HELD
    COVERT_CLOAK = 1885, ItemParam.HELD
    LOADED_DICE = 1886, ItemParam.HELD

    TM101 = 2161, ItemParam.TM
    TM102 = 2162, ItemParam.TM
    TM103 = 2163, ItemParam.TM
    TM104 = 2164, ItemParam.TM
    TM105 = 2165, ItemParam.TM
    TM106 = 2166, ItemParam.TM
    TM107 = 2167, ItemParam.TM
    TM108 = 2168, ItemParam.TM
    TM109 = 2169, ItemParam.TM
    TM110 = 2170, ItemParam.TM
    TM111 = 2171, ItemParam.TM
    TM112 = 2172, ItemParam.TM
    TM113 = 2173, ItemParam.TM
    TM114 = 2174, ItemParam.TM
    TM115 = 2175, ItemParam.TM
    TM116 = 2176, ItemParam.TM
    TM117 = 2177, ItemParam.TM
    TM118 = 2178, ItemParam.TM
    TM119 = 2179, ItemParam.TM
    TM120 = 2180, ItemParam.TM
    TM121 = 2181, ItemParam.TM
    TM122 = 2182, ItemParam.TM
    TM123 = 2183, ItemParam.TM
    TM124 = 2184, ItemParam.TM
    TM125 = 2185, ItemParam.TM
    TM126 = 2186, ItemParam.TM
    TM127 = 2187, ItemParam.TM
    TM128 = 2188, ItemParam.TM
    TM129 = 2189, ItemParam.TM
    TM130 = 2190, ItemParam.TM
    TM131 = 2191, ItemParam.TM
    TM132 = 2192, ItemParam.TM
    TM133 = 2193, ItemParam.TM
    TM134 = 2194, ItemParam.TM
    TM135 = 2195, ItemParam.TM
    TM136 = 2196, ItemParam.TM
    TM137 = 2197, ItemParam.TM
    TM138 = 2198, ItemParam.TM
    TM139 = 2199, ItemParam.TM
    TM140 = 2200, ItemParam.TM
    TM141 = 2201, ItemParam.TM
    TM142 = 2202, ItemParam.TM
    TM143 = 2203, ItemParam.TM
    TM144 = 2204, ItemParam.TM
    TM145 = 2205, ItemParam.TM
    TM146 = 2206, ItemParam.TM
    TM147 = 2207, ItemParam.TM
    TM148 = 2208, ItemParam.TM
    TM149 = 2209, ItemParam.TM
    TM150 = 2210, ItemParam.TM
    TM151 = 2211, ItemParam.TM
    TM152 = 2212, ItemParam.TM
    TM153 = 2213, ItemParam.TM
    TM154 = 2214, ItemParam.TM
    TM155 = 2215, ItemParam.TM
    TM156 = 2216, ItemParam.TM
    TM157 = 2217, ItemParam.TM
    TM158 = 2218, ItemParam.TM
    TM159 = 2219, ItemParam.TM
    TM160 = 2220, ItemParam.TM
    TM161 = 2221, ItemParam.TM
    TM162 = 2222, ItemParam.TM
    TM163 = 2223, ItemParam.TM
    TM164 = 2224, ItemParam.TM
    TM165 = 2225, ItemParam.TM
    TM166 = 2226, ItemParam.TM
    TM167 = 2227, ItemParam.TM
    TM168 = 2228, ItemParam.TM
    TM169 = 2229, ItemParam.TM
    TM170 = 2230, ItemParam.TM
    TM171 = 2231, ItemParam.TM
    TM172 = 2232, ItemParam.TM
    TM173 = 2233, ItemParam.TM
    TM174 = 2234, ItemParam.TM
    TM175 = 2235, ItemParam.TM
    TM176 = 2236, ItemParam.TM
    TM177 = 2237, ItemParam.TM
    TM178 = 2238, ItemParam.TM
    TM179 = 2239, ItemParam.TM
    TM180 = 2240, ItemParam.TM
    TM181 = 2241, ItemParam.TM
    TM182 = 2242, ItemParam.TM
    TM183 = 2243, ItemParam.TM
    TM184 = 2244, ItemParam.TM
    TM185 = 2245, ItemParam.TM
    TM186 = 2246, ItemParam.TM
    TM187 = 2247, ItemParam.TM
    TM188 = 2248, ItemParam.TM
    TM189 = 2249, ItemParam.TM
    TM190 = 2250, ItemParam.TM
    TM191 = 2251, ItemParam.TM
    TM192 = 2252, ItemParam.TM
    TM193 = 2253, ItemParam.TM
    TM194 = 2254, ItemParam.TM
    TM195 = 2255, ItemParam.TM
    TM196 = 2256, ItemParam.TM
    TM197 = 2257, ItemParam.TM
    TM198 = 2258, ItemParam.TM
    TM199 = 2259, ItemParam.TM
    TM200 = 2260, ItemParam.TM
    TM201 = 2261, ItemParam.TM
    TM202 = 2262, ItemParam.TM
    TM203 = 2263, ItemParam.TM
    TM204 = 2264, ItemParam.TM
    TM205 = 2265, ItemParam.TM
    TM206 = 2266, ItemParam.TM
    TM207 = 2267, ItemParam.TM
    TM208 = 2268, ItemParam.TM
    TM209 = 2269, ItemParam.TM
    TM210 = 2270, ItemParam.TM
    TM211 = 2271, ItemParam.TM
    TM212 = 2272, ItemParam.TM
    TM213 = 2273, ItemParam.TM
    TM214 = 2274, ItemParam.TM
    TM215 = 2275, ItemParam.TM
    TM216 = 2276, ItemParam.TM
    TM217 = 2277, ItemParam.TM
    TM218 = 2278, ItemParam.TM
    TM219 = 2279, ItemParam.TM
    TM220 = 2280, ItemParam.TM
    TM221 = 2281, ItemParam.TM
    TM222 = 2282, ItemParam.TM
    TM223 = 2283, ItemParam.TM
    TM224 = 2284, ItemParam.TM
    TM225 = 2285, ItemParam.TM
    TM226 = 2286, ItemParam.TM
    TM227 = 2287, ItemParam.TM
    TM228 = 2288, ItemParam.TM
    TM229 = 2289, ItemParam.TM
 







    
    

    











    
    
    # Generation IX items
    AUSPICIOUS_ARMOR = 2344, ItemParam.EVO
    LEADERS_CREST = 2345, ItemParam.UNIMPL
    MALICIOUS_ARMOR = 1861, ItemParam.EVO
    
    
    








    #GEN IX DLC

    FAIRY_FEATHER = 2401, ItemParam.HELD
    SYRUPY_APPLE = 2402, ItemParam.EVO
    UNREMARKABLE_TEACUP = 2403, ItemParam.EVO
    MASTERPIECE_TEACUP = 2404, ItemParam.EVO
    CORNERSTONE_MASK = 2406, ItemParam.UNIMPL
    WELLSPRING_MASK = 2407, ItemParam.UNIMPL
    HEARTHFLAME_MASK = 2408, ItemParam.UNIMPL
    METAL_ALLOY = 2482, ItemParam.EVO