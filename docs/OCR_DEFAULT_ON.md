# OCR Default On — v1.5.6

OCR is now enabled by default.

Default backend setting:

```text
ENABLE_OCR=true
```

This means the Register Master Bottle Signature flow will try to extract and store bottle text automatically, and the match process will use OCR text comparison when text is available.

To disable OCR for faster processing:

```bash
export ENABLE_OCR=false
```

OCR dependencies are still required for actual text extraction:

```bash
pip install -r backend/requirements_ocr.txt
```

For Tesseract OCR on Mac:

```bash
brew install tesseract
```
