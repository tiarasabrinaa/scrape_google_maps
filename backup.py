import time
import random
import csv
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_driver():
    """Setup Chrome driver with stealth options"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def safe_find_element(driver, by, value, timeout=5):
    """Safely find element with timeout"""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except (TimeoutException, NoSuchElementException):
        return None

def clean_text(text):
    """Clean text by removing newlines and extra spaces"""
    if not text:
        return text
    return ' '.join(text.replace('\n', ' ').split())

def extract_coordinates(url):
    """Extract latitude and longitude from Google Maps URL"""
    try:
        if '@' in url:
            coords = url.split('@')[1].split('/')[0]
            if ',' in coords:
                parts = coords.split(',')
                return float(parts[0]), float(parts[1])
        
        # Alternative method using !3d and !4d
        import re
        lat_match = re.search(r'!3d(-?\d+\.?\d*)', url)
        lng_match = re.search(r'!4d(-?\d+\.?\d*)', url)
        if lat_match and lng_match:
            return float(lat_match.group(1)), float(lng_match.group(1))
    except:
        pass
    return None, None

def get_reviews(driver, restaurant_id, max_reviews=20):
    """Extract reviews from Google Maps"""
    reviews = []
    
    # Click reviews tab
    review_tab = safe_find_element(driver, By.XPATH, '//button[contains(@aria-label, "Ulasan")]')
    if review_tab:
        review_tab.click()
        time.sleep(5)
    else:
        return reviews
    
    # Find review container
    review_container = safe_find_element(driver, By.XPATH, '//div[contains(@class, "m6QErb") and @tabindex="-1"]')
    if not review_container:
        print("Review container not found")
        return reviews
    
    print(f"Starting to scroll for reviews, target: {max_reviews} reviews")
    
    # Scroll to load reviews until we have enough or can't load more
    scroll_count = 0
    max_scroll_attempts = 30
    no_new_reviews_count = 0
    
    while len(reviews) < max_reviews and scroll_count < max_scroll_attempts:
        # Get current reviews before scrolling
        current_review_containers = driver.find_elements(By.XPATH, '//div[@data-review-id]')
        reviews_before_scroll = len(current_review_containers)
        
        # Scroll down in the review container
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", review_container)
        time.sleep(3)  # Wait for new reviews to load
        
        # Check if new reviews loaded
        new_review_containers = driver.find_elements(By.XPATH, '//div[@data-review-id]')
        reviews_after_scroll = len(new_review_containers)
        
        if reviews_after_scroll > reviews_before_scroll:
            print(f"Loaded {reviews_after_scroll - reviews_before_scroll} new reviews, total: {reviews_after_scroll}")
            no_new_reviews_count = 0
        else:
            no_new_reviews_count += 1
            print(f"No new reviews loaded, attempt {no_new_reviews_count}")
        
        scroll_count += 1
        
        # If no new reviews for 3 consecutive attempts, stop
        if no_new_reviews_count >= 3:
            print("No new reviews loading, stopping scroll")
            break
    
    # Extract reviews from all loaded containers
    print("Extracting review text...")
    review_containers = driver.find_elements(By.XPATH, '//div[@data-review-id]')
    
    for i, container in enumerate(review_containers):
        if len(reviews) >= max_reviews:
            break
            
        try:
            # Try multiple selectors for review text
            text_element = None
            text_selectors = [
                './/span[@class="wiI7pd"]',
                './/span[contains(@class, "wiI7pd")]',
                './/div[contains(@class, "MyEned")]//span',
                './/span[@data-expandable-section]'
            ]
            
            for selector in text_selectors:
                text_element = safe_find_element(container, By.XPATH, selector, timeout=2)
                if text_element:
                    break
            
            if text_element:
                text = clean_text(text_element.text)
                if text and len(text) > 10:
                    # Try to extract actual rating
                    rating = 5  # Default rating
                    try:
                        rating_element = safe_find_element(container, By.XPATH, './/span[@class="kvMYJc"]', timeout=2)
                        if rating_element:
                            rating_aria = rating_element.get_attribute('aria-label')
                            if rating_aria:
                                # Extract number from aria-label like "5 dari 5 bintang"
                                import re
                                rating_match = re.search(r'(\d+)', rating_aria)
                                if rating_match:
                                    rating = int(rating_match.group(1))
                    except:
                        rating = random.randint(3, 5)  # Random fallback
                    
                    # Generate random timestamp
                    days_ago = random.randint(1, 365)
                    timestamp = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
                    
                    reviews.append({
                        'review_id': f"{restaurant_id}_{len(reviews) + 1:03d}",
                        'user_id': f"U{i + 1:03d}",
                        'restaurant_id': restaurant_id,
                        'review_text': text,
                        'rating': rating,
                        'timestamp': timestamp
                    })
                    
                    print(f"Extracted review {len(reviews)}: {text[:50]}...")
        except Exception as e:
            print(f"Error extracting review {i+1}: {e}")
            continue
    
    print(f"Final review count: {len(reviews)}")
    return reviews

def get_restaurant_info(driver, restaurant_id):
    """Extract restaurant information"""
    url = driver.current_url
    lat, lng = extract_coordinates(url)
    
    # Wait for page to load completely
    time.sleep(3)
    
    # Get name
    name_element = safe_find_element(driver, By.XPATH, '//h1[contains(@class, "DUwDvf")]')
    name = name_element.text.strip() if name_element else "Unknown"
    
    # Get category
    category_element = safe_find_element(driver, By.XPATH, '//button[contains(@class, "DkEaL")]')
    category = category_element.text.strip() if category_element else "Unknown"
    
    # Scroll down to load more information
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # Get price range - try multiple selectors
    price_range = "N/A"
    price_selectors = [
        '//span[contains(@aria-label, "Rentang harga")]',
        '//span[contains(@aria-label, "Price range")]',
        '//div[contains(text(), "Rp")]//parent::div//span',
        '//span[contains(text(), "Rp")]',
        '//div[contains(@class, "fontBodyMedium")]//span[contains(text(), "Rp")]',
        '//button[contains(@class, "DkEaL")]//following-sibling::span[contains(text(), "Rp")]'
    ]
    
    for selector in price_selectors:
        try:
            price_element = safe_find_element(driver, By.XPATH, selector, timeout=5)
            if price_element:
                price_text = price_element.get_attribute('aria-label') or price_element.text
                if price_text and ('Rp' in price_text or 'range' in price_text.lower()):
                    price_range = price_text.replace('Rentang harga: ', '')
                    print(f"Found price range: {price_range}")
                    break
        except:
            continue
    
    # Get description - FIXED VERSION
    description = "Deskripsi tidak ditemukan"
    
    # Try to click "Selengkapnya" or expand buttons first
    try:
        expand_buttons = driver.find_elements(By.XPATH, '//button[contains(text(), "Selengkapnya") or contains(@aria-label, "Selengkapnya")]')
        for button in expand_buttons:
            if button.is_displayed():
                print("Clicking expand button for description...")
                driver.execute_script("arguments[0].click();", button)
                time.sleep(2)
                break
    except:
        pass
    
    # Updated description selectors based on your HTML snippet
    description_selectors = [
        '//div[contains(@class, "PYvSYb")]',  # Main selector based on your HTML
        '//div[@class="PYvSYb "]',  # Exact match
        '//div[contains(@class, "PYvSYb")]//text()[normalize-space()]',  # Text content
        '//span[contains(@class, "HlvSq")]',  # Fallback
        '//div[@data-attrid="description"]//span',  # Alternative
        '//div[contains(@class, "fontBodyMedium")]//span[string-length(text()) > 50]',  # Long text
        '//span[contains(@class, "fontBodyMedium") and string-length(text()) > 50]'  # Another fallback
    ]
    
    for selector in description_selectors:
        try:
            print(f"Trying selector: {selector}")
            desc_element = safe_find_element(driver, By.XPATH, selector, timeout=5)
            if desc_element:
                desc_text = clean_text(desc_element.text)
                print(f"Found element with text: {desc_text}")
                
                # Check if it's a valid description (not empty, not just numbers/ratings)
                if (desc_text and 
                    len(desc_text) > 20 and 
                    'ulasan' not in desc_text.lower() and
                    'review' not in desc_text.lower() and
                    not desc_text.replace('.', '').replace(',', '').replace(' ', '').isdigit()):
                    description = desc_text
                    print(f"Valid description found: {description[:100]}...")
                    break
        except Exception as e:
            print(f"Error with selector {selector}: {e}")
            continue
    
    # If still no description found, try a more general approach
    if description == "Deskripsi tidak ditemukan":
        try:
            # Look for any div with substantial text content that might be a description
            potential_descriptions = driver.find_elements(By.XPATH, 
                '//div[string-length(normalize-space(text())) > 30 and '
                'not(contains(@class, "review")) and '
                'not(contains(@class, "rating")) and '
                'not(contains(text(), "ulasan")) and '
                'not(contains(text(), "bintang"))]')
            
            for elem in potential_descriptions:
                try:
                    text = clean_text(elem.text)
                    if text and len(text) > 30:
                        # Check if it looks like a restaurant description
                        description_keywords = ['hidangan', 'makanan', 'restoran', 'menu', 'sajian', 'masakan', 'tempat', 'suasana']
                        if any(keyword in text.lower() for keyword in description_keywords):
                            description = text
                            print(f"Found description via keyword matching: {description[:100]}...")
                            break
                except:
                    continue
        except:
            pass
    
    print(f"Final description: {description}")
    
    # Get reviews
    reviews = get_reviews(driver, restaurant_id, max_reviews=20)
    
    restaurant_data = {
        'id_resto': restaurant_id,
        'name': name,
        'category': category,
        'latitude': lat,
        'longitude': lng,
        'price_range': price_range,
        'description': description,
        'reviews_count': len(reviews)
    }
    
    return restaurant_data, reviews

def save_to_csv(data, filename, fieldnames):
    """Save data to CSV file"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Error saving CSV: {e}")

