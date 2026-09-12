from pydub import AudioSegment
import numpy as np
from ._model import get_feature_extractor, get_model
import torch
from logging import getLogger

__all__ = ["load_and_resample_audio", "get_audio_embedding", "scan_audio"]

logger = getLogger(__name__)


def load_and_resample_audio(file: str, target_sr: int = 48000) -> np.ndarray:
    """
    ファイルを読み込んで指定したサンプリングレート、モノラル、float32 (-1, 1) のNumPy配列として返す。
    """
    audio = AudioSegment.from_file(file)
    audio = audio.set_frame_rate(target_sr).set_channels(1)
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    if audio.sample_width == 2:
        samples /= np.iinfo(np.int16).max
    elif audio.sample_width == 4:
        samples /= np.iinfo(np.int32).max
    else:
        max_val = float(2 ** (8 * audio.sample_width - 1))
        samples /= max_val
    return samples


def get_audio_embedding(
    samples: np.ndarray,
    window_sec=10,
    stride_sec=5,
    sr=48000,
) -> np.ndarray:
    """
    サンプル配列からオーディオ埋め込みを取得する。
    """
    feature_extractor = get_feature_extractor()
    model = get_model(eval=True)

    window_samples = int(window_sec * sr)
    stride_samples = int(stride_sec * sr)
    total_samples = len(samples)

    with torch.no_grad():
        embeddings = []
        for start in range(0, total_samples - window_samples + 1, stride_samples):
            chunk = samples[start : start + window_samples]

            inputs = feature_extractor(chunk, return_tensors="pt", sampling_rate=sr)
            embed = model.get_audio_features(**inputs).pooler_output.squeeze(0)
            embeddings.append(embed)

        embeddings = torch.stack(embeddings)
        mean_embedding = embeddings.mean(dim=0)
        norm = torch.linalg.norm(mean_embedding)
        if norm > 0:
            mean_embedding = mean_embedding / norm
        return mean_embedding.cpu().numpy()  # 形状: (512,)


def scan_audio(file: str, sr=48000):
    samples = load_and_resample_audio(file, target_sr=sr)
    embedding = get_audio_embedding(samples, sr=sr)
    return embedding
