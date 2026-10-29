"""Donanım kablolama sihirbazı: hangi kablo nereye, adım adım. Pin numaraları config/pins.yaml'dan okunur."""
import subprocess

import yaml

from ortak import (MOCK, ROOT, ask_float, ask_yn, baslik, say, sorun)

# BCM GPIO -> fiziksel pin (40 pinli başlık)
BCM2PIN = {2: 3, 3: 5, 4: 7, 14: 8, 15: 10, 17: 11, 18: 12, 27: 13, 22: 15, 23: 16, 24: 18, 10: 19, 9: 21,
           25: 22, 11: 23, 8: 24, 7: 26, 5: 29, 6: 31, 12: 32, 13: 33, 19: 35, 16: 36, 26: 37, 20: 38, 21: 40}
GND_PINS = {6, 9, 14, 20, 25, 30, 34, 39}
P3V3 = (1, 17)
FIZIK_ISIM = {1: "3V3", 2: "5V", 4: "5V", 17: "3V3"}


def pins():
    return yaml.safe_load(open(ROOT / "config" / "pins.yaml", encoding="utf-8"))


def etiketler(p):
    """fiziksel pin -> kısa açıklama"""
    e = {}
    for side, ad in (("left", "SOL"), ("right", "SAĞ")):
        m, n = p["motors"][side], p["encoders"][side]
        e[BCM2PIN[m["pwm"]]] = f"{ad} L298N ENA"
        e[BCM2PIN[m["in1"]]] = f"{ad} L298N IN1"
        e[BCM2PIN[m["in2"]]] = f"{ad} L298N IN2"
        e[BCM2PIN[n["a"]]] = f"{ad} ENKODER A"
        e[BCM2PIN[n["b"]]] = f"{ad} ENKODER B"
    e[1] = "SOL ENKODER güç (3,3V)"
    e[17] = "SAĞ ENKODER güç (3,3V)"
    e[6] = "ORTAK GND (yıldız nokta)"
    e[14] = "SOL ENKODER GND"
    e[20] = "SAĞ ENKODER GND"
    return e


def baslik_tablosu():
    """Pi'nin 40 pinli başlığı, kullanılan pinler işaretli (ekranda kalır, Pi kapansa da bakabilirsin)."""
    e = etiketler(pins())
    say("\nRaspberry Pi 5 — 40 pinli başlık (iki sıra metal pin). Pin 1: köşede, kartta KARE lehim pedi olan pin.\n"
        "TEK numaralı pinler (1,3,5…) kartın İÇ tarafındaki sırada, ÇİFT numaralılar (2,4,6…) kart KENARINA yakın sıradadır.\n"
        "Pin 1'den başlayıp say; sonra bir arkadaşınla yeniden say.", "y")
    say("\n  tek numaralı pinler            çift numaralı pinler")
    say("  (kart kenarına uzak)           (kart kenarına yakın)\n")
    for k in range(1, 41, 2):
        o, c = k, k + 1
        lo = e.get(o, FIZIK_ISIM.get(o, "GND" if o in GND_PINS else ""))
        lc = e.get(c, FIZIK_ISIM.get(c, "GND" if c in GND_PINS else ""))
        mo = "●" if o in e else "○"
        mc = "●" if c in e else "○"
        say(f"  {lo:>26} {mo} {o:>2}  {c:>2} {mc} {lc}")
    say("\n  ● = bu projede kullanılan pin,  ○ = boş bırak", "b")
    say("  ⚠️  Pin 1 (3,3 V) ile hemen YANINDAKİ pin 2 (5 V) birbirine çok yakın! Enkoder gücünü SADECE pin 1 ve\n"
        "  pin 17'ye (3,3 V) tak. 5 V'a (pin 2, 4) takarsan Pi'nin pini YANAR.", "r")


def kontrol_et(soru):
    return ask_yn(soru)


