import scrapy
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

class MevzuatSeleniumSpider(scrapy.Spider):
    name = "MevzuatSeleniumSpider"
    start_urls = ['https://www.mevzuat.gov.tr']
    
    MEVZUAT_SELECTORS = {
        "Kanun": {
            "link_title": "Kanunlar",
            "form_id": "kanunlar_form"
        },
        "Cumhurbaşkanlığı Kararnamesi": {
            "link_title": "Cumhurbaşkanlığı Kararnameleri",
            "form_id": "cumhurbaskanligiKararnameleri_form"
        },
        "Cumhurbaşkanlığı ve Bakanlar Kurulu Yönetmeliği": {
            "link_title": "Cumhurbaşkanlığı ve Bakanlar Kurulu Yönetmelikleri",
            "form_id": "cumhurbaskanligiveBakanlarKuruluYonetmelikleri_form"
        },
        "Kanun Hükmünde Kararname": {
            "link_title": "Kanun Hükmünde Kararnameler",
            "form_id": "kanunHukmundeKararnameler_form"
        },
        "Tüzük": {
            "link_title": "Tüzükler",
            "form_id": "tuzukler_form"
        },
        "Kurum ve Kuruluş Yönetmeliği": {
            "link_title": "Kurum Kuruluş ve Üniversite Yönetmelikleri",
            "form_id": "kurumKurulusVeUniversiteYonetmelikleri_form"
        },
        "Tebliğ": {
            "link_title": "Tebliğler",
            "form_id": "tebligler_form"
        }
    }

    def __init__(self, start_year=None, end_year=None, mevzuat_turu="Kanun", search_term=None, *args, **kwargs):
        super(MevzuatSeleniumSpider, self).__init__(*args, **kwargs)
        options = Options()
        options.headless = True
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
        
        self.start_year = start_year
        self.end_year = end_year
        self.mevzuat_turu = mevzuat_turu
        self.search_term = search_term
        
    def parse(self, response):
        self.driver.get(response.url)
        
        # Seçilen mevzuat türüne göre selector'ları al
        selectors = self.MEVZUAT_SELECTORS.get(self.mevzuat_turu)
        if not selectors:
            raise ValueError(f"Desteklenmeyen mevzuat türü: {self.mevzuat_turu}")
            
        # İlgili mevzuat türü linkine tıkla
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f'a[title="{selectors["link_title"]}"]'))
        ).click()

        # Arama formunu bekle
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.ID, selectors["form_id"]))
        )
 
        # Form elementini bul
        form = self.driver.find_element(By.ID, selectors["form_id"])

        # Arama alanına terimi gir (eğer varsa)
        if self.search_term:
            search_input = form.find_element(By.ID, "AranacakIfade")
            search_input.clear()
            search_input.send_keys(self.search_term)

        # Yıl aralığını gir (eğer varsa)
        if self.start_year:
            form.find_element(By.ID, "BaslangicTarihi").send_keys(str(self.start_year))
        if self.end_year:
            form.find_element(By.ID, "BitisTarihi").send_keys(str(self.end_year))
            
        form.find_element(By.ID, "btnSearch").click()
        
        # Sayfanın tamamen yüklendiğinden emin ol
        WebDriverWait(self.driver, 20).until(
            lambda driver: self.driver.find_element(By.ID, "loaderContainer").get_attribute("style") == "display: none;"
        )
        time.sleep(10)
        
        while True:
            try:
                # Sonuç tablosunu bul
                kanunlar_table = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.ID, "DataTables_Table_0"))
                )
                
                kanunlar_rows = kanunlar_table.find_elements(By.TAG_NAME, "tr")

                # Eğer arama sonucu yoksa döngüyü kır
                if len(kanunlar_rows) <= 1:  # Sadece header varsa
                    self.logger.info("Arama sonucu bulunamadı.")
                    break

                for row in kanunlar_rows[1:]:  # Header'ı atla
                    try:
                        # Her kanun için linki bul
                        link_element = row.find_element(By.CSS_SELECTOR, "td a")
                        link = link_element.get_attribute("href")
                        kanun_adi = link_element.text.strip()

                        self.logger.info(f"İşleniyor: {kanun_adi}")

                        # Yeni sekmede linki aç
                        self.driver.execute_script("window.open(arguments[0]);", link)

                        # Yeni sekmeye geç
                        self.driver.switch_to.window(self.driver.window_handles[-1])

                        # Kanun detaylarını içeren iframe'e geç
                        iframe = WebDriverWait(self.driver, 20).until(
                            EC.presence_of_element_located((By.ID, "mevzuatDetayIframe"))
                        )
                        self.driver.switch_to.frame(iframe)

                        # Sayfa içeriğini al
                        html_content = self.driver.page_source
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Sadece <body> tag'inden metni çıkar
                        body_content = soup.body.get_text(separator=' ', strip=True)

                        # Sonuçları döndür
                        yield {
                            'url': link,
                            'kanun_adi': kanun_adi,
                            'full_text': body_content,
                            'search_term': self.search_term if self.search_term else "Tümü"
                        }

                        # Mevcut sekmeyi kapat ve ana sekmeye dön
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])

                    except Exception as e:
                        self.logger.error(f"Hata oluştu: {e}")
                        # Eğer bir hata oluştuysa, pencere durumunu kontrol et
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])

                # Bir sonraki sayfaya geç
                try:
                    next_page_button = self.driver.find_element(By.CSS_SELECTOR, 'li.paginate_button.page-item.active + li.paginate_button.page-item')
                    if 'disabled' in next_page_button.get_attribute('class'):
                        # Sonraki sayfa butonu devre dışıysa, son sayfadayız
                        break
                    next_page_button.click()

                    # Sonraki sayfanın tamamen yüklendiğinden emin ol
                    WebDriverWait(self.driver, 20).until(
                        lambda driver: self.driver.find_element(By.ID, "loaderContainer").get_attribute("style") == "display: none;"
                    )
                    time.sleep(3)  # Sayfanın yüklenmesi için bekle

                except Exception as e:
                    self.logger.info(f"Sonraki sayfa bulunamadı veya son sayfa: {e}")
                    break

            except Exception as e:
                self.logger.error(f"Genel hata oluştu: {e}")
                break

    def closed(self, reason):
        self.driver.quit()