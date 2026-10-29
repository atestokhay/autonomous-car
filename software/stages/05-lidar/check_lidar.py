"""Aşama 5: LiDAR bağlantı kontrolü (ROS gerektirmez). Seri porttan cihaz bilgisi ve sağlık durumu ister.
Gerekli: pip/apt ile pyserial (sudo apt install python3-serial)."""
import argparse
import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from arac import rplidar_probe  # noqa: E402
from arac.config import load_config  # noqa: E402


def main():
    cfg = load_config()["pins"]["lidar"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=cfg["port"])
    ap.add_argument("--baud", type=int, default=cfg["baud"])
    a = ap.parse_args()

    ports = sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
    print("Bulunan seri aygıtlar:", ports or "YOK")
    if not ports:
        print("→ LiDAR adaptörü USB'de görünmüyor: kabloyu, adaptörü ve `lsusb` çıktısını kontrol et (notes/sorun-giderme.md).")
        sys.exit(1)
    try:
        import serial
    except ImportError:
        sys.exit("pyserial yok: sudo apt install python3-serial")
    try:
        port = serial.Serial(a.port, a.baud, timeout=1.0)
    except (serial.SerialException, PermissionError) as e:
        print(f"{a.port} açılamadı: {e}")
        print("→ İzin hatasıysa: sudo usermod -aG dialout $USER  (sonra çıkış yapıp tekrar gir)")
        sys.exit(1)
    try:
        info, (status, err, text) = rplidar_probe.probe(port)
    except RuntimeError as e:
        print("HATA:", e)
        sys.exit(1)
    finally:
        port.close()
    print(f"Cihaz: model_id={info['model_id']:#x}  firmware={info['firmware']}  donanım={info['hardware']}")
    print(f"Seri no: {info['serial']}")
    print(f"Sağlık: {text} (hata kodu {err:#06x})")
    if status != 0:
        sys.exit(2)
    print("\nLiDAR haberleşiyor. Sonraki adım: ros2 launch ros/launch/bringup.launch.py")


if __name__ == "__main__":
    main()
