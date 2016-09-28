#!/usr/bin/env python

__author__ = 'Gian Paolo Jesi'

from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
import json
from util.config import Configuration

PORT = 5000

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

SHOE_FILE = 'game422-small.txt'
c = Configuration(config_file=SHOE_FILE)
c.purgelines()
hands = c.content
# print hands

app = Flask(__name__)
app.config['SECRET_KEY'] = 'itsasecret!'
socket_io = SocketIO(app, async_mode=async_mode)
thread = None

def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socket_io.sleep(10)
        count += 1
        socket_io.emit('my response',
                       {'data': 'Server generated event', 'count': count},
                       namespace='/test')


@app.route('/')
def index():
    global thread
    print "serving"
    # if thread is None:
    #    thread = socket_io.start_background_task(target=background_thread)
    return render_template('index.html', async_mode=socket_io.async_mode)


@socket_io.on('login')
def login(message):
    """
    When a client login. It replies with a 'game response' message holding everything required
    to start the game:
    + status: failure/success
    + hand: where in card must be located, which is the goal card, whose player turn is
    + covered cards: which card must be covered

    :param message: json message with proposed username. No real auth.
    :return:
    """
    print "User: %s logged in" % message['username']
    # generate a DB entry for username if not in use

    emit('hand', {'success': 'ok', 'hand': {'NK': '3C', 'N': '4H', 'U': '2H', 'C': '3H',
                                            'CK': '2C', 'T': '4C', 'GC': '2H', 'PL': 'CK'},
                  'covered': {'NK': True, 'N': True, 'U': False, 'C': True,
                              'CK': False, 'T': False}})


@socket_io.on('move')
def move(message):
    """
    When receiving a move from the client.
    :param message:
    :return:
    """
    store(message['username'], message['move'], message['ts'])


@socket_io.on('my event', namespace='/test')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': message['data'], 'count': session['receive_count']})


@socket_io.on('my broadcast event', namespace='/test')
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socket_io.on('join', namespace='/test')
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socket_io.on('leave', namespace='/test')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socket_io.on('close room', namespace='/test')
def close(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response', {'data': 'Room ' + message['room'] + ' is closing.',
                         'count': session['receive_count']},
         room=message['room'])
    close_room(message['room'])


@socket_io.on('my room event', namespace='/test')
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socket_io.on('disconnect request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()


@socket_io.on('my ping', namespace='/test')
def ping_pong():
    emit('my pong')


@socket_io.on('connect')
def test_connect():
    print "A client connected"
    # emit('my response', {'data': 'Connected', 'count': 0})


@socket_io.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


def store(user, move, time):
    print "Vaid move received from user: %s, move: %s, at time: %s " % (user, move, time)
    pass


if __name__ == '__main__':
    print "Started Game Server at port:%d!" % PORT
    socket_io.run(app, port=PORT, debug=True)
