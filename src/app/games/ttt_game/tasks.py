from ... import db
from time import sleep
from ... import celery
from celery.contrib.abortable import AbortableTask, Task
from ...models import Move, User, MPSession
from flask_socketio import SocketIO
from parser import RuleParser
from json import dumps, loads
from redis import Redis
from datetime import datetime
from random import uniform


class NotifierTask(Task):
    """Task that sends notification on completion."""
    abstract = True

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        print "After return handler!"
        print retval
        conn = Redis()
        srv = loads(conn.get('srv_credentials'))
        from socketIO_client import SocketIO as skio
        with skio('localhost', srv['port']) as s:
            s.emit('notify_groups', retval)


@celery.task(bind=True, base=NotifierTask)
def timeout_task(self, gid, sid, struct):
    """
        Generate a local web socket linked to the queue url. The task process is tied to this
        communication link for its lifespan.
        Takes all the element of a game session and sends back to the client the exact sequence of
        events scheduling them with the exact timing.
        The code is verbose using print statements. They are visible through the celery worker
        console in debug mode.

        :param gid: game id of the (multi-player) game associated
        :param sid: session ID
        :param struct: dictionary with game instance parameters
        :return:
        """
    print "inside timeout task"
    sleep(5)
    print "exit from sleep"
    conn = Redis()
    mpt = loads(conn.get('mp_table'))
    result = {'gid': gid,
              'groups': [],
              'failed': []
              }
    print "mpt: ", mpt

    # making groups:
    for game_id in mpt:
        print "game_id: -%s-, gid: -%s-" % (game_id, gid)
        if int(game_id) == int(gid):  # the timer is just for this game id, skip the others!
            l = mpt[game_id]
            print "l: ", l
            groups = [l[i:i + struct['max_users']] for i in xrange(0, len(l), struct['max_users'])]
            print "groups: ", groups
            for group in groups:
                print "group: ", group
                sids = ' '.join(str(x[1]) for x in group)
                users = ' '.join(str(x[0]) for x in group)

                if len(group) <= struct['max_users'] and len(group) >= struct['min_users']:
                    print "appending group"
                    result['groups'].append(group)

                    mps = MPSession(gid=game_id, sids=sids, users=users)
                    db.session.add(mps)
                    db.session.commit()

                else:
                    print "appending to failed!"
                    for item in group:
                        result['failed'].append(item)

            print result

        else:
            print "NOT EQUAL!"

    return result


@celery.task(bind=True)
def replay_task(self, url, sid, struct):
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
        # if self.is_aborted:
        #     return

        c = move.ts - moves[i].ts
        m = moves[i].mv
        fsec = c.total_seconds()
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

        # if self.is_aborted:
        #     return

        i += 1
        # send the last move:
        if i == len(moves) - 1:
            print "Send last move!"
            local_socket.emit('replay', {'success': 'ok', 'hand': None,
                                         'move': m_struct,
                                         'next_move_at': fsec,
                                         'covered': struct['covered'],
                                         'opponent_covered': struct['opponent_covered']})
            print "replaying: %s" % m_struct

    sleep(5.0)  # by default wait half second before quitting the game
    local_socket.emit('gameover', {'comment': 'Replay ended'})  # end the game
    # session.pop('replay_bot', None)

    print "Game over."


@celery.task()
def bot_task(url, sid, hand, up, target, player_role='NK', fake_delay=3.0, memory_size=2):
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
    :param player_role: role played, default NK
    :param fake_delay: delay to mimic a human-like reply
    :param memory_size: how many moves (per player) the bot can remember (e.g., 2 means: 2 bot
    moves and 2 human player moves)
    """
    print "TTT bot started!"
    rulep = RuleParser()
    rulep.load_rules()
    local_socket = SocketIO(message_queue=url)
    # get the last game state from DB:
    memory = Move.query.filter_by(sid=sid).order_by(Move.ts.desc()).limit(memory_size * 2)
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
