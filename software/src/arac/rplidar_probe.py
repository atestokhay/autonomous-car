"""ROS'suz RPLIDAR bağlantı teşhisi: seri porttan sağlık ve cihaz bilgisi ister.
Slamtec seri protokolü: istek A5 <cmd>; cevap tanıtıcısı A5 5A <4 bayt> <tip>, ardından veri."""
GET_INFO, GET_HEALTH = 0x50, 0x52
DESCRIPTOR_LEN = 7
HEALTH = {0: "İYİ", 1: "UYARI", 2: "HATA (donanım arızası, yeniden başlat)"}


def request(cmd):
    return bytes([0xA5, cmd])


def parse_descriptor(buf):
    """-> (veri_uzunluğu, tip) ya da None."""
    if len(buf) < DESCRIPTOR_LEN or buf[0] != 0xA5 or buf[1] != 0x5A:
        return None
    word = buf[2] | buf[3] << 8 | buf[4] << 16 | (buf[5] & 0x3F) << 24
    return word, buf[6]


def parse_health(payload):
    status = payload[0]
    err = payload[1] | payload[2] << 8
    return status, err, HEALTH.get(status, "?")


def parse_info(payload):
    return {"model_id": payload[0], "firmware": f"{payload[2]}.{payload[1]:02d}",
            "hardware": payload[3], "serial": payload[4:20].hex().upper()}


def _read_exact(port, n):
    data = b""
    while len(data) < n:
        chunk = port.read(n - len(data))
        if not chunk:
            break
        data += chunk
    return data


def ask(port, cmd, expect_len, expect_type):
    port.reset_input_buffer()
    port.write(request(cmd))
    desc = parse_descriptor(_read_exact(port, DESCRIPTOR_LEN))
    if desc is None:
        raise RuntimeError("Cevap yok / bozuk. Baud (S3: 1000000), port, güç ve USB adaptörünü kontrol et.")
    length, typ = desc
    if length != expect_len or typ != expect_type:
        raise RuntimeError(f"Beklenmeyen cevap (uzunluk {length}, tip {typ:#x}). Baud yanlış olabilir.")
    payload = _read_exact(port, length)
    if len(payload) != length:
        raise RuntimeError("Cevap yarım kaldı (güç düşüyor olabilir).")
    return payload


def probe(port):
    """port: pyserial benzeri nesne (read/write/reset_input_buffer). Döner: (info, (status, err, text))."""
    info = parse_info(ask(port, GET_INFO, 20, 0x04))
    health = parse_health(ask(port, GET_HEALTH, 3, 0x06))
    return info, health
