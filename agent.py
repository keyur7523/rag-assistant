from anthropic import Anthropic
import sqlite3
from datetime import date
from query import retrieval_query

itrs = 5
client = Anthropic()
connection = sqlite3.connect("orders.db")
cursor = connection.cursor()

tool = [{
    'name': 'get_order_status',
    'description': """
    Look up a specific customer order by its order ID. Returns the order's current status, the item ordered, the order date, and the expected delivery date. Use this whenever a customer asks about a particular order.
    """,
    'input_schema': {
        'type': 'object',
        'properties': {
            'order_id': {
                'type': 'string',
                'description': "The customer's order ID, e.g. 12345.",
            },
        },
        'required': ['order_id'],
    },
},
{
    'name': 'search_policies',
    'description': """
    Search Northwind Supply Co.'s official policy documents for information about returns, refunds, shipping timelines, and warranties. Use this whenever a customer question depends on company policy — for example return windows, refund processing times, restocking fees, what counts as a late delivery, or warranty coverage. Returns the most relevant policy excerpts with their source document.
    """,
    'input_schema': {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': """
                A natural-language search query describing the policy information needed, e.g. "return window for opened electronics" or "what counts as a late delivery".
                """,
            }
        },
        'required': ['query'],
    }
}]

def get_order_status(order_id):
    cursor.execute(
        """
        SELECT * FROM orders WHERE order_id = ?
        """, (order_id,)
    )
    result = cursor.fetchone()
#    print(result)
    if result is None:
        return f"No order found with id:{order_id}"
    return f"""Order 
            Order Id: {order_id}
            status: {result[4]} 
            ordered on: {result[3]}
            delivery on: {result[5]}
            """

def search_policies(question):
    return retrieval_query(question)

messages = [
        {
            "role": "user",
            #"content": f"What's the status of order 12345?",
            #"content": f"How long do I have to return something?",
            #"content": f"I got order 12346 last week — can I still return it?",
            "content": "I got order 12347 in June — can I still return it?",
        }
    ]

def tool_orchestrator(tool_requested, parameters):
    if tool_requested == 'get_order_status':
        return get_order_status(parameters['order_id'])
    if tool_requested == 'search_policies':
        return search_policies(parameters['query'])

for i in range(itrs):
    message = client.messages.create(
        max_tokens=1024,
        system=f"""
        You are a customer support assistant for Northwind Supply Co.

        Today's date is {date.today().isoformat()}.

        Use the available tools to answer customer questions. Look up specific orders
        when a customer mentions an order, and search the policy documents whenever the
        answer depends on company policy. When a question needs both — for example
        whether an order is still within the return window — use both tools and combine
        what you find.

        Base your answers on what the tools return, not on assumptions. Cite the policy
        document when you state a policy. If the information isn't available, say so
        rather than guessing.
        """,
        tools=tool,
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
                #print(f"TOOL: {block.name} INPUT: {block.input}")
                parameters = block.input
                #print(f'parameters={parameters}')
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

#print(message.content)

for block in message.content:
    if block.type == "text":
        print(block.text)

connection.close()


