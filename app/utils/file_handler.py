import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def generate_unique_filename(original_filename):
    """Generate unique filename while preserving extension"""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    return unique_name


def save_uploaded_file(file, folder=None):
    """
    Save uploaded file and return filepath
    
    Args:
        file: FileStorage object
        folder: Optional subfolder within UPLOAD_FOLDER
    
    Returns:
        tuple: (filepath, filename, filesize)
    """
    if folder is None:
        folder = current_app.config['UPLOAD_FOLDER']
    
    # Generate unique filename
    original_filename = secure_filename(file.filename)
    unique_filename = generate_unique_filename(original_filename)
    
    # Create full path
    filepath = os.path.join(folder, unique_filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Save file
    file.save(filepath)
    
    # Get file size
    filesize = os.path.getsize(filepath)
    
    return filepath, original_filename, filesize


def get_image_dimensions(filepath):
    """
    Get image dimensions
    
    Args:
        filepath: Path to image file
    
    Returns:
        tuple: (width, height)
    """
    try:
        with Image.open(filepath) as img:
            return img.size
    except Exception:
        return (0, 0)


def delete_file(filepath):
    """Safely delete a file"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except Exception:
        pass
    return False


def cleanup_old_files(folder, max_age_days=7):
    """
    Delete files older than max_age_days
    
    Args:
        folder: Folder to clean
        max_age_days: Maximum age in days
    """
    import time
    
    if not os.path.exists(folder):
        return
    
    current_time = time.time()
    max_age_seconds = max_age_days * 86400
    
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        
        if os.path.isfile(filepath):
            file_age = current_time - os.path.getmtime(filepath)
            
            if file_age > max_age_seconds:
                delete_file(filepath)


def get_file_mime_type(filepath):
    """Get MIME type of file"""
    try:
        with Image.open(filepath) as img:
            return Image.MIME.get(img.format, 'application/octet-stream')
    except Exception:
        return 'application/octet-stream'