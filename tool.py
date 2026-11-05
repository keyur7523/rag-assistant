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
        },
        {
            'name': "draft_reply",
            'description': """Draft a customer support reply and save it for human review. Use this after you have gathered the relevant order details and policy information, when the customer needs a written response to an issue such as a late delivery, a return request, or a refund question. The draft is saved for a support agent to review and send — it is not sent directly to the customer.""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        'description': "The customer's order ID, e.g. 12345.",
                    },
                    "customer_name": {
                        "type": "string",
                        'description': "The customer's name, e.g. Tony Stark.", 
                    },
                    "message": {
                        "type": "string",
                        'description': "The complete reply text to send to the customer, written in a professional and empathetic support tone. Reference the specific order details and cite the relevant policy.",
                    },
                },
                "required": ['order_id', 'customer_name', 'message'],
            },
        },
        {
            "name": "escalate_to_human",
            "description": (
                "Hand the conversation to a human support agent. Use this when the "
                "request is outside policy tools (billing disputes beyond published "
                "rules, legal threats, repeated frustration, or anything you cannot "
                "verify with get_order_status / search_policies). Do not invent an answer."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Short reason for escalation, for the human agent.",
                    },
                    "order_id": {
                        "type": "string",
                        "description": "Order ID if one was mentioned, otherwise omit.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of what the customer asked and what you already checked.",
                    },
                },
                "required": ["reason", "summary"],
            },
        },
]