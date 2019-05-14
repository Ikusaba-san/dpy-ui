import re
import typing
from dataclasses import dataclass

import discord

from .message import Message
from .session import Session

__all__ = [
    'prompt',
    'select',
    'confirm',

    # Internal selection helpers
    'Choice',
    'Selector'
]

# ----- Message helpers -----

async def _send_prompt(ctx, prompt):
    return await ctx.send(**Message.to_args(prompt))

# ----- Prompt ----

async def prompt(ctx, prompt):
    """Prompts a user for input.

    Parameters
    ----------
    prompt: Union[str, discord.Embed, Message]
        The message to show along with the prompt.
    """
    await _send_prompt(ctx, prompt)

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    while True:
        message = await ctx.bot.wait_for('message', check=check)
        return message.content

# ------ Select -----

@dataclass
class Choice:
    value: typing.Any
    button: str = None
    pattern: str = None
    label: str = None

    def __post_init__(self):
        if self.label is None:
            self.label = str(self.value)

    def __str__(self):
        if self.button:
            return f'{self.button} = {self.label}'

        return f'{self.label}'

# TODO: Paginated select.

class Selector(Session):
    def __init__(self, prompt, choices, reactions, **kwargs):
        super().__init__(**kwargs)
        self._result = None

        self.prompt = prompt
        self.choices = list(choices)
        self._use_reactions = reactions

    def format_choices(self):
        if self._use_reactions:
            return '\n'.join(f'{choice.button} = {choice.label}' for choice in self.choices)
        return '\n'.join(f'{i} = {choice.label}' for i, choice in enumerate(self.choices, 1))

    def format_prompt(self, prompt):
        choices = self.format_choices()

        if not isinstance(prompt, Message):
            fields = Message(**Message.to_args(prompt))

        if fields.embed is not None:
            description = fields.embed.description or ''
            fields.embed.description = f'{description}\n{choices}'
        else:
            fields.content = f'{fields.content}\n{choices}'

        return fields

    async def send_initial_message(self):
        return await _send_prompt(self.context, self.format_prompt(self.prompt))

    # ----- Callbacks -----

    async def _on_button_press(self, payload):
        choice = discord.utils.get(self.choices, button=str(payload.emoji))
        self._result = choice.value
        await self.stop()

    async def _on_number_input(self, message, number):
        index = int(number)
        if not 0 < index <= len(self.choices):
            await self.context.send(
                f'{number} is out of range. Please enter a number'
                f'between 1 and {len(self.choices)}'
            )
            return

        choice = self.choices[index - 1]
        self._result = choice.value
        await self.stop()

    async def _on_text_input(self, message, input_):
        matches = []
        for choice in self.choices:
            if not choice.pattern:
                continue

            if not re.match(choice.pattern, input_):
                continue

            matches.append(choice.value)

        if not matches:
            # It's a tough call here because sometimes the user wants to send
            # messages while choosing (for some reason), and we don't want
            # the bot to bark at the user in that instance.
            return

        # TODO: Accept multiple
        if len(matches) > 1:
            await self.context.send(
                f'{input_} is ambiguous (results in {len(matches)} matches).'
                'Please refine your input.'
            )
            return

        self._result = matches[0]
        await self.stop()

    # ----- Main -----

    async def start(self, ctx):
        if self._use_reactions is None:
            self._use_reactions = ctx.channel.permissions_for(ctx.me).add_reactions

        if self._use_reactions:
            buttons = self.__ui_buttons__ = self.__ui_buttons__.copy()
            for choice in self.choices:
                if choice.button:
                    buttons[choice.button] = self._on_button_press
        else:
            commands = self.__ui_commands__ = self.__ui_commands__.copy()
            commands['([0-9]+)'] = self._on_number_input
            commands['(.*)'] = self._on_text_input

        await super().start(ctx)

    async def select(self, ctx):
        await self.start(ctx)
        return self._result

async def select(ctx, prompt, choices, selector_cls=None, reactions=None, **options):
    """Prompts a user to choose between a list of choices.

    Parameters
    ----------
    prompt: Union[str, discord.Embed, Message]
        The message to show along with the prompt.
    choices: Iterable[typing.Any]
        An iterable of choices. To add button functionalities or special text
        input, wrap them in a Choice object.
    selector_cls:
        The class to create the underlying selector. Defaults to Selector.
    reactions: Optional[bool]
        A tribool indicating if it must use reactions.

        If True, reactions are forced and if it can't add reactions, it
        will error.
        If False, text input is forced.
        If None, whether reactions or text input will be used will depend
        on the permissions in the channel in question.
    options:
        Any options that will be passed to the underlying selector class
    """
    if selector_cls is None:
        selector_cls = Selector

    choices = (obj if isinstance(obj, Choice) else Choice(obj) for obj in choices)

    selector = selector_cls(prompt, choices, reactions=reactions, **options)
    return await selector.select(ctx)

# ----- Confirm -----

class Confirmation(Selector):
    def format_choices(self):
        if self._use_reactions:
            return ' | '.join(f'{choice.button} = {choice.label}' for choice in self.choices)
        return f'(yes/no)'

    async def _on_number_input(self, *args):
        # Ban number input because it doesn't make sense here.
        pass

async def confirm(ctx, prompt, emojis=None, user=None, **options):
    r"""Prompts a user for confirmation (yes/no)

    .. note::
    Unlike select, whether it uses buttons or text depends on the permissions
    on the current channel. This cannot be changed.

    Parameters
    ----------
    prompt: Union[str, discord.Embed, Message]
        The message to show along with the prompt.
    emojis: List[str]
        A list of emojis to represent [yes/no]. Defaults to
        ['\N{WHITE HEAVY CHECK MARK}', '\N{CROSS MARK}']
    user: Optional[discord.abc.User]
        The user who should respond to the prompt. defaults to the author
        of the Context's message.
    options:
        Any options that will be passed to the underlying selector class
    """

    if emojis is None:
        emojis = ['\N{WHITE HEAVY CHECK MARK}', '\N{CROSS MARK}']

    if user is None:
        user = ctx.author

    # Not efficient in any way, but it's short :^)
    choices = list(map(Choice, [True, False], emojis, ['y(?:es)?', 'no?'], ['Yes', 'No']))

    selector = Confirmation(prompt, choices, allowed_users={user.id}, reactions=None, **options)
    return await selector.select(ctx)
