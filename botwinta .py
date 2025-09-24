import os
import discord
from discord import app_commands # Import เพิ่ม
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timedelta

from myserver import server_on

# --- 1. การตั้งค่าพื้นฐาน ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# --- 2. การตั้งค่าระบบเลเวล (สำคัญ! แก้ไขตรงนี้) ---
DATA_FILE = "level_data.json"
COOLDOWN_SECONDS = 60
XP_PER_MESSAGE = (10, 20)
# *** ใส่ ID ของห้องที่จะให้บอทประกาศตรงนี้! ***
ANNOUNCEMENT_CHANNEL_ID = 123456789012345678 # << แก้เป็น Channel ID ของคุณ

# --- 3. ฟังก์ชันจัดการข้อมูลและเลเวล ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def calculate_xp_for_level(level: int):
    return 5 * (level ** 2) + (50 * level) + 100

async def check_level_up(user_id, guild):
    data = load_data()
    user_data = data[user_id]
    xp_needed = calculate_xp_for_level(user_data["level"])

    if user_data["xp"] >= xp_needed:
        user_data["level"] += 1
        current_level = user_data["level"]
        
        announcement_channel = guild.get_channel(1419642518898872371)
        member = guild.get_member(int(user_id))

        if announcement_channel and member:
            try:
                embed = discord.Embed(
                    title="🎉 LEVEL UP! 🎉",
                    description=f"ขอแสดงความยินดีกับ {member.mention} ที่ได้เลื่อนระดับเป็น **Level {current_level}**!",
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await announcement_channel.send(embed=embed)
            except discord.Forbidden:
                print(f"บอทไม่มีสิทธิ์ส่งข้อความในห้อง ID: {1414277732010823770}")
        
        save_data(data)

# --- 4. Event ของบอท ---
@bot.event
async def on_ready():
    print(f'{bot.user} ออนไลน์แล้ว!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    data = load_data()
    user_id = str(message.author.id)
    now = datetime.utcnow()
    
    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 1, "last_message_time": "2000-01-01T00:00:00.000000"}

    last_msg_time = datetime.fromisoformat(data[user_id]["last_message_time"])
    if now < last_msg_time + timedelta(seconds=COOLDOWN_SECONDS):
        return

    xp_to_add = random.randint(*XP_PER_MESSAGE)
    data[user_id]["xp"] += xp_to_add
    data[user_id]["last_message_time"] = now.isoformat()
    save_data(data)

    await check_level_up(user_id, message.guild)

# --- 5. คำสั่ง Slash Command ---
@bot.tree.command(name="myrank", description="ดูเลเวลและ XP ของคุณ")


async def rank(interaction: discord.Interaction, member: discord.Member = None):
    # ... (โค้ดเหมือนเดิม) ...
    await interaction.response.defer()
    target_member = member or interaction.user
    data = load_data()
    user_id = str(target_member.id)
    if user_id not in data:
        await interaction.followup.send(f"{target_member.display_name} ยังไม่มีข้อมูลเลเวล!")
        return
    user_data = data[user_id]
    level = user_data["level"]
    xp = user_data["xp"]
    xp_for_current_level = calculate_xp_for_level(level - 1)
    xp_for_next_level = calculate_xp_for_level(level)
    current_level_xp = xp - xp_for_current_level
    xp_needed = xp_for_next_level - xp_for_current_level
    progress = int((current_level_xp / xp_needed) * 20)
    progress_bar = '█' * progress + '─' * (20 - progress)
    embed = discord.Embed(color=target_member.color)
    embed.set_author(name=f"ข้อมูลเลเวลของ {target_member.display_name}", icon_url=target_member.avatar.url)
    embed.add_field(name="Level", value=f"**{level}**", inline=True)
    embed.add_field(name="Total XP", value=f"**{xp}**", inline=True)
    embed.add_field(name="Progress", value=f"`{progress_bar}`\n`{current_level_xp} / {xp_needed} XP`", inline=False)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="myleaderboard", description="ดูอันดับผู้ที่มีเลเวลสูงสุดในเซิร์ฟเวอร์")
async def leaderboard(interaction: discord.Interaction):
    # ... (โค้ดเหมือนเดิม) ...
    await interaction.response.defer()
    data = load_data()
    if not data:
        await interaction.followup.send("ยังไม่มีข้อมูลเลเวลของใครเลย")
        return
    sorted_users = sorted(data.items(), key=lambda item: item[1]["xp"], reverse=True)
    embed = discord.Embed(title="🏆 Leaderboard", description="ผู้ที่มี XP สูงสุด 10 อันดับแรก", color=discord.Color.gold())
    for i, (user_id, user_data) in enumerate(sorted_users[:10]):
        try:
            member = interaction.guild.get_member(int(user_id))
            member_name = member.display_name if member else f"Unknown User"
        except:
            member_name = f"Left User"
        embed.add_field(name=f"#{i+1}. {member_name}", value=f"**Level:** {user_data['level']} | **XP:** {user_data['xp']}", inline=False)
    await interaction.followup.send(embed=embed)

# --- 5.5 คำสั่งสำหรับแอดมิน (เพิ่มใหม่!) ---
@bot.tree.command(name="เสกเวล", description=" มอบ XP ให้กับสมาชิก")
@app_commands.checks.has_permissions(administrator=True) # กำหนดให้ใช้ได้เฉพาะแอดมิน
async def givexp(interaction: discord.Interaction, member: discord.Member, amount: int):
    sync = await bot.tree.sync()
    data = load_data()
    user_id = str(member.id)
    
    # สร้างข้อมูลผู้ใช้ถ้ายังไม่มี
    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 1, "last_message_time": "2000-01-01T00:00:00.000000"}
        
    data[user_id]["xp"] += amount
    save_data(data)
    
    # ตอบกลับแอดมินว่าทำรายการสำเร็จ (ephemeral=True คือเห็นแค่เรา)
    await interaction.response.send_message(f"✅ มอบ XP จำนวน **{amount}** ให้กับ {member.mention} เรียบร้อยแล้ว", ephemeral=True)
    
    # ตรวจสอบการเลเวลอัปทันที
    await check_level_up(user_id, interaction.guild)

# จัดการ Error กรณีที่คนใช้คำสั่งไม่ใช่แอดมิน
@givexp.error
async def givexp_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!", ephemeral=True)

        server_on()

bot.run(os.getenv('TOKEN'))
