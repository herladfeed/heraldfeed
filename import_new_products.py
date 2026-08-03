import subprocess
import re
import time
import random
import requests

from bs4 import BeautifulSoup


PRODUCTS_FILE = "products.js"
WEBSITE_FOLDER = r"C:\Website"

SHOPIFY_SOURCES = [
    {
        "brand": "BAPE",
        "category": "mens",
        "sale": False,
        "base_url": "https://uk.bape.com",
        "url": "https://uk.bape.com/collections/new/products.json?limit=50",
    }
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json,text/plain,*/*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Cache-Control": "no-cache",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


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

    image_url = image_url.strip()

    if "," in image_url:
        image_url = image_url.split(",")[0].strip()

    if " " in image_url:
        image_url = image_url.split(" ")[0].strip()

    if image_url.startswith("//"):
        image_url = "https:" + image_url
    elif image_url.startswith("/"):
        image_url = base_url.rstrip("/") + image_url

    return image_url


def make_product_block(image_url, product_url, category, brand, sale=False):
    sale_line = ",\n    sale: true" if sale else ""

    return f'''  {{
    image: "{image_url}",
    link: "{product_url}",
    category: "{category}",
    brand: "{brand}"{sale_line}
  }},'''


def shopify_product_to_js(product, source):
    handle = product.get("handle")
    images = product.get("images", [])

    if not handle or not images:
        return None

    image = images[0]
    image_url = image.get("src") if isinstance(image, dict) else image
    image_url = clean_image_url(image_url, source["base_url"])

    if not image_url:
        return None

    product_url = f'{source["base_url"].rstrip("/")}/products/{handle}'

    return make_product_block(
        image_url=image_url,
        product_url=product_url,
        category=source["category"],
        brand=source["brand"],
        sale=source["sale"],
    )


def get_with_retries(url, max_retries=4):
    for attempt in range(max_retries):
        try:
            response = SESSION.get(url, timeout=30)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")

                if retry_after:
                    try:
                        wait_time = int(float(retry_after))
                    except ValueError:
                        wait_time = 60
                else:
                    wait_time = 30 * (attempt + 1)

                wait_time += random.randint(3, 10)

                print(
                    f"Rate limited. Waiting {wait_time} seconds "
                    f"before retry {attempt + 1}/{max_retries}..."
                )
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            return response

        except requests.RequestException as error:
            if attempt == max_retries - 1:
                print(f"Request failed permanently: {error}")
                return None

            wait_time = 10 * (attempt + 1)
            print(f"Request failed: {error}")
            print(f"Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)

    return None


def find_image_for_product_link(link_tag):
    image_tag = link_tag.find("img")

    if image_tag is None:
        image_tag = link_tag.find_next("img")

    if image_tag is None:
        return None

    return (
        image_tag.get("src")
        or image_tag.get("data-src")
        or image_tag.get("data-original")
        or image_tag.get("data-lazy-src")
        or image_tag.get("data-srcset")
        or image_tag.get("srcset")
    )


def import_shopify_products(existing_links):
    new_blocks = []

    for source in SHOPIFY_SOURCES:
        print("Checking:", source["brand"])

        try:
            response = get_with_retries(source["url"])

            if response is None:
                print("No response received.")
                continue

            data = response.json()
            products = data.get("products", [])

            print(f"Found {len(products)} products")

            for product in products:
                handle = product.get("handle")

                if not handle:
                    continue

                product_url = (
                    f'{source["base_url"].rstrip("/")}/products/{handle}'
                )

                if product_url in existing_links:
                    continue

                block = shopify_product_to_js(product, source)

                if block:
                    new_blocks.append(block)
                    existing_links.add(product_url)
                    print("Added:", product_url)

        except (ValueError, requests.RequestException) as error:
            print("Could not import:", source["brand"])
            print(error)
        except Exception as error:
            print("Unexpected error importing:", source["brand"])
            print(error)

        time.sleep(random.randint(10, 20))

    return new_blocks


def import_bbc(existing_links):
    print("Checking: BBC")

    new_blocks = []
    collection_url = "https://bbcicecream.eu/collections/newarrivals"
    base_url = "https://bbcicecream.eu"

    try:
        response = get_with_retries(collection_url)

        if response is None:
            print("No response received for BBC.")
            return new_blocks

        soup = BeautifulSoup(response.text, "html.parser")

        for link_tag in soup.find_all("a", href=True):
            href = link_tag.get("href", "")

            if "/products/" not in href:
                continue

            product_url = (
                href if href.startswith("http")
                else base_url + href
            )
            product_url = product_url.split("?")[0]

            if product_url in existing_links:
                continue

            image_url = find_image_for_product_link(link_tag)
            image_url = clean_image_url(image_url, base_url)

            if not image_url:
                continue

            block = make_product_block(
                image_url=image_url,
                product_url=product_url,
                category="mens",
                brand="BBC",
            )

            new_blocks.append(block)
            existing_links.add(product_url)
            print("Added:", product_url)

    except Exception as error:
        print("Could not import: BBC")
        print(error)

    return new_blocks


def import_dickies(existing_links):
    print("Checking: Dickies")

    new_blocks = []
    base_url = "https://dickies.eu"

    sources = [
        {
            "url": "https://dickies.eu/en-gb/collections/men-new-arrivals",
            "category": "mens",
        },
        {
            "url": "https://dickies.eu/en-gb/collections/women-new-arrivals",
            "category": "womens",
        },
    ]

    for source in sources:
        category = source["category"]
        print(f"Checking Dickies {category} products")

        try:
            response = get_with_retries(source["url"])

            if response is None:
                print(f"No response received for Dickies {category}.")
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            for link_tag in soup.find_all("a", href=True):
                href = link_tag.get("href", "")

                if "/products/" not in href:
                    continue

                product_url = (
                    href if href.startswith("http")
                    else base_url + href
                )
                product_url = product_url.split("?")[0]

                if product_url in existing_links:
                    continue

                image_url = find_image_for_product_link(link_tag)
                image_url = clean_image_url(image_url, base_url)

                if not image_url:
                    continue

                block = make_product_block(
                    image_url=image_url,
                    product_url=product_url,
                    category=category,
                    brand="Dickies",
                )

                new_blocks.append(block)
                existing_links.add(product_url)
                print("Added:", product_url)

        except Exception as error:
            print(f"Could not import Dickies {category}")
            print(error)

        time.sleep(random.randint(10, 20))

    return new_blocks



def import_stussy(existing_links):
    print("Checking: Stüssy")

    new_blocks = []
    collection_url = "https://uk.stussy.com/collections/new-arrivals"
    base_url = "https://uk.stussy.com"

    try:
        response = get_with_retries(collection_url)

        if response is None:
            print("No response received for Stüssy.")
            return new_blocks

        soup = BeautifulSoup(response.text, "html.parser")

        for link_tag in soup.find_all("a", href=True):
            href = link_tag.get("href", "")

            if "/products/" not in href:
                continue

            product_url = (
                href if href.startswith("http")
                else base_url + href
            )
            product_url = product_url.split("?")[0]

            if product_url in existing_links:
                continue

            image_url = find_image_for_product_link(link_tag)
            image_url = clean_image_url(image_url, base_url)

            if not image_url:
                continue

            block = make_product_block(
                image_url=image_url,
                product_url=product_url,
                category="mens",
                brand="Stüssy",
            )

            new_blocks.append(block)
            existing_links.add(product_url)
            print("Added:", product_url)

    except Exception as error:
        print("Could not import: Stüssy")
        print(error)

    return new_blocks

def import_motel_rocks(existing_links):
    print("Checking: Motel Rocks")

    new_blocks = []
    url = "https://www.motelrocks.com/collections/new-in"
    base_url = "https://www.motelrocks.com"

    try:
        response = SESSION.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for link_tag in soup.find_all("a", href=True):
            href = link_tag.get("href", "")

            if "/products/" not in href:
                continue

            product_url = (
                href if href.startswith("http")
                else base_url + href
            )
            product_url = product_url.split("?")[0]

            if product_url in existing_links:
                continue

            image_url = find_image_for_product_link(link_tag)
            image_url = clean_image_url(image_url, base_url)

            if not image_url:
                continue

            block = make_product_block(
                image_url=image_url,
                product_url=product_url,
                category="womens",
                brand="Motel Rocks",
            )

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
    base_url = "https://www.carhartt-wip.com"

    try:
        response = SESSION.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for link_tag in soup.find_all("a", href=True):
            href = link_tag.get("href", "")

            if "/en-gb/p/" not in href:
                continue

            product_url = (
                href if href.startswith("http")
                else base_url + href
            )
            product_url = product_url.split("?")[0]

            if product_url in existing_links:
                continue

            image_url = find_image_for_product_link(link_tag)
            image_url = clean_image_url(image_url, base_url)

            if not image_url:
                continue

            block = make_product_block(
                image_url=image_url,
                product_url=product_url,
                category="mens",
                brand="Carhartt",
            )

            new_blocks.append(block)
            existing_links.add(product_url)
            print("Added:", product_url)

    except Exception as error:
        print("Could not import: Carhartt")
        print(error)

    return new_blocks


def push_to_github():
    print("Pushing updates to GitHub...")

    subprocess.run(
        ["git", "add", "products.js"],
        cwd=WEBSITE_FOLDER,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Daily product update"],
        cwd=WEBSITE_FOLDER,
        check=True,
    )
    subprocess.run(
        ["git", "push"],
        cwd=WEBSITE_FOLDER,
        check=True,
    )

    print("GitHub updated. Netlify should redeploy automatically.")


def import_products():
    existing_blocks, existing_links = read_existing_products()
    new_blocks = []

    new_blocks += import_shopify_products(existing_links)
    new_blocks += import_bbc(existing_links)
    new_blocks += import_dickies(existing_links)
    new_blocks += import_stussy(existing_links)
    new_blocks += import_motel_rocks(existing_links)
    new_blocks += import_carhartt(existing_links)

    if not new_blocks:
        print("Done. Added 0 new products.")
        print("No new products found, so nothing was pushed to GitHub.")
        return

    all_blocks = new_blocks + existing_blocks

    new_content = "const products = [\n\n"
    new_content += "\n\n".join(all_blocks)
    new_content += "\n\n];\n"

    with open(PRODUCTS_FILE, "w", encoding="utf-8") as file:
        file.write(new_content)

    print(f"Done. Added {len(new_blocks)} new products.")
    push_to_github()


if __name__ == "__main__":
    import_products()