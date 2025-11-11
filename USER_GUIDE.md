# Keynote2PDF User Guide

## How to Use the App

Keynote2PDF is a **web-based application** that runs in the background on your Mac. Unlike traditional Mac apps with windows, this app is accessed through your web browser.

## ⚠️ First Time Installation - macOS Security

When you first try to open Keynote2PDF, macOS will block it with a security warning because the app is not signed with an Apple Developer ID certificate. **This is normal and expected.**

### Method 1: Open via System Settings (Recommended)

1. **Download and mount the DMG file**
2. **Drag Keynote2PDF.app to Applications folder**
3. **Try to open the app** - You'll see a warning: *"Keynote2PDF.app cannot be opened because it is from an unidentified developer"*
4. Click **"OK"** to dismiss the warning
5. Open **System Settings** (or System Preferences on older macOS)
6. Go to **Privacy & Security**
7. Scroll down to the **Security** section
8. You'll see a message: *"Keynote2PDF.app was blocked from use because it is not from an identified developer"*
9. Click **"Open Anyway"**
10. Confirm by clicking **"Open"** in the dialog that appears
11. The app will now launch and run in the background

### Method 2: Right-Click to Open (Alternative)

1. **Download and mount the DMG file**
2. **Drag Keynote2PDF.app to Applications folder**
3. Open **Finder** and navigate to your **Applications** folder
4. **Right-click** (or Control+click) on **Keynote2PDF.app**
5. Select **"Open"** from the context menu
6. Click **"Open"** in the dialog that appears

### Method 3: Command Line (Advanced Users)

If the above methods don't work, you can remove the quarantine flag:
```bash
xattr -d com.apple.quarantine /Applications/Keynote2PDF.app
```

Then open the app normally.

### Why Does This Happen?

- The app is not signed with an Apple Developer ID certificate ($99/year)
- This is a free, open-source tool, so it's distributed unsigned
- macOS Gatekeeper blocks unsigned apps by default to protect users
- **The app is safe** - you can review the source code on GitHub: https://github.com/ericxyz86/keynote2pdf

### After First Launch

Once you've opened the app using one of the methods above, macOS will remember your choice and won't block it again.

---

## Quick Start

### 1. Launch the App
- After installation, the app starts automatically in the background
- You'll see a small icon in your macOS menu bar (top-right corner)
- The app also appears in your Dock

### 2. Access the Web Interface
Open your web browser and navigate to:
```
http://127.0.0.1:8080
```

**Tip**: Bookmark this URL for quick access!

### 3. Use the App
Once the web interface opens, you can:
- **Upload Keynote files** (.key) for conversion to PDF
- **Download converted PDFs**
- **Merge multiple PDFs** into one file
- **Delete files** when done

## Understanding How It Works

### Menu Bar Icon
- The icon in your menu bar indicates the app is running
- The app runs silently in the background
- It does NOT open a traditional window

### Background Service
- The app automatically starts when you log in to macOS
- It runs a local web server on port 8080
- Only accessible from your Mac (localhost) - very secure!

### Web Interface
- All interactions happen through your web browser
- Works with any modern browser (Safari, Chrome, Firefox, etc.)
- Familiar web-based UI for uploading and managing files

## Features

### Convert Keynote to PDF
1. Click "Choose Files" or drag & drop .key files
2. Files are automatically converted
3. Download the resulting PDFs

### Merge PDFs
1. Upload multiple PDFs
2. Click "Merge All PDFs"
3. Download the combined file

### Automatic Compression
- Images are automatically optimized during conversion
- Reduces file sizes while maintaining quality
- See compression statistics in the logs

## Troubleshooting

### "Cannot Connect" Error
If you can't access http://127.0.0.1:8080:
1. Check if the app is running: look for the menu bar icon
2. Restart the app:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.keynote2pdf.converter.plist
   launchctl load ~/Library/LaunchAgents/com.keynote2pdf.converter.plist
   ```

### App Not in Menu Bar
1. Check if it's running:
   ```bash
   ps aux | grep menubar.py
   ```
2. If not running, restart:
   ```bash
   cd /Applications/Keynote2PDF.app/Contents/MacOS
   ./run.sh
   ```

### View Logs
Check application logs for errors:
```bash
tail -f /Users/$USER/Desktop/keynote2pdf/app.log
```

## Uninstalling

To completely remove Keynote2PDF:
1. Run the uninstaller:
   ```bash
   /Applications/Keynote2PDF.app/Contents/MacOS/uninstall.sh
   ```
2. Or manually:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.keynote2pdf.converter.plist
   rm ~/Library/LaunchAgents/com.keynote2pdf.converter.plist
   rm -rf /Applications/Keynote2PDF.app
   ```

## Privacy & Security

- ✅ Runs entirely on your Mac (no data sent to the cloud)
- ✅ Only accessible from localhost (127.0.0.1)
- ✅ No external network connections required
- ✅ Your files never leave your computer

## System Requirements

- macOS 10.14 or later
- Apple Keynote installed
- Python 3.6+ (included with macOS)
- Modern web browser

## Support

For issues or questions:
- Check logs: `/Users/$USER/Desktop/keynote2pdf/app.log`
- GitHub: https://github.com/ericxyz86/keynote2pdf
- Report issues: https://github.com/ericxyz86/keynote2pdf/issues

---

**Remember**: To use the app, simply open http://127.0.0.1:8080 in your browser!
