# from OpenSSL.SSL import Session
from datetime import datetime
from flask import render_template, session, redirect, url_for, flash, request, make_response
from flask_login import current_user, login_required
from . import main
from .forms import NameForm, BaseForm, GameTypeForm
from .. import db, csv2string
from ..models import User, GameType, GameSession, Role, Move
from ..decorators import authenticated_only, admin_required
from wtforms import SelectField, SubmitField, BooleanField
from json import loads


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


@main.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_administrator():
        flash('Cannot access to admin panel when not having administrative privileges.')
        redirect(url_for('.index'))

    else:
        return render_template('admin.html')


@main.route('/session_admin', methods=['GET', 'POST'])
@login_required
def session_admin():
    if not current_user.is_administrator():
        flash('Cannot access to session admin panel when not having administrative '
              'privileges.')
        redirect(url_for('.index'))

    ss = GameSession.query.all()
    for gs in ss:
        field = BooleanField()
        BaseForm.append_field(str(gs.id), field)

    BaseForm.append_field('download', SubmitField())
    form = BaseForm(request.form)

    print len(request.form)
    if request.method == "POST":
        print "VALIDATED!"
        sids = [fieldname for fieldname in request.form if fieldname != 'download']
        moves = Move.query.filter(Move.sid.in_(sids)).all()
        s = csv2string(['MOVE ID', 'USER_ID', 'SESSION_ID', 'MOVE', 'TIMESTAMP']) + '\n'
        for move in moves:
            s = s + csv2string([move.id, move.uid, move.sid, move.mv, move.ts]) + '\n'

        response = make_response(s)
        response.headers["Content-Disposition"] = "attachment; filename=moves_data.csv"

        # flash('File download is going to start shortly.')
        return response

    print "form: ", form.data
    print "sessions: ", ss
    return render_template('session_admin.html', form=form, data=ss)


@main.route('/user_admin')
@login_required
def user_admin():
    if not current_user.is_administrator():
        flash('Cannot access to admin panel features when not having administrative privileges.')
        redirect(url_for('.index'))

    users = User.query.all()
    for user in users:
        print user.username
        field = SelectField(user.username, choices=[(user.role.name, user.role.name),
                                                    (Role.opposite_role(user.role.name),
                                                     Role.opposite_role(user.role.name))
                                                    ])
        BaseForm.append_field('user_' + str(user.id), field)

    BaseForm.append_field('Submit privilege change', SubmitField())
    form = BaseForm()

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
        flash('Cannot access to admin panel features when not having administrative privileges.')
        redirect(url_for('.index'))

    st = GameType.query.all()

    return render_template('config.html', data=st)


@main.route('/config_add', methods=['GET', 'POST'])
@login_required
def config_add():
    if not current_user.is_administrator():
        flash('Cannot access to admin panel features when not having administrative privileges.')
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
        flash('Cannot access to admin panel features when not having administrative privileges.')
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
    s = csv2string(['ID', 'USER_ID', 'MOVE', 'TIMESTAMP']) + '\n'
    for move in moves:
        s = s + csv2string([move.id, move.uid, move.mv, move.ts]) + '\n'

    # We need to modify the response, so the first thing we
    # need to do is create a response out of the CSV string
    response = make_response(s)
    # This is the key: Set the right header for the response
    # to be downloaded, instead of just printed on the browser
    response.headers["Content-Disposition"] = "attachment; filename=moves_data.csv"
    return response


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
    :return:
    """
    # Generate a GameSession and add to the WSGI session
    s = GameSession(uid=current_user.id, type=game_id, start=datetime.now())
    db.session.add(s)
    db.session.commit()

    session['game_session'] = s.id

    st = GameType.query.filter_by(id=game_id).first()
    session['game_cfg'] = loads(st.params)  # the json from the DB is converted into python dict
    session['game_type'] = game_id

    # return render_template(session['game_cfg']['html_file'])
    return render_template("ttt-page.html")

    # NOTE:
    # the html file holding the actual game (js link) must be listed in the json config in the DB
    # SessionType class. The dynamic route show_game, according to the config redirects to the
    # corresponding html file. The dynamic route attaches the json config in a parameter in the
    # session.
    #
    # The session can be read from socket-io handlers and the current config can be
    # dispatched to clients.
    #
    # Since the js inside the page cannot read the session (as far as I know), during the login
    # session, the js game client receives the json config.
    #
    # However, it is still to be solved the fact that
