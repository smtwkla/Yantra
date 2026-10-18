"""Removed documents (S008): the list, restore and delete for good.  Needs the dev MariaDB.

Isolation: the test DB is emptied once per session and the manager sees every unit, so other
tests' removed rows are in the list too.  Every assertion on total, order or page position
filters by q=<class code>; the titles and file names searched for carry the class code too.
"""

import errno
import logging
import os

import pytest

import config_rbac
import documents
import file_store
from tests.documents_helpers import (
    EQUIPMENT, JPEG, PDF, docs_url, folder_files, model_docs_url, owner_files, refusal, scrap, uploaded,
    uploaded_to,
)

REMOVED = f"{EQUIPMENT}/removed-documents"
PURGE_KEY = "equipment:purge_documents"
UNKNOWN_MODEL_DOCS = "/api/masters/equipment-models/999999999/documents"


@pytest.fixture
def manager(role_client):
    return role_client("maint_manager")


@pytest.fixture
def engineer(at_unit):
    return at_unit("maint_engineer")


@pytest.fixture
def cls(make_class):
    return make_class()


@pytest.fixture
def root(make_equipment, unit, cls):
    return make_equipment(unit=unit, cls=cls)


def remove(client, node, doc):
    res = client.delete(f"{docs_url(node)}/{doc['id']}")
    assert res.status_code == 204, res.get_json()


def removed_doc(client, node, **kwargs):
    doc = uploaded(client, node, **kwargs)
    remove(client, node, doc)
    return doc


def listing(client, **params):
    res = client.get(REMOVED, query_string=params)
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def ids(page):
    return [item["id"] for item in page["items"]]


def action_url(node, doc, action):
    return f"{docs_url(node)}/{doc['id']}/{action}"


def row(db_rows, doc):
    rows = db_rows("SELECT * FROM equipment_documents WHERE id = %s", (doc["id"],))
    return rows[0] if rows else None


