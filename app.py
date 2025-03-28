import os
import subprocess
import uuid
from flask import (
    Flask,
    request,
    render_template,
    send_from_directory,
    flash,
    url_for,
    redirect,
)
from werkzeug.utils import secure_filename
import logging

# --- Configuration ---
# Use absolute paths for reliability
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
CONVERTED_FOLDER = os.path.join(BASE_DIR, "converted")
ALLOWED_EXTENSIONS = {"key"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["CONVERTED_FOLDER"] = CONVERTED_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # Max upload 300 MB total
app.secret_key = "your_very_secret_key_here"  # Change this in production!

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Helper Functions ---


def allowed_file(filename):
    """Checks if the filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def create_folders():
    """Creates upload and converted folders if they don't exist."""
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["CONVERTED_FOLDER"], exist_ok=True)


def convert_key_to_pdf(key_filepath, pdf_filepath):
    """
    Uses AppleScript to ask Keynote to export a .key file to .pdf.
    Returns True on success, False on failure.
    """
    logging.info(f"Attempting conversion: {key_filepath} -> {pdf_filepath}")
    # Ensure paths are absolute for AppleScript
    abs_key_path = os.path.abspath(key_filepath)
    abs_pdf_path = os.path.abspath(pdf_filepath)

    # Check if input file exists before attempting conversion
    if not os.path.exists(abs_key_path):
        logging.error(f"Input Keynote file not found: {abs_key_path}")
        return False, "Input file not found"

    # Construct the AppleScript command with proper escaping
    applescript = f'''
    tell application "Keynote"
        set keyFile to (POSIX file "{abs_key_path}") as alias
        set pdfFile to "{abs_pdf_path}"
        
        try
            open keyFile
            delay 1 -- Give Keynote a moment to open the file
            
            tell front document
                export to (POSIX file pdfFile) as PDF
                close saving no
            end tell
            
            return "success"
            
        on error errMsg number errNum
            try
                if front document exists then
                    close front document saving no
                end if
            end try
            error "Error: " & errMsg number errNum
        end try
    end tell
    '''

    try:
        # Execute the AppleScript using osascript
        process = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit code, we check output
            timeout=120,  # Add a timeout (e.g., 120 seconds)
        )

        # Check output and return code
        if process.returncode == 0 and "success" in process.stdout.strip().lower():
            if os.path.exists(abs_pdf_path):
                logging.info(f"Successfully converted {os.path.basename(key_filepath)}")
                return True, "Success"
            else:
                # Script ran but file wasn't created - rare but possible
                logging.error(
                    f"Conversion script ran for {os.path.basename(key_filepath)}, but output PDF not found."
                )
                return False, "Output PDF not generated despite script success"
        else:
            error_message = (
                process.stderr.strip() if process.stderr else process.stdout.strip()
            )
            if not error_message:
                error_message = f"osascript exited with code {process.returncode}"
            logging.error(
                f"AppleScript execution failed for {os.path.basename(key_filepath)}. Error: {error_message}"
            )
            return False, f"AppleScript Error: {error_message}"

    except subprocess.TimeoutExpired:
        logging.error(f"Conversion timed out for {os.path.basename(key_filepath)}")
        return False, "Conversion process timed out"
    except Exception as e:
        logging.error(
            f"Failed to run osascript for {os.path.basename(key_filepath)}. Error: {e}"
        )
        return False, f"Subprocess execution failed: {e}"


# --- Flask Routes ---


