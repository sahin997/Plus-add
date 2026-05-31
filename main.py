import re
from io import BytesIO
import telebot
from telebot import types
import openpyxl

BOT_TOKEN = "8345551411:AAF-CIu9IErrC6_mLmd-jeXjPY92UfMDX6U"

class NumberFormatterBot:
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self.MAX_MSG_CHARS = 3800
        self.data_store = {}
        self.register_handlers()

    # সব ধরনের নাম্বার বের করা
    def extract_numbers(self, text: str):
        return re.findall(r'\+?\d+', text)

    # নাম্বার normalize করা
    def normalize_numbers(self, numbers):
        out = []
        for n in numbers:
            n = n.strip()
            if not n or re.fullmatch(r'0+', n) or re.fullmatch(r'\+0+', n):
                continue
            if n.startswith("+"):
                out.append(n)
            else:
                out.append("+" + n)
        return out

    # বড় টেক্সট হলে ফাইল হিসেবে পাঠানো
    def split_or_file(self, chat_id, text: str, caption: str, filename=None):
        if len(text) <= self.MAX_MSG_CHARS:
            self.bot.send_message(chat_id, caption + "\n\n" + text)
        else:
            bio = BytesIO(text.encode("utf-8"))
            bio.seek(0)
            fname = filename if filename else "numbers_with_plus.txt"
            self.bot.send_document(chat_id, (fname, bio), caption=caption)

    # ফাইল প্রসেস করা
    def process_file(self, downloaded_bytes, filename):
        text = ""
        filename = filename.lower()
        if filename.endswith(".txt") or filename.endswith(".csv"):
            try:
                text = downloaded_bytes.decode("utf-8")
            except:
                text = downloaded_bytes.decode("latin-1")
            if filename.endswith(".csv"):
                text = text.replace(",", "\n")
        elif filename.endswith(".xlsx"):
            wb = openpyxl.load_workbook(BytesIO(downloaded_bytes), data_only=True)
            sheet = wb.active
            lines = []
            for row in sheet.iter_rows(values_only=True):
                for cell in row:
                    if cell is not None:
                        val = str(cell).strip()
                        if val and not re.fullmatch(r'0+', val) and not re.fullmatch(r'\+0+', val):
                            lines.append(val)
            text = "\n".join(lines)
        return text

    # হ্যান্ডলার রেজিস্টার করা
    def register_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            markup = types.InlineKeyboardMarkup(row_width=2)
            # 2x2 grid বাটন
            markup.row(
                types.InlineKeyboardButton("📥 Send Numbers", callback_data="send_numbers"),
                types.InlineKeyboardButton("📄 Upload File", callback_data="upload_file")
            )
            markup.row(
                types.InlineKeyboardButton("❓ How to Use", callback_data="how_to_use"),
                types.InlineKeyboardButton("📞 Contact Support", url="https://t.me/FOXyChatSupport")
            )

            user_name = message.from_user.first_name or "there"

            msg = (
                f"👋 Hello, {user_name}!\n\n"
                "✨ *FoXyPrefix* ✨\n\n"
                "➕ Automatically adds '+' prefix to all numbers\n"
                "🌍 Works with numbers from all countries\n"
                "📄 Supports text, .txt, .csv, and .xlsx files\n"
                "❌ Skips invalid numbers like 0 or +0\n\n"
                "⬇️ Choose an option below to get started:"
            )
            self.bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call):
            chat_id = call.message.chat.id
            self.bot.answer_callback_query(call.id)

            if call.data == "send_numbers":
                self.bot.send_message(chat_id, "Send numbers separated by spaces, commas, or newlines.")
            elif call.data == "upload_file":
                self.bot.send_message(chat_id, "Upload a .txt, .csv, or .xlsx file with numbers only.")
            elif call.data == "how_to_use":
                self.bot.send_message(chat_id,
                    "🎬 Watch this short guide to use FoXyPrefix:\n\n"
                    "https://t.me/FoXyMx2/867"
                )

        @self.bot.message_handler(content_types=['text'])
        def handle_text(message):
            chat_id = message.chat.id
            numbers = self.extract_numbers(message.text or "")
            if not numbers:
                self.bot.reply_to(message, "❌ Invalid input. Send digits like 123456789 or +123456789.", parse_mode="Markdown")
                return
            normalized = self.normalize_numbers(numbers)
            self.data_store[chat_id] = normalized
            result_text = "\n".join(normalized)
            self.split_or_file(chat_id, result_text, "✅ Here are your formatted numbers:")

        @self.bot.message_handler(content_types=['document'])
        def handle_document(message):
            chat_id = message.chat.id
            doc = message.document
            file_info = self.bot.get_file(doc.file_id)
            downloaded = self.bot.download_file(file_info.file_path)
            filename = doc.file_name

            if not (filename.lower().endswith(".txt") or filename.lower().endswith(".csv") or filename.lower().endswith(".xlsx")):
                self.bot.reply_to(message, "❌ Unsupported file type. Upload .txt, .csv, or .xlsx.", parse_mode="Markdown")
                return

            try:
                text = self.process_file(downloaded, filename)
            except Exception as e:
                self.bot.reply_to(message, f"❌ Could not read file: {str(e)}", parse_mode="Markdown")
                return

            numbers = self.extract_numbers(text)
            if not numbers:
                self.bot.reply_to(message, "❌ No numbers found in file.", parse_mode="Markdown")
                return

            normalized = self.normalize_numbers(numbers)
            self.data_store[chat_id] = normalized
            result_text = "\n".join(normalized)
            self.split_or_file(chat_id, result_text, f"✅ Processed {len(normalized)} numbers from {filename}", filename)

    def run(self):
        print("Bot started...")
        self.bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_REAL_BOT_TOKEN_HERE":
        raise SystemExit("❌ Please set your BOT_TOKEN inside the script.")
    NumberFormatterBot(BOT_TOKEN).run()