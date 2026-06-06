from flask import Blueprint

batch = Blueprint('batch', __name__)

from app.blueprints.batch import routes