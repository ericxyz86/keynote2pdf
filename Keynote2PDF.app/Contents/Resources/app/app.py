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
    jsonify,
)
from werkzeug.utils import secure_filename
import logging
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from datetime import datetime

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
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_very_secret_key_here")

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "app.log")),
        logging.StreamHandler(),
    ],
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
    conversion_complete = False  # Flag to indicate if conversion just completed

    # Get list of existing PDF files
    if os.path.exists(app.config["CONVERTED_FOLDER"]):
        pdf_files = [
            f for f in os.listdir(app.config["CONVERTED_FOLDER"]) if f.endswith(".pdf")
        ]

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

                # Check if a PDF with this unique_id already exists
                pdf_filename = (
                    f"{os.path.splitext(original_filename)[0]}_{unique_id}.pdf"
                )
                pdf_filepath = os.path.join(
                    app.config["CONVERTED_FOLDER"], pdf_filename
                )

                if pdf_filename in pdf_files:
                    # Skip processing if file already exists
                    continue

                try:
                    file.save(key_filepath)
                    logging.info(f"Saved uploaded file: {key_filepath}")

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

        # Flash messages based on results
        if processed_count > 0:
            flash(f"Successfully converted {processed_count} file(s).", "success")
            conversion_complete = True
        if failed_files:
            flash(
                f"Failed to convert {len(failed_files)} file(s). See details below.",
                "error",
            )
            conversion_complete = True

        # Render template showing download links and failures
        return render_template(
            "index.html",
            pdf_files=pdf_files,
            failed_files=failed_files,
            conversion_complete=conversion_complete,
        )

    # For GET request, just show the upload form with existing files
    return render_template(
        "index.html", pdf_files=pdf_files, failed_files=None, conversion_complete=False
    )


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


@app.route("/merge", methods=["POST"])
def merge_pdfs():
    try:
        # Get list of PDF files to merge from the request
        files_to_merge = request.json.get("files", [])
        if not files_to_merge:
            return jsonify({"error": "No files selected for merging"}), 400

        # Create a timestamp for the merged file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        merged_filename = f"merged_{timestamp}.pdf"
        merged_path = os.path.join(app.config["CONVERTED_FOLDER"], merged_filename)

        # Create PDF writer instance for the final output
        writer = PdfWriter()

        # Process each PDF file
        for filename in files_to_merge:
            file_path = os.path.join(app.config["CONVERTED_FOLDER"], filename)
            if not os.path.exists(file_path):
                return jsonify({"error": f"File not found: {filename}"}), 404

            # Read and process each PDF
            reader = PdfReader(file_path)
            for page in reader.pages:
                # Compress content streams
                page.compress_content_streams()

                # Get the page's resources dictionary
                if "/Resources" in page:
                    resources = page["/Resources"]

                    # Compress images if they exist
                    if "/XObject" in resources:
                        xObject = resources["/XObject"]
                        for obj in xObject:
                            if xObject[obj]["/Subtype"] == "/Image":
                                # Reduce image quality if it's a JPEG
                                if (
                                    "/Filter" in xObject[obj]
                                    and xObject[obj]["/Filter"] == "/DCTDecode"
                                ):
                                    xObject[obj]["/Quality"] = (
                                        60  # Lower quality for JPEG images
                                    )

                # Add the compressed page
                writer.add_page(page)

        # Write the final compressed PDF
        with open(merged_path, "wb") as output_file:
            writer.write(output_file)

        # Return the filename of the merged PDF
        return jsonify({"success": True, "merged_file": merged_filename})

    except Exception as e:
        logging.error(f"Error merging PDFs: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/delete", methods=["POST"])
def delete_files():
    try:
        # Get list of files to delete from the request
        files_to_delete = request.json.get("files", [])
        if not files_to_delete:
            return jsonify({"error": "No files selected for deletion"}), 400

        # Delete each file
        for filename in files_to_delete:
            file_path = os.path.join(
                app.config["CONVERTED_FOLDER"], secure_filename(filename)
            )
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Deleted file: {filename}")
            else:
                logging.warning(f"File not found for deletion: {filename}")

        return jsonify({"success": True})

    except Exception as e:
        logging.error(f"Error deleting files: {str(e)}")
        return jsonify({"error": str(e)}), 500


# --- Main Execution ---
if __name__ == "__main__":
    create_folders()  # Ensure folders exist before starting

    # Get configuration from environment variables with defaults
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")

    # In production, always use 127.0.0.1 as host for security
    if not debug:
        host = "127.0.0.1"

    app.run(debug=debug, host=host, port=port, threaded=True)
    # Note: For production, use: gunicorn -w 4 -b 127.0.0.1:8080 app:app
