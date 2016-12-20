from flask import make_response
from . import celery
from models import Move
from csv import writer
from io import BytesIO


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


