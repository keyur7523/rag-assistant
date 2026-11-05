import datetime
from anthropic import Anthropic
import sqlite3
from query import retrieval_query
from tool import tool
from dotenv import load_dotenv
from guardrails import check_input, check_tool_call, check_output
load_dotenv()


def run_agent(user_message):
    blocked = check_input(user_message)
    if blocked:
        return blocked.message, [("guardrail_block", {"reason": blocked.reason})], 0, False
    itrs = 5
    client = Anthropic()
    connection = sqlite3.connect("orders.db")
    cursor = connection.cursor()
    tools_used = []
    itr_overshoot = True

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
                Customer name: {result[1]}
                Item: {result[2]}
                status: {result[4]} 
                ordered on: {result[3]}
                delivery on: {result[5]}
                """

    def search_policies(question):
        return retrieval_query(question)

    def draft_reply(order_id, customer_name, message):
        with open(f"email_drafts/{order_id}-{customer_name}-{datetime.datetime.now().timestamp()}.txt", "w", encoding="utf-8") as file:
            file.write(message)
        return f"Draft saved for order {order_id}."

    messages = [
            {
                "role": "user",
                #"content": f"What's the status of order 12345?",
                #"content": f"How long do I have to return something?",
                #"content": f"I got order 12346 last week — can I still return it?",
                #"content": "I got order 12347 in June — can I still return it?",
                #'content': "A customer emailed saying order 12345 never arrived. Handle it."
                'content': user_message,
            }
        ]

    def tool_orchestrator(tool_requested, parameters):
        if tool_requested == 'get_order_status':
            return get_order_status(parameters['order_id'])
        if tool_requested == 'search_policies':
            return search_policies(parameters['query'])
        if tool_requested == 'draft_reply':
            return draft_reply(parameters['order_id'], parameters['customer_name'], parameters['message'])
        if tool_requested == "escalate_to_human":
            return escalate_to_human(
                parameters["reason"],
                parameters["summary"],
                parameters.get("order_id"),
            )
        else:
            return f"Unknown tool: {tool_requested}"

    def escalate_to_human(reason, summary, order_id=None):
        ticket = {
            "reason": reason,
            "summary": summary,
            "order_id": order_id,
            "created_at": datetime.datetime.now().isoformat(),
        }
        import json
        from pathlib import Path
        Path("escalations").mkdir(exist_ok=True)
        path = Path("escalations") / f"{datetime.datetime.now().timestamp()}.json"
        path.write_text(json.dumps(ticket, indent=2), encoding="utf-8")
        return (
            f"Escalated to a human agent. Ticket saved at {path.name}. "
            "Tell the customer a human will follow up; do not invent a resolution."
        )

    for i in range(itrs):
        message = client.messages.create(
            max_tokens=1024,
            system=f"""
            You are a customer support assistant for Northwind Supply Co.

            Today's date is {datetime.date.today().isoformat()}.

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
                    tools_used.append((block.name, block.input))
                    parameters = block.input
                    #print(f'parameters={parameters}')
                    tool_requested = block.name
                    tool_guard = check_tool_call(tool_requested, parameters)
                    if tool_guard:
                        tools_used.append(("guardrail_block", {"reason": tool_guard.reason, "tool": tool_requested}))
                        tool_output = tool_guard.message
                    else:
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

    if message.stop_reason == "end_turn": itr_overshoot = False

    #print(message.content)
    connection.close()

    text_block = []

    for block in message.content:
        if block.type == "text":
            text_block.append(block.text)
            
    answer = '\n'.join(text_block)
    answer, _flags = check_output(answer, tools_used)
    return answer, tools_used, i + 1, itr_overshoot

if __name__ == '__main__':
    response, tools_used, iterations_ran, iterations_overshoot = run_agent(user_message="A customer emailed saying order 12345 never arrived. Handle it.")
    print(response)


