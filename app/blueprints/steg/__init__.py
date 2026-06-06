from flask import Blueprint

steg = Blueprint('steg', __name__)

from . import routes
