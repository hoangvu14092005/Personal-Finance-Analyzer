# Implementation Plan: Architecture Analysis & Documentation System

## Overview

Implement một static analysis tool để tự động phân tích kiến trúc backend và tạo tài liệu chi tiết. Tool sử dụng Python AST để parse source code, trích xuất thông tin về functions, classes, dependencies, và call relationships, sau đó generate markdown documentation với Mermaid diagrams.

## Tasks

- [ ] 1. Setup project structure và core data models
  - Tạo thư mục `tools/architecture_analyzer/`
  - Define core data models: `FunctionInfo`, `ClassInfo`, `ImportInfo`, `FileInfo`, `CallRelationship`, `DependencyInfo`, `AnalysisResult`, `AnalyzerConfig`
  - Setup logging configuration
  - _Requirements: 8.6, 2.1-2.7_

- [ ] 2. Implement FileScanner component
  - [ ] 2.1 Implement FileScanner class với scan logic
    - Implement `__init__` với root_paths và exclusions
    - Implement `scan()` method sử dụng `pathlib.Path.rglob("**/*.py")`
    - Implement exclusion pattern filtering
    - Sort results để đảm bảo deterministic output
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  
  - [ ]* 2.2 Write property test for FileScanner
    - **Property 3: File Scanning Correctness**
    - **Validates: Requirements 6.1-6.6**
  
  - [ ]* 2.3 Write unit tests for FileScanner
    - Test với temporary directory structure
    - Test exclusion patterns hoạt động đúng
    - Test edge cases: empty directory, no Python files
    - _Requirements: 6.1-6.6_

- [ ] 3. Implement ASTParser component
  - [ ] 3.1 Implement ASTParser class
    - Implement `parse_file()` method sử dụng `ast.parse()`
    - Handle `SyntaxError` gracefully với logging
    - Return `None` cho files có syntax error
    - _Requirements: 8.1, 8.2_
  
  - [ ]* 3.2 Write property test for ASTParser
    - **Property 4: AST Parsing Robustness**
    - **Validates: Requirements 8.1, 8.2**
  
  - [ ]* 3.3 Write unit tests for ASTParser
    - Test parse valid Python files
    - Test handle syntax errors gracefully
    - Test với various Python syntax features
    - _Requirements: 8.1, 8.2_

- [ ] 4. Checkpoint - Verify file scanning và parsing
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement CodeAnalyzer component với visitor pattern
  - [ ] 5.1 Implement CodeAnalyzer class kế thừa ast.NodeVisitor
    - Implement `__init__` để initialize state
    - Implement `analyze_file()` method
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 8.3, 8.4_
  
  - [ ] 5.2 Implement visitor methods cho functions
    - Implement `visit_FunctionDef()` để extract function info
    - Implement `visit_AsyncFunctionDef()` cho async functions
    - Extract signatures với type hints
    - Extract docstrings và decorators
    - _Requirements: 2.2, 2.3, 2.4, 8.3, 8.4, 8.5_
  
  - [ ] 5.3 Implement visitor methods cho classes
    - Implement `visit_ClassDef()` để extract class info
    - Extract base classes và methods
    - Handle nested classes
    - _Requirements: 2.2, 2.3, 2.4_
  
  - [ ] 5.4 Implement visitor methods cho imports
    - Implement `visit_Import()` cho import statements
    - Implement `visit_ImportFrom()` cho from...import statements
    - _Requirements: 2.1, 4.1_
  
  - [ ]* 5.5 Write property test for CodeAnalyzer
    - **Property 1: Extraction Completeness**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 8.3, 8.4**
  
  - [ ]* 5.6 Write property test for signature formatting
    - **Property 7: Signature Formatting Consistency**
    - **Validates: Requirements 8.5**
  
  - [ ]* 5.7 Write unit tests for CodeAnalyzer
    - Test extract functions với type hints
    - Test extract classes với methods
    - Test extract imports
    - Test extract docstrings và decorators
    - _Requirements: 2.1-2.4, 8.3-8.5_

