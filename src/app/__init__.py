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

bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()

socket_io = SocketIO()
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'

celery = None

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


def create_app(config_name):
    global celery

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    config[config_name].init_app(app)
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    socket_io.init_app(app)
    celery = make_celery(app)  # not very elegant!

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


def make_celery(app):
    """
    Generate a Celery instance, configures with the broker and sets the default parameters set
    from Flask config.

    :param app: web app handler
    :return: a celery instance
    """
    celery = Celery(app.import_name, backend=app.config['CELERY_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
