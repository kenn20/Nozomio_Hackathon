import { createClient } from 'npm:@insforge/sdk';

export default async function(req: Request): Promise<Response> {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  const client = createClient({
    baseUrl: Deno.env.get('INSFORGE_BASE_URL'),
    anonKey: Deno.env.get('ANON_KEY')
  });

  const url = new URL(req.url);
  const acknowledged = url.searchParams.get('acknowledged');
  const limit = parseInt(url.searchParams.get('limit') || '50');

  let query = client.database
    .from('alerts')
    .select('*, old_decision:decision_records!old_decision_id(content, context, timestamp, source), new_decision:decision_records!new_decision_id(content, context, timestamp, source)')
    .order('created_at', { ascending: false })
    .limit(limit);

  if (acknowledged !== null) {
    query = query.eq('acknowledged', acknowledged === 'true');
  }

  const { data, error } = await query;

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
