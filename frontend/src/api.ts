import { useEffect, useState } from "react";
import type { Reason } from "./types";
let token = localStorage.getItem("chakra-token") || "";
export function setToken(value: string) {
  token = value;
  localStorage.setItem("chakra-token", value);
}
export class ApiError extends Error {
  constructor(
    public reason: Reason,
    public fields: Record<string, string> = {},
  ) {
    super(reason.message);
  }
}
export async function api<T>(
  path: string,
  body?: unknown,
  method = "GET",
): Promise<T> {
  const form = body instanceof FormData;
  const response = await fetch("/api" + path, {
    method,
    headers: {
      Authorization: "Bearer " + token,
      ...(form ? {} : { "Content-Type": "application/json" }),
      ...(method === "GET" ? {} : { "Idempotency-Key": crypto.randomUUID() }),
    },
    ...(body !== undefined ? { body: form ? body : JSON.stringify(body) } : {}),
  });
  const data = await response
    .json()
    .catch(() => ({
      detail: {
        code: "NETWORK_RESPONSE_ERROR",
        message: "Server returned an unreadable response.",
      },
    }));
  if (!response.ok) {
    if (Array.isArray(data.detail)) {
      const fields: Record<string, string> = {};
      for (const e of data.detail) fields[e.loc?.[1] || "form"] = e.msg;
      throw new ApiError(
        { code: "VALIDATION_ERROR", message: "Correct the marked fields." },
        fields,
      );
    }
    throw new ApiError(
      typeof data.detail === "object"
        ? data.detail
        : {
            code: "API_ERROR",
            message: String(data.detail || response.statusText),
          },
    );
  }
  return data;
}
export function useResource<T>(
  path: string | null,
  version: number,
  initial: T,
) {
  const [data, setData] = useState<T>(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    if (!path) {
      setData(initial);
      return;
    }
    setLoading(true);
    api<T>(path)
      .then((d) => {
        if (active) {
          setData(d);
          setError("");
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path, version]);
  return { data, loading, error };
}
