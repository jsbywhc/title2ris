"""
Configuration file for title2ris
"""

# API Configuration
CROSSREF_API_URL = "https://api.crossref.org/works"
USER_AGENT = "Title2RIS/1.0 (mailto:wanghc2023@nanoctr.cn)"
API_TIMEOUT = 20  # seconds
MAX_RETRIES = 3
WAIT_TIME_BETWEEN_REQUESTS = 3  # seconds
BATCH_SIZE = 3  # Number of entries to process before saving

# Special Titles to Skip
SKIP_TITLES = [
    'Frontispiece',
    'Frontispiz',
    'SI',
    'Supplemental Information',
    'Supplementary Information',
    'Supporting Information',
    'Cover Picture',
    'Cover Image',
    'Graphical Abstract',
    'Table of Contents'
]

# File Configuration
DEFAULT_OUTPUT_FILE = "output.ris"
ENCODING = 'utf-8'

# Logging Configuration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_LEVEL = 'INFO'
LOG_FILE = 'title2ris.log' 