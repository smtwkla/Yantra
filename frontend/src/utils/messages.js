/**
 * Screen texts used in more than one place (S064 UX-06, UX-21), so one wording holds everywhere.
 * CLAUDE-COMMON § Writing style, scope B: what happened, and what the user can do next.
 */

// A list screen for a person who reads no unit at all (Me, Equipment, Tickets, Readings)
export const NO_UNITS_TEXT = "No units are given to you yet. Ask your engineer or IT.";

// fetch() itself failed (Wi-Fi or mobile data dropped): never the browser's "Failed to fetch"
export const NO_CONNECTION_TEXT = "No connection. Check Wi-Fi or mobile data and try again.";

// A 5xx without a JSON body (the proxy's "Bad Gateway" page while the backend restarts)
export const NOT_ANSWERING_TEXT = "Yantra is not answering. Try again in a minute.";
