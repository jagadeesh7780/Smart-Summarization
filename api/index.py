import sys
import os

# Add the parent directory to path so app.py can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel expects a variable named 'app'
# The handler is the Flask app itself
