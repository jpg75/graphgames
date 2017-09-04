from flask import send_file, flash, session, abort, redirect, request, url_for
from flask_admin import BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.base import AdminIndexView
from flask_admin.actions import action
from flask_admin.model.template import LinkRowAction
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.form import SecureForm
from flask_security import current_user
from datetime import datetime
from . import aggregate_moves, make_zip, db, csv2string
from json import loads, dumps
from jinja2 import Markup
from xml.sax.saxutils import escape


def pre_format(view, value):
    return Markup('<div class="pre">{}</div>'.format(escape(value)))


def json_format(view, value):
    return pre_format(view, dumps(value, indent=2))


def json_formatter(view, context, model, name):
    return json_format(view, getattr(model, name, None))


class GGFileAdmin(FileAdmin):
    """
    A FileAdmin customized in order to allow the access by users having 'admin' role.
    """
    form_base_class = SecureForm
    can_download = True
    editable_extensions = ('txt', 'json', 'js')

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


class GGBasicAdminView(ModelView):
    """
    Basic class for Graphgames views. Only 'admin' is allowed.
    """
    page_size = 20
    can_set_page_size = True
    can_view_details = True
    form_base_class = SecureForm

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
    column_list = ['id', 'params', 'info']
    column_editable_list = ['params', 'info']
    can_view_details = False
    create_modal = True
    edit_modal = True
    can_edit = True
    column_type_formatters = dict()
    # column_formatters = {
    #     'params': json_formatter
    # }
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
        LinkRowAction('glyphicon glyphicon-repeat', '/admin/replay/{row_id}',
                      title='Replay'),
    ]

    @action('delete', 'Delete', 'Are you sure to delete the selected rows?')
    def action_delete(self, ids):
        try:
            from models import MPSession, GameSession, Move
            mp_records = []
            for sid in ids:
                mp_records.extend(MPSession.query.filter(MPSession.sids.contains(sid)))

            gs_records = GameSession.query.filter(GameSession.id.in_(ids)).all()
            m_records = Move.query.filter(Move.sid.in_(ids)).all()
            for item in gs_records:
                db.session.delete(item)
            for item in m_records:
                db.session.delete(item)
            for item in mp_records:
                db.session.delete(item)

            db.session.commit()
            return flash("The selected Sessions and related Moves has been deleted.")

        except Exception as e:
            if not self.handle_view_exception(e):
                raise
            return flash("Impossible to delete data")

    @action('download', 'Download (Nemik format)', 'Are you sure you want to download selected '
                                                   'session data in Nemik format?')
    def action_download(self, ids):
        try:
            from models import Move

            moves = Move.query.filter(Move.sid.in_(ids)).order_by(Move.sid).all()
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

    @action('download_csv', 'Download (CSV format)', 'Are you sure you want to download '
                                                     'selected '
                                                     'session data in CSV format?')
    def action_download_csv(self, ids):
        try:
            from models import Move

            moves = Move.query.filter(Move.sid.in_(ids)).order_by(Move.sid).all()
            line = csv2string(['ID', 'UID', 'SID', 'MOVE', 'PLAY_ROLE', 'TIME_STAMP']) + '\n'
            for move in moves:
                line += csv2string([move.id, move.uid, move.sid]) + ',' + move.mv + ',' \
                                                                                    '' + csv2string(
                    [move.play_role, move.ts]) + '\n'
                '\n'

            files = [{'file_name': 'output.txt',
                      'file_data': line
                      }
                     ]

            zf = make_zip(files)
            flash('Sessions were successfully downloaded.')
            return send_file(zf, attachment_filename='CSV_output.zip',
                             as_attachment=True)

        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash('Failed to download session data')


class MPSessionAdminView(GGBasicAdminView):
    can_edit = False
    can_create = False
    can_view_details = False
    column_list = ['id', 'gid', 'sids', 'users']

    @action('delete', 'Delete', 'Are you sure to delete the selected rows?')
    def action_delete(self, ids):
        try:
            from models import MPSession, GameSession, Move
            mp_records = MPSession.query.filter(MPSession.id.in_(ids)).all()
            sids = []
            for item in mp_records:
                sids.extend(item.sids.split())

            gs_records = GameSession.query.filter(GameSession.id.in_(sids)).all()
            m_records = Move.query.filter(Move.sid.in_(sids)).all()

            for item in mp_records:
                db.session.delete(item)
            for item in gs_records:
                db.session.delete(item)
            for item in m_records:
                db.session.delete(item)

            db.session.commit()
            return flash("The selected Sessions and related Moves has been deleted.")

        except Exception as e:
            if not self.handle_view_exception(e):
                raise
            return flash("Impossible to delete data")


class StatsView(BaseView):
    can_edit = False
    can_create = False

    def __init__(self, ssion, name=None, category=None, endpoint=None, url=None,
                 static_folder=None,
                 menu_class_name=None, menu_icon_type=None, menu_icon_value=None):
        self.session = ssion

        super(StatsView, self).__init__(name, category, endpoint, url, static_folder,
                                        menu_class_name=menu_class_name,
                                        menu_icon_type=menu_icon_type,
                                        menu_icon_value=menu_icon_value)

    @expose('/')
    def index(self):
        from models import MPSession, GameSession, User
        from sqlalchemy import desc
        from itertools import izip

        data = {'solo': [], 'mp': []}
        mp_sids = self.session.query(MPSession.sids).all()

        x = ''
        for item in mp_sids:
            x += ' '.join(item) + ' '

        mp_sids = x.split()
        records = GameSession.query.filter(GameSession.end != None, GameSession.score > 0,
                                           GameSession.id.notin_(mp_sids)).order_by(
            GameSession.score).order_by(desc(
            GameSession.end - GameSession.start)).limit(10).all()

        records_mp = GameSession.query.filter(GameSession.end != None, GameSession.score > 0,
                                              GameSession.id.in_(mp_sids)).limit(10).all()

        for item in records:
            user = User.query.get(item.uid)
            data['solo'].append({'user_login': user.email, 'uid': item.uid, 'sid': item.id,
                                 'score': item.score, 'gid': item.type, 'time': (item.end -
                                                                                 item.start).total_seconds()})
        for item in records_mp:
            user = User.query.get(item.uid)
            data['mp'].append({'user_login': user.email, 'uid': item.uid, 'sid': item.id,
                               'score': item.score, 'gid': item.type, 'time': (item.end -
                                                                               item.start).total_seconds()})

        def pairwise(iterable):
            """s -> (s0, s1), (s2, s3), (s4, s5), ..."""
            a = iter(iterable)
            return izip(a, a)

        scores = []
        for x, y in pairwise(data['mp']):
            z = (x['score'] + y['score'], {'user_login': "%s ; %s" % (x['user_login'],
                                                                      y['user_login']),
                                           'uid': "%r %r" % (x['uid'], y['uid']),
                                           'sid': "%r %r" % (x['sid'], y['sid']),
                                           'gid': x['gid'],
                                           'score': x['score'] + y['score'],
                                           'time': max(x['time'], y['time']),
                                           })
            scores.append(z)

        scores.sort()
        data['mp'][:] = []

        for item in scores:
            data['mp'].append(item[1])

        return self.render('admin/stats.html', stats=data)
