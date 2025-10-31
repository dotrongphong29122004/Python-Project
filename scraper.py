import time
import hashlib
import random
import json 
from bs4 import BeautifulSoup 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

# Import đúng theo cấu trúc file của bạn
from app import app, db
from models import Product, Category

# --- CẤU HÌNH --- (Giữ nguyên)
CATEGORIES_TO_SCRAPE = {
    "dienthoai": "Điện thoại",
    "laptop": "Laptop",
    "sach": "Sách",
    "dienlanh": "Điện lạnh",
    "giadung": "Thiết bị gia dụng",
    "yte": "Thiết bị y tế",
    "thethao": "Thể thao",
    "thoitrangnam": "Thời trang nam",
    "thoitrangnu": "Thời trang nữ",
    "mypham": "Mỹ phẩm",
}

# --- CÁC HÀM CRAWL --- (Giữ nguyên)
def clean_price(price_text):
    if not price_text:
        return 0
    try:
        # Chuyển đổi price_text sang string nếu nó là số (từ JSON)
        price_text = str(price_text)
        price_part = price_text.split('-')[0]
        return int(price_part.replace('₫', '').replace('đ', '').replace('.', '').strip())
    except (ValueError, IndexError):
        return 0

def get_product_id(product_url):
    if not product_url:
        return None
    return hashlib.md5(product_url.encode()).hexdigest()

