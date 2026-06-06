from flask import render_template, request, flash, redirect, url_for
from app.blueprints.batch import batch
from app.models import Batch as BatchModel, Analysis
from app.extensions import db
from app.utils.file_handler import allowed_file, save_uploaded_file, get_image_dimensions
from app.detection.coordinator import DetectionCoordinator
from datetime import datetime

@batch.route('/upload', methods=['GET', 'POST'])
def upload():
    """Batch upload and analyze"""
    if request.method == 'POST':
        files = request.files.getlist('images')
        
        if not files or files[0].filename == '':
            flash('No files selected', 'error')
            return redirect(request.url)
        
        # Filter valid files
        valid_files = [f for f in files if f and allowed_file(f.filename)]
        
        if not valid_files:
            flash('No valid image files found', 'error')
            return redirect(request.url)
        
        # Create batch
        scan_type = request.form.get('scan_type', 'standard')
        batch_record = BatchModel(
            name=f"Batch {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            total_images=len(valid_files),
            status='processing'
        )
        db.session.add(batch_record)
        db.session.commit()
        
        # Process each file
        for file in valid_files:
            try:
                # Save file
                filepath, original_filename, filesize = save_uploaded_file(file)
                width, height = get_image_dimensions(filepath)
                
                # Create analysis record
                analysis_record = Analysis(
                    filename=original_filename,
                    filepath=filepath,
                    filesize=filesize,
                    image_width=width,
                    image_height=height,
                    scan_type=scan_type,
                    batch_id=batch_record.id
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
                
                # Update batch progress
                batch_record.completed += 1
                db.session.commit()
                
            except Exception as e:
                flash(f'Error processing {file.filename}: {str(e)}', 'error')
                continue
        
        # Mark batch as completed
        batch_record.status = 'completed'
        batch_record.completed_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'Batch processing complete! {batch_record.completed}/{batch_record.total_images} images analyzed.', 'success')
        return redirect(url_for('batch.view_batch', batch_id=batch_record.id))
    
    return render_template('batch/upload.html')


@batch.route('/view/<int:batch_id>')
def view_batch(batch_id):
    """View batch results"""
    batch_record = BatchModel.query.get_or_404(batch_id)
    analyses = Analysis.query.filter_by(batch_id=batch_id).all()
    
    # Calculate statistics
    total_detections = sum(1 for a in analyses if a.confidence >= 50)
    avg_confidence = sum(a.confidence for a in analyses) / len(analyses) if analyses else 0
    
    stats = {
        'total_detections': total_detections,
        'avg_confidence': round(avg_confidence, 2),
        'detection_rate': round((total_detections / len(analyses) * 100) if analyses else 0, 1)
    }
    
    return render_template('batch/view.html', 
                         batch=batch_record, 
                         analyses=analyses,
                         stats=stats)