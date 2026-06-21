import os
import io
import zipfile
import traceback
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import numpy as np
import cv2

try:
    from rembg import remove as rembg_remove
except Exception:
    rembg_remove = None

app = Flask(__name__)
CORS(app)
@app.route("/")
def home():
    return render_template("index.html")
# Production-ready limits and settings
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))  # 10 MB default
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def pil_from_bytes(b: bytes) -> Image.Image:
    return Image.open(io.BytesIO(b)).convert('RGBA')


def bytes_from_pil(img: Image.Image, fmt='JPEG', quality=95, dpi=300) -> bytes:
    buf = io.BytesIO()
    save_kwargs = {}
    if dpi:
        save_kwargs['dpi'] = (dpi, dpi)
    if fmt.upper() == 'JPEG':
        rgb = img.convert('RGB')
        rgb.save(buf, format='JPEG', quality=quality, optimize=True, **save_kwargs)
    else:
        img.save(buf, format=fmt, **save_kwargs)
    buf.seek(0)
    return buf.getvalue()


def remove_background(img_bytes: bytes) -> Image.Image:
    if rembg_remove is None:
        raise RuntimeError('rembg is not available; install rembg to enable background removal')
    out_bytes = rembg_remove(img_bytes)
    return pil_from_bytes(out_bytes)


def paste_on_white(img: Image.Image) -> Image.Image:
    # Smooth alpha edges to avoid harsh cutouts
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    alpha = img.split()[-1]
    # Apply slight blur to alpha for clean edges
    alpha_blur = alpha.filter(ImageFilter.GaussianBlur(radius=2))
    img.putalpha(alpha_blur)
    bg = Image.new('RGB', img.size, (255, 255, 255))
    bg.paste(img, mask=img.split()[-1])
    return bg


def detect_face(img: Image.Image):
    # Returns (x, y, w, h) of primary face or None
    arr = np.array(img.convert('RGB'))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
    if len(faces) == 0:
        return None
    # choose largest
    faces = sorted(faces, key=lambda r: r[2] * r[3], reverse=True)
    return tuple(int(v) for v in faces[0])


def detect_eyes(img: Image.Image):
    arr = np.array(img.convert('RGB'))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    eyes = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(10, 10))
    centers = []
    for (ex, ey, ew, eh) in eyes:
        centers.append((ex + ew / 2, ey + eh / 2))
    return centers


def align_image(img: Image.Image) -> Image.Image:
    # Try to detect eyes and rotate to make them horizontal
    eyes = detect_eyes(img)
    if len(eyes) >= 2:
        # pick two eyes with largest separation
        eyes = sorted(eyes, key=lambda c: c[0])
        left, right = eyes[0], eyes[1]
        dx = right[0] - left[0]
        dy = right[1] - left[1]
        angle = np.degrees(np.arctan2(dy, dx))
        return img.rotate(-angle, resample=Image.BICUBIC, expand=True)
    return img


