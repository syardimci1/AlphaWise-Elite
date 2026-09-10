"""
Karar REPLAY — decision_log'dan kararin yeniden uretilmesi (Madde 34).

NEDEN (AutoGen dersi)
=====================
Bir karar sistemi, verdigi karari SONRADAN aynen yeniden uretebilmelidir.
Uretemiyorsa: "neden bu karar verildi" sorusunun yaniti kayittaki metne
guvenmek zorunda kalir, kayit ile kod arasindaki sessiz bir ayrisma hic fark
edilmez ve gecmis kararlarin denetimi imkansizlasir.

BU MODUL KURALI YENIDEN YAZAR, KOPYALAMAZ
=========================================
Canli karar kurali maa/src/main.py icindedir ve o dosya KORUNMUSTUR
(degistirilemez, buradan ithal de edilmez — ithal etmek FastAPI, LLM
istemcisi ve veritabani baglantilarini da yuklerdi). Bunun yerine kural
BELGELENDIGI gibi bagimsiz uygulanir ve iki uygulamanin ayni oldugu
TESTLE kilitlenir. parite.py'deki desenin aynisi.

Kural (maa/src/main.py:583-600):
    gecerli katman = None OLMAYAN katman skoru
    gecerli < 3            -> BEKLE, toplam None
    toplam <= -3           -> DIKKAT ET
    toplam >= 4            -> EKLE
    aksi                   -> TUT

REPLAY EDILEMEYEN KAYIT, "UYUSTU" SAYILMAZ
==========================================
decision_log TEK BIR gunluk degildir: olculdu (09.09.2026), ayni tabloda
ALTI farkli kayit semasi var (5 katmanli MAA karari, 4 katmanli eski MAA
karari, god_mode kayitlari, portfoy sinyali, LLM kaskadi...). Yalnizca
katman skoru tasiyanlar yeniden uretilebilir. Digerleri "replay edilemedi"
olarak AYRI raporlanir; basari oranina dahil edilmez.
"""
from __future__ import annotations
from typing import Optional

KATMANLAR = ("taa", "faa", "raa", "saa", "chronos")
ESKI_KATMANLAR = ("taa", "faa", "raa", "saa")   # Chronos eklenmeden onceki sema

ASGARI_KATMAN = 3
DIKKAT_ESIGI = -3
EKLE_ESIGI = 4


def karar_uret(katman_skorlari: dict) -> dict:
    """Katman skorlarindan karari yeniden uretir.

    Doner: {"karar", "toplam", "gecerli_katman"}
    None skorlar (olculemedi) toplama GIRMEZ ve sifir sayilmaz — bu ayrim
    232d1a0 ile kurulmustur.
    """
    gecerli = {k: v for k, v in (katman_skorlari or {}).items() if v is not None}
    n = len(gecerli)
    if n < ASGARI_KATMAN:
        return {"karar": "BEKLE", "toplam": None, "gecerli_katman": n}
    toplam = sum(gecerli.values())
    if toplam <= DIKKAT_ESIGI:
        karar = "DIKKAT ET"
    elif toplam >= EKLE_ESIGI:
        karar = "EKLE"
    else:
        karar = "TUT"
    return {"karar": karar, "toplam": toplam, "gecerli_katman": n}


def sema_sinifi(layer_scores: Optional[dict]) -> str:
    """Kaydin hangi kayit turune ait oldugunu soyler.

    decision_log alti farkli sema tasiyor; hepsini ayni sayip "replay
    basarisiz" demek yaniltici olurdu.
    """
    if not isinstance(layer_scores, dict) or not layer_scores:
        return "katman_skoru_yok"
    anahtarlar = set(layer_scores)
    if set(KATMANLAR) <= anahtarlar:
        return "maa_5_katman"
    if set(ESKI_KATMANLAR) <= anahtarlar:
        return "maa_4_katman_eski"
    if "market_regime" in anahtarlar or "target_portfolio" in anahtarlar:
        return "portfoy_sinyali"
    if "master_model" in anahtarlar or "analyst_model" in anahtarlar:
        return "llm_kaskadi"
    if "all_checks_clear" in anahtarlar:
        return "god_mode"
    return "bilinmeyen_sema"


REPLAY_EDILEBILIR = ("maa_5_katman", "maa_4_katman_eski")


