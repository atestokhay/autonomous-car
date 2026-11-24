
# Hardware — Donanım Laboratuvarı ve Montaj Rehberi

Bu klasör, otonom araç donanımının güvenli biçimde kurulması, kablolanması ve doğrulanması için hazırlanmıştır.

Amaç yalnızca parçaları birbirine bağlamak değil; her bağlantının neden yapıldığını anlamak, ölçüm sonuçlarını kaydetmek ve bir sonraki aşamaya geçmeden önce sistemin güvenli olduğunu doğrulamaktır.

> [!CAUTION]
> **Güç güvenliği:** Araçta 3S LiPo batarya kullanılmaktadır. Batarya nominal olarak 11,1 V, tam doluyken 12,6 V seviyesindedir. Motorlarımız 6 V'luk, 300 RPM N20 motorlardır. Bataryayı motorlara veya TB6612 VM girişine doğrudan bağlamayın; motorlar 6,0 V buck regülatörden beslenir. PWM kullanılması aşırı besleme gerilimini güvenli hâle getirmez.

> [!WARNING]
> İlk enerjilendirme sırasında araç sabitlenmeli, tekerlekler yerden kesilmeli ve acil güç kesme yöntemi hazır olmalıdır. Duman, yanık kokusu, olağan dışı ısınma veya batarya hasarı görülürse testi durdurun ve [`software/docs/acil-durum.md`](../software/docs/acil-durum.md) prosedürünü uygulayın.

## 1. Donanım bileşenleri

| Bileşen | Adet | Görev |
|---|---:|---|
| Raspberry Pi 5 (8 GB) | 1 | Ana bilgisayar ve kontrol |
| N20 6 V 300 RPM enkoderli DC motor | 2 | Tahrik sistemi |
| TB6612FNG çift kanallı motor sürücü | 1 | Motor yönü ve PWM kontrolü (A = sol, B = sağ) |
| RPLIDAR S3 + USB adaptörü | 1 | Lazer tabanlı mesafe algılama |
| Başlat butonu (anlık basmalı, normalde açık) | 1 | Basıldıktan 5 sn sonra programı başlatır; çalışırken basınca durdurur |
| BNO055 9 eksen IMU | 1 | Gyro: odometride dönüş açısı (I2C, 0x28; yoksa açı enkoderden) |
| 3S LiPo batarya, 11,1 V nominal | 1 | Ana güç kaynağı |
| Buck regülatör, 6,0 V / 5 A | 1 | Motor beslemesi (TB6612 VM) |
| Buck regülatör, 5 V / 3 A (ayarlanabilir) | 1 | LiDAR için 5,0 V besleme |
| Buck regülatör, 5 V / 3 A (ayarlanabilir) | 1 | Raspberry Pi 5 beslemesi (5,1 V, USB-C güç kablosuyla) |
| USB-C güç kablosu (USB-C erkek → açık uç) | 1 | Pi regülatöründen Pi'nin USB-C girişine |
| Ana şalter ve 10 A DC sigorta | 1'er | Güç kesme ve aşırı akım koruması |
| Güç dağıtım klemensleri | İhtiyaca göre | Güç hatlarının dağıtımı |
| Kablo, konektör ve bağlantı elemanları | İhtiyaca göre | Elektriksel ve mekanik bağlantılar |

Parça listesi, kullanılan modüllerin tam modeline ve elektriksel özelliklerine göre doğrulanmalıdır.

## 2. Sistem mimarisi

### Güç dağıtımı

```text
3S LiPo Batarya (+)
        |
        v
  10 A DC Sigorta
        |
        v
    Ana Şalter
        |
        v
  +11,1 V Bara
        |
        +----> Buck regülatör (6,0 V)
        |        |
        |        +----> TB6612FNG VM ----> Sol / Sağ N20 motor
        |
        +----> Pi regülatörü (5,1 V / 3 A buck)
        |        |
        |        +----> USB-C güç kablosu ----> Raspberry Pi 5 (USB-C girişi)
        |
        +----> LiDAR regülatörü (5,0 V / 3 A buck)
                 |
                 +----> RPLIDAR S3 5V / GND
```

