"""Documents and photos on equipment — the API, against the test DB and a temporary
DATA_DIR (conftest.py).  Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).
Node documents (S006); model documents and the node's inherited group (S012) at the end."""

import errno
import os
from io import BytesIO

import pymysql
import pytest
from PIL import Image

import documents
import file_store
from config import MB
from tests.conftest import SERVER_ERROR, server_error
from tests.documents_helpers import (
    EQUIPMENT, JPEG, PDF, docs_url, folder_files, jpeg_with_size, listed, listed_at, model_docs_url, owner_files,
    refusal, scrap, upload, upload_to, uploaded, uploaded_to,
)

SIZE_MESSAGE_1_MB = "The file is larger than 1 MB"


@pytest.fixture
def engineer(at_unit):
    return at_unit("maint_engineer")


class TestUploadAndServe:

    def test_pdf_and_jpeg_are_listed_newest_first_and_served(self, engineer, admin, node):
        pdf = uploaded(admin, node)
        photo = uploaded(admin, node, kind="photo", title="Nameplate", data=JPEG, filename="IMG_2034.jpg")
        assert (pdf["content_type"], pdf["size_bytes"], pdf["has_thumb"]) == ("application/pdf", len(PDF), False)
        assert (photo["content_type"], photo["has_thumb"], photo["original_name"]) == ("image/jpeg", True,
                                                                                       "IMG_2034.jpg")
        assert pdf["created_by"] == "test_it_admin" and pdf["updated_at"] is None
        assert "stored_name" not in pdf

        page = listed(engineer, node)
        assert [d["id"] for d in page["items"]] == [photo["id"], pdf["id"]]
        assert page["upload_max_mb"] == 20
        assert "stored_name" not in page["items"][0]

        res = engineer.get(f"{docs_url(node)}/{pdf['id']}/file")
        assert res.status_code == 200
        assert res.data == PDF
        assert res.headers["Content-Type"] == "application/pdf"
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        cache = res.headers["Cache-Control"]
        assert "private" in cache and "max-age=3600" in cache and "public" not in cache
        assert res.headers["Content-Disposition"].startswith("inline;")
        assert "Pump manual.pdf" in res.headers["Content-Disposition"]
        assert res.headers.get("ETag")

        thumb = engineer.get(f"{docs_url(node)}/{photo['id']}/thumb")
        assert thumb.status_code == 200
        assert thumb.headers["Content-Type"] == "image/jpeg"
        assert Image.open(BytesIO(thumb.data)).format == "JPEG"
        assert "Nameplate.jpg" in thumb.headers["Content-Disposition"]

    def test_files_are_stored_under_system_names(self, admin, node, db_rows):
        doc = uploaded(admin, node, filename="../../etc/passwd.pdf")
        assert doc["original_name"] == "passwd.pdf"
        stored = db_rows("SELECT stored_name FROM equipment_documents WHERE id = %s", (doc["id"],))[0]["stored_name"]
        assert len(stored) == 36 and stored.endswith(".pdf")
        assert folder_files(node) == [stored]

    def test_pdf_has_no_thumbnail(self, admin, node):
        doc = uploaded(admin, node)
        assert admin.get(f"{docs_url(node)}/{doc['id']}/thumb").status_code == 404

    def test_a_second_request_with_the_etag_is_304(self, admin, node):
        doc = uploaded(admin, node)
        url = f"{docs_url(node)}/{doc['id']}/file"
        etag = admin.get(url).headers["ETag"]
        assert admin.get(url, headers={"If-None-Match": etag}).status_code == 304

    def test_corrupt_jpeg_is_accepted_without_thumbnail(self, admin, node):
        doc = uploaded(admin, node, kind="photo", data=b"\xff\xd8\xff" + b"not really" * 50, filename="x.jpg")
        assert doc["has_thumb"] is False
        assert admin.get(f"{docs_url(node)}/{doc['id']}/thumb").status_code == 404
        assert admin.get(f"{docs_url(node)}/{doc['id']}/file").status_code == 200

    def test_photo_over_the_pixel_cap_is_refused(self, admin, node):
        res = upload(admin, node, kind="photo", data=jpeg_with_size(8000, 8000), filename="huge.jpg")
        assert refusal(res) == (400, "file", "Photo too large (64 megapixels). Take it at a lower resolution.")
        assert folder_files(node) == []