# =======================================================================
# HÀM CRAWL TIKI 
# =======================================================================
def scrape_tiki(keyword, category_id):
    print(f"\n--- Bắt đầu cào dữ liệu TIKI cho: '{keyword}' ---")
    
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200,800")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"Lỗi khi khởi tạo WebDriver: {e}")
        return

    stealth(driver,
            languages=["vi-VN", "vi"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    try:
        url = f"https://tiki.vn/search?q={keyword.replace(' ', '+')}"
        driver.get(url)

        wait = WebDriverWait(driver, 120) 
        product_card_selector = "a.product-item" 
        
        print("\n*******************************************")
        print("*** LƯU Ý: TIKI CÓ THỂ YÊU CẦU CAPTCHA ***")
        print("Nếu thấy hình trượt, vui lòng GIẢI BẰNG TAY.")
        print(f"Bạn có 120 giây để làm việc này...")
        print("*******************************************")
        
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, product_card_selector)))
        
        print("\nĐÃ PHÁT HIỆN SẢN PHẨM! Bắt đầu cào...")
        
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            thoi_gian_cho_cuon = random.randint(3, 7)
            print(f"Đã cuộn lần {i+1}, chờ {thoi_gian_cho_cuon} giây...")
            time.sleep(thoi_gian_cho_cuon)

        products_elements = driver.find_elements(By.CSS_SELECTOR, product_card_selector)
        
        print(f"Tìm thấy {len(products_elements)} sản phẩm trên trang.")
        
        new_products = 0
        processed_ids_in_this_session = set()
        
        main_window = driver.current_window_handle
        
        for i, el in enumerate(products_elements):
            print(f"\n--- Đang xử lý sản phẩm #{i+1} ---")
            product_name = ""
            product_price = 0
            product_image = ""
            product_url = ""

            try:
                # 1. Lấy URL và ID
                product_url = el.get_attribute('href')
                if not product_url or not product_url.startswith('http'):
                    print("DEBUG: Lỗi URL. Bỏ qua.")
                    continue 
                
                product_id = get_product_id(product_url)
                print(f"DEBUG: ID = {product_id}")
                
                # 2. Kiểm tra trùng lặp
                if product_id in processed_ids_in_this_session:
                    print("DEBUG: Đã xử lý trong session này. Bỏ qua.")
                    continue
                
                exists = db.session.get(Product, product_id) 
                if exists:
                    print("DEBUG: Đã tồn tại trong DB. Bỏ qua.")
                    continue

                # 3. Lấy TÊN SẢN PHẨM
                try:
                    img_el = el.find_element(By.XPATH, ".//img")
                    product_name = img_el.get_attribute('alt')
                    print(f"DEBUG: Tên (thử 2: img alt) = {product_name}")
                except Exception:
                    product_name = ""
                    print("DEBUG: (img alt) thất bại.")

                # 4. Lấy GIÁ
                try:
                    price_container = el.find_element(By.XPATH, ".//div[contains(@class, 'price-discount__price')]")
                    product_price_text = price_container.text
                    product_price = clean_price(product_price_text)
                    print(f"DEBUG: Giá text = '{product_price_text}', Giá clean = {product_price}")
                except NoSuchElementException:
                    print("DEBUG: LỖI không tìm thấy GIÁ")

                # 5. Lấy ẢNH
                try:
                    img_el = el.find_element(By.XPATH, ".//img")
                    product_image = None 
                    product_image = img_el.get_attribute('data-src')
                    if not product_image:
                        product_image = img_el.get_attribute('src')
                    if not product_image or product_image.startswith('data:image'):
                        product_image = img_el.get_attribute('data-srcset')
                    if not product_image:
                        product_image = img_el.get_attribute('srcset')
                    if product_image and ',' in product_image:
                        product_image = product_image.split(',')[0].split(' ')[0]
                    if not product_image:
                        product_image = ""
                    print(f"DEBUG: Ảnh = {product_image[:50]}...")

                except NoSuchElementException:
                    print("DEBUG: LỖI không tìm thấy ẢNH")
                
                # 6. KIỂM TRA CUỐI CÙNG VÀ LẤY MÔ TẢ
                if product_name and product_price > 0 and product_url and product_image:
                    
                    # === KHỐI LẤY MÔ TẢ ĐÃ THAY ĐỔI HOÀN TOÀN ===
                    product_description = ""
                    try:
                        # Mở tab mới
                        driver.execute_script("window.open(arguments[0]);", product_url)
                        driver.switch_to.window(driver.window_handles[-1]) 
                        
                        # Chờ trang tải (có thể giảm xuống)
                        time.sleep(random.randint(2, 4)) 

                        # 1. Tìm thẻ script __NEXT_DATA__
                        script_tag = driver.find_element(By.ID, "__NEXT_DATA__")
                        script_content = script_tag.get_attribute("textContent")
                        
                        # 2. Phân tích JSON
                        data = json.loads(script_content)
                        
                        # 3. Trích xuất HTML mô tả
                        desc_html = data['props']['initialState']['productv2']['productData']['response']['data']['description']
                        
                        # 4. Dùng BeautifulSoup để làm sạch HTML
                        soup = BeautifulSoup(desc_html, 'html.parser')
                        product_description = soup.get_text(separator='\n').strip()

                        if product_description:
                             print("DEBUG: Đã lấy được mô tả từ JSON.")
                        else:
                             print("DEBUG: Tìm thấy JSON nhưng trường mô tả bị rỗng.")
                        
                    except Exception as e_tab:
                        print(f"DEBUG: Lỗi khi lấy mô tả từ JSON: {e_tab}")
                    finally:
                        driver.close() 
                        driver.switch_to.window(main_window) 
                    # --- KẾT THÚC CRAWL MÔ TẢ ---

                    product = Product(
                        id=product_id,
                        name=product_name,
                        price=product_price,
                        image_url=product_image,
                        url=product_url,
                        platform="Tiki",
                        category_id=category_id,
                        description=product_description 
                    )
                    db.session.add(product)
                    
                    processed_ids_in_this_session.add(product_id)
                    
                    new_products += 1
                    print(f"TRẠNG THÁI: OK! Đã thêm vào session (Mô tả: {bool(product_description)}).")
                else:
                    print(f"TRẠNG THÁI: BỎ QUA. (Tên: '{bool(product_name)}', Giá: {product_price > 0}, Ảnh: '{bool(product_image)}')")

            except Exception as e:
                print(f"LỖI NGHIÊM TRỌNG (Sản phẩm #{i+1}): {e}")
                pass
                
        db.session.commit()
        print(f"\n==========================================")
        print(f"KẾT QUẢ: Đã thêm {new_products} sản phẩm TIKI mới cho danh mục '{category_id}'.")
        print(f"==========================================")

    except TimeoutException:
        print(f"\nLỖI: HẾT THỜI GIAN CHỜ (120 giây) cho '{keyword}'.")
        time.sleep(5) 
    except Exception as e:
        print(f"Lỗi nghiêm trọng khi cào '{keyword}': {e}")
    finally:
        print("Đóng trình duyệt cho danh mục này.")
        driver.quit()

