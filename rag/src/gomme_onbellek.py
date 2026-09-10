"""Sorgu gommesi onbellegi — olculen darbogaz burasi.

NEDEN (madde 48, Qdrant degerlendirmesi)
========================================
Qdrant'a gecmenin gerekcesi arandi ve OLCULDU (10.09.2026,
alphawise_knowledge koleksiyonu, 14.329 kayit):

    GOMME (sentence-transformers)  medyan 521 ms   -> toplam surenin %97'si
    VEKTOR ARAMA (ChromaDB)        medyan  14 ms   -> toplam surenin %3'u

Yani sorgu suresinin %97'si sorgu METNINI VEKTORE CEVIRMEKTE geciyor,
yalnizca %3'u ChromaDB'nin arama isinde. Qdrant o %3'u hedefler ve
gommeyi O DA YAPMAZ; degistirmek olculebilir bir kazanc saglamazdi.
Gercek kazanc, ayni metnin tekrar tekrar gommelenmesini onlemekte.

NEDEN REDIS DEGIL
=================
rag servisinde Redis ne ortam degiskeni ne de bagimlilik olarak var.
Tek sureclik bir servis icin surec-ici sinirli onbellek ayni kazanci
bagimlilik eklemeden veriyor. Bedeli acikca soylenir: onbellek yeniden
baslatmada KAYBOLUR ve kopyalar arasinda PAYLASILMAZ.

MODEL KIMLIGI ANAHTARIN PARCASIDIR
==================================
Gomme modeli degisirse eski vektorler SESSIZCE yanlis sonuc uretir.
Surum etiketine guvenmek yerine model, sabit bir deneme metninin
gommesinden turetilen bir PARMAK IZIYLE tanimlanir: model degisirse
parmak izi kendiliginden degisir ve onbellek gecersizlesir. Kimsenin
bir surum numarasini elle artirmasi gerekmez.
"""
from __future__ import annotations

import hashlib
from collections import OrderedDict

# Model parmak izi icin sabit deneme metni. DEGISTIRILMEMELI —
# degisirse tum onbellek gereksiz yere gecersizlesir.
DENEME_METNI = "alphawise gomme modeli parmak izi"

VARSAYILAN_KAPASITE = 512


class GommeOnbellegi:
    """Sinirli boyutlu, model parmak izine bagli gomme onbellegi."""

    def __init__(self, gomme_fn, kapasite: int = VARSAYILAN_KAPASITE):
        if not callable(gomme_fn):
            raise TypeError("gomme_fn cagrilabilir olmali")
        if kapasite < 1:
            raise ValueError("kapasite en az 1 olmali")
        self._fn = gomme_fn
        self._kapasite = kapasite
        self._depo: OrderedDict = OrderedDict()
        self._parmak_izi = None
        self.isabet = 0
        self.iska = 0

    # ------------------------------------------------------ parmak izi
    def parmak_izi(self) -> str:
        """Modelin kimligi: sabit bir metnin gommesinin ozeti."""
        if self._parmak_izi is None:
            v = self._fn([DENEME_METNI])[0]
            ham = ",".join(f"{float(x):.6f}" for x in v)
            self._parmak_izi = hashlib.sha256(ham.encode()).hexdigest()[:16]
        return self._parmak_izi

    def _anahtar(self, metin: str) -> str:
        return (self.parmak_izi() + ":"
                + hashlib.sha256(metin.encode("utf-8")).hexdigest())

    # ---------------------------------------------------------- kullanim
    def gom(self, metin: str):
        """Metnin gommesini dondurur; ayni metin ikinci kez hesaplanmaz."""
        if not isinstance(metin, str):
            raise TypeError(f"metin str olmali, {type(metin).__name__} geldi")
        a = self._anahtar(metin)
        if a in self._depo:
            self._depo.move_to_end(a)
            self.isabet += 1
            return self._depo[a]
        v = self._fn([metin])[0]
        self.iska += 1
        self._depo[a] = v
        self._depo.move_to_end(a)
        while len(self._depo) > self._kapasite:
            self._depo.popitem(last=False)      # en eski kullanilan atilir
        return v

    def bosalt(self):
        self._depo.clear()
        self._parmak_izi = None

    def durum(self) -> dict:
        toplam = self.isabet + self.iska
        return {
            "kapasite": self._kapasite,
            "dolu": len(self._depo),
            "isabet": self.isabet,
            "iska": self.iska,
            # Hic sorgu yapilmadiysa oran SIFIR DEGIL, None: "olculemedi"
            # ile "hic isabet yok" ayni sey degildir.
            "isabet_orani": round(self.isabet / toplam, 4) if toplam else None,
            "model_parmak_izi": self._parmak_izi,
            "not": ("Surec-ici onbellek: yeniden baslatmada KAYBOLUR ve "
                    "kopyalar arasinda PAYLASILMAZ."),
        }
