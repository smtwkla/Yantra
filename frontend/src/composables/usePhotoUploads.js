/**
 * The photo list of a screen that uploads photos to an owner's documents (S071 § 5.6; taken out of
 * the raise-ticket screen, S017, so Mark done does not copy it).
 *
 * `path` is the owner's documents collection URL and `maxMb` the owner's upload limit (`null`:
 * unknown, the server still checks); both are refs or getters. `previews` makes an object URL for
 * each file, for a thumbnail.
 *
 * `files` rows: {key, file, name, previewUrl, state: "pending" | "uploading" | "done" | "failed", message}.
 *   add(fileList)   appends each file as `pending`; one above the limit is `failed` at once;
 *   remove(key)     takes a file off the list and frees its preview;
 *   uploadAll()     uploads every `pending` file, one at a time (kinder to a slow mobile link), as
 *                   kind `photo` titled with the file name; a `failed` file is not sent again unless
 *                   it is chosen again; -> the number uploaded by this call;
 *   uploading       true while a file is on its way;
 *   revokeAll()     frees every preview (at the dialog's next open, and on unmount: FormModal emits no close event, and freeing during its fade would show broken images).
 */
import { computed, onBeforeUnmount, ref, toValue } from "vue";
import { apiUpload } from "../api";
import { withoutExtension } from "../utils/documentTypes";

const TITLE_MAX = 200;
const MB = 1024 * 1024;

export function usePhotoUploads({ path, maxMb, previews = false }) {
  const files = ref([]);
  const uploading = computed(() => files.value.some((f) => f.state === "uploading"));
  let nextKey = 0;

  function add(fileList) {
    const limit = toValue(maxMb);
    for (const file of fileList) {
      const row = {
        key: ++nextKey, file, name: file.name, previewUrl: previews ? URL.createObjectURL(file) : "",
        state: "pending", message: "",
      };
      if (limit && file.size > limit * MB) Object.assign(row, { state: "failed", message: `Larger than ${limit} MB` });
      files.value.push(row);
    }
  }

  function remove(key) {
    const row = files.value.find((f) => f.key === key);
    if (row?.previewUrl) URL.revokeObjectURL(row.previewUrl);
    files.value = files.value.filter((f) => f.key !== key);
  }

  async function uploadAll() {
    let uploaded = 0;
    for (let row = files.value.find((f) => f.state === "pending"); row; row = files.value.find((f) => f.state === "pending")) {
      row.state = "uploading"; // before the first await: a second call never picks the same file
      const body = new FormData();
      body.append("kind", "photo");
      body.append("title", withoutExtension(row.name).slice(0, TITLE_MAX));
      body.append("file", row.file);
      try {
        await apiUpload(toValue(path), body);
        row.state = "done";
        uploaded += 1;
      } catch (err) {
        Object.assign(row, { state: "failed", message: err.message });
      }
    }
    return uploaded;
  }

  function revokeAll() {
    for (const row of files.value) if (row.previewUrl) URL.revokeObjectURL(row.previewUrl);
    files.value = files.value.map((f) => ({ ...f, previewUrl: "" }));
  }

  onBeforeUnmount(revokeAll);

  return { files, add, remove, uploadAll, uploading, revokeAll };
}
