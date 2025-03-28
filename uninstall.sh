#!/bin/bash

echo "Uninstalling Keynote2PDF Converter service..."

# Unload the Launch Agent
launchctl unload ~/Library/LaunchAgents/com.keynote2pdf.converter.plist 2>/dev/null || true

# Remove the plist file
rm -f ~/Library/LaunchAgents/com.keynote2pdf.converter.plist

echo "Uninstallation complete! The service has been removed."
echo "Note: The application files are still in the directory."
echo "You can start the application manually with ./run.sh" 