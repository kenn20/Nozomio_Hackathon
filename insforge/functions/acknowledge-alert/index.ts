import { createClient } from 'npm:@insforge/sdk';

export default async function(req: Request): Promise<Response> {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  const client = createClient({
    baseUrl: Deno.env.get('INSFORGE_BASE_URL'),
    anonKey: Deno.env.get('ANON_KEY')
  });

  const body = await req.json();
  const { id, resolution } = body;

  if (!id) {
    return new Response(JSON.stringify({ error: 'Missing alert id' }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  const validResolutions = ['acknowledged', 'old_was_right', 'new_is_right'];
  if (resolution && !validResolutions.includes(resolution)) {
    return new Response(JSON.stringify({ error: `Invalid resolution. Must be one of: ${validResolutions.join(', ')}` }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  const { data, error } = await client.database
    .from('alerts')
    .update({
      acknowledged: true,
      resolution: resolution || 'acknowledged'
    })
    .eq('id', id)
    .select();

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  return new Response(JSON.stringify({ data }), {
    status: 200,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  });
}
