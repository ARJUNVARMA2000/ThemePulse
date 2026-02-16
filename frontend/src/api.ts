const API_URL = import.meta.env.VITE_API_URL || '';

export interface CreateSessionResponse {
  session_id: string;
  admin_token: string;
  student_url: string;
  admin_url: string;
}

export interface SessionInfo {
  session_id: string;
  question: string;
  response_count: number;
}

export interface Theme {
  title: string;
  description: string;
  student_names: string[];
}

export interface SummaryPayload {
  themes: Theme[];
  response_count: number;
  model_used: string | null;
  timestamp: string;
}

export interface StatusPayload {
  response_count: number;
  min_required: number;
}

export async function createSession(question: string): Promise<CreateSessionResponse> {
  const res = await fetch(`${API_URL}/api/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`);
  return res.json();
}

export async function getSession(sessionId: string): Promise<SessionInfo> {
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Session not found`);
  return res.json();
}

export async function submitResponse(
  sessionId: string,
  studentName: string,
  answer: string,
): Promise<{ message: string; response_id: string }> {
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}/responses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student_name: studentName, answer }),
  });
  if (!res.ok) throw new Error(`Failed to submit response: ${res.statusText}`);
  return res.json();
}

export function getQRCodeUrl(sessionId: string): string {
  return `${API_URL}/api/sessions/${sessionId}/qr`;
}

export function getStreamUrl(sessionId: string, adminToken: string): string {
  return `${API_URL}/api/sessions/${sessionId}/stream?admin_token=${adminToken}`;
}
