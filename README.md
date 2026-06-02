# Truflux Bottle Signature Core v1.5.7

A working prototype for physical-signature based bottle identification.

## What this build does

1. Builds a physical signature for a bottle using:
   - Required front image
   - Required side image
   - Required top image
   - Optional calibrated measurements are supported but not required

2. Registers master bottle signatures into SQLite.

3. Identifies an unknown bottle by recreating the signature and matching against the master repository using:
   - 50+ parameter schema
   - Parameter-level tolerance
   - Weighted similarity scoring
   - Match decision: Confirmed / High Confidence / Review / Suspicious / No Match

## Architecture

```text
Node.js UI
   ↓
Python FastAPI Backend
   ↓
Image Feature Extraction + Manual Measurements
   ↓
Bottle Signature Vector
   ↓
SQLite Signature Repository
   ↓
Tolerance-Based Weighted Matching Engine
```

## Folder Structure

```text
bottle-signature-core-v1.5.7/
  backend/
    main.py
    image_features.py
    matcher.py
    database.py
    signature_schema.py
    requirements.txt
  frontend/
    server.js
    package.json
    public/
      index.html
      app.js
      styles.css
  docs/
    API_TESTS.md
  start_backend.bat
  start_frontend.bat
  start_backend_mac.sh
  start_frontend_mac.sh
```

## Run Steps - Windows

### 1. Start Backend

Open Command Prompt in the project folder:

```bat
start_backend.bat
```

Backend runs at:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

### 2. Start Frontend

Open another Command Prompt:

```bat
start_frontend.bat
```

Frontend runs at:

```text
http://localhost:3000
```

## Run Steps - Mac / Linux

### 1. Start Backend

```bash
chmod +x start_backend_mac.sh
./start_backend_mac.sh
```

### 2. Start Frontend

```bash
chmod +x start_frontend_mac.sh
./start_frontend_mac.sh
```

## How to Use

### Step 1: Register Master Bottle

Use the "Register Master Bottle Signature" form.

Minimum:
- Brand
- Product name
- Front image
- Side image
- Top image

No optional physical measurements are required.

The 3-axis photos are the required core input. Advanced users may add height, width, weight, quantity and neck diameter, but these fields are optional.

### Step 2: Identify Bottle

Use the "Identify Bottle" form.

Upload fresh front, side and top bottle images. Optional measurements are hidden under Advanced inputs and are not required.

The system will return:
- Best match
- Match score
- Decision
- Parameter-level comparison

## Production Upgrade Notes

This is a core prototype. For production use, upgrade the measurement layer using:
- Calibrated cameras
- Reference marker in frame
- Depth camera
- Load cell
- Fixed lighting booth
- Polarized glass reflection control
- Barcode/excise scanner
- Camera calibration matrix
- Controlled SKU onboarding workflow


## v1.5.7 Change

This version removes the requirement for optional physical parameters from the normal workflow.

The user can now:
- Register a bottle using brand, product name, and at least one image.
- Identify a bottle using at least one image.
- Ignore all advanced physical measurement fields.

Advanced measurements are still available in a collapsed section for future calibrated deployments.

## v1.5.7 Change

This version confirms the intended product flow:

- 3-axis photos are required for both registration and identification.
- Front photo, side photo and top photo must be uploaded.
- Optional physical measurement parameters are not required in the normal UI flow.
- Advanced measurements remain available in a collapsed section for calibrated deployments.

Normal input model:

```text
Brand + Product Name + Front Photo + Side Photo + Top Photo
```

Identification input model:

```text
Front Photo + Side Photo + Top Photo
```


## v1.5.7 Fix

Fixed registration error when optional parameters are left blank.

What changed:
- The frontend now removes blank optional fields before sending the form.
- The API now handles optional measurement fields more safely.
- Error messages are displayed in readable text instead of `[object Object]`.

Normal registration remains:

```text
Brand + Product Name + Front Photo + Side Photo + Top Photo
```

No optional measurement values are required.


## v1.5.7 Change

Operational and decision-rule update:

1. All major actions are logged in SQLite audit logs:
   - Register bottle
   - Identify bottle
   - Compare bottle
   - List bottle signatures
   - Delete bottle
   - Clear logs

2. Suspicious review is now treated as `NO_MATCH`.

3. Any score below 85% is now `NO_MATCH`.

4. Color mismatch is now a hard `NO_MATCH` rule.

The UI includes an Audit Logs section with refresh and clear actions.


## v1.5.7 Change — Tightened Match Algorithm

