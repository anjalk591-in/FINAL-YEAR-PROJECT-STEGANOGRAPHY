from flask import request, jsonify
from app.blueprints.api import api
from app.models import Analysis, Batch
from app.extensions import db
from app.utils.file_handler import allowed_file, save_uploaded_file, get_image_dimensions
from app.detection.coordinator import DetectionCoordinator

@api.route('/analyze', methods=['POST'])
def analyze():
    """
    Analyze single image via API
    
    POST /api/analyze
    Body: multipart/form-data with 'image' file
    Optional: scan_type (quick|standard|deep)
    
    Returns: JSON with analysis results
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Save file
        scan_type = request.form.get('scan_type', 'standard')
        filepath, original_filename, filesize = save_uploaded_file(file)
        width, height = get_image_dimensions(filepath)
        
        # Create analysis record
        analysis_record = Analysis(
            filename=original_filename,
            filepath=filepath,
            filesize=filesize,
            image_width=width,
            image_height=height,
            scan_type=scan_type
        )
        db.session.add(analysis_record)
        db.session.commit()
        
        # Run detection
        coordinator = DetectionCoordinator(filepath, scan_type)
        detection_results = coordinator.run_analysis()
        
        # Update analysis record
        analysis_record.statistical_results = detection_results['results']['statistical']
        analysis_record.visual_results = detection_results['results']['visual']
        analysis_record.frequency_results = detection_results['results']['frequency']
        analysis_record.format_results = detection_results['results']['format']
        analysis_record.extraction_results = detection_results['results']['extraction']
        analysis_record.score = detection_results['score']
        analysis_record.verdict = detection_results['verdict']
        analysis_record.confidence = detection_results['confidence']
        analysis_record.processing_time = detection_results['processing_time']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_record.id,
            'verdict': analysis_record.verdict,
            'confidence': analysis_record.confidence,
            'score': analysis_record.score,
            'processing_time': analysis_record.processing_time,
            'results': {
                'statistical': analysis_record.statistical_results,
                'visual': analysis_record.visual_results,
                'extraction': analysis_record.extraction_results
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/analysis/<int:analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    """
    Get analysis results by ID
    
    GET /api/analysis/<id>
    
    Returns: Complete analysis results in JSON
    """
    analysis_record = Analysis.query.get(analysis_id)
    
    if not analysis_record:
        return jsonify({'error': 'Analysis not found'}), 404
    
    return jsonify(analysis_record.to_dict()), 200


@api.route('/analyses', methods=['GET'])
def list_analyses():
    """
    List all analyses
    
    GET /api/analyses
    Optional params: limit, offset, verdict
    
    Returns: List of analyses
    """
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    verdict_filter = request.args.get('verdict', None)
    
    query = Analysis.query
    
    if verdict_filter:
        query = query.filter_by(verdict=verdict_filter)
    
    analyses = query.order_by(Analysis.timestamp.desc()).limit(limit).offset(offset).all()
    
    return jsonify({
        'success': True,
        'count': len(analyses),
        'analyses': [a.to_dict() for a in analyses]
    }), 200


@api.route('/stats', methods=['GET'])
def get_stats():
    """
    Get overall statistics
    
    GET /api/stats
    
    Returns: Statistics summary
    """
    total_scans = Analysis.query.count()
    total_detections = Analysis.query.filter(Analysis.confidence >= 50).count()
    avg_confidence = db.session.query(db.func.avg(Analysis.confidence)).scalar() or 0
    
    return jsonify({
        'success': True,
        'total_scans': total_scans,
        'total_detections': total_detections,
        'avg_confidence': round(avg_confidence, 2),
        'detection_rate': round((total_detections / total_scans * 100) if total_scans > 0 else 0, 1)
    }), 200