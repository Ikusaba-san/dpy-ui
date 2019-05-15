from itertools import islice

import discord

from .message import Message
from .session import button, Session


__all__ = [
    'InvalidPage',
    'Paginator',
    'PageSource',
]

class InvalidPage(Exception):
    """Exception raised in PageSources to indicate if an index is invalid"""


PREVIOUS_EMOJI = '\N{BLACK LEFT-POINTING TRIANGLE}'
NEXT_EMOJI = '\N{BLACK RIGHT-POINTING TRIANGLE}'

class PageSource:
    """Base class for any sources of "pages" in the Paginator"""

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

    async def get_page(self, index):
        """Returns a page with a given index.

        If an index is invalid, raise InvalidPage.

        Subclasses must override this.
        """
        raise NotImplementedError

# ----- Sources -----

class IterableSource(PageSource):
    def __init__(self, iterable):
        self._it = iter(iterable)
        self._cache = []

    async def get_page(self, index):
        if index < 0:
            raise InvalidPage

        cache_len = len(self._cache)
        if index >= cache_len:
            self._cache.extend(islice(self._it, index + 1 - cache_len))

        try:
            return self._cache[index]
        except IndexError:
            raise InvalidPage

class AsyncIterableSource(PageSource):
    def __init__(self, aiterable):
        self._it = aiterable.__aiter__()
        self._cache = []

    async def get_page(self, index):
        if index < 0:
            raise InvalidPage

        cache_len = len(self._cache)
        if index >= cache_len:
            # islice can't be used here because this is an async iterable
            self._cache.extend(await atake(self._it, index + 1 - cache_len))

        try:
            return self._cache[index]
        except IndexError:
            raise InvalidPage

# ------ Chunking (for Paginator.chunked) -----

def chunked(iterable, n):
    it = iter(iterable)
    return iter(lambda: tuple(islice(it, n)), ())

async def atake(aiterable, n):
    i = 0
    a = []
    async for elem in aiterable:
        a.append(elem)
        i += 1
        if i >= n:
            break
    return a

async def achunked(aiterable, n):
    while True:
        chunk = await atake(aiterable, n)
        if not chunk:
            break
        yield tuple(chunk)

class Paginator(Session):
    """Paginates an iterable of entries with a formatting callback

    Parameters
    ----------
    source: Union[Iterable, AsyncIterable, PageSource]
        A source to get the pages from.
    page_formatter: Optional[Callable[[Any], Any]]
        A callback that takes one argument, a "page" returned from the source,
        and formats it into a message that will be sent to the user.
    per_page: Optional[int]
        The number of entries per "page", useful for chunking long iterables
        and displaying them in lists.
    kwargs:
        Any other arguments to pass into Session.
    """

    def __init__(self, source, page_formatter=None, **kwargs):
        super().__init__(**kwargs)

        if hasattr(source, '__aiter__'):
            self.pages = AsyncIterableSource(source)
        elif hasattr(source, '__iter__'):
            self.pages = IterableSource(source)
        elif not hasattr(source, 'get_page'):
            raise TypeError(
                'source must be an async-iterable, an iterable, or a PageSource, '
                f'not {source.__class__.__name__!r}'
            )

        if page_formatter is not None:
            self.format_page = page_formatter

        self._index = 0

    @classmethod
    def chunked(cls, iterable, n, *args, **kwargs):
        """Return a paginator chunked in groups of n

        This is useful for the most common usecase: paginating a long
        list in groups of n per page.

        Parameters
        ----------
        iterable: Union[Iterable, AsyncIterable]
            The iterable (or async-iterable) to chunk into the paginator.
        n: int
            Number of elements per page.
        args, kwargs
            Extra arguments that go into the Paginator
        """

        if hasattr(iterable, '__aiter__'):
            it = achunked(iterable, n)
        elif hasattr(iterable, '__iter__'):
            it = chunked(iterable, n)
        else:
            raise TypeError(f'{iterable!r} is not an iterable or an async-iterable')

        return cls(it, *args, **kwargs)

    async def get_page(self, index):
        page = await self.pages.get_page(index)
        return self.format_page(page)

    async def send_initial_message(self):
        page = await self.get_page(0)
        return await self.context.send(**Message.to_args(page))

    async def update_message(self, index):
        try:
            page = await self.get_page(index)
        except InvalidPage:
            return

        self._index = index
        await self.message.edit(**Message.to_args(page))

    def format_page(self, page):
        description = '\n'.join(map(str, page))
        return discord.Embed(description=description)  \
               .set_footer(text=f'Page {self._index}')

    @button(PREVIOUS_EMOJI)
    async def previous(self, payload):
        await self.update_message(self._index - 1)

    @button('\N{BLACK SQUARE FOR STOP}')
    async def quit(self, payload):
        await self.stop()

    @button(NEXT_EMOJI)
    async def next(self, payload):
        await self.update_message(self._index + 1)

    async def start(self, ctx):
        # Check if there are at least two pages
        try:
            await self.pages.get_page(1)
        except InvalidPage:
            # Single page
            buttons = self.__ui_buttons__ = self.__ui_buttons__.copy()
            del buttons[PREVIOUS_EMOJI]
            del buttons[NEXT_EMOJI]

        await super().start(ctx)
