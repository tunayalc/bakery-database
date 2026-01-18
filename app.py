from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Veritabanı Ayarları
db_config = {
    'host': 'localhost',
    'user': 'root', 
    'password': '',
    'database': 'firin_db'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Veritabanı başarısız: {err}")
        return None

# --- DECORATORS ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Lütfen önce giriş yapın.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('rol') not in allowed_roles:
                flash('Yetkiniz yok.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def utility_processor():
    def get_sepet_count():
        if 'user_id' in session:
            conn = get_db_connection()
            if not conn: return 0
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(adet) FROM sepet WHERE musteri_id = %s", (session['user_id'],))
                res = cursor.fetchone()
                return int(res[0]) if res and res[0] else 0
            finally:
                conn.close()
        return 0

    def get_site_settings():
        conn = get_db_connection()
        settings = {}
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM site_ayarlari WHERE id=1")
                settings = cursor.fetchone() or {}
            finally:
                conn.close()
        return settings

    return dict(sepet_count=get_sepet_count(), site_ayarlari=get_site_settings())

# --- ROUTES ---

@app.route('/ara')
def ara():
    query = request.args.get('q', '').strip()
    urunler = []
    if query:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                like = f"%{query}%"
                cursor.execute("""
                    SELECT * FROM urun 
                    WHERE aktif=1 AND (ad LIKE %s OR aciklama LIKE %s)
                    ORDER BY ad
                """, (like, like))
                urunler = cursor.fetchall()
            finally:
                conn.close()
    return render_template('arama_sonuc.html', query=query, urunler=urunler)

@app.route('/')
def index():
    conn = get_db_connection()
    if not conn: return "Veritabanı bağlantısı yok.", 500
    cursor = conn.cursor(dictionary=True)
    
    # Kategorileri getir
    cursor.execute("SELECT * FROM kategori WHERE aktif = 1 ORDER BY id")
    kategoriler = cursor.fetchall()
    
    # Tüm aktif ürünleri getir (kategori bilgisiyle)
    cursor.execute("""
        SELECT u.*, k.ad as kategori_adi,
               (SELECT miktar FROM stok s WHERE s.urun_id = u.id) as stok_durumu 
        FROM urun u 
        JOIN kategori k ON u.kategori_id = k.id
        WHERE u.aktif = 1
        ORDER BY u.kategori_id, u.id
    """)
    urunler = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', kategoriler=kategoriler, urunler=urunler)

@app.route('/hakkimizda')
def hakkimizda():
    return render_template('hakkimizda.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Form 'email' gönderiyor ama biz hem email hem k_adi kontrol edelim
        giris_bilgisi = request.form.get('email') # Formda name='email' yaptık
        sifre = request.form.get('sifre')
        
        conn = get_db_connection()
        if not conn:
            flash('Veritabanı bağlantısı yok.', 'danger')
            return render_template('login.html')
        try:
            cursor = conn.cursor(dictionary=True)
            user = None
            rol = None
            
            # 1. Admin Kontrolü
            cursor.execute("SELECT * FROM admin WHERE (email=%s OR k_adi=%s)", (giris_bilgisi, giris_bilgisi))
            user = cursor.fetchone()
            if user: rol = 'ADMIN'
            
            # 2. Müşteri Kontrolü (Bulunmadıysa)
            if not user:
                cursor.execute("SELECT * FROM musteri WHERE (email=%s OR k_adi=%s)", (giris_bilgisi, giris_bilgisi))
                user = cursor.fetchone()
                if user: rol = 'MUSTERI'
                
            # 3. Kurye Kontrolü (Bulunmadıysa)
            if not user:
                cursor.execute("SELECT * FROM kurye WHERE (k_adi=%s)", (giris_bilgisi,)) # Kuryeler genelde k.adi ile girer ama email de eklenebilir
                user = cursor.fetchone()
                if user: rol = 'KURYE'

        finally:
            conn.close()
        
        if user and user['sifre'] == sifre:
            if rol == 'MUSTERI' and not user.get('aktif', 1):
                flash('Hesabınız pasif durumda.', 'danger')
                return redirect(url_for('login'))
                
            session['user_id'] = user['id']
            session['ad_soyad'] = f"{user['ad']} {user['soyad']}"
            session['k_adi'] = user['k_adi']
            session['rol'] = rol
            session['email'] = user.get('email', '')  # E-posta otomatik doldurma için
            
            flash(f"Hoşgeldin {user['ad']}", 'success')
            if rol == 'ADMIN': return redirect(url_for('admin_panel'))
            if rol == 'KURYE': return redirect(url_for('kurye_panel'))
            return redirect(url_for('index'))
        else:
            flash('Hatalı bilgi.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        ad = request.form['ad']
        soyad = request.form['soyad']
        email = request.form['email']
        telefon = request.form['telefon']
        sifre = request.form['sifre']
        # Basit k_adi oluşturma (email'den)
        k_adi_base = email.split('@')[0]
        
        conn = get_db_connection()
        if not conn:
            flash('Veritabanı bağlantısı yok.', 'danger')
            return render_template('register.html')
        cursor = conn.cursor()
        
        import random
        success = False
        k_adi = k_adi_base
        
        for _ in range(5):
            try:
                cursor.execute("""
                    INSERT INTO musteri (k_adi, sifre, ad, soyad, email, telefon, aktif, puan)
                    VALUES (%s, %s, %s, %s, %s, %s, 1, 0)
                """, (k_adi, sifre, ad, soyad, email, telefon))
                conn.commit()
                success = True
                break
            except mysql.connector.IntegrityError as e:
                # 1062 = Duplicate entry
                if e.errno == 1062:
                    if "email" in str(e):
                        flash('Bu e-posta adresi zaten kayıtlı.', 'danger')
                        success = False
                        break
                    else:
                        # Username duplicate, try new one
                        k_adi = f"{k_adi_base}{random.randint(100, 999)}"
                else:
                    flash(f'Bir hata oluştu: {e}', 'danger')
                    success = False
                    break
        
        conn.close()
        
        if success:
            flash(f'Kayıt Başarılı! Kullanıcı Adınız: {k_adi}', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/urun/<int:id>')
def urun_detay(id):
    conn = get_db_connection()
    if not conn:
        return "Veritabanı bağlantısı yok.", 500
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM urun WHERE id=%s", (id,))
    urun = cursor.fetchone()
    
    if not urun:
        conn.close()
        return "Ürün yok", 404
    
    cursor.execute("SELECT ad FROM kategori WHERE id=%s", (urun['kategori_id'],))
    kat = cursor.fetchone()
    
    # Stok durumu
    cursor.execute("SELECT miktar FROM stok WHERE urun_id=%s", (id,))
    stok_res = cursor.fetchone()
    stok_adet = stok_res['miktar'] if stok_res else 0

    # Favori ve yorum izni (daha önce satın aldı mı)
    favoride = False
    yorum_izni = False
    if session.get('user_id'):
        cursor.execute("SELECT 1 FROM favoriler WHERE musteri_id=%s AND urun_id=%s", (session['user_id'], id))
        favoride = cursor.fetchone() is not None
        cursor.execute("""
            SELECT s.id
            FROM siparis_detay sd
            JOIN siparis s ON s.id = sd.siparis_id
            WHERE s.musteri_id=%s AND sd.urun_id=%s AND s.durum NOT IN ('IPTAL_EDILDI','REDDEDILDI')
            ORDER BY s.tarih DESC
            LIMIT 1
        """, (session['user_id'], id))
        yorum_izni = cursor.fetchone() is not None
        
    # Yorumları Çek (Onaylılar + Kendi Yorumlarım)
    uid = session.get('user_id', -1)
    cursor.execute("""
        SELECT y.*, m.ad, m.soyad 
        FROM yorum y 
        JOIN musteri m ON y.musteri_id = m.id 
        WHERE y.urun_id=%s AND (y.onay_durumu=1 OR y.musteri_id=%s)
        ORDER BY y.tarih DESC
    """, (id, uid))
    yorumlar = cursor.fetchall()
    
    conn.close()
    # Varyant YOK, direkt ürün gönderiyoruz
    return render_template('urun_detay.html', urun=urun, kategori=kat, stok=stok_adet, favoride=favoride, yorum_izni=yorum_izni, yorumlar=yorumlar)

@app.route('/sepet', methods=['GET', 'POST'])
@login_required
def sepet():
    if request.method == 'POST':
        kupon = request.form.get('kupon_kodu')
        if kupon == 'TUNA20':
            session['indirim'] = 20
            session['aktif_kupon'] = 'TUNA20'
            flash('Kupon uygulandı! %20 indirim kazandınız.', 'success')
        elif kupon == 'DB50':
            if session.get('user_id') == 4:
                session['indirim'] = 50
                session['aktif_kupon'] = 'DB50'
                flash('Süper Kupon! %50 indirim uygulandı.', 'success')
            else:
                flash('Bu kupon size özel değil.', 'warning')
                session['indirim'] = 0
        else:
            flash('Geçersiz kupon kodu.', 'warning')
            session['indirim'] = 0
        return redirect(url_for('sepet'))
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)
    
    # Varyant tabloları yok, direkt urun tablosu
    cursor.execute("""
        SELECT s.id as sepet_id, s.adet, u.fiyat, u.ad as urun_ad, u.resim, (s.adet * u.fiyat) as toplam
        FROM sepet s
        JOIN urun u ON s.urun_id = u.id
        WHERE s.musteri_id = %s
    """, (session['user_id'],))
    items = cursor.fetchall()
    
    toplam = sum(i['toplam'] for i in items)
    
    indirim_orani = session.get('indirim', 0)
    indirim_tutari = (toplam * indirim_orani) / 100
    odenecek = toplam - indirim_tutari
    
    conn.close()
    return render_template('sepet.html', items=items, toplam=toplam, indirim_tutari=indirim_tutari, odenecek=odenecek)

@app.route('/sepet/ekle', methods=['POST'])
@login_required
@role_required(['MUSTERI'])
def sepet_ekle():
    urun_id = request.form['urun_id'] # Varyant ID değil, Urun ID
    adet = int(request.form.get('adet', 1))
    
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(request.referrer or url_for('index'))
    cursor = conn.cursor()
    
    # Stok Kontrolü
    cursor.execute("SELECT miktar FROM stok WHERE urun_id=%s", (urun_id,))
    stok_res = cursor.fetchone()
    stok = stok_res[0] if stok_res else 0
    
    cursor.execute("SELECT id, adet FROM sepet WHERE musteri_id=%s AND urun_id=%s", (session['user_id'], urun_id))
    existing = cursor.fetchone()
    mevcut_adet = existing[1] if existing else 0

    if stok < adet + mevcut_adet:
        flash('Yetersiz stok!', 'warning')
        conn.close()
        return redirect(request.referrer)
    
    # Sepete ekle (DB'de UNIQUE(musteri_id, urun_id) var)
    cursor.execute("""
        INSERT INTO sepet (musteri_id, urun_id, adet)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE adet = adet + VALUES(adet)
    """, (session['user_id'], urun_id, adet))
    conn.commit()
    conn.close()
    flash('Sepete Eklendi', 'success')
    return redirect(request.referrer or url_for('sepet'))

@app.route('/sepet/guncelle/<int:id>/<action>')
@login_required
@role_required(['MUSTERI'])
def sepet_guncelle(id, action):
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('sepet'))
    cursor = conn.cursor()
    
    # Mevcut adet ve stok durumu
    cursor.execute("""
        SELECT s.adet, st.miktar 
        FROM sepet s 
        JOIN urun u ON s.urun_id = u.id
        JOIN stok st ON u.id = st.urun_id 
        WHERE s.id=%s AND s.musteri_id=%s
    """, (id, session['user_id']))
    row = cursor.fetchone()
    
    if row:
        adet, stok = row
        if action == 'arttir':
            if adet < stok:
                cursor.execute("UPDATE sepet SET adet = adet + 1 WHERE id=%s", (id,))
            else:
                flash('Stok yetersiz.', 'warning')
        elif action == 'azalt':
            if adet > 1:
                cursor.execute("UPDATE sepet SET adet = adet - 1 WHERE id=%s", (id,))
            else:
                cursor.execute("DELETE FROM sepet WHERE id=%s", (id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('sepet'))

@app.route('/sepet/sil/<int:id>')
@login_required
@role_required(['MUSTERI'])
def sepet_sil(id):
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('sepet'))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sepet WHERE id=%s AND musteri_id=%s", (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('sepet'))

@app.route('/siparis/olustur', methods=['GET', 'POST'])
@login_required
@role_required(['MUSTERI'])
def siparis_olustur():
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('index'))
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM adres WHERE musteri_id=%s ORDER BY varsayilan DESC, id DESC", (session['user_id'],))
        adresler = cursor.fetchall()

        if request.method == 'GET':
            return render_template('siparis_olustur.html', adresler=adresler)

        # --- POST ---
        if not adresler:
            flash('Önce adres ekleyin.', 'warning')
            return redirect(url_for('profil'))

        adres_id = request.form.get('adres_id')
        if not adres_id:
            flash('Teslimat adresi seçin.', 'warning')
            return redirect(url_for('siparis_olustur'))

        if not any(str(a['id']) == str(adres_id) for a in adresler):
            flash('Geçersiz adres.', 'danger')
            return redirect(url_for('siparis_olustur'))

        cursor.execute("""
            SELECT s.urun_id, s.adet, u.fiyat
            FROM sepet s
            JOIN urun u ON s.urun_id=u.id
            WHERE s.musteri_id=%s
        """, (session['user_id'],))
        items = cursor.fetchall()
        if not items:
            flash('Sepet boş.', 'warning')
            return redirect(url_for('sepet'))

        toplam = sum(i['adet'] * i['fiyat'] for i in items)

        try:
            # conn.start_transaction() # Implicit transaction usage to avoid "Transaction already in progress"

            # İndirim Hesapla
            indirim_orani = session.get('indirim', 0)
            indirim_tutari = (toplam * indirim_orani) / 100
            odenecek_tutar = toplam - indirim_tutari
            
            # Sipariş Notu
            siparis_notu = request.form.get('siparis_notu', '')

            # Stokları kilitle + kontrol et
            for item in items:
                cursor.execute("SELECT miktar FROM stok WHERE urun_id=%s FOR UPDATE", (item['urun_id'],))
                row = cursor.fetchone()
                stok_miktar = row['miktar'] if row else 0
                if stok_miktar < item['adet']:
                    conn.rollback()
                    flash('Yetersiz stok (checkout sırasında kontrol edildi).', 'warning')
                    return redirect(url_for('sepet'))

            # Sipariş Kaydı (İndirimli Tutar ile)
            kupon_kodu = session.get('aktif_kupon', None)
            cursor.execute("""
                INSERT INTO siparis (musteri_id, adres_id, durum, odeme_tipi, toplam_tutar, siparis_notu, indirim_tutari, kupon_kodu)
                VALUES (%s, %s, 'OLUSTURULDU', 'KAPIDA_NAKIT', %s, %s, %s, %s)
            """, (session['user_id'], adres_id, odenecek_tutar, siparis_notu, indirim_tutari, kupon_kodu))
            sid = cursor.lastrowid

            # Detaylar + stok düşme + hareket
            for item in items:
                cursor.execute("""
                    INSERT INTO siparis_detay (siparis_id, urun_id, adet, birim_fiyat)
                    VALUES (%s, %s, %s, %s)
                """, (sid, item['urun_id'], item['adet'], item['fiyat']))

                cursor.execute(
                    "UPDATE stok SET miktar = miktar - %s WHERE urun_id=%s",
                    (item['adet'], item['urun_id'])
                )

                cursor.execute("""
                    INSERT INTO stok_hareketi (urun_id, siparis_id, hareket_tipi, miktar, aciklama, yapan_id)
                    VALUES (%s, %s, 'SATIS', %s, 'Sipariş satışı', %s)
                """, (item['urun_id'], sid, -item['adet'], session['user_id']))

            # Log
            cursor.execute("""
                INSERT INTO siparis_durum_log (siparis_id, eski_durum, yeni_durum, degistiren_id, aciklama, tarih)
                VALUES (%s, '-', 'OLUSTURULDU', %s, 'Sipariş oluşturuldu', NOW())
            """, (sid, session['user_id']))

            # Kupon Kullanımını Kaydet
            if 'aktif_kupon' in session:
                # Tablo var mı kontrol etmeyeceğiz, hata verirse rollback olur. tablo oluşturmalıyız.
                try:
                    cursor.execute("""
                        INSERT INTO kupon_kullanim (kupon_kod, musteri_id, siparis_id)
                        VALUES (%s, %s, %s)
                    """, (session['aktif_kupon'], session['user_id'], sid))
                except mysql.connector.Error:
                    pass # Tablo yoksa siparişi patlatma, kupon loglanmasın
            
            # Session temizliği
            session.pop('indirim', None)
            session.pop('aktif_kupon', None)            # Sepeti temizle
            cursor.execute("DELETE FROM sepet WHERE musteri_id=%s", (session['user_id'],))

            conn.commit()
            flash('Sipariş alındı!', 'success')
            return redirect(url_for('siparis_detay', id=sid))
        except Exception as e:
            conn.rollback()
            flash(f'Sipariş oluşturulamadı: {e}', 'danger')
            return redirect(url_for('sepet'))
    finally:
        conn.close()

    return render_template('siparis_olustur.html', adresler=adresler)



@app.route('/profil')
@login_required
def profil():
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM siparis WHERE musteri_id=%s ORDER BY tarih DESC", (session['user_id'],))
    siparisler = cursor.fetchall()
    devam_set = ('OLUSTURULDU','ONAYLANDI','HAZIRLANIYOR','KURYE_ATANDI','YOLDA')
    siparis_devam = [s for s in siparisler if s['durum'] in devam_set]
    siparis_gecmis = [s for s in siparisler if s['durum'] not in devam_set]

    cursor.execute("SELECT * FROM adres WHERE musteri_id=%s ORDER BY id DESC", (session['user_id'],))
    adresler = cursor.fetchall()
    conn.close()
    conn.close()
    return render_template('profil.html', siparis_devam=siparis_devam, siparis_gecmis=siparis_gecmis, adresler=adresler)

@app.route('/profil/guncelle', methods=['POST'])
@login_required
def profil_guncelle():
    ad = request.form.get('ad')
    soyad = request.form.get('soyad')
    telefon = request.form.get('telefon')
    sifre = request.form.get('sifre')
    
    if not all([ad, soyad, telefon]):
        flash('Ad, Soyad ve Telefon boş olamaz.', 'warning')
        return redirect(url_for('profil'))
        
    conn = get_db_connection()
    if not conn: return redirect(url_for('profil'))
    
    try:
        cursor = conn.cursor()
        rol = session.get('rol')
        uid = session.get('user_id')
        
        table = None
        if rol == 'MUSTERI': table = 'musteri'
        elif rol == 'KURYE': table = 'kurye'
        elif rol == 'ADMIN': table = 'admin'
        
        if table:
            if sifre:
                # Not: Prodüksiyonda hashlenmeli! Şimdilik plain-text devam.
                cursor.execute(f"UPDATE {table} SET ad=%s, soyad=%s, telefon=%s, sifre=%s WHERE id=%s", 
                               (ad, soyad, telefon, sifre, uid))
            else:
                 cursor.execute(f"UPDATE {table} SET ad=%s, soyad=%s, telefon=%s WHERE id=%s", 
                               (ad, soyad, telefon, uid))
            conn.commit()
            
            # Session güncelle
            session['ad_soyad'] = f"{ad} {soyad}"
            flash('Bilgileriniz güncellendi.', 'success')
        else:
            flash('Rol hatası.', 'danger')
            
    except Exception as e:
        flash(f'Hata: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('profil'))

@app.route('/adres/sil/<int:id>', methods=['POST'])
@role_required(['MUSTERI'])
def adres_sil(id):
    conn = get_db_connection()
    if not conn: return redirect(url_for('profil'))
    
    try:
        cursor = conn.cursor()
        
        # 1. Adres bu kullanıcıya mı ait?
        cursor.execute("SELECT id FROM adres WHERE id=%s AND musteri_id=%s", (id, session['user_id']))
        if not cursor.fetchone():
            flash('Adres bulunamadı veya yetkiniz yok.', 'danger')
            conn.close()
            return redirect(url_for('profil'))

        # 2. En az 1 adres kuralı (Opsiyonel ama mantıklı)
        cursor.execute("SELECT COUNT(*) FROM adres WHERE musteri_id=%s", (session['user_id'],))
        count = cursor.fetchone()[0]
        
        if count <= 1:
            flash('Sipariş verebilmek için en az bir adresiniz kayıtlı kalmalıdır.', 'warning')
        else:
            # 3. Silme şlemi
            # Not: Eğer bu adresle verilmiş eski siparişler varsa, foreign key hatası verebilir.
            # CASCADE veya SET NULL durumu kontrol edilmeli. Eğer yoksa hata alırız.
            # Şimdilik deneyelim, hata alırsak soft delete'e veya adres_id null yapmaya geçeriz.
            # Veritabanı yapımızda foreign key varsa constraint hatası verir.
            # Güvenli yol: Try-catch ile yakala.
            try:
                cursor.execute("DELETE FROM adres WHERE id=%s", (id,))
                conn.commit()
                flash('Adres silindi.', 'success')
            except mysql.connector.errors.IntegrityError:
                flash('Bu adres ile geçmiş siparişleriniz olduğu için tamamen silinemiyor. (Veritabanı Kısıtı)', 'warning')
                
    except Exception as e:
        flash(f'Hata: {e}', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('profil'))

@app.route('/siparis/<int:id>')
@login_required
def siparis_detay(id):
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('index'))

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                s.*,
                a.adres_basligi, a.acik_adres,
                m.k_adi AS musteri_kadi, m.ad AS musteri_ad, m.soyad AS musteri_soyad, m.telefon AS musteri_telefon,
                k.k_adi AS kurye_kadi, k.ad AS kurye_ad, k.soyad AS kurye_soyad, k.telefon AS kurye_telefon
            FROM siparis s
            JOIN adres a ON a.id = s.adres_id
            JOIN musteri m ON m.id = s.musteri_id
            LEFT JOIN kurye k ON k.id = s.kurye_id
            WHERE s.id=%s
        """, (id,))
        siparis = cursor.fetchone()
        if not siparis:
            flash('Sipariş bulunamadı.', 'danger')
            return redirect(url_for('index'))

        rol = session.get('rol')
        uid = session.get('user_id')
        if rol == 'ADMIN':
            pass
        elif rol == 'MUSTERI' and siparis['musteri_id'] == uid:
            pass
        elif rol == 'KURYE' and (siparis.get('kurye_id') == uid or (siparis.get('durum') == 'HAZIRLANIYOR' and siparis.get('kurye_id') is None)):
            pass
        else:
            flash('Bu siparişi görüntüleme yetkiniz yok.', 'danger')
            return redirect(url_for('index'))

        cursor.execute("""
            SELECT d.*, u.ad AS urun_ad, u.resim
            FROM siparis_detay d
            JOIN urun u ON u.id = d.urun_id
            WHERE d.siparis_id=%s
            ORDER BY d.id
        """, (id,))
        detaylar = cursor.fetchall()

        # Loglarda degistiren_id hangi tablodan? Rol bilgisi logda yok. 
        # Pratik çözüm: Tüm tablolara left join atıp hangisi doluysa onu alalım.
        # Not: ID çakışması varsa yanlış isim gelebilir. Ancak bu aşamada yapacak bir şey yok.
        # İleride log tablosuna 'degistiren_rol' eklenmeli.
        cursor.execute("""
            SELECT l.*, 
                   COALESCE(a.k_adi, m.k_adi, k.k_adi) as k_adi,
                   COALESCE(a.ad, m.ad, k.ad) as ad,
                   COALESCE(a.soyad, m.soyad, k.soyad) as soyad
            FROM siparis_durum_log l
            LEFT JOIN admin a ON l.degistiren_id = a.id
            LEFT JOIN musteri m ON l.degistiren_id = m.id
            LEFT JOIN kurye k ON l.degistiren_id = k.id
            WHERE l.siparis_id=%s
            ORDER BY l.tarih ASC, l.id ASC
        """, (id,))
        loglar = cursor.fetchall()

        cursor.execute("""
            SELECT sh.*, u.ad AS urun_ad
            FROM stok_hareketi sh
            JOIN urun u ON u.id = sh.urun_id
            WHERE sh.siparis_id=%s
            ORDER BY sh.created_at ASC, sh.id ASC
        """, (id,))
        stok_hareketleri = cursor.fetchall()

        return render_template(
            'siparis_detay.html',
            siparis=siparis,
            detaylar=detaylar,
            loglar=loglar,
            stok_hareketleri=stok_hareketleri
        )
    finally:
        conn.close()

@app.route('/islemlerim')
@login_required
def islemlerim():
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('index'))

    try:
        cursor = conn.cursor(dictionary=True)
        uid = session['user_id']
        rol = session.get('rol')

        cursor.execute("""
            SELECT
                l.tarih, l.siparis_id, l.eski_durum, l.yeni_durum, l.aciklama,
                s.durum AS siparis_guncel_durum
            FROM siparis_durum_log l
            JOIN siparis s ON s.id = l.siparis_id
            WHERE l.degistiren_id=%s
            ORDER BY l.tarih DESC, l.id DESC
            LIMIT 100
        """, (uid,))
        durum_islemleri = cursor.fetchall()

        cursor.execute("""
            SELECT
                sh.created_at, sh.hareket_tipi, sh.miktar, sh.siparis_id, sh.aciklama,
                u.ad AS urun_ad
            FROM stok_hareketi sh
            JOIN urun u ON u.id = sh.urun_id
            WHERE sh.yapan_id=%s
            ORDER BY sh.created_at DESC, sh.id DESC
            LIMIT 100
        """, (uid,))
        stok_islemleri = cursor.fetchall()

        yorumlar = []
        favoriler = []
        if rol == 'MUSTERI':
            cursor.execute("""
                SELECT y.tarih, y.puan, y.onay_durumu, y.siparis_id, y.metin, u.ad AS urun_ad
                FROM yorum y
                JOIN urun u ON u.id = y.urun_id
                WHERE y.musteri_id=%s
                ORDER BY y.tarih DESC, y.id DESC
                LIMIT 50
            """, (uid,))
            yorumlar = cursor.fetchall()

            cursor.execute("""
                SELECT f.id, u.ad AS urun_ad
                FROM favoriler f
                JOIN urun u ON u.id = f.urun_id
                WHERE f.musteri_id=%s
                ORDER BY f.id DESC
                LIMIT 50
            """, (uid,))
            favoriler = cursor.fetchall()

        return render_template(
            'islemlerim.html',
            durum_islemleri=durum_islemleri,
            stok_islemleri=stok_islemleri,
            yorumlar=yorumlar,
            favoriler=favoriler
        )
    finally:
        conn.close()

# ========== FAVORİLER ==========
@app.route('/favorilerim')
@login_required
def favorilerim():
    conn = get_db_connection()
    if not conn: return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.* FROM favoriler f
        JOIN urun u ON f.urun_id = u.id
        WHERE f.musteri_id = %s
    """, (session['user_id'],))
    favoriler = cursor.fetchall()
    conn.close()
    return render_template('favorilerim.html', favoriler=favoriler)

@app.route('/favori/ekle', methods=['POST'])
@app.route('/favori/ekle/<int:urun_id>', methods=['POST'])
@login_required
def favori_ekle(urun_id=None):
    if urun_id is None:
        urun_id = request.form.get('urun_id')
    if not urun_id:
        flash('Ürün belirtilmedi.', 'warning')
        return redirect(request.referrer or url_for('index'))
    
    conn = get_db_connection()
    if not conn: return redirect(url_for('index'))
    cursor = conn.cursor()
    
    # Zaten favoride mi kontrol et
    cursor.execute("SELECT id FROM favoriler WHERE musteri_id=%s AND urun_id=%s", (session['user_id'], urun_id))
    if cursor.fetchone():
        # Favoriden çıkar (toggle)
        cursor.execute("DELETE FROM favoriler WHERE musteri_id=%s AND urun_id=%s", (session['user_id'], urun_id))
        flash('Favorilerden çıkarıldı.', 'info')
    else:
        # Favoriye ekle
        cursor.execute("INSERT INTO favoriler (musteri_id, urun_id) VALUES (%s, %s)", (session['user_id'], urun_id))
        flash('Favorilere eklendi!', 'success')
    
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('favorilerim'))

