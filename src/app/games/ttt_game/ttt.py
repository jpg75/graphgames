from ... import socket_io, db, Configuration, app
from ...decorators import authenticated_only
from flask_security import current_user
from flask_socketio import emit
from flask import request, session
from datetime import datetime
from ...models import Move, GameSession, User, GameType
from json import dumps, loads
from redis import Redis
from tasks import timeout_task, bot_task, replay_task

user_d = dict()  # maps user names to game configuration session objects
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


def ttt_player_gen(tags=['CK', 'NK']):
    """
    Super simple generator. It just works for TTT players.
    :return:
    """
    for item in tags:
        yield item


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
        payload = serve_new_hand(current_user, session['game_session'], session['game_type'],
                                 session['game_cfg'], multi_player=False)
        emit('hand', payload, room=redis.hget('clients', current_user.email))

    else:  # manage the wait or start the game between the parties
        # get mptable if any
        table = redis.get('mp_table')
        print "table: ", table
        if table:
            table_obj = loads(table)
            print "table obj: ", table_obj
            mpdef = table_obj.get(str(session['game_type']), None)
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

                # timeout_task.delay(gid=session['game_type'], sid=session['game_session'],
                #                    struct=session['game_cfg'])

        else:  # table not yet available on redis
            # makes the table and set current player as a candidate for current game:
            print "Building table and set current game id: %d for user %d in session %d" % (
                session['game_type'], current_user.id, session['game_session'])
            redis.set('mp_table',
                      dumps({session['game_type']: [(current_user.id, session['game_session'])]}))
            redis.set('srv_credentials', dumps({'host': 'localhost', 'port': app.config[
                'SOCKET_IO_PORT'], 'msg': 'notify_groups'}))
            print "set srv_credentials var in redis: ", redis.get('srv_credentials')

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
        emit('set_replay', {}, room=redis.hget('clients', current_user.email))

    elif session['game_cfg']['enable_multiplayer'] and session['game_cfg']['enable_bot']:
        print "Client have to play a multi-user game (AI)"
        emit('set_multiplayer', {}, room=redis.hget('clients', current_user.email))

    elif session['game_cfg']['enable_multiplayer'] and not session['game_cfg']['enable_bot']:
        print "Client have to play a multi-user game"
        emit('set_multiplayer', {}, room=redis.hget('clients', current_user.email))

    else:
        print "Simple game"
        tot_hands = len(user_d[current_user.email].content)
        payload = serve_new_hand(current_user, session['game_session'], session['game_type'],
                                 session['game_cfg'], multi_player=False)
        payload['total_hands_num'] = tot_hands
        emit('hand', payload, room=redis.hget('clients', current_user.email))


