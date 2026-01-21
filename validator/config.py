from __future__ import annotations

# Resolution rules (Day 4)
MAX_SIZE_WARN = 4096
MAX_SIZE_ERROR = 8192

# Map-type format expectations (Day 4, lightweight)
# We treat these as warnings (studios differ).
ALLOWED_EXT_BY_MAP = {
    "BaseColor": {".png", ".tif", ".tiff", ".jpg", ".jpeg"},
    "Normal": {".png", ".tif", ".tiff"},
    "Roughness": {".png", ".tif", ".tiff", ".jpg", ".jpeg"},
    "Metallic": {".png", ".tif", ".tiff", ".jpg", ".jpeg"},
    "AmbientOcclusion": {".png", ".tif", ".tiff", ".jpg", ".jpeg"},
    "ORM": {".png", ".tif", ".tiff"},
    "Emissive": {".png", ".tif", ".tiff", ".jpg", ".jpeg"},
    "Opacity": {".png", ".tif", ".tiff"},
    "Height": {".png", ".tif", ".tiff", ".exr"},
}

SUPPORTED_EXTS = {".png", ".tif", ".tiff", ".jpg", ".jpeg", ".exr"}
