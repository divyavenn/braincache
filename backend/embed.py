import openai, uuid
import torch, clip
from PIL import Image
device = "cpu"
clip_model, clip_preproc = clip.load("ViT-B/32", device=device).  # 512 dims

# TEXT EMBEDDING
  
def text_embed(text):
    resp = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return resp.data[0].embedding



# IMAGE EMBEDDING

# memory 
def clip_image_embed(path: str):
    with torch.no_grad():
        img = clip_preproc(Image.open(path).convert("RGB")).unsqueeze(0).to(device)
        v = clip_model.encode_image(img).float()
        v = v / v.norm(dim=-1, keepdim=True)
    return v.cpu().numpy()[0].tolist()

from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')
def extract_ocr(path):
    res = ocr.ocr(path, cls=True)[0]
    spans = [{"text": t[1][0], "conf": t[1][1], "bbox": t[0]} for t in res]
    spans = [s for s in spans if s["conf"] >= 0.6]
    text = " ".join(s["text"] for s in spans)
    return text_embed(text)
  
  
# queries
def clip_query_embed(text: str):
    with torch.no_grad():
        t = clip.tokenize([text]).to(device)
        v = clip_model.encode_text(t).float()
        v = v / v.norm(dim=-1, keepdim=True)
    return v.cpu().numpy()[0].tolist()


# AUDIO EMBEDDING
from openai import OpenAI
client = OpenAI()

def audio_embed(audio_path: str):
    # Transcribe audio using Whisper API
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    
    # Get embedding of transcript text
    return text_embed(transcript.text)