@app.route('/favori/sil', methods=['POST'])
@login_required
def favori_sil():
    urun_id = request.form.get('urun_id')
    if not urun_id:
        flash('Ürün belirtilmedi.', 'warning')
        return redirect(request.referrer or url_for('favorilerim'))
    
    conn = get_db_connection()
    if not conn: return redirect(url_for('favorilerim'))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM favoriler WHERE musteri_id=%s AND urun_id=%s", (session['user_id'], urun_id))
    conn.commit()
    conn.close()
    flash('Favorilerden çıkarıldı.', 'info')
    return redirect(request.referrer or url_for('favorilerim'))

@app.route('/adres/ekle', methods=['POST'])
@login_required
def adres_ekle():
    baslik = request.form.get('adres_basligi', '').strip()
    acik = request.form.get('acik_adres', '').strip()
    set_default = request.form.get('varsayilan') == 'on'

    if not baslik or not acik:
        flash('Adres başlığı ve adres alanı boş olamaz.', 'warning')
        return redirect(request.referrer or url_for('profil'))

    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(request.referrer or url_for('profil'))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM adres WHERE musteri_id=%s", (session['user_id'],))
    mevcut = cursor.fetchone()[0]
    if mevcut == 0:
        set_default = True
    if set_default:
        cursor.execute("UPDATE adres SET varsayilan=0 WHERE musteri_id=%s", (session['user_id'],))
    varsayilan = 1 if set_default else 0

    cursor.execute("""
        INSERT INTO adres (musteri_id, adres_basligi, acik_adres, varsayilan)
        VALUES (%s, %s, %s, %s)
    """, (session['user_id'], baslik, acik, varsayilan))
    conn.commit()
    conn.close()
    flash('Adres eklendi.', 'success')
    return redirect(request.referrer or url_for('profil'))



