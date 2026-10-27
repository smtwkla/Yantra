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

// A camera's own file name says nothing about the photo (S064 UX-11): IMG_2034, PXL_20261020_143512,
// DSC01234, image, or digits only (20261020_143512).  The prefix must end the name or be followed by a
// separator or a digit, so "Imagery report" is a title.
const CAMERA_PREFIX = /^(IMG|PXL|DSC|image)(?=$|[_\-\s\d(])/i;
const DIGITS_ONLY = /^[\d_-]+$/;

/** True when the file name (with or without its extension) is a camera's, not a title. */
export function isCameraName(name) {
  const stem = withoutExtension(name);
  return CAMERA_PREFIX.test(stem) || DIGITS_ONLY.test(stem);
}

/** True for an iPhone HEIC / HEIF photo, by its extension or its type: the server refuses it. */
export function isHeicFile(file) {
  if (!file) return false;
  return /\.(heic|heif)$/i.test(file.name) || /^image\/hei[cf]/i.test(file.type ?? "");
}

/** "IMG_2034.jpg" → "IMG_2034": the title a new upload is given. */
export function withoutExtension(name) {
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(0, dot) : name;
}
