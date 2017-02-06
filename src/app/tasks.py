from flask import make_response
from . import celery
from models import Move
from csv import writer
from io import BytesIO
from flask_socketio import SocketIO
from time import sleep


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


@celery.task
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


@celery.task
def replay_task(url, sid):
    """
    Generate a local web socket linked to the queue url. The task process is tied to this
    communication link for its lifespan.
    Takes all the element of a game session and sends back to the client the exact sequence of
    events scheduling them with the exact timing.

    :param url: A (Redis) queue url
    :param sid: session ID
    :return:
    """
    local_socket = SocketIO(message_queue=url)
    # get all the session moves
    moves = Move.query.filter_by(sid=sid).all()
    schedules = []
    i = 0
    for move in moves[1:]:
        c = move.ts - moves[i].ts
        schedules.append(c.total_seconds())
        local_socket.emit('replay', {'move': moves[i].mv})
        sleep(c.total_seconds())
        i += 1

    pass
