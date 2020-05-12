# from typing import Any
from datetime import datetime
import random
import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
# from sqlalchemy.exc import IntegrityError

from werewolf.schemas import schema_in, schema_out
from werewolf.models import User, Game, Role
from werewolf.api import deps
from werewolf.websocket.websocket import publish_info, publish_history
# from werewolf.core.config import settings
from werewolf.utils.enums import GameEnum
# from werewolf.utils.game_exceptions import GameFinished

router = APIRouter()


@router.post("/create", response_model=schema_out.GameCreateOut)
async def create_game(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    game_in: schema_in.GameCreateIn,
):
    cards = [GameEnum.ROLE_TYPE_VILLAGER] * game_in.villagerCnt + [GameEnum.ROLE_TYPE_NORMAL_WOLF] * game_in.normalWolfCnt
    cards += game_in.selectedGods
    cards += game_in.selectedWolves

    new_game = Game(host_uid=current_user.uid,
                    victory_mode=game_in.victoryMode,
                    captain_mode=game_in.captainMode,
                    witch_mode=game_in.witchMode,
                    wolf_mode=Game.get_wolf_mode_by_cards(cards),
                    cards=cards,
                    )
    new_game.init_game()
    db.add(new_game)
    db.commit()

    return GameEnum.OK.digest(gid=new_game.gid)


@router.get("/join/{gid}", response_model=schema_out.ResponseBase)
async def join_game(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    gid: int,
):
    game = db.query(Game).with_for_update().get(gid)
    if not game or datetime.utcnow() > game.end_time:
        return GameEnum.GAME_MESSAGE_GAME_NOT_EXIST.digest()
    if game.status is not GameEnum.GAME_STATUS_WAIT_TO_START:
        return GameEnum.GAME_MESSAGE_ALREADY_STARTED.digest()
    if current_user.uid in game.players:
        current_user.gid = gid
        db.commit()
        return GameEnum.GAME_MESSAGE_ALREADY_IN.digest()
    if len(game.players) >= game.get_seats_cnt():
        return GameEnum.GAME_MESSAGE_GAME_FULL.digest()

    # fine to join the game
    game.players.append(current_user.uid)
    current_user.gid = gid
    current_role = db.query(Role).get(current_user.uid)
    current_role.gid = gid
    current_role.reset()
    db.commit()
    return GameEnum.OK.digest()


