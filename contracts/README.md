# 프론트–백엔드 계약 모음

이 폴더는 소비나침반 프론트엔드와 백엔드가 공유해야 하는 API 계약, 데이터 흐름, 예시를 한 곳에 모은 인계 기준이다.

## 계약 파일

| 파일 | 내용 |
|---|---|
| `frontend-backend-contract.md` | v3.2 엔드포인트·검증 메뉴·정보 부족·Gemini 실행 게이트 계약 |
| `openapi.generated.json` | FastAPI에서 생성한 전체 OpenAPI 계약 |
| `examples/` | 프론트가 보내고 받는 대표 JSON 예시 |
| `REVIEW.md` | v2.1 인계 검토 쟁점과 현재 해소/보류 상태 |
| `PROPOSED_CHANGES.md` | 검토 문서의 계약 보완안과 적용 결과 |
| `v3.1-submission-contract.md` | 실제 데이터·개별 메뉴 계산·Gemini 프로토타입의 추가 계약과 완료 시나리오 |
| `../data/real/data_candidates.json` | 3개 장소·7개 공개 가격 참조 후보와 미확보 필드 |
| `../config/gemini_approval_plan.json` | 미승인 Gemini 전송·비용·키 정책과 승인 기록 양식 |

## 실제 코드와의 관계

- 백엔드 모델 원본: `backend/app/models.py`
- 백엔드 라우트 원본: `backend/app/api.py`
- 프론트 API client: `frontend/src/api/client.ts`
- 프론트 타입: `frontend/src/types.ts`
- 호환을 위해 `schemas/openapi.generated.json`도 계속 생성한다.

`health/meta`를 포함한 성공 응답과 404/409/413/422/500/503 오류 응답은 생성 OpenAPI의 명시 DTO를 기준으로 한다. 공개 웹 가격 후보는 실제 예산 DTO에 자동 반입하지 않으며, 검증 필드와 권한을 모두 통과한 real 패키지만 사용한다.

계약을 변경할 때는 백엔드 모델 → OpenAPI 생성 → 프론트 타입/client → 예시 → 테스트 순서로 함께 갱신한다. 가격·총액·순위는 프론트가 계산하거나 신뢰하지 않고 백엔드 응답을 표시한다.

## 재생성

```powershell
.venv\Scripts\python.exe scripts\export_openapi.py
```

이 명령은 `contracts/openapi.generated.json`과 기존 호환 경로인 `schemas/openapi.generated.json`을 동시에 갱신한다.
