import os
import asyncio
import pandas as pd
import argparse
import logging

from aiohttp_retry import ExponentialRetry, RetryClient
from aiohttp import ClientError, ClientOSError
from src.selenium import get_authorized_session, install_geckodriver
from src.urls import create_aiohttp_session
from src.subcategories_parsing import get_subcategories_URLs
from src.item_parsing import gather_data
from src.google_sheets import get_sheet_as_dataframe_or_load_from_storage, get_category_ids
from src.settings import RESULTS_DIR, PREFIXES_SHEET, DELIVERY_SHEET, LOGS_DIR
from datetime import datetime


RETRY_OPTIONS = ExponentialRetry(
    attempts=5,
    statuses=(500, 502, 503, 504),
    exceptions=(ClientError, ClientOSError)
)

error_handler = logging.FileHandler(os.path.join(LOGS_DIR, 'error.log'))
error_handler.setLevel(logging.ERROR)

warning_handler = logging.FileHandler(os.path.join(LOGS_DIR, 'logs.log'))
warning_handler.setLevel(logging.WARNING)

logging.basicConfig(handlers=[error_handler, warning_handler], format='%(asctime)s - %(name)s - %(levelname)s : %(message)s')
logger = logging.getLogger(__file__)

def get_mapping(sheetname: str):
    df = get_sheet_as_dataframe_or_load_from_storage(sheetname)
    return dict(zip(df[df.columns[0]].astype(str), df[df.columns[1]].astype(str)))


def remove_prefix(row, prefixes: dict):
    if row['item_brand'] in prefixes:
        prefix = prefixes[row['item_brand']]
        return row['item_number'].replace(prefix, '')
    else:
        return row['item_number']


def remove_prefixes_from_dataframe(df: pd.DataFrame):
    prefixes = get_mapping(PREFIXES_SHEET)
    df['item_number'] = df.apply(lambda x: remove_prefix(x, prefixes), axis=1)
    return df


def adjust_delivery_time(date: str, dates_mapping: dict):
    if date in dates_mapping:
        return dates_mapping[date]
    return date


def adjust_delivery_time_in_dataframe(df: pd.DataFrame):
    dates_mapping = get_mapping(DELIVERY_SHEET)
    df['delivery_time'] = df['delivery_time'].apply(lambda x: adjust_delivery_time(x, dates_mapping))
    return df


def write_result_to_file(df: pd.DataFrame):
    directory = RESULTS_DIR
    filename = f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
    filepath = os.path.join(directory, filename)
    pd.DataFrame(df).to_csv(filepath, index=False)

    return filepath


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', type=str, metavar='', default=os.environ.get('USERNAME'),
                        help='Username for website authorization. \
                            If not specified authorization will run in manual mode. \
                            Also can be specified by setting `USERNAME` env variable')

    parser.add_argument('-p', '--password', type=str, metavar='', default=os.environ.get('PASSWORD'),
                        help='Password for website authorization. \
                            If not specified authorization will run in manual mode. \
                            Also can be specified by setting `PASSOWRD` env variable')

    return parser.parse_args()


async def main():
    args = parse_args()

    install_geckodriver()
    print('[+] Authorizing...')
    session = get_authorized_session(args.username, args.password)
    session = create_aiohttp_session(session)
    async with RetryClient(session, retry_options=RETRY_OPTIONS) as retry_client:
        category_ids = get_category_ids()
        print(f'[+] Got {len(category_ids)} categories from source table')

        subcategories_urls = await get_subcategories_URLs(retry_client, category_ids)
        print(
            f'[+] Successfully got {len(subcategories_urls)} subcategoreis URL\'s')

        print('[+] Staring parsing')
        data = await gather_data(subcategories_urls, retry_client)

        df = pd.DataFrame(data)
        print('[+] Removing brands prefixes')
        df = remove_prefixes_from_dataframe(df)

        print('[+] Making delivery time adjustments')
        df = adjust_delivery_time_in_dataframe(df)

        print('[+] Writing data to csv')
        result_path = write_result_to_file(df)

        print(f'[+] Parsing complete! \n Result: {result_path}')


if __name__ == '__main__':
    try:
        print(f'Logs are storing in: {LOGS_DIR}')
        print(f'Results are storing in {RESULTS_DIR}')
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except:
        logger.exception('Got exception on main handler')
        print(f'[!] An error has accured. You can see traceback in {os.path.join(LOGS_DIR, "error.log")}')
        raise
    finally:
        input('Press enter to leave')