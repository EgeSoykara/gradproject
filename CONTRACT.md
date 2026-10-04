# PortföyAI geliştirme sözleşmesi

Sürüm: 1.0 — 1 Ekim 2026  
Durum: Kullanıcı kararları alındı; geliştirme kapsamı kesinleştirildi.

Bu belge, Python ve Django ile geliştirilecek AI-Assisted Portfolio Management System projesinin kapsamını, teslimlerini ve kabul kriterlerini belirler. Hukuki bir hizmet sözleşmesi değil, geliştirme boyunca esas alınacak teknik çalışma mutabakatıdır. Açık kararlar kullanıcıyla netleştirildikten sonra güncellenir ve uygulamaya geçilir.

## 1. Dayanak ve öncelikler

- Gereksinim kaynağı: `Graduation Projects Proposal Form_ H. Altıncay.docx`. Belgenin proje özeti, detaylı şartnamesi, kısıtları ve yedi teslim kalemi incelendi.
- Kullanıcının teknoloji kararı: Python ve Django.
- Bulunan Stitch referansı: **PortföyAI — Akıllı Portföy Yönetimi**, proje kimliği `15540356392388727426`. Genel Bakış, Varlıklarım, AI Analiz ve Karşılaştırma ekranları ile tasarım sistemi mevcut.
- Kullanıcının açık kararları bu taslağın varsayımlarından önce gelir. DOCX gereksinimleri sessizce kaldırılmaz; değişiklikler bu dosyada kayda geçirilir.
- DOCX'teki STG/TL/EURO ifadeleri uygulamada GBP/TRY/EUR olarak standartlaştırılır.

## 2. Amaç ve kullanım sınırı

Kullanıcı, TEFAS fonlarını ve gram bazlı altın, gümüş, platin varlıklarını manuel işlem kayıtlarıyla takip eder; portföyünü farklı para birimlerinde inceler; performansını kıyaslar ve tarihsel verilere dayalı risk ve tahmin analizleri görür. Haberler, sosyal medya duygu analizi ve kişisel notlar karar desteğini tamamlar.

Uygulama eğitim amaçlıdır. Gerçek banka bağlantısı, banka parolası saklama, emir iletimi ve otomatik alım satım kapsam dışıdır. Analizlerde belirsizlik, kullanılan veri dönemi ve yöntemin sınırları görünür olur.

## 3. İşlevsel kapsam

| Kimlik | Modül | Teslim edilecek davranış |
| --- | --- | --- |
| F01 | Hesaplar | Kayıt, giriş, çıkış; kullanıcıya ait verilerin erişim kontrolü; yönetici için Django admin. Çok kullanıcılı yapı öneridir ve karar bekler. |
| F02 | Portföy ve işlemler | Fon adedi ve metal gramı ile alış/satış kaydı; tarih, fiyat, para birimi, miktar ve isteğe bağlı komisyon; işlemleri düzenleme/silme sonrası tutarlı yeniden hesaplama. |
| F03 | Değerleme | Maliyet, eldeki miktar, güncel değer, gerçekleşmiş ve gerçekleşmemiş kâr/zarar; TRY, USD, EUR ve GBP görünümü. Nakit ve para giriş/çıkışları ayrıca takip edilir. |
| F04 | Veri entegrasyonu | TEFAS, metaller, döviz ve kıyaslama varlıkları için değiştirilebilir veri sağlayıcıları; geçmiş veri toplama, temizleme, önbellekleme ve tekrarsız güncelleme. |
| F05 | Dashboard | Toplam değer, dağılım pasta grafiği, tarihsel performans çizgisi, tarih ve para birimi filtreleri, varlık listesi ve veri güncellik bilgisi. |
| F06 | Karşılaştırma | S&P 500, NASDAQ 100 ve Bitcoin seçenekleri; aynı tarih aralığı ve para biriminde normalize edilmiş portföy ve benchmark getirileri. |
| F07 | Dayanıklılık | Volatilite, maksimum düşüş, Sharpe oranı, çeşitlendirme/korelasyon analizi; tarihsel stres senaryoları ve yöntemi açıklanan 0–100 dayanıklılık skoru. |
| F08 | Yatırım rehberi | Tarihsel verilerle eğitilmiş zaman serisi veya makine öğrenmesi modeli; kullanıcı bakiyesi ve risk tercihiyle açıklanabilir aday varlık sıralaması; eğitim ve değerlendirme raporu. |
| F09 | Haber ve duygu analizi | Ekonomi haber başlıkları, kaynak bağlantıları ve tarihleri; erişilebilen X/Twitter verilerinden olumlu/nötr/olumsuz duygu dağılımı, örneklem ve yöntem açıklaması. Canlı sosyal veri erişimi açık karardır. |
| F10 | Notlar | Kullanıcıya özel not oluşturma, düzenleme ve silme; gelecek planlarını kaydetme. |

