#!/usr/bin/env python
#
# Copyright (c) 2026, René Moser <mail@renemoser.net>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at http://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
#
# Note: the rest of this collection is GPL-3.0-or-later. This standalone
# development script is deliberately licensed differently and is excluded from
# the built collection by "build_ignore" in galaxy.yml.

"""Generate an OpenAPI 3.2 document from the Apache CloudStack ``listApis`` endpoint.

CloudStack describes itself through ``listApis``, which returns a bespoke,
non-standard catalogue of every API command, its request parameters and its
response fields.  This script translates that catalogue into an OpenAPI 3.2.0
document that can be fed to documentation browsers and client generators.

Requires Python 3.10 or newer. See scripts/README.md for the mapping rules and
their known limits.
"""

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Literal, TextIO

# A JSON object as it appears in listApis, and an OpenAPI schema fragment.
Json = dict[str, Any]
Schema = dict[str, Any]
Kind = Literal["top", "nested"]

OPENAPI_VERSION = "3.2.0"

# Verbs CloudStack puts in front of the entity name, longest first so that e.g.
# "disassociate" wins over "associate". Used for tag names and schema names only.
COMMAND_VERBS: tuple[str, ...] = (
    "disassociate",
    "deactivate",
    "authorize",
    "reconnect",
    "configure",
    "associate",
    "provision",
    "unregister",
    "unmanage",
    "dedicate",
    "activate",
    "generate",
    "download",
    "register",
    "schedule",
    "validate",
    "release",
    "restore",
    "suspend",
    "migrate",
    "destroy",
    "extract",
    "recover",
    "replace",
    "archive",
    "cancel",
    "change",
    "create",
    "delete",
    "detach",
    "enable",
    "expunge",
    "import",
    "attach",
    "assign",
    "remove",
    "resize",
    "revert",
    "revoke",
    "update",
    "upload",
    "verify",
    "deploy",
    "reboot",
    "reset",
    "scale",
    "start",
    "query",
    "issue",
    "prepare",
    "quiesce",
    "restart",
    "link",
    "lock",
    "mark",
    "move",
    "find",
    "list",
    "copy",
    "add",
    "get",
    "put",
    "run",
    "stop",
    "is",
)

# CloudStack scalar types -> OpenAPI schema. Anything absent here is handled by
# SchemaRegistry.map_type() below.
SCALAR_TYPES: dict[str, Schema] = {
    "string": {"type": "string"},
    "uuid": {"type": "string", "format": "uuid"},
    "boolean": {"type": "boolean"},
    "integer": {"type": "integer", "format": "int32"},
    "int": {"type": "integer", "format": "int32"},
    "short": {"type": "integer", "format": "int32"},
    "long": {"type": "integer", "format": "int64"},
    "float": {"type": "number", "format": "float"},
    "double": {"type": "number", "format": "double"},
    "bigdecimal": {"type": "number"},
    # CloudStack renders dates as "2026-07-29T11:18:10+0000", which is ISO 8601
    # but not RFC 3339 (no colon in the offset), so "format: date-time" would be
    # a lie. Request parameters additionally accept a bare "yyyy-MM-dd".
    "date": {"type": "string"},
    "tzdate": {"type": "string"},
    # Only ever used for opaque strings such as a MAC address or a URL.
    "object": {"type": "string"},
}

DATE_NOTE = 'CloudStack date, ISO 8601 with a numeric offset, for example "2026-07-29T11:18:10+0000".'
MAP_NOTE = "Map parameter. CloudStack expects it index-encoded as `{name}[0].key=k&{name}[0].value=v`."
LIST_NOTE = "List parameter. CloudStack expects the values comma-separated in a single occurrence."

# Injected by this generator, so a command may not redefine them.
RESERVED_PARAMETERS = ("command", "response", "apiKey", "signature", "sessionkey")


def die(msg: str) -> None:
    sys.stderr.write(f"cs_openapi: {msg}\n")
    sys.exit(1)


