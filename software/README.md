# software — Otonom araç yazılımı

> **Öğrenci misin?** Kurulumdan sonra terminale sadece `arac` yaz. Aşağısı ayrıntılı başvuru içindir.

Raspberry Pi 5 + RPLIDAR S3 + iki enkoderli motorla **duvar takibi yapan** otonom araç. Donanım bağlantıları
`~/autonomous-car.v2/hardware/` klasöründe; buradaki pinler (`config/pins.yaml`) o dokümanlarla birebir aynıdır.

> **Durum (dürüst özet):** Kodun tamamı simülasyonda ve birim testlerinde (46 test) doğrulandı. **Gerçek robotta,
> gerçek Pi 5'te ve gerçek ROS 2'de henüz çalıştırılmadı.** Bu yüzden aşamalar sırayla, her birinin "Bitti sayılır"
> kriteri sağlanarak ilerlenir. Takıldığın yerde önce `notes/sorun-giderme.md`'ye bak.

## Bir şey çalışmıyorsa
1. `python3 tools/diag.py` (motor oynatmaz) → `diag_rapor.txt`
2. `~/autonomous-car.v2/hardware/docs/emergency.md` → Bölüm B: sırayla kontrol listesi
3. `notes/sorun-giderme.md`: aşama aşama belirti tablosu
4. Ölçümlerini `~/autonomous-car.v2/hardware/docs/test_sheet.md`'ye yaz

## Hızlı başlangıç
1. Pi'ye **Ubuntu 24.04** yaz, sonra tek komut: `autonomous-car.v2` deposundaki kurulum komutu (ayrıntı/elle yol: `notes/kurulum-ubuntu-ros.md`)
2. `cd software && python3 -m unittest discover -s tests` → hepsi `OK` olmalı (Pi'yi doğrular)
3. Aşamaları sırayla yap (aşağıdaki tablo). Her aşama klasöründe kendi `README.md`'si var.

## Aşamalar (bir öncekinin "Bitti sayılır" kriteri sağlanmadan geçme)

| # | Klasör | Ne yapılır | Robot gerekir mi |
|---|---|---|---|
| 1 | `stages/01-guc-ve-pi` | Pi kurulumu, güç doğrulaması | Evet (güç) |
| 2 | `stages/02-motor` | Motor yönü, PWM | Evet, tekerlekler havada |
| 3 | `stages/03-enkoder` | Enkoder yönü ve tick/tur doğrulaması | Evet |
| 4 | `stages/04-pid` | Hız PID **otomatik ayar**, adım testi | Evet, tekerlekler havada |
| 5 | `stages/05-lidar` | LiDAR bağlantısı, `/scan` kontrolü | Evet (LiDAR) |
| 6 | `stages/06-odometri` | Tekerlek yarıçapı/mesafesi kalibrasyonu, sürüş düğümü | Evet |
| 7 | `stages/07-duvar-takibi` | Duvar takibi (önce simülasyon, sonra robot) | Evet, açık alan |
| 8 | `stages/08-slam` | (İsteğe bağlı) SLAM ile harita çıkarma | Evet |

## Klasör yapısı
```
config/    pins.yaml (pinler, tek kaynak) · robot.yaml (ölçüler) · pid.yaml · nav.yaml (duvar takibi) · slam_toolbox.yaml
           tuned.yaml ve robot_cal.yaml: kalibrasyon scriptleri BU robot için üretir, varsayılanların üstüne biner
src/arac/  motor, encoder, pid, wheel (tekerlek hız döngüsü), drive (v,w -> tekerlekler), kinematics (+odometri),
           scan + wall_follow (duvar takibi), autotune, sim*/ (donanımsız test modelleri)
ros/       drive_node.py · wall_follow_node.py · scan_check.py · launch/ (bringup, wall_follow, slam)
stages/    aşama README'leri ve çalıştırılabilir scriptler
tests/     donanımsız testler (simülasyon)
notes/     kurulum, sorun giderme, kavramlar
```

## Ortak kurallar (güvenlik)
- **İlk denemede tekerlekler her zaman havada.** Yere ancak aşama 4 "Bitti sayılır" sağlanınca.
- Duvar takibini ilk kez çalıştırırken **güç şalterine elin yetişen biri** başında dursun, açık alan olsun.
- Hız komutu kesilirse (kablo, ağ, Ctrl+C) araç **0,5 sn içinde durur**; LiDAR verisi kesilirse de durur.
- Bir testte beklenmedik bir şey olursa **durdur ve nedenini bul**; sonraki aşamaya geçme.
- Yön ters çıkarsa kabloyu sökme: `config/pins.yaml`'da ilgili `invert` değerini çevir.

## Komut özeti
```bash
python3 stages/02-motor/run.py --side left --duty 0.3          # aşama 2
python3 stages/03-enkoder/run.py watch                          # aşama 3
python3 stages/04-pid/autotune.py                               # aşama 4 (tek komut)
python3 stages/05-lidar/check_lidar.py                          # aşama 5
python3 stages/06-odometri/calibrate.py radius                  # aşama 6
python3 stages/07-duvar-takibi/sim_demo.py --world blok --side left   # aşama 7 (robotsuz)
ros2 launch ros/launch/wall_follow.launch.py side:=right v_scale:=0.5 # aşama 7 (robotla)
```
