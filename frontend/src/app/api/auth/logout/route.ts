import { NextRequest } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    // In a real app, you'd invalidate the session/token here
    // For this demo, we just return a success response

    return Response.json({
      message: 'Logout successful'
    });
  } catch (error) {
    console.error('Logout error:', error);
    return Response.json(
      { error: 'Logout failed' },
      { status: 500 }
    );
  }
}