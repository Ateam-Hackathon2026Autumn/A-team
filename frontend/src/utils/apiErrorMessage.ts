import ApiError from "../api/apiError";

export function apiErrorMessage(
  cause: unknown,
  fallback: string,
  field?: string,
): string {
  if (!(cause instanceof ApiError)) return fallback;
  const detail = field ? cause.details[field]?.[0] : undefined;
  return detail ? `${cause.message} ${detail}` : cause.message;
}