def pascal_case(value: str) -> str:
    """cloudstackName -> CloudstackName, keeping already-cased words intact."""
    value = re.sub(r"[^0-9a-zA-Z]+", " ", value or "").strip()
    if not value:
        return ""
    return "".join(part[:1].upper() + part[1:] for part in value.split(" "))


def entity_of(command: str) -> str:
    """Strip the leading verb off a command name: listVirtualMachines -> VirtualMachines."""
    lowered = command.lower()
    for verb in COMMAND_VERBS:
        if lowered.startswith(verb) and len(command) > len(verb):
            return command[len(verb) :]
    return command


def singularize(entity: str) -> str:
    """listVirtualMachines and deployVirtualMachine must land in the same group."""
    if entity.endswith("ies") and len(entity) > 4:
        return f"{entity.removesuffix('ies')}y"
    if entity.endswith("sses") and len(entity) > 5:
        return entity.removesuffix("es")
    # "Address" and "Status" are not plurals.
    if entity.endswith("s") and not entity.endswith(("ss", "us")) and len(entity) > 2:
        return entity.removesuffix("s")
    return entity


def entity_name(command: str) -> str:
    """The entity a command acts on, as spelled in the command name."""
    return singularize(pascal_case(entity_of(command))) or "Other"


def build_tagger(commands: list[str], min_shared: int = 3, min_anchor_length: int = 5):
    """Map each command onto a tag, collapsing compound entities onto a common one.

    Stripping the verb alone splits the API into ~380 groups, half of them with a
    single command: addNicToVirtualMachine becomes "NicToVirtualMachine" rather
    than "VirtualMachine". Entities shared by several commands are therefore used
    as anchors, and a compound entity is folded into the longest anchor it ends
    with.
    """
    counts = Counter(entity_name(command) for command in commands)
    anchors = sorted(
        (entity for entity, hits in counts.items() if hits >= min_shared and len(entity) >= min_anchor_length),
        key=len,
        reverse=True,
    )

    def tag(command: str) -> str:
        entity = entity_name(command)
        if counts.get(entity, 0) >= min_shared:
            return entity
        lowered = entity.lower()
        for anchor in anchors:
            if lowered != anchor.lower() and lowered.endswith(anchor.lower()):
                return anchor
        return entity

    return tag


def clean_fields(fields: list[Json] | None) -> list[Json]:
    """listApis pads response field lists with empty objects; drop them."""
    return [f for f in (fields or []) if f.get("name")]


def join_description(base: str | None, note: str) -> str:
    """Append a generator note to a listApis description without running it together."""
    base = (base or "").strip()
    if not base:
        return note
    if base[-1] not in ".!?":
        base += "."
    return f"{base} {note}"


def described(schema: Schema, description: str | None) -> Schema:
    if description:
        schema["description"] = description
    return schema


def related_commands(value: str | None) -> list[str]:
    """listApis repeats entries in the comma separated "related" field."""
    if not value:
        return []
    return sorted({name.strip() for name in value.split(",") if name.strip()})


def envelope_key(command: str) -> str:
    """CloudStack wraps every body in a "<command>response" key, lower-cased."""
    return f"{command.lower()}response"


def first_sentence(text: str | None) -> str:
    text = (text or "").strip().replace("\n", " ")
    if not text:
        return ""
    match = re.match(r"^(.+?\.)(\s|$)", text)
    return (match.group(1) if match else text)[:250]


@dataclass
class Shape:
    """One structurally distinct CloudStack response object."""

    fields: list[Json]
    labels: list[tuple[str, Kind]] = field(default_factory=list)
    name: str = ""


