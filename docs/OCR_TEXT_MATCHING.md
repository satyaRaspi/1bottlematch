# OCR Text Matching — v1.5.6

This version extracts text from front/side/top bottle images and stores it as unstructured text data.

Optional OCR engines:

- pytesseract
- easyocr

Install optional OCR dependencies:

```bash
pip install -r backend/requirements_ocr.txt
```

For pytesseract, also install the system Tesseract binary.

New API:

```text
GET /ocr/status
```

Stored data:

- registered bottle OCR text
- observed comparison OCR text
- text match percentage
- matched tokens
- missing tokens
- new tokens

Decision rule:

If OCR text is available on both sides and similarity is below threshold, the result becomes `NO_MATCH`.