class TestList:

    def test_lists_the_removed_newest_first_with_the_node(self, admin, manager, make_equipment, unit, cls, root):
        unit_node = make_equipment(parent=root, cls=cls)
        part = make_equipment(parent=unit_node, level="component", cls=cls)
        pdf = removed_doc(admin, root, title=f"Manual {cls['code']}")
        photo = removed_doc(admin, part, kind="photo", title="Nameplate", data=JPEG,
                            filename=f"{cls['code']}-nameplate.jpg")
        active = uploaded(admin, root, title=f"Active {cls['code']}")

        page = listing(manager, q=cls["code"])
        assert ids(page) == [photo["id"], pdf["id"]]
        assert page["total"] == 2 and active["id"] not in ids(page)
        newest, older = page["items"]
        assert (older["code"], older["name"], older["level"], older["status"]) == (
            root["code"], "Test node", "equipment", "in_service")
        assert older["removed_by"] == "test_it_admin" and older["created_by"] == "test_it_admin"
        assert older["equipment_id"] == root["id"] and older["original_name"] == "manual.pdf"
        assert "stored_name" not in older and "has_thumb" not in older
        # A part's unit and path are the root's
        site_unit = older["unit"]
        assert newest["level"] == "component" and newest["unit"] == site_unit
        # The same path the equipment list shows
        for shown, node in ((newest, part), (older, root)):
            listed = manager.get(EQUIPMENT, query_string={"level": "all", "q": node["code"]}).get_json()["items"]
            assert shown["full_path"] == next(e for e in listed if e["id"] == node["id"])["full_path"]
        assert newest["full_path"].count(unit_node["code"]) == 1 and part["code"] in newest["full_path"]

    def test_filters_by_kind_and_by_title_or_file_name(self, admin, manager, root, cls):
        pdf = removed_doc(admin, root, title=f"Manual {cls['code']}", filename="plain.pdf")
        photo = removed_doc(admin, root, kind="photo", title="Shot", data=JPEG,
                            filename=f"{cls['code']}-nameplate.jpg")
        assert ids(listing(manager, q=cls["code"], kind="photo")) == [photo["id"]]
        assert ids(listing(manager, q=cls["code"], kind="document")) == [pdf["id"]]
        by_title = listing(manager, q=f"Manual {cls['code']}")
        assert (by_title["total"], ids(by_title)) == (1, [pdf["id"]])
        by_name = listing(manager, q=f"{cls['code']}-nameplate")
        assert (by_name["total"], ids(by_name)) == (1, [photo["id"]])

    def test_pages(self, admin, manager, root, cls):
        first = removed_doc(admin, root, title=f"One {cls['code']}")
        second = removed_doc(admin, root, title=f"Two {cls['code']}")
        page = listing(manager, q=cls["code"], per_page=1, page=2)
        assert (page["total"], page["page"], page["per_page"], ids(page)) == (2, 2, 1, [first["id"]])
        assert ids(listing(manager, q=cls["code"], per_page=1)) == [second["id"]]

    @pytest.mark.parametrize("params, field", [
        ({"kind": "video"}, "kind"), ({"page": "0"}, "page"), ({"per_page": "201"}, "per_page"),
    ])
    def test_bad_arguments_are_refused(self, manager, params, field):
        res = manager.get(REMOVED, query_string=params)
        assert (res.status_code, res.get_json()["field"]) == (400, field)

    def test_who_may_list(self, role_client):
        for role in ("maint_engineer", "maint_operator"):
            assert role_client(role).get(REMOVED).status_code == 403
        for role in ("maint_manager", "it_admin"):
            assert role_client(role).get(REMOVED).status_code == 200

    def test_the_unit_scope_is_enforced_fail_closed(self, monkeypatch, admin, make_unit, make_equipment,
                                                    user_with_units, unit, cls, root):
        monkeypatch.setitem(config_rbac.PERMISSIONS, PURGE_KEY, ("maint_manager", "it_admin", "maint_engineer"))
        other_unit = make_unit()
        other = make_equipment(unit=other_unit, cls=cls)
        mine = removed_doc(admin, root, title=f"Mine {cls['code']}")
        theirs = removed_doc(admin, other, title=f"Theirs {cls['code']}")
        engineer = user_with_units("maint_engineer", [unit])
        assert ids(listing(engineer, q=cls["code"])) == [mine["id"]]
        assert theirs["id"] not in ids(listing(engineer, q=cls["code"]))
        nobody = user_with_units("maint_engineer", [])
        # No units leaves out the node branch, not the whole list: model rows stay (S012 § 5.6)
        assert listing(nobody, q=cls["code"]) == {"items": [], "total": 0, "page": 1, "per_page": 50}
        assert all(item["owner"] == "model" for item in listing(nobody)["items"])


