import { createClient } from "@/lib/supabase/client";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (!apiBaseUrl) {
    throw new Error("The API URL is not configured.");
  }
  const {
    data: { session },
    error: sessionError,
  } = await createClient().auth.getSession();
  if (sessionError) {
    throw new Error(`Could not read your login session: ${sessionError.message}`);
  }
  if (!session?.access_token) {
    throw new Error("Please sign in again to continue.");
  }

  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${session.access_token}`);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error("The server may be waking up. Please try again in a minute.");
  }

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (body && typeof body === "object") {
        message = body.error ?? body.detail ?? message;
      }
    } catch (error) {
      if (!(error instanceof SyntaxError)) {
        throw error;
      }
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
