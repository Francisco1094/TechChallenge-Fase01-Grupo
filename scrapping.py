import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

base_url= "https://books.toscrape.com/"

def get_book_data(soup):
    books = []
    
    for article in soup.select("article.product_pod"):
        title = article.h3.a["title"]
        price = article.select_one(".price_color").text
        rating_class = article.select_one(".star-rating")["class"][-1]
        availability = article.select_one(".instock.availability").text.strip()
        detail_href = article.h3.a["href"]
        detail_url = urljoin(base_url + "catalogue/", detail_href)


        # Get category from detail page
        detail_response = requests.get(detail_url, verify=False)
        detail_soup = BeautifulSoup(detail_response.text,"html.parser")
        category = detail_soup.select_one("ul.breadcrumb li:nth-of-type(3) a").text
        
        image_relative = article.img["src"]
        image_url = urljoin(base_url, image_relative)


        books.append({
            "title": title,
            "price": price,
            "rating": rating_class,
            "availability": availability,
            "category": category,
            "image_url": image_url
        })

    return books

def scrape_all_books():
    all_books = []
    page_url = base_url +"catalogue/page-1.html"

    while True:
        print(f"Scraping {page_url}")
        response = requests.get(page_url, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")
        books = get_book_data(soup)
        all_books.extend(books)

        

        next_button = soup.select_one("li.next a")
        if next_button:
            next_href = next_button["href"]
            page_url = urljoin(page_url, next_href)
        else:
            break

    return all_books

def save_to_csv(books, filename):
    import csv
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Title", "Price", "Rating", "Availability", "Category", "Image URL"])
        for book in books:
            writer.writerow([
                book["title"],
                book["price"],
                book["rating"],
                book["availability"],
                book["category"],
                book["image_url"]
            ])
