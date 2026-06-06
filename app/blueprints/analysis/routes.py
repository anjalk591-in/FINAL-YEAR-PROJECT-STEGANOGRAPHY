from flask import render_template, request, flash, redirect, url_for, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from app.blueprints.analysis import analysis
from app.models import Analysis as AnalysisModel, Visualization
from app.extensions import db
from app.utils.file_handler import allowed_file, save_uploaded_file, get_image_dimensions
from app.utils.json_serializer import serialize_results  # ADD THIS IMPORT
from app.detection.coordinator import DetectionCoordinator
import os

@analysis.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload and analyze image"""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'image' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['image']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Get scan type
            scan_type = request.form.get('scan_type', 'standard')
            
            # Save file
            filepath, original_filename, filesize = save_uploaded_file(file)
            
            # Get image dimensions
            width, height = get_image_dimensions(filepath)
            
            # Create analysis record
            analysis_record = AnalysisModel(
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
            try:
                coordinator = DetectionCoordinator(filepath, scan_type)
                detection_results = coordinator.run_analysis(analysis_id=analysis_record.id)
                
                # Update analysis record - SERIALIZE JSON FIELDS
                analysis_record.statistical_results = serialize_results(detection_results['results']['statistical'])
                analysis_record.visual_results = serialize_results(detection_results['results']['visual'])
                analysis_record.frequency_results = serialize_results(detection_results['results']['frequency'])
                analysis_record.format_results = serialize_results(detection_results['results']['format'])
                analysis_record.extraction_results = serialize_results(detection_results['results']['extraction'])
                
                # Convert numeric fields to Python types
                analysis_record.score = int(detection_results['score']) if detection_results.get('score') is not None else 0
                analysis_record.verdict = str(detection_results['verdict']) if detection_results.get('verdict') else 'Unknown'
                analysis_record.confidence = float(detection_results['confidence']) if detection_results.get('confidence') is not None else 0.0
                analysis_record.processing_time = float(detection_results['processing_time']) if detection_results.get('processing_time') is not None else 0.0
                
                # Save visualizations
                for viz_type, viz_filename in detection_results.get('visualizations', {}).items():
                    if viz_filename:
                        viz_record = Visualization(
                            analysis_id=analysis_record.id,
                            viz_type=viz_type,
                            filepath=viz_filename
                        )
                        db.session.add(viz_record)
                
                db.session.commit()
                
                flash(f'Analysis complete! Verdict: {detection_results["verdict"]}', 'success')
                return redirect(url_for('analysis.view_result', analysis_id=analysis_record.id))
            
            except Exception as e:
                db.session.rollback()  # IMPORTANT: Rollback on error
                flash(f'Error during analysis: {str(e)}', 'error')
                
                # Try to clean up
                try:
                    db.session.delete(analysis_record)
                    db.session.commit()
                except:
                    db.session.rollback()
                
                return redirect(request.url)
        else:
            flash('Invalid file type. Allowed: PNG, JPG, JPEG, BMP, GIF', 'error')
            return redirect(request.url)
    
    return render_template('analysis/upload.html')


@analysis.route('/result/<int:analysis_id>')
def view_result(analysis_id):
    """View analysis results"""
    analysis_record = AnalysisModel.query.get_or_404(analysis_id)
    
    return render_template('analysis/result.html', analysis=analysis_record)


@analysis.route('/delete/<int:analysis_id>', methods=['POST'])
def delete(analysis_id):
    """Delete an analysis"""
    analysis_record = AnalysisModel.query.get_or_404(analysis_id)
    
    # Delete file
    if os.path.exists(analysis_record.filepath):
        os.remove(analysis_record.filepath)
    
    # Delete from database
    db.session.delete(analysis_record)
    db.session.commit()
    
    flash('Analysis deleted successfully', 'success')
    return redirect(url_for('main.dashboard'))


@analysis.route('/download/<int:analysis_id>')
def download_image(analysis_id):
    """Download analyzed image"""
    analysis_record = AnalysisModel.query.get_or_404(analysis_id)
    # Get absolute path
    filepath = os.path.abspath(analysis_record.filepath)

    if os.path.exists(filepath):
        return send_file(
            filepath,
            as_attachment=True,
            download_name=analysis_record.filename
        )
    else:
        flash('File not found', 'error')
        return redirect(url_for('main.dashboard'))


@analysis.route('/visualization/<int:viz_id>')
def view_visualization(viz_id):
    """Serve visualization image"""
    viz_record = Visualization.query.get_or_404(viz_id)
    
    # Build path from project root (not from app folder)
    viz_path = os.path.join(
        current_app.config['VISUALIZATIONS_FOLDER'],
        viz_record.filepath
    )
    
    # Make it absolute
    viz_path = os.path.abspath(viz_path)
    
    if os.path.exists(viz_path):
        return send_file(viz_path, mimetype='image/png')
    else:
        # Debug: show what path we're looking for
        return f"File not found: {viz_path}", 404


@analysis.route('/reanalyze/<int:analysis_id>', methods=['POST'])
def reanalyze(analysis_id):
    """Re-run analysis on existing image"""
    analysis_record = AnalysisModel.query.get_or_404(analysis_id)
    
    scan_type = request.form.get('scan_type', analysis_record.scan_type)
    
    if not os.path.exists(analysis_record.filepath):
        flash('Original file not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Run detection
        coordinator = DetectionCoordinator(analysis_record.filepath, scan_type)
        detection_results = coordinator.run_analysis(analysis_id=analysis_record.id)
        
        # Update analysis record - SERIALIZE JSON FIELDS
        analysis_record.statistical_results = serialize_results(detection_results['results']['statistical'])
        analysis_record.visual_results = serialize_results(detection_results['results']['visual'])
        analysis_record.frequency_results = serialize_results(detection_results['results']['frequency'])
        analysis_record.format_results = serialize_results(detection_results['results']['format'])
        analysis_record.extraction_results = serialize_results(detection_results['results']['extraction'])
        
        # Convert numeric fields to Python types
        analysis_record.score = int(detection_results['score']) if detection_results.get('score') is not None else 0
        analysis_record.verdict = str(detection_results['verdict']) if detection_results.get('verdict') else 'Unknown'
        analysis_record.confidence = float(detection_results['confidence']) if detection_results.get('confidence') is not None else 0.0
        analysis_record.processing_time = float(detection_results['processing_time']) if detection_results.get('processing_time') is not None else 0.0
        analysis_record.scan_type = scan_type
        
        # Delete old visualizations
        Visualization.query.filter_by(analysis_id=analysis_record.id).delete()
        
        # Save new visualizations
        for viz_type, viz_filename in detection_results.get('visualizations', {}).items():
            if viz_filename:
                viz_record = Visualization(
                    analysis_id=analysis_record.id,
                    viz_type=viz_type,
                    filepath=viz_filename
                )
                db.session.add(viz_record)
        
        db.session.commit()
        
        flash('Re-analysis complete!', 'success')
        return redirect(url_for('analysis.view_result', analysis_id=analysis_record.id))
    
    except Exception as e:
        db.session.rollback()  # IMPORTANT: Rollback on error
        flash(f'Error during re-analysis: {str(e)}', 'error')
        return redirect(url_for('analysis.view_result', analysis_id=analysis_record.id))