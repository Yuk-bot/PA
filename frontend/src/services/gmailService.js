import { API_BASE } from './apiConfig';

const BASE_URL = API_BASE;

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

export async function connectGmail(token) {
  const res = await fetch(`${BASE_URL}/calendar/connect`, {
    headers: authHeaders(token),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Connect failed (${res.status})`);
  }

  return res.json();
}

export async function checkGmailStatus(token) {
  const res = await fetch(`${BASE_URL}/calendar/today`, {
    headers: authHeaders(token),
  });

  if (res.status === 404) {
    return { connected: false, email: null };
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Status check failed (${res.status})`);
  }

  try {
    const userProfileRes = await fetch(`${BASE_URL}/users/profile`, {
      headers: authHeaders(token),
    });
    if (userProfileRes.ok) {
      const profileData = await userProfileRes.json();
      const email = profileData.email || null;
      return { connected: true, email };
    }
  } catch (e) { }

  return { connected: true, email: null };
}

export async function disconnectGmail(token) {
  const res = await fetch(`${BASE_URL}/calendar/disconnect`, {
    method: "POST",
    headers: authHeaders(token),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Disconnect failed (${res.status})`);
  }

  return res.json();
}

export async function syncGmail(token, force = false) {
  const res = await fetch(`${BASE_URL}/inbox/sync`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ force_sync: force }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Sync failed (${res.status})`);
  }

  return res.json();
}

export async function getGmailSuggestions(token) {
  const res = await fetch(`${BASE_URL}/inbox/suggestions`, {
    headers: authHeaders(token),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch suggestions (${res.status})`);
  }

  return res.json();
}

export async function dismissGmailSuggestion(token, suggestionId) {
  const res = await fetch(`${BASE_URL}/inbox/suggestions/${suggestionId}/dismiss`, {
    method: "POST",
    headers: authHeaders(token),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Dismiss failed (${res.status})`);
  }

  return res.json();
}
