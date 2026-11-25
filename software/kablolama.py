"""Donanım kablolama sihirbazı: hangi kablo nereye, adım adım. Pin numaraları config/pins.yaml'dan okunur."""
import subprocess
from pathlib import Path

import yaml

from ortak import (MOCK, ROOT, ask_float, ask_yn, baslik, olcum_kaydet, say, sorun)

# BCM GPIO -> fiziksel pin (40 pinli başlık)
BCM2PIN = {2: 3, 3: 5, 4: 7, 14: 8, 15: 10, 17: 11, 18: 12, 27: 13, 22: 15, 23: 16, 24: 18, 10: 19, 9: 21,
           25: 22, 11: 23, 8: 24, 7: 26, 5: 29, 6: 31, 12: 32, 13: 33, 19: 35, 16: 36, 26: 37, 20: 38, 21: 40}
GND_PINS = {6, 9, 14, 20, 25, 30, 34, 39}
P3V3 = (1, 17)
FIZIK_ISIM = {1: "3V3", 2: "5V", 4: "5V", 17: "3V3"}
# "Robot önceden komple kablolandı" yolu seçildiyse işaret dosyası (Pi kapanıp açılınca da hatırlansın)
HAZIR = Path.home() / (".arac_hazir_robot_deneme" if MOCK else ".arac_hazir_robot")


def pins():
    return yaml.safe_load(open(ROOT / "config" / "pins.yaml", encoding="utf-8"))


def etiketler(p):
    """fiziksel pin -> kısa açıklama"""
    e = {}
    for side, ad, k in (("left", "SOL", "A"), ("right", "SAĞ", "B")):
        m, n = p["motors"][side], p["encoders"][side]
        e[BCM2PIN[m["pwm"]]] = f"TB6612 PWM{k} ({ad})"
        e[BCM2PIN[m["in1"]]] = f"TB6612 {k}IN1 ({ad})"
        e[BCM2PIN[m["in2"]]] = f"TB6612 {k}IN2 ({ad})"
        e[BCM2PIN[n["a"]]] = f"{ad} ENKODER A"
        e[BCM2PIN[n["b"]]] = f"{ad} ENKODER B"
    e[BCM2PIN[p["driver"]["stby"]]] = "TB6612 STBY"
    e[1] = "TB6612 VCC (3,3V)"
    e[17] = "3,3V lojik hattı"
    e[6] = "TB6612 GND"
    e[14] = "GND lojik hattı"
    e[3] = "BNO055 SDA"
    e[5] = "BNO055 SCL"
    sb = p.get("start_button")
    if sb:
        e[BCM2PIN[sb["gpio"]]] = "BAŞLAT BUTONU"
        e[34] = "BAŞLAT BUTONU (GND)"
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
    say("  ⚠️  Pin 1 (3,3 V) ile hemen YANINDAKİ pin 2 (5 V) birbirine çok yakın! TB6612 VCC'yi, enkoder ve BNO055\n"
        "  gücünü SADECE 3,3 V'a (pin 1, 17) tak. 5 V'a (pin 2, 4) takarsan Pi'nin pini YANAR.", "r")


def kontrol_et(soru):
    return ask_yn(soru)


# ---------- ortak ölçüm adımları ----------
def bip_testi(baslik_metni, ek=""):
    say(f"\n--- {baslik_metni} ---", "b")
    say("Multimetreyi BİP (süreklilik) konumuna al. Bataryanın TAKILI OLMADIĞINDAN emin ol.\n"
        "Bir probu GÜÇ DAĞITIM (+) barasına, diğerini GND barasına değdir." + ek + "\n"
        "Regülatörlerin kondansatörleri yüzünden çok kısa bir 'cik' sesi normaldir; SÜREKLİ bip kısa devredir.")
    if ask_yn("Multimetre SÜREKLİ BİP SESİ ÇIKARDI mı? (sürekli bip = kısa devre)", "h"):
        say("Kısa devre var! Bataryayı TAKMA. Kabloları tek tek çıkararak hangisinin kısa yaptığını bul "
            "(+ ile − uçları birbirine değiyor olabilir). Düzelttikten sonra tekrar: arac", "r")
        return sorun("Güç dağıtımda kısa devre.")
    return True


