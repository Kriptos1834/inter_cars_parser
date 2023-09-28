from typing import Iterable


class Brand:
    def __init__(self, code: str, items_count: int) -> None:
        self.code = code
        self.items_count = items_count


class BrandFilter:
    def __init__(self, brands_lsit: Iterable[Brand] = []) -> None:
        self.brands_list = list(brands_lsit)

    def add_brand(self, brand: Brand):
        self.brands_list.append(brand)

    def get_filter_query(self):
        return ''.join(brand.code for brand in self.brands_list)

    def get_total_items_count(self):
        return sum(brand.items_count for brand in self.brands_list)


class ItemPrice:
    def __init__(self, product_code: str, price: float | None) -> None:
        self.product_code = product_code
        self.price = price

    def to_dict(self):
        return {'product_code': self.product_code, 'price': self.price}
    
    def __repr__(self) -> str:
        return f'{self.product_code}: {self.price}'

    def __str__(self) -> str:
        return f'{self.product_code}: {self.price}'