class TestUploadRefusals:

    @pytest.mark.parametrize("kind, data", [
        ("document", b"PK\x03\x04 a docx renamed to pdf"),
        ("document", b"MZ\x90\x00 an exe"),
        ("photo", PDF),            # types the kind refuses
        ("document", JPEG),
    ])
    def test_wrong_type(self, admin, node, kind, data):
        res = upload(admin, node, kind=kind, data=data)
        assert refusal(res) == (400, "file", "This file can't be added. Use a PDF, or a JPEG, PNG or WebP photo.")

    def test_empty_file(self, admin, node):
        assert refusal(upload(admin, node, data=b"")) == (400, "file", "The file is empty")

    def test_no_file(self, admin, node):
        assert refusal(upload(admin, node, data=None)) == (400, "file", "Choose a file")

    def test_missing_title_and_bad_kind(self, admin, node):
        assert refusal(upload(admin, node, title="  ")) == (400, "title", "Title is required")
        assert refusal(upload(admin, node, kind="drawing"))[:2] == (400, "kind")

    def test_over_the_limit_by_content_length(self, admin, node, upload_limit_mb):
        upload_limit_mb(1)
        res = upload(admin, node, data=PDF + b"x" * (MB + 100 * 1024))
        assert refusal(res) == (400, "file", SIZE_MESSAGE_1_MB)

    def test_over_the_limit_by_reading(self, admin, node, upload_limit_mb):
        upload_limit_mb(1)
        # Within the 64 KB form allowance, so only the read check can catch it
        over = PDF + b"x" * (MB + 1 - len(PDF))
        assert refusal(upload(admin, node, data=over)) == (400, "file", SIZE_MESSAGE_1_MB)
        at_limit = PDF + b"x" * (MB - len(PDF))
        assert upload(admin, node, data=at_limit).status_code == 201

    def test_chunked_request_without_length_is_still_limited(self, admin, node, upload_limit_mb):
        upload_limit_mb(1)
        res = upload(admin, node, data=PDF + b"x" * (2 * MB),
                      environ_overrides={"HTTP_TRANSFER_ENCODING": "chunked", "wsgi.input_terminated": True})
        assert refusal(res) == (400, "file", SIZE_MESSAGE_1_MB)

    def test_request_ceiling_backstop_is_json_413(self, app, admin, node, monkeypatch):
        # Below upload_max_mb + 64 KB, so the route's own check lets it through to Werkzeug
        monkeypatch.setitem(app.config, "MAX_CONTENT_LENGTH", 1000)
        res = upload(admin, node, data=PDF + b"x" * 5000)
        assert refusal(res) == (413, "file", "The file is larger than 100 MB")

    def test_a_bad_limit_setting_falls_back_to_20(self, admin, node, upload_limit_mb):
        upload_limit_mb("abc")
        assert listed(admin, node)["upload_max_mb"] == 20


