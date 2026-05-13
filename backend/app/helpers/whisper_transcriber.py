import os
from deepgram import DeepgramClient, PrerecordedOptions, DeepgramClientOptions
from dotenv import load_dotenv
from app.utils.video_to_audio_converter import convert_video_to_audio

load_dotenv()

config = DeepgramClientOptions(
    options={"timeout": 300}
)

deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"), config)


def merge_utterances(utterances, max_words: int = 200):
    """Merge small utterances into larger RAG-friendly chunks"""
    chunks = []
    current_text = ""
    current_start = None
    current_end = None
    word_count = 0

    for utt in utterances:
        words_in_utt = len(utt.transcript.split())

        if current_start is None:
            current_start = utt.start

        if word_count + words_in_utt > max_words and current_text:
            chunks.append({
                "start": current_start,
                "end": current_end,
                "text": current_text.strip()
            })
            current_text = ""
            current_start = utt.start
            word_count = 0

        current_text += " " + utt.transcript
        current_end = utt.end
        word_count += words_in_utt

    if current_text:
        chunks.append({
            "start": current_start,
            "end": current_end,
            "text": current_text.strip()
        })

    return chunks


def find_exact_timestamp(utterances: list, topic: str) -> float | None:
    """Find exact timestamp of first utterance mentioning the topic"""
    topic_lower = topic.lower()
    for utt in utterances:
        if topic_lower in utt["text"].lower():
            return utt["start"]
    return None


def transcribe_audio(file_path: str):
    """
    Transcribe audio or video file.
    - If video → auto convert to audio first, delete video
    - If audio → transcribe directly
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = file_path.rsplit(".", 1)[-1].lower()

    # ← convert video to audio if needed
    if ext in VIDEO_EXTENSIONS:
        print(f"Video detected → converting to audio...")
        file_path = convert_video_to_audio(file_path)
        ext = "mp3"

    mimetype_map = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
    }
    mimetype = mimetype_map.get(ext, "audio/mpeg")

    with open(file_path, "rb") as file:
        buffer_data = file.read()

    options = PrerecordedOptions(
        model="nova-2",
        punctuate=True,
        paragraphs=True,
        smart_format=True,
        utterances=True,
    )

    response = deepgram.listen.rest.v("1").transcribe_file(
        {"buffer": buffer_data, "mimetype": mimetype},
        options
    )

    alternative = response.results.channels[0].alternatives[0]
    full_text = alternative.transcript

    raw_utterances = [
        {
            "start": utt.start,
            "end": utt.end,
            "text": utt.transcript
        }
        for utt in response.results.utterances
    ]

    rag_chunks = merge_utterances(response.results.utterances, max_words=200)

    return {
        "full_text": full_text,
        "rag_chunks": rag_chunks,
        "utterances": raw_utterances
    }


# usage
if __name__ == "__main__":
    result = transcribe_audio("app/temp/0b6180e2-42c289c4_4min.mp4")  # audio ✅
    # result = transcribe_audio("app/temp/video.mp4")       # video ✅

    print(f"Total RAG chunks: {len(result['rag_chunks'])}")
    print(f"Total utterances: {len(result['utterances'])}")

    timestamp = find_exact_timestamp(result["utterances"], "google")
    print(f"Google mentioned at: {timestamp}s")