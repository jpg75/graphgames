# from OpenSSL.SSL import Session
from datetime import datetime
from flask import render_template, session, redirect, url_for, flash, request, make_response
from flask_login import current_user, login_required
from . import main
from .forms import BaseForm, GameTypeForm
from .. import db, csv2string
from ..models import User, GameType, GameSession, Role, Move
from ..decorators import authenticated_only, admin_required
from wtforms import SelectField, SubmitField
from json import loads
from ..tasks import download_task


@main.route('/', methods=['GET', 'POST'])
def index():
    avail_games = GameType.query.all()
    avail_games = {x.id: x.info for x in avail_games}

    return render_template('index.html',
                           games=avail_games,
                           current_time=datetime.utcnow())


@main.route('/user')
@login_required
def user():
    return render_template('user.html')


@main.route('/gsessions/<username>')
@login_required
def sessions(username):
    gs = GameSession.query.filter_by(uid=current_user.id).all()

    return render_template('sessions.html', user=current_user, data=gs)


@main.route('/gsessions/<int:sid>')
@login_required
def session_moves(sid):
    s = Move.query.filter_by(sid=sid).all()

    return render_template('session.html', user=current_user, data=s, sid=sid)


@main.route('/adm', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_administrator():
        flash('Cannot access to adm panel when not having administrative privileges.')
        redirect(url_for('.index'))

    else:
        return render_template('adm.html')


# @main.route('/session_admin', methods=['GET', 'POST'])
# @login_required
# def session_admin():
#     if not current_user.is_administrator():
#         flash('Cannot access to session adm panel when not having administrative '
#               'privileges.')
#         redirect(url_for('.index'))
#
#     class F(BaseForm):  # internal subclass to avoid polluting the BaseForm class
#         pass
#
#     ss = GameSession.query.all()
#     for gs in ss:
#         field = BooleanField()
#         F.append_field(str(gs.id), field)
#
#     F.append_field('download', SubmitField())
#     form = F(request.form)
#
#     print len(request.form)
#     if request.method == "POST":
#         sids = [fieldname for fieldname in request.form if fieldname != 'download']
#         moves = Move.query.filter(Move.sid.in_(sids)).all()
#         s = csv2string(
#             ['MOVE', 'TIMESTAMP', 'MOVE_ID', 'USER_ID', 'SESSION_ID', 'PLAY_ROLE']) + '\n'
#         for move in moves:
#             s = s + csv2string([move.mv, move.ts, move.id, move.uid, move.sid, move.play_role]) + \
#                 '\n'
#
#         response = make_response(s)
#         response.headers["Content-Disposition"] = "attachment; filename=moves_data.csv"
#
#         # flash('File download is going to start shortly.')
#         return response
#
#     print "form: ", form.data
#     print "sessions: ", ss
#     return render_template('session_admin.html', form=form, data=ss)


@main.route('/user_admin')
@login_required
def user_admin():
    class F(BaseForm):  # internal subclass to avoid polluting the BaseForm class
        pass

    if not current_user.is_administrator():
        flash('Cannot access to adm panel features when not having administrative privileges.')
        redirect(url_for('.index'))

    users = User.query.all()
    for user in users:
        print user.username
        field = SelectField(user.username, choices=[(user.role.name, user.role.name),
                                                    (Role.opposite_role(user.role.name),
                                                     Role.opposite_role(user.role.name))
                                                    ])
        F.append_field('user_' + str(user.id), field)

    F.append_field('Submit privilege change', SubmitField())
    form = F(request.form)

    if form.validate_on_submit():
        print form.data
        for user in form.data:
            if user.startswith('user_'):
                uid = int(user.replace('user_', ''))
                users[uid - 1].role_id = Role.role_id_from_name(form.data[user])
                db.session.add(users[uid - 1])

        db.session.commit()
        flash('Privileges updated.')
        return redirect(url_for('.index'))

    return render_template('user_admin.html', form=form)


@main.route('/config')
@login_required
def config():
    if not current_user.is_administrator():
        flash('Cannot access to adm panel features when not having administrative privileges.')
        redirect(url_for('.index'))

    st = GameType.query.all()

    return render_template('config.html', data=st)


@main.route('/config_add', methods=['GET', 'POST'])
@login_required
def config_add():
    if not current_user.is_administrator():
        flash('Cannot access to adm panel features when not having administrative privileges.')
        redirect(url_for('.index'))

    form = GameTypeForm()
    if form.validate_on_submit():
        gt = GameType(info=form.info.data, params=form.params.data)
        db.session.add(gt)
        db.session.commit()
        flash('New game configuration injected.')
        return redirect(request.args.get('next') or url_for('main.config'))

    return render_template('config_add.html', form=form)


@main.route('/config_edit/<int:conf_id>', methods=['GET', 'POST'])
@login_required
def config_edit(conf_id):
    if not current_user.is_administrator():
        flash('Cannot access to adm panel features when not having administrative privileges.')
        redirect(url_for('.index'))

    gt = GameType.query.filter_by(id=conf_id).first()
    form = GameTypeForm()

    if form.validate_on_submit():
        gt.info = form.info.data
        gt.params = form.params.data
        db.session.add(gt)
        db.session.commit()
        flash('Configuration updated.')
        return redirect(request.args.get('next') or url_for('main.config'))

    form.info.data = gt.info
    form.params.data = gt.params
    form.submit.label.text = 'Update configuration'

    return render_template('config_edit.html', form=form, conf_id=conf_id)


@main.route('/config_del/<int:conf_id>')
@login_required
def config_del(conf_id):
    gt = GameType.query.filter_by(id=conf_id).first()
    if gt is not None:
        db.session.delete(gt)
        db.session.commit()
        flash("Game configuration successfully deleted.")

    else:
        flash("Warning: the selected configuration was no longer available in the system.")

    return redirect(url_for('main.config'))


@main.route('/download/<int:sid>')
def download(sid):
    moves = Move.query.filter_by(sid=sid).all()

    # put column headers:
    s = csv2string(['MOVE', 'TIMESTAMP', 'MOVE_ID', 'USER_ID', 'PLAY_ROLE']) + '\n'
    for move in moves:
        s = s + csv2string([move.mv, move.ts, move.id, move.uid, move.play_role]) + '\n'

    # We need to modify the response, so the first thing we
    # need to do is create a response out of the CSV string
    response = make_response(s)
    # This is the key: Set the right header for the response
    # to be downloaded, instead of just printed on the browser
    response.headers["Content-Disposition"] = "attachment; filename=moves_data.csv"
    return response


# @main.route('/download/<int:sid>')
def download_once(sid):
    task_res = download_task.delay(sid)
    task_res.wait()
    pass


@main.route('/<int:game_id>')
@authenticated_only
def show_game(game_id):
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
    # Generate a GameSession db object and add to the WSGI session
    s = GameSession(uid=current_user.id, type=game_id, start=datetime.now())
    db.session.add(s)
    db.session.commit()

    session['game_session'] = s.id

    st = GameType.query.filter_by(id=game_id).first()
    session['game_cfg'] = loads(st.params)  # the json from the DB is converted into python dict
    session['game_type'] = game_id

    return render_template(session['game_cfg']['html_file'])


@main.route('/<int:sid>')
@authenticated_only
def replay_game_session(sid):
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
    s = GameSession.query.filter_by(id=sid).first()
    gt = GameType.query.filter_by(id=s.type).first()
    gt_struct = loads(gt.params)
    gt_struct['replay'] = True  # set replay active

    return render_template(gt_struct['game_cfg']['html_file'])
