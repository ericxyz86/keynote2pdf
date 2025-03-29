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
import fitz  # PyMuPDF
import io
from PIL import Image
import shutil
from datetime import datetime

Image.MAX_IMAGE_PIXELS = None  # Disable decompression bomb check

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


def convert_to_pdfa(input_pdf, output_pdf):
    """
    Convert a PDF to PDF/A format using Ghostscript.
    Returns True on success, False on failure.
    """
    try:
        # Ghostscript command to convert to PDF/A
        args = [
            "gs",
            "-dPDFA=1",
            "-dBATCH",
            "-dNOPAUSE",
            "-sColorConversionStrategy=UseDeviceIndependentColor",
            "-sDEVICE=pdfwrite",
            "-dPDFACompatibilityPolicy=1",
            "-sOutputFile={}".format(output_pdf),
            input_pdf,
        ]

        process = subprocess.run(args, capture_output=True, text=True, check=False)

        if process.returncode == 0 and os.path.exists(output_pdf):
            logging.info("Successfully converted to PDF/A: {}".format(output_pdf))
            return True, "Success"
        else:
            error_msg = (
                process.stderr.strip() or "Unknown error during PDF/A conversion"
            )
            logging.error("PDF/A conversion failed: {}".format(error_msg))
            return False, "PDF/A conversion failed: {}".format(error_msg)

    except Exception as e:
        logging.error("Error during PDF/A conversion: {}".format(e))
        return False, "PDF/A conversion error: {}".format(e)


def convert_key_to_pdf(key_filepath, pdf_filepath):
    """
    Uses AppleScript to ask Keynote to export a .key file to .pdf,
    then applies image compression.
    Returns True on success, False on failure.
    """
    logging.info(">>> convert_key_to_pdf function STARTED <<<")
    logging.info(f"Attempting conversion: {key_filepath} -> {pdf_filepath}")
    abs_key_path = os.path.abspath(key_filepath)
    # Use a temporary path in the SAME directory as the final file to avoid cross-device move issues
    temp_pdf_path = os.path.join(
        os.path.dirname(pdf_filepath),
        f"temp_{uuid.uuid4().hex[:8]}_{os.path.basename(pdf_filepath)}",
    )
    abs_pdf_path = os.path.abspath(pdf_filepath)

    if not os.path.exists(abs_key_path):
        logging.error(f"Input Keynote file not found: {abs_key_path}")
        return False, "Input file not found"

    keynote_success = False
    compression_success = False
    final_message = "Unknown error"
    temp_size = 0

    try:
        # 1. Convert to regular PDF using Keynote
        logging.info(f"Starting Keynote export: {abs_key_path} -> {temp_pdf_path}")
        keynote_success, message = keynote_to_pdf(abs_key_path, temp_pdf_path)
        if not keynote_success:
            final_message = message
            return False, final_message  # Exit early if Keynote fails

        if not os.path.exists(temp_pdf_path):
            logging.error(
                f"Keynote export seemed successful but temp PDF not found: {temp_pdf_path}"
            )
            return False, "Intermediate PDF file not created by Keynote"

        # Log the size of the temporary PDF before compression
        try:
            temp_size = os.path.getsize(temp_pdf_path)
            logging.info(
                f"Temporary PDF size before compression: {temp_size / 1024:.2f} KB"
            )
        except OSError as e:
            logging.warning(f"Could not get size of temp PDF {temp_pdf_path}: {e}")
            # Continue anyway, compression might still work

        # 2. Apply image compression to the temporary PDF
        logging.info(f"Starting image compression: {temp_pdf_path} -> {abs_pdf_path}")
        # Use effective image compression
        compression_success, message = compress_pdf_images(
            temp_pdf_path,
            abs_pdf_path,
            dpi=150,
            quality=75,  # Increased default quality slightly
        )
        final_message = message  # Store message from compress_pdf_images

        if not compression_success:
            logging.warning(
                f"Image compression failed: {message}. Falling back to uncompressed PDF."
            )
            # If compression fails, copy the uncompressed temp PDF to the final location
            try:
                shutil.copy2(temp_pdf_path, abs_pdf_path)
                logging.info(
                    f"Copied uncompressed temporary PDF to final path: {abs_pdf_path}"
                )
                # Treat fallback as overall success for this function's purpose
                compression_success = True
                final_message = (
                    "Conversion succeeded (compression failed, used uncompressed)"
                )
            except Exception as copy_e:
                logging.error(
                    f"Failed to copy uncompressed PDF {temp_pdf_path} to {abs_pdf_path}: {copy_e}"
                )
                # Fallback failed, so overall conversion failed
                compression_success = False
                final_message = f"Compression failed ({message}) and fallback copy also failed ({copy_e})"

        # Log the final size if compression step was reached (even if fallback occurred)
        if os.path.exists(abs_pdf_path):
            try:
                final_size = os.path.getsize(abs_pdf_path)
                logging.info(f"Final PDF size: {final_size / 1024:.2f} KB")
                if temp_size > 0:
                    logging.info(
                        f"Effective compression ratio: {(1 - final_size / temp_size) * 100:.1f}%"
                    )
            except OSError as e:
                logging.warning(f"Could not get size of final PDF {abs_pdf_path}: {e}")
        else:
            logging.error(
                f"Final PDF does not exist at {abs_pdf_path} after processing."
            )
            compression_success = False  # Mark as failure if final file doesn't exist
            if final_message == "Success":  # Avoid overwriting specific error messages
                final_message = "Final PDF file is missing after processing"

        return compression_success, final_message

    except Exception as e:
        logging.error(
            f"Unexpected error during convert_key_to_pdf for {key_filepath}: {e}",
            exc_info=True,
        )
        return False, f"Conversion failed due to unexpected error: {e}"
    finally:
        # Clean up temporary PDF regardless of success/failure
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                logging.info(f"Removed temporary PDF: {temp_pdf_path}")
            except OSError as e:
                logging.warning(f"Could not remove temporary PDF {temp_pdf_path}: {e}")


