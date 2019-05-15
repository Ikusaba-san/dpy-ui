# discord.py UI

An extension package for anything relating to user input and interactions.

Ever wanted to make a prompt for your users? Maybe a cool paginator? `dpy-ui`
will make it all happen in simple, easy to remember functions and classes.

## Installation

**Requires Python 3.6+**

```
pip install -U dpy-ui
```

### Development version

```
pip install -U git+https://github.com/Ikusaba-san/discord.py-ui.git
```
or
```
git clone git+https://github.com/Ikusaba-san/discord.py-ui.git
cd discord.py-ui
pip install -U .[voice]
```

Then once it's installed, you can import it via
```py
from discord.ext import ui
```

## Quick Examples

### Prompt the user for some input
```py
name = await ui.prompt(ctx, 'What is your name?')
await ctx.send(f'Ok, your name is {name}')
```

### Choose between a list of choices
```py
choices = ['red', 'blue', 'green', 'yellow']
colour = await ui.select(ctx, 'What is your favo(u)rite colo(u)r?', choices)

# Want buttons instead of text? No problem.

choices = [
    ui.Choice('Very Happy', button='😄'),
    ui.Choice('Happy', button='🙂'),
    ui.Choice('Neutral', button='😐'),
    ui.Choice('Sad', button='😦'),
    ui.Choice('Very Sad', button='😢'),
]
feeling = await ui.select(ctx, 'How are you feeling today?', choices)
```

### Make a simple paginator
```py
def some_statements():
    for i in range(20):
        yield f'This is sentence {i}'

def format_page(page):
    return f'This is a page\n{page}'

paginator = ui.Paginator(some_statements(), page_formatter=format_page)
await paginator.start(ctx)

# And to chunk it:

def format_chunk(chunk):
    # Formatters can return embeds too
    return discord.Embed(description='\n'.join(chunk))

paginator = ui.Paginator.chunked(some_statements(), 10, page_formatter=format_chunk)
await paginator.start(ctx)
```

### Make a custom session
```py
class MySession(ui.Session):
    async def send_initial_message(self):
        return await self.context.send('Say hi or click the thinking face.')

    @ui.button('🤔')
    async def think(self, payload):
        await self.context.send('Thinking a lot...')

    @ui.button('⏹')
    async def quit(self, payload):
        await self.stop()
    
    @ui.command('hello|hi')
    async def say_hello(self, message):
        await self.context.send(f'Hello, {message.author.mention}!')

session = MySession(timeout=120)
await session.start(ctx)
```