class SchemaRegistry:
    """Collects response object shapes and deduplicates structurally identical ones.

    A CloudStack response object (a virtual machine, a NIC, a tag, ...) is
    repeated verbatim in every command that returns it -- 1376 objects collapse
    to roughly 250 distinct shapes -- so each shape becomes one component schema
    that the operations reference.
    """

    def __init__(self) -> None:
        self._by_signature: dict[str, Shape] = {}
        self.schemas: dict[str, Schema] = {}

    @staticmethod
    def _signature(fields: list[Json] | None) -> str:
        parts = [
            (f["name"], f.get("type") or "", SchemaRegistry._signature(nested) if (nested := f.get("response")) else "")
            for f in sorted(clean_fields(fields), key=lambda f: f["name"])
        ]
        return json.dumps(parts, sort_keys=True)

    def add(self, fields: list[Json] | None, label: str, kind: Kind) -> str:
        """Register an object shape. Returns its signature; names are assigned later."""
        cleaned = clean_fields(fields)
        signature = self._signature(cleaned)
        shape = self._by_signature.setdefault(signature, Shape(fields=cleaned))
        shape.labels.append((label, kind))
        for entry in cleaned:
            if nested := entry.get("response"):
                self.add(nested, entry["name"], "nested")
        return signature

    @staticmethod
    def _preferred_name(shape: Shape) -> str:
        """Name a shape after what it structurally is, not after one of its users."""
        if nested_labels := [label for label, kind in shape.labels if kind == "nested"]:
            return pascal_case(Counter(nested_labels).most_common(1)[0][0])

        names = {f["name"] for f in shape.fields}
        if names <= {"success", "displaytext", "jobid", "jobstatus"} and "success" in names:
            # Shared by every delete-style command, so no single command should name it.
            return "SuccessResult"

        # A top-level shape: if the commands returning it agree on an entity,
        # the shape is that entity (29 commands return the VirtualMachine shape).
        commands = [label for label, kind in shape.labels if kind == "top"]
        entity, hits = Counter(entity_name(command) for command in commands).most_common(1)[0]
        if hits > 1 or len(commands) == 1:
            return entity
        return f"{pascal_case(sorted(commands)[0])}Result"

    def finalize(self) -> dict[str, Schema]:
        """Assign a unique name to every shape and build the component schemas."""
        used: set[str] = set()
        for shape in self._by_signature.values():
            name = self._preferred_name(shape) or "Object"
            if name in used:
                suffix = 2
                while f"{name}{suffix}" in used:
                    suffix += 1
                name = f"{name}{suffix}"
            used.add(name)
            shape.name = name
        self.schemas = {shape.name: self._build(shape) for shape in self._by_signature.values()}
        return self.schemas

    def ref(self, signature: str) -> Schema:
        return {"$ref": f"#/components/schemas/{self._by_signature[signature].name}"}

    def _build(self, shape: Shape) -> Schema:
        return {
            "type": "object",
            "properties": {f["name"]: self.map_type(f, response=True) for f in sorted(shape.fields, key=lambda f: f["name"])},
        }

    def map_type(self, field: Json, response: bool) -> Schema:
        """Translate one CloudStack type name into an OpenAPI schema."""
        cs_type = (field.get("type") or "string").lower()
        description = (field.get("description") or "").strip()
        nested = field.get("response")

        match cs_type:
            case _ if cs_type in SCALAR_TYPES:
                schema = dict(SCALAR_TYPES[cs_type])
                if cs_type in ("date", "tzdate"):
                    description = join_description(description, DATE_NOTE)
                if cs_type not in ("string", "uuid") and schema.get("type") == "string":
                    schema["x-cloudstack-type"] = cs_type
                return described(schema, description)

            case _ if cs_type.endswith("[]"):
                item = SCALAR_TYPES.get(cs_type.removesuffix("[]"), {"type": "string"})
                return described({"type": "array", "items": dict(item)}, description)

            case "list" | "set":
                if nested:
                    items = self.ref(self._signature(nested))
                elif response:
                    # listApis documents no element shape here, and such fields do
                    # carry objects in practice (Template.downloaddetails), so the
                    # items stay unconstrained rather than guessing "string".
                    items = {}
                else:
                    # A request list is comma-joined into one query value, so its
                    # elements are always strings on the wire.
                    items = {"type": "string"}
                if not response:
                    description = join_description(description, LIST_NOTE)
                return described({"type": "array", "items": items, "x-cloudstack-type": cs_type}, description)

            case "map":
                # On the wire a request map is always strings; a response map is not.
                schema = {
                    "type": "object",
                    "additionalProperties": {} if response else {"type": "string"},
                    "x-cloudstack-type": "map",
                }
                if not response:
                    schema["x-cloudstack-encoding"] = "indexed-map"
                    description = join_description(description, MAP_NOTE.format(name=field["name"]))
                return described(schema, description)

            case _ if nested:
                ref = self.ref(self._signature(nested))
                # A $ref sibling is allowed in OpenAPI 3.1+ but keep it unambiguous.
                return {"allOf": [ref], "description": description} if description else ref

            case _ if cs_type.endswith("response") or cs_type == "responseobject":
                return described({"type": "object", "x-cloudstack-type": cs_type}, description)

            case _:
                # Enum-like CloudStack types (state, powerstate, imageformat, ...).
                # The allowed values are not part of listApis, so only the name is
                # carried.
                return described({"type": "string", "x-cloudstack-type": cs_type}, description)


