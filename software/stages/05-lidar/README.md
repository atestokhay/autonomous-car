# Aşama 5 — LiDAR (RPLIDAR S3)

Önce `hardware/` aşama 5 kontrol listesi: adaptör pinout'u, **MP1584EN çıkışı ~5,0 V**, USB sadece veri.
LiDAR gücü Pi'den **alınmaz**.

## 1) Seri bağlantı kontrolü (ROS'suz)
```bash
python3 stages/05-lidar/check_lidar.py
```
Beklenen: `Sağlık: İYİ` ve cihaz bilgisi. Script LiDAR'a doğrudan sağlık/bilgi sorusu sorar (S3: **1 000 000 baud**).

| Çıktı | Anlamı → ne yap |
|---|---|
| `Bulunan seri aygıtlar: YOK` | USB adaptör görünmüyor → kablo, adaptör, `lsusb` |
| `açılamadı: Permission denied` | `sudo usermod -aG dialout $USER`, çıkış-giriş yap |
| `Cevap yok / bozuk` | Güç yok/düşük (5 V'u ölç), baud yanlış, port yanlış (`ttyUSB1`?) |
| `Sağlık: HATA` | LiDAR'ı yeniden başlat (gücü kes-ver), lens temizle |

## 2) ROS 2 sürücüsü ve `/scan`
`notes/kurulum-ubuntu-ros.md` içinde `sllidar_ros2` derlendiyse (her yeni terminalde `source ~/ros2_ws/install/setup.bash`):
```bash
cd software
ros2 launch ros/launch/bringup.launch.py        # LiDAR + sürüş düğümü + TF
# başka terminalde:
python3 ros/scan_check.py
```
`scan_check.py` 5 sn dinler: tarama hızı (~10 Hz), geçerli nokta oranı, ön/sol/arka/sağ mesafeler yazar.

**Yön testi (önemli):** Bir kutuyu aracın **önüne** koy, `ön` mesafesi düşmeli. Düşmüyorsa LiDAR farklı yöne bakıyor:
`config/robot.yaml` → `lidar_yaw_deg` değerini 90 / 180 / -90 dene. Sol-sağ **ayna** gibiyse `lidar_inverted: true` yap.
Ayrıca LiDAR'ın `x, y` konumunu (tekerlek ekseni merkezine göre, metre) `lidar_x_m`, `lidar_y_m`'ye yaz;
gövdenin LiDAR'dan en uzak noktasını `robot_radius_m`'ye yaz (güvenlik mesafeleri buna göre hesaplanır).

## Bitti sayılır
- [ ] `check_lidar.py` → `Sağlık: İYİ`.
- [ ] `/scan` ~10 Hz, geçerli nokta oranı makul (açık odada > %60).
- [ ] Kutu önüne konunca `ön` değişiyor; yön/ayna ayarı doğru.
- [ ] LiDAR motoru dönerken Pi'de `Under-Voltage` uyarısı yok, reset yok.

## Olası sorunlar
→ `notes/sorun-giderme.md` ("Aşama 5" bölümü)
