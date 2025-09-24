import os
import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta

from myserver import server_on

# --- 1. การตั้งค่าพื้นฐาน ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents) 

# --- 2. การตั้งค่าระบบเกม ---
PVP_DATA_FILE = "pvp_data.json"
CONFIG_FILE = "config.json"

GAME_SETTINGS = {
    "fight_cooldown_seconds": 300,  # 5 นาที
    "points_on_win": 50,
    "points_on_loss": 10,
    "upgrade_cost_multiplier": 1.5,
    "professions": {
        "swordsman": {
            "display_name": "นักดาบ ⚔️",
            "base_stats": {"hp": 120, "atk": 10, "def": 8}
        },
        "mage": {
            "display_name": "นักเวท 🧙",
            "base_stats": {"hp": 80, "atk": 15, "def": 5}
        }
    }
}

# --- 3. ฟังก์ชันจัดการข้อมูล ---
def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def generate_showcase_embeds():
    embeds = []
    for prof_key, prof_data in GAME_SETTINGS["professions"].items():
        embed = discord.Embed(
            title=prof_data["display_name"],
            description=f"เส้นทางการเติบโตของอาชีพ {prof_data['display_name']}",
            color=discord.Color.random()
        )
        base_stats = prof_data["base_stats"]
        embed.add_field(
            name="ค่าสถานะเริ่มต้น",
            value=f"❤️ HP: {base_stats['hp']} | ⚔️ ATK: {base_stats['atk']} | 🛡️ DEF: {base_stats['def']}",
            inline=False
        )
        embed.add_field(
            name="แนวทางการเล่น",
            value=f"ใช้พอยต์ที่ได้จากการต่อสู้มาอัปเกรดค่าสถานะต่างๆ ผ่านคำสั่ง `!upgrade`",
            inline=False
        )
        embeds.append(embed)
    return embeds

# --- 4. Event ของบอท ---
@bot.event
async def on_ready():
    print(f'{bot.user} ออนไลน์พร้อมระบบต่อสู้แล้ว! (Prefix: !)')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

# --- 5. คำสั่งหลักของระบบอาชีพ ---

@bot.command(name="choose", help="เลือกอาชีพของคุณ (เลือกได้ครั้งเดียว!) | ใช้งาน: !choose <swordsman/mage>")
async def choose(ctx, profession: str):
    user_id = str(ctx.author.id)
    data = load_data(PVP_DATA_FILE)
    
    profession = profession.lower()

    if user_id in data and "profession" in data[user_id]:
        await ctx.send("❌ คุณได้เลือกอาชีพไปแล้ว ไม่สามารถเปลี่ยนได้!")
        return

    if profession not in GAME_SETTINGS["professions"]:
        await ctx.send("❌ ไม่มีอาชีพนี้! กรุณาเลือก 'swordsman' หรือ 'mage'")
        return
        
    base_stats = GAME_SETTINGS["professions"][profession]["base_stats"]
    data[user_id] = {
        "profession": profession, "points": 100,
        "hp": base_stats["hp"], "atk": base_stats["atk"], "def": base_stats["def"],
        "last_fight_time": "2000-01-01T00:00:00.000000"
    }
    save_data(data, PVP_DATA_FILE)
    
    prof_display_name = GAME_SETTINGS["professions"][profession]["display_name"]
    await ctx.send(f"🎉 ยินดีด้วย {ctx.author.mention}! คุณได้เริ่มต้นเส้นทางแห่ง **{prof_display_name}** แล้ว!")

