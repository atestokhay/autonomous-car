# Sorun giderme — belirti → kontrol

Önce hangi aşamadasın, o bölüme bak. Çözülmezse çıktıyı kopyalayıp gönder.
**Gerçek robotta olan kural:** emin değilsen güç şalterini kapat, tekerlekleri havaya al, sonra düşün.

## Aşama 1 — Pi / güç
| Belirti | Kontrol |
|---|---|
| Pi açılırken veya motor çalışınca kendiliğinden kapanıyor | Motor hattı ve Pi hattı aynı regülatörde mi? Pi'nin 5 V hattını multimetre ile ölç (4,9–5,2 V). Batarya dolu mu? |
| `vcgencmd get_throttled` ≠ `0x0` | Güç yetersiz: kablo kalınlığı/uzunluğu, kontaklar, regülatör akım kapasitesi |
| `gpiodetect` boş / komut yok | `sudo apt install gpiod`; çıktıda `pinctrl-rp1` aranır |
| `lgpio` import hatası | `sudo apt install python3-lgpio` |
| `Permission denied` GPIO | `ls -l /dev/gpiochip*` ile grubuna bak; `notes/kurulum-ubuntu-ros.md` §2'deki udev kuralı uygulanmamışsa uygula, çıkış-giriş yap |
| Pi'de düşük voltaj uyarısı | LiDAR gücünü Pi'den almıyorsa da, ortak GND kontrol et; Pi'yi besleyen hattın voltaj düşüşü (ince kablo, gevşek konnektör) |
| Testler hata veriyor | `pip list` ile `pyyaml`, `numpy` var mı? Hata satırını gönder |

## Aşama 2 — Motor
| Belirti | Kontrol |
|---|---|
| Motor hiç dönmüyor | Motor hattı gücü açık mı (12 V regülatör çıkışı)? L298N'de IN1/IN2 kabloları doğru GPIO'ya mı (`pins.yaml`)? ENA jumper'ı çıkarılmış ve PWM pini ENA'ya bağlı mı? GND ortak mı? |
| Düşük duty'de dönmüyor, yüksekte dönüyor | Normal (ölü bölge); aşama 4 ölçer |
| Tekerlek ters yönde | `pins.yaml` → o motorun `invert` değerini çevir |
| Biri dönüyor, diğeri dönmüyor | Hangisi? Kabloyu diğer sürücüye takıp dene; sorun sürücüde mi motorda mı anla |
| L298N çok ısınıyor | Duty düşük tut; ısınma L298N'de normaldir ama dokunamayacak kadar sıcaksa durdur; besleme gerilimi/motor kilitli mi |
| Pi resetleniyor | Motor çalışınca batarya gerilimi çöküyor: batarya şarjı, kablo, regülatör akım limiti |