class TestModelRows:
    """S012 § 5.6: removed model documents in the same list, at every site."""

    @pytest.fixture
    def model(self, make_manufacturer, make_model, uniq):
        return make_model(manufacturer=make_manufacturer(name=f"Atlas Copco {uniq.manufacturer_name()}"))

    def _removed(self, admin, model, **kwargs):
        url = model_docs_url(model)
        doc = uploaded_to(admin, url, **kwargs)
        assert admin.delete(f"{url}/{doc['id']}").status_code == 204
        return doc

    def test_listed_with_owner_path_and_label_and_ordered_with_node_rows(self, admin, manager, root, cls, model):
        node_doc = removed_doc(admin, root, title=f"Manual {cls['code']}")
        model_doc = self._removed(admin, model, title=f"Manual {cls['code']}")
        page = listing(manager, q=cls["code"])
        assert (page["total"], ids(page)) == (2, [model_doc["id"], node_doc["id"]])
        model_row, node_row = page["items"]
        assert {key: model_row[key] for key in ("owner", "path", "name", "code", "equipment_id", "level", "status",
                                                "unit", "full_path")} == {
            "owner": "model", "path": model_docs_url(model), "name": model["label"], "code": None,
            "equipment_id": None, "level": None, "status": None, "unit": None, "full_path": None}
        assert (node_row["owner"], node_row["path"], node_row["code"]) == ("equipment", docs_url(root), root["code"])
        assert model_row["removed_by"] == "test_it_admin"
        assert ids(listing(manager, q=cls["code"], per_page=1, page=2)) == [node_doc["id"]]

    def test_q_matches_designation_manufacturer_title_and_file_name(self, admin, manager, model):
        doc = self._removed(admin, model, title="Parts list", filename=f"{model['designation']}-parts.pdf")
        for q in (model["designation"], model["manufacturer_name"], model["label"], f"{model['designation']}-parts"):
            assert doc["id"] in ids(listing(manager, q=q)), q
        photo = self._removed(admin, model, kind="photo", title="Plate", data=JPEG, filename="a.jpg")
        assert ids(listing(manager, q=model["manufacturer_name"], kind="photo")) == [photo["id"]]

    def test_a_manager_limited_to_one_site_sees_them(self, admin, user_at_sites, make_site, make_unit, model):
        site = make_site()
        manager_a, _ = user_at_sites([(site, "maint_manager", [make_unit(site)])])
        doc = self._removed(admin, model)
        assert ids(listing(manager_a, q=model["designation"])) == [doc["id"]]

    def test_restore_and_purge(self, caplog, admin, manager, model, db_rows):
        url = model_docs_url(model)
        restored = self._removed(admin, model, title="Manual")
        res = manager.post(f"{url}/{restored['id']}/restore")
        assert (res.status_code, res.get_json()["id"]) == (200, restored["id"])
        assert [d["id"] for d in admin.get(url).get_json()["items"]] == [restored["id"]]

        photo = self._removed(admin, model, kind="photo", title="Plate", data=JPEG, filename="a.jpg")
        stored = row(db_rows, photo)["stored_name"]
        assert stored in owner_files("model", model["id"])
        caplog.set_level(logging.INFO, logger="documents")
        assert manager.post(f"{url}/{photo['id']}/purge").status_code == 204
        assert row(db_rows, photo) is None
        assert stored not in owner_files("model", model["id"])
        assert f"{stored}.thumb.jpg" not in owner_files("model", model["id"])
        messages = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
        assert any(f"of model {model['id']} deleted for good by test_maint_manager" in m for m in messages), messages

    def test_refusals(self, admin, manager, engineer, role_client, make_model, model):
        url = model_docs_url(model)
        removed = self._removed(admin, model)
        active = uploaded_to(admin, url)
        assert refusal(manager.post(f"{url}/{active['id']}/purge")) == (409, None, "Remove the document first")
        assert manager.post(f"{url}/{active['id']}/restore").status_code == 404
        other = model_docs_url(make_model())
        assert manager.post(f"{other}/{removed['id']}/restore").status_code == 404
        assert manager.post(f"{other}/{removed['id']}/purge").status_code == 404
        for client in (engineer, role_client("maint_operator")):
            assert client.post(f"{url}/{removed['id']}/restore").status_code == 403
            assert client.post(f"{url}/{removed['id']}/purge").status_code == 403
        assert manager.post(f"{UNKNOWN_MODEL_DOCS}/1/purge").status_code == 404



