"""Documents and photos on equipment — the API, against the test DB and a temporary
DATA_DIR (conftest.py).  Needs the dev MariaDB container (tooling/dev/dev-db-up.bat)."""

import errno
import os
from io import BytesIO

import pytest
from PIL import Image

import documents
import file_store
from config import MB
from tests.test_documents_core import jpeg_with_size

EQUIPMENT = "/api/equipment"

PDF = b"%PDF-1.4\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"
SIZE_MESSAGE_1_MB = "The file is larger than 1 MB"


def _jpeg(size=(64, 48)):
    out = BytesIO()
    Image.new("RGB", size, (20, 140, 60)).save(out, format="JPEG")
    return out.getvalue()


JPEG = _jpeg()


def _docs_url(node):
    return f"{EQUIPMENT}/{node['id']}/documents"


def _upload(client, node, kind="document", title="Pump manual", data=PDF, filename="manual.pdf", **kwargs):
    form = {"kind": kind, "title": title}
    if data is not None:
        form["file"] = (BytesIO(data), filename)
    return client.post(_docs_url(node), data=form, content_type="multipart/form-data", **kwargs)


def _uploaded(client, node, **kwargs):
    res = _upload(client, node, **kwargs)
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def _list(client, node):
    res = client.get(_docs_url(node))
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def _refusal(res):
    return res.status_code, res.get_json().get("field"), res.get_json()["error"]


def _folder_files(node):
    folder = file_store.node_folder(node["id"])
    return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


def _scrap(admin, node):
    res = admin.put(f"{EQUIPMENT}/{node['id']}", json={"status": "scrapped"})
    assert res.status_code == 200, res.get_json()


@pytest.fixture
def unit(make_unit):
    return make_unit()


@pytest.fixture
def node(make_equipment, unit):
    return make_equipment(unit=unit)


@pytest.fixture
def at_unit(user_with_units, unit):
    """at_unit(role) -> a client for a fresh user of that role holding the node's unit."""
    return lambda role: user_with_units(role, [unit])


@pytest.fixture
def engineer(at_unit):
    return at_unit("maint_engineer")


class TestUploadAndServe:

    def test_pdf_and_jpeg_are_listed_newest_first_and_served(self, engineer, admin, node):
        pdf = _uploaded(admin, node)
        photo = _uploaded(admin, node, kind="photo", title="Nameplate", data=JPEG, filename="IMG_2034.jpg")
        assert (pdf["content_type"], pdf["size_bytes"], pdf["has_thumb"]) == ("application/pdf", len(PDF), False)
        assert (photo["content_type"], photo["has_thumb"], photo["original_name"]) == ("image/jpeg", True,
                                                                                       "IMG_2034.jpg")
        assert pdf["created_by"] == "test_it_admin" and pdf["updated_at"] is None
        assert "stored_name" not in pdf

        listed = _list(engineer, node)
        assert [d["id"] for d in listed["items"]] == [photo["id"], pdf["id"]]
        assert listed["upload_max_mb"] == 20
        assert "stored_name" not in listed["items"][0]

        res = engineer.get(f"{_docs_url(node)}/{pdf['id']}/file")
        assert res.status_code == 200
        assert res.data == PDF
        assert res.headers["Content-Type"] == "application/pdf"
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        cache = res.headers["Cache-Control"]
        assert "private" in cache and "max-age=3600" in cache and "public" not in cache
        assert res.headers["Content-Disposition"].startswith("inline;")
        assert "Pump manual.pdf" in res.headers["Content-Disposition"]
        assert res.headers.get("ETag")

        thumb = engineer.get(f"{_docs_url(node)}/{photo['id']}/thumb")
        assert thumb.status_code == 200
        assert thumb.headers["Content-Type"] == "image/jpeg"
        assert Image.open(BytesIO(thumb.data)).format == "JPEG"
        assert "Nameplate.jpg" in thumb.headers["Content-Disposition"]

    def test_files_are_stored_under_system_names(self, admin, node, db_rows):
        doc = _uploaded(admin, node, filename="../../etc/passwd.pdf")
        assert doc["original_name"] == "passwd.pdf"
        stored = db_rows("SELECT stored_name FROM equipment_documents WHERE id = %s", (doc["id"],))[0]["stored_name"]
        assert len(stored) == 36 and stored.endswith(".pdf")
        assert _folder_files(node) == [stored]

    def test_pdf_has_no_thumbnail(self, admin, node):
        doc = _uploaded(admin, node)
        assert admin.get(f"{_docs_url(node)}/{doc['id']}/thumb").status_code == 404

    def test_a_second_request_with_the_etag_is_304(self, admin, node):
        doc = _uploaded(admin, node)
        url = f"{_docs_url(node)}/{doc['id']}/file"
        etag = admin.get(url).headers["ETag"]
        assert admin.get(url, headers={"If-None-Match": etag}).status_code == 304

    def test_corrupt_jpeg_is_accepted_without_thumbnail(self, admin, node):
        doc = _uploaded(admin, node, kind="photo", data=b"\xff\xd8\xff" + b"not really" * 50, filename="x.jpg")
        assert doc["has_thumb"] is False
        assert admin.get(f"{_docs_url(node)}/{doc['id']}/thumb").status_code == 404
        assert admin.get(f"{_docs_url(node)}/{doc['id']}/file").status_code == 200

    def test_photo_over_the_pixel_cap_is_refused(self, admin, node):
        res = _upload(admin, node, kind="photo", data=jpeg_with_size(8000, 8000), filename="huge.jpg")
        assert _refusal(res) == (400, "file", "Photo too large (64 megapixels)")
        assert _folder_files(node) == []


