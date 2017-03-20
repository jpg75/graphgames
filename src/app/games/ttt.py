from .. import socket_io, db, Configuration
from ..decorators import authenticated_only
from flask_security import current_user
from flask_socketio import emit
from flask import request, session
from datetime import datetime
from ..models import Move, GameSession
from ..tasks import replay_task
from json import dumps

user_d = dict()  # maps user names to Session objects
_SHOE_FILE_ORDER = ['NK', 'N', 'U', 'C', 'CK', 'T', 'GC', 'PL']

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
