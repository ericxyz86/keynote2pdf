# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Keynote to PDF Converter is a Flask web application that converts Apple Keynote (.key) files to PDF format with optimized compression and merging capabilities. The application is macOS-specific and requires the Keynote application to be installed.

## Development Commands

### Running the Application

```bash
# Development mode (with auto-reload)
python app.py

# Production mode (recommended)
gunicorn -w 4 -b 127.0.0.1:8080 app:app
```

The application runs on `http://127.0.0.1:8080` by default.

### Environment Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir uploads converted
```

### Configuration via Environment Variables

- `FLASK_DEBUG`: Set to "1" for development mode
- `HOST`: Server host (default: 127.0.0.1)
- `PORT`: Server port (default: 8080)
- `FLASK_SECRET_KEY`: **[REQUIRED FOR PRODUCTION]** Secret key for Flask sessions. If not set, a secure random key will be auto-generated with a warning. Generate with: `python -c 'import secrets; print(secrets.token_hex(32))'`

## Architecture

### Core Conversion Pipeline

The application follows a multi-stage conversion process:

1. **File Upload**: Users upload .key files via the web interface
2. **Keynote Export**: AppleScript commands drive Keynote to export to PDF
3. **Image Compression**: PyMuPDF scans the PDF and compresses embedded images
4. **Cleanup**: Temporary files are automatically removed

### Key Components

#### app.py:90-210 - Keynote Conversion Functions

- `convert_key_to_pdf()`: Main conversion orchestrator that coordinates the pipeline
- `keynote_to_pdf()`: Uses AppleScript to drive Keynote's export functionality (with proper escaping to prevent injection)
- `escape_applescript_string()`: Security helper that escapes strings before AppleScript execution
- `compress_pdf_images()`: Post-processes PDFs to compress embedded raster images

The conversion process uses a temporary file approach to ensure atomicity and enable fallback to uncompressed PDFs if compression fails.

#### app.py:217-237 - AppleScript Security

The `escape_applescript_string()` function prevents code injection by properly escaping:
- Backslashes (`\` → `\\`)
- Double quotes (`"` → `\"`)

This is **critical** - never insert user-controlled strings directly into AppleScript without escaping.

#### app.py:295-508 - Image Compression Strategy

The `compress_pdf_images()` function:
- Iterates through all pages and extracts embedded images using PyMuPDF
- Downsamples images relative to a 300 DPI reference (configurable via `dpi` parameter)
- Converts to RGB color space and re-compresses as JPEG with specified quality
- **Only replaces images if the compressed version is smaller** (avoids increasing file size)
- Skips very small images (< 5KB) to avoid unnecessary processing
- Uses PyMuPDF's deflate compression when saving the final document

#### app.py:718-796 - PDF Merging

The `/merge` endpoint:
- Uses PyMuPDF's `insert_pdf()` method for efficient page-level merging
- Applies stream compression (`deflate=True`) during the save operation
- Tracks compression ratios and logs detailed statistics

### AppleScript Integration

The application uses `osascript` to control Keynote programmatically (app.py:239-292). The script:
- Opens the .key file in Keynote
- Exports to PDF format
- Closes the document without saving
- Includes error handling to clean up open documents on failure
- **Uses proper escaping to prevent AppleScript injection attacks**

### Important Design Decisions

1. **Removed Unused Functions**: The `convert_to_pdfa()` and `compress_pdf()` functions were removed from the codebase. They were not used in the active pipeline and posed potential security risks.

2. **Temporary File Pattern**: Conversions use temporary files in the same directory as the final output to avoid cross-device move issues (app.py:107-110).

3. **Fallback Strategy**: If image compression fails, the application falls back to the uncompressed PDF rather than failing the entire conversion (app.py:150-178).

4. **Memory Management**: PIL images are explicitly deleted after processing to manage memory with large files.

5. **Error Message Sanitization**: The application uses `log_error_return_generic()` to log detailed errors server-side while returning generic messages to users, preventing information disclosure (app.py:62-74).

## macOS Integration

### LaunchAgent Setup

The application includes installation scripts for running as a LaunchAgent:

- `install.sh`: Sets up the LaunchAgent to run at login
- `uninstall.sh`: Removes the LaunchAgent configuration
- `com.keynote2pdf.converter.plist`: LaunchAgent configuration
- `run.sh`: Startup script invoked by the LaunchAgent

### Menu Bar Application

The `Keynote2PDF.app` bundle provides a menu bar interface for easy access. It uses the `rumps` Python library to create a native macOS menu bar application.

## Logging

