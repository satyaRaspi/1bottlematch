# Register-Time Bottle Text Analysis — v1.5.6

This version adds a text-analysis feature to Register Master Bottle Signature.

UI additions:

- Analyze and store text checkbox
- Analyze Bottle Text Before Registering button
- Text preview panel

Backend additions:

```text
POST /signature/text-preview
```

Registration now stores OCR/unstructured text with the master bottle record when the checkbox is enabled.

The stored text is later compared with observed/test sample OCR text during bottle matching.

Note:
Fast Mode still keeps automatic OCR off by default, but the register-time checkbox forces OCR for that registration request.
For OCR to work, install:

```bash
pip install -r backend/requirements_ocr.txt
```

For pytesseract on Mac:

```bash
brew install tesseract
```
