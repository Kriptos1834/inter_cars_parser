import os

from src.utils import get_or_create_dir

DEBUG = False

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
LOGS_DIR = get_or_create_dir(os.path.join(BASE_DIR, 'logs'))
STORAGE_DIR = get_or_create_dir(os.path.join(BASE_DIR, 'storage'))
RESULTS_DIR = get_or_create_dir(os.path.join(BASE_DIR, 'results'))

PREFIXES_SHEET = 'Prefixes'
DELIVERY_SHEET = 'Delivery'
CATEGORIES_SHEET = 'Categories'


print(BASE_DIR)