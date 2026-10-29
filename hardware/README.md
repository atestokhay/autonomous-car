
# Hardware — Donanım Laboratuvarı ve Montaj Rehberi

Bu klasör, otonom araç donanımının güvenli biçimde kurulması, kablolanması ve doğrulanması için hazırlanmıştır.

Amaç yalnızca parçaları birbirine bağlamak değil; her bağlantının neden yapıldığını anlamak, ölçüm sonuçlarını kaydetmek ve bir sonraki aşamaya geçmeden önce sistemin güvenli olduğunu doğrulamaktır.

> [!CAUTION]
> **Güç güvenliği:** Araçta 4S LiPo batarya kullanılmaktadır. Batarya nominal olarak 14,8 V, tam doluyken 16,8 V seviyesindedir. Motorlarımız 12 V sınıfındadır. Bataryayı motorlara doğrudan bağlamayın. Motor beslemesi uygun biçimde sınırlandırılmalıdır; PWM kullanılması aşırı besleme gerilimini güvenli hâle getirmez.

> [!WARNING]
> İlk enerjilendirme sırasında araç sabitlenmeli, tekerlekler yerden kesilmeli ve acil güç kesme yöntemi hazır olmalıdır. Duman, yanık kokusu, olağan dışı ısınma veya batarya hasarı görülürse testi durdurun ve `docs/emergency.md` prosedürünü uygulayın.

## 1. Donanım bileşenleri

| Bileşen | Adet | Görev |
|---|---:|---|
| Raspberry Pi 5 | 1 | Ana bilgisayar ve kontrol |
| JSumo 12 V 430 RPM enkoderli DC motor | 2 | Tahrik sistemi |
| L298N motor sürücü modülü | 2 | Motor yönü ve PWM kontrolü |
| RPLIDAR S3 | 1 | Lazer tabanlı mesafe algılama |
| 4S LiPo batarya, 14,8 V nominal | 1 | Ana güç kaynağı |
| MP1584EN buck regülatör | 1 | LiDAR için ayarlanabilir besleme |
| 6–24 V → 5 V USB-C DC-DC dönüştürücü | 1 | Raspberry Pi beslemesi |
| Ana şalter ve uygun DC sigorta | 1'er | Güç kesme ve aşırı akım koruması |
| Güç dağıtım klemensleri | İhtiyaca göre | Güç hatlarının dağıtımı |
| Kablo, konektör ve bağlantı elemanları | İhtiyaca göre | Elektriksel ve mekanik bağlantılar |

Parça listesi, kullanılan modüllerin tam modeline ve elektriksel özelliklerine göre doğrulanmalıdır.

## 2. Sistem mimarisi

### Güç dağıtımı

```text
4S LiPo Batarya (+)
        |
        v
    Ana Şalter
        |
        v
    DC Sigorta
        |
        v
  Güç Dağıtım Noktası
        |
        +----> Motor besleme yolu
        |        |
        |        +----> Sol L298N
        |        +----> Sağ L298N
        |
        +----> 5 V USB-C DC-DC
        |        |
        |        +----> Raspberry Pi 5
        |
        +----> MP1584EN
                 |
                 +----> LiDAR adaptörünün
                        doğrulanmış güç girişi
```

Negatif güç dönüşleri, uygun kablo kesitleri kullanılarak ortak bir yıldız GND noktasında birleştirilmelidir. Motorların yüksek akımlı dönüş yolu Raspberry Pi'nin ince GND kablolarından geçirilmemelidir.

**Önemli:** Bu çizim kavramsal güç mimarisidir. Gerçek bağlantılar, kullanılan modüllerin pin etiketleri ve üretici şemaları doğrulandıktan sonra yapılmalıdır.

### Motor beslemesi

L298N entegresinin belirli yüksek gerilimlere dayanabilmesi, bağlı motorların aynı gerilimde güvenle çalışacağı anlamına gelmez. Kullanılan 12 V motorlar için uygun gerilim sınırlandırması yapılmalı ve besleme yük altında ölçülmelidir.

Motorların kalkış akımı, sürücüdeki gerilim kaybı, kablo kesiti ve regülatör kapasitesi tasarım sırasında dikkate alınmalıdır.

### Raspberry Pi beslemesi

Raspberry Pi 5 için önerilen besleme 5 V / 5 A düzeyindedir. Kullanılacak 5 V / 3 A dönüştürücünün yeterliliği, Pi ve bağlı USB çevre birimleri birlikte çalışırken test edilmelidir.

Raspberry Pi aynı anda iki ayrı USB-C güç kaynağına bağlanmamalıdır.

### LiDAR beslemesi

RPLIDAR S3 için üretici tarafından belirtilen besleme aralığı 4,9–5,2 V'tur. Besleme devresi, cihazın başlangıç akımını da karşılayabilmelidir.

MP1584EN çıkışı LiDAR bağlanmadan önce ayarlanmalı ve ölçülmelidir. LiDAR adaptörünün güç pinleri doğrulanmadan herhangi bir pine harici gerilim uygulanmamalıdır.

## 3. GPIO ve bağlantı referansı

Yazılım tarafında BCM GPIO numaraları kullanılacaktır. Fiziksel pin numaraları, Raspberry Pi'nin 40 pinli başlığındaki konumları ifade eder.

| İşlev | BCM GPIO | Fiziksel pin |
|---|---:|---:|
| Sol motor ENA / PWM | GPIO12 | 32 |
| Sol motor IN1 | GPIO5 | 29 |
| Sol motor IN2 | GPIO6 | 31 |
| Sağ motor ENA / PWM | GPIO13 | 33 |
| Sağ motor IN1 | GPIO16 | 36 |
| Sağ motor IN2 | GPIO20 | 38 |
| Sol enkoder A | GPIO17 | 11 |
| Sol enkoder B | GPIO27 | 13 |
| Sağ enkoder A | GPIO22 | 15 |
| Sağ enkoder B | GPIO23 | 16 |

