from flask import render_template, request, flash, redirect, url_for
from app.blueprints.main import main
from app.models import Analysis, Batch
from app.extensions import db
from sqlalchemy import desc

@main.route('/')
def dashboard():
    """Main dashboard"""
    # Get recent analyses
    recent_analyses = Analysis.query.order_by(desc(Analysis.timestamp)).limit(10).all()
    
    # Get statistics
    total_scans = Analysis.query.count()
    total_detections = Analysis.query.filter(
        Analysis.confidence >= 50
    ).count()
    
    # Get average confidence
    avg_confidence = db.session.query(
        db.func.avg(Analysis.confidence)
    ).scalar() or 0
    
    # Recent batches
    recent_batches = Batch.query.order_by(desc(Batch.created_at)).limit(5).all()
    
    stats = {
        'total_scans': total_scans,
        'total_detections': total_detections,
        'avg_confidence': round(avg_confidence, 2),
        'detection_rate': round((total_detections / total_scans * 100) if total_scans > 0 else 0, 1)
    }
    
    return render_template('dashboard.html',
                         recent_analyses=recent_analyses,
                         recent_batches=recent_batches,
                         stats=stats)


@main.route('/history')
def history():
    """View all analyses"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filter options
    verdict_filter = request.args.get('verdict', None)
    
    query = Analysis.query
    
    if verdict_filter and verdict_filter != 'all':
        query = query.filter_by(verdict=verdict_filter)
    
    pagination = query.order_by(desc(Analysis.timestamp)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    analyses = pagination.items
    
    return render_template('history.html',
                         analyses=analyses,
                         pagination=pagination,
                         verdict_filter=verdict_filter)


@main.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@main.route('/help')
def help():
    """Help documentation"""
    return render_template('help.html')