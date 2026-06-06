import os
from flask import render_template, request, flash, redirect, url_for, current_app, send_file
from werkzeug.utils import secure_filename
from . import steg
from app.utils.steg import encode_text, decode_text
import uuid

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@steg.route('/encode', methods=['GET', 'POST'])
def encode():
    if request.method == 'POST':
        # Check if file is provided
        if 'image' not in request.files:
            flash('No image file provided', 'danger')
            return redirect(request.url)
            
        file = request.files['image']
        text = request.form.get('secret_text', '')
        technique = request.form.get('technique', 'lsb')
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if not text:
            flash('No secret text provided', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())
            
            # Ensure safe absolute paths based on root directory
            root_dir = os.path.dirname(current_app.root_path)
            upload_dir = os.path.join(root_dir, current_app.config['UPLOAD_FOLDER'])
            reports_dir = os.path.join(root_dir, current_app.config['REPORTS_FOLDER'])
            
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(reports_dir, exist_ok=True)
            
            input_path = os.path.join(upload_dir, f"in_{unique_id}_{filename}")
            output_filename = f"out_{unique_id}.png"
            output_path = os.path.join(reports_dir, output_filename)
            
            file.save(input_path)
            
            # Encode text
            success, msg, final_output_path = encode_text(input_path, text, output_path, technique=technique)
            
            # Clean up input file
            if os.path.exists(input_path):
                os.remove(input_path)
                
            if success:
                download_name = os.path.basename(final_output_path)
                return send_file(final_output_path, as_attachment=True, download_name=download_name)
            else:
                flash(f'Encoding failed: {msg}', 'danger')
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload a PNG or JPG image.', 'danger')
            return redirect(request.url)
            
    return render_template('steg/encode.html')

@steg.route('/decode', methods=['GET', 'POST'])
def decode():
    decoded_message = None
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No image file provided', 'danger')
            return redirect(request.url)
            
        file = request.files['image']
        technique = request.form.get('technique', 'lsb')
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())
            
            root_dir = os.path.dirname(current_app.root_path)
            upload_dir = os.path.join(root_dir, current_app.config['UPLOAD_FOLDER'])
            os.makedirs(upload_dir, exist_ok=True)
            
            input_path = os.path.join(upload_dir, f"dec_{unique_id}_{filename}")
            
            file.save(input_path)
            
            # Decode text
            success, result_or_msg = decode_text(input_path, technique=technique)
            
            # Clean up
            if os.path.exists(input_path):
                os.remove(input_path)
                
            if success:
                decoded_message = result_or_msg
                flash('Message successfully decoded!', 'success')
            else:
                flash(f'Decoding failed: {result_or_msg}', 'danger')
        else:
            flash('Invalid file type. Please upload a PNG or JPG image.', 'danger')
            
    return render_template('steg/decode.html', decoded_message=decoded_message)