Bu eşleşmeler `software/config/pins.yaml` dosyasıyla aynı tutulmalıdır.

> [!CAUTION]
> Raspberry Pi GPIO girişleri 5 V toleranslı değildir. Enkoder çıkışının lojik seviyesi, bağlantıdan önce veri sayfası ve uygun ölçüm ekipmanıyla doğrulanmalıdır. Sinyal 3,3 V'u aşabiliyorsa uygun seviye dönüştürücü kullanılmalıdır.

## 4. Montaj aşamaları

### Aşama 0 — Enerjisiz hazırlık

- [ ] Batarya ve tüm harici güç kaynakları çıkarıldı.
- [ ] Kabloların iki uçları etiketlendi.
- [ ] Güç dağıtımında kısa devre ihtimali kontrol edildi.
- [ ] GND bağlantıları doğrulandı.
- [ ] Kablolama listesi yazılım pin eşleşmeleriyle karşılaştırıldı.

### Aşama 1 — Güç sisteminin doğrulanması

- [ ] Ana şalter ve sigorta doğru hatta yerleştirildi.
- [ ] Motor beslemesinin 12 V motor sınırlarına uygun olduğu doğrulandı.
- [ ] MP1584EN çıkışı, yükler bağlanmadan önce ölçüldü.
- [ ] Raspberry Pi DC-DC çıkışı ölçüldü.
- [ ] Güç kabloları ile sinyal kabloları mümkün olduğunca ayrı güzergâhlara yerleştirildi.

### Aşama 2 — Raspberry Pi 5

- [ ] Besleme kaynağının akım kapasitesi doğrulandı.
- [ ] Pi tek bir USB-C güç kaynağına bağlandı.
- [ ] Sistem başlatıldı ve kararlı çalıştığı doğrulandı.
- [ ] `vcgencmd get_throttled` çıktısı kaydedildi.

### Aşama 3 — Motorlar ve L298N sürücüleri

- [ ] Araç sabitlendi ve tekerlekler yerden kesildi.
- [ ] Her sürücüde kullanılacak A kanalı belirlendi.
- [ ] PWM kontrolü için ENA jumper'ı çıkarıldı.
- [ ] `5V-EN` jumper'ının işlevi kullanılan kartın şeması üzerinden doğrulandı.
- [ ] Motorlar tek tek ve düşük PWM ile test edildi.
- [ ] Yazılımdaki ileri komutunun fiziksel ileri yönle eşleştiği doğrulandı.

### Aşama 4 — Enkoderler

- [ ] Enkoder beslemesi ve çıkış seviyeleri doğrulandı.
- [ ] A/B sinyalleri osiloskop veya lojik analizörle incelendi.
- [ ] Tekerlek elle döndürülerek darbe üretimi kontrol edildi.
- [ ] Sayım yönü ve bir tam turdaki sayım miktarı kaydedildi.

### Aşama 5 — LiDAR

- [ ] Adaptör pinout'u doğrulandı.
- [ ] LiDAR beslemesi yük altında ölçüldü.
- [ ] USB veri bağlantısı kontrol edildi.
- [ ] Seri aygıtın sistem tarafından tanındığı doğrulandı.
- [ ] LiDAR'ın kesintisiz çalıştığı gözlemlendi.

### Aşama 6 — Bütünleşik sistem

- [ ] Önceki aşamalardaki tüm testler geçti.
- [ ] Güç bağlantıları ve kablo sabitlemeleri son kez kontrol edildi.
- [ ] Motorlar, enkoderler, Raspberry Pi ve LiDAR birlikte test edildi.
- [ ] Beklenmeyen reset, bağlantı kopması veya olağan dışı ısınma görülmedi.

## 5. Test ve arıza belgeleri

Detaylı ölçüm ve kabul işlemleri için:

- [`docs/test_sheet.md`](docs/test_sheet.md) — Enerjisiz kontroller, regülatör ölçümleri, lojik seviye ve motor testleri.
- [`docs/emergency.md`](docs/emergency.md) — Acil durum prosedürleri ve arıza teşhisi.
- [`wiring/README.md`](wiring/README.md) — Kablolama, renk kodları ve bağlantı referansı.
- [`wiring/netlist.txt`](wiring/netlist.txt) — Hızlı bağlantı listesi.
- [`wiring/schematic.png`](wiring/schematic.png) — Görsel bağlantı şeması.
- [`wiring/schematic.fzz`](wiring/schematic.fzz) — Fritzing proje dosyası.

Her testte ölçülen değerler ve sonuçlar kaydedilmelidir. Bir test başarısız olduğunda, neden belirlenmeden sonraki aşamaya geçilmemelidir.

## 6. Kaynaklar

- [Raspberry Pi resmi belgeleri](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [RPLIDAR S3 veri sayfası](https://wiki.slamtec.com/download/attachments/83066883/SLAMTEC_rplidar_datasheet_S3_v1.1_en.pdf)
- [ST L298 veri sayfası](https://www.st.com/resource/en/datasheet/cd00000240.pdf)
- [JSumo 12 V 430 RPM enkoderli DC motor](https://www.robotsepeti.com/jsumo-12v-430rpm-enkoderli-dc-motor)

---

**Doküman durumu:** İlk donanım montajı ve doğrulama rehberi. Gerçek donanım revizyonu üzerinde yapılan testler sonucunda güncellenmelidir.
