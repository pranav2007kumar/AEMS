# Supplied ANPR models

These weights are committed to the repository so the project can be reproduced. EasyOCR's `ocr/english_g2.pth` is the standard English recognizer.

| File | Verified role | Checkpoint details |
| --- | --- | --- |
| `plate-detector.pt` | Plate bounding-box detector | Original `plate_detector.pt.zip`; a PyTorch checkpoint, YOLO11s, Ultralytics 8.4.175, one class: `number_plate`. |
| `campus-anpr.pt` | Cropped-plate text recognizer | Original `model.pt.zip`; CRNN using MobileNetV3 Large, two bidirectional LSTM layers with hidden size 128, CTC, 36 letters/digits plus blank, input 256 × 64. |

Inspection used ZIP/pickle metadata, restricted weights-only checkpoint loading and strict OCR state-dictionary matching. This verifies format and architecture, not recognition accuracy. Subsequent integration tests ran real inference on a generated plate and a 1280 × 720 camera-like frame. The supplied YOLO detector located the plate; the free EasyOCR reader returned `TN38AB1234`. This is a smoke test, not an accuracy benchmark.

The camera pipeline is implemented in `backend/camera.py`: JPEG frame → supplied YOLO11s detector → cropped plate → local EasyOCR English reader → existing audited ANPR API. The CRNN architecture is reconstructed in `plate_reader.py`, but is not the active reader because it failed the generated-plate test and its training preprocessing is unconfirmed. A guided OCR crop is used when the detector cannot locate a plate held up to a laptop. Multiple detected plates require manual review. Recognition never records a vehicle passage or bypasses physical inspection and passenger-count checks.

Inference is enabled in the non-production loopback runner when detector and downloaded English OCR weights exist; `ANPR_ENABLE_INFERENCE=0` explicitly disables it. Production requires explicit `ANPR_ENABLE_INFERENCE=1`. Installation and status checks never run recognition. Install `backend/requirements-anpr.txt`, selecting CPU PyTorch wheels if no GPU is used. The reader's original training code is needed to confirm normalization, resize interpolation and forward preprocessing before claiming camera accuracy. `ANPR_OCR_NORMALIZATION` accepts `half` (current provisional default), `unit` or `imagenet`; it must be selected from training information, not assumed from confidence scores.

The detector loads with Ultralytics `safe_only=True`; the reader loads with PyTorch `weights_only=True`. Unknown architectures/classes fail rather than falling back to unrestricted deserialization.

The browser requires a user camera permission. Start camera enables a video-only stream; frames are sent only to the local authenticated backend. Two matching automatic readings populate the editable plate field and run permission lookup. A manual edit pauses scanning; successful recognition also pauses to preserve guard corrections. Navigation or Stop camera releases the camera tracks. No camera hardware end-to-end test has been performed by the agent.