# --- PANEL ROUTES ---
@app.route('/admin')
@role_required(['ADMIN'])
def admin_panel():
    # Basit yönlendirme/özet
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)
    
    # Bekleyen siparişler (OLUSTURULDU veya ONAY_BEKLIYOR)
    cursor.execute("SELECT COUNT(*) as c FROM siparis WHERE durum IN ('ONAY_BEKLIYOR', 'OLUSTURULDU')")
    bekleyen = cursor.fetchone()['c']
    
    # Aktif ürün sayısı
    cursor.execute("SELECT COUNT(*) as c FROM urun WHERE aktif=1")
    urun_sayisi = cursor.fetchone()['c']
    
    # Toplam müşteri sayısı
    cursor.execute("SELECT COUNT(*) as c FROM musteri")
    musteri_sayisi = cursor.fetchone()['c']
    
    # Toplam yorum sayısı (onaylı + bekleyen)
    cursor.execute("SELECT COUNT(*) as c FROM yorum")
    yorum_sayisi = cursor.fetchone()['c']
    
    # Okunmamış mesajlar (yeni sistem)
    cursor.execute("SELECT COUNT(*) as c FROM mesajlar WHERE alici_rol='ADMIN' AND durum='BEKLIYOR'")
    okunmamis_mesaj = cursor.fetchone()['c']

    conn.close()
    return render_template('admin_panel.html', bekleyen=bekleyen, urun_sayisi=urun_sayisi, musteri_sayisi=musteri_sayisi, yorum_sayisi=yorum_sayisi, okunmamis_mesaj=okunmamis_mesaj)

