# from OpenSSL.SSL import Session
from flask import render_template, redirect, url_for, flash, request, make_response, send_file
from flask_login import current_user, login_required
from . import adm
from ..main.forms import BaseForm, GameTypeForm
from .. import db, csv2string, make_zip
from ..models import User, GameType, GameSession, Role, Move, SHOE_FILE_ORDER
# from ..decorators import authenticated_only, admin_required
from wtforms import SelectField, SubmitField, BooleanField
from json import loads


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


@adm.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_administrator():
        flash('Cannot access to adm panel when not having administrative privileges.')
        redirect(url_for('.index'))

    else:
        return render_template('adm/admin.html')


@adm.route('/session_admin', methods=['GET', 'POST'])
@login_required
def session_admin():
    if not current_user.is_administrator():
        flash('Cannot access to session adm panel when not having administrative '
              'privileges.')
        redirect(url_for('.index'))
        # redirect(url_for('.admin'))

    class F(BaseForm):  # internal subclass to avoid polluting the BaseForm class
        pass

    ss = GameSession.query.all()
    sd = {x.id: x for x in ss}
    for gs in ss:
        print "adding field %d in form " % gs.id
        field = BooleanField()
        F.append_field(str(gs.id), field)

    F.append_field('download', SubmitField())
    form = F(request.form)

    print len(request.form)
    if request.method == "POST":
        sids = [fieldname for fieldname in request.form if fieldname != 'download']
        moves = Move.query.filter(Move.sid.in_(sids)).all()

        data, hands = aggregate_moves(moves, sids)

        line = ''
        for h in hands:
            line += h + '\n\n'
            for sid in sids:
                if h in data[sid]:
                    line += ''.join(data[sid][h]) + '\n'
                else:
                    line += 'NA\n'
            line += '\n'

        files = [{'file_name': 'aggregated_output.txt',
                  'file_data': line
                  },
                 {'file_name': 'aggregated_output_companion.txt',
                  'file_data': '\n'.join(sids)
                  }]

        zf = make_zip(files)
        return send_file(zf, attachment_filename='aggregated_output.zip',
                         as_attachment=True)

    return render_template('adm/session_admin.html', form=form, data=sd)


@adm.route('/user_admin')
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

    return render_template('adm/user_admin.html', form=form)


@adm.route('/config')
@login_required
def config():
    if not current_user.is_administrator():
        flash('Cannot access to adm panel features when not having administrative privileges.')
        redirect(url_for('main.index'))

    st = GameType.query.all()

    return render_template('adm/config.html', data=st)


@adm.route('/config_add', methods=['GET', 'POST'])
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

    return render_template('adm/config_add.html', form=form)


@adm.route('/config_edit/<int:conf_id>', methods=['GET', 'POST'])
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

    return render_template('adm/config_edit.html', form=form, conf_id=conf_id)


@adm.route('/config_del/<int:conf_id>')
@login_required
def config_del(conf_id):
    gt = GameType.query.filter_by(id=conf_id).first()
    if gt is not None:
        db.session.delete(gt)
        db.session.commit()
        flash("Game configuration successfully deleted.")

    else:
        flash("Warning: the selected configuration was no longer available in the system.")

    return redirect(url_for('adm.config'))


@adm.route('/download/<int:sid>')
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
