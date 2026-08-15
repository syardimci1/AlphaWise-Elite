#!/bin/bash
# Model B egitimi + IC hesaplamasini TEK SEFERDE, sirayla yapar.
LOG="/app/models/full_checkpoint.txt"
echo "[1/2] Model B egitimi baslıyor $(date)" > $LOG
MLFLOW_ALLOW_FILE_STORE=true python3 /app/data_prep/train_lightgbm_alpha360.py >> $LOG 2>&1
echo "[2/2] IC hesaplamasi basliyor $(date)" >> $LOG
python3 /app/data_prep/compare_models.py >> $LOG 2>&1
echo "TAMAMLANDI $(date)" >> $LOG
