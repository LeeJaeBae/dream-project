"""
RunPod Serverless handler template.

Fact: 이 레포에는 아직 Next.js/백엔드 코드가 없고, RunPod 연동 TODO만 존재합니다.
Inference: 우선 RunPod Serverless에 올릴 "핸들러 컨테이너" 템플릿을 제공합니다.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple
import uuid

import runpod
import requests
import websocket


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

def _env_bool(key: str, default: bool) -> bool:
    v = os.environ.get(key)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "y", "on")


def _get_comfy_base_url() -> str:
    """
    ComfyUI가 컨테이너 내부에서 뜬다는 전제의 기본값을 제공.
    - env COMFYUI_BASE_URL이 있으면 우선 사용 (예: http://127.0.0.1:8188)
    """
    return os.environ.get("COMFYUI_BASE_URL", "http://127.0.0.1:8188").rstrip("/")


def _get_comfy_host(base_url: str) -> str:
    # websocket URL 조립에 필요: "127.0.0.1:8188"
    # (base_url이 http(s)://host:port 라는 가정)
    if "://" in base_url:
        return base_url.split("://", 1)[1]
    return base_url


def _check_server(url: str, retries: int, delay_ms: int) -> bool:
    for _ in range(max(1, retries)):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(max(1, delay_ms) / 1000)
    return False


def _attempt_websocket_reconnect(
    ws_url: str,
    max_attempts: int,
    delay_s: int,
    initial_error: Exception,
    comfy_http_root: str,
) -> websocket.WebSocket:
    last_reconnect_error: Exception = initial_error
    for attempt in range(max(1, max_attempts)):
        # ComfyUI HTTP가 죽었으면 websocket 재시도 의미가 없음
        if not _check_server(comfy_http_root, retries=1, delay_ms=0):
            raise websocket.WebSocketConnectionClosedException(
                "ComfyUI HTTP unreachable during websocket reconnect"
            )
        try:
            new_ws = websocket.WebSocket()
            new_ws.connect(ws_url, timeout=10)
            return new_ws
        except (websocket.WebSocketException, ConnectionRefusedError, socket.timeout, OSError) as e:
            last_reconnect_error = e
            if attempt < max_attempts - 1:
                time.sleep(max(1, delay_s))
    raise websocket.WebSocketConnectionClosedException(
        f"Failed to reconnect websocket. Last error: {last_reconnect_error}"
    )


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

    qs = urllib.parse.urlencode(
        {"filename": filename, "subfolder": subfolder, "type": file_type}
    )
    return f"{base_url}/view?{qs}"

def _upload_images_from_input(
    base_url: str,
    job_input: Dict[str, Any],
) -> Tuple[List[str], List[str]]:
    """
    업로드된 파일명을 반환:
    - names: 업로드된 파일명 리스트
    - errors: 에러 메시지 리스트

    지원 입력:
    - images: [{ "name": "x.png", "image": "<base64 or data-uri>" }, ...]
    - 또는 image_url / image_base64 (+ image_filename)
    """
    uploaded_names: List[str] = []
    errors: List[str] = []

    images = job_input.get("images")
    if images is None:
        image_url = job_input.get("image_url")
        image_base64 = job_input.get("image_base64")
        if not image_url and not image_base64:
            return [], ["Provide either `images` or (`image_url`/`image_base64`)"]
        name = str(job_input.get("image_filename") or "input.png")
        try:
            if image_url:
                image_bytes = _download_image_bytes(str(image_url))
            else:
                image_bytes = _decode_base64_image(str(image_base64))
            uploaded_names.append(_comfy_upload_image(base_url, image_bytes, name))
        except Exception as e:
            errors.append(f"Failed to upload image: {e}")
        return uploaded_names, errors

    if not isinstance(images, list):
        return [], ["`images` must be a list"]

    for item in images:
        if not isinstance(item, dict):
            errors.append("Each item in `images` must be an object")
            continue
        name = item.get("name")
        data = item.get("image")
        if not name or not data:
            errors.append("Each image must have `name` and `image`")
            continue
        try:
            image_bytes = _decode_base64_image(str(data))
            uploaded_names.append(_comfy_upload_image(base_url, image_bytes, str(name)))
        except Exception as e:
            errors.append(f"Failed to upload `{name}`: {e}")

    return uploaded_names, errors


def _queue_and_wait_ws(
    comfy_base_url: str,
    workflow: Dict[str, Any],
    comfy_org_api_key: Optional[str] = None,
) -> Tuple[Optional[str], List[str]]:
    """
    ComfyUI에 workflow를 큐잉하고 websocket으로 완료를 대기.
    """
    errors: List[str] = []
    comfy_host = _get_comfy_host(comfy_base_url)

    client_id = str(uuid.uuid4())
    ws_url = f"ws://{comfy_host}/ws?clientId={client_id}"

    ws: Optional[websocket.WebSocket] = None
    prompt_id: Optional[str] = None

    # Comfy.org API Nodes 키(선택) - 예제 구조 따라 payload에 extra_data로 삽입
    payload: Dict[str, Any] = {"prompt": workflow, "client_id": client_id}
    effective_key = comfy_org_api_key or os.environ.get("COMFY_ORG_API_KEY")
    if effective_key:
        payload["extra_data"] = {"api_key_comfy_org": effective_key}

    comfy_http_root = f"{comfy_base_url}/"
    if not _check_server(comfy_http_root, retries=int(os.environ.get("COMFY_API_AVAILABLE_MAX_RETRIES", "50")), delay_ms=int(os.environ.get("COMFY_API_AVAILABLE_INTERVAL_MS", "50"))):
        return None, [f"ComfyUI server ({comfy_host}) not reachable"]

    try:
        ws = websocket.WebSocket()
        assert ws is not None
        ws.connect(ws_url, timeout=10)

        r = requests.post(f"{comfy_base_url}/prompt", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, timeout=30)
        r.raise_for_status()
        resp = r.json()
        prompt_id = resp.get("prompt_id") or resp.get("id")
        if not prompt_id:
            return None, [f"Missing prompt_id in response: {resp}"]

        reconnect_attempts = int(os.environ.get("WEBSOCKET_RECONNECT_ATTEMPTS", "5"))
        reconnect_delay_s = int(os.environ.get("WEBSOCKET_RECONNECT_DELAY_S", "3"))

        while True:
            try:
                if ws is None:
                    return None, ["Websocket not initialized"]
                msg_raw = ws.recv()
                if not isinstance(msg_raw, str):
                    continue
                msg = json.loads(msg_raw)
                if msg.get("type") == "execution_error":
                    data = msg.get("data", {})
                    if data.get("prompt_id") == prompt_id:
                        errors.append(
                            f"Workflow execution error: node_type={data.get('node_type')}, node_id={data.get('node_id')}, message={data.get('exception_message')}"
                        )
                        break
                if msg.get("type") == "executing":
                    data = msg.get("data", {})
                    if data.get("node") is None and data.get("prompt_id") == prompt_id:
                        break
            except websocket.WebSocketConnectionClosedException as closed_err:
                ws = _attempt_websocket_reconnect(
                    ws_url,
                    reconnect_attempts,
                    reconnect_delay_s,
                    closed_err,
                    comfy_http_root,
                )
                assert ws is not None
                continue
            except Exception:
                # websocket 메시지 파싱 에러 등은 일단 무시하고 계속 대기
                continue
    except Exception as e:
        return None, [f"Websocket/queue error: {e}"]
    finally:
        try:
            if ws is not None:
                ws.close()
        except Exception:
            pass

    return str(prompt_id) if prompt_id else None, errors


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
        # images 리스트 방식도 지원하므로 여기서는 강제하지 않음
        pass

    comfy_base_url = _get_comfy_base_url()

    # 입력 이미지 업로드(예제 스타일: images[] 또는 단일 image_url/base64)
    uploaded_names, upload_errors = _upload_images_from_input(comfy_base_url, job_input)
    if upload_errors:
        return {"error": "Image upload failed", "details": upload_errors}

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
                # 단일 이미지 케이스는 첫 업로드 이름을 사용
                if uploaded_names:
                    inputs[str(job_input_image_field)] = uploaded_names[0]

    # 4) 큐잉 + websocket 완료대기(예제 방식)
    prompt_id, ws_errors = _queue_and_wait_ws(
        comfy_base_url,
        workflow,
        comfy_org_api_key=job_input.get("comfy_org_api_key"),
    )
    if not prompt_id:
        return {"error": "Failed to queue workflow", "details": ws_errors}

    # 5) history에서 결과 수집
    try:
        history = _comfy_get_history(comfy_base_url, prompt_id)
        images, videos = _collect_outputs_from_history(history, prompt_id)
    except Exception as e:
        return {"error": f"Failed to fetch history: {e}"}

    image_urls: List[str] = []
    for x in images:
        if x.get("type") == "temp":
            continue
        u = _comfy_file_url(comfy_base_url, x)
        if u:
            image_urls.append(u)

    video_urls: List[str] = []
    for x in videos:
        if x.get("type") == "temp":
            continue
        u = _comfy_file_url(comfy_base_url, x)
        if u:
            video_urls.append(u)

    # URL만 반환(요청)
    return {"image_urls": image_urls, "video_urls": video_urls}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})


