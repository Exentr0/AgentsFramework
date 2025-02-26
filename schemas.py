import json
import inspect
from typing import (
    Dict, List, Callable, Union, get_origin, get_args
)
from enum import Enum

def get_python_type(annotation: type) -> str:
    """Maps Python basic types to JSON schema types."""
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        dict: "object",
        list: "array",
    }
    if annotation in type_mapping:
        return type_mapping[annotation]
    else:
        raise ValueError(f"Unsupported annotation type: {annotation}")

def get_schema_for_type(annotation: type) -> Dict:
    """
    Recursively converts a Python type annotation into a JSON Schema snippet.
    """
    # First, check if the type is an Enum.
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return {
            "type": "string",
            "enum": [member.value for member in annotation]
        }

    # Next, check if it's a TypedDict (has defined properties)
    if isinstance(annotation, type) and issubclass(annotation, dict) and hasattr(annotation, '__annotations__'):
        properties = {}
        for key, val in annotation.__annotations__.items():
            properties[key] = get_schema_for_type(val)
        return {
            "type": "object",
            "properties": properties,
            "required": list(annotation.__annotations__.keys()),
            "additionalProperties": False
        }

    origin = get_origin(annotation)
    if origin is None:
        return {"type": get_python_type(annotation)}

    # Handle Union types (including Optional)
    if origin is Union:
        args = get_args(annotation)
        return {"anyOf": [get_schema_for_type(arg) for arg in args]}

    # Handle list types.
    elif origin in (list, List):
        args = get_args(annotation)
        if args:
            return {"type": "array", "items": get_schema_for_type(args[0])}
        else:
            return {"type": "array", "items": {"type": "string"}}

    # Handle dict types.
    elif origin in (dict, Dict):
        args = get_args(annotation)
        if args and len(args) == 2:
            key_type, value_type = args
            key_schema = get_schema_for_type(key_type) if key_type is not None else {"type": "string"}
            value_schema = get_schema_for_type(value_type) if value_type is not None else {"type": "string"}
            return {
                "type": "object",
                "properties": {
                    "property1": key_schema,
                    "property2": value_schema
                },
                "required": ["property1", "property2"],
                "additionalProperties": False
            }
        else:
            # If no explicit key/value types are provided, assume strings.
            return {
                "type": "object",
                "properties": {
                    "property1": {"type": "string"},
                    "property2": {"type": "string"}
                },
                "required": ["property1", "property2"],
                "additionalProperties": False
            }

    else:
        return {"type": get_python_type(annotation)}

def extract_function_schema(functions: Dict[str, Callable]) -> str:
    """
    Extracts metadata from functions and generates a JSON schema.

    For each function the parameter type hints are recursively processed.
    """
    schema = []

    for name, func in functions.items():
        signature = inspect.signature(func)
        parameters_schema = {}

        for param_name, param in signature.parameters.items():
            # Use the annotation if available; otherwise, default to str.
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
            param_schema = get_schema_for_type(annotation)
            param_schema["title"] = param_name.capitalize()
            param_schema["description"] = f"Parameter for {param_name}"
            parameters_schema[param_name] = param_schema

        schema.append({
            "function": {
                "name": name,
                "description": func.__doc__.strip() if func.__doc__ else "No description available.",
                "parameters": {
                    "type": "object",
                    "properties": parameters_schema,
                    "required": list(parameters_schema.keys()),
                    "additionalProperties": False
                },
                "strict": True
            },
            "type": "function"
        })

    return json.dumps(schema, indent=4)

def build_action_input_schema(tool_definitions_schema: str) -> List[Dict]:
    """Builds a dynamic 'oneOf' schema for the 'Action_Input' field."""
    tool_definitions = json.loads(tool_definitions_schema)
    branches = []

    for tool in tool_definitions:
        func_info = tool["function"]
        branches.append({
            "type": "object",
            "properties": {
                "name": {
                    "enum": [func_info["name"]],
                    "description": func_info["description"]
                },
                "arguments": func_info["parameters"]
            },
            "required": ["name", "arguments"],
            "additionalProperties": False
        })

    return branches + [{"type": "null"}]

def generate_response_schema(tool_definitions_schema: str) -> Dict:
    """Generates a JSON schema for the AI's ReAct output."""
    return {
        "type": "object",
        "description": "Schema for AI responses ensuring strict JSON formatting.",
        "properties": {
            "Thought": {"type": "string", "description": "AI's reasoning before taking action."},
            "Action": {"type": "string", "enum": ["CALL_FUNCTION", "NONE"], "description": "Chosen action."},
            "Action Input": {"anyOf": build_action_input_schema(tool_definitions_schema)},
            "Observation": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "null"},
                    {"type": "object", "additionalProperties": False}
                ],
                "description": "Result of the executed action."
            },
            "Final Answer": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Final answer to the query. Should be null if an action is executed."
            }
        },
        "additionalProperties": False,
        "required": ["Thought", "Action", "Action Input", "Observation", "Final Answer"]
    }
