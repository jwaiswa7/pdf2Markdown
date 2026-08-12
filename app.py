import uuid
import os
import time
from pathlib import Path
import markdown
import pymupdf4llm
from flask import Flask, request, redirect, url_for, render_template, abort

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB limit

CONVERSION_TTL_SECONDS = 10 * 60
CONVERSIONS_DIR = Path("/tmp/pdf2md-conversions")


def cleanup_expired_conversions() -> None:
    now = time.time()
    if not CONVERSIONS_DIR.exists():
        return

    for file_path in CONVERSIONS_DIR.glob("*.md"):
        try:
            if now - file_path.stat().st_mtime > CONVERSION_TTL_SECONDS:
                file_path.unlink()
        except FileNotFoundError:
            continue


def get_conversion_path(conversion_id: str) -> Path:
    return CONVERSIONS_DIR / f"{conversion_id}.md"


def save_conversion(conversion_id: str, md_text: str) -> None:
    CONVERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    get_conversion_path(conversion_id).write_text(md_text, encoding="utf-8")


def load_conversion(conversion_id: str) -> str | None:
    file_path = get_conversion_path(conversion_id)
    if not file_path.exists():
        return None

    return file_path.read_text(encoding="utf-8")


@app.route("/")
def index():
    cleanup_expired_conversions()
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    cleanup_expired_conversions()
    file = request.files.get("pdf")
    if not file or not file.filename.lower().endswith(".pdf"):
        return render_template("index.html", error="Please upload a valid PDF file."), 400

    # Save to a temp path so pymupdf4llm can open it
    tmp_path = f"/tmp/{uuid.uuid4().hex}.pdf"
    try:
        file.save(tmp_path)
        md_text = pymupdf4llm.to_markdown(tmp_path)
    except Exception as e:
        return render_template("index.html", error=f"Conversion failed: {e}"), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    conversion_id = uuid.uuid4().hex
    save_conversion(conversion_id, md_text)
    return redirect(url_for("result", conversion_id=conversion_id))


@app.route("/result/<conversion_id>")
def result(conversion_id):
    cleanup_expired_conversions()
    md_text = load_conversion(conversion_id)
    if md_text is None:
        abort(404)
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    return render_template("result.html", html_body=html_body, md_text=md_text)


if __name__ == "__main__":
    app.run(debug=True)
