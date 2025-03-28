# Keynote2PDF Converter

A macOS application that converts Keynote files to PDF format with a modern web interface and menu bar integration.

## Features

- 🔄 Convert Keynote files to PDF with drag-and-drop
- 📎 Merge multiple PDFs into a single file
- 🗑️ Easy file management with select all and delete options
- 🔍 File compression for optimized PDF size
- 📱 Modern, responsive web interface
- 🖥️ Menu bar integration for quick access
- 🚀 Automatic startup on login
- 📊 Service status monitoring

## Requirements

- macOS 10.15 or later
- Keynote application installed
- Internet browser (Safari, Chrome, Firefox, etc.)

## Installation

### Easy Install (Recommended)
1. Download `Keynote2PDF-Installer.dmg`
2. Double-click the DMG file
3. Drag `Keynote2PDF.app` to your Applications folder
4. Double-click `Keynote2PDF.app` to start
5. Click "Open" if prompted about security
6. Look for the 📄 icon in your menu bar

### Manual Install (From Source)
```bash
# Clone the repository
git clone https://github.com/ericxyz86/keynote2pdf.git
cd keynote2pdf

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the application
./run.sh
```

## Usage

### Web Interface
1. Open your browser to `http://127.0.0.1:8080`
2. Drag and drop Keynote files or click "Choose Files"
3. Wait for conversion to complete
4. Download converted PDFs
5. Optionally merge selected PDFs

### Menu Bar Controls
- Click the 📄 icon in the menu bar to:
  - Open the web interface
  - Check service status
  - Start/Stop the service
  - Uninstall the application

### Keyboard Shortcuts
- `Command + Space`: Search for "Keynote2PDF"
- `Command + C`: Copy files for drag and drop
- `Command + V`: Paste files for conversion

## File Management

### Converting Files
1. Select or drag Keynote files
2. Wait for conversion animation
3. Download converted PDFs

### Merging PDFs
1. Select PDFs using checkboxes
2. Click "Merge Selected"
3. Download merged file

### Deleting Files
1. Use "Select All" or individual checkboxes
2. Click "Delete Selected"
3. Confirm deletion

## Troubleshooting

### Common Issues
1. **App won't open**: Check System Preferences > Security & Privacy
2. **Service not running**: Use menu bar to Start Service
3. **Conversion fails**: Ensure Keynote is installed and file is not corrupted

### Logs
- Check `~/.keynote2pdf/output.log` for general logs
- Check `~/.keynote2pdf/error.log` for error details

## Uninstalling

### Option 1: Menu Bar
1. Click the 📄 icon
2. Select "Uninstall"
3. Confirm removal

### Option 2: Manual
```bash
launchctl unload ~/Library/LaunchAgents/com.keynote2pdf.converter.plist
rm -rf ~/.keynote2pdf
rm ~/Library/LaunchAgents/com.keynote2pdf.converter.plist
```

## Development

### Building from Source
```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run for development
FLASK_DEBUG=1 python app.py

# Build installer
./build_installer.sh
```

### Project Structure
```
keynote2pdf/
├── app.py              # Main Flask application
├── menubar.py          # Menu bar integration
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
└── run.sh             # Production startup script
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask for the web framework
- PyPDF2 for PDF operations
- Rumps for menu bar integration 