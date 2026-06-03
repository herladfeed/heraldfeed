import re
import requests

PRODUCTS_FILE = "products.js"

SALE_PAGES = [
    "https://bbcicecream.eu/collections/sale",
]

def get_sale_page_links():
    sale_links = set()

    for page in SALE_PAGES:
        html = requests.get(page, timeout=20).text

        links = re.findall(r'href="(/products/[^"]+)"', html)

        for link in links:
            full_link = "https://bbcicecream.eu" + link.split("?")[0]
            sale_links.add(full_link)

    return sale_links


def main():
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
        content = file.read()

    sale_links = get_sale_page_links()

    product_blocks = re.findall(r"\{[\s\S]*?\},", content)

    kept_products = []

    for block in product_blocks:
        link_match = re.search(r'link:\s*"([^"]+)"', block)
        sale_match = re.search(r"sale:\s*true", block)

        if not link_match:
            kept_products.append(block)
            continue

        product_link = link_match.group(1).split("?")[0]

        if sale_match:
            if product_link in sale_links:
                kept_products.append(block)
            else:
                print("Removed:", product_link)
        else:
            kept_products.append(block)

    new_content = "const products = [\n\n"
    new_content += "\n\n".join(kept_products)
    new_content += "\n\n];"

    with open(PRODUCTS_FILE, "w", encoding="utf-8") as file:
        file.write(new_content)

    print("Done. products.js updated.")

main()