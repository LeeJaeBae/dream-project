파일이 잠겨있어서 직접 출력하겠습니다.

---

# i2v MVP 프로젝트 TODO

## P0 - Critical (필수, 블로킹 항목)

### 프로젝트 초기화
- [ ] **[SETUP] Next.js 프로젝트 초기화** - TypeScript + App Router 기반 (~0.5h)
- [ ] **[SETUP] 필수 의존성 설치** - Tailwind, Supabase SDK, AWS S3 SDK 등 (~0.5h)
- [ ] **[SETUP] 환경변수 설정** - .env.local 파일 구성 (RunPod API Key, Supabase, S3 credentials) (~0.5h)

### 백엔드 API 핵심
- [ ] **[API] POST /api/generate - 생성 요청 엔드포인트** - RunPod /run 호출 및 job_id 반환 (~2h)
- [ ] **[API] GET /api/status/[jobId] - 상태 확인 엔드포인트** - RunPod /status 폴링 래퍼 (~1.5h)
- [ ] **[API] POST /api/webhook - 완료 콜백 수신** - RunPod 웹훅 처리 및 DB 상태 업데이트 (~1.5h)

### 스토리지 연동
- [ ] **[STORAGE] Supabase Storage 또는 S3 연동 설정** - 버킷 생성 및 SDK 설정 (~1h)
- [ ] **[STORAGE] 이미지 업로드 기능** - signed URL 생성 또는 직접 업로드 (~1.5h)
- [ ] **[STORAGE] 비디오 다운로드/저장 기능** - 생성된 mp4 파일 저장 및 URL 제공 (~1.5h)

### 데이터베이스
- [ ] **[DB] Supabase 테이블 스키마 설계** - generations 테이블 (job_id, status, input_url, output_url, metadata) (~1h)
- [ ] **[DB] DB CRUD 유틸리티 함수** - 생성 기록 저장/조회/업데이트 (~1.5h)

---

## P1 - High (핵심 기능, 1주 내)

### 프론트엔드 기본
- [ ] **[UI] 메인 페이지 레이아웃** - 기본 구조 및 네비게이션 (~1h)
- [ ] **[UI] 이미지 업로드 컴포넌트** - 드래그앤드롭 + 파일 선택 (~2h)
- [ ] **[UI] 이미지 미리보기 컴포넌트** - 업로드된 이미지 썸네일 표시 (~1h)
- [ ] **[UI] 프롬프트 입력 폼** - 텍스트 입력 + 옵션 파라미터 (optional) (~1.5h)
- [ ] **[UI] 생성 버튼 및 상태 표시** - 로딩/진행률/완료 상태 표현 (~1.5h)
- [ ] **[UI] 비디오 결과 표시 컴포넌트** - mp4 플레이어 + 다운로드 버튼 (~2h)

### 생성 흐름 통합
- [ ] **[FLOW] 전체 생성 워크플로우 연결** - 업로드→요청→폴링→결과 표시 (~2h)
- [ ] **[FLOW] 상태 폴링 로직 구현** - 5초 간격 /status 호출 + 완료 시 중단 (~1.5h)
- [ ] **[FLOW] 에러 핸들링 통합** - API 에러, 타임아웃, 네트워크 오류 처리 (~1.5h)

### 생성 이력
- [ ] **[HISTORY] 생성 이력 페이지** - 과거 생성 기록 목록 표시 (~2h)
- [ ] **[HISTORY] 이력 상세 보기** - 개별 생성 결과 및 메타데이터 (~1.5h)

---

## P2 - Medium (품질 개선, 2주 내)

### UX 개선
- [ ] **[UX] 로딩 스켈레톤 UI** - 콘텐츠 로딩 시 사용자 경험 개선 (~1h)
- [ ] **[UX] 토스트 알림 시스템** - 성공/에러 메시지 표시 (~1h)
- [ ] **[UX] 폼 유효성 검사** - 입력값 검증 및 에러 메시지 (~1h)
- [ ] **[UX] 반응형 디자인** - 모바일/태블릿 대응 (~2h)

### 기능 고도화
- [ ] **[FEATURE] 생성 옵션 확장** - 해상도, 길이, 스타일 등 파라미터 (~2h)
- [ ] **[FEATURE] 비디오 썸네일 자동 생성** - mp4에서 썸네일 추출 (~1.5h)
- [ ] **[FEATURE] 생성 취소 기능** - 진행 중인 작업 취소 API (~1h)

### 성능/안정성
- [ ] **[PERF] API 요청 재시도 로직** - 지수 백오프 전략 (~1h)
- [ ] **[PERF] 이미지 최적화** - 업로드 전 리사이즈/압축 (~1.5h)
- [ ] **[SECURITY] API 키 보안 점검** - 클라이언트 노출 방지 확인 (~0.5h)