@app.route("/", methods=["GET", "POST"])
def upload_and_convert():
    """Handles file uploads and initiates conversion."""
    pdf_files = []
    failed_files = {}  # Dictionary to store {original_filename: error_message}

    if request.method == "POST":
        # Check if the post request has the file part
        if "keynote_files" not in request.files:
            flash("No file part in the request.", "error")
            return redirect(request.url)

        files = request.files.getlist("keynote_files")  # Get list of files

        if not files or files[0].filename == "":
            flash("No selected files.", "error")
            return redirect(request.url)

        processed_count = 0
        for file in files:
            if file and allowed_file(file.filename):
                # Sanitize filename and create unique names to avoid clashes
                original_filename = secure_filename(file.filename)
                unique_id = uuid.uuid4().hex[:8]
                temp_filename = (
                    f"{os.path.splitext(original_filename)[0]}_{unique_id}.key"
                )
                key_filepath = os.path.join(app.config["UPLOAD_FOLDER"], temp_filename)

                try:
                    file.save(key_filepath)
                    logging.info(f"Saved uploaded file: {key_filepath}")

                    # Prepare output PDF path
                    pdf_filename = (
                        f"{os.path.splitext(original_filename)[0]}_{unique_id}.pdf"
                    )
                    pdf_filepath = os.path.join(
                        app.config["CONVERTED_FOLDER"], pdf_filename
                    )

                    # Perform conversion
                    success, message = convert_key_to_pdf(key_filepath, pdf_filepath)

                    if success:
                        pdf_files.append(pdf_filename)
                        processed_count += 1
                    else:
                        failed_files[original_filename] = message
                        logging.warning(
                            f"Failed to convert {original_filename}: {message}"
                        )

                    # Clean up the uploaded .key file immediately after processing
                    try:
                        os.remove(key_filepath)
                        logging.info(f"Removed uploaded file: {key_filepath}")
                    except OSError as e:
                        logging.error(
                            f"Error removing uploaded file {key_filepath}: {e}"
                        )

                except Exception as e:
                    logging.error(f"Error processing file {original_filename}: {e}")
                    failed_files[original_filename] = (
                        f"Server error during processing: {e}"
                    )
                    # Attempt cleanup if file was saved
                    if os.path.exists(key_filepath):
                        try:
                            os.remove(key_filepath)
                        except OSError as remove_err:
                            logging.error(
                                f"Error removing file {key_filepath} after error: {remove_err}"
                            )

            elif file and file.filename != "":
                flash(
                    f"File type not allowed for '{file.filename}'. Only .key files are accepted.",
                    "error",
                )
            # If file.filename is empty, it means no file was selected (already handled), skip.

        # Flash messages based on results
        if processed_count > 0:
            flash(f"Successfully converted {processed_count} file(s).", "success")
        if failed_files:
            flash(
                f"Failed to convert {len(failed_files)} file(s). See details below.",
                "error",
            )
        elif (
            processed_count == 0
            and not failed_files
            and files
            and files[0].filename != ""
        ):
            # This case handles if only invalid file types were uploaded
            pass  # Error already flashed inside loop
        elif not files or files[0].filename == "":
            # No files selected case, already flashed.
            pass

        # Render template showing download links and failures
        return render_template(
            "index.html", pdf_files=pdf_files, failed_files=failed_files
        )

    # For GET request, just show the upload form
    return render_template("index.html", pdf_files=None, failed_files=None)


@app.route("/download/<filename>")
def download_file(filename):
    """Provides the converted PDF file for download."""
    # Sanitize filename again just to be safe, although it should be safe already
    safe_filename = secure_filename(filename)
    if not safe_filename.lower().endswith(".pdf"):
        flash("Invalid file requested for download.", "error")
        return redirect(url_for("upload_and_convert"))

    logging.info(f"Download requested for: {safe_filename}")
    try:
        return send_from_directory(
            app.config["CONVERTED_FOLDER"],
            safe_filename,
            as_attachment=True,  # Force download dialog
        )
    except FileNotFoundError:
        logging.error(f"Download failed: File not found {safe_filename}")
        flash(f"Error: File '{safe_filename}' not found on server.", "error")
        return redirect(url_for("upload_and_convert"))
    except Exception as e:
        logging.error(f"Error during download of {safe_filename}: {e}")
        flash("An error occurred while trying to download the file.", "error")
        return redirect(url_for("upload_and_convert"))


# --- Main Execution ---
if __name__ == "__main__":
    create_folders()  # Ensure folders exist before starting
    # Use host='0.0.0.0' to make it accessible on your network
    # Use debug=True only for development, not production
    app.run(debug=True, host="127.0.0.1", port=8080)
    # For production, use a proper WSGI server like Gunicorn or Waitress
    # Example: gunicorn -w 4 app:app
