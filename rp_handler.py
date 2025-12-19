"""
RunPod Serverless handler template.

Fact: 이 레포에는 아직 Next.js/백엔드 코드가 없고, RunPod 연동 TODO만 존재합니다.
Inference: 우선 RunPod Serverless에 올릴 "핸들러 컨테이너" 템플릿을 제공합니다.
"""

from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import runpod
import requests


def _require_dict(value: Any, name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"`{name}` must be an object")
    return value


def _download_image_bytes(image_url: str, timeout_s: int = 30) -> bytes:
    r = requests.get(image_url, timeout=timeout_s)
    r.raise_for_status()
    return r.content


def _decode_base64_image(image_base64: str) -> bytes:
    # data URL ("data:image/png;base64,...")도 지원
    if "," in image_base64 and image_base64.strip().lower().startswith("data:"):
        image_base64 = image_base64.split(",", 1)[1]
    return base64.b64decode(image_base64, validate=False)


def _comfy_upload_image(
    base_url: str,
    image_bytes: bytes,
    filename: str,
    timeout_s: int = 60,
) -> str:
    """
    Inference: ComfyUI 표준 API `/upload/image`를 사용한다고 가정합니다.
    - 응답 형식은 설치/버전에 따라 다를 수 있어, 최소한 filename만 확보합니다.
    """
    files = {"image": (filename, image_bytes, "application/octet-stream")}
    r = requests.post(f"{base_url}/upload/image", files=files, timeout=timeout_s)
    r.raise_for_status()
    try:
        data = r.json()
    except Exception:
        data = {}
    return str(data.get("name") or data.get("filename") or filename)