@bot.command(name="profile", help="ดูข้อมูลและค่าสถานะของคุณ | ใช้งาน: !profile [@mention]")
async def profile(ctx, member: discord.Member = None):
    target_user = member or ctx.author
    user_id = str(target_user.id)
    data = load_data(PVP_DATA_FILE)

    if user_id not in data or "profession" not in data[user_id]:
        await ctx.send(f"{target_user.display_name} ยังไม่มีอาชีพ! ใช้ `!choose` เพื่อเลือกก่อน")
        return
        
    user_data = data[user_id]
    prof = user_data["profession"]
    
    embed = discord.Embed(title=f"Profile ของ {target_user.display_name}", color=discord.Color.dark_gold())
    embed.set_thumbnail(url=target_user.display_avatar.url)
    embed.add_field(name="อาชีพ", value=GAME_SETTINGS["professions"][prof]["display_name"], inline=False)
    embed.add_field(name="💰 Points", value=f"**{user_data['points']}**", inline=True)
    embed.add_field(name="❤️ HP", value=f"**{user_data['hp']}**", inline=True)
    embed.add_field(name="⚔️ ATK", value=f"**{user_data['atk']}**", inline=True)
    embed.add_field(name="🛡️ DEF", value=f"**{user_data['def']}**", inline=True)
        
    await ctx.send(embed=embed)

@bot.command(name="upgrade", help="ใช้พอยต์เพื่ออัปเกรดค่าสถานะ | ใช้งาน: !upgrade <hp/atk/def>")
async def upgrade(ctx, stat: str):
    user_id = str(ctx.author.id)
    data = load_data(PVP_DATA_FILE)
    stat = stat.lower()

    if user_id not in data or "profession" not in data[user_id]:
        await ctx.send("คุณยังไม่มีอาชีพ! ใช้ `!choose` เพื่อเลือกก่อน")
        return
        
    if stat not in ["hp", "atk", "def"]:
        await ctx.send("❌ ค่าสถานะไม่ถูกต้อง! กรุณาเลือก: `hp`, `atk`, หรือ `def`")
        return

    user_data = data[user_id]
    cost = int(user_data[stat] * GAME_SETTINGS["upgrade_cost_multiplier"])
    
    if user_data["points"] < cost:
        await ctx.send(f"❌ พอยต์ไม่พอ! คุณต้องการ **{cost}** Points เพื่ออัปเกรด (คุณมี {user_data['points']} Points)")
        return

    data[user_id]["points"] -= cost
    if stat == "hp": data[user_id]["hp"] += 10
    else: data[user_id][stat] += 1
    
    save_data(data, PVP_DATA_FILE)
    await ctx.send(f"✅ อัปเกรดสำเร็จ! ค่า **{stat.upper()}** ของคุณเพิ่มขึ้นแล้ว")

@bot.command(name="fight", help="ท้าต่อสู้กับผู้เล่นอื่น! | ใช้งาน: !fight <@mention>")
async def fight(ctx, opponent: discord.Member):
    attacker_id = str(ctx.author.id)
    defender_id = str(opponent.id)
    data = load_data(PVP_DATA_FILE)

    if attacker_id == defender_id: await ctx.send("คุณไม่สามารถต่อสู้กับตัวเองได้!"); return
    if opponent.bot: await ctx.send("คุณไม่สามารถต่อสู้กับบอทได้!"); return
    if attacker_id not in data or defender_id not in data: await ctx.send("คุณหรือคู่ต่อสู้ยังไม่ได้เลือกอาชีพ!"); return

    now = datetime.utcnow()
    last_fight_time = datetime.fromisoformat(data[attacker_id]["last_fight_time"])
    cooldown = timedelta(seconds=GAME_SETTINGS["fight_cooldown_seconds"])
    if now < last_fight_time + cooldown:
        remaining = (last_fight_time + cooldown) - now
        await ctx.send(f"คุณติดคูลดาวน์อยู่! กรุณารออีก {int(remaining.total_seconds())} วินาที"); return

    attacker_stats = data[attacker_id].copy()
    defender_stats = data[defender_id].copy()
    
    embed = discord.Embed(title=f"⚔️ {ctx.author.display_name} VS {opponent.display_name} 🛡️", color=discord.Color.red())
    fight_message = await ctx.send(embed=embed)
    
    battle_log = ""
    winner = None

    for i in range(1, 6):
        battle_log += f"\n**--- Round {i} ---**\n"
        
        # Attacker's turn
        damage = max(1, attacker_stats["atk"] - defender_stats["def"])
        defender_stats["hp"] -= damage
        battle_log += f"{ctx.author.display_name} โจมตี {opponent.display_name} ทำความเสียหาย **{damage}**! (HP เหลือ {defender_stats['hp']})\n"
        if defender_stats["hp"] <= 0: winner = ctx.author; break
            
        # Defender's turn
        damage = max(1, defender_stats["atk"] - attacker_stats["def"])
        attacker_stats["hp"] -= damage
        battle_log += f"{opponent.display_name} โจมตีกลับ ทำความเสียหาย **{damage}**! (HP เหลือ {attacker_stats['hp']})\n"
        if attacker_stats["hp"] <= 0: winner = opponent; break

        embed.description = battle_log
        await fight_message.edit(embed=embed)
        await asyncio.sleep(2)

    if winner:
        winner_id = str(winner.id)
        loser_id = defender_id if winner_id == attacker_id else attacker_id
        
        data[winner_id]["points"] += GAME_SETTINGS["points_on_win"]
        data[loser_id]["points"] = max(0, data[loser_id]["points"] - GAME_SETTINGS["points_on_loss"])
        
        battle_log += f"\n**🏆 ผู้ชนะคือ {winner.mention}!**\nได้รับ **{GAME_SETTINGS['points_on_win']}** Points"
    else:
        battle_log += "\n**ผลการต่อสู้: เสมอ!**"

    data[attacker_id]["last_fight_time"] = now.isoformat()
    save_data(data, PVP_DATA_FILE)

    embed.description = battle_log
    await fight_message.edit(embed=embed)

