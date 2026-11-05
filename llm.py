from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv()

class AnthropicBackend:
    def __init__(self, model_name, system_prompt, tools, max_tokens):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.tools = tools
        self.max_tokens = max_tokens

        self.client = Anthropic()

    def send(self, messages):
        return  self.client.messages.create(
                    model=self.model_name, 
                    max_tokens=self.max_tokens, 
                    system= self.system_prompt, 
                    tools=self.tools, 
                    messages=messages
                )

    def wants_tools(self, response):
        return response.stop_reason == "tool_use"

    def tool_calls(self, response):
        tool_call = []
        for block in response.content:
            if block.type == "tool_use":
                tool_call.append((block.id, block.name, block.input))
        return tool_call

    def assistant_turn(self, response):
        return {"role": "assistant", "content": response.content}

    def tool_result_turns(self, pairs):
        tool_result_turn = []
        for pair in pairs:        
            tool_result_turn.append({
                "type": "tool_result", 
                "tool_use_id": pair[0], 
                "content": pair[1]
            })
        return tool_result_turn

    def final_text(self, response):
        output = []
        for block in response.content:
            if block.type == "text":
                output.append(block.text)
        return '\n'.join(output)



class OllamaBackend:
    def __init__(self, model_name, system_prompt, max_tokens):
        pass