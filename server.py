import os
import re
import time
import requests
from flask import Flask, jsonify, request, abort

app = Flask(__name__)
IA_ADVANCED = "https://archive.org/advancedsearch.php"
IA_METADATA = "https://archive.org/metadata/{}"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "FeriFLACArchive/1.0 (BitChord addon)"})

# Small in-memory cache to avoid repeatedly querying Internet Archive.
CACHE = {}
CACHE_TTL = 300

MANIFEST = {
    "id": "id.feri.flacarchive",
    "name": "Feri FLAC Archive",
    "version": "1.0.0",
    "resources": ["search", "stream"],
    "allowDownloads": 1,
    "settings": [
        {
            "key": "quality",
            "type": "select",
            "label": "Audio quality",
            "default": "lossless",
            "options": [
                {"value": "lossless", "label": "FLAC Lossless"},
                {"value": "all", "label": "All available audio"}
            ]
        }
    ]
}

def cache_get(key):
    item = CACHE.get(key)
    if item and time.time() - item[0] < CACHE_TTL:
        return item[1]
    return None

def cache_set(key, value):
    CACHE[key] = (time.time(), value)

def get_metadata(identifier):
    cached = cache_get("meta:" + identifier)
    if cached is not None:
        return cached
    response = SESSION.get(IA_METADATA.format(identifier), timeout=20)
    response.raise_for_status()
    data = response.json()
    cache_set("meta:" + identifier, data)
    return data

def flac_files(metadata):
    result = []
    for item in metadata.get("files", []):
        name = item.get("name", "")
        if name.lower().endswith(".flac"):
            # Exclude files marked as derivatives or not actually downloadable.
            if item.get("source") == "original" or item.get("source") is None:
                result.append(item)
    return result

def file_url(identifier, filename):
    # Archive.org file paths must be URL-encoded, including spaces and special characters.
    from urllib.parse import quote
    return f"https://archive.org/download/{quote(identifier, safe='')}/{quote(filename, safe='/')}"

@app.get("/")
@app.get("/manifest.json")
def manifest():
    return jsonify(MANIFEST)

@app.get("/health")
def health():
    return jsonify({"ok": True, "addon": MANIFEST["name"], "version": MANIFEST["version"]})

@app.get("/search")
def search():
    query = (request.args.get("q") or "").strip()
    quality = (request.args.get("quality") or "lossless").lower()
    if len(query) < 2:
        return jsonify({"tracks": [], "total": 0})

    cache_key = f"search:{query.lower()}:{quality}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    # Search audio items first, then inspect their file metadata to confirm real FLAC files.
    params = {
        "q": f'mediatype:audio AND ({query})',
        "fl[]": ["identifier", "title", "creator", "album", "year"],
        "rows": 35,
        "page": 1,
        "output": "json"
    }
    try:
        response = SESSION.get(IA_ADVANCED, params=params, timeout=25)
        response.raise_for_status()
        docs = response.json().get("response", {}).get("docs", [])
    except (requests.RequestException, ValueError):
        return jsonify({"tracks": [], "total": 0, "error": "Internet Archive sedang tidak bisa dijangkau."}), 502

    tracks = []
    for doc in docs:
        identifier = doc.get("identifier")
        if not identifier:
            continue
        try:
            metadata = get_metadata(identifier)
            candidates = flac_files(metadata)
            if not candidates and quality == "lossless":
                continue

            chosen = candidates[0] if candidates else None
            title = doc.get("title") or identifier
            artist = doc.get("creator") or "Unknown artist"
            if isinstance(artist, list):
                artist = ", ".join(str(x) for x in artist[:3])

            track = {
                "id": identifier,
                "title": str(title),
                "artist": str(artist),
                "album": str(doc.get("album") or ""),
                "audioQuality": "LOSSLESS" if chosen else "ARCHIVE AUDIO",
                "format": "FLAC" if chosen else "OTHER"
            }
            if chosen:
                track["duration"] = int(float(chosen.get("length", 0) or 0))
            tracks.append(track)
            if len(tracks) >= 20:
                break
        except Exception:
            continue

    result = {"tracks": tracks, "total": len(tracks)}
    cache_set(cache_key, result)
    return jsonify(result)

@app.get("/stream/<path:identifier>")
def stream(identifier):
    try:
        metadata = get_metadata(identifier)
    except requests.RequestException:
        return jsonify({"error": "Gagal mengambil metadata dari Internet Archive."}), 502

    candidates = flac_files(metadata)
    if not candidates:
        return jsonify({"error": "Item ini tidak memiliki file FLAC asli."}), 404

    # Prefer the largest FLAC, which is usually the full-quality source.
    chosen = max(candidates, key=lambda x: int(x.get("size", 0) or 0))
    try:
        sample_rate = int(metadata.get("metadata", {}).get("sample_rate", 44100))
    except (TypeError, ValueError):
        sample_rate = 44100

    try:
        bit_depth = int(metadata.get("metadata", {}).get("bit_depth", 16))
    except (TypeError, ValueError):
        bit_depth = 16

    return jsonify({
        "url": file_url(identifier, chosen["name"]),
        "format": "flac",
        "quality": f"FLAC · {bit_depth}-bit / {sample_rate} Hz",
        "codec": "flac",
        "container": "flac",
        "manifest": "none",
        "encrypted": False,
        "sampleRate": sample_rate,
        "bitDepth": bit_depth
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
