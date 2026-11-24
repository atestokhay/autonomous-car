# Aşama 9 – Şerit ortalama (yarışma sürüşü)

Fibonacci Autonomous Car şartnamesi **AC-3.5** duvar takibini yasaklar (duvarı referans alarak sürekli yol almak).
Bu aşamadaki denetleyici (`src/arac/lane_follow.py`) tek bir duvarı takip etmez:

- **Boşluk takibi:** Her LiDAR taramasında gövde genişliğinde bir koridorun hangi yönde en uzun açık kaldığına bakar ve o yöne döner.
- **Şerit ortalama:** Düzlükte iki yanda da duvar varsa iki duvarın ortasında kalır.
- **Köşeler:** Önü kapanınca açık tarafa dönerek geçer. Sağ/sol ayarı yoktur; araç başlangıç çizgisine hakemin söylediği yöne bakacak şekilde konur.
- **Diğer robotlar:** Engel olarak görülür ve etraflarından dolaşılır. Önü tamamen kapalıysa önce 3 sn bekler, geri dönmez (ters yönde çizgi geçişi cezalıdır).

## 1. Simülasyon (robotsuz)
```bash
python3 stages/09-serit-ortalama/sim_pist.py --robots 1
python3 stages/09-serit-ortalama/sim_pist.py --robots 3
```
Çıktı: lap sayısı, ters geçiş, duvara en yakın mesafe ve `serit-N-robot.png` grafiği. İlk çizgi geçişi başlangıçtır.

## 2. Gerçek robot
1. `config/robot.yaml` ve `config/nav.yaml -> lane_follow` içindeki gövde ölçülerini (`half_width_m`, `front_len_m`) aracın gerçek ölçüsüne göre düzelt. LiDAR gövde ortasında değilse `lidar_x_m` ayarla.
2. Önce yarım hızla dene: `ros2 launch ros/launch/lane_follow.launch.py v_scale:=0.5`
3. Başlat butonu `config/pins.yaml -> start_button.mode: lane` iken bu programı başlatır.

**Uyarı:** AC-3.5'in yorumu hakeme aittir. Bu yaklaşımın kabul edildiğini organizasyondan yazılı teyit etmeniz önerilir.
