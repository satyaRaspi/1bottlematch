# Dropdown UI Visibility Fix — v1.6.0

This patch forces the registered bottle dropdown to remain visible in the Identify Bottle frame.

Fixes:
- replaced nested label/select layout with a dedicated selector block
- added visible status text under the dropdown
- forced select display/visibility through CSS
- added explicit loaded/error/warning status states
- added comparison guard if no bottle is selected

If the dropdown still has no options:
1. register a master bottle
2. open `http://localhost:8000/bottles`
3. open `http://localhost:3000/api/bottles`
4. click Refresh Registered Bottles
