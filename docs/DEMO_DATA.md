# Demo Data — v1.5.7

This version adds a Create Demo Data button.

It creates three synthetic registered bottle records:

1. Demo Kinley — Clear Strong Soda Bottle
2. Demo Cello — Yellow Opaque Flask Bottle
3. Demo Amber — Amber Liquor Style Bottle

Endpoint:

```text
POST /demo/create
```

The demo records help test:

- registered bottle dropdown
- strict mismatch gates
- OCR text gate
- no-match behavior
- audit logs

The records use synthetic signatures and do not require image uploads.
