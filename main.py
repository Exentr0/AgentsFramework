import os
import openai
from dotenv import load_dotenv
from agent import Agent

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Define a simple function for Agent2 that returns a greeting.
def say_hello(name: str) -> str:
    return f"Hello, {name}! This is Agent2."

# Initialize Agent2 with its function tool.
agent2_functions = {
    'say_hello': say_hello,
}
agent2 = Agent(name="Agent2", functions=agent2_functions)

# Initialize Agent1 and register Agent2 as a recipient.
# This automatically creates a function called 'talk_to_agent2' in Agent1.
agent1 = Agent(name="Agent1", recipients=[(agent2, "provides greeting functionality")])

# Agent1 sends a message requesting Agent2 to greet a user.
# The framework will internally use the registered function 'talk_to_agent2' to communicate.
response = agent1.call("Please ask Agent2 to say hello to Alice.")
print("Final Answer from Agent1:", response)