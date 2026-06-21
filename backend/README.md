# Backend API for Digital Café SaaS (Production-ready)

## Endpoints
- GET /api/health
- POST /process-photo  --> accepts `image` file, returns a ZIP with multiple outputs
- POST /generate-pdf   --> accepts `image` file and `layout` (single|4x6|a4), returns PDF
	- POST /process-photo parameters:
		- `format`: `jpg` or `pdf` (default `jpg`)
		- `sheet`: `6`, `12`, `4x6`, `a4` or empty for single
		- `dpi`: integer (default 300)
		- `download`: `single` to return single image/pdf, `zip` to return a ZIP with multiple outputs (default `zip`)
		- returns: `application/zip` (default) or single `image/jpeg` or `application/pdf` when requested

## Setup (local)
1. Create and activate a Python 3.10+ virtualenv
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run server for development:

```bash
FLASK_DEBUG=1 python app.py
```

## Production (gunicorn)
Render / Heroku / similar services can run the app with gunicorn. Example command:

```bash
gunicorn backend.app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120
```

Notes:
- `rembg` uses a pretrained model and increases slug size; ensure the deployment environment has enough disk and memory.
- The app uses OpenCV (headless) for face/eye detection. If more accurate landmarking/alignment is required, consider adding `dlib` or `mediapipe`.

## Security & limits
- Max upload size set via `MAX_CONTENT_LENGTH` env var (default 10 MB).
- Allowed image types: png, jpg, jpeg, webp.