S&P 500, NASDAQ 100 ve Bitcoin ilk kapsamda karşılaştırma araçlarıdır; bunların doğrudan portföy varlığı olarak alım/satım kaydı ayrı kapsam kararıdır. Ek ekranlar, bulunan Stitch tasarım diliyle tamamlanır. Tasarımdaki sayılar ve yapay zekâ sonuçları gerçek uygulama verisi olarak kullanılmaz.

## 4. Önerilen teknik yapı

- Backend ve sayfalar: Django, Django Templates ve gerektiği kadar JavaScript; ayrı bir SPA zorunluluğu yoktur.
- Grafikler: Python tarafında hazırlanan verilerle Plotly.
- Veri analizi: Pandas, NumPy, scikit-learn ve ihtiyaç halinde statsmodels. LSTM zorunlu seçilirse TensorFlow veya PyTorch değerlendirilir.
- Veritabanı: yerel geliştirme için SQLite; sunucuya yayın hedeflenirse PostgreSQL yapılandırması ve doğrulaması.
- Uygulama bölümleri: hesaplar, portföy, piyasa verileri, analiz, haber/duygu ve notlar.
- Güncelleme ve model eğitimi sayfa isteği içinde çalıştırılmaz; yönetim komutları ve zamanlanabilir işler kullanılır. Ek kuyruk altyapısı ihtiyaç oluşursa eklenir.
- Para ve miktar kayıtlarında ondalık hassasiyet korunur. Parolalar Django'nun parola mekanizmasıyla işlenir; gizli ayarlar ortam değişkenlerinden okunur.
- Paket sürümleri geliştirme başlangıcında uyumluluk ve destek durumları kontrol edilerek sabitlenir.

Arayüz ve proje dokümantasyonu İngilizce, masaüstü öncelikli ve mobil uyumludur. Stitch'teki lacivert navigasyon, açık yüzeyler ve yeşil vurgular temel alınır. Bu Türkçe mutabakat, konuşmanın diliyle korunur.

## 5. Hesaplama kuralları

1. Önerilen maliyet yöntemi ağırlıklı ortalamadır. Satış komisyonu gerçekleşmiş sonuca, alış komisyonu maliyete yansır; vergi muhasebesi kapsam dışıdır.
2. Negatif/sıfır miktar ve elde bulunandan fazla satış reddedilir. Geçmiş işlem değişiklikleri sonraki bakiyeleri de doğrular; tutarsız işlem zinciri kaydedilmez.
3. Güncel değer güncel fiyat/kurla, tarihsel değer ilgili tarihte bilinen fiyat/kurla hesaplanır. Kur yönü ve tarih eşleştirme kuralları belgelenir.
4. Para yatırma/çekme yatırım getirisi sayılmaz. Karşılaştırmada nakit akışlarından arındırılmış zaman ağırlıklı getiri kullanılması önerilir; metrik ve formül kullanıcıya açıklanır.
5. Tatiller, eksik geçmiş, yetersiz gözlem ve farklı işlem takvimleri açık veri kurallarıyla ele alınır. Gelecekteki fiyat geçmiş bir tarihe taşınmaz.
6. Banka bazlı metal alış/satış fiyatları ile genel referans metal fiyatı ayrılır. Referans fiyat kullanılıyorsa banka hesabının kesin tasfiye değeri gibi sunulmaz.
7. Sharpe oranında kullanılan risksiz getiri ve yıllıklaştırma varsayımları; dayanıklılık skorunun bileşenleri, ağırlıkları ve sürümü raporlanır. Yetersiz veri için sahte skor üretilmez.

