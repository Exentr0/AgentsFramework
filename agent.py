import json
from enum import Enum

import openai
from datetime import datetime
from schemas import generate_response_schema, extract_function_schema


def pretty_print_response(response_json):
    """
    Prints the LLM response in a pretty, structured way with emojis.
    """
    emoji_map = {
        "Thought": "💭",
        "Action": "🎬",
        "Action Input": "🛠️",
        "Observation": "👀",
        "Final Answer": "✅"
    }
    print("\n-------------------------------------------------------------------------------- LLM Response --------------------------------------------------------------------------------")
    for key in ["Thought", "Action", "Action Input", "Observation", "Final Answer"]:
        value = response_json.get(key)
        emoji = emoji_map.get(key, "")
        if value == "NONE" or value is None:
            value_str = "❌"
        else:
            value_str = json.dumps(value, indent=4)
        print(f"{emoji} {key}: {value_str}")
    print("-------------------------------------------------------------------------------- End of Response --------------------------------------------------------------------------------\n")


class Agent:
    def __init__(self, name, functions=None, recipients=None, system_prompt=None, examples=None, additional_instructions=None):
        self.name = name
        self.functions = functions or {}
        self.recipients = recipients or []
        self._register_recipients()
        self.tool_schema = extract_function_schema(self.functions)
        self.system_prompt = (
            system_prompt
            if system_prompt is not None
            else self._generate_system_prompt(examples, additional_instructions)
        )
        self.conversation = [{"role": "system", "content": self.system_prompt}]
        self.response_schema = generate_response_schema(self.tool_schema)

    def _register_recipients(self):
        """Dynamically register recipient agents as callable functions using an Enum for recipient names."""
        # Build a mapping from recipient name (lowercase) to recipient object.
        recipient_mapping = {}

        # Create a dictionary for Enum members.
        enum_members = {recipient.name.lower(): recipient.name.lower() for recipient, description in self.recipients}
        RecipientsEnum = Enum("RecipientsEnum", enum_members)

        # For each recipient, register a function that requires a RecipientsEnum value.
        for recipient, description in self.recipients:
            recipient_name = recipient.name.lower()
            recipient_mapping[recipient_name] = recipient
            function_name = f"talk_to_{recipient_name}"
            function_doc = f"Ask {recipient.name}, which {description}."

            def generated_function(message: str, recipient_name: RecipientsEnum, function_doc=function_doc):
                """{0}""".format(function_doc)
                return recipient_mapping[recipient_name].call(message)

            self.functions[function_name] = generated_function

    def _generate_system_prompt(self, examples=None, additional_instructions=None):
        """
        Generate a system prompt enforcing structured JSON output.
        If additional_instructions is provided, it is prepended to the prompt.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        prompt = ""
        if additional_instructions:
            prompt += additional_instructions.strip() + "\n"
        prompt += f"""
You reason and act to solve user queries. Today's date is {current_date}.
Your responses must always be valid JSON following this schema:

{{
    "Thought": "string",
    "Action": "CALL_FUNCTION" or "NONE",
    "Action Input": {{
        "name": "string (function name)",
        "arguments": {{"any": "object (function arguments)"}}
    }} or null,
    "Observation": "string or object or null",
    "Final Answer": "string or null"
}}

You are also an AI that can call functions using the schema below:
    {self.tool_schema}
"""
        if examples:
            prompt += f"\n\nEXAMPLES:\n{examples}\n"
        prompt += """
When executing a function call, omit Final_Answer.
If a function call fails, adjust parameters and retry.
Only output valid JSON; no extraneous text.
"""
        return prompt

    def call_function(self, function_name, **kwargs):
        """Execute a registered function with given arguments."""
        function = self.functions.get(function_name)
        if not function:
            return {"error": f"Unknown function '{function_name}'"}
        return function(**kwargs)

    def call(self, user_input, max_retries=100):
        """Process user input via OpenAI API, executing function calls as needed."""
        self.conversation.append({"role": "user", "content": user_input})

        for _ in range(max_retries):
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=self.conversation,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "response_schema",
                        "schema": self.response_schema,
                        "strict": True
                    }
                }
            )

            response_message = response.choices[0].message.content
            self.conversation.append({"role": "assistant", "content": response_message})

            structured_output = json.loads(response_message)

            print(f"Agent : {self.name}")
            # Use the external pretty_print_response function to display the response
            pretty_print_response(structured_output)

            if structured_output.get("Final Answer"):
                return structured_output["Final Answer"]

            elif action_input := structured_output.get("Action Input"):
                function_name = action_input.get("name")
                arguments = action_input.get("arguments", {})
                function_result = self.call_function(function_name, **arguments)
                self.conversation.append({
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(function_result)
                })
            else:
                self.conversation.append({
                    "role": "system",
                    "content": "Action Input and Final Answer can't be null simultaneously"
                })

        return "Error: Maximum retries reached."
