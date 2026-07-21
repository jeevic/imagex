"""End-to-end endpoint tests via the Flask test client (real image processing, no mocks)."""
import io

from PIL import Image


def test_healthcheck(client):
    resp = client.get("/healthcheck")
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == "ok"


def test_info_endpoint_jpeg(client, jpeg_bytes):
    resp = client.post("/v1/image/info", data={"file": (jpeg_bytes, "t.jpg")})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["format"] == "JPEG"
    assert body["data"]["width"] == 320
    assert body["data"]["height"] == 240


def test_process_endpoint_resize_webp(client, jpeg_bytes):
    resp = client.post(
        "/v1/image/process",
        data={"file": (jpeg_bytes, "t.jpg"), "x-image-process": "resize,m_lfit,w_200,h_100/format,f_WEBP"},
    )
    assert resp.status_code == 200
    im = Image.open(io.BytesIO(resp.get_data()))
    assert im.format == "WEBP"
    # lfit of 320x240 into a 200x100 box is height-limited -> 133x100 (not the plan's 200x150, which is mfit)
    assert im.size == (133, 100)


def test_process_endpoint_avif(client, jpeg_bytes):
    resp = client.post(
        "/v1/image/process",
        data={"file": (jpeg_bytes, "t.jpg"), "x-image-process": "format,f_AVIF"},
    )
    assert resp.status_code == 200
    im = Image.open(io.BytesIO(resp.get_data()))
    assert im.format == "AVIF"
    assert im.size == (320, 240)


def test_info_endpoint_heic(client, heic_bytes):
    """HEIC input decoding works via the centralized register_heif_opener (Task 4)."""
    resp = client.post("/v1/image/info", data={"file": (heic_bytes, "t.heic")})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["data"]["format"] == "HEIF"  # Pillow reports HEIF for HEIC containers
    assert body["data"]["width"] == 100
