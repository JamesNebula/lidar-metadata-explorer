from flask import Blueprint, render_template_string, request, current_app, Response
from werkzeug.utils import secure_filename
import os
import laspy
import numpy as np
import pyproj
import json

main_bp = Blueprint('main', __name__)

def allowed_file(filename):
    allowed_exts = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

@main_bp.route('/', methods=['GET', 'POST'])
def upload_file():
    metadata = None
    filename = None
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

                        # CRS
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
                                        crs_info = f"EPSG:{epsg} — {crs.name}" if epsg else crs.name
                                    except:
                                        crs_info = f"WKT (truncated): {wkt[:60]}…"
                                    break
                        metadata['crs'] = crs_info

                        # Classification
                        if 'classification' in h.point_format.dimension_names:
                            points = las.read()
                            cls_arr = points.classification
                            unique, counts = np.unique(cls_arr, return_counts=True)
                            total = len(cls_arr)
                            
                            class_names = {
                                1: "Unclassified", 2: "Ground", 3: "Low Veg",
                                4: "Med Veg", 5: "High Veg", 6: "Building", 9: "Water"
                            }
                            classification_lines = []
                            for cid, c in zip(unique, counts):
                                name = class_names.get(cid, f"Class {cid}")
                                pct = round(c / total * 100, 1)
                                classification_lines.append(f"{int(cid)} ({name}): {int(c):,} pts ({pct}%)")
                            metadata['classification'] = "<br>".join(classification_lines)
                        else:
                            metadata['classification'] = "No classification field"

                except Exception as e:
                    messages.append(('error', f'Error reading LAS: {str(e)}'))
                    metadata = None

    # Build response
    flash_html = ''.join(
        f'<p style="color:{"green" if level=="success" else "red"}">{msg}</p>'
        for level, msg in messages
    )

    metadata_html = ""
    if metadata:
        items = [f"<li><strong>{k}:</strong> {v}</li>" for k, v in metadata.items()]
        metadata_html = f"<h2>Metadata</h2><ul>{''.join(items)}</ul>"

    download_link = ""
    if filename and metadata:
        download_link = f'<p><a href="/download/{filename}" target="_blank">📥 Download Metadata (JSON)</a></p>'

    return f"""
    <!doctype html>
    <html>
    <head>
        <title>LiDAR Metadata Explorer</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; }}
            li {{ margin: 4px 0; }}
        </style>
    </head>
    <body>
        <h1>LiDAR Metadata Explorer</h1>
        {flash_html}
        {metadata_html}
        {download_link}
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".las,.laz" required>
            <input type="submit" value="Upload">
        </form>
    </body>
    </html>
    """

@main_bp.route('/download/<filename>')
def download_metadata(filename):
    safe_filename = secure_filename(filename)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_filename)
    
    if not os.path.exists(file_path):
        return "File not found", 404

    try:
        with laspy.open(file_path, laz_backend=laspy.LazBackend.Laszip) as las:
            h = las.header

            data = {
                'filename': safe_filename,
                'version': str(h.version),
                'point_format': h.point_format.id,
                'point_count': h.point_count,
                'bounds': {
                    'x_min': h.mins[0],
                    'x_max': h.maxs[0],
                    'y_min': h.mins[1],
                    'y_max': h.maxs[1],
                    'z_min': h.mins[2],
                    'z_max': h.maxs[2]
                }
            }

            # CRS
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
                            crs_info = f"EPSG:{epsg} — {crs.name}" if epsg else crs.name
                        except:
                            crs_info = "WKT (parsing failed)"
                        break
            data['crs'] = crs_info

            # Classification (structured JSON)
            if 'classification' in h.point_format.dimension_names:
                points = las.read()
                cls_arr = points.classification
                unique, counts = np.unique(cls_arr, return_counts=True)
                total = len(cls_arr)
                
                class_names = {
                    1: "Unclassified", 2: "Ground", 3: "Low Veg",
                    4: "Med Veg", 5: "High Veg", 6: "Building", 9: "Water"
                }
                data['classification'] = [
                    {
                        "class_id": int(cid),
                        "name": class_names.get(cid, f"Class {cid}"),
                        "count": int(c),
                        "percentage": round(c / total * 100, 1)
                    }
                    for cid, c in zip(unique, counts)
                ]
            else:
                data['classification'] = []

            json_str = json.dumps(data, indent=2)
            return Response(
                json_str,
                mimetype='application/json',
                headers={"Content-Disposition": f"attachment;filename={safe_filename}.metadata.json"}
            )

    except Exception as e:
        return f"Error generating metadata: {str(e)}", 500