@router.get("/quit", response_model=schema_out.ResponseBase)
async def quit(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    gid = current_user.gid
    if gid < 0:
        return GameEnum.GAME_MESSAGE_NOT_IN_GAME.digest()

    game = db.query(Game).with_for_update().get(gid)
    if not game or datetime.utcnow() > game.end_time:
        current_user.gid = -1
        db.commit()
        return GameEnum.GAME_MESSAGE_NOT_IN_GAME.digest()
    if game.status is not GameEnum.GAME_STATUS_WAIT_TO_START:
        pass  # todo easy to quit??
    if current_user.uid not in game.players:
        current_user.gid = -1
        db.commit()
        return GameEnum.GAME_MESSAGE_NOT_IN_GAME.digest()
    game.players.remove(current_user.uid)
    current_user.gid = -1
    current_role = db.query(Role).get(current_user.uid)
    current_role.gid = -1
    current_role.reset()
    db.commit()
    return GameEnum.OK.digest()


@router.get("/deal", response_model=schema_out.ResponseBase)
async def deal(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    game = db.query(Game).with_for_update().get(current_user.gid)
    if not game or datetime.utcnow() > game.end_time:
        return GameEnum.GAME_MESSAGE_CANNOT_START.digest()
    if game.status is not GameEnum.GAME_STATUS_WAIT_TO_START:
        return GameEnum.GAME_MESSAGE_CANNOT_START.digest()
    players_cnt = len(game.players)
    if players_cnt != game.get_seats_cnt():
        return GameEnum.GAME_MESSAGE_CANNOT_START.digest()
    players = db.query(Role).filter_by(gid=game.gid).limit(players_cnt).all()
    if len(players) != players_cnt:
        return GameEnum.GAME_MESSAGE_CANNOT_START.digest()
    for p in players:
        if p.uid not in game.players:
            return GameEnum.GAME_MESSAGE_CANNOT_START.digest()
    if set([p.position for p in players]) != set(range(1, players_cnt + 1)):
        return GameEnum.GAME_MESSAGE_CANNOT_START.digest()

    # fine to deal
    game.status = GameEnum.GAME_STATUS_READY
    players.sort(key=lambda p: p.position)
    game.players = [p.uid for p in players]
    cards = game.cards.copy()
    random.shuffle(cards)
    for p, c in zip(players, cards):
        p.role_type = c
        p.prepare(game.captain_mode)
    db.commit()
    publish_info(game.gid, json.dumps({
        'action': 'getGameInfo'
    }))
    publish_history(game.gid, "身份牌已发放")
    return GameEnum.OK.digest()


@router.get("/info", response_model=schema_out.GameInfoOut, response_model_exclude_unset=True)
async def info(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    game = db.query(Game).get(current_user.gid)
    if not game:
        return GameEnum.GAME_MESSAGE_NOT_IN_GAME.digest()
    all_players = db.query(Role).filter(Role.gid == game.gid).limit(len(game.players)).all()
    role = db.query(Role).get(current_user.uid)
    return GameEnum.OK.digest(
        game={
            'gid': game.gid,
            'days': game.days,
            'players': [{'pos': p.position, 'nickname': p.nickname, 'avatar': p.avatar} for p in all_players],
            'status': game.status,
            'seat_cnt': game.get_seats_cnt(),
            'victoryMode': game.victory_mode,
            'captainMode': game.captain_mode,
            'witchMode': game.witch_mode,
        },
        role={
            'role_type': role.role_type,
            'skills': role.skills,
            'alive': role.alive,
            'ishost': game.host_uid == role.uid,
            'speakable': role.speakable,
            'nickname': role.nickname,
        })


@router.get("/sit", response_model=schema_out.ResponseBase)
async def sit(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    position: int
):
    game = db.query(Game).get(current_user.gid)
    if game.status is not GameEnum.GAME_STATUS_WAIT_TO_START:
        return GameEnum.GAME_MESSAGE_ALREADY_STARTED.digest()
    my_role = db.query(Role).get(current_user.uid)
    my_role.position = position
    db.commit()
    all_players = db.query(Role).filter(Role.gid == game.gid).limit(len(game.players)).all()
    players = [{'pos': p.position, 'nickname': p.nickname, 'avatar': p.avatar} for p in all_players]
    publish_info(game.gid, json.dumps({
        'game': {
            'players': players
        },
        'mutation': 'SOCKET_GAME'
    }))
    return GameEnum.OK.digest()


@router.get("/next_step", response_model=schema_out.ResponseBase)
async def next_step(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    game = db.query(Game).with_for_update().get(current_user.gid)
    if game.status not in [GameEnum.GAME_STATUS_READY, GameEnum.GAME_STATUS_DAY]:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    ret = game.move_on(db)
    db.commit()
    return ret


@router.get("/vote", response_model=schema_out.ResponseBase)
async def vote(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    target: int
):
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)
    if not my_role.voteable or my_role.position not in game.history['voter_votee'][0]:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target != GameEnum.TARGET_NO_ONE.value and target not in game.history['voter_votee'][1]:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target > 0:
        target_role = game.get_role_by_pos(db, target)
        if not target_role or not target_role.alive:
            return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()

    now = game.current_step()
    if now in [GameEnum.TURN_STEP_VOTE, GameEnum.TURN_STEP_ELECT_VOTE]:
        game.history['vote_result'][my_role.position] = target
        game.history.changed()
        db.commit()
        if target > 0:
            return GameEnum.OK.digest(result=f'你投了{target}号玩家')
        else:
            return GameEnum.OK.digest(result=f'你弃票了')
    elif now in [GameEnum.TURN_STEP_PK_VOTE, GameEnum.TURN_STEP_ELECT_PK_VOTE]:
        if target == GameEnum.TARGET_NO_ONE.value:
            return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
        else:
            game.history['vote_result'][my_role.position] = target
            game.history.changed()
            db.commit()
            if target > 0:
                return GameEnum.OK.digest(result=f'你投了{target}号玩家')
            else:
                return GameEnum.OK.digest(result=f'你弃票了')
    else:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()


@router.get("/handover", response_model=schema_out.ResponseBase)
async def handover(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    target: int
):
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        logging.info('my_role is not alive')
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target == my_role.position:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)
    now = game.current_step()
    if now not in [GameEnum.TURN_STEP_LAST_WORDS, GameEnum.TURN_STEP_ANNOUNCE]:
        logging.info(f'wrong now step:{now.label}')
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if str(my_role.position) not in game.history['dying']:
        logging.info(f'not in dying: my position={my_role.position},dying={game.history["dying"]}')
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if game.captain_pos != my_role.position:
        logging.info(f'I am not captain, my position={my_role.position},captain pos={game.captain_pos}')
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target > 0:
        target_role = game.get_role_by_pos(db, target)
        if not target_role.alive:
            logging.info(f'target not alive, target={target}')
            return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game.captain_pos = target
    db.commit()
    publish_history(game.gid, f'{my_role.position}号玩家将警徽移交给了{target}号玩家')
    return GameEnum.OK.digest()


@router.get("/elect", response_model=schema_out.ResponseBase)
async def elect(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    choice: str
):
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)
    now = game.current_step()
    if choice in ['yes', 'no'] and now is not GameEnum.TURN_STEP_ELECT:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if choice == 'quit' and now is not GameEnum.TURN_STEP_ELECT_TALK:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if choice in ['yes', 'no'] and (GameEnum.TAG_ELECT in my_role.tags or GameEnum.TAG_NOT_ELECT in my_role.tags):
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if choice == 'quit' and (GameEnum.TAG_ELECT not in my_role.tags or GameEnum.TAG_GIVE_UP_ELECT in my_role.tags):
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()

    ret = None

    if choice == 'yes':
        my_role.tags.append(GameEnum.TAG_ELECT)
    elif choice == 'no':
        my_role.tags.append(GameEnum.TAG_NOT_ELECT)
    elif choice == 'quit':
        publish_history(game.gid, f'{my_role.position}号玩家退水')
        my_role.tags.remove(GameEnum.TAG_ELECT)
        my_role.tags.append(GameEnum.TAG_GIVE_UP_ELECT)
        votee = game.history['voter_votee'][1]
        votee.remove(my_role.position)
        if len(votee) == 1:
            while game.now_index + 1 < len(game.steps) and game.steps[game.now_index + 1] in {GameEnum.TURN_STEP_ELECT_TALK, GameEnum.TURN_STEP_ELECT_VOTE}:  # noqa E501
                game.steps.pop(game.now_index + 1)
            captain_pos = votee[0]
            game.captain_pos = captain_pos
            publish_history(game.gid, f'仅剩一位警上玩家，{captain_pos}号玩家自动当选警长')
            ret = game.move_on(db)
    else:
        raise ValueError(f'Unknown choice: {choice}')
    db.commit()
    return ret or GameEnum.OK.digest()


@router.get("/wolf_kill", response_model=schema_out.ResponseBase)
async def wolf_kill(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    target: int
):
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)
    now = game.current_step()
    history = game.history
    if now != GameEnum.TAG_ATTACKABLE_WOLF or GameEnum.TAG_ATTACKABLE_WOLF not in my_role.tags:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target > 0:
        target_role = game.get_role_by_pos(db, target)
        if not target_role.alive:
            return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if game.wolf_mode is GameEnum.WOLF_MODE_FIRST:
        history['wolf_kill_decision'] = target
    else:
        history['wolf_kill'][my_role.position] = target
        history.changed()
        all_players = Role.query.filter(Role.gid == game.gid, Role.alive == int(True)).limit(len(game.players)).all()
        attackable_cnt = 0
        for p in all_players:
            if GameEnum.TAG_ATTACKABLE_WOLF in p.tags:
                attackable_cnt += 1
        if attackable_cnt == len(history['wolf_kill']):
            decision = set(history['wolf_kill'].values())
            if len(decision) == 1:
                history['wolf_kill_decision'] = decision.pop()
            else:
                history['wolf_kill_decision'] = GameEnum.TARGET_NO_ONE.value
    game.move_on(db)
    db.commit()
    if target > 0:
        return GameEnum.OK.digest(result=f'你选择了击杀{target}号玩家')
    else:
        return GameEnum.OK.digest(result=f'你选择空刀')


