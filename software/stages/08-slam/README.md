# Aşama 8 — SLAM ile harita çıkarma (isteğe bağlı)

SLAM: aracın aynı anda hem haritayı çıkarması hem de haritada yerini bulması. `slam_toolbox` kullanılır
(LiDAR taramaları + odometri). **Odometri (aşama 6) iyi kalibre değilse harita bozuk çıkar.**

## Çalıştır
```bash
cd software
ros2 launch ros/launch/slam.launch.py
```
Aracı yavaş sür: elle (`ros2 run teleop_twist_keyboard teleop_twist_keyboard`) ya da duvar takibiyle
(ayrı terminalde `python3 ros/wall_follow_node.py --side right`). Hızlı dönüşler haritayı bozar; düz duvarlı, bol köşeli
bir oda seç, başlangıç noktasına dönerek "döngüyü kapat".

## Haritayı görmek (dizüstü bilgisayarda RViz)
Pi ile bilgisayar **aynı ağda ve aynı `ROS_DOMAIN_ID`'de** olsun:
```bash
export ROS_DOMAIN_ID=7        # iki tarafta da aynı
rviz2                         # Fixed Frame: map; Add > Map (/map), LaserScan (/scan)
```

## Kaydet
```bash
ros2 run nav2_map_server map_saver_cli -f ~/harita
```
`~/harita.pgm` ve `~/harita.yaml` oluşur.

## Ayar
`config/slam_toolbox.yaml`: `resolution` (0,05 m), `max_laser_range`, `minimum_travel_distance`.
Harita çarpık/çift duvarlı çıkıyorsa önce yavaşla ve aşama 6'yı tekrarla.

## Bitti sayılır
- [ ] RViz'de oda duvarları düz ve tek çizgi, döngü kapanınca kayma yok.
- [ ] `map_saver_cli` ile harita dosyası alındı.

## Olası sorunlar
→ `notes/sorun-giderme.md` ("Aşama 8" bölümü)
