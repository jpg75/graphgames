from ... import socket_io, db, Configuration
from ...decorators import authenticated_only
from flask_security import current_user
from flask_socketio import SocketIO, emit
from flask import request, session
from datetime import datetime
from ...models import Move, GameSession
from json import dumps, loads
from time import sleep
from ... import celery
from parser import RuleParser
from collections import deque

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
        if m.startswith('HAND'):
            hand = m.replace('HAND ', '')
            local_socket.emit('replay', {'success': 'ok', 'hand': loads(hand),
                                         'next_move_at': fsec,
                                         'move': None,
                                         'covered': struct['covered'],
                                         'opponent_covered': struct['opponent_covered']})
            print "replaying: %s" % hand
        else:
            local_socket.emit('replay', {'success': 'ok', 'hand': None,
                                         'next_move_at': fsec,
                                         'move': m,
                                         'covered': struct['covered'],
                                         'opponent_covered': struct['opponent_covered']})
            print "replaying: %s" % m

        print "Waiting: %f seconds" % fsec
        sleep(fsec)
        i += 1
        print i
        # send the last move:
        if i == len(moves) - 1:
            print "send last move!"
            local_socket.emit('replay', {'success': 'ok', 'hand': None,
                                         'move': moves[i].mv,
                                         'next_move_at': fsec,
                                         'covered': struct['covered'],
                                         'opponent_covered': struct['opponent_covered']})
            print "replaying: %s" % moves[i].mv

    sleep(5.0)  # by default wait half second before quitting the game
    local_socket.emit('gameover', {'comment': 'Replay ended'})  # end the game
    print "Game over."


@celery.task()
def bot_task(url, sid, struct):
    """
    Generate a local web socket linked to the queue url. The task process is tied to this
    communication link for its lifespan.
    Play the TTT using a rule-based AI. Rules are in the file 'data/arules.txt'.
    The game is entirely managed by this thread. The client is driven passively.
    AI moves and client ones are stored in DB.

    The code is verbose using print statements. They are visible through the celery worker
    console in debug mode.

    :param url: A (Redis) queue url
    :param sid: session ID
    :param struct: dictionary with game instance parameters
    """
    print "TTT bot started!"
    rulep = RuleParser()
    rulep.load_rules()
    local_socket = SocketIO(message_queue=url)


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
    # bot_task.delay(url='redis://localhost:6379/0', sid=session['game_session'],
    #                   struct=session['game_cfg'])
    pass


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

    if session['game_cfg']['replay']:
        print "Client have to replay a session"
        emit('set_replay', {})

    elif session['game_cfg']['multiplayer']:
        print "Client have to play a multi-user game (possibly AI)"
        emit('set_multiplayer', {})

    else:
        user_d[current_user.email] = Configuration(config_file=session['game_cfg']['shoe_file'])
        user_d[current_user.email].purgelines()

        serve_new_hand(current_user.email)


@socket_io.on('move')
@authenticated_only
def move(message):
    """
    When receiving a move from the client.
    :param message:
    :return:
    """
    print "received move: ", message['move']
    print current_user
    print current_user.id
    print current_user.email
    # It actually generates the timestamp now!
    m = Move(uid=current_user.id, sid=session['game_session'], mv=message['move'],
             play_role=message['player'], ts=datetime.now())
    db.session.add(m)
    db.session.commit()

    if message['move'] == 'T' and message['moved_card'] == message['goal_card']:
        # Serve a new hand and the dummy move 'HAND' which represents the start of a hand:
        serve_new_hand(message['username'])

    else:
        player = message['player']
        # updates the history for the current player before switching it
        history = deque(session[player + '_history'], 2)
        history.appendleft({'move': message['move'],
                            'up': message['up'],
                            'target': message['target'],
                            'in_hand': message['in_hand']
                            })
        session[player + '_history'] = history

        if player == 'CK':
            player = 'NK'
        else:
            player = 'CK'
        emit('toggle_players', {'player': player})


@socket_io.on('connect')
@authenticated_only
def test_connect():
    print "A client connected"


@socket_io.on('disconnect')
@authenticated_only
def test_disconnect():
    user_d.pop(current_user.email, None)  # remove user from connected users

    print('Client disconnected', request.sid)


def serve_new_hand(username):
    s = user_d[current_user.email]
    if len(s.content) > 0:
        # clean the histories in the session:
        session['ck_history'] = None
        session['nk_history'] = None

        hand = s.content.pop(0)
        hand = hand.upper()
        hand = hand.split()
        hand = dict(zip(_SHOE_FILE_ORDER, hand))

        m2 = Move(uid=current_user.id, sid=session['game_session'], mv='HAND ' + dumps(hand),
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
