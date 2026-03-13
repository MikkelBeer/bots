import os
import discord
import asyncio
from aiohttp import web
from dotenv import load_dotenv
from discord import app_commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = discord.Object(id=int(os.getenv('GUILD_ID')))

class MyBot(discord.Client):
    def __init__(self):
        # Set up intents to allow the bot to read message content and other necessary events
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
        # Initialize the command tree for slash commands
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync the command tree with the specified guild to make the slash commands available
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)

bot = MyBot()

# Commands

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord! (ID: {bot.user.id})')
    print(f'Connected to guild: {GUILD_ID}')
    
@bot.tree.command(name="ping", description="Test command to check if the bot is responsive and gives its ping", guild=GUILD_ID)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f'Hallo! Latency: {round(bot.latency * 1000)}ms')
    
@bot.tree.command(name="serverinfo", description="Geeft info over deze server")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    await interaction.response.send_message(
        f"Servernaam: **{guild.name}**\nAantal leden: **{guild.member_count}**"
    )
    
# 3. GitHub Webhook Ontvanger
async def github_webhook_handler(request):
    data = await request.json()
    
    # Check wat voor event het is (bijv. een 'push')
    if "commits" in data:
        repo_name = data['repository']['name']
        pusher = data['pusher']['name']
        commit_msg = data['head_commit']['message']
        url = data['head_commit']['url']

        # Zoek het kanaal waar het bericht heen moet (vervang ID!)
        channel = bot.get_channel(1482046500778541186) # JOUW CHANNEL ID
        if channel:
            embed = discord.Embed(
                title=f"🚀 Nieuwe Push in {repo_name}",
                description=f"**{pusher}** heeft een commit gepusht:\n`{commit_msg}`",
                url=url,
                color=discord.Color.green()
            )
            await channel.send(embed=embed)

    return web.Response(text="OK")

# 4. Start de Webserver naast de Bot
async def start_webhook_server():
    app = web.Application()
    app.router.add_post('/github', github_webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000) # Luistert op poort 8000
    await site.start()

# Pas je main loop aan:
async def main():
    async with bot:
        await start_webhook_server()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())