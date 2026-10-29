# Aşama 7 — Duvar takibi

Araç LiDAR ile yan taraftaki duvarı bulur, `target_dist_m` (varsayılan 0,40 m) uzaklıkta paralel gider;
iç köşede (önde duvar) yerinde dönüp devam eder; dış köşede (duvar biter) yayla dolanır; çok yakında acil durur.
Mantık `src/arac/wall_follow.py`, ayarlar `config/nav.yaml`.

## 1) Önce robotsuz: simülasyon
```bash
cd software
python3 stages/07-duvar-takibi/sim_demo.py --world oda --side right
python3 stages/07-duvar-takibi/sim_demo.py --world blok --side left
python3 stages/07-duvar-takibi/sim_demo.py --world koridor --side right
```
Duvara en yakın mesafeyi ve araç yolunu `wall_follow_sim.png` olarak verir (örnek: `ornek_oda.png`, `ornek_blok.png`).
`nav.yaml`'ı değiştirip etkisini hemen görebilirsin. Simülasyon **gerçek hayatı birebir temsil etmez**:
sürtünme, gecikme, gürültü farklıdır; bu yüzden hız ölçeğiyle düşükten başlanır.

## 2) Robotla (sırasıyla)
Ön koşul: aşama 4 (PID), 5 (LiDAR + yön testi), 6 (odometri) bitti.

1. **Tekerlekler havada**, düşük hız:
   ```bash
   ros2 launch ros/launch/wall_follow.launch.py side:=right v_scale:=0.3
   ```
   3 sn geri sayım sonra konsolda `FOLLOW v=… w=…` yazar. Elinle duvar gibi bir yüzeyi aracın sağına tut:
   tekerlekler duvara paralel gidecek şekilde dönmeli (duvar uzaksa duvara doğru, yakınsa uzağa).
2. **Yerde**, açık alanda, karton/koli ile yapılmış düz bir duvar (en az 2 m) kenarında, `v_scale:=0.5`.
   Elin güç şalterinde. Ctrl+C araç durdurur.
3. Köşeli bir oda/koridor (karton) ile iç ve dış köşeleri dene. Sonra `v_scale:=1.0`.

`side:=left` ile sol duvar takibi.

## 3) Davranış ve ayar (config/nav.yaml)
| Gözlem | Değiştir |
|---|---|
| Duvara hedefe oturması yavaş | `kd` ↑ |
| Duvar boyunca sağa-sola salınıyor | `kh` ↓, `kd` ↓, `v_max` ↓ |
| Duvara çok yaklaşıyor/uzak duruyor | `target_dist_m` |
| İç köşede çok geç dönüyor | `front_margin_m` ↑ ya da `slow_dist_m` ↑ |
| Dış köşede duvardan uzaklaşıp kayboluyor | `arc_radius_m` (≈ `target_dist_m` tut) |
| Duvar yokken sürekli arıyor | `lost_dist_m`, `min_wall_span_m` |
| Hemen acil durup duruyor | `hard_margin_m`, `robot_radius_m` (gövde ölçüsü doğru mu?) |

## 4) Durumlar (konsolda görünür)
`FOLLOW` duvar takibi · `TURN_INSIDE` iç köşe dönüşü · `ARC` dış köşe yayı · `SEARCH` duvar yok, arıyor ·
`ESTOP` çok yakın engel: dur (engel çekilince devam).
LiDAR verisi 0,5 sn gelmezse düğüm **durma komutu** yayınlar.

## Bitti sayılır
- [ ] Simülasyon üç dünyada da "ÇARPMA YOK".
- [ ] Düz duvar: araç duvara 0,40 m ±5 cm'ye oturuyor, salınımsız.
- [ ] İç ve dış köşeleri çarpmadan geçiyor (düşük hızda).
- [ ] Araç önüne el/kutu konunca duruyor/dönüyor; LiDAR fişi çekilince duruyor.

## Olası sorunlar
→ `notes/sorun-giderme.md` ("Aşama 7" bölümü)
