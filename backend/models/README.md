# ANPR models

Both models were trained by the project team and are committed so the results can be reproduced.

| File | Role | Details |
| --- | --- | --- |
| `plate-detector.pt` | Finds the number plate in a camera frame | Ultralytics YOLO11s, one class `number_plate`, Ultralytics 8.4.175. Trained 40 epochs at `imgsz` 640 (AdamW, lr0 0.002, batch 16, scale 0.7, mosaic 1.0, mixup 0.05). Validation: precision ≈ 0.998, recall 1.0, mAP50 0.995, mAP50-95 ≈ 0.78. Inference runs at 640. |
| `campus-anpr.pt` | Reads the plate text from a crop (**primary OCR**) | CRNN: MobileNetV3-Large backbone (stride (2,1) at blocks 7 and 13) → 1×1 conv + BatchNorm + Hardswish → two feature rows joined into a 64-step sequence → 2-layer BiLSTM(128) → Linear(256, 37), CTC over `0-9A-Z` (blank = 0). |
| `ocr/english_g2.pth` | EasyOCR English recognizer | **Fallback only**, used when the CRNN finds no valid plate. |

## CRNN input and decoding (must match training)

- RGB crop resized to **64 high × 256 wide** (`INTER_AREA` if wider than 256, else `INTER_LINEAR`), no aspect-ratio padding.
- Divide by 255, subtract mean `[0.485, 0.456, 0.406]`, divide by std `[0.229, 0.224, 0.225]`, CHW.
- Greedy CTC: argmax per step, collapse repeats, drop blanks. Confidence = mean of the max softmax over the kept characters.

This is implemented in `backend/plate_reader.py` and mirrors `train_mobilenet_ocr_kaggle.ipynb`.

Held-out results from training: exact plate match 96.9 % on clean real crops and 89.8 % with synthetic weather (fog, rain, overcast/blur).

## How the camera pipeline uses them (`backend/camera.py`)

JPEG frame → YOLO11s detector → plate box → CRNN reader. The reader looks at the detector's own box and a few padded/stretched views of it, and the readings vote. A read must be a valid Indian plate format with confidence ≥ 0.5, otherwise EasyOCR is tried. Overlapping boxes on one plate are merged; several different plates in one frame, or no valid read, go to manual review. The result is passed to the audited ANPR API. **Recognition never records passage** and never replaces the guard's check, physical inspection or people count.

## Loading and safety

The detector loads with Ultralytics `safe_only=True` and the reader with `torch.load(weights_only=True)`. Unknown classes or architectures are rejected. Inference starts only when `ANPR_ENABLE_INFERENCE=1` (the local runner turns it on when the weights exist); status checks and imports never load a model. Install `backend/requirements-anpr.txt` (CPU PyTorch wheels are fine).

## Measured here (not a benchmark)

On 30 generated plates (varied states, 7 fonts, three sizes, blur, tilt up to 7°) the full pipeline read 25 exactly and the detector found the plate in all 30. On the bundled 1280×720 test frame it reads `TN38AB1234` at 0.99 confidence in about 0.6 s after the first (model-loading) request. These are synthetic plates, not real gate footage; accuracy on real vehicles still needs a labelled test set.
