import ttt_game.ttt as games
from flask_socketio import emit


class GameSocket(object):
    def __init__(self, handle):
        self.handle = handle
        self.connected = True
        self.config = None  # Game dependent: any relevant data for each game session socket

    def emit(self, event, data):
        emit(event, data, room=self.handle)