class TestAccess:

    def test_another_units_node_is_404(self, admin, make_unit, make_equipment, user_with_units):
        node = make_equipment()
        doc = uploaded(admin, node)
        outsider = user_with_units("maint_engineer", [make_unit()])
        assert outsider.get(docs_url(node)).status_code == 404
        assert outsider.get(f"{docs_url(node)}/{doc['id']}/file").status_code == 404
        assert upload(outsider, node).status_code == 404
        assert outsider.delete(f"{docs_url(node)}/{doc['id']}").status_code == 404

    def test_a_user_at_the_unit_canupload(self, make_unit, make_equipment, user_with_units):
        unit = make_unit()
        node = make_equipment(unit=unit)
        assert upload(user_with_units("maint_engineer", [unit]), node).status_code == 201

    def test_parts_take_documents_too(self, admin, make_equipment):
        part = make_equipment(parent=make_equipment())
        assert upload(admin, part).status_code == 201

    def test_operator_reads_but_cannot_upload_edit_or_remove(self, admin, at_unit, node):
        doc = uploaded(admin, node)
        operator = at_unit("maint_operator")
        assert operator.get(docs_url(node)).status_code == 200
        assert operator.get(f"{docs_url(node)}/{doc['id']}/file").status_code == 200
        assert upload(operator, node).status_code == 403
        assert operator.put(f"{docs_url(node)}/{doc['id']}", json={"title": "x"}).status_code == 403
        assert operator.delete(f"{docs_url(node)}/{doc['id']}").status_code == 403

    def test_a_doc_id_of_another_node_is_404(self, admin, make_equipment):
        node_a, node_b = make_equipment(), make_equipment()
        doc = uploaded(admin, node_a, kind="photo", data=JPEG, filename="a.jpg")
        assert admin.get(f"{docs_url(node_b)}/{doc['id']}/file").status_code == 404
        assert admin.get(f"{docs_url(node_b)}/{doc['id']}/thumb").status_code == 404
        assert admin.put(f"{docs_url(node_b)}/{doc['id']}", json={"title": "x"}).status_code == 404
        assert admin.delete(f"{docs_url(node_b)}/{doc['id']}").status_code == 404

    def test_unknown_node_is_404(self, admin):
        assert admin.get(f"{EQUIPMENT}/999999999/documents").status_code == 404


class TestScrapped:

    def test_no_changes_but_still_viewable(self, admin, node):
        doc = uploaded(admin, node)
        scrap(admin, node)
        assert upload(admin, node).status_code == 409
        assert admin.put(f"{docs_url(node)}/{doc['id']}", json={"title": "New"}).status_code == 409
        assert admin.delete(f"{docs_url(node)}/{doc['id']}").status_code == 409
        assert [d["id"] for d in listed(admin, node)["items"]] == [doc["id"]]
        assert admin.get(f"{docs_url(node)}/{doc['id']}/file").status_code == 200

    def test_scrapped_while_uploading_leaves_no_file(self, admin, node, monkeypatch):
        """The locked re-check decides: a node scrapped after the early check refuses the
        insert, and the files already written are removed."""
        real_write = file_store.write_file

        def write_then_scrap(*args):
            path = real_write(*args)
            scrap(admin, node)
            return path
        monkeypatch.setattr(file_store, "write_file", write_then_scrap)
        assert upload(admin, node).status_code == 409
        assert folder_files(node) == []


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
        assert upload(engineer, node).status_code == 404
        assert folder_files(node) == []


class TestEditTitle:

    def _put(self, client, node, doc, body):
        return client.put(f"{docs_url(node)}/{doc['id']}", json=body)

    def test_title_is_changed_and_stamped(self, engineer, node):
        doc = uploaded(engineer, node, kind="photo", title="IMG_2034", data=JPEG, filename="IMG_2034.jpg")
        res = self._put(engineer, node, doc, {"title": "  Nameplate ", "kind": "document"})
        assert res.status_code == 200, res.get_json()
        item = res.get_json()
        assert (item["title"], item["kind"], item["updated_by"]) == ("Nameplate", "photo", doc["created_by"])
        assert item["updated_at"] and item["original_name"] == "IMG_2034.jpg"
        assert listed(engineer, node)["items"][0]["title"] == "Nameplate"
        file_res = engineer.get(f"{docs_url(node)}/{doc['id']}/file")
        assert "Nameplate.jpg" in file_res.headers["Content-Disposition"]

    def test_saving_the_same_title_is_200(self, admin, node):
        doc = uploaded(admin, node)
        assert self._put(admin, node, doc, {"title": doc["title"]}).status_code == 200

    @pytest.mark.parametrize("title", ["", "   ", "x" * 201, None])
    def test_bad_title_is_400(self, admin, node, title):
        doc = uploaded(admin, node)
        res = self._put(admin, node, doc, {"title": title})
        assert refusal(res)[:2] == (400, "title")

    def test_not_a_json_object_is_400(self, admin, node):
        doc = uploaded(admin, node)
        assert admin.put(f"{docs_url(node)}/{doc['id']}", data="x").status_code == 400

    def test_removed_document_is_404(self, admin, node):
        doc = uploaded(admin, node)
        assert admin.delete(f"{docs_url(node)}/{doc['id']}").status_code == 204
        assert self._put(admin, node, doc, {"title": "New"}).status_code == 404