The matching engine is now stricter and more suitable for controlled customer demonstrations.

New rules:

1. Minimum score increased from 85% to 90%.

2. Minimum comparable parameters required:
   - At least 24 comparable parameters must be available.

3. Primary identity gate added:
   - Key bottle-shape, neck, cap, label geometry, base, quantity and identifier parameters must pass at an 82% rate.

4. Category gate added:
   - Each comparable signature category must maintain at least a 70% pass rate where enough parameters exist.

5. Color gate tightened:
   - Color mismatch threshold reduced.
   - Color pass-rate logic added.

6. Exact identifier gate added:
   - Barcode/SKU hash mismatch becomes hard `NO_MATCH` when provided on both sides.
   - Quantity mismatch beyond 1% becomes hard `NO_MATCH`.

7. Stricter parameter scoring:
   - Out-of-tolerance parameters now decay faster.
   - Primary identity tolerances are tightened at runtime.

Possible decisions remain:

```text
CONFIRMED_MATCH
MATCH
NO_MATCH
```

Suspicious/review-level outcomes continue to be treated as `NO_MATCH`.


## v1.5.7 Change — Targeted Bottle Comparison

The Identify Bottle frame now includes a dropdown of all registered bottle signatures.

New flow:

```text
Select registered bottle
      ↓
Upload front + side + top photos of bottle to be checked
      ↓
Compare only against selected registered bottle
      ↓
Return MATCH / CONFIRMED_MATCH / NO_MATCH
```

This is different from reverse lookup across all bottles. The backend still has `/identify` for reverse lookup, but the UI now uses `/compare/{bottle_id}` for customer-friendly targeted verification.


## v1.5.7 Change — Processing Dialog

The Compare and Determine Match flow now opens a processing dialog.

The dialog shows:

- Processing stages
- 3-axis input validation
- Signature recreation stage
- Master signature comparison stage
- Gate checks
- Final decision
- Match score
- No-match reasons
- Parameter-by-parameter comparison
- Pass/fail status for each calculated parameter
- Close button

This makes the match process visible to the customer during demonstrations.


## v1.5.7 Change — Processing Match Storage and Dialog Close Fix

1. Fixed the Processing Bottle Match dialog close button.

2. Added persistent Processing Bottle Match records.

Every comparison now generates a unique ID:

```text
PBM-XXXXXXXXXX
```

Stored data includes:

- Processing Bottle Match ID
- Selected registered bottle ID
- Brand and product name
- Final decision
- Match score
- Compared parameter count
- No-match reasons
- Request details
- Observed live signature
- Gate results
- Parameter-by-parameter pass/fail details
- Full comparison result JSON

New API endpoints:

```text
GET /processing-matches
GET /processing-matches/{processing_match_id}
```

The UI now includes a Processing Bottle Match Records table.


## v1.5.7 Change — Audit Log Processing Match Hyperlink

Audit Logs now show a clickable Processing Bottle Match ID whenever the log entry is related to a bottle comparison.

Example:

```text
Processing Bottle Match: PBM-XXXXXXXXXX
```

Clicking the ID opens the processing dialog and displays:

- Stored processing match ID
- Final decision
- Match score
- Gate results
- Parameter-by-parameter pass/fail table
- Observed signature
- Full stored JSON record

The Processing Bottle Match Records table also has clickable IDs.


## v1.5.7 Change — Controlled Geometry Gate

This version adds the controlled capture logic into the match engine.

Assumption:

```text
Same camera height
Same camera distance
Same background
Same lighting
Same bottle placement
Same 3-axis setup
```

New match feature:

```text
Controlled Geometry Gate
```

The Controlled Geometry Gate compares fixed-capture geometric parameters such as:

- Height in pixels
- Width in pixels
- Aspect ratio
- Contour extent
- Solidity
- Perimeter
- Top width ratio
- Middle width ratio
- Bottom width ratio
- Shoulder slopes
- Symmetry score
- Neck height ratio
- Shoulder height ratio
- Cap width ratio
- Cap height ratio
- Label geometry
- Base width ratio
- Side profile
- Top circularity

Decision rule:

```text
If Controlled Geometry Gate fails = NO_MATCH
```

This improves detection of:

- Wrong bottle shape
- Same label on wrong bottle
- Reused bottle
- Counterfeit packaging
- Wrong SKU size
- Wrong cap or neck structure

The processing dialog, audit-linked dialog and stored processing match records now include the Controlled Geometry Gate result.


