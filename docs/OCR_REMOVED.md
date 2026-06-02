# OCR Removed — v1.5.7

OCR has been removed from this build.

Removed:

- pytesseract dependency
- Tesseract system dependency
- EasyOCR dependency
- OCR registration preview
- OCR text gate
- OCR text comparison
- `/ocr/status`
- `/signature/text-preview`

Reason:

OCR added environment complexity and slowed processing. The app now focuses on:

- physical signature generation
- object appearance gates
- geometry matching
- color/material matching
- ML-assisted features
- optional overlay visualization
- demo data

No Tesseract installation is required in this build.