Negatif güç dönüşleri GND barasında birleşir. TB6612 kartında motor GND'si ile lojik GND içeriden ortak olduğu için motor buck OUT− ile GND bara arasında kısa ve kalın bir kablo bulunmalıdır; motorların dönüş akımı Raspberry Pi'nin ince GND kablolarından geçirilmemelidir.

**Önemli:** Bu çizim kavramsal güç mimarisidir. Gerçek bağlantılar, kullanılan modüllerin pin etiketleri ve üretici şemaları doğrulandıktan sonra yapılmalıdır.

### Motor beslemesi

TB6612FNG'nin VM girişi 13,5 V'a kadar dayanır, ama N20 motorlar 6 V'luktur; bu yüzden VM'ye batarya değil 6,0 V buck çıkışı bağlanır. Buck çıkışı yük bağlanmadan önce ayarlanmalı ve motorlar dönerken tekrar ölçülmelidir.

TB6612FNG kanal başına yaklaşık 1,2 A sürekli, 3,2 A tepe akım verir. Seçilen N20 modelinin kilitlenme (stall) akımı bu sınırla karşılaştırılmalıdır. Sürücünün STBY pini (GPIO26) LOW iken motorlar dönmez; yazılım bu pini kendisi yönetir.

### Raspberry Pi beslemesi

Raspberry Pi 5, 3 A'lik ayarlanabilir bir buck regülatörden beslenir. Regülatör çıkışı **yük bağlanmadan önce 5,1 V'a** ayarlanır ve Pi'ye bir USB-C güç kablosuyla (OUT+ → kırmızı/VBUS, OUT− → siyah/GND) bağlanır. Pi'nin GPIO 5 V pinleri (pin 2, 4) besleme için kullanılmaz; USB-C girişi Pi'nin kendi koruma devresinden geçer.

Raspberry Pi'nin önerdiği besleme 5 V / 5 A'dir; 3 A ile de çalışır, ancak bu durumda Pi 5 USB portlarına toplam 600 mA verir. Bu projede LiDAR kendi regülatöründen beslendiği ve USB'den sadece veri aktığı için bu sınır yeterlidir; USB'ye güç çeken başka cihaz (disk, kamera) takılmamalıdır. Regülatörün yükte gerçekten 3 A verebildiği, Pi tam yükte ve motorlar dönerken `vcgencmd get_throttled` (`0x0` olmalı) ile test edilmelidir. Regülatör aşırı ısınıyor ya da gerilim 5,0 V'un altına düşüyorsa 5 A'lik bir regülatöre geçilmelidir.

Raspberry Pi aynı anda iki ayrı güç kaynağına (ör. duvar adaptörü + regülatör) bağlanmamalıdır.

### LiDAR beslemesi

RPLIDAR S3 için üretici tarafından belirtilen besleme aralığı 4,9–5,2 V'tur. Besleme devresi, cihazın başlangıç akımını da karşılayabilmelidir.

LiDAR regülatörünün (5 V / 3 A buck) çıkışı LiDAR bağlanmadan önce 5,00 V'a ayarlanmalı ve ölçülmelidir. LiDAR'ın veri hattı USB adaptörü üzerinden Pi'ye gider. Adaptör kendi USB 5 V'unu da LiDAR'a veriyorsa regülatörle paralel iki kaynak oluşur; bunun olmadığı doğrulanmalıdır.

İki 3 A regülatör birbirine benzer: karıştırılmaması için üzerlerine **Pi (5,1 V)** ve **LiDAR (5,0 V)** etiketi yapıştırılmalıdır.

## 3. GPIO ve bağlantı referansı

Yazılım tarafında BCM GPIO numaraları kullanılacaktır. Fiziksel pin numaraları, Raspberry Pi'nin 40 pinli başlığındaki konumları ifade eder.