@socket_io.on('move')
@authenticated_only
def move(message):
    print "received move: ", message
    print current_user.id
    print current_user.email
    # It actually generates the timestamp now!
    m = Move(uid=current_user.id, sid=session['game_session'], mv=dumps(message),
             play_role=message['player'], ts=datetime.now())
    db.session.add(m)
    db.session.commit()

    # final move for the current hand:
    if message['move'] == 'T' and message['moved_card'] == message['goal_card']:
        print "Game changing move"
        """ Serve a new hand and generate the dummy move 'HAND' which represents the start of a hand:
            multi player case:"""
        if session['game_cfg']['enable_multiplayer']:
            print "move multi player"
            print "serving new hand to the current user: ", current_user.id
            # serve next_hand to the current user or quits game if no more hands
            next_hand = serve_new_hand(current_user, session['game_session'], session['game_type'],
                                       session['game_cfg'], multi_player=True)
            if next_hand:
                # emitting 'toggle_player' no longer required
                emit('hand', next_hand, room=redis.hget('clients', current_user.email))
            else:
                emit('gameover', {}, room=redis.hget('clients', current_user.email))

            # when bots are enabled and next is NK, then bot task must be triggered:
            # CAREFUL: the else branch must run ONLY when enable_bot is disabled!!
            if next_hand and session['game_cfg']['enable_bot'] and next_hand['panel']['PL'] == 'NK':
                print "multi player bot triggered"
                bot_task.delay(url='redis://localhost:6379/0', sid=session['game_session'],
                               hand=next_hand['panel'][next_hand['panel']['PL']],
                               up=next_hand['panel']['U'], target=next_hand['panel']['T'])

                print "hand ", next_hand['panel'][next_hand['panel']['PL']]
                print "up: ", next_hand['panel']['U']
                print "target ", next_hand['panel']['T']

            elif not session['game_cfg']['enable_bot']:
                """ this MP session os not with a bot, but with a human: we send the hand to the
                    other party"""
                # get the other party from Redis:
                gitem, gid = redis.hmget(str(current_user.id) + ':' + str(session['game_session']),
                                         'group', 'gid')
                other_user_id, other_user_sid = gitem.split(':')
                other_user = User.query.filter_by(id=int(other_user_id)).first()
                # send the last move to the other party:
                emit('external_move', {'move': message['move'], 'player': message['player']},
                     room=redis.hget('clients', other_user.email))

                print "Serving new hand to the other player: %d" % other_user.id
                # serve new hand or quit message if no more hands available
                payload = serve_new_hand(other_user, int(other_user_sid),
                                         session['game_type'],
                                         session['game_cfg'], multi_player=True)
                if payload:
                    # emitting 'toggle_player' no longer required
                    emit('hand', payload, room=redis.hget('clients', other_user.email))
                else:
                    emit('gameover', {}, room=redis.hget('clients', other_user.email))

        else:  # single player: just send hand message: no need to send set_player or invert_players
            payload = serve_new_hand(current_user, session['game_session'], session['game_type'],
                                     session['game_cfg'], multi_player=False)
            emit('hand', payload, room=redis.hget('clients', current_user.email)) if payload else \
                emit('gameover', {}, room=redis.hget('clients', current_user.email))

    else:  # just a regular move:
        player = message['player']
        if player == 'CK':
            player = 'NK'
        else:
            player = 'CK'

        print "Basic move"
        if session['game_cfg']['enable_multiplayer']:
            print "move multi player"
            # if bot enabled, trigger the celery bot:
            if session['game_cfg']['enable_bot']:
                print "multi player bot triggered"
                bot_task.delay(url='redis://localhost:6379/0',
                               sid=session['game_session'],
                               hand=message['panel'][player],
                               up=message['panel']['U'],
                               target=message['panel']['T'])

            else:  # multi player among humans: forward the move to the other parties
                # get the other party from Redis:
                gitem, gid = redis.hmget(str(current_user.id) + ':' + str(session['game_session']),
                                         'group', 'gid')
                other_user = User.query.filter_by(id=int(gitem.split(':')[0])).first()
                print "Forward move to uid: %d" % other_user.id

                # No need to trigger a toggle_player since it is automatic in external_move
                emit('external_move', {'move': message['move'], 'player': message['player']},
                     room=redis.hget('clients', other_user.email))

                print "toggle player to the current user: ", current_user.id
                emit('toggle_players', {'player': player},
                     room=redis.hget('clients', current_user.email))

        else:  # single player: just send toggle_player message
            print "Move toggle player"
            emit('toggle_players', {'player': player},
                 room=redis.hget('clients', current_user.email))


@socket_io.on('notify_groups')
def notify_groups_handler(message):
    """
    It is called by the timeout task. It generates the messages to setup the groups of players
    related to a particular game id. These information are collected from the message received.
    The clients eventually excluded from the group formation are informed by an
    'abort_multiplayer' message.

    For each element in a game group tuple (a pair in the TTT case), it generates a Structure in
    Redis as follows: uid:sid -> {'group': <uid:sid>[ uid:sid...], 'gid': <gid>}. In this manner,
    any client and the server have access to the group of players.

    :param message: carries the following json object:
        {
            "gid": gid,
            "groups": [],
            "failed": []
        }
    :return:
    """
    print "in handler, message: ", message
    ms = loads(message)

    for group in ms['groups']:
        print "Group: ", group
        # put each group into the redis set related to the game group: 'groups_game_<gid>'

        redis.hmset(str(group[0][0]) + ':' + str(group[0][1]),
                    {'group': str(group[1][0]) + ':' + str(
                        group[1][1]), 'gid': str(ms['gid'])})
        redis.hmset(str(group[1][0]) + ':' + str(group[1][1]),
                    {'group': str(group[0][0]) + ':' + str(
                        group[0][1]), 'gid': str(ms['gid'])})

        gc = GameType.query.filter_by(id=ms['gid']).first()
        gen = ttt_player_gen()  # WARNING: in ttt no more than 2 participant
        for participant in group:
            print "participant ", participant
            u = User.query.filter_by(id=participant[0]).first()
            rns = redis.hget('clients', u.email)
            if rns:
                next_p = gen.next()
                print "Set to player role %s user: %s" % (next_p, u.email)
                emit('set_player_role', {'player_role': next_p}, room=redis.hget('clients',
                                                                                 u.email))
                print "Set player and role"
                payload = serve_new_hand(u, participant[1], ms['gid'], loads(gc.params),
                                         multi_player=True)
                emit('hand', payload, room=redis.hget('clients', u.email))

    for failed in ms['failed']:
        # for failure in failed:
        print "failed: ", failed
        u = User.query.filter_by(id=failed[0]).first()
        # print "user: ", u
        rns = redis.hget('clients', u.email)
        print "rns: ", rns
        if rns:
            emit('abort_multiplayer', {}, room=rns)

            # it should clean the mp_table stored in Redis here!


