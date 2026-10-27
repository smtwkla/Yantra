// The app's navigation on any width: the sidebar's icon buttons on a desktop, the bottom bar's
// links on a phone (S064 UX-22: real links, so Tab reaches them).  Only one of the two is visible.

/** The visible nav item named `name` ("Me", "Readings", …). */
export function navItem(page, name) {
  return page.getByRole("button", { name, exact: true })
    .or(page.getByRole("link", { name, exact: true }))
    .filter({ visible: true });
}
