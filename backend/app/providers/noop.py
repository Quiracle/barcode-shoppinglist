from typing import Optional

from app.providers.base import ProductInfo, ProductLookupProvider


class NoopLookupProvider(ProductLookupProvider):
    def lookup(self, barcode: str) -> Optional[ProductInfo]:
        return None