def olc_batarya():
    return ask_float("BATARYA geriliminin (dağıtım + ile GND arası)", 10.5, 12.7, "batarya_V",
                     "10,5 V altı: 3S bataryayı şarj et. 12,7 V üstü: bu 3S değil ya da bataryada sorun var, kullanma.")


def olc_ham(soru, ad):
    """Ayarlamadan ÖNCEKİ (fabrika/eski) değeri kaydeder; aralık kontrolü yapmaz."""
    while True:
        a = input(f"\n{soru} (sayı yaz, örn. 5,02): ").strip().replace(",", ".")
        try:
            v = float(a)
        except ValueError:
            print("Lütfen sadece sayı yaz (virgül ya da nokta olur).")
            continue
        olcum_kaydet(ad, v)
        return v


def regulatorleri_ayarla():
    """Üç regülatörün çıkışını hedefe getirir. Çıkışlarda YÜK OLMAMALI."""
    say("Multimetreyi gerilim (V, düz çizgi =) konumuna al; kırmızı prob regülatör OUT+, siyah prob OUT−.\n"
        "Regülatör üzerindeki küçük vidayı küçük tornavidayla yavaşça çevirerek ayarla.")
    m = ask_float("MOTOR BUCK çıkışını 6,0 V yapacak şekilde ayarla. Ölçtüğün gerilim", 5.8, 6.2, "motor_regulator_V",
                  "Vidayı çevirip 6,0 V'a getir; 6,2 V üstüne ÇIKMA (N20 motorlar 6 V'luktur).")
    if m is None:
        return False
    pdc = ask_float("Pi REGÜLATÖRÜ (3 A buck) çıkışını 5,1 V yapacak şekilde ayarla. Ölçtüğün gerilim", 5.0, 5.2, "pi_dcdc_V",
                    "Vidayı çevirip 5,1 V'a getir (5,0–5,2 V). 5,2 V üstü Pi'ye zarar verebilir; ayarlanabilir "
                    "değilse bu modül uygun değildir: öğretmene haber ver.")
    if pdc is None:
        return False
    mp = ask_float("LiDAR REGÜLATÖRÜ (3 A buck) çıkışını 5,00 V yapacak şekilde ayarla. Ölçtüğün gerilim", 4.95, 5.10, "mp1584_V",
                   "LiDAR için 4,9–5,2 V gerekir; hedef 5,00 V. Vidayı çevirerek ayarla.")
    return mp is not None


def adim_onay(maddeler, soru_eki):
    """Her maddeyi TEK TEK onaylatır; biri 'hayır' ise False."""
    for m in maddeler:
        if not ask_yn(f"{m}\n   → {soru_eki}", None):
            say("Bu yapılmadan devam etmek GÜVENLİ DEĞİL. Yaptıktan sonra tekrar: arac", "r")
            return False
    return True