COMMON_PARAMETERS: dict[str, Json] = {
    "response": {
        "name": "response",
        "in": "query",
        "description": "Format of the response body. This document only describes the JSON rendering.",
        "required": False,
        "schema": {"type": "string", "enum": ["json", "xml"], "default": "json"},
    },
    "page": {
        "name": "page",
        "in": "query",
        "description": "Page to return, used together with `pagesize`.",
        "required": False,
        "schema": {"type": "integer", "format": "int32", "minimum": 1},
    },
}

SECURITY_SCHEMES: dict[str, Json] = {
    "apiKey": {
        "type": "apiKey",
        "in": "query",
        "name": "apiKey",
        "description": "API key of the CloudStack user. Must be sent together with `signature`.",
    },
    "signature": {
        "type": "apiKey",
        "in": "query",
        "name": "signature",
        "description": ("Base64-encoded HMAC-SHA1 of the lower-cased, alphabetically sorted, URL-encoded query string, signed with the user's secret key."),
    },
    "sessionKey": {
        "type": "apiKey",
        "in": "query",
        "name": "sessionkey",
        "description": "Session key obtained from `login`, used instead of `apiKey` plus `signature`.",
    },
}

ERROR_SCHEMA: Schema = {
    "type": "object",
    "description": "Error body CloudStack returns in place of the documented payload.",
    "properties": {
        "errorcode": {"type": "integer", "description": "Error code, mirrored in the HTTP status."},
        "cserrorcode": {"type": "integer", "description": "CloudStack specific error code."},
        "errortext": {"type": "string", "description": "Human readable error message."},
        "uuidList": {
            "type": "array",
            "description": "UUIDs of the entities the error refers to.",
            "items": {"type": "object"},
        },
    },
}

ASYNC_SCHEMA: Schema = {
    "type": "object",
    "description": ("Acknowledgement of an asynchronous command. Poll `queryAsyncJobResult` with `jobid` to obtain the documented payload."),
    "properties": {
        "jobid": {"type": "string", "format": "uuid", "description": "ID of the async job."},
        "id": {"type": "string", "description": "ID of the entity the job acts on, when already known."},
    },
    "additionalProperties": True,
}

DESCRIPTION_HEADER = """\
OpenAPI rendering of the Apache CloudStack API, generated from the `listApis`
command by `scripts/cs_openapi.py` of the `ngine_io.cloudstack` Ansible
collection.

**Paths in this document are synthetic.** CloudStack exposes a single endpoint
and selects the command with a query parameter, which OpenAPI cannot express:
every request actually goes to `{server}?command=<operationId>`. Each operation
is therefore keyed by a path named after its command, and carries a required
`command` parameter pinned to that command. A client generated from this
document must send the `command` parameter and ignore the path segment.

Every response body is wrapped by CloudStack in a single `<command>response`
key, which is reflected in the schemas. `listApis` describes the *entity* a
command returns rather than that envelope, so for non-list commands the payload
is modelled as either the entity itself or the entity nested under a
command-specific key.

Requests are authenticated with `apiKey` plus a `signature` computed from the
request, or with a `sessionkey` obtained from `login`.\
"""


