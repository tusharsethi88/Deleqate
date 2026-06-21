@echo off
REM ============================================================
REM  Deleqate codebase cleanup
REM  Removes only confirmed-unused / regenerable files.
REM  Reviewed against current routing (backend/config/urls.py),
REM  Home.jsx, the built SPA bundle, and /logo-showroom.
REM  Run from the repo root:  D:\Deleqate
REM  Safe to re-run; missing items are skipped.
REM ============================================================
setlocal
cd /d "%~dp0"
echo.
echo Cleaning Deleqate repo at %CD%
echo.

REM --- 1. Python bytecode caches (regenerable, gitignored) ---
echo [1/5] Removing __pycache__ folders...
for /d /r %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d"
)
del /s /q *.pyc >nul 2>&1

REM --- 2. static/img dev scratch (only view_grid.html referenced them) ---
echo [2/5] Removing static/img scratch experiments...
if exist "static\img\sheet_6_cells"   rmdir /s /q "static\img\sheet_6_cells"
if exist "static\img\view_grid.html"  del /q "static\img\view_grid.html"
if exist "static\img\test_2_5_crop.png"    del /q "static\img\test_2_5_crop.png"
if exist "static\img\test_favicon.png"     del /q "static\img\test_favicon.png"
if exist "static\img\test_favicon_2_5.png" del /q "static\img\test_favicon_2_5.png"
if exist "static\img\test_logo_2_5.png"    del /q "static\img\test_logo_2_5.png"
if exist "static\img\test_logo_tight.png"  del /q "static\img\test_logo_tight.png"

REM --- 3. Redundant Photoroom.zip (extracted Photoroom\ folder kept alongside) ---
echo [3/5] Removing redundant Photoroom.zip archives...
if exist "static\img\task_holders\4\Photoroom.zip"          del /q "static\img\task_holders\4\Photoroom.zip"
if exist "frontend\public\img\task_holders\4\Photoroom.zip" del /q "frontend\public\img\task_holders\4\Photoroom.zip"
if exist "frontend\dist\img\task_holders\4\Photoroom.zip"   del /q "frontend\dist\img\task_holders\4\Photoroom.zip"

REM --- 4. Duplicate source copy of task-holder images ---
echo [4/5] Removing duplicate _source-assets\sku-task-holders...
if exist "_source-assets\sku-task-holders" rmdir /s /q "_source-assets\sku-task-holders"

REM --- 5. Planning / handover docs (not part of website code) ---
REM Kept on purpose: CLAUDE.md (active tooling config) and per-folder README.md files.
echo [5/5] Removing non-code planning/handover markdown docs...
if exist "SESSION_HANDOVER.md"          del /q "SESSION_HANDOVER.md"
if exist "PRELAUNCH_QA_REPORT.md"       del /q "PRELAUNCH_QA_REPORT.md"
if exist "LAUNCH_READINESS_DEV_GUIDE.md" del /q "LAUNCH_READINESS_DEV_GUIDE.md"
if exist "DEPLOY_README_LAUNCH.md"      del /q "DEPLOY_README_LAUNCH.md"
if exist "DEPLOY.md"                    del /q "DEPLOY.md"
if exist "DELEQATE_PRELAUNCH_CRITIQUE.md" del /q "DELEQATE_PRELAUNCH_CRITIQUE.md"
if exist "DELEQATE_FORM_SPECS_v1.md"    del /q "DELEQATE_FORM_SPECS_v1.md"
if exist "CODEBASE_BIBLE.md"            del /q "CODEBASE_BIBLE.md"
if exist "CAROUSEL_REDESIGN.md"         del /q "CAROUSEL_REDESIGN.md"
if exist "BUG_HANDOVER_VS_UPLOAD.md"    del /q "BUG_HANDOVER_VS_UPLOAD.md"
if exist "Issues with Current SKUs.docx" del /q "Issues with Current SKUs.docx"

echo.
echo Cleanup complete.
echo NOTE: __pycache__ regenerates automatically when Django next runs.
echo NOTE: _source-assets\sku-task-holders removed; live copies remain in
echo       static\img\task_holders and frontend\public\img\task_holders.
pause
endlocal