class TestUploadRefusals:

    @pytest.mark.parametrize("kind, data", [
        ("document", b"PK\x03\x04 a docx renamed to pdf"),
        ("document", b"MZ\x90\x00 an exe"),
        ("photo", PDF),            # types the kind refuses
        ("document", JPEG),
    ])
    def test_wrong_type(self, admin, node, kind, data):
        res = _upload(admin, node, kind=kind, data=data)
        assert _refusal(res) == (400, "file", "Only PDF documents and JPEG, PNG or WebP photos")

    def test_empty_file(self, admin, node):
        assert _refusal(_upload(admin, node, data=b"")) == (400, "file", "The file is empty")

    def test_no_file(self, admin, node):
        assert _refusal(_upload(admin, node, data=None)) == (400, "file", "Choose a file")

    def test_missing_title_and_bad_kind(self, admin, node):
        assert _refusal(_upload(admin, node, title="  ")) == (400, "title", "Title is required")
        assert _refusal(_upload(admin, node, kind="drawing"))[:2] == (400, "kind")

    def test_over_the_limit_by_content_length(self, admin, node, upload_limit_mb):
        upload_limit_mb(1)
        res = _upload(admin, node, data=PDF + b"x" * (MB + 100 * 1024))
        assert _refusal(res) == (400, "file", SIZE_MESSAGE_1_MB)

    def test_over_the_limit_by_reading(self, admin, node, upload_limit_mb):
        upload_limit_mb(1)
        # Within the 64 KB form allowance, so only the read check can catch it
        over = PDF + b"x" * (MB + 1 - len(PDF))
        assert _refusal(_upload(admin, node, data=over)) == (400, "file", SIZE_MESSAGE_1_MB)
        at_limit = PDF + b"x" * (MB - len(PDF))
        assert _upload(admin, node, data=at_limit).status_code == 201

    def test_chunked_request_without_length_is_still_limited(self, admin, node, upload_limit_mb):
        upload_limit_mb(1)
        res = _upload(admin, node, data=PDF + b"x" * (2 * MB),
                      environ_overrides={"HTTP_TRANSFER_ENCODING": "chunked", "wsgi.input_terminated": True})
        assert _refusal(res) == (400, "file", SIZE_MESSAGE_1_MB)

    def test_request_ceiling_backstop_is_json_413(self, app, admin, node, monkeypatch):
        # Below upload_max_mb + 64 KB, so the route's own check lets it through to Werkzeug
        monkeypatch.setitem(app.config, "MAX_CONTENT_LENGTH", 1000)
        res = _upload(admin, node, data=PDF + b"x" * 5000)
        assert _refusal(res) == (413, "file", "The file is larger than 100 MB")

    def test_a_bad_limit_setting_falls_back_to_20(self, admin, node, upload_limit_mb):
        upload_limit_mb("abc")
        assert _list(admin, node)["upload_max_mb"] == 20


