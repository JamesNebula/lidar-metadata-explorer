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
                        header = las.header
                        vlrs = header.vlrs
                        evlrs = header.evlrs
                        metadata = {
                            'filename': filename,
                            'version': str(header.version),
                            'point_format': header.point_format.id,
                            'point_count': f"{header.point_count:,}",
                            'bounds': (
                                f"X[{header.mins[0]:.2f}, {header.maxs[0]:.2f}], "
                                f"Y[{header.mins[1]:.2f}, {header.maxs[1]:.2f}], "
                                f"Z[{header.mins[2]:.2f}, {header.maxs[2]:.2f}]"
                            )
                        }

                        crs_info = "Not specified"
                        # Helper: safely get user_id/record_id (works for all VLR types)
                        def get_vlr_id(vlr):
                            # Newer laspy: VLRs are typed; use class name or header
                            if hasattr(vlr, 'header'):
                                return vlr.header.user_id, vlr.header.record_id
                            # Fallback for older or raw VLRs
                            return getattr(vlr, 'user_id', ''), getattr(vlr, 'record_id', -1)


                        # Check standard VLRs
                        for vlr in header.vlrs:
                            user_id, record_id = get_vlr_id(vlr)
                            # Standard WKT VLR: user_id="LASF_Projection", record_id=2112
                            if user_id == "LASF_Projection" and record_id == 2112:
                                wkt = None
                                # Try common WKT attributes
                                if hasattr(vlr, 'string'):
                                    wkt = vlr.string
                                elif hasattr(vlr, 'wkt_string'):
                                    wkt = vlr.wkt_string
                                elif hasattr(vlr, '__str__'):
                                    wkt = str(vlr)

                                if wkt and wkt.strip():
                                    wkt = wkt.strip()
                                    try:
                                        crs = pyproj.CRS.from_wkt(wkt)
                                        epsg = crs.to_epsg()
                                        name = crs.name
                                        crs_info = f"EPSG:{epsg} — {name}" if epsg else f"WKT: {name}"
                                    except Exception:
                                        crs_info = f"WKT (truncated): {wkt[:80]}…"
                                    break

                        # Check EVLRs (if any)
                        if crs_info == "Not specified" and hasattr(header, 'evlrs'):
                            for evlr in header.evlrs:
                                user_id, record_id = get_vlr_id(evlr)
                                if user_id == "LASF_Projection" and record_id == 2112:
                                    wkt = getattr(evlr, 'string', '') or getattr(evlr, 'wkt_string', '')
                                    if wkt and wkt.strip():
                                        crs_info = f"WKT EVLR (truncated): {wkt[:80]}…"
                                        break
                                    
                        metadata['crs'] = crs_info

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