def crop_centered_on_face(img: Image.Image, face_box, output_size=(413, 531)) -> Image.Image:
    if face_box is None:
        # fallback: center crop using target ratio
        return ImageOps.fit(img, output_size, Image.LANCZOS, centering=(0.5, 0.4))

    x, y, w, h = face_box
    # expand box to include shoulders and some margin
    cx = x + w // 2
    cy = y + h // 2
    # desired aspect ratio
    target_w, target_h = output_size
    target_ratio = target_w / target_h

    # choose crop size based on face height; tuned for head+shoulders
    crop_h = int(h * 2.8)
    crop_w = int(crop_h * target_ratio)

    left = max(0, cx - crop_w // 2)
    top = max(0, cy - crop_h // 2)
    right = min(img.width, left + crop_w)
    bottom = min(img.height, top + crop_h)

    crop = img.crop((left, top, right, bottom))
    # ensure face is vertically positioned (head slightly above center)
    # We'll center with a slight upward bias
    out = ImageOps.fit(crop, output_size, Image.LANCZOS, centering=(0.5, 0.38))
    return out


def enhance_image(img: Image.Image) -> Image.Image:
    img = img.convert('RGB')
    # Auto contrast and gentle color balancing
    img = ImageOps.autocontrast(img)
    # Slight color correction using ImageEnhance.Color
    color_enh = ImageEnhance.Color(img)
    img = color_enh.enhance(1.02)
    # Brightness and contrast
    bright = ImageEnhance.Brightness(img)
    img = bright.enhance(1.04)
    cont = ImageEnhance.Contrast(img)
    img = cont.enhance(1.08)
    # Sharpen gently
    sharp = ImageEnhance.Sharpness(img)
    img = sharp.enhance(1.5)
    return img


def denoise_cv(img: Image.Image) -> Image.Image:
    arr = np.array(img)
    try:
        dst = cv2.fastNlMeansDenoisingColored(arr, None, h=8, hColor=8, templateWindowSize=7, searchWindowSize=21)
        return Image.fromarray(dst)
    except Exception:
        return img


def make_grid(img: Image.Image, count=6) -> Image.Image:
    # Create a print-ready grid with thin cutting borders and gaps
    single_w, single_h = img.size
    cols = 3 if count == 6 else 4
    rows = 2 if count == 6 else 3
    gap = max(8, int(single_w * 0.03))  # gap between photos
    border = max(4, int(single_w * 0.02))  # thin cutting border outside image

    cell_w = single_w + gap + border * 2
    cell_h = single_h + gap + border * 2
    grid_w = cell_w * cols - gap
    grid_h = cell_h * rows - gap
    grid = Image.new('RGB', (grid_w, grid_h), 'white')

    for i in range(count):
        r = i // cols
        c = i % cols
        x = c * cell_w
        y = r * cell_h
        # paste photo centered inside cell (leave border space)
        paste_x = x + border
        paste_y = y + border
        grid.paste(img, (paste_x, paste_y))
        # draw thin cutting border as rectangle outside photo area
        # border color slightly gray for print guides
        from PIL import ImageDraw
        draw = ImageDraw.Draw(grid)
        rect_outer = [x + border - 1, y + border - 1, x + border + single_w + 1, y + border + single_h + 1]
        draw.rectangle(rect_outer, outline=(80, 80, 80))

    return grid


def layout_4x6(single_img: Image.Image, dpi=300):
    # 4x6 inches in pixels
    w = int(4 * dpi)
    h = int(6 * dpi)
    canvas = Image.new('RGB', (w, h), 'white')
    # create multiple copies with borders for print
    # decide target size for each passport on 4x6
    target_w = int(w * 0.45)
    target_h = int(target_w * (single_img.height / single_img.width))
    # place two columns
    margin_x = (w - target_w * 2) // 3
    margin_y = (h - target_h * 2) // 3
    positions = [
        (margin_x, margin_y),
        (margin_x * 2 + target_w, margin_y),
        (margin_x, margin_y * 2 + target_h),
        (margin_x * 2 + target_w, margin_y * 2 + target_h)
    ]
    from PIL import ImageDraw
    for pos in positions:
        s = single_img.resize((target_w, target_h), Image.LANCZOS)
        canvas.paste(s, pos)
        draw = ImageDraw.Draw(canvas)
        # draw cutting border
        draw.rectangle([pos[0]-2, pos[1]-2, pos[0]+target_w+2, pos[1]+target_h+2], outline=(80,80,80))
    return canvas


def layout_a4(single_img: Image.Image, dpi=300):
    # A4 at 300dpi ~ 2480x3508
    w, h = int(8.27 * dpi), int(11.69 * dpi)
    canvas = Image.new('RGB', (w, h), 'white')
    # create many small copies (e.g., fit 3 columns)
    cols = 3
    rows = 6
    thumb_w = w // cols
    thumb_h = int(thumb_w * (single_img.height / single_img.width))
    y = 0
    for r in range(rows):
        x = 0
        for c in range(cols):
            t = single_img.resize((thumb_w - 20, thumb_h - 20), Image.LANCZOS)
            canvas.paste(t, (x + 10, y + 10))
            x += thumb_w
        y += thumb_h
        if y > h:
            break
    return canvas


def images_to_pdf_bytes(images):
    buf = io.BytesIO()
    pil_images = [im.convert('RGB') for im in images]
    pil_images[0].save(buf, format='PDF', save_all=True, append_images=pil_images[1:])
    buf.seek(0)
    return buf.getvalue()


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


@app.route('/process-photo', methods=['POST'])
def process_photo():
    try:
        app.logger.info('process_photo called')
        app.logger.info('form keys: %s', list(request.form.keys()))
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        f = request.files['image']
        filename = secure_filename(f.filename)
        if not allowed_file(filename):
            return jsonify({'error': 'Unsupported file type'}), 400

        data = f.read()

        # Validate image by trying to open
        try:
            orig_img = pil_from_bytes(data)
        except Exception:
            return jsonify({'error': 'Invalid image file'}), 400

        # remove background (best effort)
        try:
            bg_removed = remove_background(data)
        except Exception:
            bg_removed = orig_img

        # paste on white with smooth edges
        white = paste_on_white(bg_removed)

        # align and detect face
        aligned = align_image(white)
        face = detect_face(aligned)

        # target passport size (413x531 px at 300 DPI)
        target_px = (413, 531)
        passport = crop_centered_on_face(aligned, face, output_size=target_px)
        passport = denoise_cv(passport)
        passport = enhance_image(passport)

        # parameters
        out_format = request.form.get('format', 'jpg').lower()  # 'jpg' or 'pdf'
        sheet = request.form.get('sheet', '').lower()  # '6', '12', '4x6', 'a4' or ''
        dpi = int(request.form.get('dpi', 300))
        download = request.form.get('download', 'zip').lower()  # 'single'|'zip'
        app.logger.info('params: out_format=%s sheet=%r dpi=%s download=%r', out_format, sheet, dpi, download)

        # generate assets
        single_bytes = bytes_from_pil(passport, fmt='JPEG', quality=95, dpi=dpi)

        outputs = {}

        if sheet == '6':
            grid6 = make_grid(passport, 6)
            outputs['passport_6.jpg'] = bytes_from_pil(grid6, fmt='JPEG', quality=95, dpi=dpi)
        if sheet == '12':
            grid12 = make_grid(passport, 12)
            outputs['passport_12.jpg'] = bytes_from_pil(grid12, fmt='JPEG', quality=95, dpi=dpi)
        if sheet == '4x6':
            layout46 = layout_4x6(passport, dpi=dpi)
            outputs['layout_4x6.jpg'] = bytes_from_pil(layout46, fmt='JPEG', quality=95, dpi=dpi)
        if sheet == 'a4':
            a4 = layout_a4(passport, dpi=dpi)
            outputs['layout_A4.jpg'] = bytes_from_pil(a4, fmt='JPEG', quality=95, dpi=dpi)

        # PDFs
        if out_format == 'pdf':
            # single passport PDF
            pdf_bytes = images_to_pdf_bytes([passport])
            outputs['passport.pdf'] = pdf_bytes
            if 'layout_A4.jpg' in outputs:
                # create A4 PDF from image
                a4_img = Image.open(io.BytesIO(outputs['layout_A4.jpg']))
                outputs['layout_A4.pdf'] = images_to_pdf_bytes([a4_img])

        # Include single image in outputs
        outputs['passport.jpg'] = single_bytes

        # If client asked for PDF output specifically and sheet exists, create PDF from sheet images
        if out_format == 'pdf' and 'passport_6.jpg' in outputs:
            img = Image.open(io.BytesIO(outputs['passport_6.jpg']))
            outputs['passport_6.pdf'] = images_to_pdf_bytes([img])
        if out_format == 'pdf' and 'passport_12.jpg' in outputs:
            img = Image.open(io.BytesIO(outputs['passport_12.jpg']))
            outputs['passport_12.pdf'] = images_to_pdf_bytes([img])

        # If client requested a direct single download, return that now
        if download == 'single' and out_format == 'jpg' and not sheet:
            return send_file(io.BytesIO(single_bytes), mimetype='image/jpeg', as_attachment=True, download_name='passport.jpg')
        if download == 'single' and out_format == 'pdf' and not sheet:
            pdf_bytes = images_to_pdf_bytes([passport])
            return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name='passport.pdf')

        # package into zip
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for name, b in outputs.items():
                zf.writestr(name, b)

        zip_buf.seek(0)
        return send_file(zip_buf, mimetype='application/zip', as_attachment=True, download_name='passport_outputs.zip')

    except Exception as exc:
        tb = traceback.format_exc()
        app.logger.exception('Processing error')
        return jsonify({'error': 'Processing failed', 'detail': str(exc), 'trace': tb if app.debug else ''}), 500


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        # Accept either an image file or base64 image in form
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        f = request.files['image']
        filename = secure_filename(f.filename)
        if not allowed_file(filename):
            return jsonify({'error': 'Unsupported file type'}), 400

        data = f.read()
        img = pil_from_bytes(data)
        # optional layout param
        layout = request.form.get('layout', 'single')
        if layout == 'a4':
            page = layout_a4(img)
            out_bytes = images_to_pdf_bytes([page])
        elif layout == '4x6':
            page = layout_4x6(img)
            out_bytes = images_to_pdf_bytes([page])
        else:
            out_bytes = images_to_pdf_bytes([img.convert('RGB')])

        return send_file(io.BytesIO(out_bytes), mimetype='application/pdf', as_attachment=True, download_name='output.pdf')

    except Exception as exc:
        tb = traceback.format_exc()
        app.logger.exception('PDF generation error')
        return jsonify({'error': 'PDF generation failed', 'detail': str(exc), 'trace': tb if app.debug else ''}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
