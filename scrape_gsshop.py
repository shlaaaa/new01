"""Utility to scrape liquor product listings from GS Shop.

This module demonstrates how to automate the extraction of at least
1,000 liquor products (including prices) from the GS Shop category at
https://www.gsshop.com/shop/wine/cate.gs?msectid=1548240.  It mirrors the
workflow previously outlined:

* Identify the product-listing API through developer tools.
* Recreate authenticated requests with the necessary headers.
* Iterate over pages until the desired number of records is collected.
* Persist the resulting data to a CSV file for later use.

The script assumes that the product API returns JSON objects with the
following shape (field names can be adjusted to match the actual
response):

{
    "products": [
        {
            "goodsNo": "12345678",
            "goodsNm": "Sample Liquor",
            "price": {"sellPrice": 10000},
            "detailUrl": "https://www.gsshop.com/shop/detail.gs?...")
        }
    ]
}

Before running the script, update ``BASE_URL`` and any query parameters
or headers to match the real API call captured from the browser's
network inspector.
"""
from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests

LOGGER = logging.getLogger(__name__)


BASE_URL = "https://www.gsshop.com/some/product/api"
"""Placeholder endpoint discovered via browser developer tools.

Replace this value with the actual API endpoint captured from the
Network panel (typically an endpoint such as
``https://api.gsshop.com/prdw/store/v1/goods``).  The remainder of the
module is agnostic to the specific endpoint structure.
"""

REFERER_URL = "https://www.gsshop.com/shop/wine/cate.gs?msectid=1548240"
"""Referer header that mimics navigation from the category page."""

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": REFERER_URL,
    "Accept": "application/json, text/plain, */*",
}
"""Baseline headers required to emulate a browser request.

Add cookies or authentication headers if the captured request requires
it.  The defaults are intentionally lightweight so that developers can
extend them for their own environment.
"""


@dataclass
class Product:
    """Represents a single product extracted from the GS Shop API."""

    id: str
    name: str
    price: int
    url: str

    @classmethod
    def from_payload(cls, payload: Dict[str, object]) -> "Product":
        """Construct a :class:`Product` from a raw API payload.

        The GS Shop product payload uses ``goodsNo`` for the product ID
        and nests pricing under the ``price`` key.  The helper is
        defensive so that the script can cope with small schema
        variations (for example, some responses might expose ``sellPrice``
        directly on the product object).
        """

        goods_no = str(payload.get("goodsNo") or payload.get("goodsId"))
        if not goods_no:
            raise ValueError("Unable to determine product ID from payload")

        name = str(payload.get("goodsNm") or payload.get("name") or "")
        if not name:
            raise ValueError(
                f"Product {goods_no!r} is missing a name: {payload!r}"
            )

        price_info = payload.get("price") or {}
        sell_price = price_info.get("sellPrice") or payload.get("sellPrice")
        if sell_price is None:
            raise ValueError(
                f"Product {goods_no!r} is missing sell price: {payload!r}"
            )

        detail_url = str(
            payload.get("detailUrl")
            or payload.get("url")
            or payload.get("goodsDetailUrl")
            or ""
        )
        if not detail_url:
            raise ValueError(
                f"Product {goods_no!r} is missing a detail URL: {payload!r}"
            )

        return cls(id=goods_no, name=name, price=int(sell_price), url=detail_url)


