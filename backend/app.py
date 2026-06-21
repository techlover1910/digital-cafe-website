from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from io import BytesIO
import io
import fitz

app = Flask(__name__)
CORS(app)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def image_to_rgb(img):
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img, mask=img.split()[-1])
        return bg
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def enhance_image(img):
    img = image_to_rgb(img)
    img = ImageOps.autocontrast(img)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.5)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(0.95)
    return img


def remove_background(img):
    img = image_to_rgb(img)
    img = img.convert("RGBA")
    width, height = img.size
    pixels = img.load()

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if r > 230 and g > 230 and b > 230:
                pixels[x, y] = (255, 255, 255, 0)
            else:
                pixels[x, y] = (r, g, b, 255)

    # Ensure a clean white base for output
    white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    white_bg.alpha_composite(img)
    return white_bg.convert("RGB")


def resize_to_passport(img, output_size=(413, 531)):
    img = img.copy()
    width, height = img.size

    if width > height:
        crop_width = int(height * 0.78)
        left = (width - crop_width) // 2
        img = img.crop((left, 0, left + crop_width, height))
    elif height > width:
        crop_height = int(width * 1.28)
        top = (height - crop_height) // 2
        img = img.crop((0, top, width, top + crop_height))

    # Keep subject centered and aligned for passport proportions
    img = img.resize(output_size, Image.LANCZOS)
    return img


def make_grid(img, count=6):
    img = img.copy()
    cols = 3 if count == 6 else 4
    rows = 2 if count == 6 else 3
    width, height = img.size
    target_w = width * cols
    target_h = height * rows
    grid = Image.new("RGB", (target_w, target_h), "white")
    for i in range(count):
        row = i // cols
        col = i % cols
        x = col * width
        y = row * height
        grid.paste(img, (x, y))
    return grid


def compress_image(img, target_kb=None, max_size=(2000, 2000)):
    img = image_to_rgb(img)
    img.thumbnail(max_size, Image.LANCZOS)
    if target_kb is None:
        return img
    quality = 95
    buf = BytesIO()
    while quality >= 10:
        buf.seek(0)
        buf.truncate(0)
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        size_kb = buf.tell() / 1024
        if size_kb <= target_kb or quality <= 10:
            break
        quality -= 5
    buf.seek(0)
    return Image.open(buf)


def image_to_pdf_bytes(img):
    buf = BytesIO()
    img.save(buf, format="PDF")
    return buf.getvalue()


def pdf_to_images_bytes(pdf_bytes):
    outputs = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image_bytes = pix.tobytes("jpeg", jpg_quality=95)
            outputs.append(image_bytes)
    except Exception:
        outputs = []
    return outputs


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


@app.route('/api/passport-photo', methods=['POST'])
def passport_photo():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    file = request.files['image']
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    count = request.form.get('count', '6')
    if count not in ('6', '12'):
        count = '6'

    img = Image.open(file.stream)
    img = remove_background(img)
    img = enhance_image(img)
    img = resize_to_passport(img)

    # Create print-ready grid
    grid = make_grid(img, count=int(count))
    buf = BytesIO()
    grid.save(buf, format='PNG')
    buf.seek(0)

    return send_file(
        buf,
        mimetype='image/png',
        as_attachment=True,
        download_name=f'passport_grid_{count}.png'
    )


@app.route('/api/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    mode = request.form.get('mode', 'pdf-to-jpg')
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    if mode == 'jpg-to-pdf':
        img = Image.open(file.stream)
        img = image_to_rgb(img)
        pdf_bytes = image_to_pdf_bytes(img)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='converted.pdf'
        )

    elif mode == 'pdf-to-jpg':
        pdf_bytes = file.read()
        images = pdf_to_images_bytes(pdf_bytes)
        if len(images) == 1:
            return send_file(
                io.BytesIO(images[0]),
                mimetype='image/jpeg',
                as_attachment=True,
                download_name='converted.jpg'
            )
        return jsonify({"error": "Multiple pages detected; please use a dedicated multi-page converter"}), 400

    return jsonify({"error": "Invalid mode"}), 400


@app.route('/api/resize', methods=['POST'])
def resize():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    width = request.form.get('width', type=int)
    height = request.form.get('height', type=int)
    target_kb = request.form.get('target_kb', type=float)

    img = Image.open(file.stream)
    img = image_to_rgb(img)

    if width and height:
        img = img.resize((width, height), Image.LANCZOS)
    elif width:
        ratio = width / img.width
        height = int(img.height * ratio)
        img = img.resize((width, height), Image.LANCZOS)
    elif height:
        ratio = height / img.height
        width = int(img.width * ratio)
        img = img.resize((width, height), Image.LANCZOS)

    if target_kb:
        img = compress_image(img, target_kb=target_kb)

    buf = BytesIO()
    img.save(buf, format='JPEG', quality=95)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='image/jpeg',
        as_attachment=True,
        download_name='resized.jpg'
    )


if __name__ == '__main__':
    import os

    # Read port and debug flags from environment for production readiness
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    app.run(debug=debug, host='0.0.0.0', port=port)
