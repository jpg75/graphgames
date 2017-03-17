# from OpenSSL.SSL import Session
from flask import redirect, url_for
from . import main


@main.route('/', methods=['GET', 'POST'])
def index():
    return redirect(url_for('admin.index'))