def build_parameter(param: Json, registry: SchemaRegistry) -> Json:
    schema = registry.map_type(param, response=False)
    description = schema.pop("description", None)
    encoding = schema.pop("x-cloudstack-encoding", None)

    parameter: Json = {"name": param["name"], "in": "query"}
    if description:
        parameter["description"] = description
    if param.get("required"):
        parameter["required"] = True
    if (param.get("type") or "string").lower() in ("list", "set"):
        # ids=a,b,c rather than ids=a&ids=b&ids=c
        parameter["style"] = "form"
        parameter["explode"] = False
    if encoding:
        parameter["x-cloudstack-encoding"] = encoding
    if (length := param.get("length")) and schema.get("type") == "string":
        schema["maxLength"] = length
    parameter["schema"] = schema
    if since := param.get("since"):
        parameter["x-cloudstack-since"] = since
    if related := related_commands(param.get("related")):
        parameter["x-cloudstack-related"] = related
    return parameter


def dedupe_params(api: Json) -> list[Json]:
    """listApis lists some parameters twice; OpenAPI requires them to be unique."""
    seen: dict[str, Json] = {}
    for param in api.get("params") or []:
        name = param["name"]
        if name in RESERVED_PARAMETERS:
            sys.stderr.write(f"cs_openapi: {api['name']} declares the reserved parameter {name!r}, skipping it\n")
            continue
        if name in seen:
            # Keep the first description, but never lose a "required" flag.
            seen[name]["required"] = seen[name].get("required") or param.get("required")
            continue
        seen[name] = dict(param)
    return list(seen.values())


def build_payload_schema(api: Json, signature: str, registry: SchemaRegistry, response_key: tuple[str, bool] | None) -> Schema:
    """Schema for the body inside the "<command>response" envelope.

    listApis documents the *entity* a command deals with, never the envelope
    around it. CloudStack then returns that entity either directly (delete-style
    commands), nested under a command specific key (`{"zone": {...}}`), or as a
    counted array (`{"count": 1, "zone": [...]}`). The key is not part of
    listApis, so unless it was resolved by probing a live endpoint the schema
    stays open enough to validate all three renderings.
    """
    payload = registry.ref(signature)
    count_property: Schema = {"type": "integer", "description": "Total number of matching entities."}

    if response_key:
        key, is_array = response_key
        properties: dict[str, Schema] = {}
        if is_array:
            properties["count"] = count_property
            properties[key] = {"type": "array", "items": payload}
        else:
            properties[key] = payload
        return {"type": "object", "properties": properties, "additionalProperties": True}

    nested: Schema = {
        "type": "object",
        "properties": {"count": count_property},
        "additionalProperties": {"oneOf": [payload, {"type": "array", "items": payload}]},
    }
    if api["name"].startswith("list"):
        return nested
    return {"oneOf": [payload, nested]}


