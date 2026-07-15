# GitHub Wiki 반영 방법

이 디렉터리의 Markdown 파일은 GitHub Wiki 저장소에 그대로 복사할 수 있는 export 형식입니다.

## 1. Wiki 저장소 clone

GitHub 저장소에서 Wiki를 한 번 생성한 뒤 아래 명령을 실행합니다.

```bash
git clone https://github.com/Edrient17/lgtm-observability-stack.wiki.git
```

## 2. 파일 복사

프로젝트의 `wiki/` 파일을 Wiki 저장소 루트로 복사합니다.

```bash
cp wiki/*.md ../lgtm-observability-stack.wiki/
```

## 3. Wiki 반영

```bash
cd ../lgtm-observability-stack.wiki
git add .
git commit -m "Add LGTM observability stack wiki"
git push
```

`_Sidebar.md`와 `_Footer.md`는 GitHub Wiki에서 자동으로 사이드바와 푸터로 인식됩니다.
