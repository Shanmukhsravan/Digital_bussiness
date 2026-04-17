import os

# Gunicorn configuration for Render
# Force binding to 0.0.0.0 and the port specified by Render
port = os.environ.get("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Performance
workers = 1 # Keep it simple for now
threads = 4
timeout = 120
