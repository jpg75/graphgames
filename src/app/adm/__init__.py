from flask import Blueprint

adm = Blueprint('adm', __name__)
from . import views