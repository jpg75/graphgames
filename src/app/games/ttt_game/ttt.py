from ... import socket_io, db, Configuration, app
from ...decorators import authenticated_only
from flask_security import current_user
from flask_socketio import emit
from flask import request, session
from datetime import datetime
from ...models import Move, GameSession, User
from json import dumps, loads
from redis import Redis
from tasks import timeout_task, bot_task, replay_task

user_d = dict()  # maps user names to game configuration session objects
# clients = dict()  # maps user names to ws connection
# maps game id to a tuple: game_id -> (task-ref, [(uid, sid), ...] )
_SHOE_FILE_ORDER = ['NK', 'N', 'U', 'C', 'CK', 'T', 'GC', 'PL']

#####################################
# utility structure
history_record = {'move': '',
                  # card in the hand of the current player: in 'NK' position if it is
                  # numberkeeper's turn
                  'in_hand': '',
                  'up': '',
                  'target': ''}

#####################################

redis = Redis()  # global Redis DB handler for this module


def ttt_player_gen():
    """
    Super simple generator. It just works for TTT players.
    :return:
    """
    yield 'CK'
    yield 'NK'


@socket_io.on('replay_ready')
@authenticated_only
def replay_ready(message):
    """
    Called when 'replay_ready' message is received. The background task is spawned.

    """
    # here start the background thread for replay session:
    print "session: ", session['game_session']
    replay_task.delay(url='redis://localhost:6379/0', sid=session['game_session'],
                      struct=session['game_cfg'])
    # session['replay_bot'] = replay_bot


@socket_io.on('multiplayer_ready')
@authenticated_only
def multiplayer_ready(message):
    """
    Called when 'multiplayer_ready' message is received.
    When playing with other human players, the 'mp_table' is populated with info about the
    current player willing to participate.
    The background task is spawned.

    :param message: the message is considered having an empty payload
    """
    if session['game_cfg']['enable_bot']:
        serve_new_hand(current_user, session['game_session'])

    else:  # manage the wait or start the game between the parties
        # conn = Redis()

        # get mptable if any
        table = redis.get('mp_table')
        print "table: ", table
        if table:
            table_obj = loads(table)
            mpdef = table_obj.get(session['game_type'], None)
            # an entry for this mplayer session already exist, append the new player but checks
            # it is not already in:
            if mpdef and (current_user.id, session['game_session']) not in mpdef:
                print "Appending new entry to table"
                mpdef.append((current_user.id, session['game_session']))
                redis.set('mp_table', dumps(table_obj))

            else:  # make a new entry:
                print "make a new entry for mp session"
                table_obj[[session['game_type']]] = [(current_user.id, session['game_session'])]
                print "new table obj: ", table_obj
                redis.set('mp_table', dumps(table_obj))
                print "set mp_table into redis: ", dumps(table_obj)
                redis.set('srv_credentials', dumps({'host': 'localhost', 'port': app.config[
                    'SOCKET_IO_PORT'], 'msg': 'notify_groups'}))
                print "set srv_credentials var in redis: ", redis.get('srv_credentials')

                timeout_task.delay(gid=session['game_type'], sid=session['game_session'],
                                   struct=session['game_cfg'])

        else:  # table not yet available on redis
            # makes the table and set current player as a candidate for current game:
            redis.set('mp_table',
                      dumps({session['game_type']: [(current_user.id, session['game_session'])]}))
            timeout_task.delay(gid=session['game_type'], sid=session['game_session'],
                               struct=session['game_cfg'])


@socket_io.on('login')
@authenticated_only
def login(message):
    """
    The actual user login is carried out by the web app through flask_login.
    Here the login represents a sort of confirmation.
    It replies with a 'game response' message holding everything required
    to start the game:
    + status: failure/success
    + hand: where the card must be located, which is the goal card, whose player turn is
    + covered cards: which card must be covered
    + opponent_covered: whether the current player opponent must be covered or not

    :param message: json message with proposed username. No real auth
    """
    if not current_user.is_authenticated:
        return

    print current_user
    print "session ", session['game_cfg']
    print "session: ", session['game_type']

    user_d[current_user.email] = Configuration(config_file=session['game_cfg']['shoe_file'],
                                               rel_path='app/static/games/ttt/data')
    user_d[current_user.email].purgelines()

    if session['game_cfg']['replay']:
        print "Client have to replay a session"
        # emit('set_replay', {}, room=clients[current_user.email])
        emit('set_replay', {}, room=redis.hget('clients', current_user.email))

    elif session['game_cfg']['enable_multiplayer'] and session['game_cfg']['enable_bot']:
        print "Client have to play a multi-user game (AI)"
        # emit('set_multiplayer', {}, room=clients[current_user.email])
        emit('set_multiplayer', {}, room=redis.hget('clients', current_user.email))

    elif session['game_cfg']['enable_multiplayer'] and not session['game_cfg']['enable_bot']:
        print "Client have to play a multi-user game"
        # emit('set_multiplayer', {}, room=clients[current_user.email])
        emit('set_multiplayer', {}, room=redis.hget('clients', current_user.email))

    else:
        serve_new_hand(current_user, session['game_session'])


