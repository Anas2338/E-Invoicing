import { NextRequest } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1';

export async function POST(request: NextRequest) {
  try {
    const { email, password } = await request.json();

    // Basic validation
    if (!email || !password) {
      return Response.json(
        { error: 'Email and password are required' },
        { status: 400 }
      );
    }

    // Call backend API
    const backendResponse = await fetch(`${BACKEND_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      return Response.json(
        { error: data.detail || 'Invalid credentials' },
        { status: backendResponse.status }
      );
    }

    // Return the response from backend (includes access_token and user data)
    return Response.json(data, { status: 200 });

  } catch (error) {
    console.error('Login error:', error);
    return Response.json(
      { error: 'Login failed. Please check if the backend is running.' },
      { status: 500 }
    );
  }
}