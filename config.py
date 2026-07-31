import os

# Database configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "requisition.db")

# Application configuration
APP_NAME = "Construction Requisition System"
APP_VERSION = "1.0"
COMPANY_NAME = "HAJI ABDUL RAHEEM CONSTRUCTION COMPANY"

# Role definitions
ROLES = {
    "ADMIN": "Administrator",
    "CEO": "Chief Executive Officer",
    "VERIFIER": "Verifier",
    "DATA_ENTRY": "Data Entry"
}

# Requisition statuses
REQUISITION_STATUSES = [
    "DRAFT",
    "SUBMITTED",
    "UNDER_VERIFICATION",
    "VERIFIED",
    "APPROVED",
    "REJECTED",
    "RETURNED",
    "ARCHIVED"
]

# Category names
DEFAULT_CATEGORIES = [
    "Site Work",
    "Materials",
    "Miscellaneous & Administration"
]

# File paths
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Ensure directories exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Banner and Icon configuration
BANNER_PATH = os.path.join(STATIC_DIR, "banner.png")
ICON_PATH = os.path.join(STATIC_DIR, "icon.png")
IMAGE_PATH = os.path.join(STATIC_DIR, "image.png")

def has_banner():
    return os.path.exists(BANNER_PATH)

def has_icon():
    return os.path.exists(ICON_PATH)

def has_image():
    return os.path.exists(IMAGE_PATH)