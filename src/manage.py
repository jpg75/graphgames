#!/usr/bin/python

import os
from app import create_app, db, socket_io
from app.models import User, Role, Move, Session, SessionType
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

cfg = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(cfg)
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Move=Move,
                Session=Session, SessionType=SessionType)


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
    SessionType.inject_session_types()


if __name__ == '__main__':
    manager.run()