def _comfy_queue_prompt(base_url: str, workflow: Dict[str, Any], timeout_s: int = 60) -> str:
    """
    Inference: ComfyUI 표준 API `/prompt`에 { "prompt": workflow }로 큐잉합니다.
    """
    payload = {"prompt": workflow}
    r = requests.post(f"{base_url}/prompt", json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    prompt_id = data.get("prompt_id") or data.get("id")
    if not prompt_id:
        raise RuntimeError("ComfyUI did not return `prompt_id`")
    return str(prompt_id)


def _comfy_get_history(base_url: str, prompt_id: str, timeout_s: int = 60) -> Dict[str, Any]:
    r = requests.get(f"{base_url}/history/{prompt_id}", timeout=timeout_s)
    r.raise_for_status()
    return _require_dict(r.json(), "history")


def _collect_outputs_from_history(history: Dict[str, Any], prompt_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Inference: history[prompt_id]["outputs"][node_id] 아래에 images/videos가 있을 수 있습니다.
    """
    item = history.get(prompt_id, {})
    outputs = item.get("outputs", {}) if isinstance(item, dict) else {}

    images: List[Dict[str, Any]] = []
    videos: List[Dict[str, Any]] = []

    if isinstance(outputs, dict):
        for _node_id, out in outputs.items():
            if not isinstance(out, dict):
                continue
            if isinstance(out.get("images"), list):
                for x in out["images"]:
                    if isinstance(x, dict):
                        images.append(x)
            if isinstance(out.get("videos"), list):
                for x in out["videos"]:
                    if isinstance(x, dict):
                        videos.append(x)
    return images, videos


def _comfy_file_url(base_url: str, file_info: Dict[str, Any]) -> Optional[str]:
    """
    Inference: ComfyUI `/view?filename=...&subfolder=...&type=...` 형태로 접근 가능합니다.
    """
    filename = file_info.get("filename")
    if not filename:
        return None
    subfolder = file_info.get("subfolder", "")
    file_type = file_info.get("type", "output")

    # 단순 쿼리스트링 조립(특수문자 케이스는 필요 시 개선)
    qs = f"filename={filename}&subfolder={subfolder}&type={file_type}"
    return f"{base_url}/view?{qs}"


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    입력 형식(이 핸들러가 기대):
      {
        "workflow": { ... },             // ComfyUI workflow JSON (오브젝트)
        "image_url": "https://...",      // 또는
        "image_base64": "....",          // base64 또는 data URL
        "image_filename": "input.png",   // 선택
        "timeout_s": 300                 // 선택: 완료 대기 최대 시간
      }
    """
    # RunPod 문서 패턴: handler(event) / event["input"]
    # 참고: https://docs.runpod.io/serverless/overview#handler-functions
    try:
        job_input = _require_dict(event["input"], "input")
    except KeyError:
        return {"ok": False, "error": "Missing `input` in event"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    try:
        workflow = _require_dict(job_input.get("workflow"), "workflow")
    except Exception as e:
        return {"ok": False, "error": str(e)}

    image_url = job_input.get("image_url")
    image_base64 = job_input.get("image_base64")
    image_filename = str(job_input.get("image_filename") or "input.png")
    timeout_s = int(job_input.get("timeout_s") or 300)

    if not image_url and not image_base64:
        return {"ok": False, "error": "Provide either `image_url` or `image_base64`"}

    comfy_base_url = os.environ.get("COMFYUI_BASE_URL")
    if not comfy_base_url:
        return {
            "ok": False,
            "error": "Missing env var `COMFYUI_BASE_URL` (e.g. http://127.0.0.1:8188). "
            "This handler is a ComfyUI-bridge template.",
        }

    # 1) 이미지 bytes 확보
    try:
        if image_url:
            image_bytes = _download_image_bytes(str(image_url))
        else:
            image_bytes = _decode_base64_image(str(image_base64))
    except Exception as e:
        return {"ok": False, "error": f"Failed to load image: {e}"}

    # 2) ComfyUI 업로드
    try:
        uploaded_name = _comfy_upload_image(comfy_base_url, image_bytes, image_filename)
    except Exception as e:
        return {"ok": False, "error": f"Failed to upload image to ComfyUI: {e}"}
    uploaded_image_url = _comfy_file_url(
        comfy_base_url,
        {
            "filename": uploaded_name,
            "subfolder": "",
            "type": "input",
        },
    )

    # 3) 워크플로우에 업로드된 파일명을 주입(옵션)
    # Fact: 사용자 제공 workflow의 노드/키 구조가 고정이라는 근거가 없음
    # Inference: workflow 내부에 "LoadImage" 같은 노드가 있을 수 있어, 사용자가 직접 맞춰야 할 수 있습니다.
    job_input_image_node = job_input.get("image_node_id")
    job_input_image_field = job_input.get("image_field")  # 예: "image"
    if job_input_image_node is not None and job_input_image_field:
        node_id = str(job_input_image_node)
        node = workflow.get(node_id)
        if isinstance(node, dict):
            inputs = node.get("inputs")
            if isinstance(inputs, dict):
                inputs[str(job_input_image_field)] = uploaded_name

    # 4) 큐잉
    try:
        prompt_id = _comfy_queue_prompt(comfy_base_url, workflow)
    except Exception as e:
        return {"ok": False, "error": f"Failed to queue workflow to ComfyUI: {e}"}

    # 5) 완료 대기 + 결과 수집
    deadline = time.time() + max(1, timeout_s)
    last_images: List[Dict[str, Any]] = []
    last_videos: List[Dict[str, Any]] = []

    while time.time() < deadline:
        try:
            history = _comfy_get_history(comfy_base_url, prompt_id)
            images, videos = _collect_outputs_from_history(history, prompt_id)
        except Exception:
            images, videos = [], []
        last_images, last_videos = images, videos
        if images or videos:
            break
        time.sleep(1.0)

    image_urls = [u for u in (_comfy_file_url(comfy_base_url, x) for x in last_images) if u]
    video_urls = [u for u in (_comfy_file_url(comfy_base_url, x) for x in last_videos) if u]

    return {
        "ok": True,
        "prompt_id": prompt_id,
        "uploaded_image_url": uploaded_image_url,
        "image_urls": image_urls,
        "video_urls": video_urls,
        "note": "If URLs are empty, increase `timeout_s` or confirm ComfyUI history/output format.",
    }


runpod.serverless.start({"handler": handler})


