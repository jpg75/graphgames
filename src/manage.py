#!/usr/bin/python

import os
from app import create_app, db
from app.models import User, Role, Move
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Move=Move)

manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def populate():
    """
    Insert Users, Roles or whatever it is required for the application.
    Please consider the security implications that might arise!
    :return:
    """
    User.inject_users()
    Role.inject_roles()

if __name__ == '__main__':
    manager.run()