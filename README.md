# Keynote to PDF Converter

A Flask web application that converts Apple Keynote (.key) files to PDF format with optimized compression and merging capabilities.

## 📥 Download for macOS

**[Download Keynote2PDF Installer](https://github.com/ericxyz86/keynote2pdf/releases/latest/download/Keynote2PDF-Installer.dmg)**

⚠️ **First Time Setup**: macOS will block the app with a security warning because it's not signed. This is normal! See the [User Guide](USER_GUIDE.md#️-first-time-installation---macos-security) for step-by-step instructions to open it safely.

After installation, open your browser and go to **http://127.0.0.1:8080** to use the app.

**👉 [Read the User Guide](USER_GUIDE.md)** for complete instructions.

---

## Features

- Convert Keynote files to PDF with optimized image compression
- Merge multiple PDFs with efficient compression
- Web interface for easy file upload and management
- Automatic cleanup of temporary files
- Detailed logging for troubleshooting
- Support for large files (up to 300MB)

## Requirements

- Python 3.6+
- macOS (for Keynote conversion)
- Keynote application installed
- Required Python packages:
  ```
  Flask
  PyMuPDF (fitz)
  Pillow
  Werkzeug
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/keynote2pdf.git
   cd keynote2pdf
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create necessary directories:
   ```bash
   mkdir uploads converted
   ```

## Usage

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:8080
   ```

3. Upload Keynote files through the web interface

4. Convert and merge PDFs as needed

## Optimization Features

### Image Compression
- Automatically detects and compresses large images
- Uses Lanczos resampling for high-quality downscaling
- Converts images to RGB color space for optimal JPEG compression
- Skips small images (< 5KB) to avoid unnecessary processing
- Only replaces images if the compressed version is smaller

### PDF Merging
- Uses PyMuPDF for efficient PDF merging
- Applies stream compression during merge
- Maintains image quality while reducing file size
- Supports merging of multiple PDFs with progress tracking

### Performance Improvements
- Removed PDF/A conversion to reduce processing time
- Optimized memory usage with proper resource cleanup
- Efficient temporary file handling
- Detailed logging for monitoring and debugging

## Configuration

The application can be configured through environment variables:

- `FLASK_DEBUG`: Set to "1" for development mode
- `HOST`: Server host (default: 127.0.0.1)
- `PORT`: Server port (default: 8080)
- `FLASK_SECRET_KEY`: Secret key for Flask sessions

## Production Deployment

For production use, it's recommended to:

1. Use a production WSGI server (e.g., Gunicorn):
   ```bash
   gunicorn -w 4 -b 127.0.0.1:8080 app:app
   ```

2. Set up a reverse proxy (e.g., Nginx)
3. Configure proper security settings
4. Monitor the application logs

## Logging

Logs are written to `app.log` in the project directory. The log includes:
- File conversion details
- Compression ratios
- Error messages
- Processing statistics

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 