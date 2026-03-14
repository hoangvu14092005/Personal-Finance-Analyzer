# Phase 1 - Auth & Session

## Outcome
Người dùng đăng ký, đăng nhập, đăng xuất được và frontend truy cập dữ liệu qua session bảo mật bằng HttpOnly Cookies.

## Task breakdown

### 1.1 User model & auth schemas
- Hoàn thiện SQLModel `User`.
- Tạo Pydantic schemas cho:
  - register request/response
  - login request/response
  - profile response
- Thêm validation email/password.
- Acceptance:
  - Payload lỗi bị reject rõ ràng.

### 1.2 Password hashing service
- Tạo service hash/verify password.
- Chọn thư viện hash ổn định cho Python.
- Viết unit tests cho hash/verify.
- Acceptance:
  - Password không bao giờ lưu plain text.

### 1.3 JWT + cookie session service
- Tạo access/session token service.
- Cấu hình HttpOnly, Secure, SameSite phù hợp.
- Tạo helper set/clear cookie response.
- Acceptance:
  - Cookie auth set đúng sau login và clear đúng sau logout.

### 1.4 Register API
- `POST /auth/register`
- Kiểm tra email unique.
- Tạo user với default currency/timezone.
- Option: tự login ngay sau register.
- Acceptance:
  - Register thành công và không tạo duplicate email.

### 1.5 Login API
- `POST /auth/login`
- Verify credentials.
- Trả user profile cơ bản.
- Set auth cookie.
- Acceptance:
  - Login đúng thông tin thì vào app được.

### 1.6 Logout API
- `POST /auth/logout`
- Clear auth cookie.
- Optional: blacklist session nếu có.
- Acceptance:
  - Logout xong không truy cập route protected được.

### 1.7 Current user endpoint
- `GET /auth/me`
- Tạo dependency lấy current user từ cookie/JWT.
- Acceptance:
  - Frontend load lại trang vẫn biết user hiện tại.

### 1.8 Frontend auth pages
- Tạo trang `/login` và `/register`.
- Thêm form validation, loading state, error state.
- Redirect đến dashboard sau login.
- Acceptance:
  - Luồng UI khớp API behavior.

### 1.9 Protected routing
- Tạo auth guard ở App Router.
- Chặn dashboard và các feature pages khi chưa auth.
- Tạo logic redirect hợp lý.
- Acceptance:
  - User chưa auth không vào được trang protected.

### 1.10 Onboarding profile init
- Tạo profile tối thiểu: full_name optional, currency, timezone.
- Thêm onboarding flag nếu cần.
- Acceptance:
  - User mới có profile usable cho các phase sau.

### 1.11 Tests
- Backend integration tests cho register/login/logout/me.
- Frontend E2E auth flow.
- Acceptance:
  - Auth flow pass qua test tự động.

## Exit criteria phase 1
- Auth flow đầy đủ hoạt động ổn định.
- Frontend dùng được session cookie an toàn.
- Protected routes và `GET /auth/me` hoạt động đúng.
