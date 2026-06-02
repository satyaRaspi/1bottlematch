# ML-Assisted Feature Extraction — v1.5.7

This version adds lightweight CPU-only ML-assisted feature extraction while keeping the physical signature engine as the core.

## Added methods

- K-means dominant color clustering
- ORB keypoint density
- Laplacian texture complexity
- Gradient histogram profiles
- Cross-view shape consistency
- Cross-view color consistency
- Capture quality scoring
- ML-assisted feature vector similarity gate

## Principle

```text
Physical Signature Engine = Source of Truth
ML-Assisted Feature Extraction = Supporting Intelligence
```

The Controlled Geometry Gate remains the primary hard-gate. ML cannot override geometry, color, primary identity, or exact identifier failures.

## New endpoint

```text
GET /ml/status
```

## Railway

Deployment remains the same: backend service root `/backend`, frontend service root `/frontend`.
