"""One-shot Qwen3-TTS CPU inference; process exit releases model memory."""
import json, sys
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

with open(sys.argv[1],encoding="utf-8") as stream:
    request=json.load(stream)
model=Qwen3TTSModel.from_pretrained(
    request["model"],device_map="cpu",dtype=torch.float32)
wavs,sample_rate=model.generate_voice_clone(
    text=request["text"],
    language=request["language"],
    ref_audio=request["reference_audio"],
    ref_text=request["reference_text"],
)
sf.write(request["output"],wavs[0],sample_rate,subtype="PCM_16")