def fetch_products(
    page: int,
    page_size: int,
    headers: Optional[Dict[str, str]] = None,
    session: Optional[requests.Session] = None,
    **params: object,
) -> List[Product]:
    """Fetch a single page of products from the GS Shop API.

    Parameters
    ----------
    page:
        Page index to request.  Many GS Shop endpoints are 1-indexed; the
        caller should adjust according to the observed API schema.
    page_size:
        Number of products per page.  The category UI typically renders
        60 items per batch, which is used as the default.
    headers:
        HTTP headers to use when making the request.  When ``None``,
        :data:`DEFAULT_HEADERS` are used.
    session:
        Optional :class:`requests.Session` for connection pooling.
    **params:
        Additional query parameters forwarded to the request (for
        example ``msectid`` or ``disp_ctg_no``).
    """

    request_headers = dict(DEFAULT_HEADERS)
    if headers:
        request_headers.update(headers)

    query_params = {"page": page, "size": page_size, **params}
    http = session or requests
    LOGGER.debug("Requesting %s with params %s", BASE_URL, query_params)
    response = http.get(BASE_URL, headers=request_headers, params=query_params, timeout=10)
    response.raise_for_status()

    payload = response.json()
    raw_products: Iterable[Dict[str, object]]
    if isinstance(payload, dict):
        if "products" in payload:
            raw_products = payload["products"]
        elif "data" in payload and isinstance(payload["data"], dict):
            raw_products = payload["data"].get("products", [])
        else:
            raw_products = []
    else:
        raw_products = []

    products: List[Product] = []
    for raw in raw_products:
        try:
            products.append(Product.from_payload(raw))
        except ValueError as exc:
            LOGGER.debug("Skipping product due to schema issue: %s", exc)

    return products


def collect_products(
    target_count: int = 1000,
    page_size: int = 60,
    delay_seconds: float = 1.0,
    headers: Optional[Dict[str, str]] = None,
    **params: object,
) -> List[Product]:
    """Collect products until ``target_count`` unique items are gathered."""

    items: Dict[str, Product] = {}
    page = 1
    session = requests.Session()

    while len(items) < target_count:
        products = fetch_products(
            page=page,
            page_size=page_size,
            headers=headers,
            session=session,
            **params,
        )

        if not products:
            LOGGER.info("No products returned for page %s; stopping.", page)
            break

        for product in products:
            items.setdefault(product.id, product)

        LOGGER.info(
            "Collected %s/%s products after page %s",
            len(items),
            target_count,
            page,
        )

        page += 1
        time.sleep(delay_seconds)

    return list(items.values())


def export_to_csv(products: Iterable[Product], output_path: str) -> None:
    """Persist the gathered products to ``output_path`` as CSV."""

    data = [asdict(product) for product in products]
    frame = pd.DataFrame(data)
    frame.to_csv(output_path, index=False)
    LOGGER.info("Saved %s products to %s", len(data), output_path)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the scraper."""

    parser = argparse.ArgumentParser(
        description=(
            "Collect liquor products from the GS Shop category and export"
            " them to a CSV file."
        )
    )
    parser.add_argument(
        "--target-count",
        type=int,
        default=1000,
        help="Number of unique products to collect (default: 1000)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=60,
        help="Number of products per page in the API (default: 60)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between page requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--output",
        default="gsshop_liquor.csv",
        help="CSV file to write results to (default: gsshop_liquor.csv)",
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Additional query parameters to pass to the API call. "
            "Specify multiple times for multiple parameters."
        ),
    )
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Additional HTTP headers to include with the request. "
            "Specify multiple times for multiple headers."
        ),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level (default: INFO)",
    )
    return parser.parse_args()


def parse_key_value_pairs(pairs: Iterable[str]) -> Dict[str, str]:
    """Convert KEY=VALUE strings into a dictionary."""

    result: Dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Invalid key/value pair: {pair!r}")
        key, value = pair.split("=", 1)
        result[key] = value
    return result


def main() -> None:
    """Entry point when running the module as a script."""

    args = parse_args()
    logging.basicConfig(level=args.log_level.upper(), format="%(message)s")

    extra_params = parse_key_value_pairs(args.param)
    extra_headers = parse_key_value_pairs(args.header)

    products = collect_products(
        target_count=args.target_count,
        page_size=args.page_size,
        delay_seconds=args.delay,
        headers={**DEFAULT_HEADERS, **extra_headers} if extra_headers else None,
        **extra_params,
    )

    if not products:
        LOGGER.warning("No products collected. Verify the API endpoint and parameters.")
        return

    export_to_csv(products, args.output)


if __name__ == "__main__":
    main()
