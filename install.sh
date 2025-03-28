#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Setting up Keynote2PDF Converter..."

# Make run.sh executable if it isn't already
chmod +x "$DIR/run.sh"

# Create LaunchAgents directory if it doesn't exist
mkdir -p ~/Library/LaunchAgents

# Copy the plist file to LaunchAgents
cp "$DIR/com.keynote2pdf.converter.plist" ~/Library/LaunchAgents/

# Load the Launch Agent
launchctl unload ~/Library/LaunchAgents/com.keynote2pdf.converter.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.keynote2pdf.converter.plist

echo "Installation complete! The Keynote2PDF converter will now:"
echo "1. Start automatically when you log in"
echo "2. Run at http://127.0.0.1:8080"
echo "3. Log output to output.log and errors to error.log"
echo ""
echo "To start the service now: launchctl start com.keynote2pdf.converter"
echo "To stop the service: launchctl stop com.keynote2pdf.converter"
echo "To remove the service: ./uninstall.sh" 