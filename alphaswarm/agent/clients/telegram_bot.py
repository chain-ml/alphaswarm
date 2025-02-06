import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..agent import AlphaSwarmAgent
from ..agent_client import AlphaSwarmAgentClient, ChatMessage, Context

logger = logging.getLogger(__name__)


class TelegramApp:
    def __init__(self, bot_token: str) -> None:
        self._app = Application.builder().token(bot_token).build()

    async def _start(self) -> None:
        """Start the bot"""
        await self._app.initialize()
        await self._app.start()
        updater = self._app.updater
        if updater:
            await updater.start_polling()
        logger.info("Telegram bot started successfully")

    async def _stop(self) -> None:
        """Stop the bot"""
        updater = self._app.updater
        if updater:
            await updater.stop()
        await self._app.stop()
        await self._app.shutdown()

    async def send_message(self, chat_id: int, *, message: str, parse_mode: str = ParseMode.MARKDOWN) -> None:
        """Send a message to a specific chat"""
        try:
            await self._app.bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            raise e


class TelegramBot(TelegramApp, AlphaSwarmAgentClient[Update]):
    def __init__(self, agent: AlphaSwarmAgent, bot_token: str) -> None:
        TelegramApp.__init__(self, bot_token)
        AlphaSwarmAgentClient.__init__(self, agent=agent, client_id="telegram")

        self.message_queue: asyncio.Queue = asyncio.Queue()

        # Add command handlers
        self._app.add_handler(CommandHandler("start", self._start_command))
        self._app.add_handler(CommandHandler("help", self._help_command))
        self._app.add_handler(CommandHandler("id", self._id_command))
        self._app.add_handler(CommandHandler("chat", self._handle_chat_command))
        self._app.add_handler(CommandHandler("alpha", self._handle_chat_command))  # Use same handler for both

        # Add message handler for non-command messages
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_chat_message))

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        if update.message is None:
            raise ValueError("missing message")
        welcome_message = self._build_welcome_message(update)
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        help_message = """🤖 *AlphaSwarm Assistant*

I can help you with:
- Getting token prices (e.g. "What's the price of ETH in USDC?")
- Checking social metrics (e.g. "Show me AIXBT's social metrics")
- Analyzing strategies (e.g. "Analyze the eth_usdc_basic strategy")
- Checking positions (e.g. "What's my ETH balance?")

*Commands:*
/start - Start the bot and get your Chat ID
/help - Show this help message
/id - Show your Chat ID (needed for notifications)

You can also just chat with me naturally!"""

        if update.message is None:
            raise ValueError("missing message")
        await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)

    async def _id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /id command"""
        if update.message is None:
            raise ValueError("missing message")
        chat_id = self._get_chat_id(update)
        await update.message.reply_text(f"Your Chat ID: `{chat_id}`", parse_mode=ParseMode.MARKDOWN)

    async def _handle_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

        if update.message is None:
            raise ValueError("missing message")

        try:
            chat_id = self._get_chat_id(update)
            # Get the message content after the command
            if update.message.text is None:
                raise ValueError("missing message text")

            current_message = update.message.text.split(" ", 1)[1] if " " in update.message.text else ""
            if not current_message.strip():
                await update.message.reply_text("Please provide a message after the command.")
                return

            logger.info(f"Processing command message: '{current_message}'")
            self.message_queue.put_nowait(Context(context=update, message=current_message, id=chat_id))

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await update.message.reply_text(f"Sorry, I encountered an error: {str(e)}")

    async def _handle_chat_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle non-command messages"""
        if update.message is None:
            raise ValueError("missing message")

        try:
            chat_id = self._get_chat_id(update)
            if update.message.text is None:
                raise ValueError("missing message text")
            current_message = update.message.text
            logger.info(f"Processing regular message: '{current_message}'")
            self.message_queue.put_nowait(Context(context=update, message=current_message, id=chat_id))

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await update.message.reply_text(f"Sorry, I encountered an error: {str(e)}")

    async def on_agent_response(self, context: Context[Update], message: ChatMessage) -> None:
        update = context.context
        if update.message is None:
            raise ValueError("missing message")
        await update.message.reply_text(message.content, parse_mode="Markdown")

    async def on_agent_error(self, context: Context[Update], error: ChatMessage) -> None:
        update = context.context
        if update.message is None:
            raise ValueError("missing message")
        await update.message.reply_text(error.content, parse_mode="Markdown")

    async def on_start(self) -> None:
        await self._start()

    async def on_stop(self) -> None:
        await self._stop()

    async def get_message(self) -> Context[Update]:
        return await self.message_queue.get()

    def _get_chat_id(self, update: Update) -> int:
        if update.effective_chat is None:
            raise ValueError("missing effective_chat")
        chat_id = update.effective_chat.id
        return chat_id

    def _build_welcome_message(self, update: Update) -> str:
        chat_id = self._get_chat_id(update)
        welcome_message = f"""👋 Welcome to AlphaSwarm!

Your Chat ID: `{chat_id}`
⚠️ Save this ID to receive notifications!

Use /help to see available commands, or just chat with me naturally about:
- Token prices
- Social metrics
- Trading strategies
- Portfolio positions"""
        return welcome_message