class TestAccess:

    def test_another_units_node_is_404(self, admin, make_unit, make_equipment, user_with_units):
        node = make_equipment()
        doc = _uploaded(admin, node)
        outsider = user_with_units("maint_engineer", [make_unit()])
        assert outsider.get(_docs_url(node)).status_code == 404
        assert outsider.get(f"{_docs_url(node)}/{doc['id']}/file").status_code == 404
        assert _upload(outsider, node).status_code == 404
        assert outsider.delete(f"{_docs_url(node)}/{doc['id']}").status_code == 404

    def test_a_user_at_the_unit_can_upload(self, make_unit, make_equipment, user_with_units):
        unit = make_unit()
        node = make_equipment(unit=unit)
        assert _upload(user_with_units("maint_engineer", [unit]), node).status_code == 201

    def test_parts_take_documents_too(self, admin, make_equipment):
        part = make_equipment(parent=make_equipment())
        assert _upload(admin, part).status_code == 201

    def test_operator_reads_but_cannot_upload_edit_or_remove(self, admin, at_unit, node):
        doc = _uploaded(admin, node)
        operator = at_unit("maint_operator")
        assert operator.get(_docs_url(node)).status_code == 200
        assert operator.get(f"{_docs_url(node)}/{doc['id']}/file").status_code == 200
        assert _upload(operator, node).status_code == 403
        assert operator.put(f"{_docs_url(node)}/{doc['id']}", json={"title": "x"}).status_code == 403
        assert operator.delete(f"{_docs_url(node)}/{doc['id']}").status_code == 403

    def test_a_doc_id_of_another_node_is_404(self, admin, make_equipment):
        node_a, node_b = make_equipment(), make_equipment()
        doc = _uploaded(admin, node_a, kind="photo", data=JPEG, filename="a.jpg")
        assert admin.get(f"{_docs_url(node_b)}/{doc['id']}/file").status_code == 404
        assert admin.get(f"{_docs_url(node_b)}/{doc['id']}/thumb").status_code == 404
        assert admin.put(f"{_docs_url(node_b)}/{doc['id']}", json={"title": "x"}).status_code == 404
        assert admin.delete(f"{_docs_url(node_b)}/{doc['id']}").status_code == 404

    def test_unknown_node_is_404(self, admin):
        assert admin.get(f"{EQUIPMENT}/999999999/documents").status_code == 404


class TestScrapped:

    def test_no_changes_but_still_viewable(self, admin, node):
        doc = _uploaded(admin, node)
        _scrap(admin, node)
        assert _upload(admin, node).status_code == 409
        assert admin.put(f"{_docs_url(node)}/{doc['id']}", json={"title": "New"}).status_code == 409
        assert admin.delete(f"{_docs_url(node)}/{doc['id']}").status_code == 409
        assert [d["id"] for d in _list(admin, node)["items"]] == [doc["id"]]
        assert admin.get(f"{_docs_url(node)}/{doc['id']}/file").status_code == 200

    def test_scrapped_while_uploading_leaves_no_file(self, admin, node, monkeypatch):
        """The locked re-check decides: a node scrapped after the early check refuses the
        insert, and the files already written are removed."""
        real_write = file_store.write_file

        def write_then_scrap(*args):
            path = real_write(*args)
            _scrap(admin, node)
            return path
        monkeypatch.setattr(file_store, "write_file", write_then_scrap)
        assert _upload(admin, node).status_code == 409
        assert _folder_files(node) == []


    def test_moved_to_another_unit_while_uploading_leaves_no_file(self, engineer, node, make_unit, db_rows,
                                                                  monkeypatch):
        """The locked re-check covers unit access too: a node moved out of the user's unit
        after the early check refuses the insert (404), and the written files are removed."""
        real_write = file_store.write_file
        other_unit = make_unit()

        def write_then_move(*args):
            path = real_write(*args)
            # Straight SQL: a nested API call as admin would share Flask's g with this request
            db_rows("UPDATE equipment SET unit_id = %s WHERE id = %s", (other_unit["id"], node["id"]))
            return path
        monkeypatch.setattr(file_store, "write_file", write_then_move)
        assert _upload(engineer, node).status_code == 404
        assert _folder_files(node) == []


