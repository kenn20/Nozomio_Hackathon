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
  const source = url.searchParams.get('source');
  const limit = parseInt(url.searchParams.get('limit') || '100');

  let query = client.database
    .from('decision_records')
    .select('id, source, content, context, timestamp, tags, status')
    .order('timestamp', { ascending: false })
    .limit(limit);

  if (source) {
    query = query.eq('source', source);
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
