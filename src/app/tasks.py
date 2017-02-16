from flask import make_response
from . import celery
from models import Move
from csv import writer
from io import BytesIO
from flask_socketio import SocketIO
from time import sleep
from json import loads


def csv2string(data):
    """
    Format a list of items into a CSV string.

    :param data: list of items
    :return: a CSV string for the arguments
    """
    si = BytesIO()
    cw = writer(si)
    cw.writerow(data)
    return si.getvalue().strip('\r\n')


@celery.task()
def download_task(sid):
    """
    Extract all moves belonging to the provided sid and pack them in a csv format.
    The extraction is returned as an http response and allows the download of the data.

    :param sid:  the session id
    :return: http response object
    """
    moves = Move.query.filter_by(sid=sid).all()

    # put column headers:
    s = csv2string(['MOVE', 'TIMESTAMP', 'MOVE_ID', 'USER_ID', 'PLAY_ROLE']) + '\n'
    for move in moves:
        s = s + csv2string([move.mv, move.ts, move.id, move.uid, move.play_role]) + '\n'

    # We need to modify the response, so the first thing we
    # need to do is create a response out of the CSV string
    response = make_response(s)
    # This is the key: Set the right header for the response
    # to be downloaded, instead of just printed on the browser
    response.headers["Content-Disposition"] = "attachment; filename=moves_data.csv"
    return response


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
        # print "Processing move: ", m
        # NOTE:  do not like the fact that a generic method "knows" about hand and simple move
        # kind of move inside the DB. A refined version would be agnostic! In should send
        # whatever found in DB entries, since each game is responsible to interpret its own data.
        if m.startswith('HAND'):
            hand = m.replace('HAND ', '')
            local_socket.emit('replay', {'success': 'ok', 'hand': loads(hand),
                                         'move': None,
                                         'covered': struct['covered'],
                                         'opponent_covered': struct['opponent_covered']})
            print "replaying: %s" % hand
        else:
            local_socket.emit('replay', {'success': 'ok', 'hand': None,
                                         'move': m,
                                         'covered': struct['covered'],
                                         'opponent_covered': struct['opponent_covered']})
            print "replaying: %s" % m

        fsec = c.total_seconds()
        print "Waiting: %f seconds" % fsec
        sleep(fsec)
        i += 1
        print i
        # send the last move:
        if i == len(moves) - 1:
            local_socket.emit('replay', {'success': 'ok', 'hand': None,
                                         'move': moves[i].mv,
                                         'covered': struct['covered'],
                                         'opponent_covered': struct['opponent_covered']})
            print "replaying: %s" % moves[i].mv

    sleep(0.5)  # by default wait half second before quitting the game
    local_socket.emit('gameover', {'comment': 'Replay ended'})  # end the game
    print "Game over."
