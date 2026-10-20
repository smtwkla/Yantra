/**
 * Document and photo file types the upload dialogs offer (S006 § 5.2), shared by the upload
 * dialog and the raise-ticket screen's photo step (S017). The backend decides the real type
 * from the file's first bytes; `accept` only narrows the phone's picker.
 */

export const ACCEPT = {
  document: "application/pdf",
  photo: "image/jpeg,image/png,image/webp",
};

export const IPHONE_PHOTO_HINT =
  "iPhone photos shared from Files or WhatsApp: set Camera › Formats › Most Compatible, or share as JPEG.";

/** "IMG_2034.jpg" → "IMG_2034": the title a new upload is given. */
export function withoutExtension(name) {
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(0, dot) : name;
}