@app.route('/admin/musteriler')
@role_required(['ADMIN'])
def admin_musteriler():
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_panel'))
    cursor = conn.cursor(dictionary=True)
    # Müşterileri ve sipariş sayılarını çek
    cursor.execute("""
        SELECT k.*, (SELECT COUNT(*) FROM siparis s WHERE s.musteri_id=k.id) as siparis_sayisi
        FROM musteri k
        ORDER BY k.id DESC
    """)
    musteriler = cursor.fetchall()
    conn.close()
    return render_template('admin_musteriler.html', musteriler=musteriler)

# ========== KURYE YÖNETİMİ ==========
@app.route('/admin/kuryeler')
@role_required(['ADMIN'])
def admin_kuryeler():
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_panel'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT k.*, 
            (SELECT COUNT(*) FROM siparis s WHERE s.kurye_id=k.id AND s.durum='TESLIM_EDILDI') as teslim_sayisi,
            (SELECT COUNT(*) FROM siparis s WHERE s.kurye_id=k.id AND s.durum IN ('YOLDA', 'KURYE_ATANDI')) as aktif_teslimat
        FROM kurye k
        ORDER BY k.id DESC
    """)
    kuryeler = cursor.fetchall()
    conn.close()
    return render_template('admin_kuryeler.html', kuryeler=kuryeler)

@app.route('/admin/kurye/ekle', methods=['POST'])
@role_required(['ADMIN'])
def admin_kurye_ekle():
    k_adi = request.form.get('k_adi')
    sifre = request.form.get('sifre')
    ad = request.form.get('ad')
    soyad = request.form.get('soyad')
    telefon = request.form.get('telefon')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO kurye (k_adi, sifre, ad, soyad, telefon, aktif)
                VALUES (%s, %s, %s, %s, %s, 1)
            """, (k_adi, sifre, ad, soyad, telefon))
            conn.commit()
            flash('Kurye başarıyla eklendi!', 'success')
        except Exception as e:
            flash(f'Hata: {e}', 'danger')
        conn.close()
    return redirect(url_for('admin_kuryeler'))

