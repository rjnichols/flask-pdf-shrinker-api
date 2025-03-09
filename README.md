Flask PDF Shrinker API
======================

This is a simple Flask API that allows users to upload a PDF file, shrink it (reducing and conforming the filesize to a quality preset) using Ghostscript, and download the shrunk PDF. The service also includes a cleanup mechanism to delete old files from the temporary upload folder on a regular schedule.

Features
--------

*   **Upload PDF**: Users can upload a PDF file via a web form or a POST request.
*   **Shrink PDF**: The API uses Ghostscript to shrink the uploaded PDF file.    
*   **Download Shrunk PDF**: The shrunk PDF is returned as a downloadable file.
*   **Cleanup**: Old files in the temporary upload folder are automatically deleted after 24 hours.
    

Prerequisites
-------------

*   Python 3.x    
*   Ghostscript (install via your package manager, e.g., `sudo apt-get install ghostscript` on Ubuntu)    
*   Flask (`pip install flask`)    
*   Waitress (`pip install waitress`) for running in production
*   WebTest (`pip install webtest`) for running tests
*   ReportLab (`pip install reportlab`) to generate test PDF data
    

Setup
-----

1.  Clone the repository   
2.  Install the required Python packages:    

        pip install -r requirements.txt
    
3.  Ensure Ghostscript is installed on your system.  e.g., `sudo apt-get install ghostscript` on Ubuntu
4.  You can set the `DEBUG` environment variable to `True` to use the Flask Debug Server instead of Waitress.
5.  You can set the `GHOSTSCRIPT_BIN` environment variable to choose which Ghostscript to use. Default is `gs` in path.
6.  You can set the `UPLOAD_FOLDER` environment variable to override where temporary files should be stored.
7.  You can set the `CLEANUP_DURATION_SECONDS` environment variable to override the time after which files temporary files are removed from the server.

Running the Server
------------------

1.  Start the Flask development server:
    
        python app.py
    
2.  The server will be available at `http://127.0.0.1:8080/` for production, or `http://127.0.0.1:5000/` for Debug mode.
    

Usage
-----

### Web Interface

1.  Open your browser and navigate to `http://127.0.0.1:5000/`.
    
2.  Use the form to upload a PDF file.
    
3.  The shrunk PDF will be automatically downloaded.
    

### API Endpoint

You can also interact with the API programmatically using tools like `curl` or Postman.

#### Shrink PDF

*   **Endpoint**: `POST /shrink-pdf`
    
*   **Request**: Include the PDF file in the `file` field of a multipart/form-data request.
    * **Optional:**: Include a specific Ghostscript profile in the `profile` field of the request. Valid settings -
        * `screen` - Screen (low quality, smallest size)
        * `ebook` - Ebook (medium quality, smaller size)
        * `printer` - Printer (high quality)
        * `prepress` (default) - Prepress (highest quality, largest size)
        
*   **Response**: The shrunk PDF file is returned as a downloadable attachment.

You'll find that even the highest `prepress` profile is considerably smaller in size, than many authored PDFs from other sources.    

Example using `curl`:

    curl -X POST -F "file=@/path/to/your/file.pdf" http://127.0.0.1:5000/shrink-pdf --output shrunk.pdf

Testing
-------

The project includes unit tests to verify the functionality of the API.

### Running Tests

1.  Ensure the Flask app is not running (the tests will start their own instance).
    
2.  Run the tests:
        
        python test_app.py    

Project Structure
-----------------


    /
    ├── app.py                # Main Flask application
    ├── test_app.py           # Unit tests for the Flask app
    ├── README.md             # Project documentation
    ├── requirements.txt      # Python dependencies
    └── sample.pdf            # Sample PDF file for testing

License
-------

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

