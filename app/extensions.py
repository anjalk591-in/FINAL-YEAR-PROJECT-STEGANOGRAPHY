from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()