class TestEditTitle:

    def _put(self, client, node, doc, body):
        return client.put(f"{_docs_url(node)}/{doc['id']}", json=body)

    def test_title_is_changed_and_stamped(self, engineer, node):
        doc = _uploaded(engineer, node, kind="photo", title="IMG_2034", data=JPEG, filename="IMG_2034.jpg")
        res = self._put(engineer, node, doc, {"title": "  Nameplate ", "kind": "document"})
        assert res.status_code == 200, res.get_json()
        item = res.get_json()
        assert (item["title"], item["kind"], item["updated_by"]) == ("Nameplate", "photo", doc["created_by"])
        assert item["updated_at"] and item["original_name"] == "IMG_2034.jpg"
        assert _list(engineer, node)["items"][0]["title"] == "Nameplate"
        file_res = engineer.get(f"{_docs_url(node)}/{doc['id']}/file")
        assert "Nameplate.jpg" in file_res.headers["Content-Disposition"]

    def test_saving_the_same_title_is_200(self, admin, node):
        doc = _uploaded(admin, node)
        assert self._put(admin, node, doc, {"title": doc["title"]}).status_code == 200

    @pytest.mark.parametrize("title", ["", "   ", "x" * 201, None])
    def test_bad_title_is_400(self, admin, node, title):
        doc = _uploaded(admin, node)
        res = self._put(admin, node, doc, {"title": title})
        assert _refusal(res)[:2] == (400, "title")

    def test_not_a_json_object_is_400(self, admin, node):
        doc = _uploaded(admin, node)
        assert admin.put(f"{_docs_url(node)}/{doc['id']}", data="x").status_code == 400

    def test_removed_document_is_404(self, admin, node):
        doc = _uploaded(admin, node)
        assert admin.delete(f"{_docs_url(node)}/{doc['id']}").status_code == 204
        assert self._put(admin, node, doc, {"title": "New"}).status_code == 404


class TestRemove:

    def test_remove_hides_but_keeps(self, engineer, node, db_rows):
        doc = _uploaded(engineer, node)
        files_before = _folder_files(node)
        assert engineer.delete(f"{_docs_url(node)}/{doc['id']}").status_code == 204
        assert _list(engineer, node)["items"] == []
        assert _folder_files(node) == files_before != []
        row = db_rows("SELECT removed_at, removed_by FROM equipment_documents WHERE id = %s", (doc["id"],))[0]
        assert row["removed_by"] == doc["created_by"] and row["removed_at"] is not None
        assert engineer.delete(f"{_docs_url(node)}/{doc['id']}").status_code == 404
        assert engineer.get(f"{_docs_url(node)}/{doc['id']}/file").status_code == 404

    def test_history_is_unchanged(self, admin, node):
        before = admin.get(f"{EQUIPMENT}/{node['id']}").get_json()["events"]
        doc = _uploaded(admin, node)
        admin.delete(f"{_docs_url(node)}/{doc['id']}")
        assert admin.get(f"{EQUIPMENT}/{node['id']}").get_json()["events"] == before


class TestFailures:

    def test_insert_failure_leaves_no_file(self, admin, node, monkeypatch):
        def fail(*args):
            raise RuntimeError("forced")
        monkeypatch.setattr(documents, "insert_row", fail)
        with pytest.raises(RuntimeError):
            _upload(admin, node, kind="photo", data=JPEG, filename="a.jpg")
        assert _folder_files(node) == []

    def test_storage_error_is_503_and_leaves_nothing(self, admin, node, monkeypatch, db_rows, caplog):
        real_write = file_store.write_file

        def fail_on_thumbnail(node_id, name, data):
            if name.endswith(".thumb.jpg"):
                raise OSError(errno.EIO, "Input/output error", name)
            return real_write(node_id, name, data)
        monkeypatch.setattr(file_store, "write_file", fail_on_thumbnail)
        res = _upload(admin, node, kind="photo", data=JPEG, filename="a.jpg")
        assert _refusal(res) == (503, None, "File storage is unavailable — try again later")
        assert _folder_files(node) == []
        assert db_rows("SELECT id FROM equipment_documents WHERE equipment_id = %s", (node["id"],)) == ()
        assert any(r.levelname == "ERROR" and "errno 5" in r.getMessage() for r in caplog.records)

    def test_file_missing_on_disk_is_404(self, admin, node, db_rows):
        doc = _uploaded(admin, node)
        stored = db_rows("SELECT stored_name FROM equipment_documents WHERE id = %s", (doc["id"],))[0]["stored_name"]
        os.remove(file_store.file_path(node["id"], stored))
        res = admin.get(f"{_docs_url(node)}/{doc['id']}/file")
        assert (res.status_code, res.get_json()["error"]) == (404, "File missing")