## 6. Veri erişimi ve AI doğrulama koşulları

Veri sağlayıcılarının güncel erişilebilirliği, ücretleri, tarihsel kapsamı ve kullanım şartları bu aşamada doğrulanmadı. Entegrasyon aşaması, seçilecek kaynaklar üzerinde gerçek bağlantı kontrolüyle başlar. Saniyelik/anlık veri garantisi verilmez; her veri türünün fiilen sağlanan sıklığı, kaynak zamanı ve son başarılı güncellemesi görünür olur.

Canlı veri, önbellekteki son veri ve örnek veri ayrı etiketlenir. Sağlayıcı kesintisi açıkça gösterilir; örnek veriye sessiz geçiş yapılmaz. İnternetsiz sunum için tekrar üretilebilir örnek veri seti sağlanması önerilir. Bu veri seti canlı entegrasyonun tamamlandığına kanıt sayılmaz.

X/Twitter erişimi veya diğer ücretli kaynaklar için gereken hesabı/API anahtarını kullanıcı sağlar; anahtarlar sözleşmeye veya kaynak koduna yazılmaz. Erişim bulunamazsa kullanıcı tarafından sağlanan izinli bir veri kümesiyle analiz yapılması alternatifidir. Böyle bir değişiklik onaylanmadan canlı sosyal analiz teslim edilmiş sayılmaz.

AI modülü yalnızca hazır metin veya rastgele puan üretmez. Eğitim kodu, veri hazırlama, model dosyası, tarihsel eğitim/test ayrımı ve değerlendirme çıktıları teslim edilir. Zaman sıralı test ve mümkünse ileri yürüyen değerlendirme kullanılır; veri sızıntısı önlenir. Basit bir temel modelle hata ve yön başarısı karşılaştırılır. Strateji performansı raporlanırsa işlem maliyetleri ve varsayımları belirtilir.

Belgede LSTM örnek olarak verilmiştir. Öneri, önce tüketici bilgisayarında çalışabilen hafif bir model ve temel karşılaştırma kurmak; LSTM'yi danışman zorunluluğu veya açık kullanıcı tercihi varsa eklemektir. Pozitif getiri ya da temel modeli geçme garantisi kabul kriteri değildir; ölçümün dürüst ve tekrar üretilebilir olması kriterdir.

## 7. Kabul kriterleri

| Kimlik | Doğrulama |
| --- | --- |
| K01 | Temiz kurulum, migration ve örnek veri yükleme README komutlarıyla tamamlanır; uygulama başlar. |
| K02 | Bir kullanıcının portföy, işlem ve notlarına başka kullanıcı URL veya istek değiştirerek erişemez. |
| K03 | Bilinen alış, kısmi satış, komisyon, geçmiş işlem değişikliği ve para hareketi örneklerinde miktar/maliyet/kâr sonuçları beklenen ondalık değerlerle eşleşir. |
| K04 | Aynı veri anındaki TRY/USD/EUR/GBP dönüşümleri doğrulanır; kur eksikliği sıfır veya uydurma sonuç olarak sunulmaz. |
| K05 | Onaylanan canlı kaynaklar için veri çekme ve güncelleme çalışır; tekrarlı çekim çoğaltma yapmaz; kesinti ve eski veri senaryoları doğru görünür. |
| K06 | Dashboard ve kıyaslama aynı veri kurallarını kullanır; tarih/para birimi filtreleri ve nakit akışının getiriye etkisi doğrulanır. |
| K07 | Risk metrikleri bilinen serilerle sınanır; en az iki veri kapsamına uygun tarihsel stres senaryosu çalışır. Sonradan oluşturulmuş bir portföyün geçmişe uygulanması varsayımsal olarak etiketlenir. |
| K08 | Model gerçek eğitim sürecinden geçer; ayrı test dönemi, temel model karşılaştırması, hata metrikleri ve tekrar çalıştırma komutu raporda yer alır. |
| K09 | Haberlerin kaynağı/tarihi; duygu analizinin veri kaynağı, örneklem büyüklüğü ve sınıflandırma değerlendirmesi görünürdür. Canlı erişim veya veri kümesi yolu açık kararla belirlenmiştir. |
| K10 | Not işlemleri çalışır; arayüzdeki temel kontroller gerçek davranışa bağlıdır; boş, yükleniyor ve hata durumları bulunur; masaüstü ve dar ekranda temel akışlar doğrulanır. |
| K11 | Kaynak kod, kurulum rehberi, gereksinim eşleştirmesi, test/backtest raporu ve final proje raporu birlikte teslim edilir; tamamlanmayan noktalar açıkça listelenir. |