# ---------- A) ROBOT TARAFI: Pi'ye DOKUNMADAN ----------
def a_kablo_robot():
    baslik("KABLOLAMA 1/2 — Robot tarafı (Pi'ye dokunmadan)")
    say("Bu bölümde araç üzerindeki parçaları birbirine bağlayacaksın. Raspberry Pi bu sırada masada kendi\n"
        "şarj adaptöründe takılı kalabilir (kurulumu o yüzden yaptık). Pi'ye KABLO TAKMAYACAĞIZ.\n"
        "Gerekenler: multimetre, küçük tornavida, kablolar, etiket/bant, tel soyucu.")
    say("\n⚠️  Batarya ÇIKARILMIŞ olmalı ve ana şalter KAPALI olmalı. Bu bölümde ölçüm için bir ara takacağız;\n"
        "program sana söyleyecek.", "y")
    if not ask_yn("Batarya şu an aracın içinde TAKILI DEĞİL ve şalter kapalı mı?"):
        say("Bataryayı çıkar, sonra tekrar çalıştır: arac", "r")
        return False
    if MOCK:
        say("(deneme modu: kablolama adımları atlandı)", "y")
        return True

    adimlar = [
        ("1) Güç dağıtım hattı",
         "Şu sırayla bağla (kalın kablolar; her kablonun iki ucuna etiket yapıştır):\n"
         "   Batarya konnektörü (+)  →  ANA ŞALTER  →  SİGORTA (7,5–10 A)  →  GÜÇ DAĞITIM (+) klemensi\n"
         "   Batarya konnektörü (−)  →  GÜÇ DAĞITIM GND klemensi (yıldız GND noktası)\n"
         "Bataryayı henüz TAKMA."),
        ("2) Üç regülatörün girişi",
         "Üç regülatörün GİRİŞİNİ (IN+ ve IN−) güç dağıtıma bağla:\n"
         "   MOTOR REGÜLATÖRÜ (12 V, ≥4 A) : IN+ → dağıtım (+)    IN− → dağıtım GND\n"
         "   Pi DC-DC (5 V USB-C)          : IN+ → dağıtım (+)    IN− → dağıtım GND\n"
         "   MP1584EN (LiDAR, 5 V)         : IN+ → dağıtım (+)    IN− → dağıtım GND\n"
         "ÇIKIŞ uçlarını henüz hiçbir şeye BAĞLAMA."),
    ]
    for t, m in adimlar:
        say(f"\n--- {t} ---", "b")
        say(m)
        if not ask_yn("Yaptın mı?", "e"):
            return False

    say("\n--- 3) BİP TESTİ (kısa devre kontrolü) ---", "b")
    say("Multimetreyi BİP (süreklilik) konumuna al. Bataryanın hâlâ takılı olmadığından emin ol.\n"
        "Bir probu GÜÇ DAĞITIM (+), diğerini GÜÇ DAĞITIM GND klemensine değdir (şalter açık/kapalı fark etmez, sigorta takılı).")
    if not ask_yn("Multimetre BİP SESİ ÇIKARDI mı? (bip = kısa devre)", "h"):
        pass
    else:
        say("Kısa devre var! Bataryayı TAKMA. Kabloları tek tek çıkararak hangisinin kısa yaptığını bul "
            "(+ ile − uçları birbirine değiyor olabilir). Düzelttikten sonra tekrar: arac", "r")
        return sorun("Güç dağıtımda kısa devre.")

    say("\n--- 4) Regülatörleri AYARLA (tek tek) ---", "b")
    say("Şimdi bataryayı tak ve şalteri aç. Regülatörlerin çıkışına hiçbir şey bağlı OLMASIN.\n"
        "Multimetreyi gerilim (V, düz çizgi =) konumuna al; kırmızı prob regülatör OUT+, siyah prob OUT−.\n"
        "Regülatör üzerindeki küçük vidayı küçük tornavidayla yavaşça çevirerek ayarla.")
    if not ask_yn("Batarya takıldı, şalter açık, çıkışlar boşta. Hazır mısın?"):
        return False
    b = ask_float("Önce BATARYA geriliminin (dağıtım + ile GND arası)", 14.0, 16.9, "batarya_V",
                  "14,0 V altı: bataryayı şarj et. 16,9 V üstü: bataryada sorun var, kullanma.")
    if b is None:
        return False
    m = ask_float("MOTOR REGÜLATÖRÜ çıkışını 12,0 V yapacak şekilde ayarla. Ölçtüğün gerilim", 11.7, 12.3, "motor_regulator_V",
                  "Vidayı çevirip 12,0 V'a getir; 12,3 V üstüne ÇIKMA (motorlar/L298N zarar görür).")
    if m is None:
        return False
    pdc = ask_float("Pi DC-DC çıkışını (5,0–5,2 V) ölç ve yaz", 5.0, 5.2, "pi_dcdc_V",
                    "Ayarlanabilir değilse bu modül uygun değildir: öğretmene haber ver.")
    if pdc is None:
        return False
    mp = ask_float("MP1584EN çıkışını 5,00 V yapacak şekilde ayarla. Ölçtüğün gerilim", 4.95, 5.10, "mp1584_V",
                   "LiDAR için 4,9–5,2 V gerekir; hedef 5,00 V. Vidayı çevirerek ayarla.")
    if mp is None:
        return False
    say("\nŞimdi ŞALTERİ KAPAT ve bataryayı ÇIKAR.", "y")
    if not ask_yn("Şalter kapalı ve batarya çıkarıldı mı?"):
        return False

    adimlar = [
        ("5) Motor sürücüleri (iki L298N)",
         "Her L298N için aynısını yap:\n"
         "   • ENA jumper'ını (ENA pininin yanındaki küçük plastik kapak) ÇIKAR.\n"
         "   • 5V-EN jumper'ı TAKILI kalsın. Kartın '5V' terminaline HİÇBİR ŞEY bağlama.\n"
         "   • +12V girişi  ← MOTOR REGÜLATÖRÜ OUT+\n"
         "   • GND          ← güç dağıtım GND (yıldız nokta), KALIN kablo\n"
         "Motor regülatörü OUT− da yıldız GND'ye gider."),
        ("6) Motorlar",
         "SOL motorun iki güç kablosu → SOL L298N  OUT1 ve OUT2 (hangisi hangisi önemli değil, yazılım düzeltir)\n"
         "SAĞ motorun iki güç kablosu → SAĞ L298N OUT1 ve OUT2\n"
         "Kablo uçlarının klemensde sıkı durduğunu hafifçe çekerek dene."),
        ("7) LiDAR gücü",
         "MP1584EN OUT+ → LiDAR USB adaptörünün HARİCİ 5V giriş (+)\n"
         "MP1584EN OUT− → LiDAR adaptörünün harici GND\n"
         "USB kablosunu şimdilik adaptöre TAKMA (Pi'ye sonra takılacak)."),
        ("8) Pi DC-DC çıkış kablosu",
         "Pi DC-DC OUT çıkışına USB-C kablosunu bağla ve ucunu şimdilik havada bırak (Pi'ye takma!).\n"
         "OUT− (GND) yıldız GND noktasına da bağlanır."),
        ("9) Enkoder kabloları (motor tarafı)",
         "İki enkoderin kablolarını (VCC, GND, A, B) Pi tarafına gelecek uzunlukta bırak ve etiketle\n"
         "(SOL-VCC, SOL-GND, SOL-A, SOL-B, SAĞ-... ). Pi'ye takmayacağız, sadece etiketle.\n"
         "Motor kabloları ile enkoder kabloları mümkünse AYRI demetlerde ilerlesin (gürültü olmasın)."),
    ]
    for t, m in adimlar:
        say(f"\n--- {t} ---", "b")
        say(m)
        if not ask_yn("Yaptın mı?", "e"):
            return False

    say("\n--- 10) İkinci BİP TESTİ ---", "b")
    say("Bataryasız, multimetre BİP konumunda: GÜÇ DAĞITIM (+) ile GND arası ve her L298N'in +12V girişi ile GND'si arası.")
    if not ask_yn("Hiçbirinde BİP çıkmadı mı?", "e"):
        return sorun("Kablolamada kısa devre; düzeltmeden devam edilmez.")
    tak_ok = True
    say("\nRobot tarafı tamam ✓. Sıradaki adımda Pi'ye bağlanacaksın.", "g")
    return tak_ok


