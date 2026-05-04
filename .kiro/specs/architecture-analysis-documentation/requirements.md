# Requirements Document

## Introduction

Hệ thống **Architecture Analysis & Documentation System** phân tích toàn bộ kiến trúc backend của Personal Finance Analyzer và tạo tài liệu chi tiết. Mục tiêu là cung cấp tài liệu đầy đủ về kiến trúc tổng quan, chi tiết từng file, call graph, và dependencies mapping để hỗ trợ onboarding developers mới, code review, refactoring, và planning cho features mới.

Phạm vi phân tích bao gồm:
- `backend/api/app/` - FastAPI service với các modules: api, core, dependencies, integrations, middleware, models, repos, schemas, services
- `backend/worker/` - Background worker với TaskIQ (tasks, ocr_provider, worker_app)
- `backend/shared/pfa_shared/` - Shared package (config, schemas, enums, utils, logging, storage)

Output là file markdown có cấu trúc rõ ràng với Mermaid diagrams, bảng tóm tắt, và dependencies matrix.

## Glossary

- **Analyzer**: Hệ thống phân tích kiến trúc này
- **Codebase**: Toàn bộ source code backend cần phân tích (api, worker, shared)
- **Architecture_Diagram**: Sơ đồ kiến trúc tổng quan thể hiện components và data flow
- **Call_Graph**: Sơ đồ quan hệ giữa các functions/methods (caller → callee)
- **Function_Signature**: Chữ ký đầy đủ của function bao gồm tên, parameters, return type
- **Dependencies_Matrix**: Bảng mapping giữa files và external dependencies
- **Source_File**: File Python (.py) trong phạm vi phân tích
- **Mermaid_Diagram**: Định dạng diagram dạng text có thể render thành hình
- **Documentation_Output**: File markdown chứa toàn bộ kết quả phân tích

## Requirements

### Requirement 1: Phân tích kiến trúc tổng quan

**User Story:** Là một developer mới, tôi muốn xem sơ đồ kiến trúc tổng quan, để hiểu các thành phần chính và cách chúng tương tác với nhau.

#### Acceptance Criteria

1. THE Analyzer SHALL tạo Architecture_Diagram dạng Mermaid thể hiện các components chính: Frontend, API, Worker, Database, Redis, MinIO
2. THE Architecture_Diagram SHALL thể hiện luồng dữ liệu giữa các components với mũi tên và labels rõ ràng
3. THE Architecture_Diagram SHALL thể hiện dependencies giữa các components
4. THE Architecture_Diagram SHALL được nhúng vào Documentation_Output ở phần đầu tiên

### Requirement 2: Phân tích chi tiết từng file

**User Story:** Là một developer, tôi muốn xem danh sách đầy đủ các functions và classes trong mỗi file, để hiểu cấu trúc code và trách nhiệm của từng module.

#### Acceptance Criteria

1. FOR ALL Source_Files trong phạm vi `backend/api/app`, `backend/worker`, `backend/shared/pfa_shared`, THE Analyzer SHALL trích xuất tên file và đường dẫn đầy đủ
2. FOR ALL Source_Files, THE Analyzer SHALL trích xuất danh sách tất cả functions, classes, và methods
3. FOR ALL functions và methods, THE Analyzer SHALL trích xuất Function_Signature bao gồm tên, parameters với type hints, và return type
4. FOR ALL functions và classes, THE Analyzer SHALL tạo mô tả chức năng chính dựa trên docstring hoặc code context
5. WHERE function có thuật toán phức tạp hoặc logic đặc biệt, THE Analyzer SHALL ghi chú thuật toán nổi bật
6. WHERE function có validation rules hoặc constraints, THE Analyzer SHALL liệt kê các ràng buộc logic
7. THE Analyzer SHALL tổ chức thông tin theo cấu trúc: file path → classes/functions → signatures → descriptions

### Requirement 3: Tạo Call Graph

**User Story:** Là một developer, tôi muốn xem sơ đồ quan hệ giữa các functions, để hiểu data flow và dependencies trong code.

#### Acceptance Criteria

1. THE Analyzer SHALL tạo Call_Graph dạng Mermaid flowchart thể hiện quan hệ caller → callee
2. THE Call_Graph SHALL bao gồm cả intra-file calls (trong cùng file) và inter-file calls (giữa các files)
3. THE Call_Graph SHALL thể hiện import dependencies giữa các modules
4. WHERE có vòng lặp hoặc đệ quy, THE Call_Graph SHALL đánh dấu rõ ràng
5. THE Call_Graph SHALL được nhúng vào Documentation_Output sau phần phân tích chi tiết files

### Requirement 4: Mapping External Dependencies

**User Story:** Là một developer, tôi muốn biết mỗi file sử dụng thư viện nào, để hiểu dependencies và có thể đánh giá impact khi upgrade libraries.

#### Acceptance Criteria

