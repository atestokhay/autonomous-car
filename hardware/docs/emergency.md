# Acil Durum ve Sıralı Arıza Teşhis Rehberi

Bu dosya iki bölümden oluşur:
- **BÖLÜM A — Acil durum (tehlike):** duman, koku, ısınma, şişmiş batarya, kontrol kaybı.
- **BÖLÜM B — "Çalışmıyor" (güvenli arıza):** kod/robot beklendiği gibi çalışmıyor. **Sırayla** kontrol et; atlama.

> Bölüm B'de her adım bir öncekinin doğru olduğunu varsayar. Bir adımda sorun bulursan **orada dur**, düzelt,
> o adımı tekrar test et, sonra devam et.

---

# BÖLÜM A — ACİL DURUM

## A0. Altın kurallar
1. **Önce güç.** Şüphe varsa ana şalteri kapat. Sonra düşün.
2. Batarya takılıyken kablolara/devreye çıplak elle dokunma, devre üzerinde ölçüm yaparken uç atlatma.
3. LiPo yangınına **su atma**. Küçük yangında kum/yangın battaniyesi/kuru toz söndürücü; büyükse uzaklaş, 112'yi ara.
4. Test sırasında tekerlekler yerden kesikken bile aracı sahipsiz bırakma.
5. Hiçbir arıza "bir kere daha deneyince geçer" diye tekrar denenmez; önce nedeni bul.

## A1. Belirtiye göre ilk 30 saniye

| Belirti | Hemen yap | Sonra |
|---|---|---|
| **Duman, yanık/plastik kokusu, kıvılcım** | Ana şalteri kapat → bataryanın fişini çek (eldiven/kuru bez, hızlı değil sakin) → aracı açık ve yanıcı olmayan zemine al | A2 |
| **Batarya şişmiş, ısınıyor, çok sıcak** | Aracı kullanma/şarj etme. Bataryayı metal veya seramik kapta, yanıcılardan uzakta, açık havada bırak | A3 |
| **Araç kontrolsüz gidiyor / durmuyor** | Ana şalteri kapat (yazılımı durdurmaya çalışma) | A4 |
| **Motor veya L298N dokunamayacak kadar sıcak** | Şalteri kapat, 10 dk soğut | A5 |
| **Pi kapanıyor / yeniden başlıyor** | Motorları durdur, şalteri kapat | B1 |
| **Sigorta attı** | Şalteri kapat. Sigortayı **aynı değerle** değiştirmeden önce nedeni bul (kısa devre?) | A6 |
| **Elektrik çarpması hissi / kablo erimesi** | Şalteri kapat, bataryayı çıkar | A2 |

