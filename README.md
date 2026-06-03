# Bottle Signature Core v1.6.0 — Clean No-OCR Build

This is the cleaned no-OCR build prepared for GitHub and Railway demo deployment.

## Key Features

- Register master bottle signatures from 3-axis images
- Compare observed/test bottle against registered bottle
- Physical signature extraction
- Distinctive object appearance gate
- Preliminary physical characteristics gate
- Controlled geometry gate
- Color/material checks
- ML-assisted feature extraction
- Optional real-DL segmentation hooks
- Overlay visualization
- Demo data creation
- Processing match records and audit logs

## Removed

- OCR
- pytesseract
- Tesseract dependency
- EasyOCR
- OCR gates/text matching

## Railway Deployment

Deploy as two services from the same GitHub repository:

```text
Backend service root: /backend
Start command: uvicorn main:app --host 0.0.0.0 --port $PORT

Frontend service root: /frontend
Start command: npm start
Frontend variable: API_TARGET=https://your-backend-service.up.railway.app
```

## Recommended Railway Backend Variables

```text
BOTTLE_PROCESSING_MODE=fast
MAX_IMAGE_DIM=720
ENABLE_OVERLAYS=true
ENABLE_REAL_DL=false
DETAILED_PARAMETER_TRACE=false
```

For fastest demo performance:

```text
ENABLE_OVERLAYS=false
MAX_IMAGE_DIM=640
```

## Production Note

The current build uses SQLite for demo simplicity. For production, migrate to PostgreSQL.



## v1.6.0 — AI Capture Quality + View Validation + Object Class Detection

Added lightweight AI-assisted validation.

New features:

- AI capture-quality assistant
- front/side/top view validation
- duplicate view detection
- multiple object detection
- object class detection
- AI Capture / View / Object Class Gate
- register-time capture AI preview

New endpoint:

```text
POST /signature/capture-ai-preview
```

Detected object classes:

```text
transparent_bottle
opaque_bottle
amber_glass_bottle
yellow_opaque_bottle
can_or_carton_like
non_bottle_or_unknown
```

This helps prevent wrong comparisons before deeper matching starts.
