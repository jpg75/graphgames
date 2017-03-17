from . import db, socket_io
from flask_security import UserMixin, RoleMixin, SQLAlchemyUserDatastore, current_user
from flask_security.utils import encrypt_password
from flask import current_app, request, session
from datetime import datetime
from flask_socketio import emit
from decorators import authenticated_only
from os.path import join, dirname, abspath, sep
from json import dumps

SHOE_FILE_ORDER = ['NK', 'N', 'U', 'C', 'CK', 'T', 'GC', 'PL']

user_d = dict()  # maps user names to Session objects


def loadFile(fqn_file):
    """Returns a list with all the lines in the file. The end line is purged.
    The file can include its full path name.
    """
    with open(fqn_file) as f:
        return f.read().splitlines()


class Configuration(object):
    '''
    Basic configuration class.
    It reads a file with simple key value lines and makes a corresponding
    dictionary.
    '''

    def __init__(self, config_file='config.txt', rel_path='data'):
        '''
        Constructor
        '''
        self._data = dict()
        cur_dir = dirname(abspath('file'))
        self.content = loadFile(join(sep, cur_dir, rel_path, config_file))

    def purgelines(self):
        """Remove white spaces and removes comments and blank lines."""
        lines = []
        for line in self.content:
            if line.startswith('#') or line.startswith('//') or line == '' or line.isspace():
                continue
            else:
                lines.append(line.strip())

        self.content = lines

    def initialize(self):
        """Generate the dictionary with <parameter> -> <value> maps.
        """
        for line in self.content:
            k, v = line.split('=')
            self._data[k.strip()] = v.strip()

    def getParam(self, param):
        return self._data.get(param)

    def listParams(self):
        return self._data.keys()


"""Many to many relationship: a user can have many roles and vice-versa"""
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id')))


class Role(db.Model, RoleMixin):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return self.name


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password = db.Column(db.String())  # should be 'password'
    active = db.Column(db.Boolean, default=False)  # should be 'active'

    # enables Confirmable:
    confirmed_at = db.Column(db.DateTime())

    # enables Trackable:
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(20))
    current_login_ip = db.Column(db.String(20))
    login_count = db.Column(db.Integer, default=0)

    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)

    moves = db.relationship('Move', backref='user', lazy='dynamic')

    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __repr__(self):
        return self.email

    def is_administrator(self):
        return True if 'admin' in self.roles else False


user_datastore = SQLAlchemyUserDatastore(db, User, Role)


def init_db():
    with current_app.app_context():
        db.create_all()

        default_role = user_datastore.find_or_create_role(
            'user', description="Simple user")
        adm_role = user_datastore.find_or_create_role(
            'admin', description="System administrator: has no limits")

        if not User.query.first():
            u = user_datastore.create_user(
                email='admin@graphgames.com',
                password=encrypt_password('adminpw'))
            user_datastore.add_role_to_user(
                u, adm_role)

            u = user_datastore.create_user(
                email='gp.jesi@gmail.com',
                password=encrypt_password('pippo'))
            user_datastore.add_role_to_user(
                u, default_role)

        db.session.commit()

        if not GameType.query.first():
            GameType.inject_game_types()


class Move(db.Model):
    __tablename__ = 'moves'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.id'))
    sid = db.Column(db.Integer)
    mv = db.Column(db.String(64))
    play_role = db.Column(db.String(64))
    ts = db.Column(db.DateTime)

    def __repr__(self):
        return '<Move %r made by user %r at %r>' % (self.mv, self.uid, self.ts)


class GameSession(db.Model):
    __tableName__ = 'game_sessions'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.id'))
    type = db.Column(db.Integer, db.ForeignKey('game_types.id'))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)

    def __repr__(self):
        return 'Session %r, type %r, started: %r, ended: %r' % (self.id, self.type, self.start,
                                                                self.end)