## A2. Duman / yanık kokusu sonrası inceleme
1. Batarya çıkarılmış olarak, hangi parçanın koktuğunu/rengi değiştiğini bul (L298N, regülatör, kablo, konnektör).
2. Yanmış/erimiş parça **tekrar kullanılmaz**; yenisiyle değişir.
3. Neden bulunmadan yeni parça takılmaz: kısa devre, ters polarite, fazla gerilim, ince kablo, gevşek klemens.
4. Kontrol: ters polarite var mı? Motor besleme regülatörü gerçekten 12 V mu (A6'daki ölçümlerle)? 
5. Öğretmene **fotoğraf** gönder (yanan parça, kablo bağlantıları).

## A3. LiPo batarya güvenliği
- Şişme, ısınma, hasarlı (ezik/yırtık) kılıf = **kullanılamaz**. Bu bataryayı tekrar kullanma; pil atık noktasına götür.
- Hücre gerilimi: dolu 4,2 V/hücre (toplam 16,8 V). **Asla 3,3 V/hücre (13,2 V toplam) altına indirme.**
- Bu araçta 12 V motor regülatörü bataryanın 12 V'un üstünde kalmasına ihtiyaç duyar: toplam gerilim
  **14,0 V (3,5 V/hücre)** altına inince çalışmayı bırak, şarj et. (Hücre alarmı/gerilim göstergesi kullanman önerilir.)
- LiPo'yu yalnızca LiPo dengeli şarj cihazıyla, gözetimde, yanmaz zeminde şarj et.
- Uzun süre kullanılmayacaksa depolama gerilimine (≈3,8 V/hücre) getir.

## A4. Araç kontrolsüz giderse (bir sonraki girişten önce)
Güç kesildikten sonra, **tekerlekler havada**, şu sırayla bak:
1. Kablo: ENA/PWM, IN1, IN2 kabloları doğru pinde mi (`hardware/wiring/netlist.txt`)? Bir IN kablosu GND/3,3 V'a temas ediyor mu?
2. Enkoder: ters yönde mi sayıyor? (Hız kontrolü ters geri besleme alırsa motor tam hıza kaçar.) `python3 stages/03-enkoder/run.py watch`
3. Yazılımın güvenlik düzeni: komut kesilince 0,5 sn'de durur; tam güçte hız alınamazsa 0,5 sn'de durdurur
   (runaway koruması). Bunlar **tetiklenmediyse** mesajı/çıktıyı kaydet ve öğretmene gönder; aracı bir daha yerde çalıştırma.
4. Acil durdurma için **elin her zaman şalterde** olsun.

## A5. Isınma
- L298N hafif ısınır (50–70 °C normal olabilir) ama parmağınla 2 sn tutamıyorsan fazla sıcaktır.
- Nedenleri: motor kilitli/tekerlek sıkışık, sürekli yüksek duty, düşük kaliteli kablo/gevşek klemens (dirence bağlı ısınma),
  sürücü kartı soğutucusuz/küçük, besleme gerilimi yüksek.
- Çözüm: duty düşür, kilitli motoru bul, klemensleri sık, sürücüyü havalandır. Ana akım yolunu ölç.
- Regülatör ısınıyorsa akım kapasitesini aşıyor olabilir: daha büyük regülatör gerekir.

## A6. Sigorta / ölçüm doğrulaması (şalter kapalıyken başla)
1. Batarya çıkarılmış: multimetre ile **süreklilik (bip) modu**: güç dağıtım (+) ile GND arası **bip OLMAMALI** (kısa devre).
2. Bataryayı tak, şalter açık, motorlar boşta (tekerlek havada):
   - Batarya: ≈ 14,0–16,8 V
   - Motor regülatörü çıkışı: **≈ 12,0 V** (12,5 V üstü olmamalı; L298N sonrası motor terminalinde ≈ 10 V normal)
   - Pi regülatörü çıkışı: **5,0–5,2 V**
   - MP1584EN çıkışı: **4,9–5,2 V** (hedef 5,00), LiDAR bağlanmadan ve bağlıyken yeniden ölç
3. Sigorta öneri aralığı: bu sistem için **7,5–10 A** otomotiv/DC sigorta. (Motor regülatörü ve L298N'in kendi akım
   sınırlarına göre öğretmeninle doğrula; sigorta, en zayıf kablo/regülatörden küçük olmalı.)

---

# BÖLÜM B — "ÇALIŞMIYOR": SIRALI KONTROL

Her bölümün sonunda **"Geçti"** koşulu var. Geçmeden bir sonrakine gitme.
Komutlar `software/` klasöründedir: `cd ~/autonomous-car/software`.

## B0. Hemen yap: teşhis raporu al (motor hareket etmez)
```bash
cd ~/autonomous-car/software
python3 tools/diag.py
```
`diag_rapor.txt` oluşur. Sorunu anlatmadan önce bunu al; çoğu sorunu tek bakışta gösterir.
Aşağıdaki adımlarda bu rapordaki satırlara atıf yapılır.

## B1. Güç
**Belirti:** Pi kapanıyor, motor çalışınca resetliyor, LiDAR dönmüyor.
1. Bataryayı ölç (≥ 14,0 V). Düşükse şarj et. (Bu en sık neden.)
2. Şalter + sigorta çıkışında gerilim var mı?
3. Motor regülatörü 12 V, Pi regülatörü 5,0–5,2 V, MP1584EN 4,9–5,2 V (A6).
4. Motorlar çalışırken yeniden ölç: Pi 5 V hattı **düşüyor mu?** Düşüyorsa kablo ince/gevşek, ortak GND kötü, ya da regülatör akım yetmiyor.
5. `vcgencmd get_throttled` → `0x0`. Değilse güç sorunu var (`dmesg | grep -i under`).
6. Ortak GND: Pi GND ↔ her iki L298N GND ↔ MP1584EN GND ↔ enkoder GND arasında süreklilik (bip).

**Geçti:** Motorlar yüklüyken Pi resetlenmiyor, `get_throttled` = `0x0`.

## B2. Pi açılıyor mu, bağlanabiliyor musun?
1. Pi'de yeşil LED yanıp sönüyor mu? Hiç yanmıyorsa güç (B1).
2. Ağ: Wi-Fi şifresi doğru mu? Aynı ağda mı? `ping <pi-adresi>`; `ssh kullanici@<pi-adresi>`
3. Ekran + klavye ile bağlan, `ip a` ile adresi bul.
4. SD kart: Imager ile Ubuntu 24.04'ü yeniden yaz (verileri kaybedersin; önce kodu yedekle).

**Geçti:** SSH ile bağlanıyorsun.

## B3. Yazılım kurulumu
```bash
python3 --version                  # 3.12 civarı
python3 -m unittest discover -s tests     # OK olmalı
```
- `ModuleNotFoundError` → `notes/kurulum-ubuntu-ros.md` §2'yi tekrar çalıştır (`yaml`, `numpy`, `serial`, `lgpio`).
- Testler `FAIL` → hata satırını gönder. **Robota bağlı bir şey denenmez.**
- ROS komutu yok → `source /opt/ros/jazzy/setup.bash` (ve `source ~/ros2_ws/install/setup.bash`).

**Geçti:** testler `OK`.

## B4. GPIO erişimi
```bash
gpiodetect                          # pinctrl-rp1 görünmeli
ls -l /dev/gpiochip*                # grup gpio, mod crw-rw----
id                                  # gpio ve dialout grubunda mısın
```
- `Permission denied` → `notes/kurulum-ubuntu-ros.md` §2 (udev kuralı + grup), **çıkış yapıp gir**.
- `gpiodetect` yok → `sudo apt install gpiod`.
- `lgpio` import hatası → `sudo apt install python3-lgpio`.
- Başka bir program GPIO'yu tutuyor olabilir: `python3` süreçleri kapat (`pkill -f stages/`), `sudo reboot`.

**Geçti:** `python3 stages/02-motor/run.py --help` hatasız açılıyor.

## B5. Motor (tekerlekler HAVADA)
`python3 stages/02-motor/run.py --side left --duty 0.3`
| Belirti | Sırayla bak |
|---|---|
| Hiçbiri dönmüyor | 1) Motor regülatörü 12 V çıkışı var mı  2) L298N'e +12 V ve GND geliyor mu (L298N üzerindeki güç LED'i)  3) ENA jumper'ı **çıkarılmış** mı ve ENA'ya Pi PWM pini bağlı mı  4) IN1/IN2 pinleri doğru mu  5) motor kabloları OUT1/OUT2'de mi |
| Biri dönmüyor | O tarafın bütün zinciri: Pi pini → L298N → motor. Diğer sürücüyle yer değiştirip nerede kaldığını bul. Motor terminalinde gerilim ölç (≈ 8–10 V tam duty'de) |
| Yalnız yüksek duty'de dönüyor | Normal (ölü bölge). Düşük batarya da yapar. |
| Ters dönüyor | `config/pins.yaml` → `invert` çevir |
| Titriyor ama dönmüyor | Besleme çöküyor (batarya/regülatör), ya da motor mekanik kilitli |
| L298N LED'i yanmıyor | 5V-EN jumper'ı takılı mı, besleme geliyor mu |
| Hep tam hız | PWM pini yanlış / ENA jumper'ı hâlâ takılı (ENA +5 V'a bağlı kalır) |

