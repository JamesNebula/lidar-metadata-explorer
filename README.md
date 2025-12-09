# LiDAR Metadata Explorer

A lightweight Flask app to inspect LAZ/LAS file metadata — built for geospatial technicians and LiDAR engineers.

![Upload UI](docs/screenshot-upload.png)
![JSON Output](docs/screenshot-json.png)

## ✅ Features
- Upload `.las`/`.laz` files
- View key metadata: bounds, CRS, point count, classification breakdown
- Download structured JSON report (for scripting/QC pipelines)
- Works on M1 Mac (uses `laszip` backend)

## 🛠️ Setup
```bash
git clone https://github.com/your-username/lidar-metadata-explorer.git
cd lidar-metadata-explorer
python -m venv venv && source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python run.py
