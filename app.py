from flask import Flask, request, send_file, jsonify
import subprocess
import os
import uuid
import time
import threading
from datetime import datetime, timedelta

app = Flask(__name__)

# Profiles allowed by Ghostscript, first one is used as the default
ACCEPTED_PDFSETTINGS = ['prepress', 'screen', 'ebook', 'printer']

# Debug mode serves with Flask in Debug, Production mode uses Waitress
DEBUG_MODE = (os.getenv('DEBUG_MODE', 'False') == 'True')

# Where is Ghostscript?
GHOSTSCRIPT_BIN = os.getenv('GHOSTSCRIPT_BIN', 'gs')

# Temporary directory to store uploaded and processed files
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/tmp/pdf_uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Duration in seconds, after which files should be deleted
CLEANUP_DURATION_SECONDS = int(os.getenv('CLEANUP_DURATION_SECONDS', "3600"))

def cleanup_old_files():
    """Delete files in the UPLOAD_FOLDER that are older than CLEANUP_DURATION_SECONDS."""
    now = datetime.now()
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            file_update_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if now - file_update_time > timedelta(seconds=CLEANUP_DURATION_SECONDS):
                os.remove(file_path)
                print(f"Deleted old file: {file_path}")

def cleanup_old_files_daemon():
    while True:
        try:
            cleanup_old_files()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        # Sleep for 1 minute before the next cleanup
        time.sleep(60)

# for tests
app.cleanup_old_files = cleanup_old_files
app.UPLOAD_FOLDER = UPLOAD_FOLDER
app.CLEANUP_DURATION_SECONDS = CLEANUP_DURATION_SECONDS

@app.route('/', methods=['GET'])
def index():
    # Basic HTML form for file upload
    return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Shrink PDF</title>
        </head>
        <body>
            <h1>Upload PDF to Shrink</h1>
            <form action="/shrink-pdf" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".pdf" required>
                <label for="profile">Output Profile:</label>
                <select name="profile" id="profile">
                    <option value="screen">Screen (low quality, smallest size)</option>
                    <option value="ebook">Ebook (medium quality, smaller size)</option>
                    <option value="printer">Printer (high quality)</option>
                    <option value="prepress" selected>Prepress (highest quality, largest size)</option>
                </select>
                <button type="submit">Shrink PDF</button>
            </form>
        </body>
        </html>
    '''

@app.route('/shrink-pdf', methods=['POST'])
def shrink_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.lower().endswith('.pdf'):
        # Generate unique filenames for the uploaded and output files
        fileuuid = uuid.uuid4()
        input_filename = os.path.join(UPLOAD_FOLDER, f"{fileuuid}.pdf")
        output_filename = os.path.join(UPLOAD_FOLDER, f"{fileuuid}_shrunk.pdf")

        # Save the uploaded file
        file.save(input_filename)

         # Get the PDFSETTINGS parameter (default to first in accepted, if not provided)
        profile = request.form.get('profile', ACCEPTED_PDFSETTINGS[0])

        # Validate the PDFSETTINGS value
        if profile not in ACCEPTED_PDFSETTINGS:
            return jsonify({"error": f"Invalid value for profile. Accepted values are: {ACCEPTED_PDFSETTINGS}"}), 400

        # Use Ghostscript to shrink the PDF
        try: 
            subprocess.run([
                GHOSTSCRIPT_BIN, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                '-dPDFSETTINGS=/'+profile, '-dNOPAUSE', '-dQUIET', '-dBATCH',
                f'-sOutputFile={output_filename}', input_filename
            ], check=True)

        except subprocess.CalledProcessError as e:
            return jsonify({"error": "Failed to process PDF"}), 500

        input_file_size = os.path.getsize(input_filename)        
        output_file_size = os.path.getsize(output_filename)

        # Check if the output file is smaller than the input file
        if output_file_size >= input_file_size:
            return jsonify({"error": "Failed to shrink the PDF: Output file is not smaller than the input file"}), 400

        # Return the shrunk PDF file
        return send_file(output_filename, as_attachment=True, download_name=f"{fileuuid}.pdf")

    return jsonify({"error": "Invalid file type, only PDFs are allowed"}), 400

if __name__ == '__main__':
    # Start the cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_old_files_daemon)
    cleanup_thread.daemon = True  # Daemonize thread to stop it when the main program exits
    cleanup_thread.start()

    # Run the Flask app
    if DEBUG_MODE:
        app.run(debug=True)
    else:
        from waitress import serve
        serve(app, host="0.0.0.0", port=8080)