# ---------- B) Pi TARAFI ----------
def a_kablo_pi():
    baslik("KABLOLAMA 2/2 — Raspberry Pi tarafı")
    if MOCK:
        say("(deneme modu: atlandı)", "y")
        return True
    say("Bu bölümde Pi'nin pinlerine kablo takacaksın. Güvenlik için Pi'yi KAPATIP tüm güçleri çekeceğiz.\n"
        "Aşağıdaki pin tablosu ekranda kalacak. Pi kapanınca bu SSH penceresi kopar ama yazılar kaybolmaz:\n"
        "pencereyi KAPATMA, sadece aşağı kaydırıp tabloya bak. (İstersen telefonla fotoğrafını çek.)", "y")
    baslik_tablosu()
    p = pins()
    say("\n--- Takılacak kablolar ---", "b")
    rows = []
    for side, ad in (("left", "SOL"), ("right", "SAĞ")):
        m, n = p["motors"][side], p["encoders"][side]
        rows += [(f"{ad} L298N  ENA (PWM)", BCM2PIN[m["pwm"]]), (f"{ad} L298N  IN1", BCM2PIN[m["in1"]]),
                 (f"{ad} L298N  IN2", BCM2PIN[m["in2"]]),
                 (f"{ad} ENKODER A", BCM2PIN[n["a"]]), (f"{ad} ENKODER B", BCM2PIN[n["b"]])]
    rows += [("SOL ENKODER güç (VCC)", 1), ("SAĞ ENKODER güç (VCC)", 17),
             ("SOL ENKODER GND", 14), ("SAĞ ENKODER GND", 20),
             ("İki L298N GND ve güç GND'si (yıldız nokta)", 6)]
    for ad, pin in rows:
        say(f"   {ad:<44} →  Pi fiziksel pin {pin}")
    say("\nBu tablo bir daha lazım olursa:  arac kablo", "b")
    say("\nSıra: ÖNCE GND pinleri, SONRA sinyal kabloları, EN SON güç kabloları (3,3 V) takılır.", "y")
    if not ask_yn("Tabloyu inceledin ve fotoğrafını çektin / ekranı açık bıraktın mı? Pi'yi şimdi kapatacağız."):
        return False
    say("\nPi kapanacak. Kapanınca (yeşil ışık söner, 10 sn bekle) şunları yap:", "y")
    say("  1) Pi'nin DUVAR ŞARJ ADAPTÖRÜNÜ ÇEK. (Pi'ye aynı anda İKİ güç kaynağı bağlanmaz!)\n"
        "  2) Yukarıdaki pin tablosuna göre kabloları tak (önce GND, sonra sinyal, en son 3,3 V).\n"
        "  3) LiDAR USB kablosunu Pi'nin USB portuna tak (adaptör harici 5V ile beslenir, USB sadece veri).\n"
        "  4) Pi DC-DC'nin USB-C kablosunu Pi'nin güç girişine tak.\n"
        "  5) Her telin iki ucunu tabloya göre BİR ARKADAŞINLA birlikte kontrol et (biri okur, diğeri bakar).\n"
        "  6) Tekerlekleri HAVAYA kaldır (araç sehpada).\n"
        "  7) Bataryayı tak, şalteri aç. Pi açılır (1 dk).\n"
        "  8) SSH ile tekrar bağlan ve terminale yine:  arac")
    if not ask_yn("Anladın mı? Pi'yi ŞİMDİ kapatayım mı?"):
        return False
    from pathlib import Path
    (Path.home() / ".arac_pi_kapatildi").write_text("1")
    subprocess.run(["sudo", "shutdown", "-h", "now"])
    return False


def a_guc_dogrula():
    """Pi robot bataryasından açıldıktan sonra: güç sağlıklı mı?"""
    baslik("KABLOLAMA SONRASI — Güç kontrolü")
    if MOCK:
        say("(deneme modu: atlandı)", "y")
        return True
    say("Pi artık robotun bataryasından çalışıyor. Güç yeterli mi bakalım.")
    ok = True
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True).stdout.strip()
        say("   " + out)
        ok = out.endswith("0x0")
    except FileNotFoundError:
        say("   (vcgencmd yok, atlandı)", "y")
    if not ok:
        return sorun("Güç yetersiz (throttled ≠ 0x0): Pi DC-DC çıkışı, USB-C kablosu, bağlantıları kontrol et; 'arac acil' → B1.")
    say("   ✓ Güç sağlıklı", "g")
    return True


def tablo_goster():
    baslik_tablosu()