def kayit_replay(kayit: dict) -> dict:
    """Tek bir decision_log satirini yeniden oynatir ve kayitla karsilastirir.

    kayit: {"id","ticker","decision","total_score","layer_scores"}
    """
    sinif = sema_sinifi(kayit.get("layer_scores"))
    temel = {"id": kayit.get("id"), "ticker": kayit.get("ticker"),
             "sema": sinif, "kayitli_karar": kayit.get("decision")}
    if sinif not in REPLAY_EDILEBILIR:
        return {**temel, "durum": "replay_edilemez", "uretilen_karar": None,
                "gerekce": (f"Bu kayit '{sinif}' turunde; katman skoru tasimadigi "
                            f"icin karar yeniden uretilemez. Bu bir BASARISIZLIK "
                            f"DEGIL, kapsam disidir.")}
    skorlar = {k: v for k, v in kayit["layer_scores"].items() if k in KATMANLAR}
    u = karar_uret(skorlar)
    karar_uydu = (u["karar"] == kayit.get("decision"))
    kayitli_toplam = kayit.get("total_score")
    if kayitli_toplam is not None:
        try:
            kayitli_toplam = float(kayitli_toplam)
        except (TypeError, ValueError):
            kayitli_toplam = None
    toplam_uydu = ((u["toplam"] is None and kayitli_toplam is None) or
                   (u["toplam"] is not None and kayitli_toplam is not None
                    and abs(float(u["toplam"]) - kayitli_toplam) < 1e-9))
    return {**temel, "uretilen_karar": u["karar"], "uretilen_toplam": u["toplam"],
            "kayitli_toplam": kayitli_toplam, "gecerli_katman": u["gecerli_katman"],
            "durum": "uydu" if (karar_uydu and toplam_uydu) else "uymadi",
            "karar_uydu": karar_uydu, "toplam_uydu": toplam_uydu,
            "gerekce": "" if (karar_uydu and toplam_uydu) else
                       (f"kayitli={kayit.get('decision')}/{kayitli_toplam} "
                        f"uretilen={u['karar']}/{u['toplam']}")}


def toplu_replay(kayitlar: list) -> dict:
    """Tum kayitlari oynatir ve DURUST bir ozet uretir.

    Basari orani YALNIZCA replay edilebilir kayitlar uzerinden hesaplanir;
    kapsam disi kayitlari paydaya koymak orani yapay olarak dusururdu,
    paydan cikarip gormezden gelmek ise kapsami gizlerdi. Ikisi de AYRI
    raporlanir.
    """
    sonuclar = [kayit_replay(k) for k in kayitlar]
    edilebilir = [s for s in sonuclar if s["durum"] != "replay_edilemez"]
    uyan = [s for s in edilebilir if s["durum"] == "uydu"]
    sema_sayimi: dict = {}
    for s in sonuclar:
        sema_sayimi[s["sema"]] = sema_sayimi.get(s["sema"], 0) + 1
    return {
        "toplam_kayit": len(sonuclar),
        "replay_edilebilir": len(edilebilir),
        "kapsam_disi": len(sonuclar) - len(edilebilir),
        "uyan": len(uyan),
        "uymayan": len(edilebilir) - len(uyan),
        "sadakat_orani": (len(uyan) / len(edilebilir)) if edilebilir else None,
        "sema_dagilimi": sema_sayimi,
        "uymayanlar": [s for s in edilebilir if s["durum"] == "uymadi"],
        "not": ("Sadakat orani YALNIZCA katman skoru tasiyan kayitlar uzerinden "
                "hesaplanir. Kapsam disi kayitlar ayri sayilir; basarisizlik "
                "olarak sayilmaz ama gizlenmez de."),
    }


def kural_kapsamasi(kayitlar: list) -> dict:
    """Gercek verinin kuralin HANGI dallarini sinadigini olcer.

    NEDEN GEREKLI: "%100 sadakat" tek basina yaniltici bir sayidir. Eger
    veri kuralin yalnizca iki dalini geziyorsa, oteki dallar hic dogrulanmis
    olmaz — ama oran yine %100 gorunur. Olculen (09.09.2026 dokumu): uretim
    verisinde HICBIR karar negatif toplam skor almamis, dolayisiyla
    DIKKAT ET dali gercek veriyle hic sinanmamistir; yalnizca birim
    testleriyle kapsanmaktadir. Bu, gizlenmesi degil raporlanmasi gereken
    bir bosluktur.
    """
    dallar = {"EKLE": 0, "TUT": 0, "BEKLE": 0, "DIKKAT ET": 0}
    for k in kayitlar:
        if sema_sinifi(k.get("layer_scores")) not in REPLAY_EDILEBILIR:
            continue
        s = kayit_replay(k)
        if s["uretilen_karar"] in dallar:
            dallar[s["uretilen_karar"]] += 1
    sinanmayan = [d for d, n in dallar.items() if n == 0]
    return {
        "dal_sayimi": dallar,
        "sinanmayan_dallar": sinanmayan,
        "tam_kapsam": not sinanmayan,
        "uyari": ("" if not sinanmayan else
                  "Gercek veri su karar dallarini HIC sinamadi: "
                  + ", ".join(sinanmayan)
                  + ". Bu dallar yalnizca birim testleriyle kapsanmaktadir; "
                    "sadakat orani onlar hakkinda BILGI VERMEZ."),
    }
