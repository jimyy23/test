import requests
from bs4 import BeautifulSoup
import csv
import time
import re

# Configuration
BASE_URL = "https://freedns.afraid.org/domain/registry/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
}

def parse_age(age_text):
    """Convert age text like '9013 days ago (03/15/2001)' to date"""
    match = re.search(r'\(([^)]+)\)', age_text)
    return match.group(1) if match else age_text

def scrape_page(url):
    """Scrape a single page and return list of domains"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        domains = []
        rows = soup.find_all('tr', class_=['trl', 'trd'])
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 4:
                # Extract domain name
                domain_cell = cells[0]
                domain_link = domain_cell.find('a')
                if domain_link:
                    domain = domain_link.text.strip()
                    
                    # Extract other info
                    status = cells[1].text.strip()
                    owner_link = cells[2].find('a')
                    owner = owner_link.text.strip() if owner_link else cells[2].text.strip()
                    age = parse_age(cells[3].text.strip())
                    
                    domains.append({
                        'domain': domain,
                        'status': status,
                        'owner': owner,
                        'date': age
                    })
        
        return domains
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def get_total_pages(url):
    """Get total number of pages from the first page"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find "Page X of Y" text
        page_text = soup.find('font', string=re.compile(r'Page.*of'))
        if page_text:
            match = re.search(r'of (\d+)', page_text.text)
            if match:
                return int(match.group(1))
        return 1
    except Exception as e:
        print(f"Error getting total pages: {e}")
        return 1

def main():
    print("Starting FreeDNS domain scraper...")
    
    # Get total pages
    total_pages = get_total_pages(BASE_URL)
    print(f"Total pages to scrape: {total_pages}")
    
    all_domains = []
    
    # Scrape all pages
    for page in range(1, total_pages + 1):
        if page == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}page-{page}.html"
        
        print(f"Scraping page {page}/{total_pages}...")
        domains = scrape_page(url)
        all_domains.extend(domains)
        
        # Be polite - add delay between requests
        if page < total_pages:
            time.sleep(1)
    
    print(f"\nTotal domains scraped: {len(all_domains)}")
    
    # Write to domains.txt (just domain names)
    print("Writing domains.txt...")
    with open('domains.txt', 'w', encoding='utf-8') as f:
        for domain in all_domains:
            f.write(domain['domain'] + '\n')
    
    # Write to domains.csv (all info)
    print("Writing domains.csv...")
    with open('domains.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['domain', 'status', 'owner', 'date'])
        writer.writeheader()
        writer.writerows(all_domains)
    
    print("\nScraping complete!")
    print(f"- domains.txt: {len(all_domains)} domains")
    print(f"- domains.csv: {len(all_domains)} entries with full details")

if __name__ == "__main__":
    main()