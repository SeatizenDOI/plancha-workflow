import pandas as pd
from pathlib import Path

TXT_FILE = "/media/bioeos/E/2021_plancha_session/20210310_REU-HERMITAGE_MASK-1_01/GPS/DEVICE/2021-03-10_Thomas_Hermitage_COOOL2.txt"
LLH_FILE = TXT_FILE.replace(".txt", ".LLH")

df = pd.read_csv(TXT_FILE, sep=",")

df.to_csv(LLH_FILE, sep=" ", header=False, index=False)