@socket_io.on('expired')
@authenticated_only
def expired_timeout_handler(message):
    """
    A client user took to long and the game ended. Here the session is closed since it is
    considered a valid one, but with poor performance.

    :param message:
    :return:
    """
    print "Received 'exprired' event, closing session: ", session['game_session']
    _close_game_session(sid=session['game_session'])


@socket_io.on('connect')
def connect():
    print "A client connected: %s" % request.sid
    if current_user.is_authenticated:
        redis.hset('clients', current_user.email, request.sid)
    # print clients
    print redis.hgetall('clients')


@socket_io.on('disconnect')
def disconnect():
    if current_user.is_authenticated:
        print "disconnecting user %d..." % current_user.id
        # clients.pop(current_user.email, None)
        redis.hdel('clients', current_user.email)
        # removes its own group reference
        redis.delete(str(current_user.id) + ':' + str(session['game_session']))
        # remove any client reference in mp_table:
        table_json = redis.get('mp_table')
        if table_json:
            table_obj = loads(table_json)
            print "table ", table_obj
            print session['game_type']
            gcandidates = table_obj[str(session['game_type'])]
            print "candidates: ", gcandidates
            # take all candidates which are not me:
            gcandidates = [item for item in gcandidates if item[0] != current_user.id]
            print "candidates: ", gcandidates
            if len(gcandidates) != 0:
                table_obj[str(session['game_type'])] = gcandidates
            else:  # remove the whole entry for this game type if no candidates left:
                table_obj.pop(str(session['game_type']), None)

            if table_obj:  # if not empty
                redis.set('mp_table', dumps(table_obj))
            else:  # remove if empty:
                redis.delete('mp_table')

        user_d.pop(current_user.email, None)  # remove user from connected users

    print 'Client disconnected ', request.sid


def serve_new_hand(user, sid, gid=1, gconfig=None, multi_player=False):
    """
    Generate the new hand according to the config and send a message to the client about it.
    When the session ends it is responsible to close the session(s) on db.

    :param user_email: user db object
    :param sid: session id
    :param gid: game id
    :param gconfig: dictionary holding the game configuration
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

        print "Serving new HAND: %s to user: %d sid: %d" % (hand, user.id, sid)
        timeout = 900  # default time-out: 15 minutes
        if gconfig.get('timeout', None):
            timeout = gconfig['timeout']

        next_hand_record = {'success': 'ok', 'hand': hand,
                            'card_flip': gconfig['card_flip'],
                            'covered': gconfig['covered'],
                            'opponent_covered': gconfig['opponent_covered'],
                            'timeout': timeout, 'sid': sid}

    else:
        print "session ended"
        _close_game_session(sid)

        if multi_player:
            table = redis.get('mp_table')
            print "table: ", table
            if table:
                table_obj = loads(table)
                lst = table_obj.pop(str(gid), None)
                # ends the sessions part of the multi player match
                for item in lst:
                    _, s = item
                    if sid != s:
                        _close_game_session(s)

                if any(table_obj):
                    redis.set('mp_table', dumps(table_obj))
                else:
                    redis.delete('mp_table')

    return next_hand_record


def _close_game_session(sid):
    """
    Close a game session having the specified sid.

    :param sid:
    :return:
    """
    gs = GameSession.query.filter_by(id=sid).first()
    gs.end = datetime.now()
    gs.score = Move.query.filter(Move.sid == sid,
                                 ~Move.mv.contains('\"move\": \"HAND\"')).count()
    db.session.add(gs)
    db.session.commit()
