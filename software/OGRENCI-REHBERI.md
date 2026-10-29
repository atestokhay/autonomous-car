# Öğrenci Rehberi — Otonom Araç Yazılımı (adım adım)

Bu rehber, daha önce hiç terminal kullanmamış biri için yazıldı. Acele etme: **her adımı bitirip kutuyu işaretlemeden bir sonrakine geçme.**
Takılırsan bu normal. Mühendisler zamanlarının yarısını hata arayarak geçirir. Takılınca ne yapacağın en sonda ("Takılırsan").

---

## 0. Önce şunları bil

### 0.1 Neyi yapıyoruz?
Aracın bir **beyni** (Raspberry Pi), **gözü** (LiDAR), **bacakları** (motorlar) ve **adım sayarı** (enkoder) var.
Yazılım bunları sırayla öğretir:
1. Beyin çalışıyor mu? → 2. Bacaklar doğru yöne dönüyor mu? → 3. Adım sayar doğru sayıyor mu? →
4. Bacaklar istenen hızda dönüyor mu? (PID) → 5. Göz görüyor mu? → 6. Araç ne kadar yol gittiğini biliyor mu? →
7. Duvarı takip edebiliyor mu? → 8. (Ek) Harita çıkarabiliyor mu?

Bir basamağı atlarsan sonrakinde neyin bozuk olduğunu bulamazsın. Merdiven gibi: sırayla.

### 0.2 Terminal nedir?
Bilgisayara **yazıyla emir** verdiğin siyah ekran. Aşağıdaki gri kutulardaki komutları **kopyala-yapıştır** yap, sonra **Enter**'a bas.
- Yapıştırma: terminalde genelde `Ctrl+Shift+V`.
- Çalışan bir şeyi durdurma: `Ctrl+C` (en önemli tuş, aklında olsun).
- Önceki komutu tekrar getirme: ↑ tuşu.
- Büyük/küçük harf ve boşluk önemlidir. Kopyalarken eksik kalmasın.

### 0.3 Sadece 5 komut bilmen yeterli
| Komut | Anlamı |
|---|---|
| `cd klasör` | Klasörün içine gir |
| `ls` | Bulunduğum klasörde ne var? |
| `pwd` | Neredeyim? |
| `nano dosya.yaml` | Dosyayı aç ve düzenle (Kaydet: `Ctrl+O`, Enter; çık: `Ctrl+X`) |
| `cat dosya.yaml` | Dosyanın içini ekrana yaz (sadece oku) |

**Hep yazılım klasöründe çalış:**
```bash
cd ~/autonomous-car/software
```
(Yolunu şaşırırsan bu komut seni geri getirir.)

### 0.4 GitHub'ı kullanma (sadece bunlar, başka şey yok)
- İndirmek (bir kez): `git clone <öğretmenin verdiği adres>`
- Güncelleme gelirse: `cd ~/autonomous-car && git pull`
- **Branch (dal) açma, birleştirme, push yapma YOK.** Dosyaları yerelde değiştirmen normal (ayar dosyaları).
  `git pull` "değişiklik çakışıyor" derse dur, ekranı öğretmene gönder.

### 0.5 Menü: uzun komutları ezberleme
Çoğu adımı tek menüyle çalıştırabilirsin:
```bash
cd ~/autonomous-car/software
python3 menu.py
```
Numara seçersin, menü gerekli komutu çalıştırır ve güvenlik sorusunu sorar. Komutların nasıl çalıştığını görmek istersen aşağıda hepsi yazılı.

### 0.6 Güvenlik: 5 kural (pazarlık yok)
1. **Motor testlerinde tekerlekler havada.** Araç sağlam bir sehpa/kutu üzerinde.
2. **Elin güç şalterinde.** Şüphelenirsen şalteri kapat, sonra düşün.
3. **Duman, yanık kokusu, aşırı sıcak = şalter + dur.** Sonra `hardware/docs/emergency.md` bölüm A.
4. **Ctrl+C her zaman programı durdurur.** Motorlar durur.
5. Ölçü aleti (multimetre) olmadan "sanırım doğrudur" deme. Ölç, **sayıyı yaz**.

### 0.7 Laboratuvar defteri
`hardware/docs/test_sheet.md` senin defterin. Her adımda **ölçtüğün sayıyı** yaz ("iyi" değil "5,02 V").
Sorun olursa bu sayfa seni kurtarır. Öğretmenine fotoğraf gönderirken bu sayfayı da ekle.

---

## ADIM 1 — Yazılımı kur ve test et
**Hedef:** Pi'de her şey kurulu ve program kendini kontrol edebiliyor.
**Neden:** Daha motoru çalıştırmadan, yazılımın bozuk olup olmadığını anlarız. Böylece sonraki hata kesin "donanımdır".

