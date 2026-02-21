import { NextRequest } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1';

export async function POST(request: NextRequest) {
  try {
    const { email, password, name } = await request.json();

    // Basic validation
    if (!email || !password || !name) {
      return Response.json(
        { error: 'Email, password, and name are required' },
        { status: 400 }
      );
    }

    // Call backend API
    const backendResponse = await fetch(`${BACKEND_URL}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password, name }),
    });

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      return Response.json(
        { error: data.detail || 'Registration failed' },
        { status: backendResponse.status }
      );
    }

    // Return the response from backend (includes access_token and user data)
    return Response.json(data, { status: 200 });

  } catch (error) {
    console.error('Registration error:', error);
    return Response.json(
      { error: 'Registration failed. Please check if the backend is running.' },
      { status: 500 }
    );
  }
}