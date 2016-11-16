# from OpenSSL.SSL import Session
from datetime import datetime
from flask import render_template, session, redirect, url_for, flash
from flask_login import current_user, login_required
from . import main
from .forms import NameForm, BaseForm
from .. import db
from ..models import User, GameType, GameSession, Role
from ..decorators import authenticated_only, admin_required
from wtforms import SelectField, SubmitField
from json import loads


@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    avail_games = GameType.query.all()
    avail_games = {x.id: x.info for x in avail_games}

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            session['known'] = False
        else:
            session['known'] = True

        session['name'] = form.name.data
        form.name.data = ''
        return redirect(url_for('.index'))

    return render_template('index.html',
                           form=form, name=session.get('name'),
                           known=session.get('known', False),
                           games=avail_games,
                           current_time=datetime.utcnow())


@main.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
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

    if not current_user.is_administrator():
        flash('Cannot access to admin panel when not having administrative privileges.')
        redirect(url_for('.index'))

    if form.validate_on_submit():
        print form.data
        for user in form.data:
            if user.startswith('user_'):
                uid = int(user.replace('user_', ''))
                users[uid-1].role_id = Role.role_id_from_name(form.data[user])
                db.session.add(users[uid-1])

        db.session.commit()
        flash('Privileges updated.')
        return redirect(url_for('.index'))
    
    else:
        return render_template('admin.html', form=form)


@main.route('/ttt')
@authenticated_only
def ttt():
    return render_template("ttt-page.html")


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

    # return render_template(session['game_cfg']['html-file'])
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
