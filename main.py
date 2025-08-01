# mevzuat-gov-scraper/main.py
import os
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from mevzuat_scraper.spiders.mevzuat_metadata_scraper import MevzuatMetadataScraper
from mevzuat_scraper.spiders.mevzuat_spider import MevzuatSeleniumSpider

def get_output_filename(filename, is_metadata=False):
    if not filename:
        filename = 'mevzuat.json'
    
    if not filename.endswith('.json'):
        filename += '.json'
        
    # Metadata çıktıları için dosya adına "_metadata" ekle
    if is_metadata:
        name, ext = os.path.splitext(filename)
        filename = f"{name}_metadata{ext}"
        
    return filename

# Scrapy örümceğini başlatan fonksiyon
def run_spider(start_year=None, end_year=None, filename=None, mevzuat_turu="Kanun", search_term=None):
    filename = get_output_filename(filename, is_metadata=False)
    settings = get_project_settings()
    settings.set('FEEDS', {
        filename: {
            'format': 'json',
            'encoding': 'utf8',
            'overwrite': False,  # Her kanun aynı dosyaya eklenecek
            'store_empty': False
        }
    })
    process = CrawlerProcess(settings)
    process.crawl(MevzuatSeleniumSpider, 
                 start_year=start_year, 
                 end_year=end_year,
                 mevzuat_turu=mevzuat_turu,
                 search_term=search_term)
    process.start()

# Belirli kanun arama fonksiyonu
def search_specific_law(search_term, filename=None, mevzuat_turu="Kanun"):
    filename = get_output_filename(filename, is_metadata=False)
    settings = get_project_settings()
    settings.set('FEEDS', {
        filename: {
            'format': 'json',
            'encoding': 'utf8',
            'overwrite': False,  # Mevcut dosyaya ekle
            'store_empty': False
        }
    })
    process = CrawlerProcess(settings)
    process.crawl(MevzuatSeleniumSpider, 
                 search_term=search_term,
                 mevzuat_turu=mevzuat_turu)
    process.start()