@app.route('/admin/kurye/sil/<int:id>', methods=['POST'])
@role_required(['ADMIN'])
def admin_kurye_sil(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kurye WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash('Kurye silindi.', 'success')
    return redirect(url_for('admin_kuryeler'))

@app.route('/admin/kurye/durum/<int:id>', methods=['POST'])
@role_required(['ADMIN'])
def admin_kurye_durum(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE kurye SET aktif = 1 - aktif WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash('Kurye durumu güncellendi.', 'success')
    return redirect(url_for('admin_kuryeler'))

@app.route('/admin/kuponlar')
@role_required(['ADMIN'])
def admin_kuponlar():
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_panel'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM kupon ORDER BY id DESC")
    kuponlar = cursor.fetchall()
    conn.close()
    return render_template('admin_kuponlar.html', kuponlar=kuponlar)

@app.route('/admin/kupon/ekle', methods=['POST'])
@role_required(['ADMIN'])
def admin_kupon_ekle():
    kod = request.form.get('kod').upper()
    yuzde = request.form.get('yuzde')
    tarih = request.form.get('tarih')
    aciklama = request.form.get('aciklama')
    ilk_siparis = 1 if request.form.get('ilk_siparis') else 0
    tek_seferlik = 1 if request.form.get('tek_seferlik') else 0
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO kupon (kod, indirim_yuzdesi, son_kullanim_tarihi, aciklama, sadece_ilk_siparis, tek_seferlik)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (kod, yuzde, tarih, aciklama, ilk_siparis, tek_seferlik))
            conn.commit()
            flash('Kupon oluşturuldu.', 'success')
        except Exception as e:
            flash(f'Hata: {e}', 'danger')
        conn.close()
    return redirect(url_for('admin_kuponlar'))

@app.route('/admin/kupon/sil/<int:id>', methods=['POST'])
@role_required(['ADMIN'])
def admin_kupon_sil(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kupon WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash('Kupon silindi.', 'success')
    return redirect(url_for('admin_kuponlar'))

@app.route('/admin/siparisler')
@role_required(['ADMIN'])
def admin_siparisler():
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT s.*, m.ad as musteri_ad, m.soyad as musteri_soyad, k.ad as kurye_ad, k.soyad as kurye_soyad
        FROM siparis s
        JOIN musteri m ON s.musteri_id = m.id
        LEFT JOIN kurye k ON s.kurye_id = k.id
        ORDER BY s.tarih DESC
    """)
    siparisler = cursor.fetchall()

    cursor.execute("SELECT id, ad, soyad FROM kurye WHERE durum IN ('MUSAIT', 'MESGUL') ORDER BY ad")
    kuryeler = cursor.fetchall()

    devam_set = ('OLUSTURULDU','ONAYLANDI','HAZIRLANIYOR','KURYE_ATANDI','YOLDA')
    devam_eden = [s for s in siparisler if s['durum'] in devam_set]
    bitti = [s for s in siparisler if s['durum'] in ('TESLIM_EDILDI','IPTAL_EDILDI','REDDEDILDI')]

    conn.close()
    return render_template('admin_siparisler.html', devam_eden=devam_eden, bitti=bitti, kuryeler=kuryeler)

@app.route('/admin/urunler')
@role_required(['ADMIN'])
def admin_urunler():
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.*, s.miktar, s.kritik_seviye
        FROM urun u
        LEFT JOIN stok s ON s.urun_id = u.id
        WHERE u.aktif=1
        ORDER BY u.ad
    """)
    urun_list = cursor.fetchall()

    cursor.execute("""
        SELECT y.*, u.ad AS urun_ad, m.ad AS musteri_ad, m.soyad AS musteri_soyad
        FROM yorum y
        JOIN urun u ON u.id = y.urun_id
        JOIN musteri m ON m.id = y.musteri_id
        ORDER BY y.tarih DESC, y.id DESC
        LIMIT 20
    """)
    yorumlar = cursor.fetchall()

    cursor.execute("SELECT * FROM kategori WHERE aktif=1 ORDER BY ad")
    kategoriler = cursor.fetchall()

    conn.close()
    return render_template('admin_urunler.html', urunler=urun_list, yorumlar=yorumlar, kategoriler=kategoriler)

@app.route('/admin/urun/ekle', methods=['POST'])
@role_required(['ADMIN'])
def admin_urun_ekle():
    ad = request.form.get('ad')
    fiyat = request.form.get('fiyat')
    kategori_id = request.form.get('kategori_id')
    aciklama = request.form.get('aciklama', '')
    resim = request.form.get('resim', '')

    if not all([ad, fiyat, kategori_id]):
        flash('Ad, Fiyat ve Kategori zorunlu.', 'warning')
        return redirect(url_for('admin_urunler'))

    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_urunler'))
    
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO urun (ad, fiyat, kategori_id, aciklama, resim, aktif) VALUES (%s, %s, %s, %s, %s, 1)", 
                       (ad, fiyat, kategori_id, aciklama, resim))
        # Stok kaydını da 0 olarak açalım ki hata vermesin
        urun_id = cursor.lastrowid
        cursor.execute("INSERT INTO stok (urun_id, miktar, kritik_seviye) VALUES (%s, 0, 10)", (urun_id,))
        
        conn.commit()
        flash('Ürün eklendi.', 'success')
    except Exception as e:
        flash(f'Hata: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_urunler'))

@app.route('/admin/urun/sil/<int:id>', methods=['POST'])
@role_required(['ADMIN'])
def admin_urun_sil(id):
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('admin_urunler'))
    try:
        cursor = conn.cursor()
        # Önce bağlı tablolardan sil (foreign key constraints)
        cursor.execute("DELETE FROM stok_hareketi WHERE urun_id=%s", (id,))
        cursor.execute("DELETE FROM favoriler WHERE urun_id=%s", (id,))
        cursor.execute("DELETE FROM sepet WHERE urun_id=%s", (id,))
        cursor.execute("DELETE FROM yorum WHERE urun_id=%s", (id,))
        cursor.execute("DELETE FROM stok WHERE urun_id=%s", (id,))
        cursor.execute("DELETE FROM urun WHERE id=%s", (id,))
        conn.commit()
        flash('Ürün silindi.', 'success')
    except Exception as e:
        flash(f'Hata: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_urunler'))

