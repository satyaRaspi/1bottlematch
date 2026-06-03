# Registered Bottle Dropdown Fix — v1.6.0

This version fixes the dropdown staying at "Loading registered bottles..."

Fixes:
- Added `/config.js` runtime frontend config.
- Added API timeout handling.
- Added visible dropdown error states.
- Added Refresh Registered Bottles button.
- Made `/bottles` backend response defensive.

Test:
```text
http://localhost:8000/bottles
http://localhost:3000/api/bottles
```
