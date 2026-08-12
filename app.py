import uuid
import os
import markdown
import pymupdf4llm
from flask import Flask, request, redirect, url_for, render_template, abort

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB limit

# In-memory store: {conversion_id: markdown_text}
conversions: dict[str, str] = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
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
    conversions[conversion_id] = md_text
    return redirect(url_for("result", conversion_id=conversion_id))


@app.route("/result/<conversion_id>")
def result(conversion_id):
    md_text = conversions.get(conversion_id)
    if md_text is None:
        abort(404)
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    return render_template("result.html", html_body=html_body, md_text=md_text)


if __name__ == "__main__":
    app.run(debug=True)
