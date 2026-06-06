import os
from flask import Flask
from config import config
from app.extensions import db, migrate, cache

def create_app(config_name=None):
    """Application factory pattern"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    print("8"*100)
    # Ensure instance and media folders exist
    ensure_folders_exist(app)

    print('#'*100)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    
    # Register blueprints
    from app.blueprints.main import main as main_bp
    from app.blueprints.analysis import analysis as analysis_bp
    from app.blueprints.batch import batch as batch_bp
    from app.blueprints.api import api as api_bp
    from app.blueprints.steg import steg as steg_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(analysis_bp, url_prefix='/analysis')
    app.register_blueprint(batch_bp, url_prefix='/batch')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(steg_bp, url_prefix='/steg')
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register template filters
    register_template_filters(app)
    
    return app


def ensure_folders_exist(app):
    """Create necessary folders if they don't exist"""
    folders = [
        'instance',
        app.config['UPLOAD_FOLDER'],
        app.config['CACHE_FOLDER'],
        app.config['REPORTS_FOLDER'],
        app.config['VISUALIZATIONS_FOLDER'],
    ]
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)


def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        from flask import render_template, flash
        flash('File size exceeds maximum allowed (50MB)', 'error')
        return render_template('errors/413.html'), 413


def register_template_filters(app):
    """Register custom template filters"""
    
    @app.template_filter('filesize')
    def filesize_filter(size):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @app.template_filter('datetime')
    def datetime_filter(dt, format='%Y-%m-%d %H:%M:%S'):
        """Format datetime objects"""
        if dt is None:
            return ''
        return dt.strftime(format)
    
    @app.template_filter('confidence_class')
    def confidence_class_filter(confidence):
        """Return CSS class based on confidence level"""
        if confidence >= 90:
            return 'danger'
        elif confidence >= 70:
            return 'warning'
        elif confidence >= 50:
            return 'info'
        else:
            return 'success'