# --- 6. คำสั่งสำหรับจัดการตู้โชว์ ---
@bot.group(name="showcase", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def showcase(ctx):
    await ctx.send("คำสั่งไม่ถูกต้อง! กรุณาใช้ `!showcase set` หรือ `!showcase update`")

@showcase.command(name="set", help="[Admin] ติดตั้งตู้โชว์อาชีพในห้องนี้")
@commands.has_permissions(administrator=True)
async def showcase_set(ctx):
    config = load_data(CONFIG_FILE)
    embeds = generate_showcase_embeds()
    
    message_ids = []
    for embed in embeds:
        msg = await ctx.send(embed=embed)
        message_ids.append(msg.id)
        
    config["showcase_channel_id"] = ctx.channel.id
    config["showcase_message_ids"] = message_ids
    save_data(config, CONFIG_FILE)
    
    await ctx.send(f"✅ ติดตั้งตู้โชว์อาชีพในห้องนี้เรียบร้อยแล้ว!", delete_after=10)
    await ctx.message.delete()

@showcase.command(name="update", help="[Admin] อัปเดตข้อมูลในตู้โชว์อาชีพ")
@commands.has_permissions(administrator=True)
async def showcase_update(ctx):
    config = load_data(CONFIG_FILE)
    if not config.get("showcase_channel_id"):
        await ctx.send("❌ ยังไม่ได้ติดตั้งตู้โชว์! กรุณาใช้ `!showcase set` ก่อน")
        return

    try:
        channel = await bot.fetch_channel(config["showcase_channel_id"])
        new_embeds = generate_showcase_embeds()
        
        # ตรวจสอบว่าจำนวน embed ที่จะอัปเดตตรงกับของเดิมหรือไม่
        if len(config["showcase_message_ids"]) != len(new_embeds):
             await ctx.send("❌ จำนวนอาชีพไม่ตรงกับของเดิม! กรุณาใช้ `!showcase set` ใหม่")
             return

        for msg_id, new_embed in zip(config["showcase_message_ids"], new_embeds):
            message = await channel.fetch_message(msg_id)
            await message.edit(embed=new_embed)
            
        await ctx.send("✅ อัปเดตข้อมูลตู้โชว์เรียบร้อยแล้ว!", delete_after=10)
    except discord.NotFound:
        await ctx.send("❌ หาข้อความหรือห้องของตู้โชว์ไม่เจอ! อาจจะถูกลบไปแล้ว กรุณาใช้ `!showcase set` ใหม่")
    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาด: {e}")
    
    await ctx.message.delete()

    server_on()

bot.run(os.getenv('TOKEN'))