1. SD karta **Ubuntu Server 24.04 LTS (64-bit)** yazıldıktan ve Pi internete bağlandıktan sonra, Pi'de şu **tek komutu** çalıştır (20–40 dk sürer, pencereyi ve interneti kapatma):
   ```bash
   sudo apt-get install -y git && git clone https://github.com/atestokhay/autonomous-car.git && bash autonomous-car/kurulum.sh
   ```
   Bitince ekranda `KURULUM TAMAMLANDI ✓` yazar. Sonra `sudo reboot` yap. Hata çıkarsa aynı `bash autonomous-car/kurulum.sh` komutunu tekrar çalıştır (kaldığı yerden devam eder); yine olmazsa `~/kurulum_log.txt` dosyasını öğretmene gönder.
   (Elle kurulum adımları yedek olarak `notes/kurulum-ubuntu-ros.md` içinde.)
2. Testi çalıştır (motor HAREKET ETMEZ):
   ```bash
   cd ~/autonomous-car/software
   python3 -m unittest discover -s tests
   ```
3. **Ne görmelisin?** Son satırlarda `Ran 46 tests ... OK`.
4. **Görmezsen:** `FAILED` ya da `ModuleNotFoundError` yazıyorsa kurulum eksiktir. Ekranı kopyala, `python3 tools/diag.py` çalıştır, `diag_rapor.txt`'yi öğretmene gönder.
5. Güç kontrolü:
   ```bash
   vcgencmd get_throttled
   ```
   **Ne görmelisin?** `throttled=0x0`. Başka sayı = güç sorunu → `hardware/docs/emergency.md` B1.

- [ ] Testler `OK`  - [ ] `throttled=0x0`  - [ ] Değerleri deftere yazdım

---

## ADIM 2 — Motorlar doğru yöne dönüyor mu?
**Hedef:** "İleri" deyince iki tekerlek de aracın ileri yönünde döner.
**Neden:** Sağ motor ters monte edildiği için kablolar aynı olsa bile bir tekerlek geri dönebilir. Bunu yazılımda tek satırla düzeltiriz (kablo sökmeden).
**Güvenlik:** Tekerlekler havada. Elin şalterde.

1. Menüden `2` (sol), sonra `3` (sağ). Ya da:
   ```bash
   python3 stages/02-motor/run.py --side left --duty 0.3
   python3 stages/02-motor/run.py --side right --duty 0.3
   ```
2. Program "İLERİ" der ve Enter bekler. Enter'a bas ve **tekerleğin hangi yöne döndüğüne bak**. Araç ileri giderken tekerleğin üst kısmı öne doğru hareket eder.
3. **Ters dönüyorsa:** `config/pins.yaml` dosyasını aç (`nano config/pins.yaml`), o motorun satırındaki `invert: false` yazısını `invert: true` yap (ya da tersini). Kaydet (`Ctrl+O`, Enter, `Ctrl+X`). Testi tekrarla.
4. **Hiç dönmüyorsa:** `hardware/docs/emergency.md` → B5 tablosu (sırayla bak).

- [ ] Sol ileri ✓ geri ✓  - [ ] Sağ ileri ✓ geri ✓  - [ ] Komutu bitirince motor duruyor

---

## ADIM 3 — Enkoder doğru sayıyor mu?
**Hedef:** Tekerlek ileri dönünce sayı **artıyor**; tam tur = yaklaşık 392 sayım.
**Neden:** Enkoder aracın "kilometre sayacı". Yanlış sayarsa sonraki her şey yanlış olur.
**Önce güvenlik:** Enkoder gücü Pi'nin **3,3 V** pininden gelmeli, 5 V'tan değil.

1. İzleme (tekerleği **elinle** ileri çevir):
   ```bash
   python3 stages/03-enkoder/run.py watch
   ```
   Durdurmak: `Ctrl+C`.
2. **Ne görmelisin?** İleri çevirince sayı artıyor. Geri çevirince azalıyor.
3. **Sayı azalıyorsa** (ileri çevirirken): `config/pins.yaml` → `encoders` bölümünde o tarafın `invert` değerini çevir.
4. **Hiç değişmiyorsa:** `hardware/docs/emergency.md` → B6.
5. Tur ölçümü (menü `5` ve `6`): tekerleği programın söylediği kadar tur çevir, sonuç yaklaşık **392** olmalı. Çok farklıysa sonucu `config/robot.yaml` → `ticks_per_rev` satırına yaz.
6. Motorlu test (tekerlekler havada):
   ```bash
   python3 stages/03-enkoder/run.py drive --duty 0.5 --seconds 5
   ```
   **Ne görmelisin?** `eksik` sayacı 0 kalır; devir yaklaşık 300–400 rpm.

