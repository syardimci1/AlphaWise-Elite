"""decision_log JSON dokumunu yeniden oynatir ve DURUST bir rapor basar.

Kullanim:  python replay_calistir.py <dokum.json> [--json cikti.json]

Dokum, {"id","ticker","decision","total_score","layer_scores",...} nesnelerinden
olusan bir JSON dizisidir (psql json_agg ciktisi).
"""
import json
import sys

from karar_replay import kural_kapsamasi, toplu_replay


def rapor_metni(ozet: dict) -> str:
    s = []
    s.append("KARAR REPLAY RAPORU")
    s.append("=" * 60)
    s.append(f"Toplam kayit          : {ozet['toplam_kayit']}")
    s.append(f"Replay edilebilir     : {ozet['replay_edilebilir']}")
    s.append(f"Kapsam disi           : {ozet['kapsam_disi']}")
    s.append(f"Uyan                  : {ozet['uyan']}")
    s.append(f"Uymayan               : {ozet['uymayan']}")
    oran = ozet["sadakat_orani"]
    s.append("Sadakat orani         : " +
             ("OLCULEMEDI (replay edilebilir kayit yok)" if oran is None
              else f"{oran * 100:.2f}%"))
    s.append("")
    s.append("KAYIT TURU DAGILIMI")
    s.append("-" * 60)
    for k, v in sorted(ozet["sema_dagilimi"].items(), key=lambda x: -x[1]):
        etiket = "REPLAY EDILEBILIR" if k in ("maa_5_katman", "maa_4_katman_eski") \
                 else "kapsam disi"
        s.append(f"  {k:<24} {v:>4}   [{etiket}]")
    s.append("")
    if ozet["uymayanlar"]:
        s.append(f"UYUSMAYAN KAYITLAR ({len(ozet['uymayanlar'])})")
        s.append("-" * 60)
        for u in ozet["uymayanlar"]:
            s.append(f"  id={u['id']:<5} {u['ticker']:<10} {u['gerekce']}")
    else:
        s.append("UYUSMAYAN KAYIT YOK.")
    s.append("")
    kap = ozet.get("kural_kapsamasi")
    if kap:
        s.append("KURAL KAPSAMASI (gercek veri hangi dallari sinadi?)")
        s.append("-" * 60)
        for dal, n in kap["dal_sayimi"].items():
            durum = "sinandi" if n else ">>> HIC SINANMADI <<<"
            s.append(f"  {dal:<12} {n:>4}   {durum}")
        if kap["uyari"]:
            s.append("")
            s.append("  UYARI: " + kap["uyari"])
        s.append("")
    s.append(ozet["not"])
    return "\n".join(s)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        kayitlar = json.load(f)
    ozet = toplu_replay(kayitlar)
    ozet["kural_kapsamasi"] = kural_kapsamasi(kayitlar)
    print(rapor_metni(ozet))
    if "--json" in argv:
        hedef = argv[argv.index("--json") + 1]
        with open(hedef, "w", encoding="utf-8") as f:
            json.dump(ozet, f, ensure_ascii=False, indent=2)
        print(f"\nJSON: {hedef}")
    # Cikis kodu: uymayan varsa 1 — CI'da denetim olarak kullanilabilir.
    return 1 if ozet["uymayan"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
