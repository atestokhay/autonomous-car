# Kavramlar (kısa sözlük)

- **PWM / duty:** Motora giden gücü açıp kapayarak ayarlamak. Duty 0,5 = zamanın yarısı açık ≈ yarım güç.
- **L298N:** Motor sürücü. IN1/IN2 yönü, ENA'ya (PWM) güç seviyesini belirler. Her motora ayrı sürücü kullanıyoruz.
- **Enkoder:** Motor milinde dönmeyi sayan sensör. A/B iki kanalı hem hız hem yön verir. `ticks_per_rev`: tekerlek bir turda kaç sayım üretir (392).
- **PID:** Hedef hıza ulaşmak için hatayı (hedef − ölçülen) düzelten denetleyici. **P** şimdiki hataya, **I** biriken hataya, **D** hatanın değişimine tepki verir. Bizde ayrıca **feedforward** (kff) var: hedefe uygun gücü baştan verir.
- **Ölü bölge (deadband):** Motorun dönmeye başlaması için gereken minimum güç.
- **Autotune:** Kodun motoru deneyip PID değerlerini kendi bulması.
- **Odometri:** Tekerlek sayımlarından aracın nereye gittiğini (x, y, açı) hesaplamak. Zamanla küçük hatalar birikir.
- **LiDAR:** Dönerek etrafın mesafelerini ölçen lazer. Çıktısı `/scan`.
- **base_link:** Aracın merkezi (iki tekerlek ortası). x ileri, y sol. Açı saat yönünün tersine pozitif.
- **ROS 2:** Programların birbirine mesaj (topic) göndermesini sağlayan çerçeve. `/cmd_vel` = hız komutu (v, w), `/odom` = konum, `/scan` = LiDAR.
- **v, w:** v: ileri hız (m/s); w: dönme hızı (rad/s, sola +).
- **SLAM:** Harita çıkarırken aynı anda haritada yer bulma.
- **invert:** Bir motorun veya enkoderin yönünü yazılımda çevirir; kabloya dokunmak gerekmez.
