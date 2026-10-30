/**
 * Save the file behind a blob URL under `fileName` (a click on a temporary link).
 * A blob URL has no name of its own; without `download` Android saves a nameless file.
 * The caller makes and revokes the URL.
 */
export function downloadBlobUrl(url, fileName) {
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
}
