import unittest
import os
import time
import uuid
from datetime import datetime, timedelta
from webtest import TestApp
from app import app  # Import the Flask app

from PIL import Image as PILImage
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
import io

# Temporary directory used by the Flask app
UPLOAD_FOLDER = app.UPLOAD_FOLDER
sample_pdf_path = "sample.pdf"
output_pdf_path = "shrunk.pdf"


# Generate a Gaussian noise image
def generate_gaussian_noise_image(width, height):
    # Create a numpy array with random Gaussian noise
    noise = np.random.normal(128, 30, (height, width, 3)).astype(np.uint8)
    # Convert the numpy array to a PIL image
    image = PILImage.fromarray(noise, 'RGB')
    return image

# Create a PDF file
def create_test_pdf(filename):
    # Create a SimpleDocTemplate object
    doc = SimpleDocTemplate(filename, pagesize=A4)

    # Create a list to hold the content
    content = []

    # Get the sample style sheet
    styles = getSampleStyleSheet()

    # Generate a Gaussian noise image
    image_width, image_height = 600, 400  # Dimensions of the generated image
    noise_image = generate_gaussian_noise_image(image_width, image_height)

    # Convert the PIL image to a format ReportLab can use
    img_buffer = io.BytesIO()
    noise_image.save(img_buffer, format='JPEG')
    img_buffer.seek(0)

    # Add content to the PDF
    for i in range(10):  # Create some pages
        # Add some text
        text = f"This is page {i+1} of the PDF."
        content.append(Paragraph(text, styles['Normal']))
        content.append(Spacer(1, 12))

        # Add the generated image multiple times to increase the file size
        for _ in range(2):  # Add the image multiple times per page
            img = Image(img_buffer, width=6*inch, height=4*inch)
            content.append(img)
            content.append(Spacer(1, 12))

        content.append(PageBreak())

    # Build the PDF
    doc.build(content)

class TestFlaskAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up the WebTest app for testing."""
        cls.app = TestApp(app)

    def tearDown(self):
        # clean up test files
        if os.path.exists(sample_pdf_path):
            os.remove(sample_pdf_path)

        if os.path.exists(output_pdf_path):
            os.remove(output_pdf_path)

    def test_index_page(self):
        """Test that the index page returns a 200 status code and contains the upload form."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("Upload PDF to Shrink", response.text)

    def test_shrink_pdf_endpoint(self):
        """Test that the /shrink-pdf endpoint processes a PDF file correctly."""

        # create a synthetic PDF test document
        create_test_pdf(sample_pdf_path)

        # Path to a sample PDF file (replace with a real PDF file for testing)
        if not os.path.exists(sample_pdf_path):
            self.skipTest("Sample PDF file not found. Please provide a PDF file named 'sample.pdf' in the test directory.")

        # Upload the PDF file
        with open(sample_pdf_path, 'rb') as file:
            response = self.app.post('/shrink-pdf', upload_files=[('file', file.name, file.read())])

        # Check the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/pdf')
        self.assertIn('attachment; filename=', response.headers['Content-Disposition'])

        # Save the shrunk PDF for inspection
        with open(output_pdf_path, 'wb') as f:
            f.write(response.body)
        self.assertFalse(os.path.exists(output_pdf_path))
        self.assertTrue(os.path.getsize(output_pdf_path) < os.path.getsize(sample_pdf_path))

    def test_invalid_file_upload(self):
        """Test that the /shrink-pdf endpoint rejects non-PDF files."""
        # Create a dummy non-PDF file
        dummy_file_path = "dummy.txt"
        with open(dummy_file_path, 'w') as f:
            f.write("This is not a PDF file.")

        # Upload the dummy file
        with open(dummy_file_path, 'rb') as file:
            response = self.app.post('/shrink-pdf', upload_files=[('file', file.name, file.read())], expect_errors=True)

        os.remove(dummy_file_path)
        # Check the response
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid file type, only PDFs are allowed", response.json['error'])

    def test_invalid_file_upload_as_pdf(self):
        """Test that the /shrink-pdf endpoint 5xx for non-PDF files told as PDF."""
        # Create a dummy non-PDF file
        dummy_file_path = "dummy.txt"
        with open(dummy_file_path, 'w') as f:
            f.write("This is not a PDF file.")

        # Upload the dummy file
        with open(dummy_file_path, 'rb') as file:
            response = self.app.post('/shrink-pdf', upload_files=[('file', file.name+'.pdf', file.read())], expect_errors=True)

        os.remove(dummy_file_path)
        # Check the response
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to process PDF", response.json['error'])

    def test_shrink_pdf_with_custom_pdfsettings(self):
        """Test that the /shrink-pdf endpoint processes a PDF file with custom PDFSETTINGS."""

        create_test_pdf(sample_pdf_path)
        if not os.path.exists(sample_pdf_path):
            self.skipTest("Sample PDF file not found.")

        # Upload the PDF file with custom PDFSETTINGS
        with open(sample_pdf_path, 'rb') as file:
            response = self.app.post('/shrink-pdf', upload_files=[('file', file.name, file.read())], 
                                    params={'profile': 'ebook'})

        # Check the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/pdf')
        self.assertIn('attachment; filename=', response.headers['Content-Disposition'])    

    def test_shrink_pdf_with_invalid_custom_pdfsettings(self):
        """Test that the /shrink-pdf endpoint processes a PDF file with custom PDFSETTINGS."""
        
        create_test_pdf(sample_pdf_path)        
        if not os.path.exists(sample_pdf_path):
            self.skipTest("Sample PDF file not found.")

        # Upload the PDF file with custom PDFSETTINGS
        with open(sample_pdf_path, 'rb') as file:
            response = self.app.post('/shrink-pdf', upload_files=[('file', file.name, file.read())], 
                                    params={'profile': 'something else'}, expect_errors=True)

        # Check the response
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid value for profile", response.json['error'])

    def test_cleanup_old_files(self):
        """Test that old files in the UPLOAD_FOLDER are cleaned up."""
        # Create a dummy file in the UPLOAD_FOLDER with a timestamp older than CLEANUP_DURATION_SECONDS 
        old_file_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.pdf")
        with open(old_file_path, 'w') as f:
            f.write("This is an old file.")

        # Set the file's creation time to 25 hours ago
        old_time = datetime.now() - timedelta(seconds=app.CLEANUP_DURATION_SECONDS+5)
        os.utime(old_file_path, (old_time.timestamp(), old_time.timestamp()))

        app.cleanup_old_files()

        # Check that the old file was deleted
        self.assertFalse(os.path.exists(old_file_path))

if __name__ == '__main__':
    unittest.main()