@router.get("/discover", response_model=schema_out.ResponseBase)
async def discover(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    target: int
):
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)
    now = game.current_step()
    history = game.history
    if now is not GameEnum.ROLE_TYPE_SEER or my_role.role_type is not GameEnum.ROLE_TYPE_SEER:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if history['discover'] != GameEnum.TARGET_NOT_ACTED.value:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target > 0:
        target_role = game.get_role_by_pos(db, target)
        if not target_role.alive:
            return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    history['discover'] = target
    group_result = '<span style="color:red">狼人</span>' if target_role.group_type is GameEnum.GROUP_TYPE_WOLVES else '<span style="color:green">好人</span>'  # noqa E501
    game.move_on(db)
    db.commit()
    return GameEnum.OK.digest(result=f'你查验了{target}号玩家为：{group_result}')


@router.get("/witch", response_model=schema_out.ResponseBase)
async def witch(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)
    now = game.current_step()
    history = game.history
    if now is not GameEnum.ROLE_TYPE_WITCH or my_role.role_type is not GameEnum.ROLE_TYPE_WITCH:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    # todo commit
    if not my_role.args['elixir']:
        return GameEnum.OK.digest(result=GameEnum.TARGET_NOT_ACTED.value)
    else:
        return GameEnum.OK.digest(result=history['wolf_kill_decision'])


