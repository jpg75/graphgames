from ... import socket_io, db, Configuration
from ...decorators import authenticated_only
from flask_security import current_user
from flask_socketio import SocketIO, emit
from flask import request, session
from datetime import datetime
from ...models import Move, GameSession, User
from json import dumps, loads
from time import sleep
from ... import celery
from parser import RuleParser
from collections import deque
from random import uniform

user_d = dict()  # maps user names to Session objects
_SHOE_FILE_ORDER = ['NK', 'N', 'U', 'C', 'CK', 'T', 'GC', 'PL']
history_record = {'move': '',
                  # card in the hand of the current player: in 'NK' position if it is
                  # numberkeeper's turn
                  'in_hand': '',
                  'up': '',
                  'target': ''}


@celery.task()
def replay_task(url, sid, struct):
    """
    Generate a local web socket linked to the queue url. The task process is tied to this
    communication link for its lifespan.
    Takes all the element of a game session and sends back to the client the exact sequence of
    events scheduling them with the exact timing.
    The code is verbose using print statements. They are visible through the celery worker
    console in debug mode.

    :param url: A (Redis) queue url
    :param sid: session ID
    :param struct: dictionary with game instance parameters
    :return:
    """
    print "Replay Task started!"

    # get all the session moves
    moves = Move.query.filter_by(sid=sid).all()
    print moves
    print "Fetched %d moves" % len(moves)
    local_socket = SocketIO(message_queue=url)
    i = 0
    # send all moves one by one
    for move in moves[1:]:
        c = move.ts - moves[i].ts
        m = moves[i].mv
        fsec = c.total_seconds()
        # print "Processing move: ", m
        # NOTE:  do not like the fact that a generic method "knows" about hand and simple move
        # kind of move inside the DB. A refined version would be agnostic! In should send
        # whatever found in DB entries, since each game is responsible to interpret its own data.
        m_struct = loads(m)

        if m_struct['move'] == 'HAND':
            local_socket.emit('replay', {'success': 'ok', 'hand': m_struct,
                                         'next_move_at': fsec,
                                         'move': None,
                                         'covered': struct['covered'],
                                         'opponent_covered': struct['opponent_covered']})
            print "replaying: %s" % m_struct

        else:
            local_socket.emit('replay', {'success': 'ok', 'hand': None,
                                         'next_move_at': fsec,
                                         'move': m_struct,
                                         'covered': struct['covered'],
                                         'opponent_covered': struct['opponent_covered']})
            print "replaying: %s" % m_struct

        print "Waiting: %f seconds" % fsec
        sleep(fsec)
        i += 1
        print i
        # send the last move:
        if i == len(moves) - 1:
            print "send last move!"
            local_socket.emit('replay', {'success': 'ok', 'hand': None,
                                         'move': m_struct,
                                         'next_move_at': fsec,
                                         'covered': struct['covered'],
                                         'opponent_covered': struct['opponent_covered']})
            print "replaying: %s" % m_struct

    sleep(5.0)  # by default wait half second before quitting the game
    local_socket.emit('gameover', {'comment': 'Replay ended'})  # end the game
    print "Game over."