- [ ] 6. Implement CallGraphBuilder component
  - [ ] 6.1 Implement CallGraphBuilder class kế thừa ast.NodeVisitor
    - Implement `__init__` với file_infos dictionary
    - Implement `build_graph()` method
    - Track current_function context
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [ ] 6.2 Implement call detection logic
    - Implement `visit_Call()` để detect function calls
    - Handle direct calls (Name nodes)
    - Handle method calls (Attribute nodes)
    - Resolve callee names dựa trên imports
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [ ]* 6.3 Write property test for CallGraphBuilder
    - **Property 2: Call Graph Completeness**
    - **Validates: Requirements 3.1, 3.2, 3.3**
  
  - [ ]* 6.4 Write unit tests for CallGraphBuilder
    - Test detect direct function calls
    - Test detect method calls
    - Test resolve imported functions
    - Test handle unknown callees
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 7. Checkpoint - Verify analysis components
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement DependencyMapper component
  - [ ] 8.1 Implement DependencyMapper class
    - Implement `__init__` với file_infos
    - Implement `map_dependencies()` method
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ] 8.2 Implement dependency detection logic
    - Implement `_is_external_library()` để classify imports
    - Implement `_extract_env_variables()` để find os.getenv calls
    - Detect database operations patterns
    - Detect external API usage
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 8.3 Write property test for DependencyMapper
    - **Property 5: External Dependency Identification**
    - **Validates: Requirements 4.1, 4.4**
  
  - [ ]* 8.4 Write unit tests for DependencyMapper
    - Test identify external libraries
    - Test extract environment variables
    - Test detect database operations
    - Test detect external APIs
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 9. Implement DocumentationGenerator component
  - [ ] 9.1 Implement DocumentationGenerator class
    - Implement `__init__` với file_infos, call_relationships, dependencies
    - Implement `generate()` method để orchestrate generation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_
  
  - [ ] 9.2 Implement table of contents generation
    - Implement `_generate_toc()` với anchor links
    - _Requirements: 5.7_
  
  - [ ] 9.3 Implement architecture diagram generation
    - Implement `_generate_architecture_diagram()` với Mermaid syntax
    - Generate diagram showing components: Frontend, API, Worker, DB, Redis, S3
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ] 9.4 Implement file details generation
    - Implement `_generate_file_details()` với functions và classes
    - Format signatures theo PEP 8
    - Include docstrings và line numbers
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 7.1, 7.2, 7.5_
  
  - [ ] 9.5 Implement call graph generation
    - Implement `_generate_call_graph()` với Mermaid flowchart
    - Handle cycles và recursive calls
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [ ] 9.6 Implement dependency matrix generation
    - Implement `_generate_dependency_matrix()` với markdown table
    - Include external libraries, database, APIs, env variables
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 7.3_
  
  - [ ]* 9.7 Write property test for DocumentationGenerator
    - **Property 8: Documentation Structure Invariant**
    - **Validates: Requirements 5.1-5.7**
  
  - [ ]* 9.8 Write unit tests for DocumentationGenerator
    - Test generate valid markdown
    - Test generate valid Mermaid syntax
    - Test table formatting
    - Test anchor links
    - _Requirements: 5.1-5.7, 7.1-7.5_

- [ ] 10. Implement main orchestrator và CLI
  - [ ] 10.1 Create main analyzer orchestrator
    - Implement `ArchitectureAnalyzer` class để orchestrate toàn bộ pipeline
    - Wire FileScanner → ASTParser → CodeAnalyzer → CallGraphBuilder → DependencyMapper → DocumentationGenerator
    - Handle errors gracefully và collect error reports
    - _Requirements: 8.2, 8.6_
  
  - [ ] 10.2 Implement CLI interface
    - Create `analyzer_cli.py` với argparse
    - Support `--output` flag cho output path
    - Support `--include-private` flag
    - _Requirements: 5.1_
  
  - [ ]* 10.3 Write property test for read-only invariant
    - **Property 6: Read-Only Invariant**
    - **Validates: Requirements 8.6**
  
  - [ ]* 10.4 Write integration test
    - Create mini codebase với 3-5 test files
    - Run full analysis pipeline
    - Verify output markdown có đầy đủ sections
    - Verify Mermaid diagrams có valid syntax
    - _Requirements: 5.1-5.8, 8.6_

- [ ] 11. Checkpoint - Verify complete system
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Run analyzer trên actual backend codebase
  - [ ] 12.1 Configure analyzer cho backend paths
    - Set root_paths: `backend/api/app`, `backend/worker`, `backend/shared/pfa_shared`
    - Set exclusions: tests, __pycache__, .venv, alembic, cache directories
    - _Requirements: 6.1-6.6_
  
  - [ ] 12.2 Execute analyzer và generate documentation
    - Run `python analyzer_cli.py --output docs/backend_architecture.md`
    - Verify execution completes without crashes
    - Check for any parsing errors trong logs
    - _Requirements: 5.1-5.8, 8.1, 8.2_
  
  - [ ] 12.3 Validate generated documentation
    - Verify markdown syntax is valid
    - Verify Mermaid diagrams render correctly
    - Verify table of contents links work
    - Verify all backend files are covered
    - _Requirements: 5.1-5.8, 7.1-7.6_

- [ ] 13. Add onboarding sections to documentation
  - [ ] 13.1 Add "Getting Started" section
    - Write guide on how to read the documentation
    - Explain structure và navigation
    - _Requirements: 9.1_
  
  - [ ] 13.2 Add "Key Components" section
    - Explain vai trò của API, Worker, Shared modules
    - Highlight critical components
    - _Requirements: 9.2_
  
  - [ ] 13.3 Add "Common Patterns" section
    - Document patterns: dependency injection, async context managers, repository pattern
    - _Requirements: 9.3_
  
  - [ ] 13.4 Add "Next Steps" section
    - Suggest cách sử dụng documentation cho code review và refactoring
    - _Requirements: 9.5_

- [ ] 14. Final checkpoint - Review và validate
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional và có thể skip cho faster MVP
- Analyzer sử dụng Python standard library only (ast, pathlib, dataclasses, typing, logging)
- Target performance: < 5 seconds cho ~50 files
- Output format: Markdown với Mermaid diagrams
- Property tests validate universal correctness properties từ design document
- Unit tests validate specific examples và edge cases