| İşlev | BCM GPIO | Fiziksel pin |
|---|---:|---:|
| TB6612 PWMA (sol motor hız) | GPIO12 | 32 |
| TB6612 AIN1 (sol motor yön) | GPIO5 | 29 |
| TB6612 AIN2 (sol motor yön) | GPIO6 | 31 |
| TB6612 PWMB (sağ motor hız) | GPIO13 | 33 |
| TB6612 BIN1 (sağ motor yön) | GPIO20 | 38 |
| TB6612 BIN2 (sağ motor yön) | GPIO21 | 40 |
| TB6612 STBY | GPIO26 | 37 |
| TB6612 VCC | 3V3 | 1 |
| TB6612 GND | GND | 6 |
| Sol enkoder A | GPIO17 | 11 |
| Sol enkoder B | GPIO27 | 13 |
| Sağ enkoder A | GPIO23 | 16 |
| Sağ enkoder B | GPIO24 | 18 |
| BNO055 SDA | GPIO2 | 3 |
| BNO055 SCL | GPIO3 | 5 |
| Enkoder + BNO055 VCC (3,3 V lojik hattı) | 3V3 | 17 |
| Enkoder + BNO055 GND (GND lojik hattı) | GND | 14 |
| Başlat butonu (bir ayağı) | GPIO16 | 36 |
| Başlat butonu (diğer ayağı) | GND | 34 |

Bu eşleşmeler `software/config/pins.yaml` dosyasıyla aynı tutulmalıdır.

> [!CAUTION]
> Raspberry Pi GPIO girişleri 5 V toleranslı değildir. Enkoderler ve BNO055 3,3 V'tan beslenir; enkoder kartında 5 V'a çeken bir pull-up olmadığı doğrulanmalıdır. TB6612 VCC'si de 3,3 V'tur; 6 V'luk VM ile karıştırılmamalıdır.

## 4. Montaj aşamaları

### Aşama 0 — Enerjisiz hazırlık

- [ ] Batarya ve tüm harici güç kaynakları çıkarıldı.
- [ ] Kabloların iki uçları etiketlendi.
- [ ] Güç dağıtımında kısa devre ihtimali kontrol edildi.
- [ ] GND bağlantıları doğrulandı.
- [ ] Kablolama listesi yazılım pin eşleşmeleriyle karşılaştırıldı.

### Aşama 1 — Güç sisteminin doğrulanması

- [ ] Ana şalter ve sigorta doğru hatta yerleştirildi.
- [ ] Batarya geriliminin 3S aralığında (10,5–12,6 V) olduğu doğrulandı.
- [ ] Motor buck çıkışı 6,0 V'a ayarlandı ve ölçüldü.
- [ ] LiDAR regülatörü çıkışı, yükler bağlanmadan önce 5,00 V'a ayarlandı ve ölçüldü.
- [ ] Pi regülatörü çıkışı, Pi bağlanmadan önce 5,1 V'a ayarlandı ve ölçüldü.
- [ ] Güç kabloları ile sinyal kabloları mümkün olduğunca ayrı güzergâhlara yerleştirildi.

### Aşama 2 — Raspberry Pi 5

- [ ] Besleme kaynağının akım kapasitesi doğrulandı.
- [ ] Pi tek bir güç kaynağına (USB-C güç kablosuyla Pi regülatörüne) bağlandı.
- [ ] Sistem başlatıldı ve kararlı çalıştığı doğrulandı.
- [ ] `vcgencmd get_throttled` çıktısı kaydedildi.

### Aşama 3 — Motorlar ve TB6612FNG sürücü

- [ ] Araç sabitlendi ve tekerlekler yerden kesildi.
- [ ] VM = 6 V (buck), VCC = 3,3 V (pin 1) olduğu ölçüldü.
- [ ] STBY pinin GPIO26'ya (pin 37) bağlı olduğu doğrulandı.
- [ ] Motorlar tek tek ve düşük PWM ile test edildi.
- [ ] Yazılımdaki ileri komutunun fiziksel ileri yönle eşleştiği doğrulandı.

