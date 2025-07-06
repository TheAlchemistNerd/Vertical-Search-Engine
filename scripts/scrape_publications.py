# scripts/scrape_publications.py
import json
import requests
from time import sleep
from random import randint
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
import re

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# Add the project root to the Python path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import Publication, Author, PublicationFTS, Base
from app.database import engine, SessionLocal, init_db

# Ensure database tables are created (and FTS table is handled)
init_db()

BASE_URL = 'https://pureportal.coventry.ac.uk/en/organisations/school-of-economics-finance-and-accounting/publications/'
MAX_PAGES = 16 # Adjust based on how many pages you want to scrape, dynamic detection will cap this.

# --- Selenium Setup ---
def setup_driver():
    """Configures and returns a headless Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode (no GUI)
    chrome_options.add_argument("--no-sandbox") # Required for some environments (e.g., Docker)
    chrome_options.add_argument("--disable-dev-shm-usage") # Overcomes limited resource problems
    # Add a realistic User-Agent to further mimic a real browser
    chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Use ChromeDriverManager to automatically download and manage ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# --- End Selenium Setup ---


def get_total_pages(soup):
    """
    Attempts to find the total number of pages from the pagination links,
    considering the ?page=X typically means actual_page_number = X + 1.
    """
    pagination_elements = soup.find_all(['a', 'span'], class_=['step', 'currentStep'])
    
    max_actual_page_num_found = 1 

    for element in pagination_elements:
        try:
            if element.name == 'a' and 'step' in element.get('class', []):
                href = element.get('href')
                if href:
                    match = re.search(r'\?page=(\d+)$', href)
                    if match:
                        actual_page_from_href = int(match.group(1)) + 1
                        if actual_page_from_href > max_actual_page_num_found:
                            max_actual_page_num_found = actual_page_from_href
                        
            elif element.name == 'span' and 'currentStep' in element.get('class', []):
                current_page_text = int(element.get_text(strip=True))
                if current_page_text > max_actual_page_num_found:
                    max_actual_page_num_found = current_page_text
            
            text_content = element.get_text(strip=True)
            if text_content.isdigit():
                page_num_from_text = int(text_content)
                if page_num_from_text > max_actual_page_num_found:
                    max_actual_page_num_found = page_num_from_text

        except (ValueError, TypeError):
            continue 
            
    return max_actual_page_num_found

def scrape_publications():
    """
    Scrapes publication data from PurePortal and stores it in the database using Selenium.
    """
    driver = None # Initialize driver to None
    db_session = SessionLocal()
    publications_added_count = 0
    publications_skipped_count = 0

    try:
        driver = setup_driver()
        wait = WebDriverWait(driver, 20) # Wait up to 20 seconds for elements to appear

        # Fetch the BASE_URL directly for the first page (page 1)
        print("Fetching initial page (page 1) to determine total pages and scrape first batch...")
        driver.get(BASE_URL)
        
        # Wait for the main content to load. Adjust locator if needed.
        # Assuming 'list-results' is the UL containing publication items
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-results")))
        
        initial_soup = BeautifulSoup(driver.page_source, "html.parser")
        total_pages = get_total_pages(initial_soup)
        print(f"Total pages detected: {total_pages}. Scraping up to {min(total_pages, MAX_PAGES)} pages.")
        
        # Process the first page (page 1), which we just fetched using BASE_URL
        print(f"Processing page 1/{min(total_pages, MAX_PAGES)}: {BASE_URL}")
        processed_count_on_page, skipped_count_on_page = process_page_documents(initial_soup, db_session)
        publications_added_count += processed_count_on_page
        publications_skipped_count += skipped_count_on_page
        db_session.commit() 
        print(f"Page 1 processed. New publications added this run: {publications_added_count}. Skipped (existing): {publications_skipped_count}")

        # Loop for subsequent pages starting from page 2
        for page_num_actual in range(2, min(total_pages, MAX_PAGES) + 1): 
            url_page_param = page_num_actual - 1 
            url = f"{BASE_URL}?page={url_page_param}"
            print(f"Scraping page {page_num_actual}/{min(total_pages, MAX_PAGES)}: {url}")
            try:
                driver.get(url)
                # Wait for the main content to load on subsequent pages
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-results")))
            except Exception as e:
                print(f"Error fetching {url} with Selenium: {e}")
                continue 

            sleep(randint(5, 10)) # Shorter sleep as Selenium is slower, but still polite

            soup = BeautifulSoup(driver.page_source, "html.parser")
            processed_count_on_page, skipped_count_on_page = process_page_documents(soup, db_session)
            publications_added_count += processed_count_on_page
            publications_skipped_count += skipped_count_on_page

            db_session.commit() 
            print(f"Page {page_num_actual} processed. New publications added this run: {publications_added_count}. Skipped (existing): {publications_skipped_count}")

    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        db_session.rollback()
    finally:
        if driver:
            driver.quit() # Ensure the browser is closed
        db_session.close()
        print(f"Scraping finished. Total new publications added in this run: {publications_added_count}.")
        print(f"Total publications skipped (already in DB): {publications_skipped_count}.")

def process_page_documents(soup, db_session):
    """
    Helper function to process documents on a single page.
    Returns (added_count, skipped_count) for the page.
    """
    added_count = 0
    skipped_count = 0

    documents = soup.find_all("li", {"class": "list-result-item"})

    if not documents:
        return 0, 0

    for doc in documents:
        title_h3 = doc.find("h3", {"class": "title"})
        if not title_h3:
            continue

        pub_link_tag = title_h3.find('a', {'class':'link'})
        pub_title_span = title_h3.find('span')

        if not pub_link_tag or not pub_title_span:
            continue

        pub_link = pub_link_tag.get('href')
        pub_title = pub_title_span.text.strip()

        authors_div = doc.find('div', {'class': 'relations persons'})
        current_authors = []
        if authors_div:
            author_tags = authors_div.find_all('a', {'class': 'link person'})
            for author_tag in author_tags:
                author_name = author_tag.find('span').text.strip()
                author_link = author_tag.get('href')

                author_obj = db_session.query(Author).filter_by(name=author_name).first()
                if not author_obj:
                    author_obj = Author(name=author_name, author_link=author_link)
                    db_session.add(author_obj)
                    db_session.flush()
                current_authors.append(author_obj)
        
        publication_year = None
        year_div = doc.find('div', class_='search-result-group')
        if year_div:
            try:
                year_text = year_div.get_text(strip=True)
                match = re.search(r'\b(19|20)\d{2}\b', year_text) 
                if match:
                    publication_year = int(match.group(0))
            except (ValueError, TypeError):
                pass
        
        if publication_year is None:
            date_span = doc.find('span', class_='date')
            if date_span:
                try:
                    year_text_from_date = date_span.text.strip()
                    match = re.search(r'\b(19|20)\d{2}\b', year_text_from_date)
                    if match:
                        publication_year = int(match.group(0))
                except (ValueError, TypeError):
                    pass

        abstract_text = None
        # Abstract extraction remains the same: it's not clearly visible in the list view HTML/image.
        # To get the abstract, you would need to visit each individual publication link.

        existing_publication = db_session.query(Publication).filter_by(publication_link=pub_link).first()

        if existing_publication:
            for author_obj in current_authors:
                if author_obj not in existing_publication.authors:
                    existing_publication.authors.append(author_obj)
            skipped_count += 1
        else:
            publication = Publication(
                title=pub_title,
                publication_link=pub_link,
                publication_year=publication_year,
                abstract=abstract_text
            )
            publication.authors.extend(current_authors)
            db_session.add(publication)
            db_session.flush()

            fts_entry = PublicationFTS(
                rowid=publication.id,
                title=publication.title,
                abstract=publication.abstract or ""
            )
            db_session.add(fts_entry)
            db_session.flush()

            added_count += 1

    return added_count, skipped_count


if __name__ == "__main__":
    scrape_publications()
