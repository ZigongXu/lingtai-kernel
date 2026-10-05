"""Declared, normally closed ``channel_reply`` official tool family.

The family accepts only a Core ``ChannelReplySubmitPort`` plus the read-only
workdir port used by its packaged manual.  It never receives an Agent, channel
adapter, destination, account, chat, credential, or mount capability.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from lingtai.kernel.channel_reply import (
    ChannelReplySubmitRequest,
    make_fail_closed_receipt,
)
from lingtai.kernel.tool_plugin import BoundToolPlugin, ToolPluginDeclaration
from lingtai.tools.tool_family import ChildTool, ToolFamily
from lingtai.tools.tool_family.manual import MANUAL_INPUT_SCHEMA, build_manual_child

from .schema import ACTION_ENUM_DESCRIPTION, SUBMIT_INPUT_SCHEMA, get_description

if TYPE_CHECKING:
    from lingtai.kernel.channel_reply import ChannelReplySubmitPort
    from lingtai.kernel.tool_plugin import ToolPluginHost

PROVIDERS = {"providers": [], "default": "builtin"}


def _submit(
    port: "ChannelReplySubmitPort",
    action_input: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        request = ChannelReplySubmitRequest.from_mapping(action_input)
    except ValueError as exc:
        return make_fail_closed_receipt(action_input, str(exc))
    return port.submit_channel_reply(request).to_public_dict()


def _build_family(host: "ToolPluginHost | None") -> ToolFamily:
    if host is None:
        def _unused(_input: Mapping[str, Any]) -> dict[str, Any]:
            raise AssertionError("schema-only channel_reply family never dispatches")

        submit_handler = _unused
        manual_child = ChildTool(
            "manual",
            DECLARATION.manual_input_schema,
            _unused,
            title="manual input",
        )
    else:
        submit_port = host.channel_reply_submit
        submit_handler = lambda action_input: _submit(submit_port, action_input)
        manual_child = build_manual_child(host.workdir, DECLARATION.manual)

    return ToolFamily(
        DECLARATION.name,
        [
            ChildTool(
                "submit",
                DECLARATION.input_schemas["submit"],
                submit_handler,
                title="submit input",
            ),
            manual_child,
        ],
    )


def get_schema(lang: str = "en") -> dict[str, Any]:
    schema = _FAMILY.build_schema()
    schema["properties"]["action"]["description"] = ACTION_ENUM_DESCRIPTION
    return schema


def _bind(host: "ToolPluginHost") -> BoundToolPlugin:
    family = _build_family(host)

    def handle_channel_reply(args: dict[str, Any]) -> dict[str, Any]:
        raw = dict(args or {})
        raw.pop("_tc_id", None)
        return family.handle(raw)

    return BoundToolPlugin(
        name=DECLARATION.name,
        schema=get_schema(),
        handler=handle_channel_reply,
        description=get_description(),
        glossary_package=__package__,
    )


DECLARATION = ToolPluginDeclaration(
    name="channel_reply",
    actions=("submit",),
    input_schemas={"submit": SUBMIT_INPUT_SCHEMA},
    manual_input_schema=MANUAL_INPUT_SCHEMA,
    manual="channel_reply",
    description=get_description(),
    binder=_bind,
    requires=("workdir", "channel_reply_submit"),
    glossary_package=__package__,
)

# Compatibility views are declaration-derived, never a second action inventory.
ACTION_ORDER = DECLARATION.public_actions
INPUT_SCHEMAS = DECLARATION.public_input_schemas()
_FAMILY = _build_family(None)


def setup(agent, **_ignored) -> None:
    """Mount through the kernel official-plugin registrar."""
    from lingtai.adapters.tool_plugin_host import register_agent_tool_plugins

    register_agent_tool_plugins(agent, [DECLARATION])
