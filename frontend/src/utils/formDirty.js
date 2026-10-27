// The injection key of FormModal's `dirty` flag (S064 UX-16): FormModal provides it, read-only;
// ActiveToggle injects it to block Deactivate / Reactivate while the form has unsaved changes.
export const FORM_DIRTY = Symbol("formDirty");