**Geçti:** iki tekerlek ileri ve geri doğru yönde dönüyor, komut bitince duruyor.

## B6. Enkoder (tekerlekler HAVADA)
`python3 stages/03-enkoder/run.py watch` — tekerleği elle ileri çevir.
| Belirti | Sırayla bak |
|---|---|
| Sayı hiç değişmiyor | 1) Enkoder VCC **Pi 3,3 V**'a mı bağlı (5 V değil!)  2) GND  3) A/B kabloları doğru pine mi  4) Multimetre: tekerlek dönerken A ve B pinlerinde gerilim 0 ↔ 3,3 V arası değişiyor mu |
| Yalnız bir kanal değişiyor | A veya B kablosu kopuk/yanlış pin |
| Sayı geri sayıyor | `pins.yaml` → o enkoderin `invert` değeri |
| Sayı sıçrıyor / gürültülü | Sinyal kabloları motor/güç kablosuyla yan yana: ayır, kısalt, GND'yi kontrol et |
| Tur başına tick ≠ 392 | `calibrate` ile ölç, çıkan değeri `robot.yaml`'a yaz |
| Pi'yi güçlü hissediyor / reset | Enkoder 5 V ile besleniyor ve Pi pinine 5 V sinyal geliyor olabilir: **hemen sök, 3,3 V'a geç, seviye dönüştürücü kullan** |

**Geçti:** iki enkoder ileri yönde artıyor, tur başına tutarlı.

## B7. PID (tekerlekler HAVADA)
`python3 stages/04-pid/autotune.py`
| Belirti | Sırayla bak |
|---|---|
| "hız NEGATİF" | Enkoder `invert` (B6) |
| Motor tam gaza çıkıp duruyor ("runaway") | Enkoder bağlı/yön doğru mu; tekerlek sıkışık mı; bu bir **güvenlik korumasıdır**, ayar sorunu değil |
| Autotune GEÇMEDİ | Batarya düşük mü, kablo gevşek mi; yeniden dene; hâlâ olursa raporu gönder |
| Salınım / titreme | `config/tuned.yaml` sil, autotune'u yeniden çalıştır; olmadı `pid.yaml` `kp`'yi yarıya indir |
| Sol-sağ hız farklı | Beklenir; `run.py` adım testinde ±%3 içinde olmalı |