# =======================================================================
# HÀM CRAWL LAZADA (SỬA LỖI: CÀO TỪ JSON-LD TRANG CHI TIẾT)
# =======================================================================
def scrape_lazada(keyword, category_id):
    print(f"\n--- Bắt đầu cào dữ liệu LAZADA cho: '{keyword}' ---")
    
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200,800")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"Lỗi khi khởi tạo WebDriver: {e}")
        return

    stealth(driver, languages=["vi-VN", "vi"], vendor="Google Inc.", platform="Win32",
            webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

    try:
        url = f"https://www.lazada.vn/catalog/?q={keyword.replace(' ', '+')}"
        driver.get(url)

        # Bước chờ giải CAPTCHA (Giữ nguyên)
        print("\n*******************************************")
        print("CỬA SỔ TRÌNH DUYỆT LAZADA ĐÃ MỞ.")
        print("BƯỚC 1: NHÌN VÀO TRÌNH DUYỆT CHROME.")
        print("BƯỚC 2: NẾU THẤY THANH TRƯỢT, HÃY DÙNG CHUỘT KÉO ĐỂ GIẢI CAPTCHA.")
        print("BƯỚC 3: SAU KHI GIẢI XONG, QUAY LẠI ĐÂY VÀ NHẤN 'ENTER'.")
        print("*******************************************")
        input("Nhấn ENTER sau khi bạn đã giải CAPTCHA (nếu có)...")

        # Selector cho thẻ sản phẩm (tin đăng) của Lazada
        product_card_selector = "div[data-qa-locator='product-item']" 
        
        wait = WebDriverWait(driver, 60) 
        
        try:
            # Chờ ít nhất một thẻ sản phẩm xuất hiện
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, product_card_selector)))
        except TimeoutException:
            print(f"\nLỖI: HẾT THỜI GIAN CHỜ (60 giây) cho '{keyword}'.")
            print("Đã nhấn ENTER sau khi giải CAPTCHA thủ công chưa?")
            try:
                # Lưu file debug khi timeout
                error_file = "debug_lazada_TIMEOUT_error.html"
                with open(error_file, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f"DEBUG: ĐÃ LƯU HTML TRANG LỖI VÀO: {error_file}")
            except Exception as e_file:
                print(f"DEBUG: Không thể lưu file HTML lỗi: {e_file}")
            driver.quit()
            return # Thoát hàm

        print("\nĐÃ PHÁT HIỆN SẢN PHẨM! Bắt đầu cào...")
        
        # Lấy tất cả các thẻ sản phẩm tìm thấy
        products_elements = driver.find_elements(By.CSS_SELECTOR, product_card_selector)
        print(f"Tìm thấy {len(products_elements)} sản phẩm trên trang.")
        
        new_products = 0
        processed_ids_in_this_session = set()
        
        for i, el in enumerate(products_elements):
            # 'el' bây giờ là thẻ <div> của sản phẩm
            print(f"\n--- Đang xử lý sản phẩm LAZADA #{i+1} ---")
            try:
                # === BƯỚC 1: SCROLL VÀ CHỜ ẢNH TẢI (GIỐNG HỆT CHOTOT) ===
                product_image = ""
                img_el = None
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", el)
                    time.sleep(0.5) 
                    
                    img_el = el.find_element(By.TAG_NAME, "img")
                    
                    # Chờ tối đa 5 giây để 'src' là một URL hợp lệ (bắt đầu bằng http)
                    WebDriverWait(driver, 5).until(
                        lambda d: img_el.get_attribute('src') and 
                                  img_el.get_attribute('src').startswith('http')
                    )
                    
                    product_image = img_el.get_attribute('src')
                    print(f"DEBUG: Ảnh = {product_image[:50]}...")
                    
                except (TimeoutException, NoSuchElementException) as e_img:
                    print(f"DEBUG: LỖI không tìm thấy URL ảnh (Timeout/Not Found). Bỏ qua.")
                    continue 

                # === BƯỚC 2: LẤY CÁC THÔNG TIN CÒN LẠI ===
                
                # Lấy URL (Nằm trong thẻ <a> con)
                link_element = el.find_element(By.TAG_NAME, "a")
                product_url = link_element.get_attribute('href')
                
                if product_url and product_url.startswith("//"):
                    product_url = "https:" + product_url
                
                if not product_url or not product_url.startswith('http'):
                    print("DEBUG: Lỗi URL. Bỏ qua.")
                    continue 
                
                product_id = get_product_id(product_url)
                print(f"DEBUG: ID = {product_id}")
                
                # Kiểm tra trùng lặp
                if product_id in processed_ids_in_this_session:
                    print("DEBUG: Đã xử lý trong session này. Bỏ qua.")
                    continue
                if db.session.get(Product, product_id): 
                    print("DEBUG: Đã tồn tại trong DB. Bỏ qua.")
                    continue

                # Lấy TÊN (Từ 'alt' của ảnh đã tìm thấy)
                product_name = img_el.get_attribute('alt')
                if not product_name:
                    # Phương án dự phòng nếu 'alt' rỗng
                    product_name = el.find_element(By.CSS_SELECTOR, "div[data-qa-locator='product-item-title']").text
                print(f"DEBUG: Tên = {product_name}")

                # Lấy GIÁ
                try:
                    # Dùng XPath | (OR) để tìm 1 trong 2 selector
                    price_selector_xpath = ".//span[@data-qa-locator='product-item-price'] | .//span[contains(@class, 'ooOxS')]"
                    product_price_text = el.find_element(By.XPATH, price_selector_xpath).text
                    product_price = clean_price(product_price_text)
                    print(f"DEBUG: Giá = {product_price}")
                    if product_price == 0:
                        print("DEBUG: Giá = 0. Bỏ qua.")
                        continue
                except NoSuchElementException:
                    # Nếu cả 2 selector đều không tìm thấy giá, bỏ qua sản phẩm này
                    print("DEBUG: LỖI không tìm thấy GIÁ (cả 2 selector). Bỏ qua.")
                    continue
                
                product_description = "" # Yêu cầu không lấy mô tả

                # LƯU VÀO DB
                product = Product(
                    id=product_id, name=product_name, price=product_price,
                    image_url=product_image, url=product_url, platform="Lazada", # Đổi platform
                    category_id=category_id, description=product_description 
                )
                db.session.add(product)
                processed_ids_in_this_session.add(product_id)
                new_products += 1
                print(f"TRẠNG THÁI: OK! Đã thêm vào session.")

            except Exception as e:
                print(f"LỖI (Sản phẩm #{i+1}): {e}")
                pass
                
        db.session.commit()
        print(f"\n==========================================")
        print(f"KẾT QUẢ: Đã thêm {new_products} sản phẩm LAZADA mới cho danh mục '{category_id}'.")
        print(f"==========================================")

    except Exception as e:
        print(f"Lỗi nghiêm trọng khi cào '{keyword}': {e}")
    finally:
        print("Đóng trình duyệt LAZADA cho danh mục này.")
        driver.quit()

