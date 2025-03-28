# Keynote to PDF Converter

A web-based tool that converts Apple Keynote (.key) files to PDF format. Built with Flask and designed to run on macOS.

## Requirements

- macOS with Apple Keynote installed
- Python 3.x
- Flask

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/keynote2pdf.git
cd keynote2pdf
```

2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://127.0.0.1:8080
```

3. Upload your Keynote files either by:
   - Dragging and dropping .key files into the upload area
   - Clicking "Choose Files" to select files from your computer

4. The converted PDF files will be available for download once the conversion is complete.

## Features

- Modern, clean web interface
- Drag-and-drop file upload
- Multiple file upload support
- Automatic conversion to PDF
- Error handling and status feedback
- Responsive design

## Project Structure

```
├── app.py             # Main Flask application
├── templates/
│   └── index.html     # HTML template for the web interface
├── uploads/           # Directory to store uploaded .key files
├── converted/         # Directory to store generated .pdf files
└── requirements.txt   # Python dependencies
```

## Notes

- This service must run on macOS as it requires Apple Keynote for the conversion process.
- The application uses AppleScript to interact with Keynote for the conversion process.
- Files are temporarily stored in the uploads/ directory and converted files in the converted/ directory.

## License

MIT License 