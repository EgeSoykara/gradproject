# PortföyAI teslim kontrolü

Hedef, Python 3.13 ile Windows'ta çalışan yerel bir portföy takip uygulaması. İşlev listesi için [gereksinimler](SRS.md), kurulum için [README](../README.md) ve arşiv paketi için [motor kurulumu](../UI_README.md) esas alınır.

## Yazılım ve yerel kabul

| Alan | Teslim edilen davranış | Doğrulama |
| --- | --- | --- |
| Kurulum ve açılış | Kurulum bağımlılıkları yükler, veritabanını hazırlar ve demo verisini üretir. Başlatma komutu önce bekleyen veritabanı geçişlerini uygular. | Windows'ta temiz klasör kurulumu, arşivli kurulum ve başlatma komutuyla HTTP açılışı |
| Hesaplar ve erişim | Kayıt, giriş, çıkış, kişisel portföy seçimi ve kullanıcıya özel notlar. Ortak piyasa verisini yönetici yükler. | Hesap, sahiplik ve yönetici yetkisi testleri |
| İlk kullanım | Eğitim portföyü veya kişisel portföy oluşturma, nakit ekleme ve ilk alış. Eğitim verisi gerekirse yeniden üretilir. | Yedekten açılan sistemde HTTP üzerinden kayıt, nakit ve ilk alış |
| İşlemler | Alış, satış, para yatırma ve çekme, komisyon, düzenleme, silme ve CSV hareket dökümü. Geçersiz işlem bakiyeyi değiştirmez. | Ağırlıklı maliyet, kısmi satış, yetersiz nakit, geçmiş işlem ve geri alma testleri |
| Değerleme | TRY, USD, EUR ve GBP. Fiyat ve kur kaynağı, veri tarihi ve eksik kalemler görünür. Arşiv portföyünün varsayılan tarihi arşivle birlikte ilerler ve daha yeni işlemleri hesaba katar. | Ondalık değer, kur, eski fiyat, eksik kur, arşiv tarihi ve API testleri |
| Veri aktarımı | Yönetici arayüzünde CSV ve JSON, indirilebilir CSV şablonu ve işlem geçmişi. Geçersiz yüklemede önceki veriler korunur. | Yetki, iki dosya türü, kayıtların korunması ve aktarım geçmişi testleri |
| Genel Bakış ve Kıyaslama | Dağılım, zaman ağırlıklı getiri, para birimi ve dönem filtreleri. Geçmişin eksik olması güncel değerlemeyi gizlemez. | Nakit akışı, fiyat geçmişi, seçili dönem ve kıyaslama verisi testleri |
| Risk ve sağlamlık | Panelde portföy başına tek sağlamlık puanı. Eğitim ve piyasa portföyünde yeterli geçmiş varsa hesap yöntemi gösterilir. Arşiv portföyünde analizi yerel motor üretir. Uzman modunda oynaklık, düşüş, Sharpe, korelasyon ve veri kapsamına uygun tarihsel senaryolar. | Panel ve API puan tutarlılığı, korelasyon ve tarayıcıda arşiv görünümü |
| Dil ve profil | Türkçe ve İngilizce site dili, Başlangıç ve Uzman seviyeleri, arşiv analizi için Muhafazakâr, Dengeli ve Agresif profil. | İki dilin sayfaları ve profil–seviye kombinasyonları için testler |
| Modeller | Arşiv ZIP’i ile GRU fon görünümü ve FinTurkBERT haber duygu özeti. Eski analiz adresleri panele yönlenir. | Panel, eski adresler ve çevrimdışı model kontrolleri |
| Haber ve notlar | Kaynağı ve tarihi görünen haberler, panelde FinTurkBERT özeti ve kişisel not işlemleri. | Gerçek X isteklerini engelleyen otomatik testler, sağlayıcı örnekleri ve not erişimi testleri |
| Yedekleme | Yönetim komutu çalışır durumdaki SQLite veritabanından tutarlı kopya alır ve mevcut bir dosyanın üzerine yazmayı reddeder. | SQLite bütünlük kontrolü, yeni klasöre geri yükleme ve tarayıcı oturumunun HTTP üzerinden doğrulanması |
| Sürekli test | Windows üzerinde bağımlılık, Ruff, Django, veritabanı geçişleri ve test kontrollerini içeren GitHub Actions tanımı. | Aynı kontroller yerelde çalıştırıldı. GitHub çalıştırması, dosya GitHub'a ulaştığında izlenebilir. [Checkout](https://github.com/actions/checkout) · [Setup Python](https://github.com/actions/setup-python) |

Son yerel regresyon turunda 55 Django testi geçti. Django sistem kontrolü ve veritabanı geçişi kontrolü temiz. Ruff kod denetimi geçti. Depo genelinde Ruff biçim denetimi ayrıca biçim farkları bildiriyor.

## Dış doğrulamalar

- [ ] Seçilen canlı sağlayıcılarda yetkili hesaplarla erişim, veri kapsamı ve yeniden eşitleme doğrulansın. Ücretli API çağrıları test turunda yapılmadı. Dosya yükleme ve örnek yanıtlarla sağlayıcı işleme akışı doğrulandı.
- [ ] Ege dışında bir kullanıcı kendi Windows bilgisayarında kurulum, demo, ilk işlem ve veri hata mesajları üzerinden kabul turunu tamamlasın. Telefon boyutunda temel akışlar bu turda gözden geçirilsin.
- [ ] Gerekli arşiv paketini ve varsa sağlayıcı ayarlarını yetkili kullanıcılara özel kanaldan ulaştır. Standart kurulum eğitim portföyü ve işlem kayıtlarıyla açılır. GRU ve FinTurkBERT için arşiv ZIP’i kurulur.

## Teslim öncesi tekrar çalıştırma

```powershell
.\setup.ps1
.\start.ps1
```

Tarayıcıda eğitim portföyünü aç. Başlangıç ve Uzman görünümlerini, dil değişimini ve veri tarihleri bağlantısını dene. Ayrı bir hesap ile portföy oluştur, nakit ekle ve fiyatı bulunan bir varlığın alışını kaydet. Yönetici hesabıyla bir fiyat dosyası yükle, bağlantı geçmişindeki sonucu kontrol et ve README'deki yedeği yeni bir dosyaya al.

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```