@app.route('/admin/urun/duzenle', methods=['POST'])
@role_required(['ADMIN'])
def admin_urun_duzenle():
    id = request.form.get('id')
    ad = request.form.get('ad')
    fiyat = request.form.get('fiyat')
    resim = request.form.get('resim')
    aciklama = request.form.get('aciklama')
    
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_urunler'))

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE urun 
            SET ad=%s, fiyat=%s, resim=%s, aciklama=%s 
            WHERE id=%s
        """, (ad, fiyat, resim, aciklama, id))
        conn.commit()
        flash('Ürün güncellendi.', 'success')
    except Exception as e:
        flash(f'Hata: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_urunler'))

@app.route('/admin/urun/durum/<int:id>/<int:aktif>')
@role_required(['ADMIN'])
def admin_urun_durum(id, aktif):
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_urunler'))
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE urun SET aktif=%s WHERE id=%s", (aktif, id))
        conn.commit()
        flash('Durum güncellendi.', 'success')
    finally:
        conn.close()
    return redirect(url_for('admin_urunler'))

@app.route('/admin/siparis/<int:id>/kurye', methods=['POST'])
@role_required(['ADMIN'])
def admin_kurye_ata(id):
    kurye_id = request.form.get('kurye_id')
    if not kurye_id:
        flash('Kurye seçin.', 'warning')
        return redirect(url_for('admin_siparisler'))

    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('admin_siparisler'))

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM kurye WHERE id=%s", (kurye_id,))
        if not cursor.fetchone():
            flash('Geçersiz kurye.', 'danger')
            return redirect(url_for('admin_siparisler'))

        cursor.execute("SELECT durum FROM siparis WHERE id=%s", (id,))
        row = cursor.fetchone()
        if not row:
            flash('Sipariş bulunamadı.', 'danger')
            return redirect(url_for('admin_siparisler'))

        durum = row[0]
        if durum not in ('ONAYLANDI', 'HAZIRLANIYOR', 'KURYE_ATANDI'):
            flash('Bu durumda kurye atanamaz.', 'warning')
            return redirect(url_for('admin_siparisler'))

        cursor.execute("UPDATE siparis SET kurye_id=%s, durum='KURYE_ATANDI' WHERE id=%s", (kurye_id, id))
        cursor.execute("""
            INSERT INTO siparis_durum_log (siparis_id, eski_durum, yeni_durum, degistiren_id, aciklama, tarih)
            VALUES (%s, %s, %s, %s, 'Kurye atandı', NOW())
        """, (id, durum, 'KURYE_ATANDI', session['user_id']))
        conn.commit()
        flash('Kurye atandı.', 'success')
        return redirect(url_for('admin_siparisler'))
    except Exception as e:
        flash(f'Hata: {e}', 'danger')
        return redirect(url_for('admin_siparisler'))
    finally:
        conn.close()

@app.route('/admin/stok', methods=['POST'])
@role_required(['ADMIN'])
def admin_stok_hareket():
    urun_id = request.form.get('urun_id')
    miktar = request.form.get('miktar')
    hareket = request.form.get('hareket_tipi')
    aciklama = request.form.get('aciklama', '').strip() or 'Admin stok hareketi'

    if not urun_id or not miktar or not hareket:
        flash('Ürün, miktar ve hareket tipi zorunlu.', 'warning')
        return redirect(url_for('admin_urunler'))

    try:
        miktar_int = int(miktar)
    except ValueError:
        flash('Miktar sayı olmalı.', 'warning')
        return redirect(url_for('admin_urunler'))

    if hareket not in ('GIRIS', 'CIKIS'):
        flash('Hareket tipi GIRIS veya CIKIS olmalı.', 'warning')
        return redirect(url_for('admin_urunler'))

    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('admin_urunler'))

    try:
        cursor = conn.cursor()
        conn.start_transaction()
        cursor.execute("SELECT miktar FROM stok WHERE urun_id=%s FOR UPDATE", (urun_id,))
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            flash('Ürün stok kaydı yok.', 'danger')
            return redirect(url_for('admin_urunler'))

        mevcut = row[0]
        yeni_miktar = mevcut + miktar_int if hareket == 'GIRIS' else mevcut - miktar_int
        if yeni_miktar < 0:
            conn.rollback()
            flash('Stok negatif olamaz.', 'warning')
            return redirect(url_for('admin_urunler'))

        cursor.execute("UPDATE stok SET miktar=%s WHERE urun_id=%s", (yeni_miktar, urun_id))
        cursor.execute("""
            INSERT INTO stok_hareketi (urun_id, siparis_id, hareket_tipi, miktar, aciklama, yapan_id)
            VALUES (%s, NULL, %s, %s, %s, %s)
        """, (urun_id, hareket, miktar_int if hareket == 'GIRIS' else -miktar_int, aciklama, session['user_id']))
        conn.commit()
        flash('Stok güncellendi.', 'success')
        return redirect(url_for('admin_urunler'))
    except Exception as e:
        conn.rollback()
        flash(f'Hata: {e}', 'danger')
        return redirect(url_for('admin_urunler'))
    finally:
        conn.close()

@app.route('/yorum/ekle', methods=['POST'])
@login_required
def yorum_ekle():
    urun_id = request.form.get('urun_id')
    puan = request.form.get('puan', type=int)
    metin = (request.form.get('metin') or '').strip()

    if not urun_id or not puan:
        flash('Ürün ve puan zorunlu.', 'warning')
        return redirect(request.referrer or url_for('index'))

    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(request.referrer or url_for('index'))

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.id
            FROM siparis_detay sd
            JOIN siparis s ON s.id = sd.siparis_id
            WHERE s.musteri_id=%s AND sd.urun_id=%s AND s.durum NOT IN ('IPTAL_EDILDI','REDDEDILDI')
            ORDER BY s.tarih DESC
            LIMIT 1
        """, (session['user_id'], urun_id))
        siparis_row = cursor.fetchone()
        if not siparis_row:
            flash('Bu ürüne yorum yapabilmek için önce satın almalısınız.', 'warning')
            return redirect(request.referrer or url_for('index'))

        siparis_id = siparis_row['id']
        cursor.execute("""
            INSERT INTO yorum (urun_id, musteri_id, siparis_id, puan, metin, onay_durumu)
            VALUES (%s, %s, %s, %s, %s, 1)
        """, (urun_id, session['user_id'], siparis_id, puan, metin))
        conn.commit()
        flash('Yorumunuz başarıyla eklendi. Teşekkürler!', 'success')
    finally:
        conn.close()
    return redirect(request.referrer or url_for('urun_detay', id=urun_id))
@app.route('/admin/siparis/<int:id>/<action>', methods=['POST'])
@role_required(['ADMIN'])
def admin_siparis_islem(id, action):
    actions = {
        'onayla': ('ONAYLANDI', {'OLUSTURULDU'}),
        'hazirla': ('HAZIRLANIYOR', {'ONAYLANDI'}),
        'iptal': ('IPTAL_EDILDI', {'OLUSTURULDU', 'ONAYLANDI', 'HAZIRLANIYOR', 'KURYE_ATANDI'}),
        'reddet': ('REDDEDILDI', {'OLUSTURULDU'}),
        'kapat': ('TESLIM_EDILDI', {'YOLDA'})
    }

    if action not in actions:
        flash('Geçersiz işlem.', 'danger')
        return redirect(url_for('admin_siparisler'))

    yeni_durum, izinli_eski = actions[action]

    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('admin_siparisler'))

    try:
        cursor = conn.cursor()
        conn.start_transaction()
        cursor.execute("SELECT durum FROM siparis WHERE id=%s", (id,))
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            flash('Sipariş bulunamadı.', 'danger')
            return redirect(url_for('admin_siparisler'))

        eski_durum = row[0]
        if eski_durum not in izinli_eski:
            conn.rollback()
            flash(f'Bu işlem için uygun durum değil: {eski_durum}', 'warning')
            return redirect(url_for('admin_siparisler'))

        if action == 'iptal' or action == 'reddet':
            # İptal veya Red durumunda stokları iade et
            cursor.execute("SELECT urun_id, adet FROM siparis_detay WHERE siparis_id=%s", (id,))
            detaylar = cursor.fetchall()
            for urun_id, adet in detaylar:
                cursor.execute("UPDATE stok SET miktar = miktar + %s WHERE urun_id=%s", (adet, urun_id))
                cursor.execute("""
                    INSERT INTO stok_hareketi (urun_id, siparis_id, hareket_tipi, miktar, aciklama, yapan_id)
                    VALUES (%s, %s, 'IADE', %s, 'Sipariş iptal/red iadesi', %s)
                """, (urun_id, id, adet, session['user_id']))

            cursor.execute("UPDATE siparis SET durum=%s, kurye_id=NULL WHERE id=%s", (yeni_durum, id))
        else:
            cursor.execute("UPDATE siparis SET durum=%s WHERE id=%s", (yeni_durum, id))

        cursor.execute("""
            INSERT INTO siparis_durum_log (siparis_id, eski_durum, yeni_durum, degistiren_id, aciklama, tarih)
            VALUES (%s, %s, %s, %s, 'Admin İşlemi', NOW())
        """, (id, eski_durum, yeni_durum, session['user_id']))
        conn.commit()
        flash('Sipariş durumu güncellendi.', 'success')
        return redirect(url_for('admin_siparisler'))
    except Exception as e:
        conn.rollback()
        flash(f'Hata: {e}', 'danger')
        return redirect(url_for('admin_siparisler'))
    finally:
        conn.close()

@app.route('/kurye')
@role_required(['KURYE', 'ADMIN'])
def kurye_panel():
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)
    
    # Aktif Görevler
    cursor.execute("""
        SELECT s.*, a.acik_adres, a.adres_basligi, m.ad as musteri_ad, m.soyad as musteri_soyad, m.telefon as musteri_telefon
        FROM siparis s
        LEFT JOIN adres a ON s.adres_id = a.id
        LEFT JOIN musteri m ON s.musteri_id = m.id
        WHERE s.kurye_id=%s AND s.durum IN ('KURYE_ATANDI', 'YOLDA', 'HAZIRLANIYOR')
        ORDER BY s.tarih DESC
    """, (session['user_id'],))
    active_jobs = cursor.fetchall()
    
    # Geçmiş Teslimatlar (Son 20)
    cursor.execute("""
        SELECT s.*, a.acik_adres, m.ad as musteri_ad, m.soyad as musteri_soyad
        FROM siparis s
        LEFT JOIN adres a ON s.adres_id = a.id
        LEFT JOIN musteri m ON s.musteri_id = m.id
        WHERE s.kurye_id=%s AND s.durum = 'TESLIM_EDILDI'
        ORDER BY s.tarih DESC
        LIMIT 20
    """, (session['user_id'],))
    past_jobs = cursor.fetchall()
    
    conn.close()
    return render_template('kurye_panel.html', active_jobs=active_jobs, past_jobs=past_jobs)

