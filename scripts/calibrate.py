"""Calibrate decision thresholds against the dataset ground truth.

Runs decision.decide_from_text() on the trayectorias dataset and compares
with label_ground_truth. Prints confusion matrix and recall of "rojo".
"""
import sys
from pathlib import Path
from collections import Counter
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.decision import decide_from_text

DATA = Path(__file__).resolve().parents[1] / "dataset" / "trayectorias_postop_silver.xlsx"


def main() -> None:
    wb = load_workbook(DATA, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows:
        print("No data found")
        return

    header = ["trayectoria_id", "paciente_id", "dia_postop", "dolor", "fiebre",
              "movilidad", "estado_herida", "apetito", "sueno",
              "arquetipo_recuperacion", "label_ground_truth"]
    gt_col = header.index("label_ground_truth")

    confusion = Counter()
    correct = 0
    rojo_recall_correct = 0
    rojo_total = 0

    for row in rows:
        if not row or not row[gt_col]:
            continue
        gt = str(row[gt_col]).strip().lower()
        if gt not in ("verde", "amarillo", "rojo"):
            continue
        text = " ".join(str(c) for c in row[1:gt_col] if c is not None)
        result = decide_from_text(text)
        pred = result["label"]
        confusion[(gt, pred)] += 1
        if pred == gt:
            correct += 1
        if gt == "rojo":
            rojo_total += 1
            if pred == "rojo":
                rojo_recall_correct += 1

    total = sum(confusion.values())
    print(f"\nTotal cases: {total}")
    print(f"Accuracy: {correct/total:.2%}" if total else "")
    if rojo_total:
        print(f"Recall 'rojo': {rojo_recall_correct/rojo_total:.2%} ({rojo_recall_correct}/{rojo_total})")

    print("\nConfusion matrix (rows=ground truth, cols=predicted):")
    print(f"{'':12s} {'verde':>8s} {'amarillo':>10s} {'rojo':>8s}")
    for gt in ("verde", "amarillo", "rojo"):
        row = [confusion.get((gt, p), 0) for p in ("verde", "amarillo", "rojo")]
        print(f"{gt:12s} {row[0]:>8d} {row[1]:>10d} {row[2]:>8d}")


if __name__ == "__main__":
    main()
