# backend/main.py
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps
import numpy as np
import uuid
import os

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"
GENERATED_DIR = STATIC_DIR / "generated"

# Ensure folders exist
for p in [STATIC_DIR, UPLOADS_DIR, GENERATED_DIR]:
    p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Synthetic MRI Generator")

# CORS (allow VS Code Live Server or file://)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if you want
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve /static/*
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _smooth_noise(size=(256, 256), base=8):
    """Create smooth noise by upscaling tiny random arrays."""
    small = np.random.rand(base, base) * 255
    img = Image.fromarray(small.astype(np.uint8), mode="L")
    return np.array(img.resize(size, Image.BICUBIC))


def _circular_mask(size=(256, 256)):
    """Circular mask to emulate MRI FOV (grayscale)."""
    w, h = size
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2.0, h / 2.0
    r = min(w, h) * 0.48
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    mask = (dist <= r).astype(np.float32)
    # Feather edges
    edge = (dist > r) & (dist < r + 8)
    mask[edge] = np.linspace(1, 0, edge.sum(), endpoint=True)
    return mask


def generate_synthetic_from_image(src_path: Path, out_path: Path):
    # Load and normalize input
    img = Image.open(src_path).convert("L").resize((256, 256), Image.BICUBIC)
    img_np = np.asarray(img).astype(np.float32)

    # Make smooth noise + blend
    noise = _smooth_noise((256, 256), base=10).astype(np.float32)
    blended = (0.7 * img_np + 0.3 * noise)

    # Apply circular mask
    mask = _circular_mask((256, 256))
    masked = blended * mask

    # Light gaussian blur and contrast stretch
    out = Image.fromarray(np.clip(masked, 0, 255).astype(np.uint8))
    out = out.filter(ImageFilter.GaussianBlur(radius=0.7))
    out = ImageOps.autocontrast(out)

    out.save(out_path, format="JPEG", quality=92)


@app.get("/api/gallery")
def get_gallery():
    """Return list of generated images (newest first)."""
    files = sorted(GENERATED_DIR.glob("*.jpg"), key=os.path.getmtime, reverse=True)
    urls = [f"/static/generated/{f.name}" for f in files]
    return {"images": urls}


@app.post("/api/upload")
async def upload_and_generate(mri_image: UploadFile = File(...)):
    """Upload one image, save it, generate synthetic, return URL."""
    # Save uploaded file
    up_name = f"{uuid.uuid4().hex}_{mri_image.filename}"
    up_path = UPLOADS_DIR / up_name
    with open(up_path, "wb") as f:
        f.write(await mri_image.read())

    # Generate synthetic output
    out_name = f"{uuid.uuid4().hex}.jpg"
    out_path = GENERATED_DIR / out_name
    generate_synthetic_from_image(up_path, out_path)

    return JSONResponse({"generated": f"/static/generated/{out_name}"})


# (Optional) Backward-compatible endpoint name from earlier
@app.post("/upload_dataset/")
async def legacy_upload(mri_image: UploadFile = File(...)):
    return await upload_and_generate(mri_image)
