from flask import Flask
from celery import Celery
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_socketio import SocketIO
from config import config
from csv import writer
from io import BytesIO
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from time import time, localtime
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

import views
admin = Admin(app, name='Graphgames', index_view=views.MyHomeView(),
              base_template='admin/gg_master.html',
              template_mode='bootstrap3')