# ---------- A0) ROBOT ÖNCEDEN KOMPLE KABLOLANDIYSA ----------
def a_hazir_robot():
    baslik("HAZIR ROBOT — Güvenli ölçüm ve ayar")
    say("Robotu önce komple taktınız. Sorun değil; ama regülatörler AYARLANMADAN yüklere bağlıysa batarya\n"
        "takıldığında LiDAR'a ve motorlara 12 V'a kadar gerilim gidebilir. Şimdi birkaç kabloyu GEÇİCİ olarak\n"
        "çıkaracağız, regülatörleri ölçüp ayarlayacağız ve kabloları geri takacağız.", "y")

    say("\n--- 1) ÖNCE: Pi'nin 5 V pinleri ---", "b")
    say("Pi'nin pin 2 ve pin 4'ü 5 V'tur (pin 1'in hemen yanındaki, kart KENARINA yakın sıranın ilk iki pini).\n"
        "Bu projede pin 2 ve pin 4'e HİÇBİR kablo takılmaz. TB6612 VCC, enkoderler ve BNO055 3,3 V'a (pin 1, 17) gider.")
    if ask_yn("Pin 2 veya pin 4'e takılı bir kablo VAR mı?", "h"):
        say("HEMEN şalteri kapat ve Pi'nin güç kablosunu çek! O kablo 3,3 V pinine (pin 1 ya da 17) taşınmalı.\n"
            "Pi'ye 5 V'lu sinyal geldiyse GPIO'lar zarar görmüş olabilir: öğretmenine haber ver.", "r")
        return sorun("5 V pinine kablo takılı.")

    enerji = ask_yn("Robota daha önce batarya takılıp şalter AÇILDI mı? (bir kez bile)", "h")
    if ask_yn("Pi şu an ROBOTUN bataryasından mı çalışıyor? (USB-C kablosu robottaki Pi regülatöründen geliyor)", "h"):
        say("Ölçüm için Pi'nin robottan ayrılması gerekiyor. Pi'yi kapatacağım. Kapanınca (yeşil ışık söner, 10 sn):\n"
            "  1) Şalteri KAPAT, bataryayı ÇIKAR.\n"
            "  2) Pi'nin USB-C güç kablosunu çek. Pi regülatöründen gelen kablo havada kalsın, ucu metale değmesin.\n"
            "  3) Pi'yi KENDİ duvar adaptörüyle aç, SSH ile bağlan, yine:  arac\n"
            "  4) 'Robot zaten kablolandı mı?' sorusuna yine EVET de.", "y")
        if ask_yn("Anladın mı? Pi'yi ŞİMDİ kapatayım mı?") and not MOCK:
            subprocess.run(["sudo", "shutdown", "-h", "now"])
        return False

    say("\n--- 2) Gücü kes ---", "b")
    if not adim_onay(["Ana şalter KAPALI.", "Batarya robottan ÇIKARILDI."], "Tamam mı?"):
        return False

    say("\n--- 3) Bu kabloları ÇIKAR (geçici) ---", "b")
    say("Söktüğün her kablonun ucunu bantla ve etiketle; ucu hiçbir metale değmesin.", "y")
    cikar = [
        "✗ ÇIKAR: TB6612 VM kablosu — motor buck OUT+ ucundan sök (motorlara gidecek 6 V hattı).",
        "✗ ÇIKAR: LiDAR 5V kablosu — LiDAR regülatörünün OUT+ ucundan sök.",
        "✗ ÇIKAR: LiDAR USB kablosu — Pi'nin USB portundan çek.",
        "✗ ÇIKAR: Pi regülatörünün USB-C kablosu — Pi'ye TAKILI OLMAMALI (Pi şu an duvar adaptöründe).",
    ]
    if not adim_onay(cikar, "Çıkardın mı?"):
        return False
    say("\n--- Bunları ÇIKARMA (yerinde kalsın) ---", "g")
    say("   ✓ Bütün GND kabloları (batarya −, GND bara, regülatör IN−/OUT−, TB6612 GND, LiDAR GND,\n"
        "     enkoder ve BNO055 GND)\n"
        "   ✓ Regülatörlerin GİRİŞ kabloları (IN+ / IN−)\n"
        "   ✓ Pi'nin GPIO kabloları (TB6612, enkoderler, BNO055)\n"
        "   ✓ Motor kabloları (AO1/AO2, BO1/BO2)")
    if not ask_yn("Bunların hiçbirini sökmedin, hepsi yerinde mi?", "e"):
        return sorun("Söktüğün kabloyu 'arac kablo' tablosuna ve hardware/wiring/README.md'ye göre geri tak.")

    if not bip_testi("4) BİP TESTİ (kısa devre kontrolü)"):
        return False

    say("\n--- 5) Regülatörleri ÖLÇ ve AYARLA ---", "b")
    say("Bataryayı tak, şalteri aç. Pi duvar adaptöründe kalsın. Regülatör çıkışlarında artık YÜK YOK.")
    if not ask_yn("Batarya takıldı ve şalter açık mı?"):
        return False
    if olc_batarya() is None:
        return False
    say("\nÖnce vidalara DOKUNMADAN, şu anki (ayarlanmamış) değerleri ölç:", "b")
    hm = olc_ham("MOTOR BUCK çıkışı (OUT+ / OUT−), vidaya dokunmadan", "motor_regulator_ilk_V")
    hp = olc_ham("LiDAR regülatörü çıkışı (OUT+ / OUT−), vidaya dokunmadan", "mp1584_ilk_V")
    if enerji and hm > 6.5:
        say(f"⚠️  Motor buck {hm} V veriyordu ve robot daha önce açılmış: motorlar/TB6612 fazla gerilim görmüş olabilir.\n"
            "   Motor testinde (adım 2) ısınma, koku, ses farkı olursa durdur ve öğretmene bildir.", "r")
    if enerji and hp > 5.3:
        say(f"⚠️  LiDAR regülatörü {hp} V veriyordu ve robot daha önce açılmış: LiDAR fazla gerilim görmüş olabilir.\n"
            "   LiDAR'ı tekrar takmadan önce öğretmenine haber ver; LiDAR adımında 'Sağlık: İYİ' görmezsen kullanma.", "r")
    if not regulatorleri_ayarla():
        return False

    say("\n--- 6) Gücü kes ve kabloları GERİ TAK ---", "b")
    if not adim_onay(["Ana şalter KAPALI.", "Batarya ÇIKARILDI."], "Tamam mı?"):
        return False
    geri = [
        "↩ GERİ TAK: TB6612 VM kablosu → motor buck OUT+.",
        "↩ GERİ TAK: LiDAR 5V kablosu → LiDAR regülatörü OUT+.",
    ]
    if not adim_onay(geri, "Taktın mı?"):
        return False
    say("LiDAR USB kablosu ve Pi'nin USB-C kablosu SONRAKİ adımda takılacak; şimdi TAKMA.", "y")

    if not bip_testi("7) İkinci BİP TESTİ", "\nSonra aynısını TB6612 VM ile GND arasında, iki 5 V regülatörün OUT+ ile OUT− arasında da yap."):
        return False
    HAZIR.write_text("1")
    say("\nGüç tarafı güvenli ✓. Sıradaki adımda Pi kablolarını kontrol edeceğiz.", "g")
    return True


