# GS Shop Liquor Scraper

This repository contains a Python script that automates the collection of
at least 1,000 liquor product listings (with prices) from the GS Shop
category at [msectid=1548240](https://www.gsshop.com/shop/wine/cate.gs?msectid=1548240).
The workflow mirrors the step-by-step plan previously outlined:

1. Inspect the website's network calls via the browser developer tools to
   locate the product-listing API endpoint.
2. Reproduce those API calls with the appropriate headers using the
   `requests` library.
3. Iterate through pages until the desired number of unique products is
   gathered.
4. Export the consolidated results to CSV for further analysis.

## Usage

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # or manually install requests and pandas
python scrape_gsshop.py --target-count 1000 --page-size 60 --param msectid=1548240
```

Useful options:

- `--param KEY=VALUE`: Append extra query parameters (e.g., `disp_ctg_no`).
- `--header KEY=VALUE`: Supply additional headers observed in the browser (e.g., cookies).
- `--delay`: Control pacing between requests to avoid rate limiting.
- `--output`: Choose the CSV destination filename.

Before executing, replace `BASE_URL` in `scrape_gsshop.py` with the actual
API endpoint discovered via developer tools and, if needed, adjust the
field names inside `Product.from_payload` to match the live schema.