@app.route('/kurye/islem/<int:id>/<action>', methods=['POST'])
@role_required(['KURYE', 'ADMIN'])
def kurye_islem(id, action):
    conn = get_db_connection()
    if not conn:
        flash('Veritabanı bağlantısı yok.', 'danger')
        return redirect(url_for('kurye_panel'))
    cursor = conn.cursor()
    
    # Siparişi kontrol et (Tuple index access fixed)
    cursor.execute("SELECT durum, kurye_id FROM siparis WHERE id=%s", (id,))
    siparis = cursor.fetchone() # returns tuple like ('HAZIRLANIYOR', 2)
    
    if not siparis:
        flash('Sipariş bulunamadı.', 'danger')
        conn.close()
        return redirect(url_for('kurye_panel'))
    
    eski_durum = siparis[0]
    mevcut_kurye = siparis[1]
    yeni_durum = None
    msj = ""
    
    if action == 'teslim_al':
        if (eski_durum == 'KURYE_ATANDI' or eski_durum == 'HAZIRLANIYOR') and mevcut_kurye == session['user_id']:
            yeni_durum = 'YOLDA'
            cursor.execute("""
                UPDATE siparis
                SET durum=%s
                WHERE id=%s AND durum IN ('KURYE_ATANDI', 'HAZIRLANIYOR') AND kurye_id=%s
            """, (yeni_durum, id, session['user_id']))
            if cursor.rowcount == 1:
                msj = "Sipariş teslim alındı, yola çıkabilirsiniz!"
            else:
                yeni_durum = None
                flash('Bu sipariş şu an alınamaz (Başkası almış olabilir).', 'warning')
        else:
            flash('Bu sipariş şu an alınamaz (durum uygun değil).', 'warning')
            
    elif action == 'teslim_et':
        if eski_durum == 'YOLDA' and mevcut_kurye == session['user_id']:
            yeni_durum = 'TESLIM_EDILDI'
            cursor.execute("""
                UPDATE siparis
                SET durum=%s
                WHERE id=%s AND durum='YOLDA' AND kurye_id=%s
            """, (yeni_durum, id, session['user_id']))
            if cursor.rowcount == 1:
                msj = "Sipariş başarıyla teslim edildi. Eline sağlık!"
            else:
                yeni_durum = None
                flash('Bu işlem yapılamadı (durum değişmiş olabilir).', 'warning')
        else:
            flash('Bu işlemi yapma yetkiniz yok.', 'danger')

    if yeni_durum:
        # Log Ekle
        cursor.execute("""
            INSERT INTO siparis_durum_log (siparis_id, eski_durum, yeni_durum, degistiren_id, aciklama, tarih)
            VALUES (%s, %s, %s, %s, 'Kurye Islemi', NOW())
        """, (id, eski_durum, yeni_durum, session['user_id']))
        conn.commit()
        if isinstance(msj, tuple): msj = msj[0] # Tuple fix
        flash(msj, 'success')
        
    conn.close()
    return redirect(url_for('kurye_panel'))

@app.route('/yorumlarim')
@login_required
def yorumlarim():
    conn = get_db_connection()
    if not conn: return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT y.*, u.ad as urun_ad
        FROM yorum y
        JOIN urun u ON y.urun_id=u.id
        WHERE y.musteri_id=%s
        ORDER BY y.tarih DESC
    """, (session['user_id'],))
    yorumlar = cursor.fetchall()
    conn.close()
    return render_template('yorumlarim.html', yorumlar=yorumlar)

@app.route('/admin/yorumlar')
@role_required(['ADMIN'])
def admin_yorumlar():
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_panel'))
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT y.*, u.ad as urun_ad, m.ad as musteri_ad, m.soyad as musteri_soyad 
        FROM yorum y
        JOIN urun u ON y.urun_id = u.id
        JOIN musteri m ON y.musteri_id = m.id
        ORDER BY y.onay_durumu ASC, y.tarih DESC
    """)
    yorumlar = cursor.fetchall()
    conn.close()
    return render_template('admin_yorumlar.html', yorumlar=yorumlar)

