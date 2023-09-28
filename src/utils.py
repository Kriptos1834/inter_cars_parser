import os

from typing import List

def get_or_create_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path


def prettify_description(description: str) -> dict:
    pretty_description = {}
    for desc_string in description.split('|'):
        desc_string = desc_string.strip()
        desc_items = desc_string.split(':')
        desc_title = desc_items[0].strip()
        desc_value = desc_items[1].strip()
        pretty_description[desc_title] = desc_value
    return pretty_description


def drop_duplicates(l: List[dict], key: str):
    seen = set()
    return [d for d in l if d[key] not in seen and not seen.add(d[key])]


def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def split_array_by_condition(condition, l: list):
    filtered = list(filter(condition, l))
    return [i for i in l if i not in filtered], filtered


def fix_encoding(price_string: str):
    return price_string.encode("ascii", 'ignore').decode('utf-8')
