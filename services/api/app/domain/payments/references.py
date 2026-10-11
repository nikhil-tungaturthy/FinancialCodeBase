"""Payment reference numbering.

Payment references are allocated from a block per intake channel. The scheme predates the
platform (it mirrors the legacy channel adapters) and is documented as an operational
quirk: the number tells an operator where a payment came from.

    PORTAL  MGB-PAY-1000+   institutional self-service
    API     MGB-PAY-2000+   corporate host-to-host
    FILE    MGB-PAY-5000+   bulk ACH/SEPA files
    BRANCH  MGB-PAY-8000+   retail branch capture
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from app.core.ids import PAYMENT_REF_PREFIX, parse_payment_ref, payment_ref
from app.models.enums import Channel

CHANNEL_REFERENCE_BLOCKS: Final[Mapping[Channel, int]] = {
    Channel.PORTAL: 1000,
    Channel.API: 2000,
    Channel.FILE: 5000,
    Channel.BRANCH: 8000,
}

MAX_REFERENCE_NUMBER: Final = 9999

_BLOCKS_DESCENDING: Final[tuple[tuple[int, Channel], ...]] = tuple(
    sorted(((start, channel) for channel, start in CHANNEL_REFERENCE_BLOCKS.items()), reverse=True)
)


def block_range(channel: Channel) -> tuple[int, int]:
    """Inclusive (first, last) reference numbers available to ``channel``."""
    start = CHANNEL_REFERENCE_BLOCKS[channel]
    later_starts = [s for s in CHANNEL_REFERENCE_BLOCKS.values() if s > start]
    end = (min(later_starts) - 1) if later_starts else MAX_REFERENCE_NUMBER
    return start, end


def block_capacity(channel: Channel) -> int:
    start, end = block_range(channel)
    return end - start + 1


def payment_ref_for(channel: Channel, ordinal: int) -> str:
    """Reference for the ``ordinal``-th (1-based) payment received on ``channel``.

    The 43rd portal payment is ``MGB-PAY-1042``.
    """
    if ordinal < 1:
        raise ValueError("ordinal is 1-based and must be positive")
    start, end = block_range(channel)
    number = start + ordinal - 1
    if number > end:
        raise ValueError(
            f"{channel.value} reference block exhausted: ordinal {ordinal} exceeds capacity "
            f"{end - start + 1}"
        )
    return payment_ref(number)


def channel_for_payment_ref(ref: str) -> Channel:
    """Infer the intake channel from a payment reference's block."""
    number = parse_payment_ref(ref)
    for start, channel in _BLOCKS_DESCENDING:
        if number >= start:
            return channel
    raise ValueError(f"{ref!r} is below the first channel block ({PAYMENT_REF_PREFIX}1000)")


def ordinal_for_payment_ref(ref: str) -> int:
    """Position (1-based) of the payment within its channel block."""
    number = parse_payment_ref(ref)
    channel = channel_for_payment_ref(ref)
    return number - CHANNEL_REFERENCE_BLOCKS[channel] + 1