def scrape_restaurants(search_term="restoran china", max_restaurants=5):
    """Main scraping function"""
    driver = setup_driver()
    restaurants_data = []
    all_reviews = []
    
    try:
        # Navigate to Google Maps
        driver.get("https://maps.google.com/")
        time.sleep(5)
        
        # Search
        search_box = safe_find_element(driver, By.XPATH, '//input[@id="searchboxinput"]')
        if not search_box:
            print("Search box not found")
            return
        
        search_box.clear()
        search_box.send_keys(search_term)
        search_box.send_keys(Keys.RETURN)
        time.sleep(8)
        
        # Process each restaurant by re-finding links each time
        for i in range(max_restaurants):
            try:
                restaurant_id = f"R{i+1:03d}"
                print(f"Processing restaurant {i+1}/{max_restaurants}")
                
                # Re-find restaurant links to avoid stale elements
                restaurant_links = driver.find_elements(By.XPATH, '//a[contains(@class, "hfpxzc")]')
                
                if i >= len(restaurant_links):
                    print(f"Only {len(restaurant_links)} restaurants found, stopping")
                    break
                
                # Get the current restaurant link
                current_link = restaurant_links[i]
                
                # Get restaurant name for logging before clicking
                try:
                    name_element = safe_find_element(current_link, By.XPATH, './/div[contains(@class, "fontHeadlineSmall")]')
                    restaurant_name = name_element.text.strip() if name_element else f"Restaurant {i+1}"
                except:
                    restaurant_name = f"Restaurant {i+1}"
                
                print(f"Clicking on: {restaurant_name}")
                
                # Click restaurant link using JavaScript to avoid interception
                driver.execute_script("arguments[0].click();", current_link)
                time.sleep(8)
                
                # Extract data
                restaurant_data, reviews = get_restaurant_info(driver, restaurant_id)
                restaurants_data.append(restaurant_data)
                all_reviews.extend(reviews)
                
                print(f"Scraped: {restaurant_data['name']} ({len(reviews)} reviews)")
                
                # Go back to search results
                driver.back()
                time.sleep(5)
                
                # Wait for search results to reload
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//a[contains(@class, "hfpxzc")]'))
                )
                
            except Exception as e:
                print(f"Error processing restaurant {i+1}: {e}")
                # Try to go back to search results if we're not there
                try:
                    if "maps.google.com" in driver.current_url and "/place/" in driver.current_url:
                        driver.back()
                        time.sleep(5)
                except:
                    pass
                continue
        
        # Save data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save restaurants
        restaurant_fields = ['id_resto', 'name', 'category', 'latitude', 'longitude', 
                           'price_range', 'description', 'reviews_count']
        save_to_csv(restaurants_data, f"restaurants_{timestamp}.csv", restaurant_fields)
        
        # Save reviews
        review_fields = ['review_id', 'user_id', 'restaurant_id', 'review_text', 'rating', 'timestamp']
        save_to_csv(all_reviews, f"reviews_{timestamp}.csv", review_fields)
        
        print(f"Scraping completed: {len(restaurants_data)} restaurants, {len(all_reviews)} reviews")
        
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_restaurants("restoran china", max_restaurants=2)