-- Tuna Fırın Otomasyonu
-- Tek Dosya: Şema + Seed Veri
-- MySQL 8+ önerilir (utf8mb4)

SET NAMES utf8mb4;

DROP DATABASE IF EXISTS firin_db;
CREATE DATABASE firin_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE firin_db;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS stok_hareketi;
DROP TABLE IF EXISTS yorum;
DROP TABLE IF EXISTS favoriler;
DROP TABLE IF EXISTS sepet;
DROP TABLE IF EXISTS siparis_durum_log;
DROP TABLE IF EXISTS siparis_detay;
DROP TABLE IF EXISTS siparis;
DROP TABLE IF EXISTS stok;
DROP TABLE IF EXISTS urun;
DROP TABLE IF EXISTS kategori;
DROP TABLE IF EXISTS adres;
DROP TABLE IF EXISTS kullanici;

SET FOREIGN_KEY_CHECKS = 1;

-- 1) KULLANICI
CREATE TABLE kullanici (
    id INT PRIMARY KEY AUTO_INCREMENT,
    k_adi VARCHAR(50) UNIQUE NOT NULL,
    sifre VARCHAR(255) NOT NULL,
    ad VARCHAR(100),
    soyad VARCHAR(100),
    telefon VARCHAR(20),
    email VARCHAR(100),
    rol VARCHAR(20) DEFAULT 'MUSTERI',
    aktif BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) ADRES
