# Registered Bottle Dropdown Troubleshooting — v1.5.7

If the Identify Bottle dropdown does not show registered bottles:

1. Confirm backend is running:

```text
http://localhost:8000
```

2. Confirm the API returns bottles:

```text
http://localhost:8000/bottles
```

3. Confirm frontend proxy works:

```text
http://localhost:3000/api/bottles
```

4. Register one master bottle first.

5. Refresh the frontend page.

This version includes defensive fixes so `/bottles` errors are displayed in the UI instead of silently leaving the dropdown empty.