## GitHub and Railway Deployment Ready — v1.5.7

This package has been prepared for GitHub and Railway deployment.

Added:

- Root `.gitignore`
- `backend/railway.json`
- `backend/Procfile`
- `backend/start.sh`
- `frontend/railway.json`
- `frontend/Procfile`
- `frontend/start.sh`
- `frontend/.env.example`
- `backend/.env.example`
- `docs/GITHUB_UPLOAD.md`
- `docs/RAILWAY_DEPLOYMENT.md`

Railway deployment model:

```text
Service 1: Backend
Root Directory: /backend
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

Service 2: Frontend
Root Directory: /frontend
Start Command: npm start
Environment Variable:
API_TARGET=https://your-backend-service.up.railway.app
```

Important: the app currently uses SQLite. For production Railway deployment, migrate to PostgreSQL or attach persistent storage to avoid losing data on redeploy.


## v1.5.7 — Physical Signature Engine + ML-Assisted Feature Extraction

This version adds lightweight ML-assisted feature extraction while keeping the physical signature engine as the core.

Added:

- K-means dominant color clustering
- ORB keypoint density
- Texture complexity
- Gradient histogram profiles
- Cross-view shape consistency
- Cross-view color consistency
- Capture quality scoring
- ML-assisted feature vector similarity
- ML-assisted gate in the matching engine
- `/ml/status` API endpoint
- ML gate results in Processing Bottle Match dialog and stored records

Important:

```text
ML assists feature extraction.
ML does not replace the controlled physical signature engine.
Controlled Geometry Gate remains the primary hard-gate.
```


## v1.5.7 — Light Deep-Learning Segmentation

Added optional ONNX Runtime CPU segmentation with OpenCV GrabCut fallback.

New endpoint:

```text
GET /dl/status
```

New matching result:

```text
dl_segmentation_gate
```

The DL layer assists object isolation and mask quality. The controlled physical signature engine remains the primary source of truth.


## v1.5.7 — Overlay Visualization + Real Model DL Segmentation

Added:
- Image overlay visualization for registered and observed bottle views
- Persistent overlay asset generation under `backend/assets/`
- Static asset serving from the backend
- Real model segmentation support through Ultralytics YOLO segmentation or ONNX
- `backend/requirements_real_dl.txt` for optional real-model dependencies
- Overlay assets stored with bottle records and processing bottle match records

New capabilities:
- Visual explanation of segmentation mask, contour, label region, cap region and body region
- Comparison of registered bottle overlay vs observed bottle overlay in the processing dialog
- Real segmentation model mode using:
  - `BOTTLE_SEGMENTATION_MODEL_MODE=ultralytics`
  - or `BOTTLE_SEGMENTATION_MODEL_MODE=onnx`

Without a configured model, the app continues to use OpenCV GrabCut fallback.


## v1.5.7 — Real-Time Processing Status + Preliminary Physical Gate

Added:

1. Real-time processing status frame
   - Shown inside the Processing Bottle Match dialog.
   - Scrolls automatically.
   - Shows current frontend/backend processing stages.
   - Shows backend processing trace after comparison completes.

2. Preliminary Physical Characteristics Gate
   - Observes the object-level physical characteristics of the uploaded test sample.
   - Compares them against the registered bottle before deeper gates.
   - Uses height, width, aspect ratio, contour, solidity, shoulder, neck, cap, label, base, side profile, top profile and segmentation mask geometry.

New decision rule:

```text
If Preliminary Physical Characteristics Gate fails = NO_MATCH
```

The normal decision flow is now:

```text
Input validation
  ↓
Object observation and physical characteristics extraction
  ↓
Preliminary Physical Characteristics Gate
  ↓
Controlled Geometry Gate
  ↓
Color Gate
  ↓
Primary Identity Gate
  ↓
DL Segmentation Gate
  ↓
ML-Assisted Gate
  ↓
Final MATCH / NO_MATCH
```


## v1.5.7 — Detailed Scrolling Status

The processing status feed is now more detailed.

Added:

- one status line for each uploaded-image presence check
- one status line for each segmentation-view summary
- one status line for each gate
- one status line for each parameter-level comparison
- one status line for each no-match reason
- final decision line

This makes the scrolling frame act like a transparent processing console for the user.


## v1.5.7 — Registered Bottle Dropdown Fix

Fixed the registered bottle dropdown not appearing in the Identify Bottle frame.

Fixes added:

- Defensive `/bottles` API response handling.
- Backward-compatible SQLite migration handling for `image_assets_json`.
- Robust frontend dropdown loading with visible error messages.
- Safe HTML escaping for dropdown/list values.
- Dropdown refresh after bottle registration.
- Safer frontend boot sequence.

If the dropdown still says no registered bottles, register a master bottle first and then click refresh / reload the page.


## v1.5.7 — Dropdown Loader Fix

Fixed Identify Bottle dropdown staying at `Loading registered bottles...`.

The UI now shows an error when `/api/bottles` cannot be loaded and includes a Refresh Registered Bottles button.


## v1.5.7 — OCR / Unstructured Text Matching

Added OCR text extraction and text comparison.

The system now:

- extracts text from registered bottle images
- stores extracted text as unstructured data
- extracts text from observed/test sample images during comparison
- compares registered text vs observed text
- calculates text match percentage
- shows OCR text comparison in the Processing Bottle Match dialog
- stores OCR data in Processing Bottle Match records

New endpoint:

```text
GET /ocr/status
```

Optional OCR install:

```bash
pip install -r backend/requirements_ocr.txt
```

For pytesseract, install the system Tesseract binary as well.

Decision rule:

```text
If OCR text is available and text similarity is below threshold = NO_MATCH
```


## v1.5.7 — Strict Mismatch Fix

This version fixes a false-positive risk where two visually different objects could pass too many generic ratio checks.

Added:

- Distinctive Object Appearance Gate
- opaque surface score
- transparent surface score
- yellow dominance score
- body saturation score
- whole-object saturation score
- tighter color/appearance tolerances
- non-constant label ratio detection from actual image edges

Important:
A transparent soda bottle and an opaque yellow bottle should now fail early as `NO_MATCH`.


## v1.5.7 — Dropdown UI Visibility Fix

Fixed the Identify Bottle selector area where only the label and Refresh Registered Bottles button appeared.

Changes:
- Dedicated visible selector block.
- Forced select visibility in CSS.
- Added status text under dropdown.
- Added clearer guard when no bottle is selected.


## v1.5.7 — Create Demo Data Button

Added a Create Demo Data button.

It creates three synthetic registered bottle records:

- Demo Kinley — Clear Strong Soda Bottle
- Demo Cello — Yellow Opaque Flask Bottle
- Demo Amber — Amber Liquor Style Bottle

New endpoint:

```text
POST /demo/create
```

After demo data is created, the registered bottle dropdown refreshes automatically.


## v1.5.7 — Fast Mode Performance Optimization

The app now defaults to Fast Mode.

Performance changes:

- OCR enabled by default.
- Real DL model loading disabled by default.
- Image processing resized to max 720px by default.
- Detailed per-parameter status trace disabled by default.
- Overlay generation remains on, but can be disabled.

Environment variables:

```text
BOTTLE_PROCESSING_MODE=fast
MAX_IMAGE_DIM=720
ENABLE_OCR=true
ENABLE_OVERLAYS=true
ENABLE_REAL_DL=false
DETAILED_PARAMETER_TRACE=false
```

For fastest mode:

```text
ENABLE_OVERLAYS=false
MAX_IMAGE_DIM=640
```

Runtime config endpoint:

```text
GET /runtime/config
```


## v1.5.7 — Register-Time Bottle Text Analysis

Added text analysis inside Register Master Bottle Signature.

New UI features:

- Analyze and store any text found on bottle images
- Analyze Bottle Text Before Registering
- Text preview and stored text summary

New backend endpoint:

```text
POST /signature/text-preview
```

The text extracted during registration is stored as unstructured data with the master bottle record and used later during bottle matching.

OCR dependencies remain optional:

```bash
pip install -r backend/requirements_ocr.txt
brew install tesseract
```


## v1.5.7 — OCR Default ON

OCR is now enabled by default.

Default:

```text
ENABLE_OCR=true
```

To turn OCR off for speed:

```text
ENABLE_OCR=false
```

OCR dependencies are still required for actual text extraction:

```bash
pip install -r backend/requirements_ocr.txt
brew install tesseract
```


## v1.5.7 — OCR Removed

OCR has been removed from the application.

This build no longer requires:

```text
pytesseract
Tesseract OCR
EasyOCR
ENABLE_OCR
```

Removed features:

- OCR text extraction
- Register-time text preview
- OCR text gate
- OCR text comparison
- OCR setup requirements

The app is now simpler and faster, focusing on physical bottle signatures, object appearance, geometry, color/material checks, ML-assisted features and overlays.