@socket_io.on('move')
@authenticated_only
def move(message):
    """
    When receiving a move from the client.
    If in bot_enabled game session, it has to trigger the opponent by activating the celery bot.
    If in multi player, it has to forward the current move to the opponent in order to keep the
    clients state consistent.

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
        if session['game_cfg']['enable_multiplayer']:
            next_hand = serve_new_hand(current_user, session['game_session'], multi_player=True)
        else:
            next_hand = serve_new_hand(current_user, session['game_session'], multi_player=False)

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

        emit('toggle_players', {'player': player}, room=redis.hget('clients', current_user.email))

        # when just multiplayer but no bot, forward the move to the other parties:
        if session['game_cfg']['enable_multiplayer'] and not session['game_cfg']['enable_bot']:
            # conn = Redis()
            groups = redis.get('groups_game_' + session['game_type'])
            for group in groups:
                group_obj = loads(group)
                participants = []
                for item in group_obj:
                    participants.append(item[0])

                if current_user.id in participants:
                    for item in participants:
                        if item != current_user.id:
                            u = User.query.filter_by(id=item)
                            # emit('external_move', {'move': message['move'], 'player': 'NK', },
                            #     room=clients[u.email])
                            emit('external_move', {'move': message['move'], 'player': 'NK', },
                                 room=redis.hget('clients', u.email))

        # if bot enabled, trigger the celery bot:
        if session['game_cfg']['enable_bot']:
            bot_task.delay(url='redis://localhost:6379/0',
                           sid=session['game_session'],
                           hand=message['panel'][player],
                           up=message['panel']['U'],
                           target=message['panel']['T'])


@socket_io.on('notify_groups')
def notify_groups_handler(message):
    print message
    ms = loads(message)
    # conn = Redis()

    for group in ms['groups']:
        # put each group into the redis set related to the game group:
        redis.sadd('groups_game_' + message['pid'], dumps(group))

        gen = ttt_player_gen()  # WARNING: in ttt no more than 2 participant
        for participant in group:
            u = User.query.filter_by(id=participant[0])
            # rns = clients.get(u.email, None)
            rns = redis.hget('clients', u.email)
            if rns:
                # emit('set_player', {'player': gen.next()}, room=clients[u.email])
                emit('set_player', {'player': gen.next()}, room=redis.hget('clients', u.email))
                serve_new_hand(u, participant[1], multi_player=True)

    for failed in ms['failed']:
        u = User.query.filter_by(id=failed[0])
        # rns = clients.get(u.email, None)
        rns = redis.hget('clients', u.email)
        if rns:
            # emit('abort_multiplayer', {}, room=clients[u.email])
            emit('abort_multiplayer', {}, room=redis.hget('clients', u.email))


@socket_io.on('connect')
def connect():
    print "A client connected: %s" % request.sid
    if current_user.is_authenticated:
        redis.hset('clients', current_user.email, request.sid)
        # clients[current_user.email] = request.sid
    # print clients
    print redis.hgetall('clients')


@socket_io.on('disconnect')
def disconnect():
    # if 'replay_bot' in session:  # terminate a replay bot if any
    #     session['replay_bot'].abort()

    if current_user.is_authenticated:
        # clients.pop(current_user.email, None)
        redis.hdel('clients', current_user.email)
        # remove any client reference in mp_table:
        table_json = redis.get('mp_table')
        if table_json:
            table_obj = loads(table_json)
            print "table ", table_obj
            gcandidates = table_obj[session['game_type']]
            print "candidates: ", gcandidates
            gcandidates = [item for item in gcandidates if item[0] != current_user.id]
            if len(gcandidates) != 0:
                table_obj[session['game_type']] = gcandidates
            else:
                table_obj.pop(session['game_type'], None)

            if table_obj:  # if not empty
                redis.set('mp_table', dumps(table_obj))
            else:  # remove if empty:
                redis.delete('mp_table')

        user_d.pop(current_user.email, None)  # remove user from connected users

    print 'Client disconnected ', request.sid


def serve_new_hand(user, sid, multi_player=False):
    """
    Generate the new hand according to the config and send a message to the client about it.

    :param user_email: user db object
    :param sid: session id
    :param multi_player: flag signaling multi player game or not. When multi player, the mp_table
    structure on Redis DB, must be updated
    :return: a python dictionary describing the new hand. It is the same structure which is
    written in the Move DB using JSON encoding.
    """
    next_hand_record = None
    session_config = user_d[user.email]
    if len(session_config.content) > 0:
        hand = session_config.content.pop(0)
        hand = hand.upper()
        hand = hand.split()
        hand = dict(zip(_SHOE_FILE_ORDER, hand))

        next_hand_record = {'move': 'HAND', 'panel': hand}

        m2 = Move(uid=user.id, sid=sid, mv=dumps(next_hand_record),
                  play_role='', ts=datetime.now())
        db.session.add(m2)
        db.session.commit()

        print "Serving new HAND: %s" % hand
        # emit('hand', {'success': 'ok', 'hand': hand,
        #               'covered': session['game_cfg']['covered'],
        #               'opponent_covered': session['game_cfg'][
        #                   'opponent_covered']}, room=clients[user.email])
        emit('hand', {'success': 'ok', 'hand': hand,
                      'card_flip': session['game_cfg']['card_flip'],
                      'covered': session['game_cfg']['covered'],
                      'opponent_covered': session['game_cfg'][
                          'opponent_covered']}, room=redis.hget('clients', user.email))

    else:
        print "session ended"
        # ends the session on the DB:
        gs = GameSession.query.filter_by(id=sid).first()
        gs.end = datetime.now()
        db.session.add(gs)
        db.session.commit()
        # emit('gameover', {}, room=clients[user.email])
        emit('gameover', {}, room=redis.hget('clients', user.email))
        if multi_player:
            # conn = Redis()
            table = redis.get('mp_table')
            if table:
                table_obj = loads(table)
                table_obj.pop(session['game_type'], None)
                if any(table_obj):
                    redis.set('mp_table', dumps(table_obj))
                else:
                    redis.delete('mp_table')

    return next_hand_record
