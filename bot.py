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
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)

bot = MyBot()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

# --- Webhook Handler ---

async def github_webhook_handler(request):
    try:
        data = await request.json()
        event_type = request.headers.get('X-GitHub-Event')
        target_channel_id = CHANNEL_ID.id 
        channel = bot.get_channel(target_channel_id) or await bot.fetch_channel(target_channel_id)

        if not channel:
            return web.Response(text="Channel not found", status=404)

        # 1. Push Events (Bestaande code)
        if event_type == "push":
            repo_name = data['repository']['full_name']
            pusher = data['pusher']['name']
            commits = data['commits']
            embed = discord.Embed(
                title=f"🛠️ Nieuwe Push in {repo_name}",
                url=data['repository']['html_url'],
                color=discord.Color.blue()
            )
            commit_list = "".join([f"[`{c['id'][:7]}`]({c['url']}) {c['message']}\n" for c in commits[:3]])
            embed.add_field(name="Commits", value=commit_list or "Geen details", inline=False)
            embed.set_footer(text=f"Gepusht door {pusher}")
            await channel.send(embed=embed)

        # 2. Project V2 Events (Uitgebreid)
        elif event_type == "projects_v2_item":
            action = data.get("action")
            user = data.get("sender", {}).get("login", "Onbekend")
            
            # Haal de naam van het item op (meestal een Issue of Draft Issue titel)
            # GitHub Projects v2 slaat dit op in 'content_node_id' of we halen het uit de 'changes'
            item_type = data.get("projects_v2_item", {}).get("content_type")
            
            # De embed voorbereiden
            embed = discord.Embed(color=discord.Color.green())
            
            if action == "created":
                embed.title = "🆕 Nieuw Item toegevoegd"
                embed.description = f"**{user}** heeft een nieuw item aangemaakt op het bord."
                embed.color = discord.Color.green()
                
            elif action == "edited":
                embed.title = "🚚 Project Item Verplaatst"
                embed.color = discord.Color.gold()
                
                # Probeer kolomwijzigingen te vinden
                changes = data.get("changes", {})
                if "field_value" in changes:
                    field_name = changes["field_value"].get("field_name")
                    if field_name == "Status":
                        from_col = changes["field_value"].get("from", {}).get("name", "Onbekend")
                        to_col = changes["field_value"].get("to", {}).get("name", "Onbekend")
                        embed.description = f"**{user}** verplaatste een item\n**Van:** `{from_col}`\n**Naar:** `{to_col}`"
                    else:
                        embed.description = f"**{user}** heeft het veld `{field_name}` aangepast."
                else:
                    embed.description = f"**{user}** heeft een item op het bord bijgewerkt!"
            
            else:
                return web.Response(text="Action ignored", status=200)

            embed.set_footer(text="GitHub Projects v2 Update")
            await channel.send(embed=embed)

        return web.Response(text="OK", status=200)

    except Exception as e:
        print(f"Error in webhook: {e}")
        return web.Response(text="Error", status=500)

# --- Server & Main ---

async def start_webhook_server():
    app = web.Application()
    app.router.add_post('/github', github_webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()

async def main():
    async with bot:
        await start_webhook_server()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
