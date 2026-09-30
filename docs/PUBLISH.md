# 완성된 코드를 GitHub에 올리기

ZIP을 다운로드했다면 먼저 압축을 풉니다. `README.md`와 `app.py`가 함께 있는 `IRB` 폴더에서 터미널을 엽니다.

이 안내는 `dy20231031/IRB`가 비어 있는 경우의 첫 업로드용입니다. 이미 다른 코드가 있다면 기존 저장소를 복제한 후 변경 사항을 비교하여 반영하세요. 강제 푸시를 사용하지 않습니다.

## Git으로 첫 업로드

```bash
git init -b main
git add .
git commit -m "feat: add questionnaire-based IRB preparation assistant"
git remote add origin https://github.com/dy20231031/IRB.git
git push -u origin main
```

커밋 작성자 설정이 없다는 오류가 나오면 본인의 이름과 GitHub에서 사용하는 이메일 주소를 이 저장소에 설정한 뒤 커밋부터 다시 실행합니다.

```bash
git config user.name "본인 이름"
git config user.email "본인 GitHub 이메일"
```

GitHub 인증은 본인의 Git 환경에서 진행하세요. API 키나 인증 토큰을 소스 파일이나 채팅에 붙여 넣을 필요는 없습니다.

`remote origin already exists`가 나오면 `git remote -v`로 주소를 확인하고, 올바른 저장소라면 remote 추가 단계는 건너뜁니다. 원격에 새 커밋이 있어서 푸시가 거부되면 먼저 변경 내용을 비교하세요.

## ChatGPT에서 계속 반영하려면

GitHub 연결 앱에 이 계정과 `IRB` 저장소에 대한 쓰기 접근이 허용되어 있어야 합니다. `Resource not accessible by integration` 오류는 연결 앱의 접근 범위를 확인해야 한다는 뜻입니다. 개인 계정에서 저장소 관리 권한이 있는 것과 연결 앱의 권한은 다를 수 있습니다.

GitHub의 연결 앱 설정에서 해당 저장소가 포함되어 있는지 확인한 뒤 연결을 갱신하세요. 저장소 목록이 보이지 않거나 권한을 변경할 수 없으면 계정 또는 조직 관리자에게 연결 설정을 확인해야 합니다.

## 업로드 후 확인

저장소 루트에 `app.py`, `data`, `src`, `tests`가 보이는지 확인합니다. Actions의 Tests가 실행되는 경우 결과를 확인합니다. 코드를 올려도 웹 서비스가 자동 배포되지는 않으며, 로컬 실행 방법은 README에 있습니다.
