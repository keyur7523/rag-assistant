from anthropic import Anthropic

itrs = 5
client = Anthropic()

tool = {
    'name': 'get_order_status',
    'description': 'Look up the current status of a customer order by its order ID',
    'input_schema': {
        'type': 'object',
        'properties': {
            'order_id': {
                'type': 'string',
                'description': "The customer's order ID.",
            },
        },
        'required': ['order_id'],
    },
}

def get_order_status(order_id):
    return f"Order (Order Id: {order_id}) shipped Jan 3, expected delivery Jan 8, currently in transit."

messages = [
        {
            "role": "user",
            "content": "What's the status of order 12345?",
        }
    ]

def tool_orchestrator(tool_requested, parameters):
    if tool_requested == 'get_order_status':
        return get_order_status(parameters['order_id'])

for i in range(itrs):
    message = client.messages.create(
        max_tokens=1024,
        tools=[tool],
        messages=messages,
        model="claude-opus-4-8",
    )

    if (message.stop_reason == 'end_turn'): break
    else: # 'tool_use'
        tool_result = []
        messages.append({
            'role': 'assistant',
            'content': message.content,
        })

        for block in message.content:
            if block.type == "tool_use":
                parameters = block.input
                tool_requested = block.name
                tool_output = tool_orchestrator(tool_requested, parameters)
                tool_result.append({
                    "type": "tool_result", 
                    "tool_use_id": block.id, 
                    "content": tool_output
                })

        messages.append({
            'role': 'user',
            'content': tool_result
        })

for block in message.content:
    if block.type == "text":
        print(block.text)