@celery.task()
def bot_task(url, sid, hand, up, target, ck_history=None, nk_history=None, player_role='NK',
             fake_delay=3.0, memory_size=4):
    """
    Play the TTT using a rule-based AI. Rules are in the file 'data/arules.txt'.
    This task process makes a single decision about the next move to play, then notifies to
    the client, updates db and quits. When the web server (socketio) receives the next move
    from the client, then it triggers again this task.

    Generate a local web socket linked to the queue url. The task process is tied to this
    communication link for its lifespan.

    The code is verbose using print statements. They are visible through the celery worker
    console in debug mode.

    :param url: A (Redis) queue url
    :param sid: session ID
    :param hand: current card in player's (bot) hand
    :param up: card in UP position
    :param target: card in target position
    :param ck_history: list of dictionaries representing the memory of ck actions
    :param nk_history: list of dictionaries representing the memory of nk actions
    :param player_role: role played, default NK
    :param fake_delay: delay to mimic a human-like reply
    """
    print "TTT bot started!"
    rulep = RuleParser()
    rulep.load_rules()
    local_socket = SocketIO(message_queue=url)
    # prev_state = {}
    # get the last game state from DB:
    memory = Move.query.filter_by(sid=sid).order_by(Move.ts.desc()).limit(memory_size)
    print "Memory: ", memory
    ck_history = [loads(x.mv) for x in memory if x.play_role == 'CK']
    nk_history = [loads(x.mv) for x in memory if x.play_role == 'NK']

    prev_state = loads(memory[0].mv)
    if prev_state['move'] == 'HAND':
        ck_history[:] = []
        nk_history[:] = []

    # compute the next move
    ckh = []  # list of dict
    nkh = []
    for item in ck_history:
        ckh.append({'move': item['move'], 'in_hand': item['in_hand'], 'T': item['panel'][
            'T'], 'U': item['panel']['U']})
    for item in nk_history:
        nkh.append({'move': item['move'], 'in_hand': item['in_hand'], 'T': item['panel'][
            'T'], 'U': item['panel']['U']})

    print "--ckh: ", ckh
    print "--nkh: ", nkh
    next_move = rulep.match(hand, up, target, ck_knowledge=ckh, nk_knowledge=nkh)

    # notify the move to the client with message 'external_move' along with player (bot),
    # play role, etc,..
    sleep(uniform(0.5, fake_delay))  # pretends to think for a while :-)
    print next_move
    local_socket.emit('external_move', {'move': next_move[0], 'player': 'NK', })

    # update db with the move played by the bot
    bot_user = User.query.filter_by(email='bot@graphgames.org').first()

    # NOTE: the move must be stored along with history and / or panel status
    move_record = {}
    if not ckh and not nkh:  # the db record is a HAND move
        move_record['player'] = player_role
        move_record['move'] = next_move[0]
        move_record['moved_card'] = prev_state['panel'][player_role]
        # might not be true when bot plays the CK role!
        move_record['goal_card'] = prev_state['panel']['GC']
        move_record['in_hand'] = prev_state['panel'][next_move[0]]
        move_record['panel'] = {k: prev_state['panel'][k] for k in prev_state['panel'].keys() if
                                k != 'PL' and k != 'GC'}

    else:  # the DB record is a std move
        move_record['player'] = player_role
        move_record['move'] = next_move[0]
        move_record['moved_card'] = prev_state['panel'][player_role]
        # might not be true when bot plays the CK role!
        move_record['goal_card'] = prev_state['goal_card']
        move_record['in_hand'] = prev_state['panel'][next_move[0]]
        move_record['panel'] = prev_state['panel']

        move_record['panel'][player_role] = move_record['in_hand']
        move_record['panel'][next_move[0]] = move_record['moved_card']

    print "move_record: ", move_record

    m = Move(uid=bot_user.id, sid=sid, mv=dumps(move_record), play_role='NK', ts=datetime.now())
    db.session.add(m)
    db.session.commit()


@socket_io.on('replay_ready')
@authenticated_only
def replay_ready(message):
    """
    Called when 'replay_ready' message is received. The background task is spawned.

    :return:
    """
    # here start the background thread for replay session:
    replay_task.delay(url='redis://localhost:6379/0', sid=session['game_session'],
                      struct=session['game_cfg'])


@socket_io.on('multiplayer_ready')
@authenticated_only
def multiplayer_ready(message):
    """
    Called when 'multiplayer_ready' message is received. The background task is spawned.

    :param message:
    :return:
    """
    serve_new_hand()


