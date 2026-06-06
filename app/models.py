from datetime import datetime
from app.extensions import db

class Analysis(db.Model):
    """Store analysis results"""
    __tablename__ = 'analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    filesize = db.Column(db.Integer)
    image_width = db.Column(db.Integer)
    image_height = db.Column(db.Integer)
    
    # Analysis results
    confidence = db.Column(db.Float, default=0.0)
    verdict = db.Column(db.String(50))
    score = db.Column(db.Integer, default=0)
    
    # Test results (JSON)
    statistical_results = db.Column(db.JSON)
    visual_results = db.Column(db.JSON)
    frequency_results = db.Column(db.JSON)
    format_results = db.Column(db.JSON)
    extraction_results = db.Column(db.JSON)
    
    # Metadata
    scan_type = db.Column(db.String(20), default='standard')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    processing_time = db.Column(db.Float)
    
    # Relationships
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)
    visualizations = db.relationship('Visualization', backref='analysis', 
                                    lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Analysis {self.filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'filesize': self.filesize,
            'dimensions': f'{self.image_width}x{self.image_height}',
            'confidence': round(self.confidence, 2),
            'verdict': self.verdict,
            'score': self.score,
            'timestamp': self.timestamp.isoformat(),
            'processing_time': round(self.processing_time, 2) if self.processing_time else None,
            'results': {
                'statistical': self.statistical_results,
                'visual': self.visual_results,
                'frequency': self.frequency_results,
                'format': self.format_results,
                'extraction': self.extraction_results
            }
        }


class Batch(db.Model):
    """Batch processing jobs"""
    __tablename__ = 'batches'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    total_images = db.Column(db.Integer, default=0)
    completed = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    analyses = db.relationship('Analysis', backref='batch', lazy='dynamic')
    
    def __repr__(self):
        return f'<Batch {self.name}>'
    
    @property
    def progress(self):
        if self.total_images == 0:
            return 0
        return int((self.completed / self.total_images) * 100)


class Visualization(db.Model):
    """Store generated visualizations"""
    __tablename__ = 'visualizations'
    
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analyses.id'), nullable=False)
    viz_type = db.Column(db.String(50))  # bitplane, histogram, heatmap, etc.
    filepath = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Visualization {self.viz_type} for Analysis {self.analysis_id}>'


class Settings(db.Model):
    """User settings and preferences"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.JSON)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Setting {self.key}>'