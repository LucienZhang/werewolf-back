# from typing import Any
from datetime import datetime
import random
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
# from sqlalchemy.exc import IntegrityError

from werewolf.schemas import schema_in, schema_out
from werewolf.models import User, Game, Role
from werewolf.api import deps
from werewolf.websocket.websocket import publish_info
# from werewolf.core.config import settings
from werewolf.utils.enums import GameEnum

router = APIRouter()


@router.post("/create", response_model=schema_out.GameCreateOut)
def create_game(
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
def join_game(
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
def quit(
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
def deal(
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
    publish_info(game.gid, json.dumps({'cards': True}))
    return GameEnum.OK.digest()


@router.get("/info", response_model=schema_out.GameInfoOut, response_model_exclude_unset=True)
def info(
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
            'players': [{'pos': p.position, 'nickname': p.nickname, 'avatar': p.avatar} for p in all_players],
            'status': game.status,
            'seat_cnt': game.get_seats_cnt()
        },
        role={
            'role_type': role.role_type,
            'skills': role.skills,
        })


@router.get("/sit", response_model=schema_out.ResponseBase)
def sit(
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
    all_players = Role.query.filter(Role.gid == game.gid).limit(len(game.players)).all()
    publish_info(game.gid, json.dumps(
        GameEnum.OK.digest(
            seats={p.position: [p.nickname, p.avatar] for p in all_players},
        )
    ))
    return GameEnum.OK.digest()


@router.get("/next_step", response_model=schema_out.ResponseBase)
def next_step(
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
