# Tuna Fırın Otomasyonu (Flask + MySQL)

Müşteri sipariş, admin yönetim, kurye teslimat ve mesajlaşma akışını içeren fırın otomasyon sistemi.

## Roller ve Akış

### MÜŞTERİ
- Ürünleri görüntüler, sepete ekler, sipariş oluşturur
- Yorum yapar, mesaj gönderir
- Sipariş durumu: `OLUSTURULDU` → `ONAYLANDI` → `HAZIRLANIYOR` → `KURYE_ATANDI` → `YOLDA` → `TESLIM_EDILDI`

### ADMIN
- Siparişleri onayla/iptal et, kurye ata
- Ürün, müşteri, kurye, kupon yönetimi
- Mesaj okuma ve yanıtlama
- Site ayarları

### KURYE
- Atanan siparişleri görüntüle
- **Teslim Al** → `YOLDA`
- **Teslim Et** → `TESLIM_EDILDI`
- Müşteriye mesaj gönder

## Kurulum

1. Bağımlılıklar:
   ```bash
   pip install -r requirements.txt
   ```

2. Veritabanını kur:
   ```bash
   mysql -u root -p < firin_db.sql
   ```

3. Uygulamayı başlat:
   ```bash
   python app.py
   ```
   veya
   ```bash
   start_firin.bat
   ```

4. Tarayıcı: `http://127.0.0.1:5000`

## Giriş Bilgileri

- **Admin:** `admin` / `firin`
- **Kurye:** Yeni ekle (Admin Panel → Kuryeler)
- **Müşteri:** Kayıt ol veya test: `musteri1` / `123`

## Özellikler

- ✅ Sipariş yönetimi (durum takibi, log)
- ✅ Stok kontrolü ve hareketleri
- ✅ Kurye atama ve teslimat takibi
- ✅ Mesajlaşma sistemi (Müşteri ↔ Admin ↔ Kurye)
- ✅ Ürün yorumlama (otomatik onay)
- ✅ Kupon/indirim sistemi
- ✅ Favoriler ve sepet

## Veritabanı Tabloları

| Tablo | Açıklama |
|-------|----------|
| `musteri` | Müşteri bilgileri |
| `kurye` | Kurye bilgileri |
| `admin` | Admin hesapları |
| `urun` / `kategori` / `stok` | Ürün yönetimi |
| `siparis` / `siparis_detay` | Siparişler |
| `siparis_durum_log` | Durum değişiklik geçmişi |
| `mesajlar` | Yeni mesajlaşma sistemi |
| `yorum` | Ürün yorumları |
| `kupon` | İndirim kuponları |
| `favoriler` / `sepet` | Kullanıcı tercihleri |

## Not

Bu proje eğitim/demonstrasyon amaçlıdır.
