"""Telegram owner adapter for the channel_reply Core Port."""
from __future__ import annotations

from pathlib import Path
import stat
import threading
from typing import Any, Callable

from lingtai.adapters.channel_reply_state_lock import select_channel_reply_state_lock
from lingtai.kernel.channel_reply import (
    ChannelReplyFileStore,
    ChannelReplyOwnerFileTransport,
    OwnerChannelReplyController,
    OwnerReplyGrant,
    PreSendChannelReplyError,
)
from lingtai.kernel.channel_reply._mutation_lock import ChannelReplyExpectedRootMismatch


class TelegramChannelReplyAdapter(OwnerChannelReplyController):
    """Owner-bound Telegram adapter.

    The target supplies only a Core `ChannelReplySubmitRequest`. Account alias,
    chat id, and reply anchor are read from `OwnerReplyGrant.anchor`.
    """

    def __init__(
        self,
        *,
        state_root: str | Path,
        service,
        target_agent_id: str,
        now=None,
        target_agent_name: str | None = None,
        validate_target_eligibility: Callable[[], bool] | None = None,
    ) -> None:
        self._service = service
        self._validate_target_eligibility = validate_target_eligibility
        # Drain and retention share one Core transport per exact adapter/target
        # pin. The adapter itself belongs to one immutable eligible-target pin,
        # so this cache cannot cross identity replacement. Root disappearance or
        # a positive Core root-identity mismatch evicts it for a later cycle.
        self._target_transport_lock = threading.RLock()
        self._target_transports: dict[Path, ChannelReplyOwnerFileTransport] = {}
        # Retain the historical test/debug seam while making it the same cache.
        self._target_cleanup_transports = self._target_transports
        super().__init__(
            store=ChannelReplyFileStore(
                Path(state_root),
                mutation_lock=select_channel_reply_state_lock(),
            ),
            target_agent_id=target_agent_id,
            target_agent_name=target_agent_name,
            validate_pre_send=self._validate_plain_text_reply,
            send_plain_text_reply=self._send_plain_text_reply,
            now=now,
        )

    @staticmethod
    def _canonical_target_path(target_workdir: str | Path) -> Path:
        """Return one exact cache key without following a caller-supplied symlink."""
        target_path = Path(target_workdir).expanduser()
        info = target_path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("working_directory_invalid")
        return target_path.resolve(strict=True)

    def target_file_transport(
        self,
        target_workdir: str | Path,
        *,
        recover_on_init: bool = True,
    ) -> ChannelReplyOwnerFileTransport:
        """Return the one Core transport pinned to this adapter and target path."""
        target_path = self._canonical_target_path(target_workdir)
        with self._target_transport_lock:
            transport = self._target_transports.get(target_path)
            if transport is None:
                transport = ChannelReplyOwnerFileTransport(
                    target_path,
                    submit_port=self,
                    mutation_lock=select_channel_reply_state_lock(),
                    now=self._now,
                    recover_on_init=recover_on_init,
                )
                self._target_transports[target_path] = transport
            return transport

    def drain_target_outbox(
        self,
        target_workdir: str | Path,
        *,
        max_items: int = 100,
    ):
        """Drain an initialized target outbox without creating target state.

        A newly eligible target has no ``.channel_reply`` tree until it submits
        its first reply. That whole-root absence is ordinary no-work. Once the
        root exists, Core remains the sole validator: a symlink, wrong type,
        partial tree, wrong mode, or wrong owner must still fail closed.
        """
        target_path = self._canonical_target_path(target_workdir)
        reply_root = target_path / ".channel_reply"
        if self._reply_root_is_absent(reply_root):
            self._evict_target_transport(target_path)
            return []
        try:
            return self.target_file_transport(
                target_path,
                recover_on_init=False,
            ).drain(max_items=max_items)
        except ChannelReplyExpectedRootMismatch:
            # The failed cycle positively rejected the replacement and never
            # constructs or trusts it. A later cycle may compose a fresh pin.
            self._evict_target_transport(target_path)
            raise
        except FileNotFoundError:
            # Suppress only complete-root absence; a missing required child under
            # a still-existing root remains strict malformed-state failure.
            if self._reply_root_is_absent(reply_root):
                self._evict_target_transport(target_path)
                return []
            raise

    def cleanup_target_state(
        self,
        target_workdir: str | Path,
        *,
        now: str,
        retention_seconds: int,
        max_records: int | None = None,
    ) -> int:
        """Run Core target retention without creating an absent target root."""
        target_path = self._canonical_target_path(target_workdir)
        reply_root = target_path / ".channel_reply"
        if self._reply_root_is_absent(reply_root):
            self._evict_target_transport(target_path)
            return 0
        try:
            transport = self.target_file_transport(
                target_path,
                recover_on_init=max_records is None,
            )
            return transport.cleanup_retained(
                now=now,
                retention_seconds=retention_seconds,
                max_records=max_records,
            )
        except ChannelReplyExpectedRootMismatch:
            # Evict only after the pinned transport positively rejected the named
            # root. This cycle never opens or trusts the replacement.
            self._evict_target_transport(target_path)
            raise
        except FileNotFoundError:
            if self._reply_root_is_absent(reply_root):
                self._evict_target_transport(target_path)
                return 0
            raise

    def _evict_target_transport(self, target_path: Path) -> None:
        with self._target_transport_lock:
            self._target_transports.pop(target_path, None)

    @staticmethod
    def _reply_root_is_absent(reply_root: Path) -> bool:
        try:
            reply_root.lstat()
        except FileNotFoundError:
            return True
        return False

    def _validate_plain_text_reply(self, grant: OwnerReplyGrant, _text: str) -> None:
        """Reject malformed authority or an obsolete target before sending."""
        if grant.channel != "telegram":
            raise PreSendChannelReplyError("unsupported_channel")
        anchor = dict(grant.anchor)
        if set(anchor) != {"account_alias", "chat_id", "reply_to_message_id"}:
            raise PreSendChannelReplyError("bad_anchor")
        account_alias = anchor.get("account_alias")
        chat_id = anchor.get("chat_id")
        reply_to_message_id = anchor.get("reply_to_message_id")
        if (
            not isinstance(account_alias, str)
            or not account_alias
            or account_alias != account_alias.strip()
        ):
            raise PreSendChannelReplyError("bad_anchor")
        # Simple V1 accepts only private user chats. Telegram private chat ids are
        # positive integers; group/supergroup/channel ids occupy the negative
        # domain. Booleans are not identifiers despite being int subclasses.
        if isinstance(chat_id, bool) or not isinstance(chat_id, int) or chat_id <= 0:
            raise PreSendChannelReplyError("bad_anchor")
        if (
            isinstance(reply_to_message_id, bool)
            or not isinstance(reply_to_message_id, int)
            or reply_to_message_id <= 0
        ):
            raise PreSendChannelReplyError("bad_anchor")
        if self._validate_target_eligibility is not None:
            try:
                eligible = self._validate_target_eligibility()
            except Exception:
                eligible = False
            if eligible is not True:
                raise PreSendChannelReplyError("target_ineligible")

    def _send_plain_text_reply(self, grant: OwnerReplyGrant, text: str) -> str:
        # Repeat the pure check defensively at the concrete account boundary.
        self._validate_plain_text_reply(grant, text)
        anchor = dict(grant.anchor)
        account_alias = str(anchor["account_alias"])
        chat_id = int(anchor["chat_id"])
        reply_to_message_id = int(anchor["reply_to_message_id"])
        account = self._service.get_account(account_alias)
        result: dict[str, Any] = account.send_message(
            chat_id,
            f"[{grant.target_agent_name}] {text}",
            reply_to_message_id=reply_to_message_id,
        )
        message_id = result.get("message_id")
        if not isinstance(message_id, int) or isinstance(message_id, bool):
            raise RuntimeError("bad_send_result")
        return f"owner-private-telegram-message:{message_id}"