class GameType(db.Model):
    __tablename__ = 'game_types'
    id = db.Column(db.Integer, primary_key=True)
    params = db.Column(db.Text)
    info = db.Column(db.Text)

    def __repr__(self):
        return 'Session: %r' % self.info

    @staticmethod
    def inject_game_types():
        # maps description -> tuple
        # the tuple has just a description of the configuration as a python object (dictionary)
        types = {'Small TTT Solo': ({'html_file': 'admin/games/ttt-page.html', 'shoe_file':
            'game422-small.txt',
                                     'replay': False,
                                     'opponent_covered': True,
                                     'covered': {'NK': False, 'N': True, 'U': False, 'C': True,
                                                 'CK': False, 'T': False}}),
                 'Small TTT Solo Uncovered': (
                 {'html_file': 'admin/games/ttt-page.html', 'shoe_file':
                     'game422-small.txt', 'opponent_covered': False, 'replay': False,
                  'covered': {'NK': False, 'N': True, 'U': False,
                              'C': True, 'CK': False, 'T': False}})
                 }

        for t in types:
            gt = GameType.query.filter_by(info=t).first()
            if gt is None:
                # Careful: python dicts must be converted in json strings here!
                gt = GameType(params=dumps(types[t]), info=t)
                db.session.add(gt)

        db.session.commit()


@socket_io.on('replay_ready')
@authenticated_only
def replay_ready(message):
    """
    Called when 'replay_ready' message is received. The background task is spawned.

    :return:
    """
    from tasks import replay_task

    # here start the background thread for replay session:
    replay_task.delay(url='redis://localhost:6379/0', sid=session['game_session'],
                      struct=session['game_cfg'])


@socket_io.on('login')
@authenticated_only
def login(message):
    """
    The actual login is carried out by the web app through flask_login.
    Here the login represents a sort of confirmation.
    It replies with a 'game response' message holding everything required
    to start the game:
    + status: failure/success
    + hand: where the card must be located, which is the goal card, whose player turn is
    + covered cards: which card must be covered
    + opponent_covered: whether the current player opponent must be covered or not

    :param message: json message with proposed username. No real auth.
    :return:
    """
    if not current_user.is_authenticated:
        return

    print current_user
    print "session ", session['game_cfg']
    print "session: ", session['game_type']

    if session['game_cfg']['replay']:
        print "Client have to replay a session"
        emit('set_replay', {})

    else:
        user_d[current_user.email] = Configuration(config_file=session['game_cfg']['shoe_file'])
        user_d[current_user.email].purgelines()

        serve_new_hand(current_user.email)


@socket_io.on('move')
@authenticated_only
def move(message):
    """
    When receiving a move from the client.
    :param message:
    :return:
    """
    print "received move: ", message['move']
    print current_user
    print current_user.id
    print current_user.email
    # It actually generates the timestamp now!
    m = Move(uid=current_user.id, sid=session['game_session'], mv=message['move'],
             play_role=message['player'], ts=datetime.now())
    db.session.add(m)
    db.session.commit()

    if message['move'] == 'T' and message['moved_card'] == message['goal_card']:
        # Serve a new hand and the dummy move 'HAND' which represents the start of a hand:
        serve_new_hand(message['username'])

    else:
        player = message['player']
        if player == 'CK':
            player = 'NK'
        else:
            player = 'CK'
        emit('toggle_players', {'player': player})


@socket_io.on('connect')
@authenticated_only
def test_connect():
    print "A client connected"
    # if current_user.is_authenticated():
    #    print "A client connected"
    # else:
    #    return False


@socket_io.on('disconnect')
@authenticated_only
def test_disconnect():
    user_d.pop(current_user.email, None)  # remove user from connected users

    print('Client disconnected', request.sid)


def serve_new_hand(username):
    s = user_d[current_user.email]
    if len(s.content) > 0:
        hand = s.content.pop(0)
        hand = hand.upper()
        hand = hand.split()
        hand = dict(zip(SHOE_FILE_ORDER, hand))

        m2 = Move(uid=current_user.id, sid=session['game_session'], mv='HAND ' + dumps(hand),
                  play_role='', ts=datetime.now())
        db.session.add(m2)
        db.session.commit()

        print "Serving new HAND: %s" % hand
        emit('hand', {'success': 'ok', 'hand': hand,
                      'covered': session['game_cfg']['covered'],
                      'opponent_covered': session['game_cfg']['opponent_covered']})

    else:
        print "session ended"
        # ends the session on the DB:
        gs = GameSession.query.filter_by(id=session['game_session']).first()
        gs.end = datetime.now()
        db.session.add(gs)
        db.session.commit()
        emit('gameover', {})
