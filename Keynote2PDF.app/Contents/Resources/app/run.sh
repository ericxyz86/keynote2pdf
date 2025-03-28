#!/bin/bash

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install or upgrade dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads converted

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=production
export FLASK_DEBUG=0
export FLASK_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Start gunicorn
echo "Starting Keynote2PDF converter..."
exec gunicorn -w 4 -b 127.0.0.1:8080 --timeout 120 app:app 