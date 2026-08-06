"""Check from the outside that the slot due by now really was served.

The posting job can fail in a way that runs no step at all: on 2026-08-06 the
evening run waited a quarter of an hour for a runner, never got one and was
cancelled in the queue. Nothing ran, so nothing could report it — a
notification step inside that job would have been cancelled along with it.
Hence this second workflow, which only reads the state committed by the
first one and is therefore blind to how the posting run died.

`GRACE` is what separates "late" from "missing". Scheduled runs on GitHub
are routinely delayed; two hours is normal and two and a half were seen on
the day above. Six hours is comfortably past that, and still names the right
slot when the watchdog itself is the delayed one — that is the reason the
due slot is derived by looking back from now rather than from the clock
time the watchdog was meant to run at.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone

from . import alert, telegram
from .config import Config
from .state import State, slot_of

log = logging.getLogger("bot.watchdog")

GRACE = timedelta(hours=6)


def due_slot(now: datetime) -> str:
    """The slot that should have been served by `now`."""
    return slot_of(now - GRACE)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    config = Config.from_env()
    state = State.load(config.state_file)
    slot = due_slot(datetime.now(timezone.utc))

    if state.already_posted(slot):
        log.info("Slot %s has been served — nothing to report.", slot)
        return 0

    last = state.last_post_slot or "never"
    log.error("Slot %s was never posted (last: %s).", slot, last)
    try:
        alert.send(
            config,
            f"No post for slot {slot} — the run never delivered one. "
            f"Last served slot: {last}. Run the workflow by hand to catch up.",
        )
    except telegram.TelegramError as exc:
        log.error("The alert itself could not be delivered: %s", exc)
    # A red run is the backstop: GitHub mails the owner about failed
    # scheduled workflows, which still reaches them if the alert chat is
    # unset or Telegram is the thing that is down.
    return 1


if __name__ == "__main__":
    sys.exit(main())
