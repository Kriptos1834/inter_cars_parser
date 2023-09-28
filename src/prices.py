import aiohttp
import asyncio
import json
import time

from typing import Iterable, List
from bs4 import BeautifulSoup
from itertools import chain
from src.utils import divide_chunks, split_array_by_condition, fix_encoding
from src.progress import async_execute_tasks_with_progressbar
from src.models import ItemPrice
from src.settings import DEBUG


async def fetch_missing_prices_from_API(session: aiohttp.ClientSession, product_codes: Iterable[str], semaphore: asyncio.Semaphore) -> str:
    url = 'https://md.e-cat.intercars.eu/ru/api/product/price/missing?isError=false'
    payload = [{"productCode": code,
                "quantity": 1,
                "showTooltip": True,
                "showSingleProductAmount": True,
                "showPricingData": False,
                "coreType": None,
                "omnibusPriceTimestamp": None,
                } for code in product_codes]
    async with semaphore:
        async with session.post(url, json=payload, timeout=20) as response:
            return await response.text()


def get_price_from_soup(soup: BeautifulSoup) -> float:
    try:
        price_string = soup.select('.quantity.productpricetoggle__gross .quantity__amount')[-1].get_text(separator=u' ', strip=True)
        return float(fix_encoding(price_string).replace(' ', '').replace(',', '.'))
    except (IndexError, ValueError):
        return None


def parse_prices_from_response(response: str) -> str:
    data = []
    i = 0
    for item in json.loads(response)['prices']:
        i += 1
        soup = BeautifulSoup(item['productPriceHtmlCode'], 'lxml')
        data.append(ItemPrice(item['productCode'], get_price_from_soup(soup)))
    return data


async def get_prices(session: aiohttp.ClientSession, product_codes: Iterable[str], semaphore):
    response = await fetch_missing_prices_from_API(session, product_codes, semaphore)
    return parse_prices_from_response(response)


async def get_item_prices(session: aiohttp.ClientSession, product_codes: Iterable[str], semaphore) -> List[ItemPrice]:
    tasks = []
    for chunk in divide_chunks(product_codes, 200):
        tasks.append(get_prices(session, chunk, semaphore))
    results = await async_execute_tasks_with_progressbar(tasks, not DEBUG, desc='[+] Parsing item prices')

    return list(chain(*results))

async def get_item_prices_without_loss(session: aiohttp.ClientSession, product_codes: Iterable[str], semaphore: asyncio.Semaphore, retries: int = 3, timeout: int = 5):
    """Parse prices from api with minimum losses"""
    i = 0
    retry_timeout = timeout

    prices = await get_item_prices(session, product_codes, semaphore)
    print('- Searching for losses...')
    ok, losses = split_array_by_condition(lambda x: x.price == None, prices)
    while i < retries:
        # If api didn't return prices for any products
        if losses:
            print(f'- {len(losses)} losses found. Retrying...')
            # Retry get query and define missing prices if they are
            retry_prices = await get_item_prices(session, [i.product_code for i in losses], semaphore)
            print('- Searching for losses...')
            retry_ok, retry_losses = split_array_by_condition(lambda x: x.price == None, retry_prices)

            # if missing prices are the same at previous iteration retry query for `retry` tiems with increasing timeout
            if not retry_ok:
                time.sleep(retry_timeout)
                retry_timeout += 2
                i += 1
                continue
            # If missing prices changed compared to last iterations
            else:
                # Reset tiemout and retries count
                losses = retry_losses
                ok += retry_ok
                retry_timeout = timeout
                i = 0
        # If all prices are retrieved
        else:
            print('[+] All losses retrieved')
            return ok
    # If retries attempts gone but there are still some missing prices 
    print('- Reached retries limit or prices are irreplaceable')
    print(f'- Losses: {len(losses)}')
    return ok + losses

# async def get_item_prices_without_loss(session: aiohttp.ClientSession, product_codes: Iterable[str], semaphore):
#     prices = await get_item_prices(session, product_codes, semaphore)
#     print('[+] Identifying losses...')
#     ok, missing = split_array_by_condition(lambda x: x.price == None, prices)
#     if sorted([item.product_code for item in missing]) == sorted(product_codes):
#         print(f'[+] {len(missing)} losses are irreplaceable')
#         return prices
#     if missing:
#         print(f'[+] Losses: {len(missing)}')
#         ok += await get_item_prices_without_loss(session, [item.product_code for item in missing], semaphore)
#     print(['[+] No more losses'])
#     return ok


def append_prices_to_items(items: List[dict], prices: List[ItemPrice]) -> List[dict]:
    if len(prices) != len(items):
        raise KeyError('Items length are not equal to prices length') # remove it later

    items = sorted(items, key=lambda x: x["product_code"])
    prices = sorted(prices, key=lambda x: x.product_code)

    result = []
    for item, price in zip(items, prices):
        if item["product_code"] == price.product_code:
            item.update(price.to_dict())
            result.append(item)
    return result
