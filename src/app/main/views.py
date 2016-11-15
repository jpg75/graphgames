# from OpenSSL.SSL import Session
from datetime import datetime
from flask import render_template, session, redirect, url_for
from flask_login import current_user
from . import main
from .forms import NameForm
from .. import db
from ..models import User, SessionType, Session
from ..decorators import authenticated_only
from json import loads


@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    avail_games = SessionType.query.all()
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
    s = Session(uid=current_user.id, type=game_id, start=datetime.now())
    db.session.add(s)
    db.session.commit()
    session['game_session'] = s.id

    st = SessionType.query.filter_by(id=game_id).first()
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
