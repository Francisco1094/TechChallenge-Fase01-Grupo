import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3

from monitoring.middleware import BusinessEventTracker
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

    try:
        from monitoring import BusinessEventTracker
    except ImportError:
        # Fallback se não conseguir importar
        class BusinessEventTracker:
            @staticmethod
            def track_scraping_start():
                print("Scraping started")
            @staticmethod
            def track_scraping_progress(page, books, total=None):
                print(f"Page {page} completed: {books} books")
            @staticmethod
            def track_scraping_complete(total, duration):
                print(f"Scraping completed: {total} books in {duration:.2f}s")
    
    all_books = []
    page_url = base_url + "catalogue/page-1.html"
    page_number = 1

    BusinessEventTracker.track_scraping_start()
    start_time = time.time()

    while True:
        print(f"Scraping {page_url}")
        response = requests.get(page_url, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")
        books = get_book_data(soup)
        all_books.extend(books)

        BusinessEventTracker.track_scraping_progress(
            page_number=page_number,
            books_found=len(books),
            total_pages=50
        )

        next_button = soup.select_one("li.next a")
        if next_button:
            next_href = next_button["href"]
            page_url = urljoin(page_url, next_href)
            page_number += 1
        else:
            break
    
    duration = time.time() - start_time
    BusinessEventTracker.track_scraping_complete(
        total_books=len(all_books),
        duration_seconds=duration
    )

    return all_books

def scrape_all_books_with_progress(callback_func=None):
    """Scraping com callback para atualizar progresso em tempo real"""
    
    try:
        from monitoring import BusinessEventTracker
    except ImportError:
        class BusinessEventTracker:
            @staticmethod
            def track_scraping_start():
                pass
            @staticmethod
            def track_scraping_progress(*args):
                pass
            @staticmethod
            def track_scraping_complete(*args):
                pass
    
    all_books = []
    page_url = base_url + "catalogue/page-1.html"
    page_number = 1
    
    BusinessEventTracker.track_scraping_start()
    start_time = time.time()
    
    while True:
        print(f"Scraping {page_url}")
        response = requests.get(page_url, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")
        books = get_book_data(soup)
        all_books.extend(books)
        
        if callback_func:
            callback_func(page_number, len(books), len(all_books))
        
        BusinessEventTracker.track_scraping_progress(
            page_number=page_number,
            books_found=len(books),
            total_pages=50
        )
        
        next_button = soup.select_one("li.next a")
        if next_button:
            next_href = next_button["href"]
            page_url = urljoin(page_url, next_href)
            page_number += 1
        else:
            break
    
    duration = time.time() - start_time
    BusinessEventTracker.track_scraping_complete(
        total_books=len(all_books),
        duration_seconds=duration
    )
    
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
