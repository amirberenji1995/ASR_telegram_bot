import os
import time
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import nest_asyncio
from httpx import Timeout

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from dotenv import load_dotenv
load_dotenv()

# Access your sensitive information from environment variables
API_KEY = os.getenv('API_TOKEN')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SPEECHMATICS_URL = os.getenv('SPEECHMATICS_URL')

settings = ConnectionSettings(
    url="https://asr.api.speechmatics.com/v2",
    auth_token=API_KEY,
)


async def transcribe_audio(audio_path: str) -> str:
    conf = {
        "type": "transcription",
        "transcription_config": {
            "language": "auto"
        }
    }
    
    timeout_settings = Timeout(connect=10.0, read=1000.0)  # Adjust these values as needed

    with BatchClient(settings, timeout = timeout_settings) as client:
        try:
            logging.info(f"Submitting job for audio: {audio_path}")
            job_id = client.submit_job(
                audio=audio_path,
                transcription_config=conf,
            )
            logging.info(f'Job {job_id} submitted successfully, waiting for transcript')
            transcript = client.wait_for_completion(job_id, transcription_format='txt')
            logging.info(f'Transcription completed: {transcript}')
            return transcript
        except HTTPStatusError as e:
            logging.error(f'HTTP error occurred: {e.response.status_code}')
            if e.response.status_code == 401:
                return 'Invalid API key - Check your API_KEY!'
            elif e.response.status_code == 400:
                return e.response.json()['detail']
            else:
                return 'An error occurred while processing the audio.'

async def audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Received audio file.")
    audio_file = await update.message.audio.get_file()
    audio_path = f'{audio_file.file_id}.ogg'
    await audio_file.download(audio_path)
    
    transcript = await transcribe_audio(audio_path)
    await update.message.reply_text(transcript)

    # Clean up the audio file
    os.remove(audio_path)
    logging.info(f"Deleted audio file: {audio_path}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me an audio file, and I'll transcribe it!")

if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.AUDIO, audio_handler))
    nest_asyncio.apply()
    logging.info("Bot is running...")
    application.run_polling()