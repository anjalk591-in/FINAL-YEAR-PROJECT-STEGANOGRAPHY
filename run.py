#!/usr/bin/env python
"""
StegAnalyzer Pro - Main Application Entry Point
"""

import os
from app import create_app
from app.extensions import db
from app.models import Analysis, Batch, Visualization, Settings

# Create Flask application
app = create_app(os.getenv('FLASK_ENV', 'development'))

# Shell context for flask shell command
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Analysis': Analysis,
        'Batch': Batch,
        'Visualization': Visualization,
        'Settings': Settings
    }

# CLI command to initialize database
@app.cli.command()
def init_db():
    """Initialize the database."""
    # Ensure instance directory exists
   #instance_path = os.path.join(os.path.dirname(__file__), 'instance')
    #os.makedirs(instance_path, exist_ok=True)
    print("4"*100)
    # Create all tables
    with app.app_context():
        db.create_all()

    print('✅ Database initialized successfully!')

# CLI command to seed database with sample data
@app.cli.command()
def seed_db():
    """Seed database with sample settings."""
    default_settings = [
        {'key': 'theme', 'value': 'light'},
        {'key': 'auto_delete_days', 'value': 7},
        {'key': 'default_scan_type', 'value': 'standard'}
    ]
    
    for setting in default_settings:
        existing = Settings.query.filter_by(key=setting['key']).first()
        if not existing:
            db.session.add(Settings(**setting))
    
    db.session.commit()
    print('✅ Database seeded successfully!')

# CLI command to cleanup old files
@app.cli.command()
def cleanup():
    """Cleanup old uploaded files and analyses."""
    from datetime import datetime, timedelta
    from app.utils.file_handler import delete_file
    
    # Delete analyses older than 30 days
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    old_analyses = Analysis.query.filter(Analysis.timestamp < cutoff_date).all()
    
    count = 0
    for analysis in old_analyses:
        # Delete file
        delete_file(analysis.filepath)
        
        # Delete from database
        db.session.delete(analysis)
        count += 1
    
    db.session.commit()
    print(f'✅ Cleaned up {count} old analyses.')

# CLI command to create all directories
@app.cli.command()
def create_dirs():
    """Create all required directories."""
    directories = [
        'instance',
        'media/uploads',
        'media/cache',
        'media/reports',
        'media/visualizations',
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f'✅ Created directory: {directory}')
    
    print('✅ All directories created successfully!')

if __name__ == '__main__':
    # Ensure required directories exist before running
    directories = [
        'instance',
        'media/uploads',
        'media/cache', 
        'media/reports',
        'media/visualizations',
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Run the application
    app.run(host='0.0.0.0', port=5001, debug=True)