def build_operation(api: Json, signature: str, registry: SchemaRegistry, response_key: tuple[str, bool] | None, tag: str) -> Json:
    command = api["name"]
    key = envelope_key(command)
    is_async = bool(api["isasync"])

    parameters: list[Json] = [{"$ref": "#/components/parameters/response"}]
    parameters += [build_parameter(param, registry) for param in sorted(dedupe_params(api), key=lambda p: (not p.get("required"), p["name"]))]

    if is_async:
        payload: Schema = {"$ref": "#/components/schemas/AsyncJobStart"}
    else:
        payload = build_payload_schema(api, signature, registry, response_key)

    description = (api.get("description") or "").strip()
    if is_async:
        description = (
            f"{description}\n\nThis command is asynchronous: it returns a `jobid`. "
            "The documented entity is delivered in the `jobresult` of `queryAsyncJobResult`."
        ).strip()

    operation: Json = {"operationId": command, "summary": first_sentence(api.get("description")) or command}
    if description and description != operation["summary"]:
        operation["description"] = description
    operation["tags"] = [tag]
    operation["parameters"] = parameters
    operation["responses"] = {
        "200": {
            "description": f"Successful invocation of `{command}`.",
            "content": {"application/json": {"schema": {"type": "object", "properties": {key: payload}, "required": [key]}}},
        },
        "default": {
            "description": "CloudStack error. The HTTP status repeats the `errorcode` of the body.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {key: {"$ref": "#/components/schemas/CloudStackError"}},
                        "required": [key],
                    }
                }
            },
        },
    }
    operation["x-cloudstack-command"] = command
    operation["x-cloudstack-async"] = is_async
    if since := api.get("since"):
        operation["x-cloudstack-since"] = since
    if related := related_commands(api.get("related")):
        operation["x-cloudstack-related"] = related
    if is_async:
        operation["x-cloudstack-jobresult-schema"] = registry.ref(signature)["$ref"]
    return operation


def build_document(apis: list[Json], options: argparse.Namespace) -> Json:
    registry = SchemaRegistry()
    signatures = {api["name"]: registry.add(api.get("response"), api["name"], "top") for api in apis}
    schemas = registry.finalize()

    paths: dict[str, Json] = {}
    tags: Counter[str] = Counter()
    tagger = build_tagger([api["name"] for api in apis])
    for api in apis:
        command = api["name"]
        operation = build_operation(api, signatures[command], registry, options.response_keys.get(command), tagger(command))
        operation["parameters"].insert(
            0,
            {
                "name": "command",
                "in": "query",
                "description": "API command to invoke.",
                "required": True,
                # "default" repeats "const" so that documentation browsers and
                # generated clients prefill the value instead of leaving the
                # required parameter empty.
                "schema": {"type": "string", "const": command, "default": command},
            },
        )
        tags[operation["tags"][0]] += 1
        paths[f"/{command}"] = {"get": operation}

    document: Json = {"openapi": OPENAPI_VERSION}
    if options.self_uri:
        document["$self"] = options.self_uri
    document["info"] = {
        "title": options.title,
        "summary": "Apache CloudStack API, generated from listApis.",
        "description": DESCRIPTION_HEADER,
        "license": {"name": "Apache License 2.0", "identifier": "Apache-2.0"},
        "version": options.api_version,
    }
    document["servers"] = [
        {
            "url": options.server_url,
            "name": "cloudstack",
            "description": "CloudStack API endpoint, usually the management server plus `/client/api`.",
        }
    ]
    document["security"] = [{"apiKey": [], "signature": []}, {"sessionKey": []}]
    document["tags"] = [{"name": name, "description": f"{count} command{'' if count == 1 else 's'} acting on {name}."} for name, count in sorted(tags.items())]
    document["paths"] = paths
    document["components"] = {
        "securitySchemes": SECURITY_SCHEMES,
        "parameters": COMMON_PARAMETERS,
        "schemas": {"CloudStackError": ERROR_SCHEMA, "AsyncJobStart": ASYNC_SCHEMA} | {name: schemas[name] for name in sorted(schemas)},
    }
    return document


def fetch_listapis(args: argparse.Namespace) -> tuple[Any, list[Json]]:
    try:
        from cs import CloudStack, read_config
    except ImportError:
        die("the 'cs' library is required to query a live endpoint; install it or use --from-json")

    config = read_config()
    if args.endpoint:
        config["endpoint"] = args.endpoint
    client = CloudStack(**config)
    apis = client.listApis().get("api") or []
    if not apis:
        die("listApis returned no commands")
    return client, apis


