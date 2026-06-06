from flask import Blueprint

analysis = Blueprint('analysis', __name__)

from app.blueprints.analysis import routes