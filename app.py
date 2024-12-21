import os
from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
from ftplib import FTP, error_perm
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import logging

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = set(os.getenv('ALLOWED_EXTENSIONS').split(','))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FTP server connection details
FTP_HOST = os.getenv('FTP_HOST')
FTP_USER = os.getenv('FTP_USER')
FTP_PASS = os.getenv('FTP_PASS')

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Connect to the FTP server
def connect_ftp():
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        logger.info("Connected to FTP server.")
        return ftp
    except Exception as e:
        logger.error(f"FTP connection failed: {e}")
        raise e

# Home route with file list from FTP
@app.route('/')
def index():
    ftp = connect_ftp()
    try:
        files = ftp.nlst()
    except error_perm as e:
        logger.error(f"Failed to retrieve file list: {e}")
        flash("Could not retrieve files from the server.")
        files = []
    finally:
        ftp.quit()
    
    return render_template('index.html', files=files)

# Upload file to FTP server
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        ftp = connect_ftp()
        try:
            ftp.storbinary(f"STOR {filename}", file.stream)
            flash('File uploaded successfully!', 'success')
            logger.info(f"File {filename} uploaded successfully.")
        except Exception as e:
            flash(f'Failed to upload file: {e}', 'danger')
            logger.error(f"Failed to upload {filename}: {e}")
        finally:
            ftp.quit()
    else:
        flash('Invalid file type!', 'warning')
    
    return redirect(url_for('index'))

# Download file from FTP server
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    ftp = connect_ftp()
    local_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        # Download file from FTP server
        with open(local_file_path, 'wb') as f:
            ftp.retrbinary(f"RETR {filename}", f.write)
        logger.info(f"File {filename} downloaded successfully.")
        flash('File downloaded successfully!', 'success')
    except Exception as e:
        flash(f'Failed to download file: {e}', 'danger')
        logger.error(f"Failed to download {filename}: {e}")
    finally:
        ftp.quit()
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Helper route to delete files
@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    ftp = connect_ftp()
    try:
        ftp.delete(filename)
        flash('File deleted successfully!', 'success')
        logger.info(f"File {filename} deleted successfully.")
    except Exception as e:
        flash(f'Failed to delete file: {e}', 'danger')
        logger.error(f"Failed to delete {filename}: {e}")
    finally:
        ftp.quit()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