# =======================================================================
# HÀM CRAWL ĐIỆN MÁY XANH (Chỉ cào trang tìm kiếm)
# =======================================================================
def scrape_dmx(keyword, category_id):
    print(f"\n--- Bắt đầu cào dữ liệu ĐIỆN MÁY XANH cho: '{keyword}' ---")
    
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200,800")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"Lỗi khi khởi tạo WebDriver: {e}")
        return

    stealth(driver, languages=["vi-VN", "vi"], vendor="Google Inc.", platform="Win32",
            webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

    try:
        url = f"https://www.dienmayxanh.com/search?key={keyword.replace(' ', '+')}"
        driver.get(url)

        product_card_selector = "a.main-contain" 
        
        wait = WebDriverWait(driver, 30) 
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, product_card_selector)))
        
        print("\nĐÃ PHÁT HIỆN SẢN PHẨM! Bắt đầu cào...")
        
        try:
            for i in range(3): 
                xem_them_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Xem thêm')]")
                driver.execute_script("arguments[0].click();", xem_them_button)
                print(f"Đã bấm xem thêm lần {i+1}...")
                time.sleep(random.randint(2, 4))
        except Exception:
            print("DEBUG: Không tìm thấy nút 'Xem thêm', hoặc đã cào hết.")
            pass 

        products_elements = driver.find_elements(By.CSS_SELECTOR, product_card_selector)
        print(f"Tìm thấy {len(products_elements)} sản phẩm trên trang.")
        
        new_products = 0
        processed_ids_in_this_session = set()
        
        for i, el in enumerate(products_elements):
            print(f"\n--- Đang xử lý sản phẩm DMX #{i+1} ---")
            try:
                # 1. LẤY URL
                product_url = el.get_attribute('href')
                if not product_url or not product_url.startswith('http'):
                    print("DEBUG: Lỗi URL. Bỏ qua.")
                    continue 
                
                product_id = get_product_id(product_url)
                print(f"DEBUG: ID = {product_id}")
                
                # 2. KIỂM TRA TRÙNG LẶP
                if product_id in processed_ids_in_this_session:
                    print("DEBUG: Đã xử lý trong session này. Bỏ qua.")
                    continue
                if db.session.get(Product, product_id): 
                    print("DEBUG: Đã tồn tại trong DB. Bỏ qua.")
                    continue

                # 3. LẤY TÊN
                product_name = el.find_element(By.TAG_NAME, "h3").text
                print(f"DEBUG: Tên = {product_name}")

                # 4. LẤY GIÁ
                product_price_text = el.find_element(By.XPATH, ".//strong[contains(@class, 'price')]").text
                product_price = clean_price(product_price_text)
                print(f"DEBUG: Giá = {product_price}")
                if product_price == 0:
                    print("DEBUG: Giá = 0 (hết hàng). Bỏ qua.")
                    continue

                # 5. LẤY ẢNH
                img_el = el.find_element(By.TAG_NAME, "img")
                product_image = img_el.get_attribute('src') or img_el.get_attribute('data-src')
                if not product_image or product_image.startswith('data:image'):
                    print("DEBUG: LỖI không tìm thấy URL ảnh. Bỏ qua.")
                    continue
                print(f"DEBUG: Ảnh = {product_image[:50]}...")
                
                product_description = "" # Không lấy mô tả

                # 6. LƯU VÀO DB
                if product_name and product_price > 0 and product_url and product_image:
                    product = Product(
                        id=product_id, name=product_name, price=product_price,
                        image_url=product_image, url=product_url, platform="DienMayXanh", 
                        category_id=category_id, description=product_description 
                    )
                    db.session.add(product)
                    processed_ids_in_this_session.add(product_id)
                    new_products += 1
                    print(f"TRẠNG THÁI: OK! Đã thêm vào session.")
                else:
                    print(f"TRẠNG THÁI: BỎ QUA.")

            except Exception as e:
                print(f"LỖI NGHIÊM TRỌNG (Sản phẩm #{i+1}): {e}")
                pass
                
        db.session.commit()
        print(f"\n==========================================")
        print(f"KẾT QUẢ: Đã thêm {new_products} sản phẩm DMX mới cho danh mục '{category_id}'.")
        print(f"==========================================")

    except TimeoutException:
        print(f"\nLỖI: HẾT THỜI GIAN CHỜ (30 giây) cho '{keyword}'.")
    except Exception as e:
        print(f"Lỗi nghiêm trọng khi cào '{keyword}': {e}")
    finally:
        print("Đóng trình duyệt DMX cho danh mục này.")
        driver.quit()

