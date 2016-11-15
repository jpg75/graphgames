from OpenSSL.SSL import Session
from datetime import datetime
from flask import render_template, session, redirect, url_for
from . import main
from .forms import NameForm
from .. import db
from ..models import User, SessionType
from ..decorators import authenticated_only


@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    # avail_games = ['ttt']
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
    return render_template("ttt-page.html")