class TestRemove:

    def test_remove_hides_but_keeps(self, engineer, node, db_rows):
        doc = uploaded(engineer, node)
        files_before = folder_files(node)
        assert engineer.delete(f"{docs_url(node)}/{doc['id']}").status_code == 204
        assert listed(engineer, node)["items"] == []
        assert folder_files(node) == files_before != []
        row = db_rows("SELECT removed_at, removed_by FROM equipment_documents WHERE id = %s", (doc["id"],))[0]
        assert row["removed_by"] == doc["created_by"] and row["removed_at"] is not None
        assert engineer.delete(f"{docs_url(node)}/{doc['id']}").status_code == 404
        assert engineer.get(f"{docs_url(node)}/{doc['id']}/file").status_code == 404

    def test_history_is_unchanged(self, admin, node):
        before = admin.get(f"{EQUIPMENT}/{node['id']}").get_json()["events"]
        doc = uploaded(admin, node)
        admin.delete(f"{docs_url(node)}/{doc['id']}")
        assert admin.get(f"{EQUIPMENT}/{node['id']}").get_json()["events"] == before


class TestFailures:

    def test_insert_failure_leaves_no_file(self, admin, node, monkeypatch):
        def fail(*args):
            raise RuntimeError("forced")
        monkeypatch.setattr(documents, "insert_row", fail)
        # The 500 is JSON (S025 § 1.3); the rollback after it is what this tests
        assert server_error(upload(admin, node, kind="photo", data=JPEG, filename="a.jpg")) == SERVER_ERROR
        assert folder_files(node) == []

    def test_storage_error_is_503_and_leaves_nothing(self, admin, node, monkeypatch, db_rows, caplog):
        real_write = file_store.write_file

        def fail_on_thumbnail(owner, owner_id, name, data):
            if name.endswith(".thumb.jpg"):
                raise OSError(errno.EIO, "Input/output error", name)
            return real_write(owner, owner_id, name, data)
        monkeypatch.setattr(file_store, "write_file", fail_on_thumbnail)
        res = upload(admin, node, kind="photo", data=JPEG, filename="a.jpg")
        assert refusal(res) == (503, None, "File storage is unavailable — try again later")
        assert folder_files(node) == []
        assert db_rows("SELECT id FROM equipment_documents WHERE equipment_id = %s", (node["id"],)) == ()
        assert any(r.levelname == "ERROR" and "errno 5" in r.getMessage() for r in caplog.records)

    def test_file_missing_on_disk_is_404(self, admin, node, db_rows):
        doc = uploaded(admin, node)
        stored = db_rows("SELECT stored_name FROM equipment_documents WHERE id = %s", (doc["id"],))[0]["stored_name"]
        os.remove(file_store.file_path("equipment", node["id"], stored))
        res = admin.get(f"{docs_url(node)}/{doc['id']}/file")
        assert (res.status_code, res.get_json()["error"]) == (404, "File missing")


# ---------------------------------------------------------------------------
# Documents on equipment models (S012)
# ---------------------------------------------------------------------------

MASTERS = "/api/masters"


def doc_ids(items):
    return [d["id"] for d in items]