# =======================================================================
# HÀM CRAWL CHỢ TỐT (Chỉ cào trang tìm kiếm)
# =======================================================================
def scrape_chotot(keyword, category_id):
    print(f"\n--- Bắt đầu cào dữ liệu CHỢ TỐT cho: '{keyword}' ---")
    
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200,800")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"Lỗi khi khởi tạo WebDriver: {e}")
        return

    stealth(driver, languages=["vi-VN", "vi"], vendor="Google Inc.", platform="Win32",
            webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

    try:
        url = f"https://www.chotot.com/toan-quoc/mua-ban?q={keyword.replace(' ', '+')}"
        driver.get(url)

        # Bước chờ giải CAPTCHA (Giữ nguyên)
        print("\n*******************************************")
        print("CỬA SỔ TRÌNH DUYỆT CHỢ TỐT ĐÃ MỞ.")
        print("BƯỚC 1: NHÌN VÀO TRÌNH DUYỆT CHROME.")
        print("BƯỚC 2: NẾU THẤY THANH TRƯỢT, HÃY DÙNG CHUỘT KÉO ĐỂ GIẢI CAPTCHA.")
        print("BƯỚC 3: SAU KHI GIẢI XONG, QUAY LẠI ĐÂY VÀ NHẤN 'ENTER'.")
        print("*******************************************")
        input("Nhấn ENTER sau khi bạn đã giải CAPTCHA (nếu có)...")

        product_card_selector = "li.a14axl8t" 
        wait = WebDriverWait(driver, 60) 
        
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, product_card_selector)))
        except TimeoutException:
            print(f"\nLỖI: HẾT THỜI GIAN CHỜ (60 giây) cho '{keyword}'.")
            print("Đã nhấn ENTER sau khi giải CAPTCHA thủ công chưa?")
            try:
                error_file = "debug_chotot_TIMEOUT_error.html"
                with open(error_file, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f"DEBUG: ĐÃ LƯU HTML TRANG LỖI VÀO: {error_file}")
            except Exception as e_file:
                print(f"DEBUG: Không thể lưu file HTML lỗi: {e_file}")
            driver.quit()
            return # Quan trọng: Phải thoát hàm nếu timeout

        print("\nĐÃ PHÁT HIỆN SẢN PHẨM! Bắt đầu cào...")
        
        # --- XÓA VÒNG LẶP SCROLL CŨ ---
        # Chúng ta sẽ scroll bên trong vòng lặp bên dưới
        
        products_elements = driver.find_elements(By.CSS_SELECTOR, product_card_selector)
        print(f"Tìm thấy {len(products_elements)} sản phẩm trên trang.")
        
        new_products = 0
        processed_ids_in_this_session = set()
        
        for i, el in enumerate(products_elements):
            print(f"\n--- Đang xử lý sản phẩm CHOTOT #{i+1} ---")
            try:
                # === BƯỚC 1: SCROLL VÀ CHỜ ẢNH TẢI ===
                product_image = ""
                try:
                    # Di chuyển (scroll) đến thẻ sản phẩm
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", el)
                    
                    # Chờ 0.5s để JS bắt đầu chạy
                    time.sleep(0.5) 
                    
                    # Tìm thẻ <img>
                    img_el = el.find_element(By.TAG_NAME, "img")
                    
                    # Chờ tối đa 5 giây để 'src' thay đổi (hết placeholder)
                    WebDriverWait(driver, 5).until(
                        lambda d: img_el.get_attribute('src') and 
                                  not img_el.get_attribute('src').startswith('data:image')
                    )
                    
                    # Nếu chờ thành công, lấy URL ảnh
                    product_image = img_el.get_attribute('src')
                    print(f"DEBUG: Ảnh = {product_image[:50]}...")
                    
                except (TimeoutException, NoSuchElementException) as e_img:
                    # Nếu sau 5s ảnh vẫn là placeholder, ta bỏ qua
                    print(f"DEBUG: LỖI không tìm thấy URL ảnh (Timeout/Not Found). Bỏ qua.")
                    continue # Bỏ qua sản phẩm này

                # === BƯỚC 2: LẤY CÁC THÔNG TIN CÒN LẠI ===
                # (Vì ảnh đã OK nên các thông tin khác chắc chắn đã có)

                # Lấy URL
                link_element = el.find_element(By.CSS_SELECTOR, "a.cwv3xk0")
                product_url = link_element.get_attribute('href')
                if not product_url or not product_url.startswith('http'):
                    continue 
                
                product_id = get_product_id(product_url)
                print(f"DEBUG: ID = {product_id}")
                
                # Kiểm tra trùng lặp
                if product_id in processed_ids_in_this_session:
                    print("DEBUG: Đã xử lý trong session này. Bỏ qua.")
                    continue
                if db.session.get(Product, product_id): 
                    print("DEBUG: Đã tồn tại trong DB. Bỏ qua.")
                    continue

                # Lấy TÊN
                product_name = el.find_element(By.CSS_SELECTOR, "h3.ag5pmh3").text
                print(f"DEBUG: Tên = {product_name}")

                # Lấy GIÁ
                product_price_text = el.find_element(By.CSS_SELECTOR, "span.bfe6oav").text
                product_price = clean_price(product_price_text)
                print(f"DEBUG: Giá = {product_price}")
                if product_price == 0:
                    print("DEBUG: Giá = 0 (hoặc giá thỏa thuận). Bỏ qua.")
                    continue
                
                product_description = "" 

                # LƯU VÀO DB (Không cần kiểm tra lại vì đã kiểm tra ở trên)
                product = Product(
                    id=product_id, name=product_name, price=product_price,
                    image_url=product_image, url=product_url, platform="ChoTot", 
                    category_id=category_id, description=product_description 
                )
                db.session.add(product)
                processed_ids_in_this_session.add(product_id)
                new_products += 1
                print(f"TRẠNG THÁI: OK! Đã thêm vào session.")

            except Exception as e:
                # Bắt các lỗi khác nếu có (ví dụ: không tìm thấy tên, giá...)
                print(f"LỖI (Sản phẩm #{i+1}): {e}")
                pass
                
        db.session.commit()
        print(f"\n==========================================")
        print(f"KẾT QUẢ: Đã thêm {new_products} sản phẩm CHOTOT mới cho danh mục '{category_id}'.")
        print(f"==========================================")

    except Exception as e:
        print(f"Lỗi nghiêm trọng khi cào '{keyword}': {e}")
    finally:
        print("Đóng trình duyệt CHOTOT cho danh mục này.")
        driver.quit()