@socket_io.on('login')
@authenticated_only
def login(message):
    """
    The actual login is carried out by the web app through flask_login.
    Here the login represents a sort of confirmation.
    It replies with a 'game response' message holding everything required
    to start the game:
    + status: failure/success
    + hand: where the card must be located, which is the goal card, whose player turn is
    + covered cards: which card must be covered
    + opponent_covered: whether the current player opponent must be covered or not

    :param message: json message with proposed username. No real auth.
    :return:
    """
    if not current_user.is_authenticated:
        return

    print current_user
    print "session ", session['game_cfg']
    print "session: ", session['game_type']

    user_d[current_user.email] = Configuration(config_file=session['game_cfg']['shoe_file'])
    user_d[current_user.email].purgelines()

    if session['game_cfg']['replay']:
        print "Client have to replay a session"
        emit('set_replay', {})

    elif session['game_cfg']['enable_multiplayer']:
        print "Client have to play a multi-user game (possibly AI)"
        emit('set_multiplayer', {})

    else:
        # user_d[current_user.email] = Configuration(config_file=session['game_cfg']['shoe_file'])
        # user_d[current_user.email].purgelines()

        serve_new_hand()


@socket_io.on('move')
@authenticated_only
def move(message):
    """
    When receiving a move from the client.
    If in bot_enabled game session, it has to trigger the opponent by activating the celery bot.

    :param message:
    :return:
    """
    print "received move: ", message
    print current_user
    print current_user.id
    print current_user.email
    # It actually generates the timestamp now!
    m = Move(uid=current_user.id, sid=session['game_session'], mv=dumps(message),
             play_role=message['player'], ts=datetime.now())
    db.session.add(m)
    db.session.commit()

    if message['move'] == 'T' and message['moved_card'] == message['goal_card']:
        # Serve a new hand and the dummy move 'HAND' which represents the start of a hand:
        next_hand = serve_new_hand()
        # when bots are enabled and next is NK, then the bot task is triggered:
        if next_hand and session['game_cfg']['enable_bot'] and next_hand['panel']['PL'] == 'NK':
            bot_task.delay(url='redis://localhost:6379/0', sid=session['game_session'],
                           hand=next_hand['panel'][next_hand['panel']['PL']],
                           up=next_hand['panel']['U'], target=next_hand['panel']['T'])

            print "hand ", next_hand['panel'][next_hand['panel']['PL']]
            print "up: ", next_hand['panel']['U']
            print "target ", next_hand['panel']['T']
    else:
        player = message['player']
        if player == 'CK':
            player = 'NK'
        else:
            player = 'CK'
        emit('toggle_players', {'player': player})

        # if bot enabled, trigger the celery bot:
        if session['game_cfg']['enable_bot']:
            bot_task.delay(url='redis://localhost:6379/0', sid=session['game_session'],
                           hand=message['panel'][player],
                           up=message['panel']['U'], target=message['panel']['T'])


@socket_io.on('connect')
@authenticated_only
def test_connect():
    print "A client connected"


@socket_io.on('disconnect')
@authenticated_only
def test_disconnect():
    user_d.pop(current_user.email, None)  # remove user from connected users

    print('Client disconnected', request.sid)


def serve_new_hand():
    """
    Generate the new hand according to the config and send a message to the client about it.

    :return: a python dictionary describing the new hand. It is the same structure which is
    written in the Move DB using JSON encoding.
    """
    next_hand_record = None
    session_config = user_d[current_user.email]
    if len(session_config.content) > 0:
        hand = session_config.content.pop(0)
        hand = hand.upper()
        hand = hand.split()
        hand = dict(zip(_SHOE_FILE_ORDER, hand))

        next_hand_record = {'move': 'HAND', 'panel': hand}

        m2 = Move(uid=current_user.id, sid=session['game_session'], mv=dumps(next_hand_record),
                  play_role='', ts=datetime.now())
        db.session.add(m2)
        db.session.commit()

        print "Serving new HAND: %s" % hand
        emit('hand', {'success': 'ok', 'hand': hand,
                      'covered': session['game_cfg']['covered'],
                      'opponent_covered': session['game_cfg']['opponent_covered']})

    else:
        print "session ended"
        # ends the session on the DB:
        gs = GameSession.query.filter_by(id=session['game_session']).first()
        gs.end = datetime.now()
        db.session.add(gs)
        db.session.commit()
        emit('gameover', {})

    return next_hand_record
