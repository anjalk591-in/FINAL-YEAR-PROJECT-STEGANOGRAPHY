"""
WSGI entry point for production deployment

Use with Gunicorn:
    gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app

Or with uWSGI:
    uwsgi --http :8000 --wsgi-file wsgi.py --callable app
"""

import os
from app import create_app

# Create the application
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    app.run()