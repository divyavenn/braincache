import uuid, trafilatura, requests
from qdrant_client.http import models as qm
from embed import text_embed, clip_image_embed
from qdrant import qc
import subprocess, os, glob

def ingest_web(url):
    html = requests.get(url, timeout=20).text
    text = trafilatura.extract(html) or ""
    if not text.strip(): return
    # chunk text ~800-1200 chars; here 1 chunk for brevity
    vec = text_embed(text[:2000])
    qc.upsert("text_1536", points=[qm.PointStruct(
        id=str(uuid.uuid4()),
        vector=vec,
        payload={"type":"web","url":url,"title":url,"snippet":text[:300]}
    )])
    
def ingest_image(path, src_url=None):
    vec = clip_image_embed(path)
    qc.upsert("visual_512", points=[qm.PointStruct(
        id=str(uuid.uuid4()),
        vector=vec,
        payload={"type":"image","url":src_url,"path":path}
    )])
    # optional OCR/caption -> add to text_1536 as well


def sample_frames(video_path, out_dir, every_sec=30):
    os.makedirs(out_dir, exist_ok=True)
    # 1 frame every `every_sec` seconds
    subprocess.run([
      "ffmpeg","-hide_banner","-loglevel","error","-i",video_path,
      "-vf", f"fps=1/{every_sec}",
      os.path.join(out_dir, "frame_%06d.jpg")
    ], check=True)
    return sorted(glob.glob(os.path.join(out_dir,"frame_*.jpg")))

def ingest_video(video_path, src_url=None):
    frames = sample_frames(video_path, video_path+"_frames", every_sec=30)
    points=[]
    for i,fp in enumerate(frames):
        v=clip_image_embed(fp)
        points.append(qm.PointStruct(
            id=str(uuid.uuid4()),
            vector=v,
            payload={"type":"video_frame","url":src_url,"video":video_path,"frame_idx":i}
        ))
    if points: qc.upsert("visual_512", points=points)
    # optional: transcript -> text_1536