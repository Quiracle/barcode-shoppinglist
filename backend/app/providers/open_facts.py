from __future__ import annotations

import json
import logging
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.providers.base import ProductInfo, ProductLookupProvider

logger = logging.getLogger(__name__)


SOURCE_URLS = {
    "beauty": "https://world.openbeautyfacts.org",
    "food": "https://world.openfoodfacts.org",
    "pet": "https://world.openpetfoodfacts.org",
}


class OpenFactsLookupProvider(ProductLookupProvider):
    def __init__(
        self,
        timeout_seconds: float = 3.0,
        sources: tuple[str, ...] = ("beauty", "food", "pet"),
        user_agent: str = "barcode-shoppinglist/1.0 (+https://github.com/jsala/barcode-shoppinglist)",
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.sources = tuple(source for source in sources if source in SOURCE_URLS)
        self.user_agent = user_agent

    def lookup(self, barcode: str) -> Optional[ProductInfo]:
        if not barcode:
            return None

        for source in self.sources:
            payload = self._fetch_product(source, barcode)
            if payload is None:
                continue
            info = self._parse_product(payload)
            if info is not None:
                return info
        return None

    def _fetch_product(self, source: str, barcode: str) -> Optional[dict]:
        base = SOURCE_URLS[source]
        query = urlencode(
            {
                "fields": "code,product_name,product_name_en,generic_name,brands,image_front_url,image_url,status",
            }
        )
        url = f"{base}/api/v2/product/{barcode}.json?{query}"
        request = Request(url, headers={"User-Agent": self.user_agent})

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
            return json.loads(body)
        except HTTPError as exc:
            # Missing products are expected often.
            if exc.code != 404:
                logger.debug("Lookup HTTP error for %s from %s: %s", barcode, source, exc)
            return None
        except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.debug("Lookup network/decode error for %s from %s: %s", barcode, source, exc)
            return None

    @staticmethod
    def _parse_product(payload: dict) -> Optional[ProductInfo]:
        if payload.get("status") != 1:
            return None

        product = payload.get("product") or {}
        name = (
            str(product.get("product_name") or "").strip()
            or str(product.get("product_name_en") or "").strip()
            or str(product.get("generic_name") or "").strip()
        )
        if not name:
            return None

        brand_raw = str(product.get("brands") or "").strip()
        brand = brand_raw.split(",")[0].strip() if brand_raw else None

        image_url = (
            str(product.get("image_front_url") or "").strip()
            or str(product.get("image_url") or "").strip()
            or None
        )

        return ProductInfo(name=name, brand=brand, image_url=image_url)
