# LiDAR Metadata Explorer

A lightweight Flask app to inspect LAZ/LAS file metadata — built for geospatial technicians and LiDAR engineers.

## Features
- Upload `.las`/`.laz` files
- View key metadata: bounds, CRS, point count, classification breakdown
- Download structured JSON report (for scripting/QC pipelines)
- Works on M1 Mac (uses `laszip` backend)

## Setup
```bash
git clone ...
cd lidar-metadata-explorer
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run.py