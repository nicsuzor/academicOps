export default {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }
    
    try {
      const data = await request.text();
      const message = {
        data: data,
        timestamp: Date.now(),
        id: crypto.randomUUID(),
        headers: Object.fromEntries(request.headers.entries())
      };
      
      await env.WEBHOOK_QUEUE.send(message);
      
      return new Response(JSON.stringify({ 
        success: true, 
        messageId: message.id 
      }), {
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (error) {
      return new Response(JSON.stringify({ 
        error: error.message 
      }), { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
};
