# Personel Servisi Atama Sistemi

Windows masaüstü personel servisi atama uygulamasının PySide6 ve SQLAlchemy tabanlı
proje iskeletidir.

Bu aşamada aşağıdaki altyapı hazırdır:

- Açılıp kapanabilen temel PySide6 ana penceresi
- AppData altında çalışan SQLite veritabanı
- SQLAlchemy model ve ilişki tanımları
- Ayrı engine, oturum ve repository katmanları
- Uygulama başlangıcında otomatik tablo oluşturma
- Konsol ve dönen dosya logları
- Veritabanı bütünlük testleri
- Personel, servis kapasitesi ve servis güzergâhı sütun eşleştirme altyapısı
- Arayüzden ve veritabanından bağımsız satır normalizasyonu ve doğrulaması
- Normalizasyon ve doğrulama birim testleri
- Excel çalışma kitabı ve dolu/boş sayfa okuma altyapısı
- Dosya türü tahmini ve değiştirilebilir sütun eşleştirme planı
- İş parçacığında çalışan doğrulama ve filtrelenebilir önizleme ekranı
- Servis kapasite kayıtları için aktarım öncesi özet ve çakışma seçimi
- Transaction ile yeni fiziksel servis/servis vardiyası ekleme ve kontrollü güncelleme

Yalnızca doğrulanmış Servis Kapasite Excel kayıtları kullanıcı onayıyla veritabanına
aktarılabilir. Personel ve servis güzergâhı Excel aktarımı, yönetim ekranları, harita,
atama algoritması, PyInstaller ve Inno Setup özellikleri henüz geliştirilmemiştir.

## Gereksinimler

- Windows 10 veya Windows 11
- Python 3.11 veya daha yeni bir Python 3 sürümü

## İlk kurulum

VS Code içinde proje klasörünü açın ve PowerShell terminalinde sırayla çalıştırın:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Mevcut `.venv` başka bir Python kurulumuna bağlı olduğu için çalışmıyorsa klasörü
kaldırıp yukarıdaki sanal ortam oluşturma komutunu yeniden çalıştırın.

## Git ve veri güvenliği

Repository yalnızca uygulama kaynak kodunu ve testleri içermelidir. Personel Excel
dosyaları, proje PDF'leri, dışa aktarılan raporlar, SQLite veritabanları, loglar,
yedekler, `.env` dosyaları ve sanal ortam Git'e eklenmemelidir. Bu dosya türleri
`.gitignore` ile kapsam dışı bırakılmıştır.

Gerçek uygulama veritabanı ve loglar proje klasörünün dışında, kullanıcının
`%LOCALAPPDATA%\ServisAtama` klasöründe saklanır. Kaynak kodda parola, API anahtarı
veya kişisel personel verisi tutulmamalıdır.

## Uygulamayı çalıştırma

```powershell
.\.venv\Scripts\python.exe main.py
```

Uygulama açılırken eksik SQLAlchemy tabloları otomatik oluşturulur.

## Servis kapasite aktarımı

Servis Kapasite dosyasını seçip analiz ettikten sonra `Geçerli Servis Kayıtlarını
Aktar` butonunu kullanın. Aktarım öncesi özet penceresi yeni servisleri, yeni vardiya
kayıtlarını, çakışmaları, hataları ve uyarıları gösterir. Çakışmalarda varsayılan
seçenek mevcut kaydı koruyup Excel satırını atlamaktır; istenirse kapasite, rota adı
ve aktiflik bilgileri güncellenebilir. Aktarım tek transaction içinde yürütülür.

## Testleri çalıştırma

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Testler geçici bir SQLite veritabanı kullanır; gerçek uygulama veritabanına örnek
personel veya servis kaydı eklemez.

## Yerel veri dosyaları

```text
%LOCALAPPDATA%\ServisAtama\
|-- data\
|   `-- servis_atama.db
`-- logs\
    `-- servis_atama.log
```

## Veritabanı tabloları

- `personel`
- `sofor`
- `servis`
- `servis_vardiya`
- `servis_guzergah_noktasi`
- `servis_guzergah_geometrisi`
- `atama`
- `adres_onbellek`
- `ayar`

## Proje yapısı

```text
personel_servisi_atama_sistemi/
|-- main.py
|-- requirements.txt
|-- README.md
|-- app/
|-- database/
|   |-- connection.py
|   |-- session.py
|   |-- init_db.py
|   |-- models/
|   `-- repositories/
|-- excel_import/
|-- normalization/
|-- services/
|-- tests/
`-- ui/
```
