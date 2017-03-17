import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SSL_DISABLE = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'itsasecret!'
    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_PASSWORD_SALT = SECRET_KEY
    SECURITY_CONFIRMABLE = False
    SECURITY_TRACKABLE = True
    SECURITY_REGISTERABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    GRAPHGAMES_MAIL_SUBJECT_PREFIX = '[Graphgames]'
    GRAPHGAMES_MAIL_SENDER = 'Graphgames Admin <do_not_reply@graphgames.com>'
    GRAPHGAMES = os.environ.get('FLASKY_ADMIN')
    SOCKET_IO_PORT = 5000
    CELERY_BACKEND = os.environ.get('CELERY_BACKEND') or 'redis://localhost:6379/0'
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or \
                            'redis://localhost:6379/0'

    @staticmethod
    def init_new_deploy():
        Config.SECRET_KEY = os.urandom(24)

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True

    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir,
                                                          'data.sqlite')


class ProductionConfig(DevelopmentConfig):
    DEBUG = False

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir,
                                                          'data.sqlite')


class CeleryConfig(object):
    enable_utc = True
    timezone = 'Europe/Rome'
    result_backend = 'redis://localhost:6379/0'
    broker_url = 'redis://localhost:6379/0'
    # CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or \
    #                        'redis://localhost:6379/0'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
    'celery': CeleryConfig
}
