import mimetypes
from typing import Dict
import os

from edenai_apis.utils.files import FileInfo, FileWrapper
from pydub.utils import mediainfo


feature_path = os.path.dirname(os.path.dirname(__file__))

data_path = os.path.join(feature_path, "data")

audio_path = f"{data_path}/conversation.mp3"

mime_type = mimetypes.guess_type(audio_path)[0]
file_info= FileInfo(
    os.stat(audio_path).st_size,
    mime_type,
    [extension[1:] for extension in mimetypes.guess_all_extensions(mime_type)],
    mediainfo(audio_path).get("sample_rate", "44100"),
    mediainfo(audio_path).get("channels", "1")
)
file_wrapper = FileWrapper(audio_path, "", file_info)

def speech_to_text_arguments() -> Dict:
    return {
        "file": file_wrapper, 
        "language": "en", 
        "speakers" : 2, 
        "profanity_filter": False,
        "vocabulary" : []
        }