All operations are logged to `app.log` with detailed information including:
- File conversion progress and timings
- Compression ratios (before/after sizes)
- Image processing statistics (processed/skipped counts)
- Error messages with stack traces

Error-level logs are also written to `error.log` by the LaunchAgent.

## File Size Limits

- Maximum upload size: 300MB (app.py:35)
- Pillow decompression limit: 500 million pixels (~22k x 22k image) to prevent DoS attacks (app.py:23-25)

## Security Considerations

**IMPORTANT**: A comprehensive security review was conducted on 2025-11-11. See `SECURITY_FIXES.md` for detailed information about vulnerabilities that were identified and fixed.

### Security Features Implemented

#### 1. Input Validation & Sanitization
- **Filename Sanitization**: All user-supplied filenames are sanitized using `secure_filename()` from Werkzeug before any file operations
- **File Type Validation**: Only `.key` files are accepted for upload (app.py:77-81)
- **Path Traversal Protection**: Uses `os.path.join()` and `send_from_directory()` to prevent directory traversal attacks
- **AppleScript Injection Prevention**: File paths are escaped using `escape_applescript_string()` before being inserted into AppleScript (app.py:217-227)

#### 2. Cryptographic Security
- **Secret Key Management** (app.py:39-47):
  - Auto-generates cryptographically secure random key using `secrets.token_hex(32)` if `FLASK_SECRET_KEY` not set
  - Logs warning when using auto-generated key
  - **Production requirement**: Always set `FLASK_SECRET_KEY` environment variable

#### 3. Security Headers (app.py:563-581)
The application sets comprehensive security headers on all responses:
- **X-Frame-Options: DENY** - Prevents clickjacking
- **X-Content-Type-Options: nosniff** - Prevents MIME-type sniffing
- **X-XSS-Protection: 1; mode=block** - Enables browser XSS filter
- **Content-Security-Policy** - Restricts resource loading to trusted sources
- **Strict-Transport-Security** (production only) - Forces HTTPS connections

#### 4. Information Disclosure Prevention
- **Generic Error Messages**: `log_error_return_generic()` logs detailed errors server-side but returns generic messages to users (app.py:62-74)
- **No Stack Traces**: Exception details are never exposed in HTTP responses
- **Detailed Server Logs**: Full error information is logged to `app.log` for debugging

#### 5. Denial of Service Protection
- **Image Decompression Limit**: 500 million pixel limit prevents decompression bomb attacks (app.py:23-25)
- **Upload Size Limit**: 300MB maximum to prevent resource exhaustion (app.py:35)
- **Localhost Binding**: In production, application binds only to 127.0.0.1 (app.py:833)

#### 6. Session Security
- **Secure Session Management**: Flask sessions use cryptographically signed cookies
- **Immediate File Cleanup**: Uploaded `.key` files are deleted immediately after processing to minimize exposure

### XSS Protection
- **Jinja2 Auto-escaping**: Flask's Jinja2 template engine auto-escapes all variables by default
- **No Unsafe Filters**: The `templates/index.html` does not use `|safe` or `|raw` filters

### CSRF Considerations
- **Low Risk**: POST endpoints (`/merge`, `/delete`) accept JSON without CSRF tokens
- **Mitigation**: Application binds to localhost (127.0.0.1) in production, preventing external access
- **Future Enhancement**: If the application is ever exposed beyond localhost, implement CSRF protection using Flask-WTF

### Security Testing
When making changes that could affect security:
1. Test filename handling with special characters: quotes, backslashes, Unicode
2. Verify error messages don't leak sensitive information
3. Check security headers are present: `curl -I http://localhost:8080`
4. Ensure `FLASK_SECRET_KEY` warning appears when environment variable is not set
5. Test image upload with large/malicious images to verify limits work

### Production Security Checklist
- [ ] Set `FLASK_SECRET_KEY` environment variable to a cryptographically secure value
- [ ] Verify application binds only to localhost or uses a properly configured reverse proxy
- [ ] Ensure `FLASK_DEBUG` is not set or set to "0"
- [ ] Review logs regularly for security warnings or suspicious activity
- [ ] Keep dependencies updated (Flask, PyMuPDF, Pillow)
- [ ] Consider adding rate limiting for additional DoS protection

## Deployment

For production deployment on Render.com, the `render.yaml` configuration:
- Uses Python 3.9.12
- Installs dependencies via pip
- Runs with Gunicorn as the WSGI server
- **Note**: The Render deployment will not work properly because it requires macOS and Keynote, which are not available in Render's Linux environment. This is primarily for local development.
