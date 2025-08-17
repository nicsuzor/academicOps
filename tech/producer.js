export default {
  async fetch(request, env) {
    if (request.method !== 'POST') return new Response('Method not allowed', { status: 405 });
    
    const data = await request.text();
    await env.WEBHOOK_QUEUE.send({ data, timestamp: Date.now() });
    
    return new Response('Queued successfully');
  }
};
