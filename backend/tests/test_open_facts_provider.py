from app.providers.open_facts import OpenFactsLookupProvider


def test_parse_product_with_name_brand_and_image() -> None:
    payload = {
        "status": 1,
        "product": {
            "product_name": "Shampoo Protección y Brillo",
            "brands": "Deliplus,Other",
            "image_front_url": "https://images.openbeautyfacts.org/sample.jpg",
        },
    }

    info = OpenFactsLookupProvider._parse_product(payload)

    assert info is not None
    assert info.name == "Shampoo Protección y Brillo"
    assert info.brand == "Deliplus"
    assert info.image_url == "https://images.openbeautyfacts.org/sample.jpg"


def test_parse_product_without_name_returns_none() -> None:
    payload = {
        "status": 1,
        "product": {
            "brands": "Brand",
            "image_url": "https://example.com/image.jpg",
        },
    }

    info = OpenFactsLookupProvider._parse_product(payload)

    assert info is None