1. FOR ALL Source_Files, THE Analyzer SHALL trích xuất danh sách thư viện bên ngoài được import
2. FOR ALL Source_Files có database operations, THE Analyzer SHALL ghi chú database connections và query patterns
3. FOR ALL Source_Files có external API calls, THE Analyzer SHALL liệt kê external APIs (S3, Redis, OCR providers)
4. FOR ALL Source_Files sử dụng environment variables, THE Analyzer SHALL liệt kê environment variables dependencies
5. THE Analyzer SHALL tạo Dependencies_Matrix dạng bảng với columns: File Path, External Libraries, Database, External APIs, Environment Variables

### Requirement 5: Tạo Documentation Output

**User Story:** Là một developer, tôi muốn có file markdown đầy đủ và có cấu trúc, để dễ dàng navigate và search thông tin.

#### Acceptance Criteria

1. THE Analyzer SHALL tạo Documentation_Output dạng markdown file
2. THE Documentation_Output SHALL bao gồm Architecture_Diagram ở phần đầu
3. THE Documentation_Output SHALL bao gồm bảng tóm tắt files và functions với links để navigate nhanh
4. THE Documentation_Output SHALL bao gồm phần phân tích chi tiết từng file với đầy đủ signatures và descriptions
5. THE Documentation_Output SHALL bao gồm Call_Graph sau phần phân tích chi tiết
6. THE Documentation_Output SHALL bao gồm Dependencies_Matrix ở phần cuối
7. THE Documentation_Output SHALL có table of contents với anchor links để navigate
8. THE Documentation_Output SHALL đảm bảo 100% coverage của Source_Files trong phạm vi đã định

### Requirement 6: Xử lý phạm vi và exclusions

**User Story:** Là một developer, tôi muốn hệ thống chỉ phân tích source files chính, để tránh nhiễu từ test files và build artifacts.

#### Acceptance Criteria

1. THE Analyzer SHALL bao gồm tất cả files trong `backend/api/app/`, `backend/worker/`, `backend/shared/pfa_shared/`
2. THE Analyzer SHALL loại trừ test files trong thư mục `tests/`
3. THE Analyzer SHALL loại trừ migration files trong thư mục `alembic/`
4. THE Analyzer SHALL loại trừ cache và build artifacts (`.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `__pycache__`, `.venv`)
5. THE Analyzer SHALL loại trừ frontend code
6. WHERE file không phải Python (.py), THE Analyzer SHALL bỏ qua file đó

### Requirement 7: Structured Format và Readability

**User Story:** Là một developer, tôi muốn tài liệu có format rõ ràng và dễ đọc, để nhanh chóng tìm thông tin cần thiết.

#### Acceptance Criteria

1. THE Documentation_Output SHALL sử dụng markdown headers (H1, H2, H3) để phân cấp nội dung
2. THE Documentation_Output SHALL sử dụng code blocks với syntax highlighting cho Python code
3. THE Documentation_Output SHALL sử dụng tables cho Dependencies_Matrix và summary tables
4. THE Documentation_Output SHALL sử dụng Mermaid code blocks cho diagrams
5. THE Documentation_Output SHALL có consistent formatting cho Function_Signatures (format: `def function_name(param: Type) -> ReturnType`)
6. WHERE có danh sách dài, THE Documentation_Output SHALL sử dụng collapsible sections hoặc phân trang logic

### Requirement 8: Parser và Pretty Printer

**User Story:** Là một developer, tôi muốn hệ thống parse Python source code chính xác, để đảm bảo thông tin trích xuất đúng đắn.

#### Acceptance Criteria

1. WHEN một Source_File hợp lệ được cung cấp, THE Python_AST_Parser SHALL parse file thành Abstract Syntax Tree
2. WHEN một Source_File không hợp lệ (syntax error) được cung cấp, THE Python_AST_Parser SHALL ghi log error và bỏ qua file đó
3. THE AST_Analyzer SHALL trích xuất tất cả function definitions, class definitions, và method definitions từ AST
4. THE AST_Analyzer SHALL trích xuất type hints từ function parameters và return annotations
5. THE Pretty_Printer SHALL format Function_Signatures theo chuẩn Python PEP 8
6. FOR ALL valid Source_Files, parsing và extracting thông tin SHALL hoàn thành mà không làm thay đổi source code gốc (read-only operation)

### Requirement 9: Onboarding và Documentation Purpose

**User Story:** Là một tech lead, tôi muốn sử dụng tài liệu này cho onboarding developers mới, để giảm thời gian làm quen với codebase.

#### Acceptance Criteria

1. THE Documentation_Output SHALL bao gồm phần "Getting Started" hướng dẫn cách đọc tài liệu
2. THE Documentation_Output SHALL bao gồm phần "Key Components" giải thích vai trò của từng module chính
3. THE Documentation_Output SHALL bao gồm phần "Common Patterns" mô tả các patterns thường gặp trong codebase
4. WHERE có design decisions quan trọng, THE Documentation_Output SHALL ghi chú lý do và tradeoffs
5. THE Documentation_Output SHALL bao gồm phần "Next Steps" gợi ý cách sử dụng tài liệu cho code review và refactoring