class TestModelDocuments:

    def test_upload_list_open_thumb_edit_and_remove(self, role_client, make_model, db_rows):
        engineer = role_client("maint_engineer")
        model = make_model()
        url = model_docs_url(model)
        pdf = uploaded_to(engineer, url)
        photo = uploaded_to(engineer, url, kind="photo", title="Nameplate", data=JPEG, filename="plate.jpg")
        row = db_rows("SELECT equipment_id, model_id FROM equipment_documents WHERE id = %s", (pdf["id"],))[0]
        assert row == {"equipment_id": None, "model_id": model["id"]}

        page = listed_at(engineer, url)
        assert doc_ids(page["items"]) == [photo["id"], pdf["id"]]
        assert page["upload_max_mb"] == 20
        assert "inherited" not in page

        res = engineer.get(f"{url}/{pdf['id']}/file")
        assert (res.status_code, res.data, res.headers["Content-Type"]) == (200, PDF, "application/pdf")
        assert "private" in res.headers["Cache-Control"]
        thumb = engineer.get(f"{url}/{photo['id']}/thumb")
        assert (thumb.status_code, Image.open(BytesIO(thumb.data)).format) == (200, "JPEG")

        res = engineer.put(f"{url}/{pdf['id']}", json={"title": "Manual rev B"})
        assert (res.status_code, res.get_json()["title"]) == (200, "Manual rev B")

        files_before = owner_files("model", model["id"])
        assert len(files_before) == 3   # the PDF, the photo and its thumbnail
        assert engineer.delete(f"{url}/{pdf['id']}").status_code == 204
        assert doc_ids(listed_at(engineer, url)["items"]) == [photo["id"]]
        assert owner_files("model", model["id"]) == files_before
        assert engineer.get(f"{url}/{pdf['id']}/file").status_code == 404
        assert engineer.delete(f"{url}/{pdf['id']}").status_code == 404

    def test_unknown_model_is_404(self, admin):
        url = f"{MASTERS}/equipment-models/999999999/documents"
        assert admin.get(url).status_code == 404
        assert upload_to(admin, url).status_code == 404
        assert admin.get(f"{url}/1/file").status_code == 404
        assert admin.put(f"{url}/1", json={"title": "x"}).status_code == 404
        assert admin.delete(f"{url}/1").status_code == 404

    def test_a_doc_id_of_another_owner_is_404(self, admin, make_model, make_equipment):
        model, other_model = make_model(), make_model()
        node = make_equipment(model=model)
        node_doc = uploaded(admin, node)
        model_doc = uploaded_to(admin, model_docs_url(model))
        for url, doc in ((model_docs_url(model), node_doc),          # a node's document through its model
                         (model_docs_url(other_model), model_doc),   # a model's through another model
                         (docs_url(node), model_doc)):               # a model's through its node
            assert admin.get(f"{url}/{doc['id']}/file").status_code == 404
            assert admin.put(f"{url}/{doc['id']}", json={"title": "x"}).status_code == 404
            assert admin.delete(f"{url}/{doc['id']}").status_code == 404

    def test_an_inactive_model_keeps_editable_documents(self, admin, make_model):
        model = make_model()
        assert admin.put(f"{MASTERS}/equipment-models/{model['id']}", json={"active": False}).status_code == 200
        doc = uploaded_to(admin, model_docs_url(model))
        assert doc_ids(listed_at(admin, model_docs_url(model))["items"]) == [doc["id"]]
        assert admin.delete(f"{model_docs_url(model)}/{doc['id']}").status_code == 204


