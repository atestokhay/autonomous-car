"""Başlat butonu mantığı (donanımdan bağımsız, test edilebilir).
  BEKLE      --bas-->  GERI_SAYIM (delay_s sn)  --süre doldu-->  CALISIYOR (program açık)
  GERI_SAYIM --bas-->  BEKLE        (yanlışlıkla basıldıysa iptal)
  CALISIYOR  --bas-->  durdur  -> BEKLE      (program kendi kapanırsa da BEKLE)
Buton GPIO ile GND arasında; dahili pull-up açık: basılı = 0 (LOW)."""

BEKLE, GERI_SAYIM, CALISIYOR = "BEKLE", "GERI_SAYIM", "CALISIYOR"


class Debouncer:
    """Kontak sıçramasını süzer: seviye `stable_s` boyunca değişmezse kabul edilir.
    update(now, raw) -> basılma ANINDA (bir kez) True döner.
    Açılıştaki ilk kararlı seviye basma sayılmaz: hat başta LOW ise (kısa devre / basılı tutuluyor) program
    kendiliğinden BAŞLAMAZ; buton bırakılıp yeniden basılmalıdır."""

    def __init__(self, stable_s=0.05, active_low=True):
        self.stable_s, self.active_low = stable_s, active_low
        self._raw, self._since, self._state = None, 0.0, None

    def update(self, now, raw):
        pressed = (raw == 0) if self.active_low else (raw == 1)
        if pressed != self._raw:
            self._raw, self._since = pressed, now
            return False
        if pressed != self._state and now - self._since >= self.stable_s:
            first = self._state is None
            self._state = pressed
            return pressed and not first        # sadece basılma kenarı; bırakma kenarı ve açılış False
        return False

    @property
    def pressed(self):
        return bool(self._state)


class StartController:
    """start(): programı başlatır.  stop(): programı durdurur.  running(): program hâlâ açık mı?
    log(text): durum mesajı. Hepsi dışarıdan verilir (testte sahte, Pi'de gerçek süreç)."""

    def __init__(self, delay_s, start, stop, running, log=print):
        self.delay_s = float(delay_s)
        self._start, self._stop, self._running, self.log = start, stop, running, log
        self.state, self.deadline, self._last_announce = BEKLE, 0.0, None

    def update(self, now, pressed_edge):
        if self.state == BEKLE:
            if pressed_edge:
                self.state, self.deadline = GERI_SAYIM, now + self.delay_s
                self._last_announce = None
                self.log(f"Butona basıldı: program {self.delay_s:.0f} sn sonra başlıyor "
                         "(iptal için tekrar bas). ARACIN ÖNÜNDEN ÇEKİL.")
        elif self.state == GERI_SAYIM:
            if pressed_edge:
                self.state = BEKLE
                self.log("Geri sayım İPTAL edildi. Başlatmak için butona tekrar bas.")
                return
            kalan = self.deadline - now
            if kalan <= 0:
                self.log("Program başlatılıyor. Durdurmak için butona bas.")
                self._start()
                self.state = CALISIYOR
                return
            sn = int(kalan) + 1
            if sn != self._last_announce:
                self._last_announce = sn
                self.log(f"  {sn}...")
        elif self.state == CALISIYOR:
            if pressed_edge:
                self.log("Butona basıldı: program durduruluyor (araç durur).")
                self._stop()
                self.state = BEKLE
                self.log("Durdu. Yeniden başlatmak için butona bas.")
            elif not self._running():
                self.state = BEKLE
                self.log("Program kapandı. Yeniden başlatmak için butona bas.")