class TestRestore:

    def test_restores_the_document(self, admin, manager, engineer, root, cls, db_rows):
        doc = removed_doc(admin, root, title=f"Manual {cls['code']}")
        before = row(db_rows, doc)
        assert engineer.get(f"{docs_url(root)}/{doc['id']}/file").status_code == 404

        res = manager.post(action_url(root, doc, "restore"))
        assert res.status_code == 200
        assert res.get_json()["id"] == doc["id"] and "stored_name" not in res.get_json()
        assert doc["id"] in [d["id"] for d in engineer.get(docs_url(root)).get_json()["items"]]
        served = engineer.get(f"{docs_url(root)}/{doc['id']}/file")
        assert (served.status_code, served.data) == (200, PDF)
        after = row(db_rows, doc)
        assert (after["removed_at"], after["removed_by"]) == (None, None)
        assert (after["updated_by"], after["updated_at"]) == (before["updated_by"], before["updated_at"])
        assert doc["id"] not in ids(listing(manager, q=cls["code"]))

    def test_logs_who_restored_and_who_removed(self, caplog, admin, manager, root, cls):
        doc = removed_doc(admin, root, title=f"Manual {cls['code']}")
        caplog.set_level(logging.INFO, logger="documents")
        manager.post(action_url(root, doc, "restore"))
        messages = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
        assert any(f"Document {doc['id']} 'Manual {cls['code']}'" in m and "restored by test_maint_manager" in m
                   and "removed by test_it_admin" in m for m in messages), messages

    def test_refusals(self, admin, manager, engineer, make_equipment, unit, cls, root):
        doc = removed_doc(admin, root, title=f"Manual {cls['code']}")
        active = uploaded(admin, root, title=f"Active {cls['code']}")
        other = make_equipment(unit=unit, cls=cls)
        assert manager.post(action_url(root, active, "restore")).status_code == 404
        assert manager.post(action_url(other, doc, "restore")).status_code == 404
        assert engineer.post(action_url(root, doc, "restore")).status_code == 403
        assert manager.post(action_url(root, doc, "restore")).status_code == 200
        assert manager.post(action_url(root, doc, "restore")).status_code == 404

    def test_scrapped_node_is_refused(self, admin, manager, root, cls):
        doc = removed_doc(admin, root, title=f"Manual {cls['code']}")
        scrap(admin, root)
        res = manager.post(action_url(root, doc, "restore"))
        assert refusal(res) == (409, None, documents.SCRAPPED_MESSAGE)

    def test_a_node_outside_the_users_units_is_404(self, monkeypatch, admin, user_with_units, make_unit,
                                                   root, cls):
        monkeypatch.setitem(config_rbac.PERMISSIONS, PURGE_KEY, ("maint_manager", "it_admin", "maint_engineer"))
        doc = removed_doc(admin, root, title=f"Manual {cls['code']}")
        stranger = user_with_units("maint_engineer", [make_unit()])
        assert stranger.post(action_url(root, doc, "restore")).status_code == 404
        assert stranger.post(action_url(root, doc, "purge")).status_code == 404


