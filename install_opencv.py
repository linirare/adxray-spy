"""Download opencv-python wheel and manually extract cv2.pyd"""
import urllib.request
import zipfile
import shutil
import os
import sys

VENV_SITE = os.path.expanduser("~/MediaCrawler/.venv/Lib/site-packages")
WHEEL_URL = "https://files.pythonhosted.org/packages/45/09/e2f9e5731475925584356baf5d7002c0b5d5a65ee2b5e4d5e4a3032d3d4b/opencv_python-4.9.0.80-cp37-abi3-win_amd64.whl"

wheel_path = os.path.join(VENV_SITE, "opencv_wheel.zip")

try:
    print("Downloading opencv-python wheel...")
    urllib.request.urlretrieve(WHEEL_URL, wheel_path)
    print("Extracting cv2.pyd...")
    with zipfile.ZipFile(wheel_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('.pyd') or 'cv2' in name:
                print(f"  {name}")
        zf.extract('cv2/cv2.pyd', VENV_SITE)
    dest = os.path.join(VENV_SITE, 'cv2', 'cv2.pyd')
    if os.path.exists(dest):
        size = os.path.getsize(dest)
        print(f"OK: cv2.pyd extracted ({size / 1024 / 1024:.1f} MB)")
    else:
        print("FAIL: cv2.pyd not found after extraction")
except Exception as e:
    print(f"Error: {e}")
finally:
    if os.path.exists(wheel_path):
        os.remove(wheel_path)
