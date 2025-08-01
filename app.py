from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import os
import subprocess
import threading
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Veri dosyası yolu
DATA_FILE = 'data/parsed_output.json'
RELATIONS_FILE = 'data/relations.json'

class DataUpdateHandler(FileSystemEventHandler):
    """JSON dosyası değişikliklerini izler"""
    def on_modified(self, event):
        if event.src_path.endswith('parsed_output.json'):
            print(f"Veri dosyası güncellendi: {event.src_path}")
            socketio.emit('data_updated', {'message': 'Kanun verileri güncellendi'})

def start_file_watcher():
    """Dosya izleyiciyi başlatır"""
    event_handler = DataUpdateHandler()
    observer = Observer()
    observer.schedule(event_handler, path='data/', recursive=False)
    observer.start()
    return observer

class LawManager:
    """Kanun işlemlerini yöneten sınıf"""
    
    def __init__(self):
        self.ensure_data_dir()
    
    def ensure_data_dir(self):
        """Data klasörünün varlığını kontrol eder"""
        if not os.path.exists('data'):
            os.makedirs('data')
    
    def add_law(self, law_number):
        """Yeni kanun ekler"""
        try:
            # 1. Kanunu çek
            result1 = subprocess.run([
                'python', 'specific_law_scraper.py', 
                '--search', str(law_number),
                '--output', 'mevzuat.json',
                '--append'
            ], capture_output=True, text=True, timeout=300)
            
            if result1.returncode != 0:
                return False, f"Kanun çekme hatası: {result1.stderr}"
            
            # 2. Parse et
            result2 = subprocess.run([
                'python', 'data_processing/mevzuat_parser.py'
            ], capture_output=True, text=True, timeout=300)
            
            if result2.returncode != 0:
                return False, f"Parse etme hatası: {result2.stderr}"
            
            # 3. Parsed dosyayı data klasörüne taşı
            if os.path.exists('parsed_output.json'):
                os.rename('parsed_output.json', DATA_FILE)
            
            return True, f"Kanun {law_number} başarıyla eklendi"
            
        except subprocess.TimeoutExpired:
            return False, "İşlem zaman aşımına uğradı"
        except Exception as e:
            return False, f"Beklenmeyen hata: {str(e)}"
    
    def get_laws(self):
        """Tüm kanunları getirir"""
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # JSON bir liste ise
                    if isinstance(data, list):
                        return data
                    # JSON bir dict ise
                    elif isinstance(data, dict):
                        return data
                    return []
            return []
        except Exception as e:
            print(f"Veri okuma hatası: {e}")
            return []
    
    def find_law_article(self, law_number, article_number):
        """Belirli bir kanun maddesini bulur - gelişmiş arama"""
        laws_data = self.get_laws()
        search_log = []
        
        # JSON yapısına göre arama
        if isinstance(laws_data, list):
            search_log.append(f"Liste formatında {len(laws_data)} kanun aranıyor")
            
            for i, law in enumerate(laws_data):
                kanun_no = str(law.get('kanun_numarasi', ''))
                search_log.append(f"Kanun {i}: {kanun_no} == {law_number} ?")
                
                if kanun_no == str(law_number):
                    search_log.append(f"Kanun bulundu: {law.get('Kanun Adı', '')}")
                    maddeler = law.get('maddeler', [])
                    search_log.append(f"Madde sayısı: {len(maddeler)}")
                    
                    for j, madde in enumerate(maddeler):
                        madde_no_original = madde.get('madde_numarasi', '')
                        
                        # Farklı formatları test et
                        possible_formats = [
                            madde_no_original,  # Orijinal
                            madde_no_original.replace('Madde ', '').strip(),  # "Madde 1" -> "1"
                            madde_no_original.replace('madde ', '').strip(),  # küçük harf
                            madde_no_original.replace('MADDE ', '').strip(),  # büyük harf
                            madde_no_original.split()[-1] if ' ' in madde_no_original else madde_no_original,  # Son kelime
                        ]
                        
                        search_log.append(f"Madde {j}: {madde_no_original} -> {possible_formats}")
                        
                        for format_version in possible_formats:
                            if str(format_version) == str(article_number):
                                search_log.append(f"EŞLEŞME: {format_version} == {article_number}")
                                
                                return {
                                    'lawTitle': law.get('Kanun Adı', ''),
                                    'lawNumber': law.get('kanun_numarasi', ''),
                                    'articleNumber': format_version,
                                    'articleTitle': madde_no_original,
                                    'articleContent': madde.get('text', ''),
                                    'search_log': search_log  # Debug için
                                }
        
        # Dict formatında arama (eski yapı için yedek)
        elif isinstance(laws_data, dict):
            search_log.append(f"Dict formatında {len(laws_data)} anahtar aranıyor")
            # Önceki dict mantığı...
        
        search_log.append(f"Madde bulunamadı: {law_number}-{article_number}")
        print("Arama Log:", search_log)  # Server konsoluna yazdır
        return None
    
    def save_relations(self, relations):
        """İlişkileri dosyaya kaydeder"""
        try:
            with open(RELATIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(relations, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"İlişki kaydetme hatası: {e}")
            return False
    
    def load_relations(self):
        """Kaydedilmiş ilişkileri yükler"""
        try:
            if os.path.exists(RELATIONS_FILE):
                with open(RELATIONS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"İlişki yükleme hatası: {e}")
            return []

# Global nesne
law_manager = LawManager()

@app.route('/')
def index():
    """Ana sayfa"""
    return render_template('index.html')

@app.route('/api/test/raw_data')
def api_test_raw_data():
    """Ham veriyi görmek için test endpoint"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                raw_content = f.read()
                
            # İlk 2000 karakteri göster
            preview = raw_content[:2000] + "..." if len(raw_content) > 2000 else raw_content
            
            return jsonify({
                'file_exists': True,
                'file_size': len(raw_content),
                'preview': preview,
                'first_chars': raw_content[:500] if raw_content else "Empty file"
            })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'file_exists': os.path.exists(DATA_FILE)
        })

@app.route('/api/test/search_all_articles/<law_number>')
def api_test_search_articles(law_number):
    """Belirli bir kanunun tüm maddelerini listele"""
    laws_data = law_manager.get_laws()
    result = {
        'law_number_searched': law_number,
        'data_type': type(laws_data).__name__,
        'found_law': None,
        'all_articles': [],
        'search_debug': []
    }
    
    if isinstance(laws_data, list):
        for i, law in enumerate(laws_data):
            kanun_no = law.get('kanun_numarasi', '')
            result['search_debug'].append({
                'index': i,
                'kanun_numarasi': kanun_no,
                'kanun_adi': law.get('Kanun Adı', ''),
                'matches': str(kanun_no) == str(law_number)
            })
            
            if str(kanun_no) == str(law_number):
                result['found_law'] = {
                    'kanun_numarasi': kanun_no,
                    'Kanun Adı': law.get('Kanun Adı', ''),
                    'maddeler_count': len(law.get('maddeler', []))
                }
                
                for madde in law.get('maddeler', []):
                    madde_no = madde.get('madde_numarasi', '')
                    result['all_articles'].append({
                        'original': madde_no,
                        'cleaned': madde_no.replace('Madde ', '').strip() if madde_no.startswith('Madde ') else madde_no,
                        'text_preview': madde.get('text', '')[:100] + '...' if len(madde.get('text', '')) > 100 else madde.get('text', '')
                    })
                break
    
    return jsonify(result)

@app.route('/api/debug/laws')
def api_debug_laws():
    """Debug için kanun yapısını getirir"""
    laws_data = law_manager.get_laws()
    debug_info = {
        'data_type': type(laws_data).__name__,
        'data_length': len(laws_data) if laws_data else 0,
        'sample_structure': {}
    }
    
    if isinstance(laws_data, list) and len(laws_data) > 0:
        debug_info['sample_structure'] = {
            'first_law_keys': list(laws_data[0].keys()) if laws_data[0] else [],
            'first_law_sample': laws_data[0] if laws_data[0] else {}
        }
    elif isinstance(laws_data, dict) and laws_data:
        first_key = list(laws_data.keys())[0]
        debug_info['sample_structure'] = {
            'first_key': first_key,
            'first_law_keys': list(laws_data[first_key].keys()) if laws_data[first_key] else [],
            'first_law_sample': laws_data[first_key] if laws_data[first_key] else {}
        }
    
    return jsonify(debug_info)

@app.route('/api/debug/find_article', methods=['POST'])
def api_debug_find_article():
    """Debug için madde arama"""
    data = request.json
    law_number = data.get('law_number')
    article_number = data.get('article_number')
    
    laws_data = law_manager.get_laws()
    debug_info = {
        'search_params': {'law_number': law_number, 'article_number': article_number},
        'data_type': type(laws_data).__name__,
        'found_laws': [],
        'found_articles': []
    }
    
    # Kanunları ara
    if isinstance(laws_data, list):
        for law in laws_data:
            kanun_no = law.get('kanun_numarasi', '')
            if str(kanun_no) == str(law_number):
                debug_info['found_laws'].append({
                    'kanun_numarasi': kanun_no,
                    'Kanun Adı': law.get('Kanun Adı', ''),
                    'maddeler_count': len(law.get('maddeler', []))
                })
                
                # Maddeleri ara
                for madde in law.get('maddeler', []):
                    madde_no = madde.get('madde_numarasi', '')
                    madde_no_clean = madde_no.replace('Madde ', '').strip() if madde_no.startswith('Madde ') else madde_no
                    debug_info['found_articles'].append({
                        'madde_numarasi': madde_no,
                        'madde_no_clean': madde_no_clean,
                        'matches': str(madde_no_clean) == str(article_number),
                        'text_preview': madde.get('text', '')[:100] + '...' if len(madde.get('text', '')) > 100 else madde.get('text', '')
                    })
    
    article = law_manager.find_law_article(law_number, article_number)
    debug_info['result'] = article
    
    return jsonify(debug_info)

@app.route('/api/laws')
def api_get_laws():
    """Tüm kanunları API ile getirir"""
    return jsonify(law_manager.get_laws())

@app.route('/api/add_law', methods=['POST'])
def api_add_law():
    """Yeni kanun ekler"""
    data = request.json
    law_number = data.get('law_number')
    
    if not law_number:
        return jsonify({'success': False, 'message': 'Kanun numarası gerekli'})
    
    # Arka planda çalıştır
    def add_law_async():
        success, message = law_manager.add_law(law_number)
        socketio.emit('law_add_result', {
            'success': success, 
            'message': message,
            'law_number': law_number
        })
    
    thread = threading.Thread(target=add_law_async)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Kanun ekleme işlemi başlatıldı'})

@app.route('/api/find_article', methods=['POST'])
def api_find_article():
    """Kanun maddesi arar"""
    data = request.json
    law_number = data.get('law_number')
    article_number = data.get('article_number')
    
    article = law_manager.find_law_article(law_number, article_number)
    if article:
        return jsonify({'success': True, 'article': article})
    else:
        return jsonify({'success': False, 'message': 'Madde bulunamadı'})

@app.route('/api/relations', methods=['GET', 'POST'])
def api_relations():
    """İlişkileri getirir veya kaydeder"""
    if request.method == 'GET':
        return jsonify(law_manager.load_relations())
    
    elif request.method == 'POST':
        relations = request.json
        success = law_manager.save_relations(relations)
        socketio.emit('relations_updated', relations)
        return jsonify({'success': success})

@socketio.on('connect')
def handle_connect():
    """Client bağlandığında"""
    print('Client connected')
    emit('connected', {'message': 'Bağlantı kuruldu'})

@socketio.on('disconnect')
def handle_disconnect():
    """Client bağlantısı kesildiğinde"""
    print('Client disconnected')

@socketio.on('request_data_update')
def handle_data_update():
    """Client veri güncellemesi istediğinde"""
    emit('data_updated', {'message': 'Veri güncellendi'})

if __name__ == '__main__':
    # Dosya izleyiciyi başlat
    observer = start_file_watcher()
    
    try:
        print("🏛️  Kanun Görselleştirici başlatılıyor...")
        print("📊 http://localhost:5000 adresinde çalışacak")
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()