class TestInheritedOnTheNode:

    def test_the_model_group_with_its_label_and_path(self, admin, make_manufacturer, make_model, make_equipment):
        maker = make_manufacturer()
        model = make_model(manufacturer=maker)
        node = make_equipment(model=model)
        own = uploaded(admin, node, title="Test certificate")
        manuals = [uploaded_to(admin, model_docs_url(model), title=t) for t in ("Manual", "Parts list")]

        page = listed(admin, node)
        assert doc_ids(page["items"]) == [own["id"]]
        group = page["inherited"][0]
        assert len(page["inherited"]) == 1
        assert {key: group[key] for key in ("owner", "id", "label", "path")} == {
            "owner": "model", "id": model["id"], "label": f"{maker['name']} {model['designation']}",
            "path": model_docs_url(model)}
        assert doc_ids(group["items"]) == [manuals[1]["id"], manuals[0]["id"]]   # newest first
        # The frontend joins path, the id and /file
        assert admin.get(f"{group['path']}/{manuals[0]['id']}/file").data == PDF

    def test_absent_when_the_model_has_no_documents_and_removed_ones_are_left_out(self, admin, make_model,
                                                                                  make_equipment):
        model = make_model()
        node = make_equipment(model=model)
        assert listed(admin, node)["inherited"] == []
        kept, removed = uploaded_to(admin, model_docs_url(model)), uploaded_to(admin, model_docs_url(model))
        assert admin.delete(f"{model_docs_url(model)}/{removed['id']}").status_code == 204
        assert doc_ids(listed(admin, node)["inherited"][0]["items"]) == [kept["id"]]

    def test_follows_a_model_change_at_once(self, admin, make_model, make_equipment):
        ga37, ga55 = make_model(), make_model()
        doc37, doc55 = uploaded_to(admin, model_docs_url(ga37)), uploaded_to(admin, model_docs_url(ga55))
        node = make_equipment(model=ga37)
        assert doc_ids(listed(admin, node)["inherited"][0]["items"]) == [doc37["id"]]
        assert admin.put(f"{EQUIPMENT}/{node['id']}", json={"model_id": ga55["id"]}).status_code == 200
        assert doc_ids(listed(admin, node)["inherited"][0]["items"]) == [doc55["id"]]

    def test_a_part_shows_its_own_models_documents_not_its_parents(self, admin, make_model, make_equipment):
        parent_model = make_model()
        uploaded_to(admin, model_docs_url(parent_model))
        mill = make_equipment(model=parent_model)
        part = make_equipment(parent=mill)
        assert listed(admin, part)["inherited"] == []


class TestModelDocumentAccess:

    def test_an_operator_reads_model_documents_but_cannot_change_them(self, admin, role_client, make_model):
        model = make_model()
        url = model_docs_url(model)
        doc = uploaded_to(admin, url)
        operator = role_client("maint_operator")
        assert operator.get(url).status_code == 200
        assert operator.get(f"{url}/{doc['id']}/file").status_code == 200
        assert upload_to(operator, url).status_code == 403
        assert operator.put(f"{url}/{doc['id']}", json={"title": "x"}).status_code == 403
        assert operator.delete(f"{url}/{doc['id']}").status_code == 403

    def test_a_node_at_another_site_is_404_while_its_models_documents_stay_reachable(
            self, admin, make_unit, make_model, make_equipment, user_with_units):
        """The stated ISO 27001 A.8.3 decision (S012 § 2): model documents at every site."""
        model = make_model()
        node = make_equipment(model=model)
        doc = uploaded_to(admin, model_docs_url(model))
        outsider = user_with_units("maint_engineer", [make_unit()])
        assert outsider.get(docs_url(node)).status_code == 404
        assert outsider.get(model_docs_url(model)).status_code == 200
        assert outsider.get(f"{model_docs_url(model)}/{doc['id']}/file").status_code == 200
        # An engineer at one site maintains model documents (equipment:edit held anywhere)
        assert upload_to(outsider, model_docs_url(model)).status_code == 201


class TestModelDocumentFailures:

    def test_insert_failure_leaves_no_file(self, admin, make_model, monkeypatch):
        model = make_model()

        def fail(*args):
            raise RuntimeError("forced")
        monkeypatch.setattr(documents, "insert_row", fail)
        # The 500 is JSON (S025 § 1.3); the rollback after it is what this tests
        res = upload_to(admin, model_docs_url(model), kind="photo", data=JPEG, filename="a.jpg")
        assert server_error(res) == SERVER_ERROR
        assert owner_files("model", model["id"]) == []

    def test_storage_error_is_503_and_leaves_nothing(self, admin, make_model, monkeypatch, db_rows):
        model = make_model()
        real_write = file_store.write_file

        def fail_on_thumbnail(owner, owner_id, name, data):
            if name.endswith(".thumb.jpg"):
                raise OSError(errno.EIO, "Input/output error", name)
            return real_write(owner, owner_id, name, data)
        monkeypatch.setattr(file_store, "write_file", fail_on_thumbnail)
        res = upload_to(admin, model_docs_url(model), kind="photo", data=JPEG, filename="a.jpg")
        assert refusal(res) == (503, None, "File storage is unavailable — try again later")
        assert owner_files("model", model["id"]) == []
        assert db_rows("SELECT id FROM equipment_documents WHERE model_id = %s", (model["id"],)) == ()