@router.get("/elixir", response_model=schema_out.ResponseBase)
async def elixir(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    # todo save self
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)
    now = game.current_step()
    history = game.history
    if now is not GameEnum.ROLE_TYPE_WITCH or my_role.role_type is not GameEnum.ROLE_TYPE_WITCH:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if not my_role.args['elixir']:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if history['elixir'] or history['toxic'] != GameEnum.TARGET_NOT_ACTED.value:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if history['wolf_kill_decision'] == GameEnum.TARGET_NO_ONE.value:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    history['elixir'] = True
    my_role.args['elixir'] = False
    db.commit()
    return GameEnum.OK.digest(result=f'你使用了解药')


@router.get("/toxic", response_model=schema_out.ResponseBase)
async def toxic(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    target: int
):
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target == my_role.position:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)
    now = game.current_step()
    history = game.history

    if now is not GameEnum.ROLE_TYPE_WITCH or my_role.role_type is not GameEnum.ROLE_TYPE_WITCH:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if not my_role.args['toxic']:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if history['elixir'] or history['toxic'] != GameEnum.TARGET_NOT_ACTED.value:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target > 0:
        target_role = game.get_role_by_pos(db, target)
        if not target_role.alive:
            return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    history['toxic'] = target
    if target > 0:
        my_role.args['toxic'] = False
    game.move_on(db)
    db.commit()
    if target > 0:
        return GameEnum.OK.digest(result=f'你毒杀了{target}号玩家')
    else:
        return GameEnum.OK.digest()


@router.get("/guard", response_model=schema_out.ResponseBase)
async def guard(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    target: int
):
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)
    now = game.current_step()
    history = game.history

    if now is not GameEnum.ROLE_TYPE_SAVIOR or my_role.role_type is not GameEnum.ROLE_TYPE_SAVIOR:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if my_role.args['guard'] != GameEnum.TARGET_NO_ONE.value and my_role.args['guard'] == target:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if history['guard'] != GameEnum.TARGET_NOT_ACTED.value:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target > 0:
        target_role = game.get_role_by_pos(db, target)
        if not target_role.alive:
            return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    history['guard'] = target
    my_role.args['guard'] = target
    game.move_on(db)
    db.commit()
    if target > 0:
        return GameEnum.OK.digest(result=f'你守护了{target}号玩家')
    else:
        return GameEnum.OK.digest(result=f'你选择空守')


@router.get("/shoot", response_model=schema_out.ResponseBase)
async def shoot(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    target: int
):
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target == my_role.position:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)
    now = game.current_step()

    if now not in [GameEnum.TURN_STEP_LAST_WORDS, GameEnum.TURN_STEP_ANNOUNCE]:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if not my_role.args['shootable'] or str(my_role.position) not in game.history['dying']:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    if target > 0:
        target_role = game.get_role_by_pos(db, target)
        if not target_role.alive:
            return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
        my_role.args['shootable'] = False
    publish_history(game.gid, f'{my_role.position}号玩家发动技能“枪击”，击倒了{target}号玩家')
    game._kill(db, target, GameEnum.SKILL_SHOOT)
    # try:
    # except GameFinished:
    #     pass  # todo game finished, or global except?
    db.commit()
    return GameEnum.OK.digest()


@router.get("/suicide", response_model=schema_out.ResponseBase)
async def suicide(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    target: int
):
    my_role = db.query(Role).get(current_user.uid)
    if not my_role.alive:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game = db.query(Game).with_for_update().get(current_user.gid)

    if game.status is not GameEnum.GAME_STATUS_DAY:
        return GameEnum.GAME_MESSAGE_CANNOT_ACT.digest()
    game.steps = []
    publish_history(game.gid, f'{my_role.position}号玩家自爆了')
    game._kill(db, my_role.position, GameEnum.SKILL_SUICIDE)
    # try:
    # except GameFinished:
    #     pass  # todo game finished, or global except?
    ret = game.move_on(db)
    db.commit()
    return ret
