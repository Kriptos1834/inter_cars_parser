import gspread
import gspread_dataframe as gd
import json
import pandas as pd
import os
import logging

from src.settings import CATEGORIES_SHEET, STORAGE_DIR

WORKSPACE_URL = os.environ.get('GOOGLE_SHEETS_URL', 'https://docs.google.com/spreadsheets/d/1ore1NTW2lnx8Jk8PpySAL673uWAbs2ljR56O_UQOTkI')
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'steady-ether-286511-f1c23975d185.json')

logger = logging.getLogger(__file__)


def get_workspace():
    credentials = json.loads(open(CREDENTIALS_FILE, 'r').read())
    gc = gspread.service_account_from_dict(credentials)
    workspace = gc.open_by_url(WORKSPACE_URL)

    return workspace


def get_sheet_as_datafame(sheet: str, dropna: bool = True) -> pd.DataFrame:
    worksheet = get_workspace().worksheet(sheet)
    records = gd.get_as_dataframe(worksheet, evaluate_formulas=True)
    if dropna:
        records = records.dropna(how='all').dropna(axis=1, how='all')
    return records

def get_sheet_as_dataframe_or_load_from_storage(sheet: str):
    directory = STORAGE_DIR
    stored_table_path = os.path.join(directory, f'{sheet}.csv')
    try:
        df = get_sheet_as_datafame(sheet)
        df.to_csv(stored_table_path, index=False)
    except Exception:
        logger.warning(f'Unable to access {sheet} sheet. Loading from storage')
        df = pd.read_csv(stored_table_path)

    return df

def get_category_ids():
    df = get_sheet_as_dataframe_or_load_from_storage(CATEGORIES_SHEET)
    return df['category_id'].astype(int).astype(str).to_list()