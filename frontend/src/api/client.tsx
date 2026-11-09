import { USE_MOCK, VITE_API_URL } from "../config/env";

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const url = `${VITE_API_URL}${path}`;
  const options: RequestInit = { ...init, credentials: "include" };
  if (USE_MOCK) {
    const { mockFetch } = await import("../mocks/mockFetch");
    return mockFetch(url, options);
  }
  return fetch(url, options);
}
export { apiFetch };
