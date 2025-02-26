# ReAct Structured AI Agent Framework

This repository provides an implementation of the ReAct framework for AI agents integrated with OpenAI's structured outputs. It is designed to offer a robust and modular environment where developers can create intelligent agents capable of reasoning and acting. Notably, this implementation supports the creation of schemas for nested datatypes of functions, enabling sophisticated and layered function definitions.

## Overview

The project combines two key innovations:
- **ReAct Framework:** Implements the ReAct paradigm as described in the [ReAct paper](https://arxiv.org/abs/2210.03629), which blends reasoning and action to improve decision-making in AI agents.
- **OpenAI Structured Outputs:** Utilizes OpenAI's structured output format to provide clear, consistent, and controlled responses from AI agents.

This integration facilitates the development of agents that can not only process natural language inputs but also produce well-defined, structured outputs based on nested function schemas.

## Features

- **ReAct Implementation:** Follows the principles outlined in the [ReAct paper](https://arxiv.org/abs/2210.03629) to combine reasoning and action in AI agents.
- **Structured Output Handling:** Leverages OpenAI's capabilities to generate outputs that adhere to predefined, structured formats.
- **Nested Datatype Schemas:** Supports creating detailed schemas for nested function datatypes, enabling complex function signatures and output structures.
- **Modular and Extensible:** Designed with a modular architecture to easily integrate new functionalities or customize existing ones.

## Agent Communication
Agents communicate with each other through dynamically registered functions

## Simple Example: Two-Agent Communication

This simple example demonstrates how to set up two agents where one agent communicates with another. In this example, **Agent2** provides a simple greeting function as a tool, and **Agent1** is configured to interact with Agent2 using a dynamically registered function.

### Example Code

```python
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