def keynote_to_pdf(key_filepath, pdf_filepath):
    """
    Uses AppleScript to ask Keynote to export a .key file to .pdf.
    Returns True on success, False on failure.
    """
    # Construct the AppleScript command with proper escaping
    applescript = """
    tell application "Keynote"
        set keyFile to (POSIX file "{0}") as alias
        set pdfFile to "{1}"
        
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
    """.format(key_filepath, pdf_filepath)

    try:
        # Execute the AppleScript using osascript
        process = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

        # Check output and return code
        if process.returncode == 0 and "success" in process.stdout.strip().lower():
            if os.path.exists(pdf_filepath):
                logging.info("Successfully converted to PDF: {}".format(pdf_filepath))
                return True, "Success"
            else:
                logging.error("PDF not created despite successful script execution")
                return False, "PDF not created despite successful script execution"
        else:
            error_message = process.stderr.strip() or process.stdout.strip()
            if not error_message:
                error_message = "osascript exited with code {}".format(
                    process.returncode
                )
            logging.error("AppleScript execution failed: {}".format(error_message))
            return False, "AppleScript Error: {}".format(error_message)

    except subprocess.TimeoutExpired:
        logging.error("Conversion timed out")
        return False, "Conversion process timed out"
    except Exception as e:
        logging.error("Failed to run conversion: {}".format(e))
        return False, "Conversion failed: {}".format(e)


