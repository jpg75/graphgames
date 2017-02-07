#!/usr/bin/python

import os
from app import db, socket_io, app
from app.models import User, Role, Move, GameSession, GameType
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

cfg = os.getenv('FLASK_CONFIG') or 'default'

manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Move=Move,
                GameSession=GameSession, GameType=GameType)


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def run():
    socket_io.run(app, port=app.config['SOCKET_IO_PORT'], debug=True)


@manager.command
def populate():
    """
    Insert Users, Roles or whatever it is required for the application.
    Please consider the security implications that might arise!
    :return:
    """
    Role.inject_roles()
    User.inject_users()
    GameType.inject_game_types()



if __name__ == '__main__':
    manager.run()

    # NOTE: in order to regenerate the DB:
    # > db init
    # > db migrate -m "comment"
    # > db upgrade
    # > manage.py populate
