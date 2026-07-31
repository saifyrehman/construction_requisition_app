#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p static
mkdir -p temp

echo "✅ Setup completed successfully!"
