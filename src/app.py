#!/usr/bin/env python

# TODO:
# capability of having distinct configs and making new ones

__author__ = 'Gian Paolo Jesi'

from flask import Flask, render_template, session, request, redirect, \
    url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
# import json
from flask_script import Manager, Shell
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import data_required
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand

from util.config import Configuration
from util.db_mgt import *
import os
import datetime

PORT = 5000
SHOE_FILE = 'game422-small.txt'
SHOE_FILE_ORDER = ['NK', 'N', 'U', 'C', 'CK', 'T', 'GC', 'PL']
DT_FORMAT = "%Y-%m-%d %H:%M:%S"
DB_DEFAULT = './graphgames.sqlite'

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

basedir = os.path.abspath(os.path.dirname(__file__))

users = dict()  # maps username -> session obj
cfg = Configuration(config_file=SHOE_FILE)
cfg.purgelines()
hands = cfg.content

db_conn, db_cursor = connect_db(file_name=DB_DEFAULT)
current_uid = get_last_uid(db_cursor)
current_sid = get_last_sid(db_cursor)
print "current_uid: ", current_uid
print "current_sid: ", current_sid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SECRET_KEY'] = 'itsasecret!'

db = SQLAlchemy(app)
manager = Manager(app)

def make_shell_context():
    """
    Make objects available to the interactive shell environment.

    :return:a dictionary with all the exposed elements
    """
    return dict(app=app, db=db, User=User, Role=Role, Move=Move, Session=Session,
                SessionType=SessionType)

manager.add_command("shell", Shell(make_context=make_shell_context))

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)
bootstrap = Bootstrap(app)
moment = Moment(app)
socket_io = SocketIO(app, async_mode=async_mode)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(64), unique=True)

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)

    moves = db.relationship('Move', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % self.username


class Move(db.Model):
    __tablename__ = 'moves'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.id'))
    sid = db.Column(db.Integer)
    mv = db.Column(db.String(64))
    ts = db.Column(db.DateTime)

    def __repr__(self):
        return '<Move %r made by user %r at %r>' % (self.mv, self.uid, self.ts)


class Session(db.Model):
    __tableName__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer)
    type = db.Column(db.String)
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)

    def __repr__(self):
        return 'Session %r, type %, started: %r, ended: %r' % (self.id, self.type, self.start,
                                                               self.end)


class SessionType(db.Model):
    __tablename__ = 'session_types'
    id = db.Column(db.Integer, primary_key=True)
    params = db.Column(db.Text)
    info = db.Column(db.Text)

    def __repr__(self):
        return 'Session: %r' % self.info


db.create_all()
db.session.commit()


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[data_required()])
    password = PasswordField('Password', validators=[data_required()])
    submit = SubmitField('Submit')


class Session(object):
    def __init__(self, sid, uid, username, room=None):
        self.sid = sid
        self.uid = uid
        self.type = 1
        self.username = username
        self.ts_start = datetime.datetime.now()
        self.ts_end = None
        self.room = room


class TTTSession(Session):
    def __init__(self, sid, uid, username, room=None, shoe_file='game422-small.txt'):
        super(TTTSession, self).__init__(sid, uid, username, room)

        cfg = Configuration(config_file=shoe_file)
        cfg.purgelines()
        self.hands = cfg.content
        self.goal_card = self.hands[0]
        self.goal_card = self.goal_card.split()
        self.goal_card = self.goal_card[6]


@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            session['known'] = False
        else:
            session['known'] = True

        session['name'] = form.name.data
        form.name.data = ''
        return redirect(url_for('index'))

    return render_template('index.html',
                           form=form, name=session.get('name'),
                           known=session.get('known', False))


# @app.route('/')
# def index():
#     print "serving"
#     return render_template('index.html', async_mode=socket_io.async_mode)


@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@socket_io.on('login')
def login(message):
    """
    When a client login. It replies with a 'game response' message holding everything required
    to start the game:
    + status: failure/success
    + hand: where the card must be located, which is the goal card, whose player turn is
    + covered cards: which card must be covered
    + opponent_covered: whether the current player opponent must be covered or not

    :param message: json message with proposed username. No real auth.
    :return:
    """
    global users, current_uid, current_sid

    print "User: %s logged in" % message['username']
    current_uid += 1
    inject_user(db_conn, uid=current_uid, username=message['username'])

    current_sid += 1
    users[message['username']] = TTTSession(current_sid, current_uid, message['username'])
    inject_session(db_conn, users[message['username']])

    content = users[message['username']].hands.pop(0)
    content = content.upper()
    # print content
    content = content.split()
    # print content
    hand = dict(zip(SHOE_FILE_ORDER, content))
    # print hand

    # generate a DB entry for username if not in use

    emit('hand', {'success': 'ok', 'hand': hand,
                  'covered': {'NK': False, 'N': True, 'U': False, 'C': True,
                              'CK': False, 'T': False},
                  'opponent_covered': True})


@socket_io.on('move')
def move(message):
    """
    When receiving a move from the client.
    :param message:
    :return:
    """
    store(message['username'], message['move'], message['ts'], message['moved_card'])
    if message['move'] == 'T' and message['moved_card'] == users[message['username']].goal_card:
        serve_new_hand(message['username'])


@socket_io.on('connect')
def test_connect():
    print "A client connected"
    # emit('my response', {'data': 'Connected', 'count': 0})


@socket_io.on('disconnect')
def test_disconnect():
    print('Client disconnected', request.sid)


def store(user, move, time, moved_card):
    print "Valid move received from user: %s, move: %s, at time: %s, moved_card: %s " % (user, move,
                                                                                         time,
                                                                                         moved_card)
    s = users[user]
    inject_move(db_conn, s.uid, s.sid, move, time)


def serve_new_hand(username):
    s = users[username]
    if len(s.hands) > 0:
        content = s.hands.pop(0)
        content = content.upper()
        content = content.split()
        s.goal_card = content[6]
        hand = dict(zip(SHOE_FILE_ORDER, content))
        print "Serving new HAND: %s" % hand
        emit('hand', {'success': 'ok', 'hand': hand,
                      'covered': {'NK': False, 'N': True, 'U': False, 'C': True,
                                  'CK': False, 'T': False},
                      'opponent_covered': True})

    else:  # gamedef make_shell_context():
        print "session ended"
        emit('gameover', {})


@manager.command
def run():
    socket_io.run(app, port=PORT, debug=True)


if __name__ == '__main__':
    global next_uid

    manager.run()
    print "Started Game Server at port: %d!" % PORT

# Lidia De Giovanni
