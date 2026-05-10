/**
 * Hyperspell Token Endpoint — generates user tokens for the OAuth connect flow.
 *
 * POST /hyperspell-token
 * Body: { "user_id": "..." }
 * Returns: { "token": "..." }
 *
 * The frontend uses this token to redirect to connect.hyperspell.com where
 * users authorize their Gmail, Google Drive, GitHub, etc.
 */

export default async function(req: Request): Promise<Response> {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  const apiKey = Deno.env.get('HYPERSPELL_API_KEY');
  if (!apiKey) {
    return new Response(JSON.stringify({ error: 'HYPERSPELL_API_KEY not configured' }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  try {
    const body = await req.json();
    // TODO: Replace with real auth — currently uses a user_id from the request body
    const userId = body.user_id || 'default-user';

    const response = await fetch('https://api.hyperspell.com/auth/user_token', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId }),
    });

    if (!response.ok) {
      const error = await response.text();
      return new Response(JSON.stringify({ error: `Hyperspell API error: ${error}` }), {
        status: response.status,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    const data = await response.json();

    return new Response(JSON.stringify({ token: data.token }), {
      status: 200,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: `Failed to generate token: ${err.message}` }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}
