from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, AbstractSet, Callable

from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET, Logger

from shyft.logger import get_logger

logger = get_logger(__name__)

@dataclass(frozen=True)
class Message:
    """A single message to be displayed."""

    text: str
    severity: int = INFO
    views: Optional[AbstractSet[str]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class MessageBus:
    """A class for sending and retrieving different messages for
    display to the user.
    """

    def __init__(self):
        self._messages = []

    def add_message(self, text: str, severity: int = INFO, views: Optional[AbstractSet[str]] = None,
                    timestamp: Optional[datetime] = None, logger_: Optional[Logger] = None) -> Message:
        logger.debug(f'Adding message: {text}')
        if timestamp is None:
            timestamp = datetime.utcnow()
        msg = Message(
            text=text,
            severity=severity,
            views=views,
            timestamp=timestamp
        )
        self._messages.append(msg)
        if logger_ is not None:
            logger_.log(severity, text)
        return msg

    def _get_predicate(self,
                       severity: int,
                       view: Optional[str],
                       exact_severity: bool = False) -> Callable[[Message], bool]:
        def predicate(msg: Message):
            if exact_severity:
                if msg.severity == severity:
                    severity_match = True
                else:
                    severity_match = False
            else:
                if msg.severity >= severity:
                    severity_match = True
                else:
                    severity_match = False
            view_match = (view is None) or (msg.views is None) or (view in msg.views)
            return severity_match and view_match
        return predicate

    def get_messages(self, severity: int = INFO,
                     view: Optional[str] = None, exact_severity: bool = False,
                     discard: bool = True, discard_less_severe: bool = True):
        #print('getting messages.')
        #print(f'all messages: {self._messages}')
        show_predicate = self._get_predicate(severity, view, exact_severity)
        to_show = list(filter(show_predicate, self._messages))
        logger.debug(f'Fetched {len(to_show)} messages.')
        #print(f'showing: f{to_show}')
        if discard:
            if discard_less_severe:
                keep_predicate = self._get_predicate(NOTSET, view, False)
            else:
                keep_predicate = show_predicate
            self._messages = list(filter(lambda m: not keep_predicate(m), self._messages))
        return to_show

    def copy(self) -> MessageBus:
        copy = MessageBus()
        copy._messages = self._messages[:]
        return copy