from flask import Blueprint, render_template_string, request, redirect, url_for, flash, current_app, get_flashed_messages
import os
from werkzeug.utils import secure_filename
import laspy
import numpy as np

main_bp = Blueprint('main', __name__)

def allowed_file(filename):
   allowed_exts = current_app.config['ALLOWED_EXTENSIONS']
   return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

@main_bp.route('/', methods=['GET', 'POST'])
def upload_file():
    metadata = None  # ← define here, outside POST
    messages = []

    if request.method == 'POST':
        if 'file' not in request.files:
            messages.append(('error', 'No file part'))
        else:
            file = request.files['file']
            if file.filename == '':
                messages.append(('error', 'No selected file'))
            elif file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                messages.append(('success', f'File {filename} uploaded successfully!'))

                # ✅ Extract metadata — now stays in scope
                try:
                    with laspy.open(file_path) as las:
                        h = las.header
                        metadata = {
                            'filename': filename,
                            'version': str(h.version),
                            'point_format': h.point_format.id,
                            'point_count': f"{h.point_count:,}",
                            'bounds': (
                                f"X[{h.mins[0]:.2f}, {h.maxs[0]:.2f}], "
                                f"Y[{h.mins[1]:.2f}, {h.maxs[1]:.2f}], "
                                f"Z[{h.mins[2]:.2f}, {h.maxs[2]:.2f}]"
                            )
                        }
                except Exception as e:
                    messages.append(('error', f'Error reading LAS: {str(e)}'))

    # Build HTML
    flash_html = ''.join(
        f'<p style="color:{"green" if level=="success" else "red"}">{msg}</p>'
        for level, msg in messages
    )

    metadata_html = ""
    if metadata:
        items = [f"<li><strong>{k}:</strong> {v}</li>" for k, v in metadata.items()]
        metadata_html = f"<h2>Metadata</h2><ul>{''.join(items)}</ul>"

    return f"""
    <!doctype html>
    <html>
    <head><title>LiDAR Metadata Explorer</title></head>
    <body>
        <h1>Upload LiDAR File (.las/.laz)</h1>
        {flash_html}
        {metadata_html}
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".las,.laz" required>
            <input type="submit" value="Upload">
        </form>
    </body>
    </html>
    """