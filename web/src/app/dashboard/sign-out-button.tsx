"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function SignOutButton() {
  const [errorMessage, setErrorMessage] = useState("");
  const router = useRouter();

  async function signOut() {
    setErrorMessage("");
    const { error } = await createClient().auth.signOut();
    if (error) {
      setErrorMessage(error.message);
      return;
    }
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="sign-out-wrap">
      <button className="button button-quiet" onClick={signOut}>Log out</button>
      {errorMessage && <span className="form-error">{errorMessage}</span>}
    </div>
  );
}