class TestOwnerCheckConstraint:

    @pytest.mark.parametrize("owners", ["two", "none"])
    def test_exactly_one_owner_holds_when_the_shell_is_bypassed(self, make_model, make_equipment, db_rows,
                                                                uniq, owners):
        model = make_model()
        node = make_equipment(model=model)
        equipment_id, model_id = (node["id"], model["id"]) if owners == "two" else (None, None)
        with pytest.raises(pymysql.err.OperationalError) as caught:
            db_rows("INSERT INTO equipment_documents (equipment_id, model_id, kind, title, original_name, stored_name,"
                    " content_type, size_bytes, created_by) VALUES (%s, %s, 'document', 'x', 'x.pdf', %s,"
                    " 'application/pdf', 1, 'test')", (equipment_id, model_id, f"chk-{uniq.username()}.pdf"))
        assert caught.value.args[0] == 4025
        assert "chk_equipment_documents_owner" in caught.value.args[1]


# ---------------------------------------------------------------------------
# Ticket photos (S017 § 5.5): the third owner, keys ticket:read / ticket:raise; documents too since S018
# ---------------------------------------------------------------------------

def ticket_docs_url(ticket):
    return f"/api/tickets/{ticket['id']}/documents"


def ticket_photo(client, ticket, **kwargs):
    return uploaded_to(client, ticket_docs_url(ticket), kind="photo", title="Leak", data=JPEG,
                       filename="IMG_1.jpg", **kwargs)


