// Where the e2e stack listens (S024 § 1.1): its own ports, so the dev servers keep running.
// Lanes (tooling/e2e/run_lanes.py): with E2E_LANE=<n> set, each lane has its own backend and
// Vite ports, as tooling/e2e/e2e_backend.py, so several lanes run side by side; unset, it is
// the single stack.
const LANE = process.env.E2E_LANE ? Number(process.env.E2E_LANE) : null;

export const LANE_NAME = LANE ? `lane${LANE}` : null;
export const BACKEND_PORT = LANE ? 5010 + LANE : 5002;
export const FRONTEND_PORT = LANE ? 5180 + LANE : 5177;
export const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
export const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
