from flask import Flask, send_file, flash, session, abort, redirect, request, url_for
from celery import Celery
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.view import func
from flask_admin.base import AdminIndexView
from flask_admin.actions import action
from flask_admin.model.template import LinkRowAction
from flask_admin.contrib.fileadmin import FileAdmin
from flask_security import current_user
from flask_socketio import SocketIO
from config import config
from csv import writer
from io import BytesIO
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from time import time, localtime
from datetime import datetime
from json import loads

SHOE_FILE_ORDER = ['NK', 'N', 'U', 'C', 'CK', 'T', 'GC', 'PL']


def aggregate_moves(moves, sids):
    unique_hands = []
    current_hand = None
    sid_data = dict([(x, {}) for x in sids])  # maps <sid> -> { <hand> -> [seq] }
    FILE_ORDER = [x for x in SHOE_FILE_ORDER if x != 'GC' and x != 'PL']

    for move in moves:
        if move.mv.startswith('HAND'):
            d = loads(move.mv.replace('HAND', ''))
            current_hand = ' '.join(d[x] for x in FILE_ORDER)
            if not current_hand in unique_hands:
                # print "current hand:",current_hand
                unique_hands.append(current_hand)
            else:
                current_hand = ' '.join(d[x] for x in FILE_ORDER)
        else:
            if current_hand in sid_data[str(move.sid)]:  # hand exists for this sid
                sid_data[str(move.sid)][current_hand].append(move.mv)
            else:  # hand does not exists and thus the linked list
                sid_data[str(move.sid)][current_hand] = [move.mv]

    return sid_data, unique_hands

def csv2string(data):
    """
    Format a list of items into a CSV string.

    :param data: list of items
    :return: a CSV string for the arguments
    """
    si = BytesIO()
    cw = writer(si)
    cw.writerow(data)
    return si.getvalue().strip('\r\n')


db = SQLAlchemy()
socket_io = SocketIO()


class GGFileAdmin(FileAdmin):
    """
    A FileAdmin customized in order to allow the access by users having 'admin' role.
    """
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin'):
            return True

        return False


class MyHomeView(AdminIndexView):
    """
    Overrides the standard behavior of the admin index page by loading the available games from
    DB.
    """

    @expose('/')
    def index(self):
        from models import GameType

        avail_games = GameType.query.all()
        avail_games = {x.id: x.info for x in avail_games}
        return self.render(self._template, games=avail_games)

    @expose('/game/<int:game_id>')
    def play_game(self, game_id):
        """
        This dynamic route links to the actual html file managing the game requested. The 'game_id'
        parameter is the game type, alias one of the available configuration types/config in the
        current DB.

        Before routing to the file, a GameSession objects is generated over the DB linking the
        current user to the newly created session.

        The info about the game session (id), the game cfg (as a python dict) and the game type (
        SessionType in DB) are injected into the WSGI session and are readable from the game
        web-socket implementation.

        :param game_id: the corresponding id in the SessionType DB class.
        :return: the corresponding game template
        """
        print "game id: ", game_id
        from models import GameSession, GameType

        s = GameSession(uid=current_user.id, type=game_id, start=datetime.now())
        db.session.add(s)
        db.session.commit()

        session['game_session'] = s.id

        st = GameType.query.filter_by(id=game_id).first()
        print st
        session['game_cfg'] = loads(st.params)  # the json from the DB is converted into python dict
        session['game_type'] = game_id

        return self.render(session['game_cfg']['html_file'])


class GGBasicAdminView(ModelView):
    """
    Basic class for Graphgames views. Only 'admin' is allowed.
    """
    page_size = 20
    can_set_page_size = True
    can_view_details = True

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class UserAdminView(GGBasicAdminView):
    """
    View for User table.
    Only a selected set of fields are visible. All these are editable. Only 'roles' is editable
    in line.
    Rows can be filtered by email.
    """
    can_view_details = False
    column_list = ['id', 'email', 'roles', 'last_login_at', 'login_count', 'member_since',
                   'last_seen']
    create_modal = True
    edit_modal = True
    column_editable_list = ['roles']
    column_filters = ['email']


