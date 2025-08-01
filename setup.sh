#!/bin/bash

# Kanun Görselleştirici Kurulum ve Çalıştırma Scripti

echo "🏛️  Kanun Görselleştirici Kurulum Başlıyor..."

# Virtual environment oluştur
echo "📦 Virtual environment oluşturuluyor..."
python -m venv venv

# Virtual environment'ı aktif et
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Gereksinimleri yükle
echo "📥 Gereksinimler yükleniyor..."
pip install -r requirements.txt

# Klasör yapısını oluştur
echo "📁 Klasör yapısı oluşturuluyor..."
mkdir -p templates
mkdir -p static/css
mkdir -p static/js
mkdir -p data

# Mevcut scriptlerin varlığını kontrol et
if [ ! -f "specific_law_scraper.py" ]; then
    echo "⚠️  specific_law_scraper.py bulunamadı. Lütfen bu dosyayı ana dizine koyun."
fi

if [ ! -d "data_processing" ]; then
    echo "⚠️  data_processing klasörü bulunamadı. Lütfen bu klasörü ana dizine koyun."
fi

echo "✅ Kurulum tamamlandı!"
echo ""
echo "🚀 Uygulamayı başlatmak için:"
echo "   python app.py"
echo ""
echo "🌐 Uygulama http://localhost:5000 adresinde çalışacak"
echo ""
echo "💡 Özellikler:"
echo "   • Yeni kanun ekleme (otomatik scraping + parsing)"
echo "   • Kanun maddeleri arası ilişki kurma"
echo "   • İnteraktif network görselleştirme"
echo "   • Gerçek zamanlı güncellemeler"
echo "   • Otomatik dosya izleme"