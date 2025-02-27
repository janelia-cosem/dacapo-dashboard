from flask import request, jsonify, render_template
import attr
from funlib.geometry import Coordinate
import dacapo

from .blue_print import bp

import typing
from typing import get_origin, get_args, List, Union, Tuple
from enum import Enum
from pathlib import Path


def get_name(cls):
    try:
        return cls.__name__
    except AttributeError:
        return str(cls)


@bp.route("/configurable", methods=["POST"])
def configurable():
    name = request.json["name"]
    id_prefix = request.json["id_prefix"]
    try:
        # want to add a sub_element representing a dacapo configurable element
        configurable = getattr(dacapo.configurables, name)
        fields = parse_fields(configurable)
        html = render_template(
            "dacapo/forms/subform.html", fields=fields, id_prefix=id_prefix
        )
        return jsonify({"html": html})
    except AttributeError:
        try:
            field_type = getattr(dacapo.config_fields, name)
        except AttributeError:
            field_type = eval(name)
        field = get_field_type(field_type, {})
        print(field)
        html = render_template(
            "dacapo/forms/field.html", field=field, id_prefix=id_prefix
        )
        return jsonify({"html": html})

    try:
        fields = parse_fields(configurable)
        html = render_template(
            "dacapo/forms/subform.html", fields=fields, id_prefix=id_prefix
        )
    except (attr.exceptions.NotAnAttrsClassError, TypeError) as e:
        print(e)
        field = get_field_type(configurable, {})
        html = render_template(
            "dacapo/forms/field.html", field=field, id_prefix=id_prefix
        )
    return jsonify({"html": html})


def handle_simple_types(field_type, metadata):
    """
    simple types are types that don't really need any javascript.
    int -> text input, number
    str -> text input, string
    float -> text input, (bounds, step metadata)
    """
    simple_types = {int: "int", str: "str", float: "float", bool: "bool", Path: "path"}
    return {
        "type": simple_types[field_type],
        "help_text": metadata.get("help_text"),
        "default": metadata.get("default"),
    }


def handle_special_cases(field_type, metadata):
    """
    simple types are types that don't really need any javascript.
    int -> text input, number
    str -> text input, string
    float -> text input, (bounds, step metadata)
    """
    if field_type == Coordinate:
        return {
            "type": "coordinate",
            "help_text": metadata.get("help_text"),
            "element": "int",
        }


def handle_enum(field_type, metadata):
    return {"type": "enum", "choices": [e.value for e in field_type]}


def is_optional(field_type):
    # field must be a Union with 2 options, one of which is None
    return (
        get_origin(field_type) == Union
        and len(get_args(field_type)) == 2
        and get_args(field_type)[1] == type(None)
    )


def is_choice(field_type):
    """
    A union over multiple types
    """
    return get_origin(field_type) == Union and not is_optional(field_type)


def is_expandable(field_type):
    return get_origin(field_type) in (list, dict, tuple)


def handle_complex_types(field_type, metadata):
    complex_types = {
        list: "list",
        dict: "dict",
        Union: "union",
        tuple: "tuple",
        Enum: "enum",
    }
    if is_optional(field_type):
        # add optional tag to field data and recurse 1 layer down
        field_data = {"optional": True}
        field_data.update(get_field_type(get_args(field_type)[0], metadata))
        return field_data
    elif is_choice(field_type):
        choices = [x.__name__ for x in get_args(field_type)]
        field_data = {
            "type": "choice",
            "choices": choices,
            "help_text": metadata.get("help_text"),
        }
        return field_data
    elif get_origin(field_type) == dict:
        key, value = get_args(field_type)
        key = get_name(key)
        value = get_name(value)
        field_data = {
            "type": "dict",
            "key": key,
            "value": value,
            "help_text": metadata.get("help_text"),
        }
        return field_data
    elif get_origin(field_type) == list:
        elements = get_args(field_type)
        assert len(elements) == 1
        element = get_name(elements[0])

        field_data = {
            "type": "list",
            "help_text": metadata.get("help_text"),
            "element": element,
        }
        return field_data
    elif get_origin(field_type) == tuple:
        args = [get_field_type(x, {}) for x in get_args(field_type)]
        if "__default" in metadata and metadata["__default"] is not attr.NOTHING:
            for i, default in enumerate(metadata["__default"]):
                args[i]["default"] = default
        field_data = {
            "type": "tuple",
            "help_text": metadata.get("help_text"),
            "args": args,
        }
        return field_data
    else:
        raise RuntimeError(f"GOT UNSUPPORTED COMPLEX TYPE: {field_type}")


def get_field_type(field_type, metadata):
    simple_types = {int: "int", str: "str", float: "float", bool: "bool", Path: "path"}
    complex_types = {
        list: "list",
        dict: "dict",
        Union: "union",
        tuple: "tuple",
    }
    special_cases = {Coordinate: "coordinate"}
    if field_type in simple_types:
        return handle_simple_types(field_type, metadata)

    elif get_origin(field_type) in complex_types:
        return handle_complex_types(field_type, metadata)

    elif field_type in special_cases:
        return handle_special_cases(field_type, metadata)

    elif issubclass(field_type, Enum):
        return handle_enum(field_type, metadata)

    else:
        try:
            configurable = getattr(dacapo.configurables, field_type.__name__)
            fields = parse_fields(configurable)
            return {
                "type": "configurable",
                "fields": fields,
                "help_text": metadata.get("help_text"),
            }
        except AttributeError:
            pass

    raise ValueError(
        f"Unsupported type: {field_type}, "
        f"origin: {get_origin(field_type)}, "
        f"args: {get_args(field_type)}"
    )


def parse_field(field):
    field_data = {}
    metadata = dict(**field.metadata)
    metadata["__default"] = field.default
    field_data.update(get_field_type(field.type, metadata))
    field_data["default"] = field.default if field.default is not attr.NOTHING else None
    return field_data


def parse_fields(configurable):
    field_data = {field.name: parse_field(field) for field in attr.fields(configurable)}

    return field_data
