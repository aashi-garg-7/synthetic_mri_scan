const API_BASE = "http://127.0.0.1:8000";

async function loadGallery() {
  const gallery = document.getElementById("gallery");
  gallery.innerHTML = "<div class='status'>Loading gallery…</div>";
  try {
    const res = await fetch(`${API_BASE}/api/gallery`);
    const data = await res.json();
    gallery.innerHTML = "";
    if (!data.images || data.images.length === 0) {
      gallery.innerHTML = "<div class='status'>No images yet. Upload to generate!</div>";
      return;
    }
    data.images.forEach(url => {
      const img = document.createElement("img");
      img.src = `${API_BASE}${url}`;
      img.alt = "Synthetic MRI";
      gallery.appendChild(img);
    });
  } catch (e) {
    gallery.innerHTML = "<div class='status'>Failed to load gallery.</div>";
    console.error(e);
  }
}

document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const status = document.getElementById("status");
  const fileInput = document.getElementById("mri_image");
  const preview = document.getElementById("preview");
  const previewImg = document.getElementById("preview-img");
  const dl = document.getElementById("download-link");

  if (!fileInput.files.length) {
    status.textContent = "Please choose an image file first.";
    return;
  }

  status.textContent = "Uploading and generating…";
  const form = new FormData();
  form.append("mri_image", fileInput.files[0]);

  try {
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: form,
    });
    const data = await res.json();
    if (data.generated) {
      const fullUrl = `${API_BASE}${data.generated}`;
      previewImg.src = fullUrl;
      dl.href = fullUrl;
      dl.setAttribute("download", `synthetic_mri_${Date.now()}.jpg`);
      preview.classList.remove("hidden");
      status.textContent = "Done!";
      await loadGallery();
    } else {
      status.textContent = "Unexpected response from server.";
    }
  } catch (err) {
    console.error(err);
    status.textContent = "Upload failed. Check backend is running.";
  }
});

document.getElementById("refresh").addEventListener("click", loadGallery);

// Initial load
document.addEventListener("DOMContentLoaded", loadGallery);