# Başlangıç ve bitiş yılı girişlerini almak için Tkinter GUI
def start_gui():
    def on_submit():
        selected_type = mevzuat_turu_var.get()
        if selected_type in ["Cumhurbaşkanı Kararları", "Cumhurbaşkanlığı Genelgeleri"]:
            messagebox.showwarning(
                "Desteklenmeyen Mevzuat Türü",
                "Seçilen mevzuat türü için tam metin çekimi desteklenmemektedir. Metaverileri çekerek doküman linklerini alabilirsiniz. Lütfen farklı bir mevzuat türü seçiniz."
            )
            return
            
        start_year, end_year = validate_years(entry_start_year.get(), entry_end_year.get())
        if start_year is not None and end_year is not None:
            filename = get_output_filename(entry_filename.get(), is_metadata=False)
            root.destroy()
            run_spider(start_year, end_year, filename, mevzuat_turu_var.get())

    def search_specific():
        selected_type = mevzuat_turu_var.get()
        if selected_type in ["Cumhurbaşkanı Kararları", "Cumhurbaşkanlığı Genelgeleri"]:
            messagebox.showwarning(
                "Desteklenmeyen Mevzuat Türü",  
                "Seçilen mevzuat türü için tam metin çekimi desteklenmemektedir."
            )
            return
            
        search_term = entry_search_term.get().strip()
        if not search_term:
            messagebox.showerror("Hata", "Arama terimi boş bırakılamaz.")
            return
            
        filename = get_output_filename(entry_filename.get(), is_metadata=False)
        root.destroy()
        search_specific_law(search_term, filename, mevzuat_turu_var.get())

    def fetch_all():
        selected_type = mevzuat_turu_var.get()
        if selected_type in ["Cumhurbaşkanı Kararları", "Cumhurbaşkanlığı Genelgeleri"]:
            messagebox.showwarning(
                "Desteklenmeyen Mevzuat Türü",
                "Seçilen mevzuat türü için tam metin çekimi desteklenmemektedir. Metaverileri çekerek doküman linklerini alabilirsiniz. Lütfen farklı bir mevzuat türü seçiniz."
            )
            return
            
        filename = get_output_filename(entry_filename.get(), is_metadata=False)
        root.destroy()
        run_spider(filename=filename, mevzuat_turu=mevzuat_turu_var.get())

    def fetch_metadata():
        start_year, end_year = validate_years(entry_start_year.get(), entry_end_year.get())
        if start_year is not None and end_year is not None:
            filename = get_output_filename(entry_filename.get(), is_metadata=True)
            root.destroy()
            scraper = MevzuatMetadataScraper()
            data = scraper.fetch_data(
                start_year=start_year, 
                end_year=end_year,
                mevzuat_turu=mevzuat_turu_var.get()
            )
            scraper.save_to_json(data, filename)

    def fetch_all_metadata():
        filename = get_output_filename(entry_filename.get(), is_metadata=True)
        root.destroy()
        scraper = MevzuatMetadataScraper()
        data = scraper.fetch_data(mevzuat_turu=mevzuat_turu_var.get())
        scraper.save_to_json(data, filename)

    # CustomTkinter ayarları
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Mevzuat Veri Toplama Aracı")
    root.geometry("1000x800")  # Daha geniş pencere

    # Ana frame
    main_frame = ctk.CTkFrame(root, fg_color="transparent")
    main_frame.pack(padx=40, pady=30, fill="both", expand=True)

    # Başlık
    title_label = ctk.CTkLabel(
        main_frame, 
        text="Mevzuat Veri Toplama Aracı", 
        font=("Segoe UI", 32, "bold"),
        text_color=["#1a1a1a", "#ffffff"]
    )
    title_label.pack(pady=(0, 30))

    # Giriş alanları için frame
    input_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    input_frame.pack(fill="x", pady=20)
    input_frame.grid_columnconfigure((0, 1), weight=1, pad=20)

    # Sol panel - Yıl girişleri
    year_frame = ctk.CTkFrame(input_frame)
    year_frame.grid(row=0, column=0, sticky="nsew", padx=10)

    year_label = ctk.CTkLabel(
        year_frame, 
        text="Yıl Aralığı", 
        font=("Segoe UI", 18, "bold"),
        pady=15
    )
    year_label.pack()

    entry_start_year = ctk.CTkEntry(
        year_frame, 
        placeholder_text="Başlangıç Yılı (min: 1900)",
        height=40,
        font=("Segoe UI", 14)
    )
    entry_start_year.pack(padx=20, pady=10, fill="x")

    entry_end_year = ctk.CTkEntry(
        year_frame, 
        placeholder_text=f"Bitiş Yılı (max: {datetime.now().year})",
        height=40,
        font=("Segoe UI", 14)
    )
    entry_end_year.pack(padx=20, pady=10, fill="x")

    # Sağ panel - Ayarlar
    settings_frame = ctk.CTkFrame(input_frame)
    settings_frame.grid(row=0, column=1, sticky="nsew", padx=10)

    settings_label = ctk.CTkLabel(
        settings_frame, 
        text="Çıktı Ayarları", 
        font=("Segoe UI", 18, "bold"),
        pady=15
    )
    settings_label.pack()

    entry_filename = ctk.CTkEntry(
        settings_frame, 
        placeholder_text="Çıktı Dosya Adı",
        height=40,
        font=("Segoe UI", 14)
    )
    entry_filename.pack(padx=20, pady=10, fill="x")
    entry_filename.insert(0, "mevzuat.json")

    mevzuat_turu_var = ctk.StringVar(value="Kanun")
    mevzuat_turu = ctk.CTkComboBox(
        settings_frame,
        values=list(MevzuatMetadataScraper.MEVZUAT_TURLERI.keys()),
        height=40,
        font=("Segoe UI", 14),
        dropdown_font=("Segoe UI", 14),
        variable=mevzuat_turu_var
    )
    mevzuat_turu.pack(padx=20, pady=10, fill="x")

    # Belirli kanun arama alanı
    search_frame = ctk.CTkFrame(main_frame)
    search_frame.pack(fill="x", pady=20)

    search_label = ctk.CTkLabel(
        search_frame, 
        text="Belirli Kanun Arama", 
        font=("Segoe UI", 18, "bold"),
        pady=15
    )
    search_label.pack()

    entry_search_term = ctk.CTkEntry(
        search_frame, 
        placeholder_text="Kanun adı veya anahtar kelime girin (örn: Türk Ceza Kanunu)",
        height=40,
        font=("Segoe UI", 14)
    )
    entry_search_term.pack(padx=20, pady=10, fill="x")

    specific_search_button = ctk.CTkButton(
        search_frame,
        text="Belirli Kanunu Ara ve Çek",
        command=search_specific,
        height=45,
        font=("Segoe UI", 14),
        fg_color=["#ff6b35", "#ff6b35"],
        hover_color=["#e55a2b", "#e55a2b"]
    )
    specific_search_button.pack(padx=20, pady=10, fill="x")

    # İşlem butonları
    button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    button_frame.pack(fill="x", pady=30)
    button_frame.grid_columnconfigure((0, 1), weight=1, pad=20)

    # Tam Metin İşlemleri
    text_ops_frame = ctk.CTkFrame(button_frame)
    text_ops_frame.grid(row=0, column=0, sticky="nsew", padx=10)

    text_label = ctk.CTkLabel(
        text_ops_frame, 
        text="Tam Metin İşlemleri", 
        font=("Segoe UI", 18, "bold"),
        pady=15
    )
    text_label.pack()

    submit_button = ctk.CTkButton(
        text_ops_frame,
        text="Yıl Aralığına Göre Tüm Metni Çek",
        command=on_submit,
        height=45,
        font=("Segoe UI", 14),
        fg_color=["#2d7cd6", "#2d7cd6"],
        hover_color=["#2666b0", "#2666b0"]
    )
    submit_button.pack(padx=20, pady=10, fill="x")

    all_button = ctk.CTkButton(
        text_ops_frame,
        text="Tüm Metinleri Çek",
        command=fetch_all,
        height=45,
        font=("Segoe UI", 14),
        fg_color=["#2d7cd6", "#2d7cd6"],
        hover_color=["#2666b0", "#2666b0"]
    )
    all_button.pack(padx=20, pady=10, fill="x")

    # Meta Veri İşlemleri
    meta_ops_frame = ctk.CTkFrame(button_frame)
    meta_ops_frame.grid(row=0, column=1, sticky="nsew", padx=10)

    meta_label = ctk.CTkLabel(
        meta_ops_frame, 
        text="Meta Veri İşlemleri", 
        font=("Segoe UI", 18, "bold"),
        pady=15
    )
    meta_label.pack()

    metadata_button = ctk.CTkButton(
        meta_ops_frame,
        text="Yıl Aralığına Göre Meta Veri Çek",
        command=fetch_metadata,
        height=45,
        font=("Segoe UI", 14),
        fg_color=["#2d7cd6", "#2d7cd6"],
        hover_color=["#2666b0", "#2666b0"]
    )
    metadata_button.pack(padx=20, pady=10, fill="x")

    all_metadata_button = ctk.CTkButton(
        meta_ops_frame,
        text="Tüm Meta Verileri Çek",
        command=fetch_all_metadata,
        height=45,
        font=("Segoe UI", 14),
        fg_color=["#2d7cd6", "#2d7cd6"],
        hover_color=["#2666b0", "#2666b0"]
    )
    all_metadata_button.pack(padx=20, pady=10, fill="x")

    # Bilgi metni
    info_frame = ctk.CTkFrame(main_frame)
    info_frame.pack(fill="x", pady=20)
    
    info_text = """Tam Metin: Mevzuatın tam içeriğini çeker (Selenium kullanır)
Meta Veri: Sadece özet bilgileri çeker
Belirli Kanun Arama: Anahtar kelimeye göre kanun arar ve çeker"""
    
    info_label = ctk.CTkLabel(
        info_frame,
        text=info_text,
        font=("Segoe UI", 12),
        justify="left",
        wraplength=900,
        pady=15
    )
    info_label.pack(padx=20)

    root.mainloop()

def validate_years(start_year, end_year):
    current_year = datetime.now().year

    if not start_year or not end_year:
        messagebox.showerror("Hata", "Başlangıç ve Bitiş yılı boş bırakılamaz.")
        return None, None

    if not start_year.isdigit() or not end_year.isdigit():
        messagebox.showerror("Hata", "Yıllar sayısal olmalı.")
        return None, None

    start_year = int(start_year)
    end_year = int(end_year)

    if start_year < 1900:
        messagebox.showerror("Hata", "Başlangıç yılı en az 1900 olmalıdır.")
        return None, None

    if end_year > current_year:
        messagebox.showerror("Hata", f"Bitiş yılı en fazla {current_year} olabilir.")
        return None, None

    if start_year > end_year:
        messagebox.showerror("Hata", "Başlangıç yılı, bitiş yılından büyük olamaz.")
        return None, None

    return start_year, end_year

if __name__ == "__main__":
    start_gui()