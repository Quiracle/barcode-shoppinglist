from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductInfo:
    name: str
    brand: Optional[str] = None
    image_url: Optional[str] = None


class ProductLookupProvider:
    def lookup(self, barcode: str) -> Optional[ProductInfo]:
        raise NotImplementedError
