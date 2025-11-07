export default {
  async queue(batch, env) {
    for (const message of batch.messages) {
      // Process each message
      console.log("Processing:", message.body)
      // Your processing logic here
      message.ack() // Mark as processed
    }
  },
}
