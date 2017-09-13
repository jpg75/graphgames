from . import db
from flask_security import UserMixin, RoleMixin, SQLAlchemyUserDatastore
from flask_security.utils import hash_password
from flask import current_app
from datetime import datetime
from json import dumps

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
            u = user_datastore.create_user(email='admin@graphgames.org',
                                           password=hash_password('adminpw'))
            user_datastore.add_role_to_user(u, adm_role)

            u = user_datastore.create_user(email='bot@graphgames.org',
                                           password=hash_password('botpasswd'))
            user_datastore.add_role_to_user(u, adm_role)

            u = user_datastore.create_user(email='ccalluso@graphgames.org',
                                           password=hash_password('ccpasswd'))
            user_datastore.add_role_to_user(u, adm_role)

            u = user_datastore.create_user(email='gp.jesi@graphgames.org',
                                           password=hash_password('gppasswd'))
            user_datastore.add_role_to_user(u, default_role)

            # Dummy users for pad experiments:
            for i in range(1, 11):
                u = user_datastore.create_user(email='pad' + str(i) + '@graphgames.org',
                                               password=hash_password('pad' + str(i) +
                                                                          'passwd'))
                user_datastore.add_role_to_user(u, default_role)

    db.session.commit()

    if not GameType.query.first():
        GameType.inject_game_types()


class Move(db.Model):
    __tablename__ = 'moves'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.id'))
    sid = db.Column(db.Integer, db.ForeignKey('game_sessions.id'))
    mv = db.Column(db.String(64))
    play_role = db.Column(db.String(64))
    ts = db.Column(db.DateTime)

    def __repr__(self):
        return '<Move %r made by user %r at %r>' % (self.mv, self.uid, self.ts)


class GameSession(db.Model):
    __tablename__ = 'game_sessions'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.id'))
    type = db.Column(db.Integer, db.ForeignKey('game_types.id'))
    score = db.Column(db.Integer)
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)

    moves = db.relationship('Move', backref='game_session', lazy='dynamic')

    def __repr__(self):
        return 'Session %r, type %r, score %r, started: %r, ended: %r' % (self.id, self.type,
                                                                          self.score, self.start,
                                                                          self.end)


class MPSession(db.Model):
    __tablename__ = 'mp_sessions'
    id = db.Column(db.Integer, primary_key=True)
    gid = db.Column(db.Integer, db.ForeignKey('game_types.id'))
    sids = db.Column(db.Text)
    users = db.Column(db.Text)

    def __repr__(self):
        return 'Multiplayer Session %r for game %r, involving sids: %r and users: %r' % (
            self.id,
            self.gid,
            self.sids,
            self.users)


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
        types = {
            'Small TTT Solo': (
                {'html_file': 'admin/games/ttt-page.html',
                 'shoe_file': 'game422-small.txt',
                 'timeout': 900,
                 'replay': False,
                 'enable_multiplayer': False,
                 'enable_bot': False,
                 'min_users': 2,
                 'max_users': 2,
                 'card_flip': True,
                 'opponent_covered': True,
                 'covered': {'NK': False, 'N': True, 'U': False, 'C': True,
                             'CK': False, 'T': False}}),
            'Small TTT Solo Uncovered': (
                {'html_file': 'admin/games/ttt-page.html',
                 'shoe_file': 'game422-small.txt',
                 'timeout': 900,
                 'replay': False,
                 'enable_multiplayer': False,
                 'enable_bot': False,
                 'min_users': 2,
                 'max_users': 2,
                 'card_flip': True,
                 'opponent_covered': False,
                 'covered': {'NK': False, 'N': True, 'U': False,
                             'C': True, 'CK': False, 'T': False}}),
            'AI enabled TTT. The AI bot adopts a rule-based engine.': (
                {'shoe_file': 'game422-small.txt',
                 'html_file': 'admin/games/ttt-page.html',
                 'timeout': 900,
                 'replay': False,
                 'enable_bot': True,
                 'enable_multiplayer': True,
                 'min_users': 2,
                 'max_users': 2,
                 'card_flip': True,
                 'covered': {'CK': False, 'C': True, 'NK': False,
                             'N': True, 'U': False, 'T': False},
                 'opponent_covered': True}
            ),
            'Small TTT MP': (
                {'html_file': 'admin/games/ttt-page.html',
                 'shoe_file': 'game422-small.txt',
                 'timeout': 900,
                 'replay': False,
                 'enable_multiplayer': True,
                 'enable_bot': False,
                 'min_users': 2,
                 'max_users': 2,
                 'card_flip': True,
                 'opponent_covered': True,
                 'covered': {'NK': False, 'N': True, 'U': False, 'C': True,
                             'CK': False, 'T': False}}),
            'Small TTT Solo cards unflippable': (
                {'html_file': 'admin/games/ttt-page.html',
                 'shoe_file': 'game422-small.txt',
                 'timeout': 900,
                 'replay': False,
                 'enable_multiplayer': False,
                 'enable_bot': False,
                 'min_users': 2,
                 'max_users': 2,
                 'card_flip': False,
                 'opponent_covered': True,
                 'covered': {'NK': False, 'N': True, 'U': False, 'C': True,
                             'CK': False, 'T': False}}),
        }

        for t in types:
            gt = GameType.query.filter_by(info=t).first()
            if gt is None:
                # Careful: python dicts must be converted in json strings here!
                gt = GameType(params=dumps(types[t]), info=t)
                db.session.add(gt)

        db.session.commit()
