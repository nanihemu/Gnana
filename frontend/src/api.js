const KEY = "gnana_token";
export const getToken = () => localStorage.getItem(KEY) || "";
export const setToken = (t) => (t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY));

export async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const t = getToken();
  if (t) headers.Authorization = "Bearer " + t;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch("/api" + path, { method, headers, body: payload });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {}
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const videoUrl = (id) => `/api/materials/${id}/video?token=${encodeURIComponent(getToken())}`;