## Aşama 3 — Enkoder
| Belirti | Kontrol |
|---|---|
| Sayı hiç artmıyor | Enkoder 3,3 V ile mi besleniyor (5 V Pi'ye zarar verebilir!)? A/B kabloları doğru pinde mi (`pins.yaml`)? Pull-up açık mı? |
| Sayı **azalıyor** (ileri komutta) | `pins.yaml` → o enkoderin `invert` değerini çevir |
| Tekerlek başına tick yok/değişken | A ve B kanallarından biri bağlı değil olabilir: `watch` çıktısında yalnız bir kanalın değiştiğini gör |
| `eksik` değeri artıyor | Kenarlar kaçıyor: kabloyu kısalt/ekranla, hızı düşür, CPU yükü (`top`); sürerse C++ gerekir |
| `ticks_per_rev` ≈ 392'den çok farklı | Tekerleği tam 1 tur elle çevirdin mi? Dişli oranı farklı olabilir; ölçülen değeri `robot.yaml`'a yaz |

## Aşama 4 — PID
| Belirti | Kontrol |
|---|---|
| "hız NEGATİF" uyarısı | Enkoder yönü ters: `invert` çevir (aşama 3) |
| Motor tam gaza çıkıp duruyor ("runaway") | Enkoder bağlı değil/ters ya da tekerlek sıkışık; kodu güvenlik için kesti |
| Autotune "GEÇMEDİ", dosya yazılmadı | Mesajı oku: genelde batarya düşük, tekerlek yere sürtüyor, gevşek kablo. Bataryayı doldurup tekrar dene |
| Biri çok yavaş, diğeri hızlı | Motorlar farklı: normal, autotune ayrı ayar bulur; çok fark varsa mekanik sürtünme/dişli |
| Hız salınıyor | `tuned.yaml`'ı sil, `autotune.py`'yi tekrar çalıştır; olmazsa `pid.yaml`'da `kp`'yi yarıya indir |
| Yerde ayar bozuldu | Aşama 4 §3: yerde yeniden ayar |
| `dt_max_ms` > 20 | `sudo` ile çalıştır; Pi'de başka ağır işlem var mı (`top`) |

## Aşama 5 — LiDAR
| Belirti | Kontrol |
|---|---|
| `/dev/ttyUSB0` yok | Kablo/adaptör, `lsusb`, `dmesg \| tail`; USB'yi çıkarıp tak. Port `ttyUSB1` ise `pins.yaml` `lidar.port` |
| `Permission denied` | `sudo usermod -aG dialout $USER` → çıkış-giriş |
| Motor dönmüyor / ses yok | LiDAR 5 V alıyor mu? MP1584EN çıkışını yükte ölç (düşüyorsa akım yetersiz) |
| `Cevap yok` | Baud 1 000 000 (S3) olmalı; adaptörün baud desteği; USB kablosu çok uzun/kötü |
| Yön yanlış | `robot.yaml` → `lidar_yaw_deg` (90/180/-90) |
| Duvarlar ayna görüntüsü (sağ-sol ters) | `robot.yaml` → `lidar_inverted: true` |
| `/scan` yok | `ros2 topic list`; `ros2 launch` hata mesajı; `ros2 pkg executables sllidar_ros2` çıktısında `sllidar_node` var mı (kurulum notu 4) |
| `sllidar_ros2` bulunamadı | `source ~/ros2_ws/install/setup.bash` unutulmuş; veya derleme hatası |
| Çok az geçerli nokta | Lens kirli, cam/aynalı/siyah yüzey, güneş ışığı |

## Aşama 6 — Odometri
| Belirti | Kontrol |
|---|---|
| "wheel_radius_m boş" | `robot.yaml`'a cetvelle değer yaz (metre) |
| Düz iterken sol-sağ sayım çok farklı | Araç düz gitmedi ya da bir enkoder hatalı; `invert` kontrolü |
| 1 m'de x=1,00 çıkmıyor | `radius` kalibrasyonunu uzun mesafede (2 m) tekrarla; yer kaygan mı |
| Yerinde dönüş açısı yanlış | `base` kalibrasyonunu daha çok turla tekrarla |
| Sürüş düğümü araç hareket ettirmiyor | `/cmd_vel` yayınlanıyor mu (`ros2 topic echo /cmd_vel`)? Aşama 2–4 temiz mi? |
| Komutu bırakınca araç durmuyor | **Hemen güç şalteri.** Sonra `drive_node` çalışıyor mu bak; bu durum olmamalı, hata satırını gönder |
| Araç sürekli bir yana kayıyor | Aşama 4 tekrar (iki tekerlek aynı hıza ulaşıyor mu); tekerlek yarıçapları eşit mi |

## Aşama 7 — Duvar takibi
| Belirti | Kontrol |
|---|---|
| Hiç hareket etmiyor | Geri sayım bitti mi? Konsolda durum `ESTOP` mu? (LiDAR'a çok yakın engel / `robot_radius_m` çok büyük) |
| Hemen `ESTOP` | `robot_radius_m` (LiDAR'dan gövdenin en uzak noktası), LiDAR yönü doğru mu? Kendi gövden/kablolar taramada görünüyor mu |
| Duvara doğru/uzağa gidiyor, ters davranış | Yanlış taraf (`side`), `lidar_inverted`, `lidar_yaw_deg` |
| Duvara paralel ama mesafe 40 cm değil | LiDAR konumu (`lidar_y_m`), `target_dist_m` araç merkezine göre |
| Duvar boyunca sallanıyor | `kh`, `kd`, `v_max` düşür; aşama 4 PID'i yerde yeniden ayarla |
| İç köşede çarpıyor | `front_margin_m` ↑, `v_scale` düşür |
| Dış köşede duvardan uzaklaşıp kayboluyor | `arc_radius_m` = `target_dist_m` olsun; hız düşür |
| Sürekli `SEARCH` | Duvar 1,3 m'den uzak mı (`lost_dist_m`)? Duvar çok kısa mı (`min_wall_span_m`)? |
| LiDAR kesilince durmuyor | Olmamalı; güç şalteri, hata satırını gönder |
| Simülasyon çalışıyor, gerçekte çalışmıyor | Normal olabilir: gecikme, sürtünme. Önce `v_scale` 0,3; aşama 4 doğru mu |

## Aşama 8 — SLAM
| Belirti | Kontrol |
|---|---|
| Harita boş | `/scan` ve `/odom`/TF var mı (`ros2 run tf2_tools view_frames`) |
| Duvarlar çift/çarpık | Odometri (aşama 6) tekrar; daha yavaş sür |
| RViz'de `/map` görünmüyor | `ROS_DOMAIN_ID` iki tarafta aynı mı, aynı ağ mı, Fixed Frame `map` mı |
| `map_saver_cli` bulunamadı | `sudo apt install ros-jazzy-nav2-map-server` |
