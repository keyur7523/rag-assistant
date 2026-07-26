#import os
from anthropic import Anthropic

client = Anthropic()

message = client.messages.create(
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": "Hello, Claude! How is the weather in San Francisco today?",
        }
    ],
    model="claude-opus-4-8",
)

for block in message.content:
    if block.type == "text":
        print(block.text)