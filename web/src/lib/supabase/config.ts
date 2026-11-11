export function getSupabaseConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();

  if (!url || !anonKey) {
    throw new Error(
      "Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in web/.env.local, then restart Next.js.",
    );
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(url);
  } catch {
    throw new Error(
      "NEXT_PUBLIC_SUPABASE_URL is invalid. Copy the Project URL from Supabase → Project Settings → API; it should look like https://your-project.supabase.co.",
    );
  }

  if (
    !["https:", "http:"].includes(parsedUrl.protocol) ||
    !parsedUrl.hostname ||
    parsedUrl.hostname === "your-project.supabase.co"
  ) {
    throw new Error(
      "NEXT_PUBLIC_SUPABASE_URL is invalid. Copy the Project URL from Supabase → Project Settings → API; it should look like https://your-project.supabase.co.",
    );
  }

  if (parsedUrl.pathname === "/rest/v1" || parsedUrl.pathname === "/rest/v1/") {
    parsedUrl.pathname = "/";
  } else if (parsedUrl.pathname !== "/") {
    throw new Error(
      "NEXT_PUBLIC_SUPABASE_URL must be the Supabase Project URL, not an API endpoint. Use the URL from Project Settings → API and omit paths such as /rest/v1.",
    );
  }

  return { url: parsedUrl.origin, anonKey };
}
