# Aşama 6 — Odometri kalibrasyonu ve sürüş düğümü

Odometri: enkoder sayımlarından aracın `x, y, açı` konumunu hesaplar. İki ölçüye ihtiyaç duyar:
**tekerlek yarıçapı** ve **iki tekerleğin yere temas noktaları arası mesafe**. Bu aşamada ikisini ölçüp doğrularsın.
Bu adımlarda **motorlar çalışmaz**: aracı elle iter/çevirirsin.

## 1) Ön ölçüm (cetvel)
`config/robot.yaml` içine yaz (metre): `wheel_radius_m` (lastik dahil), `wheel_base_m`. İlk tahmin yeterli, aşağıdaki
kalibrasyon inceltir. (Boşsa scriptler "boş" diye uyarır.)

## 2) Kalibrasyon
Gerekli: şerit metre, zeminde düz bir çizgi.
```bash
cd software
python3 stages/06-odometri/calibrate.py radius --distance 1.0   # aracı 1 m ELLE DÜZ it
python3 stages/06-odometri/calibrate.py base --turns 3          # aracı yerinde 3 tam tur ELLE çevir
python3 stages/06-odometri/calibrate.py live                    # canlı x, y, açı: doğrulama
```
- `radius`: sayımlardan tekerlek yarıçapını hesaplar. İki tekerlek sayımı %5'ten fazla farklıysa uyarır
  (araç düz gitmedi ya da bir enkoder sorunlu).
- `base`: yerinde dönüşte tekerlekler **zıt** sayar; buradan tekerlekler arası mesafeyi hesaplar. Daha çok tur = daha doğru.
- Sonuç `config/robot_cal.yaml`'a yazılır (onay sorar) ve `robot.yaml`'ın üstüne biner. Silersen varsayılana dönülür.
- `live`: aracı 1 m itince `x≈1.000`, yerinde 1 tur çevirince açı `≈360°` göstermeli.

## 3) Sürüş düğümü testi (tekerlekler HAVADA)
```bash
ros2 launch ros/launch/bringup.launch.py
# yeni terminal:
ros2 run teleop_twist_keyboard teleop_twist_keyboard           # ok tuşlarıyla v, w ver
ros2 topic echo /odom --once
```
Hız komutunu bırakınca tekerlekler **0,5 sn içinde durmalı**. Sonra aracı yere koy, açık alanda:
```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"   # ~5 sn sonra Ctrl+C
```
Aracın gerçek aldığı yolu ölç; `/odom` x değeriyle %5 içinde uyumalı.

## Bitti sayılır
- [ ] `radius` ve `base` kalibre edildi (`robot_cal.yaml` var).
- [ ] `live`: 1 m itince x≈1.00 (±%3), 1 tur çevirince ≈360° (±5°).
- [ ] `teleop` ile sürüş düğümü araca hareket verdi, komut bırakılınca durdu.
- [ ] Yerde 1 m düz sürüşte gerçek yol ile `/odom` farkı < %5.

## Olası sorunlar
→ `notes/sorun-giderme.md` ("Aşama 6" bölümü)
