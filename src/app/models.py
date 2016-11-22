from . import db, socket_io, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin, current_user
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, session
from datetime import datetime
from flask_socketio import emit
from decorators import authenticated_only
from os.path import join, dirname, abspath, sep
from json import dumps

SHOE_FILE_ORDER = ['NK', 'N', 'U', 'C', 'CK', 'T', 'GC', 'PL']

user_d = dict()  # maps user names to Session objects


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=True, index=True)

    users = db.relationship('User', backref='role')

    def __repr__(self):
        return '<Role %r>' % self.name

    @staticmethod
    def inject_roles():
        roles = {'User': True,
                 'Administrator': False}

        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.default = roles[r]
            db.session.add(role)
        db.session.commit()

    @staticmethod
    def opposite_role(role):
        if role == 'Administrator':
            return u'User'
        else:
            return u'Administrator'

    @staticmethod
    def role_id_from_name(name):
        return 1 if name == 'Administrator' else 2


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    moves = db.relationship('Move', backref='user', lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        # Any new user created by the GUI has no admin privileges:
        if self.role is None:
            self.role = Role.query.filter_by(default=True).first()

    def __repr__(self):
        return '<User %r>' % self.username

    def is_administrator(self):
        return True if self.role.name == 'Administrator' else False

    def ping(self):
        # self.last_seen= datetime.utcnow()
        # db.session.add(self)
        pass

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    @staticmethod
    def inject_users():
        users = {'gp.jesi@gmail.com': ('gp.jesi', 'pippo', 'User'),
                 'admin@graphgames.org': ('admin', 'adminpw', 'Administrator')
                 }

        for u in users:
            user = User.query.filter_by(email=u).first()
            if user is None:
                role = 1 if (users[u][2] == 'Administrator') else 2
                user = User(email=u, username=users[u][0], password=users[u][1], role_id=role)
                db.session.add(user)
        db.session.commit()


class AnonymousUser(AnonymousUserMixin):
    def is_administrator(self):
        return False


class Move(db.Model):
    __tablename__ = 'moves'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.id'))
    sid = db.Column(db.Integer)
    mv = db.Column(db.String(64))
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
        types = {'Small TTT Solo': ({'html_file': 'ttt-page.html', 'shoe_file': 'game422-small.txt',
                                     'opponent_covered': True,
                                     'covered': {'NK': False, 'N': True, 'U': False, 'C': True,
                                                 'CK': False, 'T': False}}),
                 'Small TTT Solo Uncovered': ({'html_file': 'ttt-page.html', 'shoe_file':
                     'game422-small.txt', 'opponent_covered': False,
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

    # TODO: get the shoe_file from the context!
    user_d[current_user.username] = Configuration(config_file=session['game_cfg']['shoe_file'])
    user_d[current_user.username].purgelines()

    hand = user_d[current_user.username].content.pop(0)
    hand = hand.upper()
    # print hand
    hand = hand.split()
    # print hand
    hand = dict(zip(SHOE_FILE_ORDER, hand))
    # print hand

    emit('hand', {'success': 'ok', 'hand': hand,
                  'covered': session['game_cfg']['covered'],
                  'opponent_covered': session['game_cfg']['opponent_covered']})


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
    print current_user.username
    print current_user.email
    # It actually generates the timestamp now!
    m = Move(uid=current_user.id, sid=session['game_session'], mv=message['move'],
             ts=datetime.now())
    db.session.add(m)
    db.session.commit()
    if message['move'] == 'T' and message['moved_card'] == message['goal_card']:
        serve_new_hand(message['username'])


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
    user_d.pop(current_user.username, None)  # removed from the current playing users
    print('Client disconnected', request.sid)


def serve_new_hand(username):
    s = user_d[current_user.username]
    if len(s.content) > 0:
        hand = s.content.pop(0)
        hand = hand.upper()
        hand = hand.split()
        hand = dict(zip(SHOE_FILE_ORDER, hand))
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
