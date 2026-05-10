import { createClient } from 'npm:@insforge/sdk';

export default async function(req: Request): Promise<Response> {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, PUT, OPTIONS',
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
  const { id, name, system_prompt, active } = body;

  if (!id) {
    return new Response(JSON.stringify({ error: 'Missing persona id' }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  const updateData: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (name !== undefined) updateData.name = name;
  if (system_prompt !== undefined) updateData.system_prompt = system_prompt;
  if (active !== undefined) updateData.active = active;

  const { data, error } = await client.database
    .from('personas')
    .update(updateData)
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
