from flask import Blueprint, render_template_string, request, redirect, url_for, flash, current_app, get_flashed_messages
import os
from werkzeug.utils import secure_filename
import laspy
import numpy as np
import pyproj

main_bp = Blueprint('main', __name__)

def allowed_file(filename):
   allowed_exts = current_app.config['ALLOWED_EXTENSIONS']
   return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

@main_bp.route('/', methods=['GET', 'POST'])
def upload_file():
    metadata = None  
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

                try:
                    with laspy.open(file_path, laz_backend=laspy.LazBackend.Laszip) as las:
                        h = las.header

                        # 1. Basic metadata
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

                        # 2. CRS detection 
                        crs_info = "Not specified"
                        for vlr in h.vlrs:
                            user_id = getattr(vlr, 'user_id', getattr(getattr(vlr, 'header', None), 'user_id', ''))
                            record_id = getattr(vlr, 'record_id', getattr(getattr(vlr, 'header', None), 'record_id', -1))
                            if user_id == "LASF_Projection" and record_id == 2112:
                                wkt = getattr(vlr, 'string', getattr(vlr, 'wkt_string', ''))
                                if wkt and wkt.strip():
                                    try:
                                        crs = pyproj.CRS.from_wkt(wkt.strip())
                                        epsg = crs.to_epsg()
                                        name = crs.name
                                        crs_info = f"EPSG:{epsg} — {name}" if epsg else f"WKT: {name}"
                                    except Exception:
                                        crs_info = f"WKT (truncated): {wkt[:80]}…"
                                    break
                        metadata['crs'] = crs_info

                        # 3. Classification summary 
                        if 'classification' in h.point_format.dimension_names:
                            points = las.read()
                            classification = points.classification

                            unique, counts = np.unique(classification, return_counts=True)
                            class_counts = dict(zip(unique, counts))

                            class_names = {
                                0: "Never Classified", 1: "Unclassified", 2: "Ground",
                                3: "Low Vegetation", 4: "Medium Vegetation", 5: "High Vegetation",
                                6: "Building", 7: "Low Point", 9: "Water", 
                                17: "Bridge Deck", 18: "High Noise"
                            }

                            total = len(classification)
                            class_summary = []
                            for cls_id in sorted(class_counts):
                                count = class_counts[cls_id]
                                name = class_names.get(cls_id, f"Class {cls_id}")
                                pct = count / total * 100
                                class_summary.append(f"{cls_id} ({name}): {count:,} pts ({pct:.1f}%)")

                            metadata['classification'] = "<br>".join(class_summary)
                        else:
                            metadata['classification'] = "No 'classification' field"

                except Exception as e:
                    messages.append(('error', f'Error reading LAS: {str(e)}'))
                    metadata = None

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