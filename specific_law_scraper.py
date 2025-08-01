#!/usr/bin/env python3
# specific_law_scraper.py
# KANUN ÇEKİP JSONA KAYDETMEK: 
  # python specific_law_scraper.py --search "5237" --output mevzuat.json --append
# Mevzuat Verilerini Ayrıştırma
  # python data_processing/mevzuat_parser.py


import argparse
import sys
import os
import json
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Proje dizinini Python path'ine ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mevzuat_scraper.spiders.mevzuat_spider import MevzuatSeleniumSpider

def merge_json_files(output_file, temp_file):
    # Eğer hedef dosya varsa aç ve JSON array olarak oku, yoksa boş liste al
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
            except Exception:
                data = []
    else:
        data = []

    # Temp dosyadan satır satır json objesi oku ve listeye ekle
    with open(temp_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line)
                data.append(item)
            except Exception:
                pass

    # Tüm veriyi JSON array olarak output_file'a yaz
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Temp dosyayı sil
    os.remove(temp_file)

def main():
    parser = argparse.ArgumentParser(description='Belirli kanunları mevzuat.gov.tr\'den çeker')
    parser.add_argument('--search', '-s', required=True, help='Aranacak kanun adı veya anahtar kelime')
    parser.add_argument('--output', '-o', default='mevzuat.json', help='Çıktı dosyası adı (varsayılan: mevzuat.json)')
    parser.add_argument('--type', '-t', default='Kanun', 
                       choices=['Kanun', 'Cumhurbaşkanlığı Kararnamesi', 'Kanun Hükmünde Kararname', 'Tüzük', 'Tebliğ'],
                       help='Mevzuat türü (varsayılan: Kanun)')
    parser.add_argument('--append', '-a', action='store_true', 
                       help='Mevcut dosyaya ekle (varsayılan: dosyayı değiştir)')

    args = parser.parse_args()

    # Dosya uzantısını kontrol et ve json olarak ayarla
    if not args.output.endswith('.json'):
        args.output = os.path.splitext(args.output)[0] + '.json'

    # Geçici dosya jsonlines formatında
    temp_file = args.output + '.tmp.jsonl'

    # Scrapy ayarları — temp dosyaya jsonlines formatında yaz
    settings = get_project_settings()
    settings.set('FEEDS', {
        temp_file: {
            'format': 'jsonlines',
            'encoding': 'utf8',
            'overwrite': True,  # temp dosya her seferinde sıfırlansın
            'store_empty': False
        }
    })

    process = CrawlerProcess(settings)
    process.crawl(MevzuatSeleniumSpider, 
                 search_term=args.search,
                 mevzuat_turu=args.type)

    print(f"Arama terimi: {args.search}")
    print(f"Mevzuat türü: {args.type}")
    print(f"Çıktı dosyası: {args.output}")
    print(f"Mod: {'Ekle' if args.append else 'Üzerine yaz'}")
    print("Spider başlatılıyor...")

    process.start()  # Scrapy bitene kadar bekle

    # Append moddaysa, temp dosyayı ana json dosyaya ekle
    if args.append and os.path.exists(temp_file):
        merge_json_files(args.output, temp_file)
        print(f"Veriler {args.output} dosyasına eklendi.")
    else:
        # Append değilse, temp dosyayı normal json array olarak çıktı dosyasına taşı
        if os.path.exists(temp_file):
            with open(temp_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            items = [json.loads(line) for line in lines]
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            os.remove(temp_file)
            print(f"Veriler {args.output} dosyasına yazıldı.")

if __name__ == "__main__":
    main()
