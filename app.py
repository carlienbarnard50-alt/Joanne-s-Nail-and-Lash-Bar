import os, time, mimetypes
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": os.getenv("ALLOWED_ORIGIN", "*")}})
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

API_BASE = "https://yce-api-01.makeupar.com"
API_KEY = os.getenv("PERFECT_CORP_API_KEY", "").strip()

@app.get("/")
def home():
    return jsonify({"service": "JoAnne's Nail Try-On connection", "ready": bool(API_KEY)})

def api_headers():
    if not API_KEY:
        raise RuntimeError("The Perfect Corp API key has not been added to the private settings yet.")
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def get_result_url(data):
    # Perfect Corp response structures can vary by API version; look for the first output URL.
    candidates = []
    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and ("url" in k.lower() or "image" in k.lower()) and v.startswith("http"):
                    candidates.append(v)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for v in obj: walk(v)
    walk(data)
    # Prefer generated/result/output URLs over source/upload URLs.
    for u in candidates:
        if any(word in u.lower() for word in ("result", "output", "generated", "download")):
            return u
    return candidates[-1] if candidates else None

@app.post("/api/try-on")
def try_on():
    if not API_KEY:
        return jsonify({"error": "The site connection is not configured yet. Add the API key in the hosting service's private environment settings."}), 503
    photo = request.files.get("photo")
    color = (request.form.get("color") or "#C2185B").strip()
    if not photo:
        return jsonify({"error": "Please choose a hand photo first."}), 400
    if not photo.mimetype or not photo.mimetype.startswith("image/"):
        return jsonify({"error": "Please upload a JPG or PNG image."}), 400
    raw = photo.read()
    if not raw:
        return jsonify({"error": "The selected image is empty."}), 400
    if len(raw) > 12 * 1024 * 1024:
        return jsonify({"error": "Please use an image smaller than 12 MB."}), 413
    if not (color.startswith("#") and len(color) in (4, 7)):
        return jsonify({"error": "Please choose a valid polish colour."}), 400

    try:
        # Ask Perfect Corp for a temporary upload location and file ID.
        mime = photo.mimetype or mimetypes.guess_type(photo.filename or "hand.jpg")[0] or "image/jpeg"
        filename = (photo.filename or "hand-photo.jpg").replace("/", "_").replace("\\", "_")
        file_info = requests.post(
            f"{API_BASE}/s2s/v2.0/file",
            headers=api_headers(),
            json={"files": [{"content_type": mime, "file_name": filename, "file_size": len(raw)}]},
            timeout=30,
        )
        file_info.raise_for_status()
        info = file_info.json()
        file_item = (info.get("files") or [None])[0]
        if not file_item:
            return jsonify({"error": "Perfect Corp did not return an upload location.", "details": info}), 502
        file_id = file_item.get("file_id") or file_item.get("id")
        upload_url = file_item.get("url") or file_item.get("upload_url")
        if not upload_url or not file_id:
            return jsonify({"error": "The upload details returned by Perfect Corp were not in the expected format. Please contact support with this message.", "details": info}), 502

        # The upload URL is a temporary signed URL supplied by Perfect Corp.
        put = requests.put(upload_url, data=raw, headers={"Content-Type": mime}, timeout=60)
        put.raise_for_status()

        # Submit a solid-colour polish task for the five visible fingers.
        fingers = ["thumb", "index", "middle", "ring", "pinky"]
        effects = [{"sub_type": "color", "finger": finger, "color": color, "texture": "cream", "reflection": 100, "contrast": 50, "roughness": 0, "transparency": 0} for finger in fingers]
        task_response = requests.post(
            f"{API_BASE}/s2s/v2.0/task/nail-vto",
            headers=api_headers(),
            json={"version": "1.0", "effect_type": "nail_polish", "src_file_id": file_id, "effects": effects},
            timeout=30,
        )
        task_response.raise_for_status()
        task_data = task_response.json()
        task_id = (task_data.get("data") or {}).get("task_id") or task_data.get("task_id")
        if not task_id:
            return jsonify({"error": "Perfect Corp did not return a task ID.", "details": task_data}), 502

        # Poll for completion for up to about 90 seconds.
        status_data = {}
        for _ in range(18):
            time.sleep(5)
            poll = requests.get(f"{API_BASE}/s2s/v2.0/task/nail-vto/{task_id}", headers={"Authorization": f"Bearer {API_KEY}"}, timeout=30)
            poll.raise_for_status()
            status_data = poll.json()
            d = status_data.get("data") or status_data
            status = str(d.get("task_status") or d.get("status") or "").lower()
            if status in ("success", "succeeded", "completed"):
                result_url = get_result_url(status_data)
                if result_url:
                    return jsonify({"result_url": result_url, "status": "success"})
                return jsonify({"error": "The task finished, but the result image URL could not be identified.", "details": status_data}), 502
            if status in ("error", "failed", "failure"):
                return jsonify({"error": "Perfect Corp could not process this photo. Try a brighter photo with all nails visible.", "details": status_data}), 422
        return jsonify({"error": "The preview is taking longer than expected. Please try again in a moment.", "task_id": task_id}), 504
    except requests.HTTPError as exc:
        response = getattr(exc, "response", None)
        details = response.text[:1200] if response is not None else str(exc)
        return jsonify({"error": "Perfect Corp returned an error. Check that your API access is active and supports AI Nail Virtual Try-On.", "details": details}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
