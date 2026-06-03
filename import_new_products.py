import subprocess
import re
import requests
from bs4 import BeautifulSoup

PRODUCTS_FILE = "products.js"

SHOPIFY_SOURCES = [
    {
        "brand": "BAPE",
        "category": "mens",
        "sale": False,
        "base_url": "https://uk.bape.com",
        "url": "https://uk.bape.com/collections/new/products.json?limit=250"
    },
    {
        "brand": "BBC",
        "category": "mens",
        "sale": False,
        "base_url": "https://bbcicecream.eu",
        "url": "https://bbcicecream.eu/collections/newarrivals/products.json?limit=250"
    }
]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def read_existing_products():
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        return [], set()

    existing_links = set(re.findall(r'link:\s*"([^"]+)"', content))
    product_blocks = re.findall(r"\{[\s\S]*?\},", content)

    return product_blocks, existing_links


def clean_image_url(image_url, base_url):
    if not image_url:
        return None

    if "," in image_url:
        image_url = image_url.split(",")[0].strip().split(" ")[0]

    if image_url.startswith("//"):
        image_url = "https:" + image_url

    if image_url.startswith("/"):
        image_url = base_url + image_url

    return image_url


def shopify_product_to_js(product, source):
    handle = product.get("handle")
    images = product.get("images", [])

    if not handle or not images:
        return None

    image = images[0]
    image_url = image.get("src") if isinstance(image, dict) else image
    product_url = f'{source["base_url"]}/products/{handle}'

    sale_line = ",\n    sale: true" if source["sale"] else ""

    return f'''  {{
    image: "{image_url}",
    link: "{product_url}",
    category: "{source["category"]}",
    brand: "{source["brand"]}"{sale_line}
  }},'''


def import_shopify_products(existing_links):
    new_blocks = []

    for source in SHOPIFY_SOURCES:
        print("Checking:", source["brand"])

        try:
            response = requests.get(source["url"], headers=HEADERS, timeout=20)
            response.raise_for_status()

            data = response.json()
            products = data.get("products", [])

            print(f"Found {len(products)} products")

            for product in products:
                handle = product.get("handle")
                product_url = f'{source["base_url"]}/products/{handle}'

                if product_url in existing_links:
                    continue

                block = shopify_product_to_js(product, source)

                if block:
                    new_blocks.append(block)
                    existing_links.add(product_url)
                    print("Added:", product_url)

        except Exception as error:
            print("Could not import:", source["brand"])
            print(error)

    return new_blocks


def import_motel_rocks(existing_links):
    print("Checking: Motel Rocks")

    new_blocks = []
    url = "https://www.motelrocks.com/collections/new-in"

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)

        for link_tag in links:
            href = link_tag["href"]

            if "/products/" not in href:
                continue

            product_url = href if href.startswith("http") else "https://www.motelrocks.com" + href
            product_url = product_url.split("?")[0]

            if product_url in existing_links:
                continue

            image_tag = link_tag.find("img") or link_tag.find_next("img")

            if not image_tag:
                continue

            image_url = (
                image_tag.get("src")
                or image_tag.get("data-src")
                or image_tag.get("data-original")
                or image_tag.get("data-srcset")
                or image_tag.get("srcset")
            )

            image_url = clean_image_url(image_url, "https://www.motelrocks.com")

            if not image_url:
                continue

            block = f'''  {{
    image: "{image_url}",
    link: "{product_url}",
    category: "womens",
    brand: "Motel Rocks"
  }},'''

            new_blocks.append(block)
            existing_links.add(product_url)

            print("Added:", product_url)

    except Exception as error:
        print("Could not import: Motel Rocks")
        print(error)

    return new_blocks


def import_carhartt(existing_links):
    print("Checking: Carhartt")

    new_blocks = []
    url = "https://www.carhartt-wip.com/en-gb/c/men-new"

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        product_links = soup.find_all("a", href=True)

        for link_tag in product_links:
            href = link_tag["href"]

            if "/en-gb/p/" not in href:
                continue

            product_url = href if href.startswith("http") else "https://www.carhartt-wip.com" + href
            product_url = product_url.split("?")[0]

            if product_url in existing_links:
                continue

            image_tag = link_tag.find("img") or link_tag.find_next("img")

            if not image_tag:
                continue

            image_url = (
                image_tag.get("src")
                or image_tag.get("data-src")
                or image_tag.get("data-original")
                or image_tag.get("data-srcset")
                or image_tag.get("srcset")
            )

            image_url = clean_image_url(image_url, "https://www.carhartt-wip.com")

            if not image_url:
                continue

            block = f'''  {{
    image: "{image_url}",
    link: "{product_url}",
    category: "mens",
    brand: "Carhartt"
  }},'''

            new_blocks.append(block)
            existing_links.add(product_url)

            print("Added:", product_url)

    except Exception as error:
        print("Could not import: Carhartt")
        print(error)

    return new_blocks


def push_to_github():
    print("Pushing updates to GitHub...")

    subprocess.run(["git", "add", "."], cwd="C:\\Website", check=True)
    subprocess.run(["git", "commit", "-m", "Daily product update"], cwd="C:\\Website", check=True)
    subprocess.run(["git", "push"], cwd="C:\\Website", check=True)

    print("GitHub updated. Netlify should redeploy automatically.")


def import_products():
    existing_blocks, existing_links = read_existing_products()

    new_blocks = []

    new_blocks += import_shopify_products(existing_links)
    new_blocks += import_motel_rocks(existing_links)
    new_blocks += import_carhartt(existing_links)

    all_blocks = new_blocks + existing_blocks

    new_content = "const products = [\n\n"
    new_content += "\n\n".join(all_blocks)
    new_content += "\n\n];"

    with open(PRODUCTS_FILE, "w", encoding="utf-8") as file:
        file.write(new_content)

    print(f"Done. Added {len(new_blocks)} new products.")

    if len(new_blocks) > 0:
        push_to_github()
    else:
        print("No new products found, so nothing was pushed to GitHub.")


import_products()