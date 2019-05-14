import typing
from dataclasses import asdict, dataclass

import discord

__all__ = [
    'Message',
]

@dataclass
class Message:
    """Helper class for sending multiple things in one message."""
    content: str = None
    file: discord.File = None
    files: typing.List[discord.File] = None
    embed: discord.Embed = None

    @staticmethod
    def to_args(message):
        """Converts into arguments that can be used in functions such
        as discord.abc.Messageable.send and discord.Message.edit
        """

        if hasattr(message, 'to_dict'):
            return dict(embed=message)
        if isinstance(message, Message):
            return asdict(message)
        return dict(content=message)
