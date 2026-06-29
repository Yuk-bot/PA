

const BASE_URL = 'http://localhost:8000/api';


function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}


export async function connectCalendar(token) {
  const res = await fetch(`${BASE_URL}/calendar/connect`, {
    headers: authHeaders(token),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Connect failed (${res.status})`);
  }

  return res.json(); // { authorization_url }
}


export async function checkCalendarStatus(token) {
  const res = await fetch(`${BASE_URL}/calendar/today`, {
    headers: authHeaders(token),
  });

  if (res.status === 404) {
    return { connected: false, events: [], count: 0 };
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Status check failed (${res.status})`);
  }

  const data = await res.json();
  return { connected: true, events: data.events || [], count: data.count || 0 };
}


export async function getEvents(token, maxResults = 30, daysAhead = 30) {
  const res = await fetch(
    `${BASE_URL}/calendar/events?max_results=${maxResults}&days_ahead=${daysAhead}`,
    { headers: authHeaders(token) }
  );

  if (res.status === 404) {
    return { connected: false, events: [], count: 0 };
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch events (${res.status})`);
  }

  const data = await res.json();
  return { connected: true, events: data.events || [], count: data.count || 0 };
}


export async function getTodayEvents(token) {
  const res = await fetch(`${BASE_URL}/calendar/today`, {
    headers: authHeaders(token),
  });

  if (res.status === 404) {
    return { connected: false, events: [], count: 0 };
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch today's events (${res.status})`);
  }

  const data = await res.json();
  return { connected: true, events: data.events || [], count: data.count || 0 };
}

export async function getFreeSlots(token) {
  const res = await fetch(`${BASE_URL}/calendar/free-slots`, {
    headers: authHeaders(token),
  });

  if (res.status === 404) {
    return { connected: false, free_slots: [], total_free_minutes: 0 };
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch free slots (${res.status})`);
  }

  const data = await res.json();
  return {
    connected: true,
    date: data.date,
    free_slots: data.free_slots || [],
    total_free_minutes: data.total_free_minutes || 0,
  };
}


export async function disconnectCalendar(token) {
  const res = await fetch(`${BASE_URL}/calendar/disconnect`, {
    method: 'POST',
    headers: authHeaders(token),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Disconnect failed (${res.status})`);
  }

  return res.json(); // { message }
}