**Geçti:** autotune iki tekerlekte GEÇTİ, adım testi uyumlu.

## B8. LiDAR
`python3 stages/05-lidar/check_lidar.py`
| Belirti | Sırayla bak |
|---|---|
| Seri aygıt yok (`/dev/ttyUSB0`) | 1) USB kablosu **veri** kablosu mu (sadece şarj kablosu olmasın)  2) adaptör takılı  3) `lsusb`, `dmesg \| tail`  4) port numarası farklı olabilir (`ttyUSB1`) |
| Permission denied | `dialout` grubu (B4), çıkış-giriş |
| LiDAR dönmüyor | 1) MP1584EN çıkışı 4,9–5,2 V ve **yük altında** düşmüyor  2) adaptörün harici güç girişi doğru kutupta  3) USB VBUS ile harici 5 V **paralel değil** |
| Cevap yok | Baud 1 000 000 (S3); başka adaptör modu (sw1 ayarı varsa) ; kablo |
| Sağlık HATA | Gücü kes-ver, lens temiz mi, motor engelsiz mi |
| ROS'ta `/scan` yok | `ros2 topic list`, `ros2 pkg executables sllidar_ros2` (sllidar_node var mı), `source ~/ros2_ws/install/setup.bash` |
| Yön yanlış / ayna | `robot.yaml` → `lidar_yaw_deg`, `lidar_inverted` |

**Geçti:** `Sağlık: İYİ`, `/scan` ≈ 10 Hz, yön testi doğru.

## B9. Odometri ve sürüş (aşama 6)
| Belirti | Sırayla bak |
|---|---|
| Hareket etmiyor | `ros2 topic echo /cmd_vel` komut geliyor mu; drive düğümü hata veriyor mu |
| Komutu bırakınca durmuyor | **Şalter.** Sonra B7 (PID) ve düğüm çıktısını gönder; bu hata olmamalı |
| Mesafe yanlış | `calibrate.py radius`; `ticks_per_rev`, tekerlek yarıçapı |
| Dönüş açısı yanlış | `calibrate.py base`; tekerlekler arası mesafe |
| Düz gitmiyor | Sol/sağ hız (B7), tekerlek çapı farkı, zemin |

## B10. Duvar takibi (aşama 7)
Önce robotsuz: `python3 stages/07-duvar-takibi/sim_demo.py --world oda --side right` → "ÇARPMA YOK".
Robotla bozuksa sırayla: LiDAR yönü (B8) → PID (B7) → odometri (B9) → `v_scale` 0,3 ile tekrar →
`notes/sorun-giderme.md` aşama 7 tablosu. Hemen ESTOP oluyorsa `robot_radius_m` ve LiDAR'ın kendi gövdesini görüp görmediğine bak.

## B11. "Donanım mı yazılım mı?" ayırma testi
| Test | Sonuç | Anlamı |
|---|---|---|
| `python3 -m unittest discover -s tests` | OK | Yazılım kurulumu sağlam |
| `python3 stages/04-pid/autotune.py --mock` | GEÇTİ | PID mantığı sağlam (donanımsız) |
| `python3 stages/07-duvar-takibi/sim_demo.py` | ÇARPMA YOK | Duvar takibi mantığı sağlam |
| Multimetre ile gerilimler (A6) | Doğru | Güç sağlam |
| `watch` / `check_lidar.py` | Veri var | Sensör ve kablolar sağlam |
Yazılım testleri geçip donanım testleri geçmiyorsa **sorun donanım/kabloda**; tersi ise yazılım/yapılandırmada.

## B12. Öğretmene ne gönderilir
1. `diag_rapor.txt` (B0)
2. Hangi aşama / hangi komut / ekrandaki **tam** hata çıktısı
3. Fotoğraf: kablolama (yakından, etiketli), güç kısmı
4. Ölçtüğün gerilimler (batarya, motor regülatörü, Pi 5 V, MP1584EN 5 V)
5. Son değiştirdiğin şey (ayar, kablo, parça)

## B13. Geri alma (hiçbir şey çalışmıyorsa)
- Kendi ayarlarını sıfırla: `rm config/tuned.yaml config/robot_cal.yaml` (varsayılana döner), sonra aşama 4 ve 6'yı yeniden yap.
- Kodu temiz kopyala: `git status` ile neyi değiştirdiğine bak; `git stash` ile sakla, `git pull`.
- Pi'yi sıfırla: yeni SD kartla `notes/kurulum-ubuntu-ros.md`.
