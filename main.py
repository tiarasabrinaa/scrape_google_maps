import time
import random
import csv
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

def setup_driver():
    """Setup Chrome driver with enhanced stealth"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def random_delay(min_seconds=1, max_seconds=3):
    """Add random delay to mimic human behavior"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def safe_find_element(driver, by, value, timeout=10):
    """Safely find element with timeout"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except (TimeoutException, NoSuchElementException):
        return None

def clean_review_text(text):
    """Clean review text to remove newlines and extra spaces"""
    if not text:
        return text
    cleaned = text.replace('\n', ' ').replace('\r', ' ')
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()

def generate_random_timestamp():
    """Generate random timestamp within the last year"""
    now = datetime.now()
    days_ago = random.randint(1, 365)
    random_date = now - timedelta(days=days_ago)
    random_hours = random.randint(0, 23)
    random_minutes = random.randint(0, 59)
    random_seconds = random.randint(0, 59)
    random_timestamp = random_date.replace(
        hour=random_hours,
        minute=random_minutes,
        second=random_seconds,
        microsecond=0
    )
    return random_timestamp.strftime("%Y-%m-%d %H:%M:%S")

def get_rating_from_review_container(container):
    """Extract rating from review container"""
    try:
        rating_elements = container.find_elements(By.XPATH, './/span[@aria-label]')
        for element in rating_elements:
            aria_label = element.get_attribute('aria-label')
            if aria_label and ('star' in aria_label.lower() or 'rated' in aria_label.lower()):
                import re
                numbers = re.findall(r'\d+', aria_label)
                if numbers:
                    rating = int(numbers[0])
                    if 1 <= rating <= 5:
                        return rating
        return random.randint(3, 5)
    except:
        return random.randint(3, 5)

def extract_coordinates_from_url(url):
    """Extract latitude and longitude from Google Maps URL"""
    try:
        if '@' in url:
            coords_part = url.split('@')[1].split('/')[0]
            if ',' in coords_part:
                parts = coords_part.split(',')
                if len(parts) >= 2:
                    lat = float(parts[0])
                    lng = float(parts[1])
                    return lat, lng
        
        if '!3d' in url and '!4d' in url:
            import re
            lat_match = re.search(r'!3d(-?\d+\.?\d*)', url)
            lng_match = re.search(r'!4d(-?\d+\.?\d*)', url)
            if lat_match and lng_match:
                lat = float(lat_match.group(1))
                lng = float(lng_match.group(1))
                return lat, lng
    except Exception as e:
        print(f"Error extracting coordinates: {e}")
    return None, None

def get_reviews(driver, restaurant_id, global_review_counter, max_reviews=15):
    """Extract reviews from Google Maps - max 10 unique reviews"""
    reviews = []
    
    try:
        # Klik tab "Ulasan"
        review_tab = safe_find_element(driver, By.XPATH, 
            '//button[@role="tab" and contains(@aria-label, "Ulasan")]')
        
        if not review_tab:
            review_tab = safe_find_element(driver, By.XPATH,
                '//button[contains(@class, "hh2c6") and contains(., "Ulasan")]')
        
        if review_tab:
            review_tab.click()
            print("Berhasil klik tab Ulasan")
            random_delay(3, 5)
        else:
            print("Gagal menemukan tab Ulasan")
            return reviews, global_review_counter
        
        # Scroll untuk memuat lebih banyak ulasan (tapi tidak terlalu banyak)
        print("Scroll ulasan untuk memuat lebih banyak...")
        try:
            review_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "m6QErb") and contains(@class, "DxyBCb")]'))
            )
            
            # Scroll 3-4 kali saja untuk memuat ulasan tambahan
            for i in range(2):
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", review_container)
                random_delay(2, 3)
                print(f"Scroll ulasan ke-{i+1}")
        except:
            print("Gagal scroll ulasan, lanjut dengan ulasan yang sudah ada")
        
        # Ambil ulasan yang sudah ter-load
        review_containers = driver.find_elements(By.XPATH, '//div[@data-review-id]')
        print(f"Menemukan {len(review_containers)} kontainer ulasan")
        
        user_counter = 1
        unique_reviews = set()
        
        for container in review_containers[:20]:  # Ambil maksimal 20 kontainer pertama
            if len(reviews) >= max_reviews:
                break
                
            try:
                review_text_element = safe_find_element(container, By.XPATH, 
                    './/span[@class="wiI7pd" or contains(@class, "MyEned")]')
                review_text = review_text_element.text.strip() if review_text_element else ""
                
                if review_text and len(review_text) > 10:
                    clean_text = clean_review_text(review_text)
                    
                    # Cek duplikat berdasarkan text
                    if clean_text not in unique_reviews:
                        unique_reviews.add(clean_text)
                        rating = get_rating_from_review_container(container)
                        timestamp = generate_random_timestamp()
                        global_review_counter += 1
                        
                        reviews.append({
                            'review_id': f"{global_review_counter:03d}",
                            'user_id': f"{user_counter:03d}",
                            'restaurant_id': restaurant_id,
                            'review_text': clean_text,
                            'rating': rating,
                            'timestamp': timestamp
                        })
                        print(f"Ulasan #{global_review_counter}: Rating {rating}/5, {clean_text[:50]}...")
                        user_counter += 1
                        
            except Exception as e:
                print(f"Error mengambil ulasan: {e}")
                continue
        
        print(f"Total ulasan yang berhasil diambil: {len(reviews)}")
        
    except Exception as e:
        print(f"Error saat mengambil ulasan: {e}")
    
    return reviews, global_review_counter

def get_restaurant_info(driver, restaurant_id, global_review_counter):
    """Extract restaurant information from Google Maps"""
    
    current_url = driver.current_url
    lat, lng = extract_coordinates_from_url(current_url)
    
    restaurant_data = {
        'id_resto': restaurant_id
    }
    
    if lat and lng:
        restaurant_data['latitude'] = lat
        restaurant_data['longitude'] = lng
        print(f"Koordinat: {lat}, {lng}")
    else:
        print("Gagal mengekstrak koordinat dari URL")
    
    # Nama restoran
    name_selectors = [
        '//h1[contains(@class, "DUwDvf")]',
        '//h1[@class="DUwDvf lfPIob"]',
        '//div[@class="lMbq3e"]//h1',
        '//span[contains(@class, "DUwDvf")]'
    ]
    
    name = 'Unknown'
    for selector in name_selectors:
        try:
            element = safe_find_element(driver, By.XPATH, selector)
            if element:
                name = element.text.strip()
                if name:
                    restaurant_data['name'] = name
                    print(f"Nama restoran: {name}")
                    break
        except:
            continue
    
    if 'name' not in restaurant_data:
        restaurant_data['name'] = 'Unknown'
    
    # Kategori
    category_selectors = [
        '//button[contains(@class, "DkEaL")]',
        '//span[contains(@class, "DkEaL")]',
        '//div[@class="LBgpqf"]//button'
    ]
    
    for selector in category_selectors:
        try:
            element = safe_find_element(driver, By.XPATH, selector)
            if element:
                category = element.text.strip()
                if category and not category.startswith('4'):
                    restaurant_data['category'] = category
                    print(f"Kategori: {category}")
                    break
        except:
            continue
    
    if 'category' not in restaurant_data:
        restaurant_data['category'] = 'Unknown'
    
    # # Harga
    # price_selectors = [
    #     '//span[contains(@aria-label, "Rentang harga")]',
    #     '//div[contains(@class, "fontBodyMedium")]//span[contains(text(), "Rp")]'
    # ]
    
    # prices_found = []
    # for selector in price_selectors:
    #     try:
    #         elements = driver.find_elements(By.XPATH, selector)
    #         for element in elements:
    #             price = element.text.strip()
    #             if price and ('Rp' in price or '$' in price):
    #                 prices_found.append(price)
    #     except:
    #         continue
    
    # if prices_found:
    #     restaurant_data['price_range'] = '; '.join(prices_found)
    #     print(f"Harga: {restaurant_data['price_range']}")
    # else:
    #     restaurant_data['price_range'] = 'N/A'
    
    # # Deskripsi
    # description_selectors = [
    #     '//span[contains(@class, "HlvSq")]',
    #     '//div[contains(@class, "PYvSYb")]',
    #     '//div[@class="fontBodyMedium"]//span'
    # ]
    
    # # Coba expand deskripsi
    # try:
    #     expand_buttons = driver.find_elements(By.XPATH, '//button[contains(., "Selengkapnya")]')
    #     for button in expand_buttons:
    #         if button.is_displayed():
    #             button.click()
    #             random_delay(1, 2)
    #             break
    # except:
    #     pass
    
    # for selector in description_selectors:
    #     try:
    #         element = safe_find_element(driver, By.XPATH, selector)
    #         if element:
    #             description = element.text.strip()
    #             if description and len(description) > 20:
    #                 restaurant_data['description'] = clean_review_text(description)
    #                 print(f"Deskripsi: {description[:100]}...")
    #                 break
    #     except:
    #         continue
    
    # if 'description' not in restaurant_data:
    #     restaurant_data['description'] = 'N/A'
    
    # Ambil ulasan (maksimal 10)
    reviews, updated_counter = get_reviews(driver, restaurant_id, global_review_counter, max_reviews=10)
    restaurant_data['reviews_count'] = len(reviews)
    
    return restaurant_data, reviews, updated_counter, name

def save_restaurants_to_csv(restaurants_data, filename=None):
    """Save restaurant data to CSV file"""
    if not restaurants_data:
        print("Tidak ada data restoran untuk disimpan")
        return None
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"restaurants_{timestamp}.csv"
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id_resto', 'name', 'category', 'latitude', 'longitude',
                         'price_range', 'description', 'reviews_count']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for restaurant in restaurants_data:
                row = {
                    'id_resto': restaurant.get('id_resto', ''),
                    'name': restaurant.get('name', ''),
                    'category': restaurant.get('category', ''),
                    'latitude': restaurant.get('latitude', ''),
                    'longitude': restaurant.get('longitude', ''),
                    # 'price_range': restaurant.get('price_range', ''),
                    # 'description': restaurant.get('description', ''),
                    'reviews_count': restaurant.get('reviews_count', 0)
                }
                writer.writerow(row)
        
        print(f"Data restoran berhasil disimpan ke {filename}")
        return filename
        
    except Exception as e:
        print(f"Error saat menyimpan CSV restoran: {e}")
        return None

def save_reviews_to_csv(all_reviews, filename=None):
    """Save reviews data to CSV file"""
    if not all_reviews:
        print("Tidak ada data ulasan untuk disimpan")
        return None
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reviews_{timestamp}.csv"
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['review_id', 'user_id', 'restaurant_id', 'review_text', 'rating', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for review in all_reviews:
                writer.writerow(review)
        
        print(f"Data ulasan berhasil disimpan ke {filename}")
        return filename
        
    except Exception as e:
        print(f"Error saat menyimpan CSV ulasan: {e}")
        return None

def scrape_multiple_restaurants(search_term="restoran", max_restaurants=10):
    """Scrape multiple restaurants - simplified approach"""
    
    driver = setup_driver()
    restaurants_data = []
    all_reviews = []
    global_review_counter = 0
    
    try:
        # 1. Buka Google Maps dan search
        print(f"Mencari: {search_term}")
        driver.get("https://maps.google.com/")
        random_delay(3, 5)
        
        search_box = safe_find_element(driver, By.XPATH, '//input[@id="searchboxinput"]')
        if not search_box:
            print("Gagal menemukan search box")
            return [], []
        
        search_box.clear()
        search_box.send_keys(search_term)
        random_delay(1, 2)
        search_box.send_keys(Keys.RETURN)
        random_delay(5, 8)
        
        # 2. Scroll hasil pencarian untuk memuat lebih banyak restoran
        print("Scroll hasil pencarian...")
        for i in range(3):  # Scroll 3 kali saja
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            random_delay(2, 3)
            print(f"Scroll ke-{i+1}")
        
        # Scroll kembali ke atas
        driver.execute_script("window.scrollTo(0, 0);")
        random_delay(2, 3)
        print("Scroll kembali ke atas")
        
        # 3. Ambil link restoran
        restaurant_links = driver.find_elements(By.XPATH, '//a[@class="hfpxzc"]')
        print(f"Ditemukan {len(restaurant_links)} restoran")
        
        # 4. Buka setiap restoran satu per satu
        for i in range(min(len(restaurant_links), max_restaurants)):
            print(f"\n=== RESTORAN KE-{i+1} ===")
            restaurant_id = f"{i+1:03d}"
            
            try:
                # Klik restoran
                restaurant_links[i].click()
                random_delay(5, 8)
                
                # Ambil data restoran
                restaurant_data, reviews, global_review_counter, name = get_restaurant_info(
                    driver, restaurant_id, global_review_counter
                )
                
                if restaurant_data:
                    restaurants_data.append(restaurant_data)
                    all_reviews.extend(reviews)
                    print(f"Berhasil scrape: {name} ({len(reviews)} ulasan)")
                else:
                    print(f"Gagal scrape restoran ke-{i+1}")
                
                # Kembali ke hasil pencarian
                driver.back()
                random_delay(3, 5)
                
                # Refresh link elements karena mungkin sudah stale
                restaurant_links = driver.find_elements(By.XPATH, '//a[@class="hfpxzc"]')
                
            except Exception as e:
                print(f"Error pada restoran ke-{i+1}: {e}")
                try:
                    driver.back()
                    random_delay(3, 5)
                    restaurant_links = driver.find_elements(By.XPATH, '//a[@class="hfpxzc"]')
                except:
                    pass
        
        # 5. Simpan hasil
        if restaurants_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            restaurants_filename = save_restaurants_to_csv(restaurants_data, f"restaurants_{timestamp}.csv")
            reviews_filename = save_reviews_to_csv(all_reviews, f"reviews_{timestamp}.csv")
            
            print(f"\n=== HASIL SCRAPING ===")
            print(f"Total restoran: {len(restaurants_data)}")
            print(f"Total ulasan: {len(all_reviews)}")
            print(f"File CSV Restoran: {restaurants_filename}")
            print(f"File CSV Ulasan: {reviews_filename}")
            
            for restaurant in restaurants_data:
                print(f"\n{restaurant.get('id_resto')}. {restaurant.get('name', 'Unknown')}")
                print(f"   Kategori: {restaurant.get('category', 'Unknown')}")
                print(f"   Harga: {restaurant.get('price_range', 'Unknown')}")
                print(f"   Ulasan: {restaurant.get('reviews_count', 0)} ulasan")
        else:
            print("Tidak ada data yang berhasil di-scrape")
            
    except Exception as e:
        print(f"Error dalam scraping: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
    
    return restaurants_data, all_reviews

if __name__ == "__main__":
    search_term = "italian food jakarta timur"
    max_restaurants = 2
    
    print(f"Mulai scraping {max_restaurants} restoran untuk '{search_term}'")
    restaurants, reviews = scrape_multiple_restaurants(search_term, max_restaurants)
    
    if restaurants:
        print(f"\nScraping selesai! Berhasil mengambil data {len(restaurants)} restoran dan {len(reviews)} ulasan.")
    else:
        print("\nScraping gagal atau tidak ada data yang ditemukan.")