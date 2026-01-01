# 🎓 OBS Grade Puller

**Malatya Turgut Özal Üniversitesi** Öğrenci Bilgi Sistemi (OBS) için geliştirilmiş; hızlı, güvenli ve modern bir terminal tabanlı not görüntüleme aracıdır.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen)

## Yapılacaklar
- Aynı şirketin yaptığı OBS sistemlerini kullanan okullar için, okul seçimine izin veren bir dropdown. Kayıtlı hesaba okul bilgisi de eklenecek.

## Projenin Amacı

Standart OBS arayüzünün yavaşlığı ve karmaşıklığı yerine; notları, harf durumlarını ve **sınıf ortalamalarını** tek bir ekranda, saniyeler içinde görüntülemek için tasarlanmıştır.

> **Önemli Fark:** OBS sisteminde sınıf ortalamalarını görmek için her dersin detayına tek tek girmeniz gerekir. Bu araç, **Reverse Engineering** yöntemleri kullanarak arka plandaki gizli API'leri tetikler ve Vize/Final/Büt için ayrı ayrı sınıf ortalamalarını getirip kendi notunuzla kıyaslar.

## Özellikler

* ** Hız:** Selenium veya Playwright gibi hantal tarayıcı otomasyonları yerine, doğrudan `requests` ile HTTP protokolü üzerinden konuşur. Çok daha az kaynak tüketir.
* ** Güvenli Kasa (Keyring):** Şifrenizi asla açık metin (plain-text) olarak saklamaz. İşletim sisteminin kendi güvenli kasasını (Windows Credential Manager, macOS Keychain vb.) kullanır. Yalnızca SİZİN BİLGİSAYARINIZA kaydeder. Herhangi bir yere göndermez.
* ** Detaylı Analiz:** Her sınav türü (Vize, Final, Bütünleme) için sınıf ortalamasını çeker. Notunuz ortalamanın altındaysa veya üstündeyse görsel olarak belirtir.
* ** Rich UI:** Terminal ekranında modern, renkli ve okunaklı tablolar sunar.
* ** Profil Yönetimi:** Birden fazla öğrenci hesabı ile kullanılabilir. Bilgileri `AppData/Local` altında düzenli saklar.

##  Mimari ve Teknoloji Yığını

Bu proje, **Clean Architecture** prensiplerine sadık kalınarak geliştirilmiştir. "God Script" mantığından uzak, modüler ve test edilebilir bir yapıya sahiptir.

* **Core:** Python
* **Network:** `requests` (Session management, Header spoofing)
* **Parsing:** `BeautifulSoup4` & `Regex` (State Machine mantığı ile HTML analizi)
* **Security:** `keyring`
* **UI:** `rich`

### Klasör Yapısı
```text
OBSGradePuller/
├── src/
│   ├── models.py          # Veri yapıları (Dataclasses)
│   ├── services/
│   │   ├── obs_client.py  # HTTP istekleri ve HTML parsing (Business Logic)
│   │   └── auth_manager.py # Profil ve şifreleme yönetimi
│   ├── ui/
│   │   └── display.py     # Terminal arayüzü ve tablo çizimleri
│   └── main.py            # Uygulama giriş noktası ve orkestrasyon
├── requirements.txt
└── README.md
```


## Kurulum

Projeyi yerel ortamınızda çalıştırmak için:

1. Repoyu klonlayın:
```Bash
git clone [https://github.com/kullaniciadi/OBSGradePuller.git](https://github.com/kullaniciadi/OBSGradePuller.git)
cd OBSGradePuller
```

2. Sanal ortam (venv) oluşturun:
```Bash
python -m venv .venv
# Windows için:
.\.venv\Scripts\activate
# Mac/Linux için:
source .venv/bin/activate
```

3. Bağımlılıkları yükleyin:
```Bash
pip install -r requirements.txt
```

4. Çalıştırın:
```Bash
    python -m src.main
```

## EXE Olarak Derleme (Build)

Uygulamayı tek bir .exe dosyası haline getirip taşınabilir şekilde kullanmak için PyInstaller kullanılır:
```Bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --console --name "OBSGradePuller" --paths . src/main.py
```

Oluşan dosya dist/ klasöründe yer alacaktır.


## Teknik Detaylar (Reverse Engineering)

Bu proje, ASP.NET WebForms altyapısına sahip OBS sisteminin çalışma mantığını simüle eder.
- ViewState Yönetimi: Sayfalar arası geçişte __VIEWSTATE ve __EVENTVALIDATION tokenlarını dinamik olarak yakalar ve taşır.
- AJAX Spoofing: Sınıf ortalaması verisi, normalde bir butona tıklandığında UpdatePanel içinde yüklenen bir iframe aracılığıyla gelir. Araç, sunucuya özel X-MicrosoftAjax: Delta=true başlıkları ve doğru ScriptManager parametreleri ile istek atarak bu verinin oluşmasını tetikler (Trigger) ve oluşan gizli URL'i yakalar.

## Yasal Uyarı

Bu proje tamamen eğitim amaçlı geliştirilmiştir.
- Kişisel verilerinizi sunuculara göndermez, sadece sizin bilgisayarınızda ve üniversite sunucuları arasında iletişim kurar.
- Üniversite sunucularına aşırı yük bindirecek (DDOS vb.) döngüler içermez.
- Kullanımdan doğabilecek sorumluluk kullanıcıya aittir.

Geliştirici: Eren Keskinoğlu Lisans: MIT
