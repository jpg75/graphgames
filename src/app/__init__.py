from flask import Flask
from celery import Celery
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import config
from csv import writer
from io import BytesIO


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

bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()

socket_io = SocketIO()
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'


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
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    # socket_io.init_app(app, async_mode='eventlet', message_queue='redis://localhost:6379/0')
    socket_io.init_app(app, message_queue='redis://localhost:6379/0')

    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .adm import adm as adm_blueprint
    app.register_blueprint(adm_blueprint, url_prefix='/adm')

    if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
        from flask_sslify import SSLify
        sslify = SSLify(app)

    return app


celery = make_celery()
app = create_app(cfg='default')
celery.config_from_object(config['celery'])






