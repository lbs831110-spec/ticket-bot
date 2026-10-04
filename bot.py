import discord
import asyncio
from datetime import datetime

# ==================== 설정 ====================
TOKEN = "MTU1NTk5MDEzODg4OTMxNDUzNA.GiwouS.stb9fD7G5VQCReeDCyuaBAdXu9fxylk3rC799c"
GUILD_ID = 1555975655299096696
TICKET_CATEGORY_ID = 1556170259990319104
STAFF_ROLE_ID = 1555980528367312968
LOG_CHANNEL_ID = 1556342408386453614
# ==============================================


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)


# ---------- 티켓 생성 버튼 ----------
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="티켓 열기",
        style=discord.ButtonStyle.primary,
        emoji="📩",
        custom_id="ticket_create",
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing:
            await interaction.followup.send(f"이미 열린 티켓이 있습니다: {existing.mention}", ephemeral=True)
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        staff_role = guild.get_role(STAFF_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            ),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
            )

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"{user.id} | {user.name}",
        )

        embed = discord.Embed(
            title=f"🎫 {user.name}님의 티켓",
            description="문의 내용을 자세히 적어주세요.\n스태프가 확인 후 답변드립니다.",
            color=0x57F287,
            timestamp=datetime.now(),
        )
        embed.set_footer(text="아래 버튼으로 티켓을 닫을 수 있습니다.")

        await channel.send(
            content=f"{user.mention} <@&{STAFF_ROLE_ID}>",
            embed=embed,
            view=CloseView(),
        )

        await interaction.followup.send(f"티켓이 생성되었습니다: {channel.mention}", ephemeral=True)


# ---------- 티켓 닫기 버튼 ----------
class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="티켓 닫기",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket_close",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "정말 이 티켓을 닫으시겠습니까?",
            view=ConfirmView(),
            ephemeral=True,
        )


# ---------- 닫기 확인 버튼 ----------
class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="확인", style=discord.ButtonStyle.danger, custom_id="confirm_close")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        # 대화 기록 저장
        messages = []
        async for msg in channel.history(limit=200, oldest_first=True):
            time_str = msg.created_at.strftime("%Y-%m-%d %H:%M")
            content = msg.content or "[첨부/임베드]"
            messages.append(f"[{time_str}] {msg.author.name}: {content}")

        transcript = "\n".join(messages) if messages else "기록 없음"

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            chunks = [transcript[i:i + 1900] for i in range(0, len(transcript), 1900)]
            embed = discord.Embed(
                title=f"🎫 티켓 닫힘 — {channel.name}",
                color=0xED4245,
                timestamp=datetime.now(),
            )
            embed.add_field(name="닫은 사람", value=interaction.user.mention, inline=False)

            await log_channel.send(embed=embed)

            for chunk in chunks[:5]:
                await log_channel.send(f"```\n{chunk}\n```")

        await interaction.followup.send("티켓이 5초 후 삭제됩니다.", ephemeral=True)
        await asyncio.sleep(5)
        try:
            await channel.delete()
        except discord.NotFound:
            pass

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, custom_id="cancel_close")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("취소되었습니다.", ephemeral=True)


# ---------- 봇 시작 ----------
@bot.event
async def on_ready():
    print(f"[4080] {bot.user} 온라인")
    print(f"[4080] 서버 수: {len(bot.guilds)}")

    # 버튼 등록 — 중복 방지
    if not bot.persistent_views:
        bot.add_view(TicketView())
        bot.add_view(CloseView())

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("[4080] 서버를 찾을 수 없음. GUILD_ID 확인 필요")
        return

    channel = discord.utils.get(guild.text_channels, name="티켓-생성")

    if not channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                read_message_history=True,
            ),
        }
        category = guild.get_channel(TICKET_CATEGORY_ID)
        channel = await guild.create_text_channel(
            "티켓-생성",
            overwrites=overwrites,
            category=category,
        )

        embed = discord.Embed(
            title="🎫 티켓 생성",
            description="아래 버튼을 눌러 티켓을 생성하세요.\n문의, 신고, 건의 등 자유롭게 이용해주세요.",
            color=0x5865F2,
        )
        await channel.send(embed=embed, view=TicketView())
        print("[4080] #티켓-생성 채널 생성 완료")


bot.run(TOKEN)