### Aşama 4 — Enkoderler

- [ ] Enkoder beslemesi ve çıkış seviyeleri doğrulandı.
- [ ] A/B sinyalleri osiloskop veya lojik analizörle incelendi.
- [ ] Tekerlek elle döndürülerek darbe üretimi kontrol edildi.
- [ ] Sayım yönü ve bir tam turdaki sayım miktarı (`ticks_per_rev`, N20 dişli oranına bağlı; 300 RPM modelde genelde ~1400) kaydedildi.
- [ ] Motor dönerken `eksik` (kaçan kenar) sayacı 0 kaldı.

### Aşama 5 — LiDAR

- [ ] Adaptör pinout'u doğrulandı.
- [ ] LiDAR beslemesi yük altında ölçüldü.
- [ ] USB veri bağlantısı kontrol edildi.
- [ ] Seri aygıtın sistem tarafından tanındığı doğrulandı.
- [ ] LiDAR'ın kesintisiz çalıştığı gözlemlendi.

### Aşama 5b — BNO055 (gyro)

- [ ] BNO055 gövdeye düz ve sıkı sabitlendi (titreşimsiz, motorlardan mümkün olduğunca uzak).
- [ ] `i2cdetect -y 1` çıktısında `28` görüldü.
- [ ] `stages/06-odometri/check_imu.py yon`: araç elle 90° sola çevrilince ≈ +90° ölçüldü.

### Aşama 5c — Başlat butonu

- [ ] Buton GPIO16 (pin 36) ile GND (pin 34) arasına bağlandı (direnç yok; Pi dahili pull-up).
- [ ] `python3 tools/baslat_butonu.py test`: her basışta tek satır görüldü.
- [ ] Servis kuruldu (`bash tools/buton_servis_kur.sh`); basınca 5 sn sonra program başladı, tekrar basınca durdu.

### Aşama 6 — Bütünleşik sistem

- [ ] Önceki aşamalardaki tüm testler geçti.
- [ ] Güç bağlantıları ve kablo sabitlemeleri son kez kontrol edildi.
- [ ] Motorlar, enkoderler, BNO055, Raspberry Pi ve LiDAR birlikte test edildi.
- [ ] Beklenmeyen reset, bağlantı kopması veya olağan dışı ısınma görülmedi.

## 5. Test ve arıza belgeleri

Detaylı ölçüm ve kabul işlemleri için:

- [`software/docs/acil-durum.md`](../software/docs/acil-durum.md) — Acil durum prosedürleri ve arıza teşhisi.
- [`wiring/README.md`](wiring/README.md) — Kablolama, renk kodları ve bağlantı referansı.
- [`wiring/netlist.txt`](wiring/netlist.txt) — Hızlı bağlantı listesi.
- [`wiring/schematic.png`](wiring/schematic.png) — Görsel bağlantı şeması.
- [`wiring/schematic.fzz`](wiring/schematic.fzz) — Fritzing proje dosyası (eski 4S/L298N düzeni; **geçersiz**, güncel şema `schematic.png`).

Her testte ölçülen değerler ve sonuçlar kaydedilmelidir. Bir test başarısız olduğunda, neden belirlenmeden sonraki aşamaya geçilmemelidir.

## 6. Kaynaklar

- [Raspberry Pi resmi belgeleri](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [RPLIDAR S3 veri sayfası](https://wiki.slamtec.com/download/attachments/83066883/SLAMTEC_rplidar_datasheet_S3_v1.1_en.pdf)
- [Toshiba TB6612FNG veri sayfası](https://toshiba.semicon-storage.com/info/TB6612FNG_datasheet_en_20141001.pdf?did=10660&prodName=TB6612FNG)
- [Bosch BNO055 veri sayfası](https://www.bosch-sensortec.com/products/smart-sensor-systems/bno055/)

---

**Doküman durumu:** İlk donanım montajı ve doğrulama rehberi. Gerçek donanım revizyonu üzerinde yapılan testler sonucunda güncellenmelidir.