- [ ] İki enkoder ileri yönde artıyor  - [ ] Tur başına sayı (sol/sağ) deftere yazıldı  - [ ] `eksik` = 0

---

## ADIM 4 — PID: tekerlekler istediğimiz hızda dönsün
**Hedef:** "Saniyede 10 radyan dön" denince tekerlek gerçekten o hızda döner, sallanmaz.
**Neden (benzetme):** Araba kullanırken hız göstergesine bakıp gaza az/çok basarsın. PID, bilgisayarın bunu saniyede 100 kere yapmasıdır.
- **P**: Hız hedefin çok altındaysa çok bas.
- **I**: Hep biraz eksik kalıyorsan yavaş yavaş biraz daha bas.
- **D**: Hızla değişiyorsa frenle.
Bu değerleri normalde elle ayarlamak zordur; **program kendi kendine bulur (autotune).** Sen sadece çalıştırırsın.
**Güvenlik:** Tekerlekler havada. Elin şalterde. Tekerlekler birdenbire hızlı dönecek, parmak/kablo yaklaştırma.

1. Menüden `7` ya da:
   ```bash
   python3 stages/04-pid/autotune.py
   ```
2. Program yaklaşık birkaç dakika çalışır. Önce motoru farklı güçlerde döndürür, sonra ayar hesaplar, sonra kendi bulduğunu dener.
3. **Ne görmelisin?** Her iki tekerlek için `GEÇTİ`. Sonuç `config/tuned.yaml` dosyasına yazılır.
4. **GEÇMEDİ derse:** Hata mesajı ne yapacağını söyler. En sık neden: batarya düşük (14,0 V altı) → şarj et, tekrar dene.
5. Doğrulama: `python3 stages/04-pid/run.py --side both --targets 0,10,20,10,0` — iki tekerlek aynı hıza benzer ulaşmalı.

- [ ] İki tekerlek `GEÇTİ`  - [ ] `config/tuned.yaml` oluştu  - [ ] Batarya gerilimi deftere yazıldı

---

## ADIM 5 — LiDAR (aracın gözü)
**Hedef:** LiDAR dönüyor, etrafın mesafesini gönderiyor, "ön" gerçekten ön.
**Önce kontrol:** LiDAR gücü Pi'den değil MP1584EN'den gelir; çıkışı multimetreyle ölç: **4,9–5,2 V** (`hardware/README.md`).

1. Bağlantıyı kontrol et (menü `8`):
   ```bash
   python3 stages/05-lidar/check_lidar.py
   ```
   **Ne görmelisin?** `Sağlık: İYİ`.
2. Yazılım LiDAR'ı ROS ile başlatır. **İki terminal** gerekecek (ikinci SSH penceresi aç ya da `tmux` kullan).
   - Terminal 1 (açık kalsın):
     ```bash
     cd ~/autonomous-car/software
     ros2 launch ros/launch/bringup.launch.py
     ```
   - Terminal 2:
     ```bash
     cd ~/autonomous-car/software
     python3 ros/scan_check.py
     ```
3. **Yön testi:** Bir kutuyu aracın **önüne** koy. `ön` mesafesi küçülmeli. Küçülmüyorsa `config/robot.yaml` → `lidar_yaw_deg` değerini 90, 180 veya -90 yap ve tekrar dene. Sağ-sol ters görünüyorsa `lidar_inverted: true`.
4. `robot.yaml`'a şunları da yaz (cetvelle, **metre**): `lidar_x_m` (LiDAR tekerlek ekseninin ne kadar ilerisinde), `robot_radius_m` (LiDAR'dan aracın en uzak köşesine mesafe).

- [ ] Sağlık İYİ  - [ ] Ön/sağ/sol/arka doğru  - [ ] `robot.yaml` ölçüleri girildi

---

## ADIM 6 — Odometri: araç ne kadar gittiğini bilsin
**Hedef:** Aracı 1 m itince "1,00 m" der; yerinde 1 tur çevirince "360°" der.
**Neden:** Duvarı takip ederken ve harita çıkarırken aracın nerede olduğunu bilmesi gerekir.
**Motorlar çalışmaz**, aracı **elinle** hareket ettireceksin.

1. Cetvelle ölç (metre cinsinden): tekerlek yarıçapı ve iki tekerleğin yere değdiği noktalar arası mesafe → `config/robot.yaml` → `wheel_radius_m`, `wheel_base_m`. (Örnek: 3,5 cm = `0.035`.)
2. Zemine 1 m çizgi çiz. Menü `9`: aracı çizgi boyunca **düz** it. Sonra menü `10`: aracı yerinde **3 tam tur** çevir.
3. Program sonuçları `config/robot_cal.yaml`'a yazmayı teklif eder; kabul et.
4. Kontrol:
   ```bash
   python3 stages/06-odometri/calibrate.py live
   ```
   Aracı 1 m itince `x` yaklaşık 1,00; 1 tur çevirince açı yaklaşık 360° olmalı.
