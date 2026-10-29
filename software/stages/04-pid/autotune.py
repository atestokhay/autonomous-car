"""Aşama 4: OTOMATİK AYAR (kendi kendine). Tekerlekler HAVADA, araç sabit.
Süpürme + basamak cevabı ölçer, PI hesaplar, kapalı çevrimde doğrular ve
config/tuned.yaml'a yazar. Doğrulama geçmezse HİÇBİR ŞEY yazmaz."""
import argparse
import datetime
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from arac.autotune import Rig, autotune_side  # noqa: E402
from arac.config import CONFIG_DIR, load_config, require_ticks  # noqa: E402
from arac.factory import close_hardware, make_hardware  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["left", "right", "both"], default="both")
    ap.add_argument("--mock", action="store_true", help="donanımsız, simülasyonla dene (dosya yazmaz)")
    ap.add_argument("--yes", action="store_true", help="onay sorma")
    a = ap.parse_args()

    cfg = load_config()
    pc = cfg["pid"]
    ticks = (cfg["robot"].get("ticks_per_rev") or 392) if a.mock else require_ticks(cfg)
    sides = ["left", "right"] if a.side == "both" else [a.side]

    if not (a.mock or a.yes):
        input("TEKERLEKLER HAVADA ve araç sabit mi? Motorlar kısa süre yüksek hızda dönecek. [Enter] ")

    results, failed = {}, []
    for s in sides:
        print(f"\n=== {s.upper()} TEKERLEK ===")
        gpio, parts = make_hardware(cfg, [s], a.mock)
        p = parts[s]
        rig = Rig(p["motor"], p["encoder"], p["plant"], hz=pc["loop_hz"], virtual=a.mock)
        try:
            results[s] = autotune_side(rig, ticks, pc)
            for w in results[s]["warnings"]:
                print("  UYARI:", w)
        except KeyboardInterrupt:
            print("\nİptal")
            failed.append(s)
            break
        except RuntimeError as e:
            print("  HATA:", e)
            failed.append(s)
        finally:
            close_hardware(gpio, parts)

    if results and not a.mock:
        path = CONFIG_DIR / "tuned.yaml"
        tuned = yaml.safe_load(open(path, encoding="utf-8")) if path.exists() else {}
        tuned = tuned or {}
        meta = tuned.get("_meta", {})
        for s, r in results.items():
            tuned[s] = r["params"]
            meta[s] = {"date": datetime.datetime.now().isoformat(timespec="seconds"),
                       "metrics": r["metrics"], "model": r["model"], "warnings": r["warnings"]}
        tuned["_meta"] = meta
        with open(path, "w", encoding="utf-8") as f:
            f.write("# autotune.py çıktısı. pid.yaml'ın üstüne biner. Silersen pid.yaml değerlerine dönülür.\n")
            yaml.safe_dump(tuned, f, sort_keys=False, allow_unicode=True)
        print(f"\nYazıldı: {path}")
    elif results:
        print("\n(mock: dosya yazılmadı)")
    if failed:
        print("Başarısız taraflar:", ", ".join(failed), "→ mevcut değerler korunuyor.")
        sys.exit(1)
    print("Bitti. Sonraki adım: python stages/04-pid/run.py --side both")


if __name__ == "__main__":
    main()
