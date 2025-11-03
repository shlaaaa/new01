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
python scrape_gsshop.py \
  --target-count 1000 \
  --page-size 60
```

> **Tip:** The script now automatically targets the liquor category
> (`msectid=1548240`). Supply a custom `--param` if you need a different
> section.

Useful options:

- `--param KEY=VALUE`: Append extra query parameters (e.g., `disp_ctg_no`).
- `--header KEY=VALUE`: Supply additional headers observed in the browser (e.g., cookies).
- `--delay`: Control pacing between requests to avoid rate limiting.
- `--output`: Choose the CSV destination filename.
- `--base-url`: Override the product API endpoint. Leave as `auto` (the default)
  to probe a set of public endpoints that power the storefront.

The script automatically attempts multiple API endpoints exposed to regular
GS Shop visitors, so you can simply run it with the defaults. The payload
parser is defensive and copes with minor schema changes by looking for
common GS Shop field names (`goodsNo`, `goodsNm`, `sellPrice`, etc.).

## Running from GitHub Actions

This repository ships with a reusable workflow (`.github/workflows/scrape.yml`)
that executes the scraper inside GitHub Actions and publishes the resulting CSV
as both a downloadable artifact and a short table inside the workflow run
summary.

1. Navigate to the **Actions** tab in GitHub and choose the "Run GS Shop scraper"
   workflow.
2. Accept the defaults (they already request 1,000 items from
   `msectid=1548240`) or provide custom inputs. Supply additional query
   parameters or headers as newline-separated `KEY=VALUE` pairs when
   needed. Leave the base URL as `auto` to rely on the built-in list of
   public endpoints.
3. Dispatch the workflow. Once the run completes you can download the generated
   CSV artifact or inspect the first few rows directly from the workflow run
   summary.