# =======================================================================
# HÀM CHẠY CHÍNH (Giữ nguyên)
# =======================================================================
def run_scraper():
    with app.app_context():
        db.create_all()
        
        categories_in_db = 0
        for cat_id, cat_name in CATEGORIES_TO_SCRAPE.items():
            if not db.session.get(Category, cat_id): 
                new_cat = Category(id=cat_id, name=cat_name)
                db.session.add(new_cat)
                categories_in_db += 1
        if categories_in_db > 0:
            db.session.commit()
            print(f"Đã thêm {categories_in_db} danh mục mới vào CSDL.")
        else:
            print("Không có danh mục mới nào cần thêm.")

        DMX_ALLOWED_CATEGORIES = ["dienthoai", "laptop", "dienlanh", "giadung"]

        total_categories = len(CATEGORIES_TO_SCRAPE)
        count = 0
        for cat_id, keyword in CATEGORIES_TO_SCRAPE.items():
            count += 1
            print(f"\n--- Bắt đầu Danh mục {count}/{total_categories}: {keyword} ---")
            
            if cat_id in DMX_ALLOWED_CATEGORIES:
                scrape_dmx(keyword, cat_id)
                time.sleep(random.randint(10, 20))
            else:
                print(f"\nBỏ qua DMX cho danh mục: '{keyword}' (Không thuộc danh mục điện máy).")

            scrape_lazada(keyword, cat_id)
            time.sleep(random.randint(10, 20)) 

            scrape_chotot(keyword, cat_id)
            time.sleep(random.randint(10, 20)) 

            scrape_tiki(keyword, cat_id)           
            
            if count < total_categories:
                thoi_gian_cho_chinh = random.randint(45, 60) 
                print(f"\n--- HOÀN THÀNH DANH MỤC {count}/{total_categories} ---")
                print(f"Tạm nghỉ {thoi_gian_cho_chinh} giây để tránh bị phát hiện...")
                time.sleep(thoi_gian_cho_chinh)

if __name__ == "__main__":
    run_scraper()