---

## P3 - Backlog (향후 고려)

### 확장 기능
- [ ] **[FUTURE] 사용자 인증 시스템** - Supabase Auth 연동
- [ ] **[FUTURE] 사용량 제한/요금제** - Rate limiting 및 크레딧 시스템
- [ ] **[FUTURE] 소셜 공유 기능** - 생성된 비디오 공유 링크
- [ ] **[FUTURE] 배치 생성** - 여러 이미지 동시 처리
- [ ] **[FUTURE] 갤러리 공개/비공개 설정** - 커뮤니티 갤러리

### 인프라
- [ ] **[INFRA] CI/CD 파이프라인** - Vercel 자동 배포 설정
- [ ] **[INFRA] 모니터링/로깅** - Sentry 또는 Vercel Analytics 연동
- [ ] **[INFRA] 백업 및 복구 전략** - 데이터 보호 정책 수립

---

## Summary

| 우선순위 | 항목 | 예상 시간 |
|---------|------|----------|
| P0 | 12 | ~12.5h |
| P1 | 10 | ~16h |
| P2 | 10 | ~12h |
| P3 | 8 | - |

**총 MVP 완성 예상: ~28.5h (P0+P1)**

---

## 핵심 의존성 관계도

```
[프로젝트 초기화] (P0)
       │
       ▼
[환경변수/SDK 설정] (P0)
       │
       ├──────────────────┬────────────────────┐
       ▼                  ▼                    ▼
[DB 스키마 설계]    [스토리지 연동]      [API 엔드포인트]
   (P0)               (P0)                 (P0)
       │                  │                    │
       └──────────────────┴────────────────────┘
                          │
                          ▼
                 [프론트엔드 UI] (P1)
                          │
                          ▼
                 [생성 워크플로우 통합] (P1)
                          │
                          ▼
                    [이력 관리] (P1)
                          │
                          ▼
                   [UX 개선] (P2)
```

---

## 권장 착수 순서

1. **Next.js 프로젝트 초기화 + 환경변수 설정** - 모든 작업의 기반
2. **Supabase DB 스키마 설계** - 데이터 구조 확정
3. **스토리지 연동 (Supabase Storage 권장)** - 이미지/비디오 저장소 준비
4. **POST /api/generate API 구현** - RunPod 연동 핵심
5. **GET /api/status/[jobId] API 구현** - 폴링 엔드포인트
6. **이미지 업로드 UI + 생성 버튼** - 기본 사용자 흐름
7. **폴링 로직 + 결과 표시** - E2E 워크플로우 완성
8. **웹훅 수신 API (선택)** - 폴링 대체/보완
9. **생성 이력 페이지** - 사용자 경험 완성
10. **UX 개선 및 에러 핸들링 보강** - 안정성 확보

---

## 기술 스택 권장

| 영역 | 기술 | 비고 |
|------|------|------|
| 프레임워크 | Next.js 14+ (App Router) | 풀스택, SSR 지원 |
| 언어 | TypeScript | 타입 안정성 |
| 스타일링 | Tailwind CSS | 빠른 UI 개발 |
| DB | Supabase (PostgreSQL) | 무료 티어, 실시간 기능 |
| 스토리지 | Supabase Storage | 통합 관리, 간편 설정 |
| AI 백엔드 | RunPod Serverless | i2v 모델 호스팅 |
| 배포 | Vercel | Next.js 최적화 |

---

## RunPod 연동 참고사항

### 비동기 실행 패턴 (/run)
```typescript
// POST /api/generate
const response = await fetch(`https://api.runpod.ai/v2/${ENDPOINT_ID}/run`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${RUNPOD_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    input: {
      image_url: uploadedImageUrl,
      prompt: userPrompt,
    },
    webhook: `${NEXT_PUBLIC_BASE_URL}/api/webhook`
  })
});
// 응답: { id: "job-id", status: "IN_QUEUE" }
```

### 상태 확인 패턴 (/status)
```typescript
// GET /api/status/[jobId]
const response = await fetch(
  `https://api.runpod.ai/v2/${ENDPOINT_ID}/status/${jobId}`,
  { headers: { 'Authorization': `Bearer ${RUNPOD_API_KEY}` } }
);
// 가능한 상태: IN_QUEUE, IN_PROGRESS, COMPLETED, FAILED
```

### 웹훅 수신
```typescript
// POST /api/webhook
// RunPod에서 완료 시 호출 - 응답 코드 200 필수 (실패 시 2회 재시도)
```
