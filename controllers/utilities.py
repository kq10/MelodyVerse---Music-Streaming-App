from mutagen.mp3 import MP3
import os
from flask import current_app
from werkzeug.utils import secure_filename


def save_song_file(song_file):
    file_name=song_file.filename
    current_file_path = os.path.abspath(__file__)
    root_path = os.path.abspath(os.path.join(current_file_path, '..', '..'))
    song_path = os.path.join(root_path, 'static/audios', file_name)
    song_file.save(song_path)
    
    return file_name

def get_audio_duration(song_file):
    file_path=song_file.filename
    current_file_path = os.path.abspath(__file__)
    root_path = os.path.abspath(os.path.join(current_file_path, '..', '..'))
    song_path = os.path.join(root_path, 'static/audios', file_path)
    audio = MP3(song_path)
    
    return audio.info.length
    