def score_explanation():
    return {
        "EKLE": "Skor >= 4: Coklu katmanlarda (Teknik/Temel/Risk/Duygu) guclu pozitif konfluans var.",
        "TUT": "Skor -3 ile 3 arasi: Karisik veya notr sinyaller, net bir yon yok.",
        "DIKKAT ET": "Skor <= -3: Coklu katmanlarda negatif sinyal birikimi var, risk artmis.",
        "BEKLE": "4 veri katmanindan (TAA/FAA/RAA/SAA) 3'ten azi yanit verdi, Confluence over Confidence prensibi geregi karar verilemiyor.",
    }
