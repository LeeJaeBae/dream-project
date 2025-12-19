## Overview
이 레포는 **RunPod Serverless Endpoint**에 올릴 **최소 핸들러 컨테이너 템플릿**입니다.

## Rules
- RunPod Serverless는 워커 컨테이너 내부에서 `handler(event)`를 호출합니다.
- 입력은 `event["input"]`로 전달됩니다.
- 이 템플릿은 ComfyUI API를 호출해서 결과를 만들고, **결과 URL만** 반환합니다.
  - 참고: https://docs.runpod.io/serverless/overview#handler-functions

## Structure
- `handler.py`: RunPod 핸들러 엔트리포인트
- `requirements.txt`: 파이썬 의존성
- `Dockerfile`: 컨테이너 빌드용
- `.runpod/hub.json`: RunPod Hub 배포 구성

## Examples
### 1) RunPod 콘솔에서 엔드포인트 생성(개요)
- **Serverless → New Endpoint**
- **Docker 이미지 소스**:
  - GitHub Repo 빌드 사용 시: Dockerfile path를 `Dockerfile`로 지정

### 2) 호출 입력 예시(ComfyUI 브릿지)
이 핸들러는 (가정상) 컨테이너 내부에 **ComfyUI가 떠있고**, `COMFYUI_BASE_URL`로 접근 가능할 때:
- `workflow`(ComfyUI workflow JSON) + `image_url` 또는 `image_base64`를 받아서
- ComfyUI에 이미지 업로드 후 워크플로우를 큐잉하고
- `history`를 폴링해서 **결과 URL만** 반환합니다. (`image_urls`, `video_urls`)

```json
{
  "input": {
    "workflow": { "1": { "class_type": "..." } },
    "image_url": "https://example.com/input.png",
    "image_filename": "input.png",
    "timeout_s": 300,
    "image_node_id": "728",
    "image_field": "image"
  }
}
```

## Edge Cases
- `runpod` 패키지가 이미지 빌드 시 설치되지 않으면 워커가 시작되지 않습니다. (`requirements.txt` 확인 필요)
- `COMFYUI_BASE_URL`이 설정되어 있지 않으면, 이 핸들러는 `ok:false` 에러를 반환합니다.
- 워크플로우에서 이미지 입력 노드(예: `LoadImage`) 위치/필드명은 워크플로우마다 다를 수 있어, `image_node_id`/`image_field`로 주입 위치를 지정할 수 있습니다.

## Version
- Version: 1.0.0
- Last Update: 2025-12-19
- Change Summary: RunPod Serverless handler/Dockerfile 템플릿 추가