CREATE TABLE adres (
    id INT PRIMARY KEY AUTO_INCREMENT,
    musteri_id INT NOT NULL,
    adres_basligi VARCHAR(50),
    acik_adres TEXT,
    varsayilan BOOLEAN DEFAULT FALSE,
    CONSTRAINT fk_adres_musteri FOREIGN KEY (musteri_id) REFERENCES kullanici(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3) KATEGORI
CREATE TABLE kategori (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ad VARCHAR(100) NOT NULL,
    aktif BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4) URUN
CREATE TABLE urun (
    id INT PRIMARY KEY AUTO_INCREMENT,
    kategori_id INT NOT NULL,
    ad VARCHAR(150) NOT NULL,
    aciklama TEXT,
    fiyat DECIMAL(10, 2) NOT NULL,
    resim VARCHAR(255),
    aktif BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_urun_kategori FOREIGN KEY (kategori_id) REFERENCES kategori(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5) STOK
CREATE TABLE stok (
    urun_id INT PRIMARY KEY,
    miktar INT DEFAULT 0,
    kritik_seviye INT DEFAULT 10,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_stok_urun FOREIGN KEY (urun_id) REFERENCES urun(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6) SIPARIS
CREATE TABLE siparis (
    id INT PRIMARY KEY AUTO_INCREMENT,
    musteri_id INT NOT NULL,
    kurye_id INT NULL,
    adres_id INT NOT NULL,
    durum VARCHAR(20) DEFAULT 'ONAY_BEKLIYOR',
    odeme_tipi VARCHAR(20),
    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    toplam_tutar DECIMAL(10, 2) NOT NULL DEFAULT 0,
    CONSTRAINT fk_siparis_musteri FOREIGN KEY (musteri_id) REFERENCES kullanici(id),
    CONSTRAINT fk_siparis_kurye FOREIGN KEY (kurye_id) REFERENCES kullanici(id),
    CONSTRAINT fk_siparis_adres FOREIGN KEY (adres_id) REFERENCES adres(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_siparis_musteri ON siparis(musteri_id);
CREATE INDEX ix_siparis_kurye ON siparis(kurye_id);
CREATE INDEX ix_siparis_durum ON siparis(durum);

-- 7) SIPARIS_DETAY
CREATE TABLE siparis_detay (
    id INT PRIMARY KEY AUTO_INCREMENT,
    siparis_id INT NOT NULL,
    urun_id INT NOT NULL,
    adet INT NOT NULL,
    birim_fiyat DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_detay_siparis FOREIGN KEY (siparis_id) REFERENCES siparis(id) ON DELETE CASCADE,
    CONSTRAINT fk_detay_urun FOREIGN KEY (urun_id) REFERENCES urun(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8) SIPARIS_DURUM_LOG
CREATE TABLE siparis_durum_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    siparis_id INT NOT NULL,
    eski_durum VARCHAR(20),
    yeni_durum VARCHAR(20),
    degistiren_id INT NOT NULL,
    aciklama VARCHAR(255),
    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_siparis FOREIGN KEY (siparis_id) REFERENCES siparis(id) ON DELETE CASCADE,
    CONSTRAINT fk_log_degistiren FOREIGN KEY (degistiren_id) REFERENCES kullanici(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_log_degistiren ON siparis_durum_log(degistiren_id);
CREATE INDEX ix_log_siparis ON siparis_durum_log(siparis_id);

-- 9) SEPET
CREATE TABLE sepet (
    id INT PRIMARY KEY AUTO_INCREMENT,
    musteri_id INT NOT NULL,
    urun_id INT NOT NULL,
    adet INT DEFAULT 1,
    CONSTRAINT fk_sepet_musteri FOREIGN KEY (musteri_id) REFERENCES kullanici(id) ON DELETE CASCADE,
    CONSTRAINT fk_sepet_urun FOREIGN KEY (urun_id) REFERENCES urun(id) ON DELETE CASCADE,
    UNIQUE KEY uk_sepet_musteri_urun (musteri_id, urun_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10) FAVORILER
CREATE TABLE favoriler (
    id INT PRIMARY KEY AUTO_INCREMENT,
    musteri_id INT NOT NULL,
    urun_id INT NOT NULL,
    CONSTRAINT fk_fav_musteri FOREIGN KEY (musteri_id) REFERENCES kullanici(id) ON DELETE CASCADE,
    CONSTRAINT fk_fav_urun FOREIGN KEY (urun_id) REFERENCES urun(id) ON DELETE CASCADE,
    UNIQUE KEY uk_fav_musteri_urun (musteri_id, urun_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11) YORUM
CREATE TABLE yorum (
    id INT PRIMARY KEY AUTO_INCREMENT,
    urun_id INT NOT NULL,
    musteri_id INT NOT NULL,
    siparis_id INT NOT NULL,
    puan INT DEFAULT 5,
    metin TEXT,
    onay_durumu BOOLEAN DEFAULT TRUE,
    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_yorum_urun FOREIGN KEY (urun_id) REFERENCES urun(id),
    CONSTRAINT fk_yorum_musteri FOREIGN KEY (musteri_id) REFERENCES kullanici(id),
    CONSTRAINT fk_yorum_siparis FOREIGN KEY (siparis_id) REFERENCES siparis(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 12) KUPON
CREATE TABLE kupon (
    id INT PRIMARY KEY AUTO_INCREMENT,
    kod VARCHAR(20) UNIQUE NOT NULL,
    indirim_yuzdesi INT NOT NULL,
    aciklama VARCHAR(100),
    aktif BOOLEAN DEFAULT TRUE,
    son_kullanim_tarihi DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 12) STOK_HAREKETI
CREATE TABLE stok_hareketi (
    id INT PRIMARY KEY AUTO_INCREMENT,
    urun_id INT NOT NULL,
    siparis_id INT NULL,
    hareket_tipi VARCHAR(20) NOT NULL,
    miktar INT NOT NULL,
    aciklama TEXT,
    yapan_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sh_urun FOREIGN KEY (urun_id) REFERENCES urun(id),
    CONSTRAINT fk_sh_siparis FOREIGN KEY (siparis_id) REFERENCES siparis(id) ON DELETE SET NULL,
    CONSTRAINT fk_sh_yapan FOREIGN KEY (yapan_id) REFERENCES kullanici(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_sh_urun ON stok_hareketi(urun_id);
CREATE INDEX ix_sh_yapan ON stok_hareketi(yapan_id);
CREATE INDEX ix_sh_siparis ON stok_hareketi(siparis_id);

-- =========================
-- SEED VERİ
-- =========================

-- Kullanıcılar (1 Admin, 2 Kurye, 30 Müşteri)
INSERT INTO kullanici (id, k_adi, sifre, ad, soyad, telefon, email, rol, aktif) VALUES
    (1, 'admin', 'firin', 'Super', 'Admin', '5550000000', 'admin@firin.com', 'ADMIN', 1),
    (2, 'kurye1', '123', 'Hasan', 'Yılmaz', '5551110001', 'kurye1@firin.com', 'KURYE', 1),
    (3, 'kurye2', '123', 'Mehmet', 'Demir', '5551110002', 'kurye2@firin.com', 'KURYE', 1),
    (4, 'kurye3', '123', 'Ali', 'Kaya', '5551110003', 'kurye3@firin.com', 'KURYE', 1),
    (5, 'kurye4', '123', 'Burak', 'Çelik', '5551110004', 'kurye4@firin.com', 'KURYE', 1);

INSERT INTO kullanici (id, k_adi, sifre, ad, soyad, telefon, email, rol, aktif) VALUES
    (10, 'musteri1', '123', 'Ahmet', 'Yılmaz', '5552000001', 'musteri1@firin.com', 'MUSTERI', 1),
    (11, 'musteri2', '123', 'Ayşe', 'Demir', '5552000002', 'musteri2@firin.com', 'MUSTERI', 1),
    (12, 'musteri3', '123', 'Mehmet', 'Kaya', '5552000003', 'musteri3@firin.com', 'MUSTERI', 1),
    (13, 'musteri4', '123', 'Fatma', 'Çelik', '5552000004', 'musteri4@firin.com', 'MUSTERI', 1),
    (14, 'musteri5', '123', 'Zeynep', 'Şahin', '5552000005', 'musteri5@firin.com', 'MUSTERI', 1),
    (15, 'musteri6', '123', 'Burak', 'Yıldız', '5552000006', 'musteri6@firin.com', 'MUSTERI', 1),
    (16, 'musteri7', '123', 'Elif', 'Aydın', '5552000007', 'musteri7@firin.com', 'MUSTERI', 1),
    (17, 'musteri8', '123', 'Can', 'Arslan', '5552000008', 'musteri8@firin.com', 'MUSTERI', 1),
    (18, 'musteri9', '123', 'Deniz', 'Öztürk', '5552000009', 'musteri9@firin.com', 'MUSTERI', 1),
    (19, 'musteri10', '123', 'Merve', 'Kurt', '5552000010', 'musteri10@firin.com', 'MUSTERI', 1),
    (20, 'musteri11', '123', 'Kerem', 'Kılıç', '5552000011', 'musteri11@firin.com', 'MUSTERI', 1),
    (21, 'musteri12', '123', 'Selin', 'Aslan', '5552000012', 'musteri12@firin.com', 'MUSTERI', 1),
    (22, 'musteri13', '123', 'Hakan', 'Doğan', '5552000013', 'musteri13@firin.com', 'MUSTERI', 1),
    (23, 'musteri14', '123', 'Pelin', 'Yıldırım', '5552000014', 'musteri14@firin.com', 'MUSTERI', 1),
    (24, 'musteri15', '123', 'Ege', 'Kara', '5552000015', 'musteri15@firin.com', 'MUSTERI', 1),
    (25, 'musteri16', '123', 'Büşra', 'Koç', '5552000016', 'musteri16@firin.com', 'MUSTERI', 1),
    (26, 'musteri17', '123', 'Arda', 'Şimşek', '5552000017', 'musteri17@firin.com', 'MUSTERI', 1),
    (27, 'musteri18', '123', 'Seda', 'Aksoy', '5552000018', 'musteri18@firin.com', 'MUSTERI', 1),
    (28, 'musteri19', '123', 'Oğuz', 'Çetin', '5552000019', 'musteri19@firin.com', 'MUSTERI', 1),
    (29, 'musteri20', '123', 'Ebru', 'Güneş', '5552000020', 'musteri20@firin.com', 'MUSTERI', 1),
    (30, 'musteri21', '123', 'Cem', 'Karaca', '5552000021', 'musteri21@firin.com', 'MUSTERI', 1),
    (31, 'musteri22', '123', 'Sevgi', 'Er', '5552000022', 'musteri22@firin.com', 'MUSTERI', 1),
    (32, 'musteri23', '123', 'Yusuf', 'Korkmaz', '5552000023', 'musteri23@firin.com', 'MUSTERI', 1),
    (33, 'musteri24', '123', 'Derya', 'Polat', '5552000024', 'musteri24@firin.com', 'MUSTERI', 1),
    (34, 'musteri25', '123', 'Emre', 'Güler', '5552000025', 'musteri25@firin.com', 'MUSTERI', 1),
    (35, 'musteri26', '123', 'İrem', 'Yalçın', '5552000026', 'musteri26@firin.com', 'MUSTERI', 1),
    (36, 'musteri27', '123', 'Kaan', 'Taş', '5552000027', 'musteri27@firin.com', 'MUSTERI', 1),
    (37, 'musteri28', '123', 'Sinem', 'Çınar', '5552000028', 'musteri28@firin.com', 'MUSTERI', 1),
    (38, 'musteri29', '123', 'Onur', 'Keskin', '5552000029', 'musteri29@firin.com', 'MUSTERI', 1),
    (39, 'musteri30', '123', 'Gamze', 'Korkut', '5552000030', 'musteri30@firin.com', 'MUSTERI', 1);

-- Adresler (her müşteri için 1 varsayılan adres; bazılarına ekstra)
INSERT INTO adres (musteri_id, adres_basligi, acik_adres, varsayilan) VALUES
    (10, 'Ev', 'İstanbul, Kadıköy, Moda Mah. Lale Sok. No:5', 1),
    (11, 'Ev', 'İstanbul, Kadıköy, Caferağa Mah. Bahar Sk. No:12', 1),
    (12, 'Ev', 'İstanbul, Kadıköy, Fenerbahçe Mah. Deniz Sk. No:8', 1),
    (13, 'Ev', 'İstanbul, Kadıköy, Suadiye Mah. Park Sk. No:22', 1),
    (14, 'Ev', 'İstanbul, Kadıköy, Caddebostan Mah. Çiçek Sk. No:7', 1),
    (15, 'Ev', 'İstanbul, Kadıköy, Feneryolu Mah. Uğur Sk. No:19', 1),
    (16, 'Ev', 'İstanbul, Kadıköy, Göztepe Mah. Çam Sk. No:3', 1),
    (17, 'Ev', 'İstanbul, Kadıköy, Erenköy Mah. Narin Sk. No:11', 1),
    (18, 'Ev', 'İstanbul, Kadıköy, Bostancı Mah. Zeytin Sk. No:4', 1),
    (19, 'Ev', 'İstanbul, Kadıköy, Kozyatağı Mah. Gül Sk. No:15', 1),
    (20, 'Ev', 'İstanbul, Kadıköy, Acıbadem Mah. Koru Sk. No:9', 1),
    (21, 'Ev', 'İstanbul, Kadıköy, Hasanpaşa Mah. Karanfil Sk. No:6', 1),
    (22, 'Ev', 'İstanbul, Kadıköy, Rasimpaşa Mah. Rıhtım Sk. No:2', 1),
    (23, 'Ev', 'İstanbul, Kadıköy, Osmanağa Mah. Dere Sk. No:18', 1),
    (24, 'Ev', 'İstanbul, Kadıköy, Sahrayıcedit Mah. Ekin Sk. No:1', 1),
    (25, 'Ev', 'İstanbul, Kadıköy, Koşuyolu Mah. Çınar Sk. No:10', 1),
    (26, 'Ev', 'İstanbul, Kadıköy, Fikirtepe Mah. Sedef Sk. No:14', 1),
    (27, 'Ev', 'İstanbul, Kadıköy, Eğitim Mah. Seda Sk. No:16', 1),
    (28, 'Ev', 'İstanbul, Kadıköy, Dumlupınar Mah. Pınar Sk. No:21', 1),
    (29, 'Ev', 'İstanbul, Kadıköy, Merdivenköy Mah. Kızıl Sk. No:13', 1),
    (30, 'Ev', 'İstanbul, Kadıköy, Koşuyolu Mah. Işık Sk. No:27', 1),
    (31, 'Ev', 'İstanbul, Kadıköy, Bostancı Mah. Yelken Sk. No:30', 1),
    (32, 'Ev', 'İstanbul, Kadıköy, Suadiye Mah. Papatya Sk. No:20', 1),
    (33, 'Ev', 'İstanbul, Kadıköy, Göztepe Mah. Kule Sk. No:17', 1),
    (34, 'Ev', 'İstanbul, Kadıköy, Caddebostan Mah. Deniz Sk. No:6', 1),
    (35, 'Ev', 'İstanbul, Kadıköy, Moda Mah. Menekşe Sk. No:9', 1),
    (36, 'Ev', 'İstanbul, Kadıköy, Erenköy Mah. Orkide Sk. No:5', 1),
    (37, 'Ev', 'İstanbul, Kadıköy, Caferağa Mah. Güneş Sk. No:25', 1),
    (38, 'Ev', 'İstanbul, Kadıköy, Fenerbahçe Mah. Sahil Sk. No:2', 1),
    (39, 'Ev', 'İstanbul, Kadıköy, Kozyatağı Mah. Ağaç Sk. No:8', 1);

INSERT INTO adres (musteri_id, adres_basligi, acik_adres, varsayilan) VALUES
    (10, 'İş', 'İstanbul, Ataşehir, Küçükbakkalköy Mah. Plaza Sk. No:1', 0),
    (15, 'İş', 'İstanbul, Maltepe, Altayçeşme Mah. Şirket Sk. No:7', 0),
    (22, 'İş', 'İstanbul, Üsküdar, Acıbadem Mah. Ofis Sk. No:3', 0);

-- Kategoriler
INSERT INTO kategori (id, ad, aktif) VALUES
    (1, 'Ekmekler', 1),
    (2, 'Simit & Poğaça', 1),
    (3, 'Börekler', 1),
    (4, 'Pastalar', 1),
    (5, 'Tatlılar', 1),
    (6, 'Kurabiyeler', 1),
    (7, 'Sandviçler', 1),
    (8, 'İçecekler', 1);

-- Ürünler (24 ürün)
INSERT INTO urun (id, kategori_id, ad, aciklama, fiyat, resim, aktif) VALUES
    (1, 1, 'Somun Ekmek', 'Günlük taze somun ekmek.', 10.00, 'https://placehold.co/600x400?text=Somun+Ekmek', 1),
    (2, 1, 'Tam Buğday', 'Sağlıklı tam buğday ekmeği.', 15.00, 'https://placehold.co/600x400?text=Tam+Bugday', 1),
    (3, 1, 'Çavdar Ekmeği', 'Lezzetli çavdar ekmeği.', 18.00, 'https://placehold.co/600x400?text=Cavdar+Ekmek', 1),
    (4, 2, 'Susamlı Simit', 'Sıcacık susamlı simit.', 15.00, 'https://placehold.co/600x400?text=Susamli+Simit', 1),
    (5, 2, 'Peynirli Poğaça', 'Taze peynirli poğaça.', 16.00, 'https://placehold.co/600x400?text=Peynirli+Pogaca', 1),
    (6, 2, 'Zeytinli Açma', 'Tereyağlı zeytinli açma.', 18.00, 'https://placehold.co/600x400?text=Zeytinli+Acma', 1),
    (7, 3, 'Su Böreği', 'El açması su böreği (porsiyon).', 60.00, 'https://placehold.co/600x400?text=Su+Boregi', 1),
    (8, 3, 'Ispanaklı Börek', 'Bol ıspanaklı börek.', 50.00, 'https://placehold.co/600x400?text=Ispanakli+Borek', 1),
    (9, 3, 'Kıymalı Börek', 'Kıymalı kol böreği (porsiyon).', 55.00, 'https://placehold.co/600x400?text=Kiymali+Borek', 1),
    (10, 4, 'Çikolatalı Pasta (Dilim)', 'Belçika çikolatalı yaş pasta.', 85.00, 'https://placehold.co/600x400?text=Cikolatali+Pasta', 1),
    (11, 4, 'Çilekli Pasta (Dilim)', 'Taze çilekli yaş pasta.', 85.00, 'https://placehold.co/600x400?text=Cilekli+Pasta', 1),
    (12, 4, 'Cheesecake', 'Limonlu cheesecake dilimi.', 90.00, 'https://placehold.co/600x400?text=Cheesecake', 1),
    (13, 5, 'Fırın Sütlaç', 'Fırında nar gibi kızarmış sütlaç.', 75.00, 'https://placehold.co/600x400?text=Firin+Sutlac', 1),
    (14, 5, 'Kazandibi', 'Kıvamında kazandibi.', 75.00, 'https://placehold.co/600x400?text=Kazandibi', 1),
    (15, 5, 'Trileçe', 'Hafif ve yumuşak trileçe.', 65.00, 'https://placehold.co/600x400?text=Trilece', 1),
    (16, 6, 'Un Kurabiyesi (250g)', 'Ağızda dağılan un kurabiyesi.', 60.00, 'https://placehold.co/600x400?text=Un+Kurabiyesi', 1),
    (17, 6, 'Tuzlu Kurabiye (250g)', 'Çay saatine tuzlu kurabiye.', 60.00, 'https://placehold.co/600x400?text=Tuzlu+Kurabiye', 1),
    (18, 6, 'Brownie Cookie', 'Yoğun çikolatalı cookie.', 25.00, 'https://placehold.co/600x400?text=Brownie+Cookie', 1),
    (19, 7, 'Kaşarlı Tost', 'Bol kaşarlı tost.', 50.00, 'https://placehold.co/600x400?text=Kasarli+Tost', 1),
    (20, 7, 'Karışık Tost', 'Sucuk, salam, kaşar karışık.', 65.00, 'https://placehold.co/600x400?text=Karisik+Tost', 1),
    (21, 7, 'Soğuk Sandviç', 'Peynirli soğuk sandviç.', 55.00, 'https://placehold.co/600x400?text=Soguk+Sandvic', 1),
    (22, 8, 'Demleme Çay', 'Demleme çay (bardak).', 15.00, 'https://placehold.co/600x400?text=Demleme+Cay', 1),
    (23, 8, 'Türk Kahvesi', 'Közde türk kahvesi.', 40.00, 'https://placehold.co/600x400?text=Turk+Kahvesi', 1),
    (24, 8, 'Limonata', 'Ev yapımı limonata.', 40.00, 'https://placehold.co/600x400?text=Limonata', 1);

-- Stoklar
INSERT INTO stok (urun_id, miktar, kritik_seviye) VALUES
    (1, 200, 10), (2, 180, 10), (3, 160, 10), (4, 220, 10), (5, 210, 10), (6, 190, 10),
    (7, 120, 10), (8, 140, 10), (9, 130, 10), (10, 110, 10), (11, 110, 10), (12, 100, 10),
    (13, 150, 10), (14, 140, 10), (15, 160, 10), (16, 130, 10), (17, 130, 10), (18, 200, 10),
    (19, 180, 10), (20, 170, 10), (21, 160, 10), (22, 300, 10), (23, 260, 10), (24, 240, 10);

-- Stok hareketi: açılış
INSERT INTO stok_hareketi (urun_id, siparis_id, hareket_tipi, miktar, aciklama, yapan_id, created_at)
SELECT urun_id, NULL, 'GIRIS', miktar, 'Açılış Stoku', 1, NOW() FROM stok;

-- Siparişler: Her müşteri için 2 sipariş (durumlar karışık)
INSERT INTO siparis (id, musteri_id, kurye_id, adres_id, durum, odeme_tipi, tarih, toplam_tutar)
SELECT
    1000 + k.id AS id,
    k.id AS musteri_id,
    CASE
        WHEN ((k.id - 10) % 4) = 3 THEN ((k.id % 4) + 2)  -- KURYE_ATANDI ise kurye 2-5 arası
        ELSE NULL
    END AS kurye_id,
    (SELECT a.id FROM adres a WHERE a.musteri_id = k.id AND a.varsayilan = 1 ORDER BY a.id LIMIT 1) AS adres_id,
    CASE ((k.id - 10) % 4)
        WHEN 0 THEN 'OLUSTURULDU'
        WHEN 1 THEN 'ONAYLANDI'
        WHEN 2 THEN 'HAZIRLANIYOR'
        ELSE 'KURYE_ATANDI'
    END AS durum,
    'KAPIDA_NAKIT' AS odeme_tipi,
    DATE_SUB(NOW(), INTERVAL (k.id - 9) DAY) AS tarih,
    0 AS toplam_tutar
FROM kullanici k
WHERE k.rol = 'MUSTERI';

INSERT INTO siparis (id, musteri_id, kurye_id, adres_id, durum, odeme_tipi, tarih, toplam_tutar)
SELECT
    2000 + k.id AS id,
    k.id AS musteri_id,
    CASE
        WHEN ((k.id - 10) % 6) IN (2, 3, 4, 5) THEN ((k.id % 4) + 2)  -- Kuryeler 2-5 döngü
        ELSE NULL
    END AS kurye_id,
    (SELECT a.id FROM adres a WHERE a.musteri_id = k.id AND a.varsayilan = 1 ORDER BY a.id LIMIT 1) AS adres_id,
    CASE
        WHEN ((k.id - 10) % 6) = 0 THEN 'IPTAL_EDILDI'
        WHEN ((k.id - 10) % 6) = 1 THEN 'REDDEDILDI'
        WHEN ((k.id - 10) % 6) = 2 THEN 'KURYE_ATANDI'
        WHEN ((k.id - 10) % 6) = 3 THEN 'YOLDA'
        WHEN ((k.id - 10) % 6) = 4 THEN 'TESLIM_EDILDI'
        ELSE 'ONAYLANDI'
    END AS durum,
    'KAPIDA_NAKIT' AS odeme_tipi,
    DATE_SUB(NOW(), INTERVAL (k.id + 20) DAY) AS tarih,
    0 AS toplam_tutar
FROM kullanici k
WHERE k.rol = 'MUSTERI';

-- Durum normalizasyonu (kurye atanmışsa status KURYE_ATANDI, YOLDA eski eşleştirmeler için)
UPDATE siparis SET durum='OLUSTURULDU' WHERE durum='ONAY_BEKLIYOR';
UPDATE siparis SET durum='YOLDA' WHERE durum='KURYEDE';

-- Sipariş detayları (1. set: 3 kalem)
INSERT INTO siparis_detay (siparis_id, urun_id, adet, birim_fiyat)
SELECT
    s.id AS siparis_id,
    u.id AS urun_id,
    (1 + ((s.id + t.off) % 3)) AS adet,
    u.fiyat AS birim_fiyat
FROM siparis s
JOIN (SELECT 0 AS off UNION ALL SELECT 1 UNION ALL SELECT 2) t
JOIN urun u ON u.id = (((s.musteri_id - 10 + t.off) % 24) + 1)
WHERE s.id BETWEEN 1010 AND 1039;

-- Sipariş detayları (2. set: 4 kalem)
INSERT INTO siparis_detay (siparis_id, urun_id, adet, birim_fiyat)
SELECT
    s.id AS siparis_id,
    u.id AS urun_id,
    (1 + ((s.id + t.off) % 2)) AS adet,
    u.fiyat AS birim_fiyat
FROM siparis s
JOIN (SELECT 3 AS off UNION ALL SELECT 7 UNION ALL SELECT 11 UNION ALL SELECT 17) t
JOIN urun u ON u.id = (((s.musteri_id - 10 + t.off) % 24) + 1)
WHERE s.id BETWEEN 2010 AND 2039;

-- Sipariş toplamlarını hesapla
UPDATE siparis s
SET s.toplam_tutar = (
    SELECT IFNULL(SUM(d.adet * d.birim_fiyat), 0)
    FROM siparis_detay d
    WHERE d.siparis_id = s.id
);

-- Sipariş durum logları (geçmiş)
INSERT INTO siparis_durum_log (siparis_id, eski_durum, yeni_durum, degistiren_id, aciklama, tarih)
SELECT s.id, '-', 'ONAY_BEKLIYOR', s.musteri_id, 'Sipariş oluşturuldu', s.tarih
FROM siparis s;

INSERT INTO siparis_durum_log (siparis_id, eski_durum, yeni_durum, degistiren_id, aciklama, tarih)
SELECT s.id, 'ONAY_BEKLIYOR', 'HAZIRLANIYOR', 1, 'Admin onayladı', DATE_ADD(s.tarih, INTERVAL 30 MINUTE)
FROM siparis s
WHERE s.durum IN ('HAZIRLANIYOR', 'KURYEDE', 'TESLIM_EDILDI', 'ONAYLANDI');

INSERT INTO siparis_durum_log (siparis_id, eski_durum, yeni_durum, degistiren_id, aciklama, tarih)
SELECT s.id, 'HAZIRLANIYOR', 'KURYEDE', s.kurye_id, 'Kurye teslim aldı', DATE_ADD(s.tarih, INTERVAL 60 MINUTE)
FROM siparis s
WHERE s.durum IN ('KURYEDE', 'TESLIM_EDILDI', 'ONAYLANDI') AND s.kurye_id IS NOT NULL;

INSERT INTO siparis_durum_log (siparis_id, eski_durum, yeni_durum, degistiren_id, aciklama, tarih)
SELECT s.id, 'KURYEDE', 'TESLIM_EDILDI', s.kurye_id, 'Kurye teslim etti', DATE_ADD(s.tarih, INTERVAL 120 MINUTE)
FROM siparis s
WHERE s.durum IN ('TESLIM_EDILDI', 'ONAYLANDI') AND s.kurye_id IS NOT NULL;

INSERT INTO siparis_durum_log (siparis_id, eski_durum, yeni_durum, degistiren_id, aciklama, tarih)
SELECT s.id, 'TESLIM_EDILDI', 'ONAYLANDI', 1, 'Admin kapattı', DATE_ADD(s.tarih, INTERVAL 180 MINUTE)
FROM siparis s
WHERE s.durum = 'ONAYLANDI';

INSERT INTO siparis_durum_log (siparis_id, eski_durum, yeni_durum, degistiren_id, aciklama, tarih)
SELECT s.id, 'ONAY_BEKLIYOR', 'IPTAL_EDILDI', 1, 'Admin iptal etti', DATE_ADD(s.tarih, INTERVAL 20 MINUTE)
FROM siparis s
WHERE s.durum = 'IPTAL_EDILDI';

-- Stok hareketi: satış (sipariş oluşturma)
INSERT INTO stok_hareketi (urun_id, siparis_id, hareket_tipi, miktar, aciklama, yapan_id, created_at)
SELECT
    d.urun_id,
    d.siparis_id,
    'SATIS',
    -d.adet,
    CONCAT('Sipariş #', d.siparis_id, ' satışı'),
    s.musteri_id,
    s.tarih
FROM siparis_detay d
JOIN siparis s ON s.id = d.siparis_id;

-- Stok hareketi: iptal iadesi
INSERT INTO stok_hareketi (urun_id, siparis_id, hareket_tipi, miktar, aciklama, yapan_id, created_at)
SELECT
    d.urun_id,
    d.siparis_id,
    'IADE',
    d.adet,
    CONCAT('Sipariş #', d.siparis_id, ' iptal iadesi'),
    1,
    DATE_ADD(s.tarih, INTERVAL 25 MINUTE)
FROM siparis_detay d
JOIN siparis s ON s.id = d.siparis_id
WHERE s.durum = 'IPTAL_EDILDI';

-- Stok güncelle: tüm siparişlerde düş, iptallerde geri ekle
UPDATE stok st
JOIN (
    SELECT urun_id, SUM(adet) AS qty
    FROM siparis_detay
    GROUP BY urun_id
) t ON t.urun_id = st.urun_id
SET st.miktar = st.miktar - t.qty;

UPDATE stok st
JOIN (
    SELECT d.urun_id, SUM(d.adet) AS qty
    FROM siparis_detay d
    JOIN siparis s ON s.id = d.siparis_id
    WHERE s.durum = 'IPTAL_EDILDI'
    GROUP BY d.urun_id
) t ON t.urun_id = st.urun_id
SET st.miktar = st.miktar + t.qty;

-- Favoriler: her müşteri 3 ürün favoriler
INSERT INTO favoriler (musteri_id, urun_id)
SELECT k.id, ((k.id - 10 + 0) % 24) + 1 FROM kullanici k WHERE k.rol = 'MUSTERI';
INSERT INTO favoriler (musteri_id, urun_id)
SELECT k.id, ((k.id - 10 + 1) % 24) + 1 FROM kullanici k WHERE k.rol = 'MUSTERI';
INSERT INTO favoriler (musteri_id, urun_id)
SELECT k.id, ((k.id - 10 + 2) % 24) + 1 FROM kullanici k WHERE k.rol = 'MUSTERI';

-- Yorumlar: sadece teslim edilen/kapatan siparişler (1 yorum/sipariş)
INSERT INTO yorum (urun_id, musteri_id, siparis_id, puan, metin, onay_durumu, tarih)
SELECT
    MIN(d.urun_id) AS urun_id,
    s.musteri_id,
    s.id AS siparis_id,
    CASE WHEN (s.id % 5) = 0 THEN 4 ELSE 5 END AS puan,
    CONCAT('Sipariş #', s.id, ' - Tadı harika, tekrar alırım.') AS metin,
    CASE WHEN (s.id % 4) = 0 THEN 0 ELSE 1 END AS onay_durumu,
    DATE_ADD(s.tarih, INTERVAL 1 DAY) AS tarih
FROM siparis s
JOIN siparis_detay d ON d.siparis_id = s.id
WHERE s.durum IN ('TESLIM_EDILDI', 'ONAYLANDI')
GROUP BY s.id
LIMIT 50;

-- Örnek sepet: ilk 5 müşteri için 2 ürün
INSERT INTO sepet (musteri_id, urun_id, adet) VALUES
    (10, 4, 2), (10, 13, 1),
    (11, 1, 1), (11, 22, 3),
    (12, 7, 1), (12, 24, 2),
    (13, 10, 1), (13, 23, 1),
    (14, 19, 2), (14, 13, 1);
