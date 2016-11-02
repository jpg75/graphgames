#!/usr/bin/env python

from flask import Flask
from flask_socketio import SocketIO

socket_io = SocketIO()

def create_app(debug=False):
    """Create an application."""
    app = Flask(__name__)
    app.debug = debug
    app.config['SECRET_KEY'] = 'gjr39dkjn344_!67#'

    # from .main import main as main_blueprint
    # app.register_blueprint(main_blueprint)

    socket_io.init_app(app)
    return app

app = create_app(debug=True)

if __name__ == '__main__':
    socket_io.run(app)