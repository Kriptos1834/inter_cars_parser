import asyncio
import aiohttp
import os

from bs4 import BeautifulSoup, Tag
from src.settings import DEBUG
from src.utils import prettify_description, drop_duplicates
from src.models import BrandFilter
from src.urls import async_get_soup_from_url, add_query_params, join_search_query, get_query_params
from src.progress import async_execute_tasks_with_progressbar
from src.brands import parse_brands_from_url, group_brands_into_filters_up_to_item_counter_limit
from src.prices import get_item_prices_without_loss, append_prices_to_items
from itertools import chain
from typing import Iterable, List


def parse_item_number(item: BeautifulSoup | Tag) -> str:
    """Extracts the item number from a BeautifulSoup object representing an item."""
    try:
        return item.find('a', class_='activenumber').get_text(strip=True)
    except AttributeError:
        return None


def parse_item_name(item: BeautifulSoup | Tag) -> str:
    """Extracts the item name from a BeautifulSoup object representing an item."""
    try:
        return item.find('div', class_='productname').get_text(strip=True)
    except AttributeError:
        return None


def parse_item_brand(item: BeautifulSoup | Tag) -> str:
    """Extracts the item brand from a BeautifulSoup object representing an item."""
    try:
        brand_img = item.find(
            'img', class_='listingcollapsed__manufacturerimg')
        if brand_img:
            return brand_img.get('title')
        return item.find('div', class_='listingcollapsed__manufacturer').get_text(strip=True)
    except AttributeError:
        return None


def parse_delivery_time(item: BeautifulSoup | Tag) -> str:
    """Extracts the delivery time from a BeautifulSoup object representing an item."""
    try:
        return item.find('div', class_='productdelivery__date').get_text(strip=True)
    except AttributeError:
        return None


def parse_stock_info(item: BeautifulSoup | Tag) -> str:
    """Extracts the stock info from a BeautifulSoup object representing an item."""
    try:
        return item.find('div', class_='productdelivery__sum').parent.find('span', class_='productdelivery__stockinfotext').get_text(strip=True)
    except AttributeError:
        return None


def parse_item_product_code(item: BeautifulSoup | Tag) -> str:
    """Extracts the product code from a BeautifulSoup object representing an item."""
    return item.get('data-product-code')


def parse_item_description(item: BeautifulSoup | Tag) -> dict:
    """Extracts the item description from a BeautifulSoup object representing an item."""
    try:
        return prettify_description(item.find(class_='productfeaturesinline').text)
    except AttributeError:
        return None

def parse_image_url(item: BeautifulSoup | Tag) -> str:
    """Extracts the image url a BeautifulSoup object representing an item."""
    try:
        return item.find('img', class_='productimage__image').get('data-src').replace('t_t150x150v2/', '')
    except AttributeError:
        return None


async def parse_items_from_soup(soup: BeautifulSoup) -> List[dict]:
    items_on_page = []
    for item_element in soup.find_all('tbody', class_='listingcollapsed__item'):
        items_on_page.append({
            'item_number': parse_item_number(item_element),
            'item_name': parse_item_name(item_element),
            'item_brand': parse_item_brand(item_element),
            'product_code': parse_item_product_code(item_element),
            'delivery_time': parse_delivery_time(item_element),
            'stock_info': parse_stock_info(item_element),
            'item_description': parse_item_description(item_element),
            'image_url': parse_image_url(item_element),
            'currency': 'MDL' # TODO: сделать нормально, но потом
        })
    return items_on_page


async def get_items_from_page(session: aiohttp.ClientSession, url: str, sm: asyncio.Semaphore) -> List[dict]:
    async with sm:
        soup = await async_get_soup_from_url(session, url)
        return await parse_items_from_soup(soup)


def get_url_for_page(subcategory_url: str, filter: BrandFilter, page: int) -> str:
    search_query = get_query_params(subcategory_url).get('q')
    search_query = join_search_query(search_query, filter.get_filter_query())
    url_with_params = add_query_params(subcategory_url, {
        'q': search_query,
        'page': page
    })
    return url_with_params


async def create_tasks_for_parsing_subcategory(session: aiohttp.ClientSession, url, sm: asyncio.Semaphore) -> List[asyncio.Task]:
    async with sm:
        brands_list = await parse_brands_from_url(session, url)
        filters = group_brands_into_filters_up_to_item_counter_limit(
            brands_list)
        tasks = []
        for brand_filter in filters:
            for page in range(brand_filter.get_total_items_count() // 25 + 1):
                page_url = get_url_for_page(url, brand_filter, page)
                tasks.append(asyncio.create_task(
                    get_items_from_page(session, page_url, sm)))
        return tasks


async def gather_data(page_URLs: Iterable[str], session: aiohttp.ClientSession) -> None:
    sm = asyncio.Semaphore((2 * os.cpu_count()) + 1)
    tasks = []
    subtasks = []

    for url in page_URLs:
        subtasks.append(asyncio.create_task(create_tasks_for_parsing_subcategory(session, url, sm)))

    subtasks_results = await async_execute_tasks_with_progressbar(subtasks, not DEBUG, desc='[+] Preparing tasks')
    for result in subtasks_results:
        tasks += result

    product_items = list(chain(*await async_execute_tasks_with_progressbar(tasks, desc='[+] Parsing pages')))
    product_items = drop_duplicates(product_items, 'product_code')
    prices = await get_item_prices_without_loss(session, [item['product_code'] for item in product_items], sm)

    return append_prices_to_items(product_items, prices)