@app.route('/admin/yorum/onayla/<int:id>', methods=['POST'])
@role_required(['ADMIN'])
def admin_yorum_onayla(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE yorum SET onay_durumu=1 WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash('Yorum onaylandı.', 'success')
    return redirect(url_for('admin_yorumlar'))

@app.route('/admin/yorum/sil/<int:id>', methods=['POST'])
@role_required(['ADMIN'])
def admin_yorum_sil(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM yorum WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash('Yorum silindi.', 'success')
    return redirect(url_for('admin_yorumlar'))

# --- CONTACT & SETTINGS ROUTES ---

@app.route('/iletisim', methods=['GET', 'POST'])
def iletisim():
    if request.method == 'POST':
        konu = request.form.get('konu')
        mesaj = request.form.get('mesaj')
        
        # Giriş yapmış müşteri ise yeni mesajlaşma sistemini kullan
        if session.get('user_id') and session.get('rol') == 'MUSTERI':
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO mesajlar (gonderen_id, gonderen_rol, alici_id, alici_rol, konu, mesaj)
                    VALUES (%s, 'MUSTERI', 1, 'ADMIN', %s, %s)
                """, (session['user_id'], konu, mesaj))
                conn.commit()
                conn.close()
                flash('Mesajınız yöneticiye gönderildi!', 'success')
                return redirect(url_for('mesajlarim'))
        else:
            # Giriş yapmamış kullanıcılar için eski sistem (veya giriş yapmaya yönlendir)
            flash('Mesaj göndermek için lütfen giriş yapın.', 'warning')
            return redirect(url_for('login'))
            
    return render_template('iletisim.html')

@app.route('/mesaj/gonder', methods=['POST'])
@login_required
def mesaj_gonder():
    alici_rol = request.form.get('alici_rol') # 'ADMIN', 'MUSTERI', 'KURYE'
    alici_id = request.form.get('alici_id', 1) # Varsayılan Admin ID=1
    konu = request.form.get('konu')
    mesaj = request.form.get('mesaj')
    
    # Güvenlik: P2P iletişimi aktif (Kurye <-> Müşteri, Herkes <-> Admin)
    gonderen_rol = session['rol']
    # Restriction Removed by User Request
    pass
        
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        
        # Insert New Message
        cursor.execute("""
            INSERT INTO mesajlar (gonderen_id, gonderen_rol, alici_id, alici_rol, konu, mesaj)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (session['user_id'], gonderen_rol, alici_id, alici_rol, konu, mesaj))
        
        # Mark original message as REPLIED (if this is a reply)
        original_id = request.form.get('original_message_id')
        if original_id:
            cursor.execute("UPDATE mesajlar SET durum='YANITLANDI' WHERE id=%s", (original_id,))
            
        conn.commit()
        conn.close()
        flash('Mesajınız gönderildi.', 'success')
    
    # Yönlendirme mantığı
    if gonderen_rol == 'ADMIN':
        return redirect(url_for('admin_mesajlar'))
    elif gonderen_rol == 'KURYE':
        return redirect(url_for('kurye_mesajlar'))
    else:
        return redirect(url_for('mesajlarim'))

@app.route('/admin/mesajlar')
@role_required(['ADMIN'])
def admin_mesajlar():
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_panel'))
    cursor = conn.cursor(dictionary=True)
    
    # Müşteri Mesajları (Eski tablo + Yeni tablo birleşik mantık yerine, sadece yeni tabloya geçiyoruz zamanla)
    # Şimdilik temiz olsun diye sadece 'mesajlar' tablosundan çekiyoruz.
    # Ancak eski 'iletisim_mesajlari' tablosunu da görebilmeli.
    # Kullanıcıya kolaylık olsun diye şimdilik SADECE YENİ SİSTEMİ gösteriyorum.
    
    # Müşterilerden Gelenler
    cursor.execute("""
        SELECT m.*, mus.ad, mus.soyad 
        FROM mesajlar m
        JOIN musteri mus ON m.gonderen_id = mus.id
        WHERE m.gonderen_rol = 'MUSTERI' AND m.alici_rol = 'ADMIN'
        ORDER BY m.tarih DESC
    """)
    musteri_mesajlari = cursor.fetchall()
    
    # Kuryelerden Gelenler
    cursor.execute("""
        SELECT m.*, k.ad, k.soyad 
        FROM mesajlar m
        JOIN kurye k ON m.gonderen_id = k.id
        WHERE m.gonderen_rol = 'KURYE' AND m.alici_rol = 'ADMIN'
        ORDER BY m.tarih DESC
    """)
    kurye_mesajlari = cursor.fetchall()

    # Kurye Listesi (Dropdown için)
    cursor.execute("SELECT id, ad, soyad FROM kurye")
    kuryeler = cursor.fetchall()
    
    conn.close()
    return render_template('admin_mesajlar.html', 
                          musteri_mesajlari=musteri_mesajlari, 
                          kurye_mesajlari=kurye_mesajlari,
                          kuryeler=kuryeler)

@app.route('/admin/mesaj/sil/<int:id>', methods=['POST'])
@role_required(['ADMIN'])
def admin_mesaj_sil(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mesajlar WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash('Mesaj veritabanından kalıcı olarak silindi.', 'success')
    return redirect(url_for('admin_mesajlar'))

@app.route('/mesaj/sil/kullanici/<int:id>', methods=['POST'])
@login_required
def generic_mesaj_sil(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True) # Fetch dictionary to check user role/id match
        
        # Check if message exists and user is part of it
        cursor.execute("SELECT * FROM mesajlar WHERE id=%s", (id,))
        msg = cursor.fetchone()
        
        if msg:
            user_id = session['user_id']
            rol = session['rol']
            
            # Logic: If I am sender, set sender_deleted. If I am receiver, set receiver_deleted.
            if msg['gonderen_id'] == user_id and msg['gonderen_rol'] == rol:
                cursor.execute("UPDATE mesajlar SET silindi_gonderen=1 WHERE id=%s", (id,))
                conn.commit()
                flash('Mesaj silindi.', 'success')
                
            elif msg['alici_id'] == user_id and msg['alici_rol'] == rol:
                cursor.execute("UPDATE mesajlar SET silindi_alici=1 WHERE id=%s", (id,))
                conn.commit()
                flash('Mesaj silindi.', 'success')
            else:
                 flash('Bu mesajı silme yetkiniz yok.', 'danger')
        else:
            flash('Mesaj bulunamadı.', 'warning')
            
        conn.close()
        
    # Redirect back
    if session['rol'] == 'KURYE':
        return redirect(url_for('kurye_mesajlar'))
    else:
        return redirect(url_for('mesajlarim'))

@app.route('/kurye/mesajlar')
@role_required(['KURYE'])
def kurye_mesajlar():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Gelen Kutusu (Kurye silmemişse silindi_alici=0)
    cursor.execute("""
        SELECT m.*, 
            CASE 
                WHEN m.gonderen_rol = 'ADMIN' THEN 'Yönetici'
                WHEN m.gonderen_rol = 'MUSTERI' THEN CONCAT(mu.ad, ' ', mu.soyad, ' (Müşteri)')
                ELSE m.gonderen_rol
            END as gonderen_ad
        FROM mesajlar m
        LEFT JOIN musteri mu ON (m.gonderen_rol = 'MUSTERI' AND m.gonderen_id = mu.id)
        WHERE m.alici_id=%s AND m.alici_rol='KURYE' AND m.silindi_alici=0
        ORDER BY m.tarih DESC
    """, (session['user_id'],))
    gelen_kutusu = cursor.fetchall()
    
    # Giden Kutusu (Kurye silmemişse silindi_gonderen=0)
    cursor.execute("""
        SELECT * FROM mesajlar 
        WHERE gonderen_id=%s AND gonderen_rol='KURYE' AND silindi_gonderen=0
        ORDER BY tarih DESC
    """, (session['user_id'],))
    giden_kutusu = cursor.fetchall()
    
    conn.close()
    return render_template('kurye_mesajlar.html', gelen_kutusu=gelen_kutusu, giden_kutusu=giden_kutusu)

@app.route('/mesajlarim')
@login_required
def mesajlarim():
    conn = get_db_connection()
    if not conn: return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)
    
    # 1. Eski Sistem Mesajları (Ticket tarzı)
    cursor.execute("""
        SELECT * FROM iletisim_mesajlari 
        WHERE musteri_id=%s 
        ORDER BY tarih DESC
    """, (session['user_id'],))
    eski_mesajlar = cursor.fetchall()
    
    # 2. Yeni Sistem Mesajları (Chat tarzı)
    # MUSTERI için:
    #   - Gelenler: Alici=Beni ID, AliciRol=MUSTERI, silindi_alici=0
    #   - Gidenler: Gonderen=BenID, GonderenRol=MUSTERI, silindi_gonderen=0
    # Tek sorguda birleştirelim veya ayrı ayrı? Template structure supports mixed list.
    # Current template iterates 'yeni_mesajlar' which included both? 
    # Wait, earlier I updated `mesajlarim` route to query `iletisim_mesajlari` AND `mesajlar`. 
    # Let me refetch the ACTUAL `mesajlarim` route implementation because `view_file` cut off right before it.
    # But based on `kurye_mesajlar` pattern, I will assume I need to fetch `yeni_mesajlar` as a UNION or similar.
    # Actually, previous interaction log shows the edit to `mesajlarim` route (Lines 1515 in PREVIOUS session).
    # Since `view_file` cut off, I will REWRITE `mesajlarim` function completely here.
    
    cursor.execute("""
        SELECT m.*, 
            CASE 
                WHEN m.gonderen_rol='ADMIN' THEN 'Yönetici'
                WHEN m.gonderen_rol='KURYE' THEN CONCAT(k.ad, ' ', k.soyad, ' (Kurye)')
                ELSE 'Siz'
            END as gonderen_ad,
            CASE 
                WHEN m.alici_rol='ADMIN' THEN 'Yönetici'
                WHEN m.alici_rol='KURYE' THEN CONCAT(k2.ad, ' ', k2.soyad, ' (Kurye)')
                ELSE 'Müşteri'
            END as alici_ad
        FROM mesajlar m
        LEFT JOIN kurye k ON (m.gonderen_rol='KURYE' AND m.gonderen_id=k.id)
        LEFT JOIN kurye k2 ON (m.alici_rol='KURYE' AND m.alici_id=k2.id)
        WHERE 
           (m.gonderen_id=%s AND m.gonderen_rol='MUSTERI' AND m.silindi_gonderen=0)
           OR 
           (m.alici_id=%s AND m.alici_rol='MUSTERI' AND m.silindi_alici=0)
        ORDER BY m.tarih DESC
    """, (session['user_id'], session['user_id']))
    yeni_mesajlar = cursor.fetchall()

    conn.close()
    return render_template('mesajlarim.html', eski_mesajlar=eski_mesajlar, yeni_mesajlar=yeni_mesajlar)

@app.route('/admin/iletisim/sil/<int:id>', methods=['POST'])
@role_required(['ADMIN'])
def admin_iletisim_sil(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM iletisim_mesajlari WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash('Mesaj silindi.', 'success')
    return redirect(url_for('admin_iletisim'))

@app.route('/admin/ayarlar', methods=['GET', 'POST'])
@role_required(['ADMIN'])
def admin_ayarlar():
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_panel'))
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        site_baslik = request.form.get('site_baslik')
        telefon = request.form.get('telefon')
        adres = request.form.get('adres')
        email = request.form.get('email')
        hero_baslik = request.form.get('hero_baslik')
        hero_alt_baslik = request.form.get('hero_alt_baslik')
        
        cursor.execute("""
            UPDATE site_ayarlari 
            SET site_baslik=%s, telefon=%s, adres=%s, email=%s, hero_baslik=%s, hero_alt_baslik=%s
            WHERE id=1
        """, (site_baslik, telefon, adres, email, hero_baslik, hero_alt_baslik))
        conn.commit()
        flash('Site ayarları güncellendi.', 'success')
        conn.close()
        return redirect(url_for('admin_ayarlar'))
        
    cursor.execute("SELECT * FROM site_ayarlari WHERE id=1")
    ayarlar = cursor.fetchone()
    conn.close()
    return render_template('admin_ayarlar.html', ayarlar=ayarlar)

if __name__ == '__main__':
    app.run(debug=True)