class TestTicketPhotos:

    def test_an_operator_uploads_lists_opens_retitles_and_removes(self, at_unit, node, make_ticket, db_rows):
        operator = at_unit("maint_operator")
        ticket = make_ticket(node, client=operator)
        url = ticket_docs_url(ticket)
        photo = ticket_photo(operator, ticket)
        assert (photo["kind"], photo["has_thumb"], photo["created_by"]) == ("photo", True,
                                                                           operator._headers["X-Test-User"])
        page = listed_at(operator, url)
        assert [d["id"] for d in page["items"]] == [photo["id"]] and "inherited" not in page
        assert operator.get(f"{url}/{photo['id']}/file").data == JPEG
        assert operator.get(f"{url}/{photo['id']}/thumb").status_code == 200
        stored = db_rows("SELECT stored_name, ticket_id, equipment_id FROM equipment_documents WHERE id = %s",
                         (photo["id"],))[0]
        assert (stored["ticket_id"], stored["equipment_id"]) == (ticket["id"], None)
        assert owner_files("ticket", ticket["id"]) == sorted([stored["stored_name"],
                                                              f"{stored['stored_name']}.thumb.jpg"])
        res = operator.put(f"{url}/{photo['id']}", json={"title": "Oil on the floor"})
        assert (res.status_code, res.get_json()["title"]) == (200, "Oil on the floor")
        assert operator.delete(f"{url}/{photo['id']}").status_code == 204
        assert listed_at(operator, url)["items"] == []

    def test_a_document_on_a_ticket_is_stored_and_listed(self, admin, node, make_ticket, db_rows):
        """S018 user decision 5: vendor reports and quotes on a ticket, under tickets/<id>/."""
        ticket = make_ticket(node)
        document = uploaded_to(admin, ticket_docs_url(ticket))
        assert document["kind"] == "document"
        stored = db_rows("SELECT stored_name, ticket_id FROM equipment_documents WHERE id = %s",
                         (document["id"],))[0]
        assert stored["ticket_id"] == ticket["id"]
        assert owner_files("ticket", ticket["id"]) == [stored["stored_name"]]
        assert [d["id"] for d in listed_at(admin, ticket_docs_url(ticket))["items"]] == [document["id"]]

    def test_a_closed_ticket_refuses_upload_title_and_remove(self, admin, node, make_ticket, set_ticket_state):
        ticket = make_ticket(node)
        url = ticket_docs_url(ticket)
        photo = ticket_photo(admin, ticket)
        set_ticket_state(ticket, "closed")
        closed = (409, None, "This ticket is closed")
        assert refusal(upload_to(admin, url, kind="photo", data=JPEG, filename="b.jpg")) == closed
        assert refusal(admin.put(f"{url}/{photo['id']}", json={"title": "x"})) == closed
        assert refusal(admin.delete(f"{url}/{photo['id']}")) == closed
        # Still listed and served
        assert [d["id"] for d in listed_at(admin, url)["items"]] == [photo["id"]]
        assert admin.get(f"{url}/{photo['id']}/file").status_code == 200

    def test_another_units_ticket_is_404(self, user_with_units, make_unit, unit, node, make_ticket):
        ticket = make_ticket(node)
        photo = ticket_photo(user_with_units("maint_operator", [unit]), ticket)
        other = user_with_units("maint_operator", [make_unit()])
        url = ticket_docs_url(ticket)
        assert other.get(url).status_code == 404
        assert other.get(f"{url}/{photo['id']}/file").status_code == 404
        assert upload_to(other, url, kind="photo", data=JPEG, filename="a.jpg").status_code == 404

    def test_the_storekeeper_is_403(self, role_client, node, make_ticket):
        ticket = make_ticket(node)
        storekeeper = role_client("maint_storekeeper")
        assert storekeeper.get(ticket_docs_url(ticket)).status_code == 403
        res = upload_to(storekeeper, ticket_docs_url(ticket), kind="photo", data=JPEG, filename="a.jpg")
        assert res.status_code == 403

    def test_read_but_not_write_after_a_move_to_another_site(self, admin, user_at_sites, make_site, make_unit,
                                                             make_equipment, make_ticket):
        """BR2-03: a user at the machine's new site reads the ticket (its machine's current
        unit) but may not change it: ticket:raise is checked at the ticket's site."""
        site_a, site_b = make_site(), make_site()
        unit_a, unit_b = make_unit(site_a), make_unit(site_b)
        machine = make_equipment(unit=unit_a)
        ticket = make_ticket(machine)
        url = ticket_docs_url(ticket)
        photo = ticket_photo(admin, ticket)
        assert admin.put(f"/api/equipment/{machine['id']}", json={"unit_id": unit_b["id"]}).status_code == 200
        reader, _ = user_at_sites([(site_b, "maint_operator", [unit_b])])
        assert reader.get(f"/api/tickets/{ticket['id']}").status_code == 200
        assert [d["id"] for d in listed_at(reader, url)["items"]] == [photo["id"]]
        assert reader.get(f"/api/tickets/{ticket['id']}").get_json()["can_add_photos"] is False
        forbidden = f"You can't do this at {site_a['code']}"
        assert refusal(upload_to(reader, url, kind="photo", data=JPEG, filename="a.jpg")) == (403, None, forbidden)
        assert refusal(reader.put(f"{url}/{photo['id']}", json={"title": "x"})) == (403, None, forbidden)
        assert refusal(reader.delete(f"{url}/{photo['id']}")) == (403, None, forbidden)
        assert owner_files("ticket", ticket["id"]) != []

    def test_access_comes_before_the_key(self, user_at_sites, make_site, make_unit, make_equipment, make_ticket):
        """BR2-02: ticket:raise at the ticket's site but not its unit -> 404, not 403."""
        site = make_site()
        unit, other_unit = make_unit(site), make_unit(site)
        ticket = make_ticket(make_equipment(unit=unit))
        client, _ = user_at_sites([(site, "maint_operator", [other_unit])])
        res = upload_to(client, ticket_docs_url(ticket), kind="photo", data=JPEG, filename="a.jpg")
        assert res.status_code == 404
        assert owner_files("ticket", ticket["id"]) == []

    def test_node_and_model_keys_are_unchanged(self, role_client, node, make_model):
        """The owners' keys are data now (S017 § 5.5): equipment:edit still needed on a node or model."""
        operator = role_client("maint_operator")
        for url in (docs_url(node), model_docs_url(make_model())):
            res = upload_to(operator, url)
            assert res.status_code == 403
            assert res.get_json()["error"] == "You don't have permission for this. Ask your engineer or IT."
