import { USE_MOCK, VITE_API_URL } from "../config/env";

type ApiFailureHandler = (status: number, path: string) => void;
let apiFailureHandler: ApiFailureHandler | null = null;

export function setApiFailureHandler(handler: ApiFailureHandler | null) {
  apiFailureHandler = handler;
}

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const url = `${VITE_API_URL}${path}`;
  const options: RequestInit = { ...init, credentials: "include" };
  let response: Response;
  if (USE_MOCK) {
    const { mockFetch } = await import("../mocks/mockFetch");
    response = await mockFetch(url, options);
  } else {
    response = await fetch(url, options);
  }
  if (response.status === 401 || response.status >= 500) apiFailureHandler?.(response.status, path);
  return response;
}
export { apiFetch };
