import aiohttp

from typing import Iterable, List
from src.models import BrandFilter, Brand
from src.urls import async_get_soup_from_url, add_query_params, get_query_params, strip_query_params
from bs4 import BeautifulSoup, Tag


def create_url_for_missing_brands(category_page_url: str) -> str:
    API_url = 'https://md.e-cat.intercars.eu/ru/fragments/category/facet/list?facetCode=productBrandCode'
    search_query = get_query_params(category_page_url).get('q')
    category_path = strip_query_params(category_page_url).split('/')[-1]
    params = {
        'categoryPath': category_path,
        'searchQuery': search_query
    }
    result_url = add_query_params(API_url, params)
    return result_url


def group_brands_into_filters_up_to_item_counter_limit(brands_list: Iterable[Brand]) -> Iterable[Iterable[BrandFilter]]:
    brands_list = sorted(
        brands_list, key=lambda brand: brand.items_count, reverse=True)

    filters = []
    current_filter = BrandFilter()
    current_sum = 0

    for brand in brands_list:
        if current_sum + brand.items_count > 2500:
            filters.append(current_filter)
            current_filter = BrandFilter()
            current_sum = 0
        current_filter.add_brand(brand)
        current_sum += brand.items_count

    if current_filter.brands_list:
        filters.append(current_filter)

    return filters


def parse_brand(element: Tag) -> Brand:
    code = element.find(
        'input', class_='facetnav__listitemfield').get('data-value')
    items_counter = element.find(class_='facetnav__listitemcounter').text
    return Brand(code, int(items_counter))


def parse_brands_from_soup(soup: BeautifulSoup) -> List[Brand]:
    brands_list = []
    for element in soup.find_all('label', class_='facetnav__listitem'):
        brands_list.append(parse_brand(element))

    return brands_list


async def parse_preloaded_brands_forom_page(session: aiohttp.ClientSession, url: str) -> List[Brand]:
    soup = await async_get_soup_from_url(session, url)
    try:
        nav_elemnt_with_brands_options = next(el for el in soup.find_all(
            'div', class_='facetnav__name') if el.get_text(strip=True).lower() == 'производитель').parent
    except StopIteration:
        return []
    return parse_brands_from_soup(nav_elemnt_with_brands_options)


async def get_missing_brands(session: aiohttp.ClientSession, category_page_url: str) -> List[Brand]:
    API_missing_brands_url = create_url_for_missing_brands(category_page_url)
    soup = await async_get_soup_from_url(session, API_missing_brands_url)
    brands_lsit = parse_brands_from_soup(soup)
    return brands_lsit


async def parse_brands_from_url(session: aiohttp.ClientSession, url):
    brands_list = []
    brands_list += await parse_preloaded_brands_forom_page(session, url)
    brands_list += await get_missing_brands(session, url)

    return brands_list
