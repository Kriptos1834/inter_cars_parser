import aiohttp
import requests

from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, parse_qsl, urlencode, unquote


def join_search_query(*queries):
    joined_query = ''
    for query in queries:
        query = unquote(query)
        joined_query += ':'+':'.join(list(filter(None, query.split(':'))))
    return joined_query


def strip_query_params(url: str) -> str:
    parsed_url = urlparse(url)
    parsed_url = parsed_url._replace(query=None)
    return parsed_url.geturl()


def get_query_params(url: str) -> dict:
    parsed_url = urlparse(url)
    params = dict(parse_qsl(parsed_url.query))
    return params


def add_query_params(url: str, params: dict) -> str:
    parsed_url = urlparse(url)
    current_params = dict(parse_qsl(parsed_url.query))
    current_params.update(params)
    encoded_params = urlencode(current_params)
    new_url = parsed_url._replace(query=encoded_params)
    return new_url.geturl()


def reformat_subcategory_path(subcategory_path: str) -> str:
    query_params = {
        'q': ':default:branchAvailability:ALL:logisticPathAvailability:true:onRequestOnly:false:retailPriceGrossValue:ALL'
    }
    path = strip_query_params(subcategory_path)
    path = add_query_params(path, query_params)
    return path


def get_subcategory_url_from_path(path: 'str') -> 'str':
    return 'https://md.e-cat.intercars.eu' + reformat_subcategory_path(path)


def get_soup_from_url(session: requests.session, url: str) -> BeautifulSoup:
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    return soup


async def async_get_soup_from_url(session: aiohttp.ClientSession, url: str) -> BeautifulSoup:
    async with session.get(url) as response:
        soup = BeautifulSoup(await response.text(), 'lxml')
        return soup


def create_aiohttp_session(sync_session: requests.Session) -> aiohttp.ClientSession:
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=20)
    return aiohttp.ClientSession(headers=sync_session.headers, cookies=sync_session.cookies.get_dict(), timeout=timeout)
