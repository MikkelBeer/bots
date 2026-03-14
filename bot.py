import os
import discord
import asyncio
from aiohttp import web
from dotenv import load_dotenv
from discord import app_commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = discord.Object(id=int(os.getenv('GUILD_ID')))
CHANNEL_ID = discord.Object(id=int(os.getenv('CHANNEL_ID')))

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
    try:
        data = await request.json()

        # Check of het een 'push' event is
        if "commits" in data:
            repo_name = data['repository']['full_name']
            pusher = data['pusher']['name']
            commits = data['commits']

            # Pak het kanaal (vervang door jouw ID uit .env of direct)
            # Gebruik de CHANNEL_ID die je bovenaan je script al hebt gedefinieerd
            # We halen het ID op uit de discord.Object die je eerder hebt gemaakt
            target_channel_id = CHANNEL_ID.id 
            channel = bot.get_channel(target_channel_id)

            # Als get_channel faalt (niet in cache), proberen we het direct te fetchen
            if channel is None:
                try:
                    channel = await bot.fetch_channel(target_channel_id)
                except Exception as fetch_error:
                    print(f"Kon kanaal niet vinden: {fetch_error}")

            if channel:
                embed = discord.Embed(
                    title=f"🛠️ Nieuwe Push in {repo_name}",
                    url=data['repository']['html_url'],
                    color=discord.Color.blue()
                )

                commit_list = ""
                for commit in commits[:3]:
                    commit_list += f"[`{commit['id'][:7]}`]({commit['url']}) {commit['message']}\n"

                embed.add_field(name="Commits", value=commit_list or "Geen details", inline=False)
                embed.set_footer(text=f"Gepusht door {pusher}")

                await channel.send(embed=embed)
            else:
                print(f"Fout: Kanaal met ID {target_channel_id} niet gevonden.")
        return web.Response(text="OK", status=200)
    except Exception as e:
        print(f"Error in webhook: {e}")
        return web.Response(text="Error", status=500)
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
