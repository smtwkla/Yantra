"""Helpers shared by the document API tests (test_documents_api.py, test_removed_documents_api.py).
A plain module rather than conftest.py, which pytest advises against importing from."""

import os
from io import BytesIO

from PIL import Image

import file_store

EQUIPMENT = "/api/equipment"

PDF = b"%PDF-1.4\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"


def image_bytes(img, fmt, **params):
    out = BytesIO()
    img.save(out, format=fmt, **params)
    return out.getvalue()


def jpeg(size=(64, 48)):
    return image_bytes(Image.new("RGB", size, (20, 140, 60)), "JPEG")


JPEG = jpeg()


def jpeg_with_size(width, height):
    """A 1 x 1 JPEG whose SOF0 header claims width x height — cheap, nothing is allocated."""
    data = bytearray(image_bytes(Image.new("RGB", (1, 1)), "JPEG"))
    sof = data.index(b"\xff\xc0")
    # FFC0, length (2), precision (1), height (2), width (2)
    data[sof + 5:sof + 7] = height.to_bytes(2, "big")
    data[sof + 7:sof + 9] = width.to_bytes(2, "big")
    return bytes(data)


def docs_url(node):
    return f"{EQUIPMENT}/{node['id']}/documents"


def model_docs_url(model):
    return f"/api/masters/equipment-models/{model['id']}/documents"


def upload_to(client, url, kind="document", title="Pump manual", data=PDF, filename="manual.pdf", **kwargs):
    """Upload to any owner's documents collection URL (a node's or a model's, S012)."""
    form = {"kind": kind, "title": title}
    if data is not None:
        form["file"] = (BytesIO(data), filename)
    return client.post(url, data=form, content_type="multipart/form-data", **kwargs)


def uploaded_to(client, url, **kwargs):
    res = upload_to(client, url, **kwargs)
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def listed_at(client, url):
    res = client.get(url)
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def upload(client, node, **kwargs):
    return upload_to(client, docs_url(node), **kwargs)


def uploaded(client, node, **kwargs):
    return uploaded_to(client, docs_url(node), **kwargs)


def listed(client, node):
    return listed_at(client, docs_url(node))


def refusal(res):
    return res.status_code, res.get_json().get("field"), res.get_json()["error"]


def owner_files(owner, owner_id):
    """The files in an owner's folder (file_store owner: equipment or model)."""
    folder = file_store.owner_folder(owner, owner_id)
    return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


def folder_files(node):
    return owner_files("equipment", node["id"])


def scrap(admin, node):
    res = admin.put(f"{EQUIPMENT}/{node['id']}", json={"lifecycle": "scrapped"})
    assert res.status_code == 200, res.get_json()