def compress_pdf(input_path, output_path, dpi=150, quality=60):
    """
    Compresses a PDF using PyMuPDF's built-in compression.
    Returns True on success, False on failure.
    """
    if not os.path.exists(input_path):
        logging.error("Input file not found at '{}'".format(input_path))
        return False, "Input file not found"

    try:
        # Open the PDF with PyMuPDF
        doc = fitz.open(input_path)

        # Process each page
        for page in doc:
            # Clean contents
            page.clean_contents()
            # Set DPI limits for images
            page.set_mediabox(page.mediabox)  # Optimize page size

        # Create a temporary file if saving to the same location
        temp_path = output_path
        if input_path == output_path:
            temp_path = output_path + ".temp"

        # Save with maximum compression
        doc.save(
            temp_path,
            garbage=4,  # Maximum garbage collection
            deflate=True,  # Compress streams
            deflate_images=True,  # Compress images
            clean=True,  # Remove unused elements
        )

        doc.close()

        # If using temp file, replace the original
        if temp_path != output_path:
            os.replace(temp_path, output_path)

        return True, "Success"

    except Exception as e:
        logging.error("PDF compression failed: {}".format(e))
        # Clean up temp file if it exists
        if (
            "temp_path" in locals()
            and os.path.exists(temp_path)
            and temp_path != output_path
        ):
            try:
                os.remove(temp_path)
            except:
                pass
        return False, "Compression failed: {}".format(e)
    finally:
        try:
            doc.close()
        except:
            pass


