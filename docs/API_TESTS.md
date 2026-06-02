
# API Test Examples

## Health

```bash
curl http://localhost:8000/
```

## Get Parameters

```bash
curl http://localhost:8000/parameters
```

## Register Bottle

```bash
curl -X POST http://localhost:8000/bottles/register \
  -F "brand=Demo Brand" \
  -F "product_name=Demo Whisky" \
  -F "sku_code=DEMO-750" \
  -F "quantity_ml=750" \
  -F "color=Amber" \
  -F "height_mm=292" \
  -F "width_mm=78" \
  -F "depth_mm=78" \
  -F "weight_g=1240" \
  -F "front_image=@front.jpg" \
  -F "side_image=@side.jpg" \
  -F "top_image=@top.jpg"
```

## Identify Bottle

```bash
curl -X POST http://localhost:8000/identify \
  -F "height_mm=292" \
  -F "width_mm=78" \
  -F "depth_mm=78" \
  -F "weight_g=1240" \
  -F "front_image=@front-test.jpg" \
  -F "side_image=@side-test.jpg" \
  -F "top_image=@top-test.jpg"
```