# ---------- A) ROBOT TARAFI: Pi'ye DOKUNMADAN ----------
def a_kablo_robot():
    say("\nRobotun kablolamasını bu programdan ÖNCE komple yaptınız mı? (şemaya bakıp her şeyi taktınız mı?)", "b")
    if ask_yn("Robot zaten TAMAMEN kablolandı mı?", "h"):
        return a_hazir_robot()
    HAZIR.unlink(missing_ok=True)
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
         "   3S LiPo (+)  →  SİGORTA (10 A)  →  ANA ŞALTER  →  GÜÇ DAĞITIM (+) klemensi\n"
         "   3S LiPo (−)  →  GÜÇ DAĞITIM GND klemensi (yıldız GND noktası)\n"
         "Bataryayı henüz TAKMA."),
        ("2) Üç regülatörün girişi",
         "Üç regülatörün GİRİŞİNİ (IN+ ve IN−) güç dağıtıma bağla:\n"
         "   MOTOR BUCK (6 V, 5 A)         : IN+ → dağıtım (+)    IN− → dağıtım GND\n"
         "   Pi REGÜLATÖRÜ (5,1 V, 3 A)    : IN+ → dağıtım (+)    IN− → dağıtım GND\n"
         "   LiDAR REGÜLATÖRÜ (5 V, 3 A)   : IN+ → dağıtım (+)    IN− → dağıtım GND\n"
         "İki 3 A regülatör birbirine benziyorsa ŞİMDİ etiketle (Pi / LiDAR): ayar gerilimleri farklı.\n"
         "ÇIKIŞ uçlarını henüz hiçbir şeye BAĞLAMA."),
    ]
    for t, m in adimlar:
        say(f"\n--- {t} ---", "b")
        say(m)
        if not ask_yn("Yaptın mı?", "e"):
            return False

    if not bip_testi("3) BİP TESTİ (kısa devre kontrolü)"):
        return False

    say("\n--- 4) Regülatörleri AYARLA (tek tek) ---", "b")
    say("Şimdi bataryayı tak ve şalteri aç. Regülatörlerin çıkışına hiçbir şey bağlı OLMASIN.")
    if not ask_yn("Batarya takıldı, şalter açık, çıkışlar boşta. Hazır mısın?"):
        return False
    if olc_batarya() is None or not regulatorleri_ayarla():
        return False
    say("\nŞimdi ŞALTERİ KAPAT ve bataryayı ÇIKAR.", "y")
    if not ask_yn("Şalter kapalı ve batarya çıkarıldı mı?"):
        return False

    adimlar = [
        ("5) Motor sürücü (tek TB6612FNG)",
         "   • VM   ← MOTOR BUCK OUT+ (6 V)\n"
         "   • VM'nin yanındaki GND ← MOTOR BUCK OUT−\n"
         "   • MOTOR BUCK OUT− ayrıca KALIN bir kabloyla yıldız GND noktasına gider\n"
         "     (motor akımı Pi'nin ince GND kablosundan dönmesin).\n"
         "   • VCC (lojik) şimdilik BOŞ: Pi tarafında pin 1'e (3,3 V) takılacak. VM'ye ASLA 3,3 V/5 V verme, VCC'ye ASLA 6 V verme."),
        ("6) Motorlar",
         "SOL motorun iki güç kablosu (M+ / M−) → TB6612 AO1 ve AO2 (hangisi hangisi önemli değil, yazılım düzeltir)\n"
         "SAĞ motorun iki güç kablosu (M+ / M−) → TB6612 BO1 ve BO2\n"
         "Kablo uçlarının klemensde sıkı durduğunu hafifçe çekerek dene."),
        ("7) LiDAR gücü",
         "LiDAR regülatörü OUT+ → LiDAR 5V    LiDAR regülatörü OUT− → LiDAR GND\n"
         "LiDAR'ın veri hattı USB adaptörüne gider. Adaptörün USB 5 V'u LiDAR'ın 5 V'una AYRICA bağlıysa\n"
         "iki kaynak paralel olur: öğretmenine sor (adaptörün harici güç girişi/jumper'ı kullanılmalı).\n"
         "USB kablosunu şimdilik adaptöre TAKMA (Pi'ye sonra takılacak)."),
        ("8) Pi regülatörü çıkış kablosu (USB-C)",
         "Pi regülatörünün çıkışı vidalı uçtur; Pi'ye USB-C GÜÇ kablosuyla (bir ucu USB-C erkek, diğer ucu açık\n"
         "kırmızı/siyah tel) bağlanır:  OUT+ → kırmızı tel (VBUS, 5 V)    OUT− → siyah tel (GND).\n"
         "Kutbu multimetreyle doğrula; USB-C ucunu şimdilik havada bırak (Pi'ye takma!).\n"
         "Pi'nin 5 V pinlerine (pin 2, 4) ASLA kablo takılmaz: Pi yalnızca USB-C girişinden beslenir.\n"
         "OUT− (GND) yıldız GND noktasına da bağlanır."),
        ("9) Enkoder kabloları (motor tarafı)",
         "İki N20 enkoderin kablolarını (VCC, GND, ENC A, ENC B) Pi tarafına gelecek uzunlukta bırak ve etiketle\n"
         "(SOL-VCC, SOL-GND, SOL-A, SOL-B, SAĞ-... ). Pi'ye takmayacağız, sadece etiketle.\n"
         "Motor kabloları ile enkoder kabloları mümkünse AYRI demetlerde ilerlesin (gürültü olmasın)."),
    ]
    for t, m in adimlar:
        say(f"\n--- {t} ---", "b")
        say(m)
        if not ask_yn("Yaptın mı?", "e"):
            return False

    say("\n--- 10) İkinci BİP TESTİ ---", "b")
    say("Bataryasız, multimetre BİP konumunda: GÜÇ DAĞITIM (+) ile GND arası ve TB6612'nin VM'si ile GND'si arası.")
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
    for side, ad, k in (("left", "SOL", "A"), ("right", "SAĞ", "B")):
        m = p["motors"][side]
        rows += [(f"TB6612 PWM{k}  ({ad} motor)", BCM2PIN[m["pwm"]]), (f"TB6612 {k}IN1  ({ad} motor)", BCM2PIN[m["in1"]]),
                 (f"TB6612 {k}IN2  ({ad} motor)", BCM2PIN[m["in2"]])]
    rows += [("TB6612 STBY", BCM2PIN[p["driver"]["stby"]]), ("TB6612 VCC (lojik 3,3 V)", 1), ("TB6612 GND (lojik)", 6)]
    for side, ad in (("left", "SOL"), ("right", "SAĞ")):
        n = p["encoders"][side]
        rows += [(f"{ad} ENKODER A", BCM2PIN[n["a"]]), (f"{ad} ENKODER B", BCM2PIN[n["b"]])]
    rows += [("BNO055 SDA", 3), ("BNO055 SCL", 5),
             ("3,3 V lojik hattı (iki enkoder VCC + BNO055 VIN)", 17),
             ("GND lojik hattı (iki enkoder GND + BNO055 GND)", 14)]
    if p.get("start_button"):
        rows += [("BAŞLAT BUTONU (bir ayağı)", BCM2PIN[p["start_button"]["gpio"]]),
                 ("BAŞLAT BUTONU (diğer ayağı, GND)", 34)]
    for ad, pin in rows:
        say(f"   {ad:<44} →  Pi fiziksel pin {pin}")
    say("\nBu tablo bir daha lazım olursa:  arac kablo", "b")
    hazir = HAZIR.exists()
    if hazir:
        say("\nKablolar zaten takılı. Tablodaki HER satırı bir arkadaşınla kontrol et: biri satırı okur,\n"
            "diğeri kabloyu iki ucuna kadar takip edip pin numarasını sayar. Yanlış olan kabloyu Pi KAPALIYKEN düzelt.", "y")
        say("Özellikle: sağ motor BIN1/BIN2 = pin 38/40, sağ enkoder A/B = pin 16/18, STBY = pin 37.", "y")
    else:
        say("\nSıra: ÖNCE GND pinleri, SONRA sinyal kabloları, EN SON güç kabloları (3,3 V) takılır.", "y")
    if not ask_yn("Tabloyu inceledin ve fotoğrafını çektin / ekranı açık bıraktın mı? Pi'yi şimdi kapatacağız."):
        return False
    say("\nPi kapanacak. Kapanınca (yeşil ışık söner, 10 sn bekle) şunları yap:", "y")
    say("  1) Pi'nin DUVAR ŞARJ ADAPTÖRÜNÜ ÇEK. (Pi'ye aynı anda İKİ güç kaynağı bağlanmaz!)\n"
        + ("  2) Yukarıdaki tabloya göre kontrol ettiğin YANLIŞ kabloları düzelt (önce GND, sonra sinyal, en son 3,3 V).\n"
           if hazir else
           "  2) Yukarıdaki pin tablosuna göre kabloları tak (önce GND, sonra sinyal, en son 3,3 V).\n")
        + "  3) LiDAR USB kablosunu Pi'nin USB portuna tak (LiDAR kendi regülatöründen beslenir, USB sadece veri).\n"
        "  4) Pi regülatörünün USB-C kablosunu Pi'nin güç girişine tak.\n"
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
        return sorun("Güç yetersiz (throttled ≠ 0x0): Pi regülatörü çıkışı (yükte ≥ 5,0 V), USB-C kablosu, bağlantıları "
                     "kontrol et; 'arac acil' → B1. 3 A regülatör ısınıp gerilim düşürüyorsa 5 A'lik bir regülatör gerekir.")
    say("   ✓ Güç sağlıklı", "g")
    otomatik_kontrol()
    HAZIR.unlink(missing_ok=True)
    return True


def otomatik_kontrol():
    """Pi'nin kendisinin görebildiği bağlantılar. Sorun = uyarı (sonraki adımlar ayrıntılı test eder)."""
    say("\nOtomatik donanım kontrolü:", "b")
    p = pins()
    port = Path(p["lidar"]["port"])
    if port.exists():
        say(f"   ✓ LiDAR USB adaptörü görünüyor ({port})", "g")
    else:
        say(f"   ! LiDAR USB adaptörü görünmüyor ({port} yok): USB kablosu Pi'ye takılı mı? (LiDAR adımında tekrar bakılacak)", "y")
    imu = p.get("imu")
    if imu:
        try:
            out = subprocess.run(["i2cdetect", "-y", str(imu["i2c_bus"])], capture_output=True, text=True,
                                 timeout=10).stdout
            adr = f"{int(imu['address']):02x}"
            if any(adr in ln.split()[1:] for ln in out.splitlines()[1:]):
                say(f"   ✓ BNO055 I2C'de görünüyor (0x{adr})", "g")
            else:
                say(f"   ! BNO055 görünmüyor (0x{adr}): SDA pin 3, SCL pin 5, VIN 3,3 V, GND kontrol et. "
                    "(Devam edilebilir: BNO055 yoksa dönüş açısı enkoderden hesaplanır.)", "y")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            say("   ! i2cdetect çalışmadı (i2c-tools kurulu mu? I2C açık mı?), BNO055 atlandı", "y")


def tablo_goster():
    baslik_tablosu()
