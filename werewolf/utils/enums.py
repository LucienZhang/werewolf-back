from enum import Enum, unique


@unique
class GameEnum(Enum):
    def __new__(cls, value, label):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj

    def __bool__(self):
        return self is GameEnum.OK

    def digest(self, *args, **kwargs):
        return {'code': self.value, 'msg': self.label.format(*args), **kwargs}

    # negative positions
    TARGET_NOT_ACTED = (-2, '未行动')
    TARGET_NO_ONE = (-1, '无目标')

    # 0
    OK = (1, 'OK')

    # 100
    VICTORY_MODE_UNKNOWN = (100, '未知胜利模式')
    VICTORY_MODE_KILL_GROUP = (101, '屠边')
    VICTORY_MODE_KILL_ALL = (102, '屠城')
    # 200
    CAPTAIN_MODE_UNKNOWN = (200, '未知警长模式')
    CAPTAIN_MODE_WITH_CAPTAIN = (201, '有警长')
    CAPTAIN_MODE_WITHOUT_CAPTAIN = (202, '没有警长')
    # 300
    WITCH_MODE_UNKNOWN = (300, '未知女巫模式')
    WITCH_MODE_CAN_SAVE_SELF = (301, '全程可以自救')
    WITCH_MODE_FIRST_NIGHT_ONLY = (302, '仅首夜可以自救')
    WITCH_MODE_CANNOT_SAVE_SELF = (303, '全程不可自救')
    # 400
    ROLE_TYPE_UNKNOWN = (400, '未知角色')
    ROLE_TYPE_SEER = (401, '预言家')
    ROLE_TYPE_HUNTER = (402, '猎人')
    ROLE_TYPE_CUPID = (403, '丘比特')
    ROLE_TYPE_WITCH = (404, '女巫')
    ROLE_TYPE_LITTLE_GIRL = (405, '小女孩')
    ROLE_TYPE_THIEF = (406, '盗贼')
    ROLE_TYPE_VILLAGER = (407, '普通村民')
    ROLE_TYPE_NORMAL_WOLF = (408, '普通狼人')
    ROLE_TYPE_IDIOT = (409, '白痴')
    ROLE_TYPE_ANCIENT = (410, '长老')
    ROLE_TYPE_SCAPEGOAT = (411, '替罪羊')
    ROLE_TYPE_SAVIOR = (412, '守卫')
    ROLE_TYPE_PIPER = (413, '吹笛者')
    ROLE_TYPE_WHITE_WOLF = (414, '白狼王')
    ROLE_TYPE_RAVEN = (415, '乌鸦')
    ROLE_TYPE_PYROMANIAC = (416, '火狼')
    ROLE_TYPE_TWO_SISTERS = (417, '两姐妹')
    ROLE_TYPE_THREE_BROTHERS = (418, '三兄弟')
    ROLE_TYPE_ANGEL = (419, '天使')
    # 500
    GROUP_TYPE_UNKNOWN = (500, '未知阵营')
    GROUP_TYPE_WOLVES = (501, '狼人')
    GROUP_TYPE_GODS = (502, '神阵营')
    GROUP_TYPE_VILLAGERS = (503, '民阵营')
    GROUP_TYPE_THIRD_PARTY = (504, '第三方阵营')
    GROUP_TYPE_GOOD = (505, '好人')
    # 600
    TURN_STEP_UNKNOWN = (600, '未知阶段')
    TURN_STEP_DEAL = (601, '发牌')
    TURN_STEP_TURN_NIGHT = (602, '入夜')
    TURN_STEP_TURN_DAY = (603, '天亮')
    TURN_STEP_ELECT = (604, '竞选')  # 上警
    TURN_STEP_ELECT_TALK = (605, '竞选发言')
    TURN_STEP_ELECT_VOTE = (606, '竞选投票')
    TURN_STEP_ELECT_PK_TALK = (607, '竞选PK发言')
    TURN_STEP_ELECT_PK_VOTE = (608, '竞选PK投票')
    TURN_STEP_TALK = (609, '发言')
    TURN_STEP_VOTE = (610, '投票')
    TURN_STEP_PK_TALK = (611, 'PK发言')
    TURN_STEP_PK_VOTE = (612, 'PK投票')
    TURN_STEP_ANNOUNCE = (613, '公布结果')
    TURN_STEP_LAST_WORDS = (614, '遗言')
    TURN_STEP_USE_SKILLS = (615, '使用技能')

    # 700
    GAME_MESSAGE_GAME_NOT_EXIST = (700, '房间不存在')
    GAME_MESSAGE_GAME_FULL = (701, '房间已满')
    GAME_MESSAGE_ALREADY_IN = (702, '你已在游戏中')
    GAME_MESSAGE_ROLE_NOT_EXIST = (703, '角色不存在')
    GAME_MESSAGE_NOT_IN_GAME = (704, '你不在游戏中')
    GAME_MESSAGE_CANNOT_START = (705, '玩家不足，无法开始')
    GAME_MESSAGE_UNKNOWN_OP = (706, '未知命令')
    # GAME_MESSAGE_DIE_IN_NIGHT = (707, '昨晚，以下位置的玩家倒下了，不分先后： {}')
    GAME_MESSAGE_ALREADY_STARTED = (708, '游戏已经开始了')
    GAME_MESSAGE_POSITION_OCCUPIED = (709, '那个位置已经有人了')
    GAME_MESSAGE_CANNOT_ACT = (710, '当前无法操作')
    GAME_MESSAGE_WRONG_PASSWORD = (711, '用户名或密码错误')
    GAME_MESSAGE_USER_EXISTS = (712, '用户名已存在')
    GAME_MESSAGE_NOT_VOTED_YET = (713, '仍有玩家未投票：{}')

    # 800
    SKILL_VOTE = (800, '投票')
    SKILL_WOLF_KILL = (801, '狼刀')
    SKILL_DISCOVER = (802, '查验')
    SKILL_WITCH = (803, '用药')
    SKILL_GUARD = (804, '守护')
    SKILL_SHOOT = (805, '开枪')
    SKILL_SUICIDE = (806, '自爆')
    SKILL_TOXIC = (807, '毒杀')
    SKILL_CAPTAIN = (808, '警长相关')

    # 900
    TAG_ELECT = (900, '上警')
    TAG_NOT_ELECT = (901, '不上警')
    TAG_GIVE_UP_ELECT = (902, '退水')

    # 1000
    WOLF_MODE_FIRST = (1000, '第一狼刀有效')
    WOLF_MODE_ALL = (1001, '所有狼刀相同有效')

    # 1100
    TAG_ATTACKABLE_WOLF = (1100, '带刀狼')

    # 1200
    STEP_FLAG_AUTO_MOVE_ON = (1200, '自动下一步')
    STEP_FLAG_WAIT_FOR_ACTION = (1201, '等待玩家操作')

    # 1300
    GAME_TIMEOUT_RANDOM_FROM = (1300, 12)
    GAME_TIMEOUT_RANDOM_TO = (1301, 15)

    # 1400
    GAME_STATUS_UNKNOWN = (1400, '未知状态')
    GAME_STATUS_WAIT_TO_START = (1401, '等待开始')
    GAME_STATUS_READY = (1402, '游戏已准备好')
    GAME_STATUS_DAY = (1403, '白天')
    GAME_STATUS_NIGHT = (1404, '夜晚')
    GAME_STATUS_FINISHED = (1405, '游戏已结束')

    # 1500
    CONNECTION_WS_4001_NOT_IN_GAME = (1500, 4001)
