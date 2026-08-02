#before running remove _output

import csv
from pathlib import Path

csv_path = Path.cwd()/ "map.csv"
root = Path.cwd()/ r"outputs"

with csv_path.open(newline="", encoding="utf-8-sig") as f:
    mapping = {
        row["Number"].strip(): row["X_Number"].strip()
        for row in csv.DictReader(f)
    }

for folder in root.iterdir():
    if folder.is_dir() and folder.name.endswith("_output"):
        number = folder.name.replace("_output", "")

        if number in mapping:
            new_folder = folder.with_name(f"{mapping[number]}")
            print(f"{folder.name} -> {new_folder.name}")
            folder.rename(new_folder)