5. Sürüş testi (**tekerlekler havada**): Terminal 1'de `ros2 launch ros/launch/bringup.launch.py`; Terminal 2'de
   `ros2 run teleop_twist_keyboard teleop_twist_keyboard` ile tuşlarla sür. Tuşu bırakınca **yarım saniyede duruyorsa** doğru.

- [ ] 1 m ≈ 1,00 (±3 cm)  - [ ] 1 tur ≈ 360° (±5°)  - [ ] Tuşu bırakınca duruyor

---

## ADIM 7 — Duvar takibi (asıl hedef!)
**Hedef:** Araç duvara 40 cm mesafede paralel gider, köşeleri döner, çarpmaz.
**Neden (benzetme):** Karanlıkta elinle duvara dokunarak yürümek gibi: duvar uzaksa yaklaş, yakınsa uzaklaş.

**Bölüm A — Simülasyon (robot gerekmez, riski sıfır).** Menü `11`:
```bash
python3 stages/07-duvar-takibi/sim_demo.py --world oda --side right
```
**Ne görmelisin?** `ÇARPMA YOK` ve `wall_follow_sim.png` resmi (aracın yolu). Sağ yerine sol için `--side left`.

**Bölüm B — Gerçek araç (kademeli):**
1. **Tekerlekler havada**, yavaş (`v_scale:=0.3`), duvar yerine elini aracın yanında tut:
   ```bash
   ros2 launch ros/launch/wall_follow.launch.py side:=right v_scale:=0.3
   ```
   (Önce Adım 5'teki `bringup.launch.py` açık olmalı; bu ikinci terminalde çalışır.)
2. Hareketler mantıklı mı? Duvar yakınsa tekerlekler uzaklaşacak şekilde dönmeli.
3. **Yerde, açık alanda,** karton duvar yanında, `v_scale:=0.5`. **Bir arkadaşın şalterin başında.** Ctrl+C durdurur.
4. Sorun giderme için `stages/07-duvar-takibi/README.md` içindeki ayar tablosuna bak.

- [ ] Simülasyon ÇARPMA YOK  - [ ] Havada mantıklı  - [ ] Yerde düz duvarda 40 cm ±5 cm  - [ ] Köşeleri geçiyor

---

## ADIM 8 — Harita çıkarma (isteğe bağlı)
Sadece Adım 7'yi bitirenler. Ayrıntı: `stages/08-slam/README.md`. Özet: aracı yavaş sürerken
```bash
ros2 launch ros/launch/slam.launch.py
```
çalışır; haritayı `ros2 run nav2_map_server map_saver_cli -f ~/harita` ile kaydedersin.

---

## Takılırsan (bu sırayla)
1. **Ekrandaki hatayı yavaşça oku.** Çoğu zaman ne yapılacağını söyler (ör. "invert değerini çevir").
2. **Hangi adımdasın?** `notes/sorun-giderme.md` → o adımın tablosuna bak.
3. **Hiçbir şey çalışmıyor / emin değilsin?** `hardware/docs/emergency.md` → **Bölüm B**, kutuları sırayla işaretle.
4. `python3 tools/diag.py` çalıştır → `diag_rapor.txt` oluşur.
5. Öğretmenine gönder: `diag_rapor.txt` + hangi adım + **ekrandaki tam hata** + kablolama fotoğrafı + deftere yazdığın sayılar.
   "Çalışmıyor" yetmez; **ne yaptığını, ne beklediğini, ne gördüğünü** yaz. Bu cümleyi kurabilmek mühendisliğin yarısıdır.

### Sık yapılan hatalar
| Hata | Çözüm |
|---|---|
| Komut "bulunamadı" / "dosya yok" | Yanlış klasördesin: `cd ~/autonomous-car/software` |
| `Permission denied` | Kurulumdaki grup ayarını yaptın mı? Çıkış yapıp tekrar girdin mi? (`notes/kurulum-ubuntu-ros.md` §2) |
| `ros2: command not found` | `source /opt/ros/jazzy/setup.bash` (ve `source ~/ros2_ws/install/setup.bash`) |
| İki program aynı anda motoru kullanıyor | Eskisini `Ctrl+C` ile kapat; bazen yeni terminal gerekir |
| Ayar dosyasını bozdum | `git checkout config/pins.yaml` (dosyayı eski haline getirir); `tuned.yaml`/`robot_cal.yaml`'ı silmek varsayılana döndürür |

## Sözlük
Kısa sözlük için: `notes/kavramlar.md`.