class TestPurge:

    def test_deletes_the_row_the_file_and_the_thumbnail(self, admin, manager, engineer, root, cls, db_rows):
        keep = uploaded(admin, root, title=f"Keep {cls['code']}")
        photo = removed_doc(admin, root, kind="photo", title=f"Shot {cls['code']}", data=JPEG, filename="a.jpg")
        stored = row(db_rows, photo)["stored_name"]
        assert sorted(folder_files(root)) == sorted([row(db_rows, keep)["stored_name"], stored, f"{stored}.thumb.jpg"])
        items_before = engineer.get(docs_url(root)).get_json()["items"]

        res = manager.post(action_url(root, photo, "purge"))
        assert (res.status_code, res.data) == (204, b"")
        assert row(db_rows, photo) is None
        assert folder_files(root) == [row(db_rows, keep)["stored_name"]]
        assert engineer.get(docs_url(root)).get_json()["items"] == items_before
        assert photo["id"] not in ids(listing(manager, q=cls["code"]))
        assert engineer.get(f"{docs_url(root)}/{photo['id']}/file").status_code == 404
        assert manager.post(action_url(root, photo, "purge")).status_code == 404
        assert manager.post(action_url(root, photo, "restore")).status_code == 404

    def test_logs_the_actor_uploader_and_remover(self, caplog, admin, manager, root, cls):
        doc = removed_doc(admin, root, title=f"Manual {cls['code']}")
        caplog.set_level(logging.INFO, logger="documents")
        manager.post(action_url(root, doc, "purge"))
        messages = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
        assert any(f"Document {doc['id']} 'Manual {cls['code']}'" in m and "deleted for good by test_maint_manager" in m
                   and "uploaded by test_it_admin" in m and "removed by test_it_admin" in m for m in messages), messages

    def test_refusals(self, admin, manager, engineer, make_equipment, unit, cls, root):
        doc = removed_doc(admin, root, title=f"Manual {cls['code']}")
        active = uploaded(admin, root, title=f"Active {cls['code']}")
        other = make_equipment(unit=unit, cls=cls)
        assert refusal(manager.post(action_url(root, active, "purge"))) == (409, None, "Remove the document first")
        assert manager.post(action_url(other, doc, "purge")).status_code == 404
        assert engineer.post(action_url(root, doc, "purge")).status_code == 403
        assert len(folder_files(root)) == 2

    def test_scrapped_equipment_may_be_purged(self, admin, manager, root, cls):
        doc = removed_doc(admin, root, title=f"Manual {cls['code']}")
        scrap(admin, root)
        assert manager.post(action_url(root, doc, "purge")).status_code == 204
        assert folder_files(root) == []

    def test_a_file_already_missing_is_204_and_a_warning(self, caplog, admin, manager, root, cls, db_rows):
        doc = removed_doc(admin, root, title=f"Manual {cls['code']}")
        path = file_store.file_path("equipment", root["id"], row(db_rows, doc)["stored_name"])
        os.remove(path)
        caplog.set_level(logging.INFO, logger="documents")
        assert manager.post(action_url(root, doc, "purge")).status_code == 204
        warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert any(path in m for m in warnings), warnings

    def test_a_file_that_cannot_be_removed_is_a_warning_not_a_204(self, monkeypatch, caplog, admin, manager,
                                                                  root, cls, db_rows):
        doc = removed_doc(admin, root, kind="photo", title=f"Shot {cls['code']}", data=JPEG, filename="a.jpg")
        stored = row(db_rows, doc)["stored_name"]
        main = file_store.file_path("equipment", root["id"], stored)
        real = file_store.remove_file

        def failing(path):
            if path == main:
                raise OSError(errno.EIO, "Input/output error")
            return real(path)

        monkeypatch.setattr(file_store, "remove_file", failing)
        caplog.set_level(logging.INFO, logger="documents")
        res = manager.post(action_url(root, doc, "purge"))
        assert (res.status_code, res.get_json()) == (200, {"warning": documents.FILE_LEFT_BEHIND})
        assert row(db_rows, doc) is None
        assert folder_files(root) == [stored]   # the thumbnail went, the main file stayed
        errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
        assert any(main in m for m in errors), errors

    def test_a_thumbnail_that_cannot_be_removed_is_a_warning_not_a_204(self, monkeypatch, caplog, admin, manager,
                                                                       root, cls, db_rows):
        doc = removed_doc(admin, root, kind="photo", title=f"Shot {cls['code']}", data=JPEG, filename="a.jpg")
        stored = row(db_rows, doc)["stored_name"]
        thumb = file_store.file_path("equipment", root["id"], f"{stored}.thumb.jpg")
        real = file_store.remove_file

        def failing(path):
            if path == thumb:
                raise OSError(errno.EIO, "Input/output error")
            return real(path)

        monkeypatch.setattr(file_store, "remove_file", failing)
        caplog.set_level(logging.INFO, logger="documents")
        res = manager.post(action_url(root, doc, "purge"))
        assert (res.status_code, res.get_json()) == (200, {"warning": documents.FILE_LEFT_BEHIND})
        assert row(db_rows, doc) is None
        assert folder_files(root) == [f"{stored}.thumb.jpg"]   # the main file went, the thumbnail stayed
        errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
        assert any(thumb in m for m in errors), errors