class GameTypeAdminView(GGBasicAdminView):
    """
    View for GameTypes. Fields are editable inline.
    """
    column_editable_list = ['params', 'info']
    can_view_details = False
    create_modal = True
    edit_modal = True
    column_extra_row_actions = [
        LinkRowAction('glyphicon glyphicon-play', '/admin/game/{row_id}', title='Play')
    ]


class SessionAdminView(GGBasicAdminView):
    """
    View for session table.
    Cannot be edited and created. Can be filtered by 'id', 'uid', 'type'.
    """
    can_edit = False
    can_create = False
    can_view_details = False
    column_list = ['id', 'uid', 'type', 'start', 'end']
    column_filters = ['id', 'uid', 'type']

    column_extra_row_actions = [
        LinkRowAction('glyphicon glyphicon-repeat', '/admin/gamesessions/replay/{row_id}',
                      title='Replay')
    ]

    @expose('/replay/<int:sid>')
    def replay_game_session(self, sid):
        """
        This dynamic route generate a dummy session of the required session game. This section is
        automatic, meaning that the system replays each moves stored in the session following the
        original temporal sequence.
        The actual game type is collected by the game session.

        The user can just watch the recorded session or quit visualization.

        The DB is not affected (no writes) by this route operation.
        :param sid:
        :return: the corresponding game template
        """
        from models import GameSession, GameType

        s = GameSession.query.filter_by(id=sid).first()
        gt = GameType.query.filter_by(id=s.type).first()
        gt_struct = loads(gt.params)
        gt_struct['replay'] = True  # set replay active

        session['game_cfg'] = gt_struct
        session['game_type'] = gt.id
        session['game_session'] = sid

        return self.render(gt_struct['html_file'])

    @action('download', 'Download', 'Are you sure you want to download selected session data?')
    def action_download(self, ids):
        try:
            from models import Move
            from adm.views import aggregate_moves

            moves = Move.query.filter(Move.sid.in_(ids)).all()
            data, hands = aggregate_moves(moves, ids)

            line = ''
            for h in hands:
                line += h + '\n\n'
                for sid in ids:
                    if h in data[sid]:
                        line += ''.join(data[sid][h]) + '\n'
                    else:
                        line += 'NA\n'
                line += '\n'

            files = [{'file_name': 'aggregated_output.txt',
                      'file_data': line
                      },
                     {'file_name': 'aggregated_output_companion.txt',
                      'file_data': '\n'.join(ids)
                      }]

            zf = make_zip(files)
            flash('Sessions were successfully downloaded.')
            return send_file(zf, attachment_filename='aggregated_output.zip',
                             as_attachment=True)

        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise

            flash('Failed to download session data')


class MyMoveAdminView(GGBasicAdminView):
    """
    View for the current user moves. Cannot be created.
    """
    can_view_details = False
    can_create = False

    def get_query(self):
        return self.session.query(self.model).filter(self.model.uid == current_user.id)

    def get_count_query(self):
        return self.session.query(func.count('*')).filter(self.model.uid == current_user.id)

    def is_accessible(self):
        """
        Admin access not required.
        :return:
        """
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        return True


def make_zip(file_list):
    """
    Generate an in-memory zip file populated with the content specified in the argument.

    :param file_list: a list of dictionaries holding the name ('file_name' field) and content (
                        'file_data' field) for each sub-file of the zip
    :return: a memory file handler
    """
    memory_file = BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        for afile in file_list:
            d = ZipInfo(afile['file_name'])
            d.date_time = localtime(time())[:6]
            d.compress_type = ZIP_DEFLATED
            zf.writestr(d, afile['file_data'])  # write content on file descriptor

    memory_file.seek(0)
    return memory_file


def make_celery():
    """
    Generate a Celery instance, configures with the broker and sets the default parameters set
    from Flask config.

    :param app: web app handler
    :return: a celery instance
    """
    celery = Celery()
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app(cfg):
    app = Flask(__name__)
    app.config.from_object(config[cfg])

    config[cfg].init_app(app)
    db.init_app(app)

    socket_io.init_app(app, message_queue='redis://localhost:6379/0')

    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
        from flask_sslify import SSLify
        sslify = SSLify(app)

    return app


celery = make_celery()
app = create_app(cfg='default')
celery.config_from_object(config['celery'])
admin = Admin(app, name='Graphgames', index_view=MyHomeView(), base_template='admin/gg_master.html',
              template_mode='bootstrap3')
