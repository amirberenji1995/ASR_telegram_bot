import os
import logging
import telebot
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
from httpx import Timeout

API_TOKEN=os.getenv("API_TOKEN")
TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
SPEECHMATICS_URL=os.getenv("SPEECHMATICS_URL")


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Set up the Speechmatics client
settings = ConnectionSettings(
    url="https://asr.api.speechmatics.com/v2",
    auth_token=API_TOKEN,
)

def transcribe_audio(audio_path: str) -> str:
    conf = {
        "type": "transcription",
        "transcription_config": {
            "language": "auto"
        }
    }

    timeout_settings = Timeout(10.0, connect=10.0, read=1000.0, write=10.0, pool=10.0)  # Adjust these values as needed

    with BatchClient(settings) as client:
        try:
            print(f"Submitting job for audio: {audio_path}")
            job_id = client.submit_job(
                audio=audio_path,
                transcription_config=conf,
            )
            print(f'Job {job_id} submitted successfully, waiting for transcript')
            transcript = client.wait_for_completion(job_id, transcription_format='txt')
            print(f'Transcription completed: {transcript}')
            return transcript
        except HTTPStatusError as e:
            print(f'HTTP error occurred: {e.response.status_code}')
            if e.response.status_code == 401:
                return 'Invalid API key - Check your API_KEY!'
            elif e.response.status_code == 400:
                return e.response.json()['detail']
            else:
                return 'An error occurred while processing the audio.'

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Send me an audio file, and I'll transcribe it!")

@bot.message_handler(content_types=['voice'])
def audio_handler(message):
    print("Received audio file.")
    audio_file = bot.get_file(message.voice.file_id)
    audio_path = f'{audio_file.file_id}.ogg'
    file_content = bot.download_file(audio_file.file_path)

    with open(audio_path, 'wb') as f:
      f.write(file_content)

    transcript = transcribe_audio(audio_path)
    bot.reply_to(message, transcript)

    # Clean up the audio file
    os.remove(audio_path)
    print(f"Deleted audio file: {audio_path}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(none_stop=True)