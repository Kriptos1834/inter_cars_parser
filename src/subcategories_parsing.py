import aiohttp
import asyncio

from src.urls import async_get_soup_from_url, get_subcategory_url_from_path
from src.progress import async_execute_tasks_with_progressbar
from bs4 import BeautifulSoup
from typing import List
from itertools import chain

async def get_subcategories_soup(session: aiohttp.ClientSession, category_id: str) -> BeautifulSoup:
    subcategories_lsit_url = f'https://md.e-cat.intercars.eu/ru/fragments/vehicle/landing-page/subcategories-tree-node?category={category_id}&vehicle'
    soup = await async_get_soup_from_url(session, subcategories_lsit_url)
    return soup


async def parse_category_URLs(session: aiohttp.ClientSession, category_id: str) -> list:
    URLs = []
    soup = await get_subcategories_soup(session, category_id)
    for element in soup.find_all('div', class_='categoriestree__subcategory'):
        category_data_code = element.get('data-code')

        if category_data_code.startswith('genart'):
            path = element.find('a', class_='categoriestree__subcategoryanchor').get('href')
            subcategory_url = get_subcategory_url_from_path(path)
            URLs.append(subcategory_url)

        else:
            URLs += await parse_category_URLs(session, category_data_code)

    return URLs


async def get_subcategories_URLs(session: aiohttp.ClientSession, category_ids: List[str]) -> List[str]:
    tasks = []
    for category_id in category_ids:
        tasks.append(asyncio.create_task(parse_category_URLs(session, category_id)))
    results = await async_execute_tasks_with_progressbar(tasks, skip_errors=False, desc='[+] Collecting subcategory URL\'s')
    return list(chain(*results))