def probe_response_keys(client: Any, apis: list[Json]) -> dict[str, tuple[str, bool]]:
    """Resolve the per-command payload key by calling read-only list commands.

    listApis does not expose the key CloudStack nests a payload under, so the
    only way to learn it is to look at a real response. Only `list*` commands
    are probed, with no arguments; commands that error or come back empty are
    left unresolved.
    """
    keys: dict[str, tuple[str, bool]] = {}
    for api in apis:
        command = api["name"]
        if not command.startswith("list") or api["isasync"]:
            continue
        try:
            result = getattr(client, command)()
        except Exception:  # noqa: BLE001 - a failing probe simply teaches us nothing
            continue
        if not isinstance(result, dict):
            continue
        candidates = [key for key in result if key != "count"]
        if len(candidates) == 1:
            # Not every list command returns a collection: listCapabilities
            # nests a single object under "capability".
            key = candidates[0]
            keys[command] = (key, isinstance(result[key], list))
    return keys


def dump(document: Json, stream: TextIO, fmt: str) -> None:
    if fmt == "json":
        json.dump(document, stream, indent=2)
        stream.write("\n")
        return

    try:
        import yaml
    except ImportError:
        die("PyYAML is required for --format yaml; install it or use --format json")

    class Dumper(yaml.SafeDumper):
        """Renders multi-line strings as block scalars so descriptions stay readable."""

    def represent_str(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
        style = "|" if "\n" in data else None
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

    Dumper.add_representer(str, represent_str)
    yaml.dump(document, stream, Dumper=Dumper, default_flow_style=False, sort_keys=False, allow_unicode=True, width=1000000)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"Generate an OpenAPI {OPENAPI_VERSION} document from the CloudStack listApis command.",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--from-api", action="store_true", help="query a live endpoint (default)")
    source.add_argument("--from-json", metavar="FILE", help="read a saved listApis response instead of querying")
    parser.add_argument("--endpoint", help="override the endpoint from the cs configuration")
    parser.add_argument("--dump-listapis", metavar="FILE", help="also write the raw listApis response to FILE")
    parser.add_argument("-o", "--output", metavar="FILE", help="write the document to FILE (default: stdout)")
    parser.add_argument("--format", choices=["yaml", "json"], help="output format (default: from --output, else yaml)")
    parser.add_argument("--server-url", default="https://localhost:8443/client/api", help="server URL to advertise")
    parser.add_argument("--title", default="Apache CloudStack API", help="info.title of the document")
    parser.add_argument("--api-version", help="info.version (default: cloudstackversion of the endpoint, else 'unknown')")
    parser.add_argument("--self", dest="self_uri", metavar="URI", help="set the OpenAPI 3.2 $self field")
    parser.add_argument(
        "--probe-response-keys",
        action="store_true",
        help="call read-only list commands on the endpoint to resolve payload keys exactly (live sources only)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    client = None
    if args.from_json:
        with open(args.from_json) as handle:
            payload = json.load(handle)
        apis = payload.get("api", payload) if isinstance(payload, dict) else payload
        if not apis:
            die(f"{args.from_json} does not contain a listApis response")
    else:
        client, apis = fetch_listapis(args)

    if args.dump_listapis:
        with open(args.dump_listapis, "w") as handle:
            json.dump({"count": len(apis), "api": apis}, handle, indent=2, sort_keys=True)

    if args.probe_response_keys and client is None:
        die("--probe-response-keys needs a live endpoint and cannot be combined with --from-json")

    args.response_keys = probe_response_keys(client, apis) if args.probe_response_keys else {}

    if not args.api_version:
        args.api_version = "unknown"
        if client is not None:
            try:
                args.api_version = client.listCapabilities()["capability"]["cloudstackversion"]
            except Exception:  # noqa: BLE001 - the version is cosmetic
                pass

    document = build_document(sorted(apis, key=lambda api: api["name"]), args)

    fmt = args.format or ("json" if (args.output or "").endswith(".json") else "yaml")

    if args.output:
        with open(args.output, "w") as handle:
            dump(document, handle, fmt)
        sys.stderr.write(
            f"cs_openapi: {len(apis)} commands, {len(document['components']['schemas'])} schemas, "
            f"{len(args.response_keys)} payload keys resolved -> {args.output}\n"
        )
    else:
        dump(document, sys.stdout, fmt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
