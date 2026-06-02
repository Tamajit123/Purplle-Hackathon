# Resource Migration Notes

The challenge resources changed after the email update. The codebase was adjusted to match the new file set:

- `data/POS_transactions.csv`
- `data/Store 1.zip`
- `data/Store 2.zip`
- `data/evaluation_framework.pdf`

## Exact Code Changes

### 1. Transaction file path

File: [app/core/settings.py](</D:\purplle hackathon\app\core\settings.py>)

Change the default transaction path to:

```python
data/POS_transactions.csv
```

### 2. Transaction parser

File: [app/services/transactions.py](</D:\purplle hackathon\app\services\transactions.py>)

The new POS file only has:

- `order_id`
- `order_date`
- `order_time`
- `store_id`
- `product_id`
- `brand_name`
- `total_amount`

So the parser now uses:

- `order_id` for unique orders
- `brand_name` for brand mix
- `store_id` for store mix
- `order_time` for hourly rhythm
- `total_amount` for revenue

Old fields such as `dep_name` and `salesperson_name` are no longer assumed.

### 3. Store archive handling

File: [app/services/resources.py](</D:\purplle hackathon\app\services\resources.py>)

The old single-layout workbook assumption was replaced with store archive discovery:

- `data/Store 1.zip`
- `data/Store 2.zip`

The service now:

- discovers all `Store *.zip` archives
- extracts each layout PNG into `dashboard/assets/stores/...`
- lists the camera MP4 files inside each archive
- returns both stores in the `/insights` payload

### 4. Dashboard display

Files:

- [dashboard/index.html](</D:\purplle hackathon\dashboard\index.html>)
- [dashboard/app.js](</D:\purplle hackathon\dashboard\app.js>)
- [dashboard/styles.css](</D:\purplle hackathon\dashboard\styles.css>)

The dashboard now shows:

- Purplle-branded hero
- live KPI cards
- funnel
- anomaly panel
- store layout image
- camera inventory from the store archives
- brand mix and hourly rhythm
- store-package resource cards
- evaluation readiness

### 5. CCTV processing

File: [scripts/process_cctv.py](</D:\purplle hackathon\scripts\process_cctv.py>)

The processing script now works from a store archive and extracts it locally before scanning a clip.

## Docker Updates

Files:

- [Dockerfile](</D:\purplle hackathon\Dockerfile>)
- [docker-compose.yml](</D:\purplle hackathon\docker-compose.yml>)

The build now copies:

- `data/POS_transactions.csv`
- `data/Store 1.zip`
- `data/Store 2.zip`

## Important Note

If you are running from an old local event log, delete `data/events/events.jsonl` once before a fresh demo so the startup seed is regenerated from the updated POS file.
