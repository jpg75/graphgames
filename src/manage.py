#!/usr/bin/python

import os
from flask import url_for
from app import db, socket_io, app, admin
from app.views import UserAdminView, GameTypeAdminView, SessionAdminView, GGFileAdmin
from app.models import User, Role, Move, GameSession, GameType, user_datastore, init_db
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand
from flask_security import Security, user_registered
from flask_admin import helpers as admin_helpers

cfg = os.getenv('FLASK_CONFIG') or 'default'

manager = Manager(app)
migrate = Migrate(app, db)

security = Security(app, user_datastore)


# assign the default role 'user' when a new user registers
@user_registered.connect_via(app)
def user_registered_sighandler(app, user, confirm_token):
    default_role = user_datastore.find_role("user")
    user_datastore.add_role_to_user(user, default_role)
    db.session.commit()


admin.add_view(UserAdminView(User, db.session, name='Users'))
admin.add_view(SessionAdminView(GameSession, db.session, name='Sessions'))
admin.add_view(GameTypeAdminView(GameType, db.session, name='Games'))

path = os.path.join(os.path.dirname(__file__), 'data')
# path += os.path.join(os.path.dirname(__file__), 'app/static')
print path
admin.add_view(GGFileAdmin(path, 'data/', name='Data files'))


# define a context processor for merging flask-admin's template context into the
# flask-security views.
@security.context_processor
def security_context_processor():
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Move=Move,
                GameSession=GameSession, GameType=GameType)


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def run():
    socket_io.run(app, host='0.0.0.0', port=app.config['SOCKET_IO_PORT'])


@manager.command
def populate():
    """
    Insert Users, Roles or whatever it is required for the application.
    Please consider the security implications that might arise!
    :return:
    """
    init_db()


if __name__ == '__main__':
    manager.run()

    # NOTE: in order to regenerate the DB:
    # > db init
    # > db migrate -m "comment"
    # > db upgrade
    # > manage.py populate