def compress_pdf_images(input_path, output_path, dpi=150, quality=75):
    """
    Compresses a PDF by finding embedded raster images, downsampling them
    (relative to 300 DPI reference), and re-compressing as JPEG.
    Preserves text and vector graphics.
    Returns (success, message) tuple.
    """
    logging.info(
        f"--- compress_pdf_images function entered for input: {input_path} ---"
    )
    if not os.path.exists(input_path):
        logging.error(f"Compression Error: Input file not found at '{input_path}'")
        return False, "Input file not found"

    try:
        initial_size = os.path.getsize(input_path)
        logging.info(
            f"Initial PDF size for image compression: {initial_size / 1024:.2f} KB"
        )

        # Use 'with' statement for reliable closing
        with fitz.open(input_path) as doc:
            image_count = 0
            processed_count = 0
            skipped_count = 0
            made_change = False  # Flag to track if any image was actually replaced

            logging.info(f"Total pages in PDF: {len(doc)}")

            # --- Iterate through pages and images ---
            for page_num, page in enumerate(doc):
                images = page.get_images(full=True)
                page_image_count = len(images)
                image_count += page_image_count

                for img_index, img in enumerate(images):
                    xref = img[0]
                    try:
                        base = doc.extract_image(xref)
                        if not base or "image" not in base:
                            skipped_count += 1
                            continue

                        image_bytes = base["image"]
                        img_ext = base["ext"]

                        # Skip very small images (e.g., icons, lines)
                        if len(image_bytes) < 5 * 1024:  # Skip images under 5KB
                            skipped_count += 1
                            continue

                        pil_img = None  # Initialize
                        try:
                            pil_img = Image.open(io.BytesIO(image_bytes))
                        except Exception as pil_e:
                            logging.warning(
                                f"    Skipping: Pillow error opening image xref {xref} (ext: {img_ext}): {pil_e}"
                            )
                            skipped_count += 1
                            continue

                        # --- Calculate new size ---
                        scale = dpi / 300.0
                        new_width = max(1, int(pil_img.width * scale))  # Ensure > 0
                        new_height = max(1, int(pil_img.height * scale))  # Ensure > 0

                        # Skip if image is already smaller than target size
                        if new_width >= pil_img.width and new_height >= pil_img.height:
                            skipped_count += 1
                            continue

                        logging.info(
                            f"    Processing xref {xref}: ({pil_img.width}x{pil_img.height} {pil_img.mode}, {len(image_bytes) / 1024:.1f}KB) -> Target: ({new_width}x{new_height}, {dpi}dpi, Q{quality})"
                        )

                        # --- Downsample, convert color space ---
                        pil_img_processed = pil_img.resize(
                            (new_width, new_height), Image.Resampling.LANCZOS
                        )
                        if pil_img_processed.mode in ("RGBA", "LA", "P"):
                            pil_img_processed = pil_img_processed.convert("RGB")

                        # --- Re-compress to JPEG ---
                        img_bytes_io = io.BytesIO()
                        pil_img_processed.save(
                            img_bytes_io, format="JPEG", quality=quality, optimize=True
                        )
                        new_image_data = img_bytes_io.getvalue()

                        # Only replace if the new image is actually smaller
                        if len(new_image_data) < len(image_bytes):
                            # Use the correct method to replace the image
                            doc.delete_object(xref)  # Remove the old image
                            doc.insert_image(
                                page.rect, stream=new_image_data
                            )  # Insert the new one
                            logging.info(
                                f"    Replaced xref {xref} with compressed image ({len(new_image_data) / 1024:.1f}KB)"
                            )
                            processed_count += 1
                            made_change = True
                        else:
                            skipped_count += 1

                    except Exception as e:
                        logging.warning(
                            f"  - Error processing image xref {xref}: {e}",
                            exc_info=True,
                        )
                        skipped_count += 1
                    finally:
                        # Clean up PIL images if they were created
                        if "pil_img" in locals() and pil_img:
                            del pil_img
                        if "pil_img_processed" in locals() and pil_img_processed:
                            del pil_img_processed

            # --- Log summary and save ---
            logging.info(
                f"Image compression summary: Processed={processed_count}, Skipped={skipped_count}, Total Found={image_count}"
            )
            if image_count == 0:
                logging.warning(
                    f"No raster images found by get_images() in {input_path}. Only applying deflate/garbage collection."
                )
            elif not made_change:
                logging.info(
                    "No images were replaced (either skipped or new size wasn't smaller)."
                )

            # Save only if changes were made or if no images were found (to apply deflate)
            if made_change or image_count == 0:
                logging.info(
                    f"Saving {'modified ' if made_change else ''}PDF to '{output_path}' with deflate options..."
                )
                doc.save(
                    output_path,
                    garbage=4,
                    deflate=True,
                    deflate_images=True,
                    deflate_fonts=True,
                )
            else:
                # If no images were found worthy of replacement, just copy the original
                logging.info(
                    f"No effective image changes made. Copying original to output: {output_path}"
                )
                shutil.copy2(input_path, output_path)

        # Log final size and compression ratio
        final_size = os.path.getsize(output_path)
        logging.info(
            f"Final PDF size after image compression: {final_size / 1024:.2f} KB"
        )
        if initial_size > 0:
            ratio = (1 - final_size / initial_size) * 100
            logging.info(f"Image compression ratio: {ratio:.1f}%")
            if ratio < 0:
                logging.warning("File size increased after image compression attempt.")
        logging.info("Image compression processing finished.")
        return True, "Success"

    except Exception as e:
        logging.error(
            f"Error during PDF image compression for {input_path}: {e}", exc_info=True
        )
        return False, f"Image compression failed: {e}"


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
                    "{}_{}".format(os.path.splitext(original_filename)[0], unique_id)
                    + ".key"
                )
                key_filepath = os.path.join(app.config["UPLOAD_FOLDER"], temp_filename)

                # Check if a PDF with this unique_id already exists
                pdf_filename = (
                    "{}_{}".format(os.path.splitext(original_filename)[0], unique_id)
                    + ".pdf"
                )
                pdf_filepath = os.path.join(
                    app.config["CONVERTED_FOLDER"], pdf_filename
                )

                if pdf_filename in pdf_files:
                    # Skip processing if file already exists
                    continue

                try:
                    file.save(key_filepath)
                    logging.info("Saved uploaded file: {}".format(key_filepath))

                    # Perform conversion
                    success, message = convert_key_to_pdf(key_filepath, pdf_filepath)

                    if success:
                        pdf_files.append(pdf_filename)
                        processed_count += 1
                    else:
                        failed_files[original_filename] = message
                        logging.warning(
                            "Failed to convert {}: {}".format(
                                original_filename, message
                            )
                        )

                    # Clean up the uploaded .key file immediately after processing
                    try:
                        os.remove(key_filepath)
                        logging.info("Removed uploaded file: {}".format(key_filepath))
                    except OSError as e:
                        logging.error(
                            "Error removing uploaded file {}: {}".format(
                                key_filepath, e
                            )
                        )

                except Exception as e:
                    logging.error(
                        "Error processing file {}: {}".format(original_filename, e)
                    )
                    failed_files[original_filename] = (
                        "Server error during processing: {}".format(e)
                    )
                    # Attempt cleanup if file was saved
                    if os.path.exists(key_filepath):
                        try:
                            os.remove(key_filepath)
                        except OSError as remove_err:
                            logging.error(
                                "Error removing file {} after error: {}".format(
                                    key_filepath, remove_err
                                )
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

    logging.info("Download requested for: {}".format(safe_filename))
    try:
        return send_from_directory(
            app.config["CONVERTED_FOLDER"],
            safe_filename,
            as_attachment=True,  # Force download dialog
        )
    except FileNotFoundError:
        logging.error("Download failed: File not found {}".format(safe_filename))
        flash("Error: File '{}' not found on server.".format(safe_filename), "error")
        return redirect(url_for("upload_and_convert"))
    except Exception as e:
        logging.error("Error during download of {}: {}".format(safe_filename, e))
        flash("An error occurred while trying to download the file.", "error")
        return redirect(url_for("upload_and_convert"))


@app.route("/merge", methods=["POST"])
def merge_pdfs():
    """Merges selected PDFs using PyMuPDF and applies basic compression."""
    logging.info(">>> merge_pdfs function STARTED <<<")
    try:
        files_to_merge = request.json.get("files", [])
        if not files_to_merge:
            logging.warning("Merge attempt with no files selected.")
            return jsonify({"error": "No files selected for merging"}), 400

        logging.info(f"Attempting to merge {len(files_to_merge)} files.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        merged_filename = f"merged_{timestamp}.pdf"
        merged_path = os.path.join(app.config["CONVERTED_FOLDER"], merged_filename)

        total_input_size = 0
        input_paths = []  # Store full paths for merging
        for filename in files_to_merge:
            # Basic sanitization - secure_filename might be too restrictive if UUIDs are used
            safe_filename = secure_filename(filename)  # Keep basic check
            file_path = os.path.join(app.config["CONVERTED_FOLDER"], safe_filename)
            if os.path.exists(file_path):
                try:
                    total_input_size += os.path.getsize(file_path)
                    input_paths.append(file_path)
                except OSError as e:
                    logging.warning(
                        f"Could not get size of file for merging: {file_path}: {e}"
                    )
            else:
                logging.error(f"File not found during merge preparation: {file_path}")
                return jsonify({"error": f"File not found: {filename}"}), 404

        logging.info(
            f"Total size of input files for merge: {total_input_size / 1024:.2f} KB"
        )

        # Use PyMuPDF for merging
        # Create an empty output document
        with fitz.open() as merged_doc:
            for file_path in input_paths:
                try:
                    with fitz.open(file_path) as pdf_to_insert:
                        logging.info(
                            f"Inserting {len(pdf_to_insert)} pages from {os.path.basename(file_path)}"
                        )
                        merged_doc.insert_pdf(pdf_to_insert)
                except Exception as insert_e:
                    logging.error(
                        f"Error inserting PDF {file_path} during merge: {insert_e}",
                        exc_info=True,
                    )
                    # Decide whether to fail the whole merge or just skip this file
                    return jsonify(
                        {
                            "error": f"Error processing file {os.path.basename(file_path)} during merge."
                        }
                    ), 500

            # Save the merged document with PyMuPDF's compression
            logging.info(f"Saving merged PDF to {merged_path} with deflate options...")
            merged_doc.save(
                merged_path,
                garbage=4,  # Max garbage collection
                deflate=True,  # Deflate text/vector streams
                deflate_images=True,  # Deflate image streams (useful even for JPEG)
                clean=True,  # Clean content streams
            )

        # Check final size and report
        final_size = os.path.getsize(merged_path)
        logging.info(f"Final merged PDF size: {final_size / 1024:.2f} KB")
        if total_input_size > 0:
            overall_ratio = (1 - final_size / total_input_size) * 100
            logging.info(f"Overall merge compression ratio: {overall_ratio:.1f}%")

        return jsonify({"success": True, "merged_file": merged_filename})

    except Exception as e:
        logging.error(f"Error merging PDFs: {e}", exc_info=True)
        return jsonify({"error": f"Server error during merge: {e}"}), 500


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