## 8. Teslimler ve uygulama sırası

1. **Sözleşme ve gereksinimler:** Bu dosyanın kararlara göre güncellenmesi; DOCX maddelerini işlev ve testlere bağlayan gereksinim belgesi.
2. **Çekirdek:** Django yapılandırması, hesaplar, veri modeli, işlemler, değerleme ve hesaplama testleri.
3. **Veri ve arayüz:** Sağlayıcılar, geçmiş veriler, dashboard, varlıklar ve karşılaştırma ekranları.
4. **Analitik:** Risk, tarihsel stres, tahmin eğitimi, bütçe temelli rehber ve backtest.
5. **Tamamlama:** Haberler, duygu analizi, notlar, uçtan uca kontroller, final raporu ve sunuma hazır örnek senaryo.

Son teslim paketi DOCX'teki yedi kalemi kapsar: veri entegrasyonu/ön işleme, portföy çekirdeği, etkileşimli dashboard, benchmarking, AI analiz motoru, test/doğrulama raporu ve kapsamlı final raporu. Bunlara kaynak kod, bağımlılık dosyası, migration dosyaları, `.env.example`, veri/model komutları ve kurulum README'si eşlik eder.

IEEE 830-1998 belge düzeni DOCX'in talebi olarak esas alınır; güvenlik önlemleri ISO/IEC 27001 başlığı altında izlenebilir şekilde açıklanır. Sertifikasyon veya bağımsız uygunluk denetimi teslimi vaat edilmez. Python kodunda PEP 8 esas alınır.

## 9. Kesinleşen kararlar

| Konu | Öneri | Durum |
| --- | --- | --- |
| Teslim tarihi | Sabit bir teslim tarihi yok. | Kullanıcı kararı |
| Dil ve hesap yapısı | İngilizce arayüz ve dokümantasyon; kullanıcıya özel hesaplar ve portföyler. | Dil kullanıcı kararı; hesap yapısı önerildiği gibi |
| Çalışma ortamı | Windows üzerinde yerel çalışma yeterli; yayın kapsam dışı. | Kullanıcı kararı |
| Veri bütçesi ve sosyal veri | Anahtarlar şu an yok; sağlayıcılar sonradan yapılandırılabilir olacak. İlk teslim açıkça işaretli örnek verilerle çalışacak; canlı bağlantıların gerçek kimlik bilgileriyle doğrulanması sonraki aşama. | Kullanıcı kararı |
| Metal değerleme | Genel referans gram fiyatları. | Kullanıcı kararı |
| AI modeli | Gerçek eğitim ve değerlendirmeye sahip hafif, değiştirilebilir bir model. | Kullanıcı kararı |

Geliştirmeye başlanabilir. K05 ve K09 için ilk teslimde örnek veri, veri içe aktarma ve yapılandırılabilir sağlayıcı davranışı doğrulanacak; canlı API erişimi anahtarlar eklendiğinde ayrıca test edilecektir. Örnek veride model eğitimi yazılım akışını doğrular, gerçek piyasa başarısını kanıtlamaz. Yeni kapsam istekleri etkilenen modül, test ve teslimlerle birlikte bu belgeye işlenir. Harici erişim engelleri tamamlanmış özellik gibi kapatılmaz.
