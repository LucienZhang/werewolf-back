from datetime import datetime, timedelta
from typing import List
import json
import collections
import logging
import random
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy import func
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Session
from werewolf.utils.enums import GameEnum
from werewolf.schemas.schema_out import ResponseBase
from werewolf.websocket.websocket import publish_info, publish_history, publish_music
from .role import Role
from werewolf.utils.game_exceptions import GameFinished


from .base import Base, EnumType, JSONEncodedType


class Game(Base):
    gid = Column(Integer, primary_key=True, autoincrement=True)
    host_uid = Column(Integer, nullable=False)
    status = Column(EnumType, nullable=False)
    victory_mode = Column(EnumType, nullable=False)
    captain_mode = Column(EnumType, nullable=False)
    witch_mode = Column(EnumType, nullable=False)
    wolf_mode = Column(EnumType, nullable=False)
    end_time = Column(DateTime, nullable=False)
    # updated_on = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    players = Column(MutableList.as_mutable(JSONEncodedType(225)), nullable=False)
    cards = Column(MutableList.as_mutable(JSONEncodedType(1023)), nullable=False)
    days = Column(Integer, nullable=False)
    now_index = Column(Integer, nullable=False)
    step_cnt = Column(Integer, nullable=False)
    steps = Column(MutableList.as_mutable(JSONEncodedType(1023)), nullable=False)
    history = Column(MutableDict.as_mutable(JSONEncodedType(1023)), nullable=False)
    captain_pos = Column(Integer, nullable=False)

    @staticmethod
    def get_wolf_mode_by_cards(cards: List[GameEnum]) -> GameEnum:
        # WOLF_MODE_FIRST if there is no thrid party, else WOLF_MODE_ALL
        if GameEnum.ROLE_TYPE_CUPID in cards:
            return GameEnum.WOLF_MODE_ALL
        else:
            return GameEnum.WOLF_MODE_FIRST

    def init_game(self):
        self.status = GameEnum.GAME_STATUS_WAIT_TO_START
        self.end_time = datetime.utcnow() + timedelta(days=1)
        self.days = 0
        self.now_index = -1
        self.step_cnt = 0
        self.steps = []
        self.history = {}
        self.captain_pos = -1
        self.players = []
        self.reset_history()

    def reset_history(self):
        """
            pos: -1=no one, -2=not acted
            {
                'wolf_kill':{wolf_pos:target_pos,...},
                'wolf_kill_decision':pos,
                'elixir':True / False,
                'guard':pos,
                'toxic':pos,
                'discover':pos,
                'voter_votee':[[voter_pos,...],[votee_pos,...]],
                'vote_result': {voter_pos:votee_pos,...},
                'dying':{pos:True},
            }
        """
        self.history = {
            'wolf_kill': {},
            'wolf_kill_decision': GameEnum.TARGET_NOT_ACTED.value,
            'elixir': False,
            'guard': GameEnum.TARGET_NOT_ACTED.value,
            'toxic': GameEnum.TARGET_NOT_ACTED.value,
            'discover': GameEnum.TARGET_NOT_ACTED.value,
            'voter_votee': [[], []],
            'vote_result': {},
            'dying': {},
        }

    def get_seats_cnt(self):
        cnt = len(self.cards)
        if GameEnum.ROLE_TYPE_THIEF in self.cards:
            cnt -= 2
        return cnt

    def move_on(self, db: Session) -> ResponseBase:
        step_flag = GameEnum.STEP_FLAG_AUTO_MOVE_ON
        while step_flag is GameEnum.STEP_FLAG_AUTO_MOVE_ON:
            leave_result = self._leave_step(db)
            if leave_result['code'] != GameEnum.OK.value:
                return leave_result

            self.step_cnt += 1
            self.now_index += 1
            if self.now_index >= len(self.steps):
                self.now_index = 0
                self.days += 1
                self._init_steps()

            step_flag = self._enter_step(db)
        instruction_string = self.get_instruction_string()
        if instruction_string:
            publish_info(self.gid, json.dumps({
                'game': {
                    'next_step': instruction_string
                },
                'mutation': 'SOCKET_GAME'
            }))
        # try:
        # except GameFinished:
        #     pass  # todo game finished
        return GameEnum.OK.digest()

    def _leave_step(self, db: Session) -> ResponseBase:
        now = self.current_step()
        if now is None:
            return GameEnum.OK.digest()
        if now is GameEnum.TURN_STEP_ELECT:
            roles = db.query(Role).filter(Role.gid == self.gid).limit(len(self.players)).all()
            for r in roles:
                if GameEnum.TAG_ELECT not in r.tags and GameEnum.TAG_NOT_ELECT not in r.tags:
                    r.tags.append(GameEnum.TAG_NOT_ELECT)

            voters = []
            votees = []
            for r in roles:
                if not r.alive:
                    continue
                if GameEnum.TAG_ELECT in r.tags:
                    votees.append(r.position)
                else:
                    voters.append(r.position)
            voters.sort()
            votees.sort()

            if not voters or not votees:
                # no captain
                while self.now_index + 1 < len(self.steps) and self.steps[self.now_index + 1] in {GameEnum.TURN_STEP_ELECT_TALK, GameEnum.TURN_STEP_ELECT_VOTE}:  # noqa E501
                    self.steps.pop(self.now_index + 1)
                if not voters:
                    publish_history(self.gid, '所有人都竞选警长，本局游戏无警长')
                else:
                    publish_history(self.gid, '没有人竞选警长，本局游戏无警长')
            elif len(votees) == 1:
                # auto win captain
                while self.now_index + 1 < len(self.steps) and self.steps[self.now_index + 1] in {GameEnum.TURN_STEP_ELECT_TALK, GameEnum.TURN_STEP_ELECT_VOTE}:  # noqa E501
                    self.steps.pop(self.now_index + 1)
                captain_pos = votees[0]
                self.captain_pos = captain_pos
                publish_history(self.gid, f'只有{captain_pos}号玩家竞选警长，自动当选')
            else:
                publish_history(self.gid, f"竞选警长的玩家为：{','.join(map(str,votees))}\n未竞选警长的玩家为：{','.join(map(str,voters))}")
                self.history['voter_votee'] = [voters, votees]
            return GameEnum.OK.digest()
        elif now in [GameEnum.TURN_STEP_VOTE, GameEnum.TURN_STEP_ELECT_VOTE, GameEnum.TURN_STEP_PK_VOTE, GameEnum.TURN_STEP_ELECT_PK_VOTE]:
            msg = ""
            announce_result = collections.defaultdict(list)
            ticket_cnt = collections.defaultdict(int)
            forfeit = []
            most_voted = []
            max_ticket = 0
            for voter_pos, votee_pos in self.history['vote_result'].items():
                voter_pos = int(voter_pos)
                votee_pos = int(votee_pos)
                if votee_pos in [GameEnum.TARGET_NOT_ACTED.value, GameEnum.TARGET_NO_ONE.value]:
                    forfeit.append(voter_pos)
                    continue
                announce_result[votee_pos].append(voter_pos)
                ticket_cnt[votee_pos] += 1
                if voter_pos == self.captain_pos:
                    ticket_cnt[votee_pos] += 0.5
            for voter in self.history['voter_votee'][0]:
                if str(voter) not in self.history['vote_result']:
                    forfeit.append(voter)
            forfeit.sort()
            if forfeit and now in [GameEnum.TURN_STEP_PK_VOTE, GameEnum.TURN_STEP_ELECT_PK_VOTE]:
                return GameEnum.GAME_MESSAGE_NOT_VOTED_YET.digest(*forfeit)
            for votee, voters in sorted(announce_result.items()):
                msg += '{} <= {}\n'.format(votee, ','.join(map(str, voters)))
            if forfeit:
                msg += '弃票：{}\n'.format(','.join(map(str, forfeit)))

            if not ticket_cnt:
                most_voted = self.history['voter_votee'][1]
            else:
                ticket_cnt = sorted(ticket_cnt.items(), key=lambda x: x[1], reverse=True)
                most_voted.append(ticket_cnt[0][0])
                max_ticket = ticket_cnt[0][1]
                for votee, ticket in ticket_cnt[1:]:
                    if ticket == max_ticket:
                        most_voted.append(votee)
                    else:
                        break
            most_voted.sort()

            if len(most_voted) == 1:
                if now in [GameEnum.TURN_STEP_VOTE, GameEnum.TURN_STEP_PK_VOTE]:
                    msg += f'{most_voted[0]}号玩家以{max_ticket}票被公投出局'
                    publish_history(self.gid, msg)
                    self._kill(db, most_voted[0], GameEnum.SKILL_VOTE)
                else:
                    self.captain_pos = most_voted[0]
                    msg += f'{most_voted[0]}号玩家以{max_ticket}票当选警长'
                    publish_history(self.gid, msg)
                return GameEnum.OK.digest()
            else:
                # 平票
                if now in [GameEnum.TURN_STEP_VOTE, GameEnum.TURN_STEP_ELECT_VOTE]:  # todo 全体进入PK
                    if now is GameEnum.TURN_STEP_VOTE:
                        self.steps.insert(self.now_index + 1, GameEnum.TURN_STEP_PK_TALK)
                        self.steps.insert(self.now_index + 2, GameEnum.TURN_STEP_PK_VOTE)
                    else:
                        self.steps.insert(self.now_index + 1, GameEnum.TURN_STEP_ELECT_PK_TALK)
                        self.steps.insert(self.now_index + 2, GameEnum.TURN_STEP_ELECT_PK_VOTE)
                    votees = most_voted
                    voters = []
                    roles = db.query(Role).filter(Role.gid == self.gid).limit(len(self.players)).all()
                    for r in roles:
                        if r.alive and r.voteable and r.position not in votees:
                            voters.append(r.position)
                    self.history['voter_votee'] = [voters, votees]
                    msg += '以下玩家以{}票平票进入PK：{}'.format(max_ticket, ','.join(map(str, votees)))
                    publish_history(self.gid, msg)
                    return GameEnum.OK.digest()
                else:
                    msg += '以下玩家以{}票再次平票：{}\n'.format(max_ticket, ','.join(map(str, most_voted)))
                    if now is GameEnum.TURN_STEP_PK_VOTE:
                        msg += '今天是平安日，无人被公投出局'
                        while self.now_index + 1 < len(self.steps) and self.steps[self.now_index + 1] is GameEnum.TURN_STEP_LAST_WORDS:
                            self.steps.pop(self.now_index + 1)
                    else:
                        msg += '警徽流失，本局游戏无警长'
                    publish_history(self.gid, msg)
                    return GameEnum.OK.digest()
        elif now is GameEnum.TAG_ATTACKABLE_WOLF:
            publish_music(self.gid, 'wolf_end_voice', None, False)
            return GameEnum.OK.digest()
        elif now is GameEnum.ROLE_TYPE_SEER:
            publish_music(self.gid, 'seer_end_voice', None, False)
            return GameEnum.OK.digest()
        elif now is GameEnum.ROLE_TYPE_WITCH:
            publish_music(self.gid, 'witch_end_voice', None, False)
            return GameEnum.OK.digest()
        elif now is GameEnum.ROLE_TYPE_SAVIOR:
            publish_music(self.gid, 'savior_end_voice', None, False)
            return GameEnum.OK.digest()
        elif now is GameEnum.TURN_STEP_ANNOUNCE:
            # for d in self.history['dying']:
            #     role = db.query(Role).filter(Role.gid == self.gid, Role.position == d).limit(1).first()
            #     role.alive = False
            # self.history['dying'] = {}
            pass
        elif now is GameEnum.TURN_STEP_USE_SKILLS:
            for d in self.history['dying']:
                role = db.query(Role).filter(Role.gid == self.gid, Role.position == d).limit(1).first()
                role.alive = False
            self.history['dying'] = {}
        else:
            return GameEnum.OK.digest()
        return GameEnum.OK.digest()

    def _enter_step(self, db: Session) -> GameEnum:
        now = self.current_step()
        if now is GameEnum.TURN_STEP_TURN_NIGHT:
            self.status = GameEnum.GAME_STATUS_NIGHT
            # for d in self.history['dying']:
            #     role = db.query(Role).filter(Role.gid == self.gid, Role.position == d).limit(1).first()
            #     role.alive = False
            self.reset_history()
            publish_music(self.gid, 'night_start_voice', 'night_bgm', True)
            publish_info(self.gid, json.dumps({
                'game': {
                    'days': self.days,
                    'status': self.status.value
                },
                'mutation': 'SOCKET_GAME'
            }))
            publish_history(self.gid,
                            (
                                '***************************\n'
                                '<pre>         第{}天           </pre>\n'
                                '***************************'
                            ).format(self.days), show=False)
            return GameEnum.STEP_FLAG_AUTO_MOVE_ON
        elif now is GameEnum.TAG_ATTACKABLE_WOLF:
            publish_music(self.gid, 'wolf_start_voice', 'wolf_bgm', True)
            all_players = db.query(Role).filter(Role.gid == self.gid, Role.alive == int(True)).limit(len(self.players)).all()
            for p in all_players:
                if GameEnum.TAG_ATTACKABLE_WOLF in p.tags:
                    break
            else:
                pass
                # todo
                # scheduler.add_job(id=f'{self.gid}_WOLF_KILL_{self.step_cnt}', func=Game._timeout_move_on,
                #                   args=(self.gid, self.step_cnt),
                #                   next_run_time=datetime.now() + timedelta(seconds=random.randint(GameEnum.GAME_TIMEOUT_RANDOM_FROM.label, GameEnum.GAME_TIMEOUT_RANDOM_TO.label)))  # noqa E501
            return GameEnum.STEP_FLAG_WAIT_FOR_ACTION
        elif now in [GameEnum.TURN_STEP_TALK, GameEnum.TURN_STEP_ELECT_TALK]:
            return GameEnum.STEP_FLAG_WAIT_FOR_ACTION
        elif now is GameEnum.TURN_STEP_ELECT:
            publish_music(self.gid, 'elect', None, False)
            publish_history(self.gid, '###上警阶段###', False)
            return GameEnum.STEP_FLAG_WAIT_FOR_ACTION
        elif now is GameEnum.TURN_STEP_VOTE:
            self.history['vote_result'] = {}
            voters = []
            votees = []
            roles = db.query(Role).filter(Role.gid == self.gid).limit(len(self.players)).all()
            for r in roles:
                if not r.alive:
                    continue
                votees.append(r.position)
                if r.voteable:
                    voters.append(r.position)
            self.history['voter_votee'] = [voters, votees]
            publish_history(self.gid, '###投票阶段###', False)
            return GameEnum.STEP_FLAG_WAIT_FOR_ACTION
        elif now is GameEnum.TURN_STEP_ELECT_VOTE:
            self.history['vote_result'] = {}
            publish_history(self.gid, '###警长投票阶段###', False)
            return GameEnum.STEP_FLAG_WAIT_FOR_ACTION
        elif now is GameEnum.TURN_STEP_PK_VOTE:
            self.history['vote_result'] = {}
            publish_history(self.gid, '###PK投票阶段###', False)
            return GameEnum.STEP_FLAG_WAIT_FOR_ACTION
        elif now is GameEnum.TURN_STEP_ELECT_PK_VOTE:
            self.history['vote_result'] = {}
            publish_history(self.gid, '###警长PK投票阶段###', False)
            return GameEnum.STEP_FLAG_WAIT_FOR_ACTION
        elif now is GameEnum.TURN_STEP_ANNOUNCE:
            if self.history['dying']:
                publish_history(self.gid, '昨晚，以下位置的玩家倒下了，不分先后：{}'.format(
                    ','.join([str(d) for d in sorted(self.history['dying'])])
                ))
            else:
                publish_history(self.gid, "昨晚是平安夜")
            return GameEnum.STEP_FLAG_AUTO_MOVE_ON
        elif now is GameEnum.TURN_STEP_TURN_DAY:
            self.status = GameEnum.GAME_STATUS_DAY
            publish_music(self.gid, 'day_start_voice', 'day_bgm', False)
            self._calculate_die_in_night(db)
            publish_info(self.gid, json.dumps({
                'game': {
                    'days': self.days,
                    'status': self.status.value
                },
                'mutation': 'SOCKET_GAME'
            }))
            return GameEnum.STEP_FLAG_AUTO_MOVE_ON
        elif now is GameEnum.ROLE_TYPE_SEER:
            publish_music(self.gid, 'seer_start_voice', 'seer_bgm', True)
            seer_cnt = db.query(func.count(Role.uid)).filter(Role.gid == self.gid, Role.alive == int(True),
                                                             Role.role_type == GameEnum.ROLE_TYPE_SEER).scalar()
            if seer_cnt == 0:
                pass
                # todo
                # scheduler.add_job(id=f'{self.gid}_SEER_{self.step_cnt}', func=Game._timeout_move_on,
                #                   args=(self.gid, self.step_cnt),
                #                   next_run_time=datetime.now() + timedelta(seconds=random.randint(GameEnum.GAME_TIMEOUT_RANDOM_FROM.label, GameEnum.GAME_TIMEOUT_RANDOM_TO.label)))  # noqa E501
            return GameEnum.STEP_FLAG_WAIT_FOR_ACTION
        elif now is GameEnum.ROLE_TYPE_WITCH:
            publish_music(self.gid, 'witch_start_voice', 'witch_bgm', True)
            witch_cnt = db.query(func.count(Role.uid)).filter(Role.gid == self.gid, Role.alive == int(True),
                                                              Role.role_type == GameEnum.ROLE_TYPE_WITCH).scalar()
            if witch_cnt == 0:
                pass
                # todo
                # scheduler.add_job(id=f'{self.gid}_WITCH_{self.step_cnt}', func=Game._timeout_move_on,
                #                   args=(self.gid, self.step_cnt),
                #                   next_run_time=datetime.now() + timedelta(seconds=random.randint(GameEnum.GAME_TIMEOUT_RANDOM_FROM.label, GameEnum.GAME_TIMEOUT_RANDOM_TO.label)))  # noqa E501
            return GameEnum.STEP_FLAG_WAIT_FOR_ACTION
        elif now is GameEnum.ROLE_TYPE_SAVIOR:
            publish_music(self.gid, 'savior_start_voice', 'savior_bgm', True)
            savior_cnt = db.query(func.count(Role.uid)).filter(Role.gid == self.gid, Role.alive == int(True),
                                                               Role.role_type == GameEnum.ROLE_TYPE_SAVIOR).scalar()
            if savior_cnt == 0:
                pass
                # todo
                # scheduler.add_job(id=f'{self.gid}_SAVIOR', func=Game._timeout_move_on,
                #                   args=(self.gid, self.step_cnt),
                #                   next_run_time=datetime.now() + timedelta(seconds=random.randint(GameEnum.GAME_TIMEOUT_RANDOM_FROM.label, GameEnum.GAME_TIMEOUT_RANDOM_TO.label)))  # noqa E501
            return GameEnum.STEP_FLAG_WAIT_FOR_ACTION

    def current_step(self) -> GameEnum:
        if self.now_index < 0 or self.now_index >= len(self.steps):
            return None
        else:
            return self.steps[self.now_index]

    def _init_steps(self):
        self.steps = [GameEnum.TURN_STEP_TURN_NIGHT]
        if self.days == 1 and GameEnum.ROLE_TYPE_THIEF in self.cards:
            pass  # todo
        if self.days == 1 and GameEnum.ROLE_TYPE_CUPID in self.cards:
            pass  # todo
        # TODO: 恋人互相确认身份
        self.steps.append(GameEnum.TAG_ATTACKABLE_WOLF)
        if GameEnum.ROLE_TYPE_SEER in self.cards:
            self.steps.append(GameEnum.ROLE_TYPE_SEER)
        if GameEnum.ROLE_TYPE_WITCH in self.cards:
            self.steps.append(GameEnum.ROLE_TYPE_WITCH)
        if GameEnum.ROLE_TYPE_SAVIOR in self.cards:
            self.steps.append(GameEnum.ROLE_TYPE_SAVIOR)
        self.steps.append(GameEnum.TURN_STEP_TURN_DAY)
        if self.days == 1 and self.captain_mode is GameEnum.CAPTAIN_MODE_WITH_CAPTAIN:
            self.steps.append(GameEnum.TURN_STEP_ELECT)
            self.steps.append(GameEnum.TURN_STEP_ELECT_TALK)
            self.steps.append(GameEnum.TURN_STEP_ELECT_VOTE)
        self.steps.append(GameEnum.TURN_STEP_ANNOUNCE)
        self.steps.append(GameEnum.TURN_STEP_USE_SKILLS)
        if self.days == 1:
            self.steps.append(GameEnum.TURN_STEP_LAST_WORDS)
        self.steps.append(GameEnum.TURN_STEP_TALK)
        self.steps.append(GameEnum.TURN_STEP_VOTE)
        self.steps.append(GameEnum.TURN_STEP_USE_SKILLS)
        self.steps.append(GameEnum.TURN_STEP_LAST_WORDS)

        return

    def get_instruction_string(self) -> str:
        now = self.current_step()
        if now in [GameEnum.TURN_STEP_TALK, GameEnum.TURN_STEP_PK_TALK, GameEnum.TURN_STEP_ELECT_TALK, GameEnum.TURN_STEP_ELECT_PK_TALK]:
            return '结束发言'

        if now is GameEnum.TURN_STEP_LAST_WORDS:
            return '结束遗言'

        if now in [GameEnum.TURN_STEP_VOTE, GameEnum.TURN_STEP_PK_VOTE, GameEnum.TURN_STEP_ELECT_VOTE, GameEnum.TURN_STEP_ELECT_PK_VOTE]:
            return '结束投票'

        if now is GameEnum.TURN_STEP_ELECT:
            return '结束上警'

        if now is GameEnum.TURN_STEP_ANNOUNCE:
            return '技能使用完毕'

        next_index = self.now_index + 1
        if next_index >= len(self.steps):
            step = GameEnum.TURN_STEP_TURN_NIGHT
        else:
            step = self.steps[next_index]

        if step is GameEnum.TURN_STEP_TURN_NIGHT:
            return '入夜'

        return ''

    def _kill(self, db: Session, pos: int, how: GameEnum):
        logging.info(f'kill pos={pos},by {how.label}')
        if pos < 1 or pos > self.get_seats_cnt():
            return
        role = db.query(Role).filter(Role.gid == self.gid, Role.position == pos).limit(1).first()

        # todo 长老?

        if role is GameEnum.ROLE_TYPE_IDIOT and how is GameEnum.SKILL_VOTE and not role.args['exposed']:
            role.args['exposed'] = True
            role.voteable = False
            return

        self.history['dying'][pos] = True
        self.history.changed()

        if how is GameEnum.SKILL_TOXIC and role is GameEnum.ROLE_TYPE_HUNTER:
            role.args['shootable'] = False

        # todo: other link die
        # if self.status is GameEnum.GAME_STATUS_DAY:
        self._check_win(db)

    def _calculate_die_in_night(self, db: Session):
        wolf_kill_pos = self.history['wolf_kill_decision']
        elixir = self.history['elixir']
        guard = self.history['guard']

        logging.info(f'wolf_kill_pos={wolf_kill_pos},elixir={elixir},guard={guard}')
        if wolf_kill_pos > 0:
            killed = True
            if elixir:
                killed = not killed
            if guard == wolf_kill_pos:
                killed = not killed

            if killed:
                self._kill(db, wolf_kill_pos, GameEnum.SKILL_WOLF_KILL)
        if self.history['toxic'] > 0:
            self._kill(db, self.history['toxic'], GameEnum.SKILL_TOXIC)
        # todo: other death way in night?
        return

    def _check_win(self, db: Session):
        # groups = db.query(Role).with_entities(Role.group_type, func.count(Role.group_type)).filter(Role.gid == self.gid, Role.alive == int(True)).group_by(Role.group_type).all()  # noqa E501
        # groups = {g: cnt for g, cnt in groups}

        players = db.query(Role).with_entities(Role.position, Role.group_type).filter(Role.gid == self.gid, Role.alive == int(True)).all()
        groups = collections.defaultdict(int)
        for p, g in players:
            if p not in self.history['dying']:
                groups[g] += 1

        if GameEnum.GROUP_TYPE_WOLVES not in groups:
            # publish_history(self.gid, '游戏结束，好人阵营胜利')
            # # self.status = GameEnum.GAME_STATUS_FINISHED
            # original_players = self.players
            # self._init_game()
            # self.players = original_players
            # all_players = db.query(Role).filter(Role.gid == self.gid).all()
            # for p in all_players:
            #     p.reset()
            raise GameFinished(self.gid, GameEnum.GROUP_TYPE_GOOD, db)

        if self.victory_mode is GameEnum.VICTORY_MODE_KILL_GROUP and (GameEnum.GROUP_TYPE_GODS not in groups or GameEnum.GROUP_TYPE_VILLAGERS not in groups):  # noqa E501
            # publish_history(self.gid, '游戏结束，狼人阵营胜利')
            # # self.status = GameEnum.GAME_STATUS_FINISHED
            # original_players = self.players
            # self._init_game()
            # self.players = original_players
            # all_players = db.query(Role).filter(Role.gid == self.gid).all()
            # for p in all_players:
            #     p.reset()
            raise GameFinished(self.gid, GameEnum.GROUP_TYPE_WOLVES, db)

        if GameEnum.GROUP_TYPE_GODS not in groups and GameEnum.GROUP_TYPE_VILLAGERS not in groups:
            # publish_history(self.gid, '游戏结束，狼人阵营胜利')
            # # self.status = GameEnum.GAME_STATUS_FINISHED
            # original_players = self.players
            # self._init_game()
            # self.players = original_players
            # all_players = db.query(Role).filter(Role.gid == self.gid).all()
            # for p in all_players:
            #     p.reset()
            raise GameFinished(self.gid, GameEnum.GROUP_TYPE_WOLVES, db)

    # def _reset_history(self):
    #     """
    #         pos: -1=no one, -2=not acted
    #         {
    #             'wolf_kill':{wolf_pos:target_pos,...},
    #             'wolf_kill_decision':pos,
    #             'elixir':True / False,
    #             'guard':pos,
    #             'toxic':pos,
    #             'discover':pos,
    #             'voter_votee':[[voter_pos,...],[votee_pos,...]],
    #             'vote_result': {voter_pos:votee_pos,...},
    #             'dying':{pos:True},
    #         }
    #     """
    #     self.history = {
    #         'wolf_kill': {},
    #         'wolf_kill_decision': GameEnum.TARGET_NOT_ACTED.value,
    #         'elixir': False,
    #         'guard': GameEnum.TARGET_NOT_ACTED.value,
    #         'toxic': GameEnum.TARGET_NOT_ACTED.value,
    #         'discover': GameEnum.TARGET_NOT_ACTED.value,
    #         'voter_votee': [[], []],
    #         'vote_result': {},
    #         'dying': {},
    #     }

    # def _init_game(self):
    #     self.status = GameEnum.GAME_STATUS_WAIT_TO_START
    #     self.end_time = datetime.utcnow() + timedelta(days=1)
    #     self.days = 0
    #     self.now_index = -1
    #     self.step_cnt = 0
    #     self.steps = []
    #     self.history = {}
    #     self.captain_pos = -1
    #     self.players = []
    #     self._reset_history()

    # @staticmethod
    # def _timeout_move_on(gid, step_cnt):
    #     with scheduler.app.test_request_context():
    #         with db.query(Game).with_for_update().get(gid) as game:
    #             if step_cnt != game.step_cnt:
    #                 return game._move_on()

    def get_role_by_pos(self, db, pos) -> Role:
        if pos < 0:
            return None
        uid = self.players[pos - 1]
        return db.query(Role).get(uid)
