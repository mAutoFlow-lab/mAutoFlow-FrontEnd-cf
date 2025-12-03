# app.py
# mAutoFlow: code2flow 스타일 레이아웃
# - 위: 헤더
# - 가운데: 좌측 코드 에디터, 우측 플로우차트, 가운데 드래그 가능한 분할바
# - 함수 자동 선택 (main 우선), 타이핑 멈추면 자동 갱신

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from c_autodiag import extract_function_body, StructuredFlowEmitter, extract_function_names

app = FastAPI()


def generate_mermaid_auto(source_code: str, branch_shape: str = "rounded"):
    func_list = extract_function_names(source_code)
    if not func_list:
        raise ValueError("The function could not be found in the code.")
    func_name = "main" if "main" in func_list else func_list[0]

    body = extract_function_body(source_code, func_name)

    # 함수 본문이 원본 코드에서 시작하는 라인 번호(0-based) 계산
    body_index = source_code.find(body)
    if body_index == -1:
        body_start_line = 0
    else:
        body_start_line = source_code[:body_index].count("\n")

    emitter = StructuredFlowEmitter(func_name, branch_shape=branch_shape)
    mermaid = emitter.emit_from_body(body)

    # N1, N2, ... -> 실제 소스 코드 라인 번호(0-based)로 변환
    node_lines = {
        nid: body_start_line + line_idx
        for nid, line_idx in emitter.node_line_map.items()
    }

    return mermaid, func_name, node_lines


@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = r"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8" />
    <title>mAutoFlow</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        :root {
            /* 기본 테마 (classic) */
            --bg-main: #f3f4f6;
            --bg-header: #1f2933;
            --header-text: #f9fafb;

            --bg-code: #111827;
            --code-text: #e5e7eb;
            --code-border: #d1d5db;

            --bg-chart: #ffffff;
            --chart-border: #d1d5db;

            --accent-primary: #2563eb;
            --accent-primary-hover: #1d4ed8;

            --toolbar-text: #374151;
        }

        /* 라이트 테마 */
        body[data-theme="light"] {
            --bg-main: #f9fafb;
            --bg-header: #2563eb;
            --header-text: #ffffff;

            --bg-code: #ffffff;
            --code-text: #111827;
            --code-border: #d1d5db;

            --bg-chart: #ffffff;
            --chart-border: #d1d5db;

            --accent-primary: #2563eb;
            --accent-primary-hover: #1d4ed8;

            --toolbar-text: #111827;
        }

        /* 다크 테마 */
        body[data-theme="dark"] {
            --bg-main: #020617;
            --bg-header: #020617;
            --header-text: #e5e7eb;

            --bg-code: #020617;
            --code-text: #e5e7eb;
            --code-border: #1f2937;

            --bg-chart: #020617;
            --chart-border: #1f2937;

            --accent-primary: #22c55e;
            --accent-primary-hover: #16a34a;

            --toolbar-text: #e5e7eb;
        }

        /* Mermaid SVG Override (dark) */
        body[data-theme="dark"] #chartInner svg path {
            stroke: #f8fafc !important;
        }
        body[data-theme="dark"] #chartInner svg line {
            stroke: #f8fafc !important;
        }
        body[data-theme="dark"] #chartInner svg polygon {
            stroke: #f8fafc !important;
            fill: #f8fafc !important;
        }
        body[data-theme="dark"] #chartInner svg marker path {
            stroke: #f8fafc !important;
            fill: #f8fafc !important;
        }
    
        * { box-sizing: border-box; }
        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
        }
        body {
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            font-size: 14px; /* UI 기본 폰트 */
            background: var(--bg-main);
        }
        header {
            padding: 10px 16px;
            background: var(--bg-header); /* ← 변경 */
            color: var(--header-text);    /* ← 변경 */
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        header h1 {
            margin: 0;
            font-size: 20px;
        }
        header .subtitle {
            font-size: 12px;
            opacity: 0.85;
        }

        .topbar-right {
            font-size: 12px;
            opacity: 0.8;
        }

        .main {
            flex: 1;
            display: flex;
            min-height: 0;
            background: var(--bg-main);
        }

        /* 좌측/우측 패널 + 드래그 분할바 */
        #leftPane {
            flex: 0 0 33%; /* 초기 약 1/3 */
            min-width: 200px;
            display: flex;
            flex-direction: column;
            padding: 8px;
        }
        #divider {
            flex: 0 0 6px;
            cursor: col-resize;
            background: #d1d5db;
        }
        #divider:hover {
            background: #9ca3af;
        }
        #rightPane {
            flex: 0 0 67%; /* 초기 약 2/3 */
            min-width: 260px;
            display: flex;
            flex-direction: column;
            padding: 8px;
        }

        .pane-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
        }
        .pane-title {
            font-weight: 600;
            font-size: 14px;
            color: var(--toolbar-text);
        }

        /* 좌측 코드 영역 */
        #codeContainer {
            flex: 1;
            border-radius: 4px;
            border: 1px solid var(--code-border);  /* ← 변경 */
            background: var(--bg-code);            /* ← 변경 */
            display: flex;
            flex-direction: column;
        }
        #codeHeader {
            padding: 4px 8px;
            border-bottom: 1px solid #4b5563;
            color: var(--code-text);      /* ← 변경 */
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        #codeArea {
            flex: 1;
            padding: 6px;
            display: flex;    /* ← 라인번호 + textarea 가 가로로 배치되도록 */
        }

        #lineNumbers {
            width: 40px;  /* 라인 번호 영역 너비 */
            padding: 6px 4px;
            text-align: right;
            color: var(--code-text);
            background: var(--bg-code);
            border-right: 1px solid var(--code-border);
            font-family: "Consolas", "Roboto Mono", monospace;
            font-size: 13px;
            line-height: 1.4;
            user-select: none;        /* 라인 번호 드래그 방지 */
            overflow: hidden;
        }
        
        #src {
            width: 100%;
            height: 100%;
            border: none;
            outline: none;
            resize: none;
            background: transparent;
            color: var(--code-text);      /* ← 변경 */
            font-family: "Consolas", "Roboto Mono", monospace;
            font-size: 13px;  /* 코드 글자 크기 (너무 크지 않게) */
            line-height: 1.4;
            flex: 1;                  /* ← 남은 영역 꽉 채우기 */
        }

        /* 우측 플로우차트 영역 */
        #toolbar {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
            font-size: 12px;
        }
        .btn {
            padding: 4px 10px;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-size: 12px;
        }
        .btn-primary {
            background: var(--accent-primary);           /* ← 변경 */
            color: white;
        }
        .btn-primary:hover {
            background: var(--accent-primary-hover);     /* ← 변경 */
        }
        .btn-ghost {
            background: #e5e7eb;
            color: #111827;
        }
        .btn-ghost:hover {
            background: #d1d5db;
        }

        #status {
            font-size: 12px;
            color: var(--toolbar-text);                  /* ← 변경 */
        }
        #status.error {
            color: #b91c1c;
        }
        #status.success {
            color: #15803d;
        }
        #currentFunc {
            font-weight: 600;
            font-size: 12px;
            color: var(--toolbar-text);
        }

        #chartContainer {
            flex: 1;
            border-radius: 4px;
            border: 1px solid var(--chart-border); /* ← 변경 */
            background: var(--bg-chart);           /* ← 변경 */
            overflow: auto;

            /* flex 제거하고, 일반 블록 + 텍스트 정렬로 가운데 맞추기 */
            text-align: center;
        }
        #chartInner {
            display: inline-block;   /* 가운데 정렬 대상 */
            margin: 8px;
            transform-origin: top center;  /* 확대 기준은 그대로 중앙 */
        }
        #chartInner .mermaid {
            margin: 0 auto;
        }

        .placeholder {
            color: #9ca3af;
            font-size: 14px;
            text-align: center;
            margin-top: 40px;
        }

        /* Mermaid가 그리는 SVG를 우측 패널 너비에 맞게 조정 */
        #chartInner svg {
            max-width: none;
            height: auto;
            display: block;
            margin: 0 auto;
        }
        

        .zoom-label {
            font-size: 12px;
            min-width: 42px;
            color: var(--toolbar-text);
        }

        /* 코드 ↔ 노드 연동: 선택된 노드 하이라이트 (더 진하게) */
        .node.autoflow-selected rect,
        .node.autoflow-selected polygon,
        .node.autoflow-selected path {
            stroke: #ff0000;              /* 더 강한 빨간색 */
            stroke-width: 4px;            /* 테두리 두께 업 */
            stroke-dasharray: 0;          /* 실선 */
            filter: drop-shadow(0 0 6px rgba(255, 0, 0, 0.9));
        }

        /* 선택된 노드 텍스트도 강조 */
        .node.autoflow-selected text {
            font-weight: 700;
            fill: #000000;
        }

        .topbar-right {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            opacity: 0.9;
        }

        .btn-settings {
            padding: 4px 10px;
            border-radius: 4px;
            border: 1px solid rgba(255,255,255,0.4);
            background: transparent;
            color: inherit;
            cursor: pointer;
            font-size: 12px;
        }
        .btn-settings:hover {
            background: rgba(255,255,255,0.12);
        }

        /* SETTINGS 모달 */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(15,23,42,0.55);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 50;
        }
        .modal-hidden {
            display: none;
        }
        .modal-panel {
            background: #ffffff;
            border-radius: 8px;
            padding: 16px 20px;
            min-width: 260px;
            max-width: 320px;
            box-shadow: 0 10px 40px rgba(15,23,42,0.45);
            font-size: 13px;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .modal-header h2 {
            margin: 0;
            font-size: 14px;
        }
        .modal-close {
            border: none;
            background: transparent;
            cursor: pointer;
            font-size: 16px;
        }
        .modal-section {
            margin-bottom: 12px;
        }
        .modal-section-title {
            font-weight: 600;
            margin-bottom: 6px;
        }
        .modal-radio-row {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
      
    </style>
    <script>
        mermaid.initialize({ startOnLoad: false });

        const HELP_TEXT_HTML = `
        <h2 style="margin-top:0;">mAutoFlow – Help</h2>

        <p>
            mAutoFlow converts C / pseudo-C functions into a structured flowchart.
            The left side is the source editor and the right side is the diagram viewer.
            Code and nodes are synchronized in both directions.
        </p>

        <h3>1. Basic Concept</h3>
        <ul>
            <li>mAutoFlow focuses on <strong>a single function</strong> at a time.</li>
            <li>When you type or paste C code on the left, mAutoFlow finds a function.</li>
            <li>The body of the selected function is analyzed and rendered as a flowchart on the right.</li>
            <li>
                Use the <strong>HELP</strong> button in the top-right toolbar to switch between
                <strong>Code view</strong> and <strong>Help view</strong>.
                When Help is open, the button label becomes <strong>CODE</strong>; click it again to return to the editor.
            </li>
        </ul>

        <h3>2. Writing / Pasting Code</h3>
        <ul>
            <li>Paste normal C code or pseudo-C code into the editor.</li>
            <li>Function prototypes and global variables are allowed; mAutoFlow focuses on the chosen function body.</li>
            <li>Supported constructs:
                <ul>
                    <li><code>if / else if / else</code></li>
                    <li><code>for</code>, <code>while</code>, <code>do…while</code></li>
                    <li><code>switch / case / default</code></li>
                    <li><code>return</code>, <code>break</code>, <code>continue</code></li>
                    <li>Simple assignments and expressions (e.g. <code>x++;</code>, <code>flag = true;</code>)</li>
                </ul>
            </li>
            <li>Very complex or unusual syntax may not be visualized perfectly, 
                but the main control flow should still appear.</li>
        </ul>

        <h3>3. Automatic Refresh</h3>
        <ul>
            <li>mAutoFlow watches your typing in the left editor.</li>
            <li>After a short idle delay, the flowchart is automatically regenerated.</li>
            <li>If you do not want to wait, press <strong>“Regenerate Now”</strong> to force an immediate update.</li>
        </ul>

        <h3>4. Code ⇄ Flowchart Synchronization</h3>
        <ul>
            <li><strong>From code to flowchart</strong>:
                <ul>
                    <li>Click a line in the editor (or move the caret).</li>
                    <li>The best-matching node in the chart is highlighted in red.</li>
                    <li>The diagram view automatically scrolls to keep the node visible.</li>
                </ul>
            </li>
            <li><strong>From flowchart to code</strong>:
                <ul>
                    <li>Click a node on the diagram.</li>
                    <li>The corresponding line in the editor is selected.</li>
                    <li>The editor scrolls so the line is centered vertically.</li>
                    <li>“start / end / merge” nodes are ignored to avoid meaningless jumps.</li>
                </ul>
            </li>
            <li>A fuzzy matching algorithm is used, so minor formatting differences are tolerated.</li>
        </ul>

        <h3>5. Zooming & Panning the Diagram</h3>
        <ul>
            <li>Use the buttons in the Flowchart header:
                <ul>
                    <li><strong>−</strong>: zoom out</li>
                    <li><strong>100%</strong>: reset zoom</li>
                    <li><strong>+</strong>: zoom in</li>
                </ul>
            </li>
            <li><strong>Ctrl + mouse wheel</strong> over the diagram zooms as well.</li>
            <li><strong>Left-drag</strong> to pan when the chart is larger than the viewport.</li>
            <li>The current zoom level is shown on the right side of the toolbar.</li>
        </ul>

        <h3>6. Downloading the Diagram</h3>
        <ul>
            <li>Click the <strong>DOWNLOAD</strong> button in the top-right toolbar.</li>
            <li>The current flowchart is exported as an <strong>SVG</strong> file.</li>
            <li>File name is based on the current function name (e.g. <code>MyFunction.svg</code>).</li>
            <li>SVG is resolution-independent and ideal for documents and high-quality printing.</li>
        </ul>

        <h3>7. Themes</h3>
        <ul>
            <li>Open <strong>SETTINGS</strong> from the top-right toolbar.</li>
            <li>You can choose:
                <ul>
                    <li><strong>Classic</strong> – default colors & layout</li>
                    <li><strong>Light</strong> – light UI suitable for bright environments</li>
                    <li><strong>Dark</strong> – dark UI optimized for low-light work</li>
                </ul>
            </li>
            <li>Your selection is saved in local storage and restored next time.</li>
        </ul>

        <h3>8. Typical Workflow</h3>
        <ol>
            <li>Paste a function from your C project into the editor.</li>
            <li>Wait for automatic refresh or click “Regenerate Now”.</li>
            <li>Inspect the resulting flowchart.</li>
            <li>Click nodes to jump directly to code.</li>
            <li>Modify code to simplify logic or conditions.</li>
            <li>Download SVG for documentation or design reviews.</li>
        </ol>

        <h3>9. Example Code Snippet</h3>
        <pre style="background:#111827; color:#e5e7eb; padding:8px; border-radius:4px; font-size:12px; overflow:auto;">
        void main(void)
        {
            int x = 0;

            if (x == 0)
            {
                x++;
            }
            else
            {
                x--;
            }
        }
        </pre>
        <p>
            Paste this sample into the editor and observe how mAutoFlow renders the branches.
            Try modifying conditions or adding loops to see dynamic updates.
        </p>

        <h3>10. Notes & Limitations</h3>
        <ul>
            <li>mAutoFlow focuses on <strong>control flow</strong>, not a full C compiler.</li>
            <li>Complicated macros or vendor-specific extensions may not be shown perfectly.</li>
            <li>If a function body cannot be detected, mAutoFlow displays an error message.</li>
            <li>Extremely long single-line statements may reduce matching accuracy.</li>
        </ul>

        <h3>11. Branch Shape Options</h3>
        <p>
            mAutoFlow allows customizing how <strong>conditional branches</strong> (<code>if / else-if / switch</code>)
            are displayed in the flowchart.
        </p>

        <ul>
            <li>Open <strong>SETTINGS → Branch Shape</strong></li>
            <li>Choose between:
                <ul>
                    <li><strong>Rounded Rectangle</strong> – default (traditional flowchart style)</li>
                    <li><strong>Diamond</strong> – classic decision symbol</li>
                </ul>
            </li>
            <li>The next time you regenerate the diagram, the new shape will be applied.</li>
        </ul>

        <p style="margin-top:16px; font-size:12px; opacity:0.8;">
            Tip: choose Rounded for compact readability, or Diamond for classic flowchart notation.
        </p>
        `;
   

        let isHelpMode = false;
        let currentBranchShape = "rounded";   // 분기 모양: 기본은 둥근 사각형
        let savedSourceCode = "";             // HELP 진입 전 코드 저장용

        function toggleHelp() {
            const codeArea   = document.getElementById("codeArea");
            const codeHeader = document.getElementById("codeHeader");
            const btn        = document.getElementById("helpToggleBtn");

            if (!codeArea || !codeHeader || !btn) return;

            if (!isHelpMode) {
                // === HELP 모드 진입 ===
                // 현재 코드 저장
                const srcNow = document.getElementById("src");
                if (srcNow) {
                    savedSourceCode = srcNow.value;
                } else {
                    savedSourceCode = "";
                }

                isHelpMode = true;
                btn.textContent = "CODE";

                codeHeader.innerHTML = "<span>HELP</span>";
                codeArea.innerHTML = `
                    <div id="helpContent" style="padding:10px; color:var(--code-text); font-size:13px; overflow-y:auto;">
                        ${HELP_TEXT_HTML}
                    </div>
                `;
            } else {
                // === CODE 모드 복귀 ===
                isHelpMode = false;
                btn.textContent = "HELP";

                codeHeader.innerHTML = `
                    <span>mAutoFlow</span>
                    <span style="opacity:0.7;">Automatic analysis</span>
                `;

                // 에디터 다시 만들기
                codeArea.innerHTML = `
                    <textarea id="src" spellcheck="false" placeholder="Paste your C / pseudo-C code here."></textarea>
                `;

                // 저장해둔 코드 복원
                const src = document.getElementById("src");
                if (src) {
                    src.value = savedSourceCode || "";

                    // 기존 이벤트 다시 연결
                    ["click", "keyup", "mouseup"].forEach(ev => {
                        src.addEventListener(ev, updateNodeHighlightFromCaret);
                    });
                    src.addEventListener("input", function() {
                        if (typingTimer) clearTimeout(typingTimer);
                        typingTimer = setTimeout(function() {
                            generateFlowchart(true);
                        }, TYPING_DELAY_MS);
                    });
                }
            }
        }

        // ============================
        //  Theme 관리
        // ============================
        let currentTheme = "classic"; // 기본
        
        function applyTheme(theme) {
            currentTheme = theme;

            // classic 은 data-theme 제거 (기본 색 사용)
            if (theme === "classic") {
                document.body.removeAttribute("data-theme");
            } else {
                document.body.setAttribute("data-theme", theme);
            }

            // 로컬 스토리지에 저장
            try {
                localStorage.setItem("autoflow-theme", theme);
            } catch (e) {
                // storage 못쓸 때는 그냥 무시
            }
        }

        function openSettings() {
            const overlay = document.getElementById("settingsOverlay");
            if (!overlay) return;
            overlay.classList.remove("modal-hidden");
        }

        function closeSettings() {
            const overlay = document.getElementById("settingsOverlay");
            if (!overlay) return;
            overlay.classList.add("modal-hidden");
        }

        // ============================
        //  Download 헬퍼들
        // ============================

        // 현재 함수 이름 기준으로 파일명 만들기
        function getCurrentFilename(ext) {
            const labelEl = document.getElementById("currentFunc");
            let base = "autoflow_diagram";

            if (labelEl && labelEl.textContent) {
                const txt = labelEl.textContent;

                // "함수: Foo()" 또는 "Function : Foo()" 둘 다 지원
                const m = txt.match(/(?:함수|Function)\s*:\s*([^(]+)/);
                if (m && m[1]) {
                    base = m[1].trim();
                }
            }
            return base + "." + ext;
        }

        function triggerDownload(url, filename) {
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }

        // SVG 다운로드
        function downloadAsSVG() {
            const svg = document.querySelector("#chartInner svg");
            if (!svg) {
                alert("다운로드할 플로우차트가 없습니다.");
                return;
            }

            const cloned = svg.cloneNode(true);
            cloned.setAttribute("xmlns", "http://www.w3.org/2000/svg");

            const serializer = new XMLSerializer();
            const source = serializer.serializeToString(cloned);
            const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
            const url = URL.createObjectURL(blob);

            triggerDownload(url, getCurrentFilename("svg"));
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        }

        // 다운로드 타입에 따라 분기
        function downloadDiagram() {
            downloadAsSVG();
        }

        let typingTimer = null;
        const TYPING_DELAY_MS = 600;

        // 다이어그램 줌 상태 (내용만 확대, 레이아웃은 그대로)
        let diagramZoom = 1.0;

        function clampZoom(z) {
            if (z < 0.5) return 0.5;   // 50%
            if (z > 7.0) return 7.0;   // 700%
            return z;
        }
        function updateZoomLabel() {
            const label = document.getElementById("zoomLabel");
            label.textContent = Math.round(diagramZoom * 100) + "%";
        }

        // 공통 적용 함수
        function applyDiagramZoom() {
            const svg = document.querySelector("#chartInner svg");
            if (!svg) return;

            // 다이어그램의 기준 크기(100%)를 기준으로 확대/축소
            const percent = diagramZoom * 100;
            svg.style.width = percent + "%";
            svg.style.height = "auto";
        }

        // 플로우차트 컨테이너 안에서 노드를 화면 가운데로 스크롤
        function scrollNodeIntoCenter(node) {
            const container = document.getElementById("chartContainer");
            if (!node || !container) return;

            try {
                // 실제 화면 좌표(줌, 스크롤 모두 반영된 상태)
                const nodeRect = node.getBoundingClientRect();
                const contRect = container.getBoundingClientRect();

                const nodeCenterX = nodeRect.left + nodeRect.width  / 2;
                const nodeCenterY = nodeRect.top  + nodeRect.height / 2;
                const contCenterX = contRect.left + contRect.width  / 2;
                const contCenterY = contRect.top  + contRect.height / 2;

                // 컨테이너의 현재 스크롤 기준으로, 중심 차이만큼 더해줌
                container.scrollLeft += (nodeCenterX - contCenterX);
                container.scrollTop  += (nodeCenterY - contCenterY);
            } catch (e) {
                // getBoundingClientRect 실패하면 그냥 무시
                console.warn("scrollNodeIntoCenter error:", e);
            }
        }
        
        function zoomChange(delta) {
            diagramZoom = clampZoom(diagramZoom + delta);
            applyDiagramZoom();       // ← zoom 적용
            updateZoomLabel();
        }
        function zoomReset() {
            diagramZoom = 1.0;
            applyDiagramZoom();       // ← 100%로
            updateZoomLabel();
        }

        // ============================
        //  코드 라인 하이라이트 관련 함수들
        // ============================

        // 매칭용 문자열 정규화 (공백/괄호/세미콜론 등 정리)
        function normalizeForMatch(s) {
            if (!s) return "";
            return String(s)
                .toLowerCase()
                .replace(/["']/g, "")       // 따옴표 제거
                .replace(/[{};]/g, "")      // 중괄호/세미콜론 제거
                .replace(/\s+/g, " ")       // 여러 공백 -> 한 칸
                .trim();
        }

        // ============================
        //  코드 라인 → 노드 하이라이트
        // ============================

        // 선택된 노드 하이라이트 해제
        function clearNodeHighlight() {
            const svg = document.querySelector("#chartInner svg");
            if (!svg) return;
            svg.querySelectorAll(".node.autoflow-selected").forEach(n => {
                n.classList.remove("autoflow-selected");
            });
        }

        // 노드 라벨에서 "핵심 한 줄"만 뽑기 (if 줄 + 대입문 같이 있을 때 대비)
        function getNodeLabelCore(node) {
            const rawText = (node.textContent || "").trim();
            if (!rawText) return "";

            if (rawText.indexOf("\n") !== -1) {
                const parts = rawText.split(/\n/).map(p => p.trim()).filter(Boolean);
                if (parts.length > 0) {
                    // 가장 짧은 한 줄을 대표 라벨로 사용
                    return parts.reduce((a, b) => (a.length <= b.length ? a : b));
                }
            }
            return rawText;
        }

        // 현재 줄과 노드 라벨의 매칭 점수 계산
        function calcMatchScore(normLine, normLabel) {
            if (!normLine || !normLabel) return 0;

            if (normLine === normLabel) return 3.0;  // 완전 일치 최우선

            if (normLine.indexOf(normLabel) !== -1) {
                // 라벨이 줄 안에 포함
                return normLabel.length / Math.max(1, normLine.length);
            }
            if (normLabel.indexOf(normLine) !== -1) {
                // 줄이 라벨 안에 포함
                return normLine.length / Math.max(1, normLabel.length);
            }
            return 0;
        }

        // 특정 라인 번호에 매핑된 "가장 잘 맞는" 노드를 찾아 하이라이트 + 스크롤
        function highlightNodesForLine(lineIdx) {
            const svg = document.querySelector("#chartInner svg");
            if (!svg) return;

            const textarea = document.getElementById("src");
            if (!textarea) return;

            const code = textarea.value || "";
            const lines = code.split("\n");
            if (!lines.length) return;

            // 라인 인덱스 보정
            let idx = lineIdx;
            if (idx < 0) idx = 0;
            if (idx >= lines.length) idx = lines.length - 1;

            const normLine = normalizeForMatch(lines[idx]);
            if (!normLine) {
                clearNodeHighlight();
                return;
            }

            const nodeLines = window.__nodeLines || {};

            clearNodeHighlight();

            const nodes = svg.querySelectorAll(".node");
            const container = document.getElementById("chartContainer");

            let bestNode = null;
            let bestScore = 0;
            let bestDist = Infinity;

            nodes.forEach(node => {
                const rawId = node.getAttribute("id") || "";
                const m = rawId.match(/(?:flowchart-)?(N\d+)/);
                if (!m) return;
                const nodeKey = m[1];   // N1, N2 ...

                const mappedLine = nodeLines[nodeKey];

                const coreLabel = getNodeLabelCore(node);
                const normLabel = normalizeForMatch(coreLabel);
                if (!normLabel) return;

                const score = calcMatchScore(normLine, normLabel);
                if (score <= 0) return;   // 전혀 안 맞으면 후보 제외

                // body_start_line 한 칸 오차 같은 경우를 위해 "라인 거리"도 같이 고려
                const dist = (typeof mappedLine === "number")
                    ? Math.abs(mappedLine - idx)
                    : Infinity;

                if (
                    score > bestScore ||
                    (score === bestScore && dist < bestDist)
                ) {
                    bestScore = score;
                    bestDist = dist;
                    bestNode = node;
                }
            });

            if (!bestNode) return;

            bestNode.classList.add("autoflow-selected");

            // 줌 상태와 상관없이, 항상 화면 중앙으로 가져오기
            scrollNodeIntoCenter(bestNode);
        }

        // 텍스트 커서 위치 기준으로 현재 라인 계산 → 노드 하이라이트
        function updateNodeHighlightFromCaret() {
            const textarea = document.getElementById("src");
            if (!textarea) return;

            const pos = textarea.selectionStart || 0;
            const textBefore = textarea.value.slice(0, pos);
            const lineIdx = textBefore.split("\n").length - 1;

            highlightNodesForLine(lineIdx);
        }

        // lineIdx 주변에서 라벨과 가장 잘 맞는 줄을 찾아서 하이라이트
        // -> 최종 선택한 라인 인덱스를 반환
        function highlightCodeAtLine(lineIdx, rawLabel) {
            const textarea = document.getElementById("src");
            if (!textarea) return -1;

            const code = textarea.value;
            const lines = code.split("\n");
            if (!lines.length) return -1;

            // 기본 인덱스 범위 보정
            let idx = lineIdx;
            if (idx < 0) idx = 0;
            if (idx >= lines.length) idx = lines.length - 1;

            const normLabel = normalizeForMatch(rawLabel);

            // node_lines 가 가리키는 줄이 라벨과 안 맞으면,
            // 주변 몇 줄(±4줄) 안에서 라벨과 제일 잘 매칭되는 줄을 다시 찾는다.
            if (normLabel) {
                const normBase = normalizeForMatch(lines[idx]);
                const baseOK =
                    normBase === normLabel ||
                    normBase.indexOf(normLabel) !== -1 ||
                    normLabel.indexOf(normBase) !== -1;

                if (!baseOK) {
                    let bestIdx = idx;
                    let found = false;
                    const MAX_OFFSET = 4;  // 위/아래 4줄까지 검색

                    for (let d = 1; d <= MAX_OFFSET && !found; d++) {
                        const candidates = [];
                        if (idx - d >= 0) candidates.push(idx - d);
                        if (idx + d < lines.length) candidates.push(idx + d);

                        for (const i of candidates) {
                            const nl = normalizeForMatch(lines[i]);
                            if (!nl) continue;

                            if (
                                nl === normLabel ||
                                nl.indexOf(normLabel) !== -1 ||
                                normLabel.indexOf(nl) !== -1
                            ) {
                                bestIdx = i;
                                found = true;
                                break;
                            }
                        }
                    }

                    idx = bestIdx;
                }
            }

            // 최종 선택된 idx 라인 하이라이트
            let start = 0;
            for (let i = 0; i < idx; i++) {
                start += lines[i].length + 1; // '\n' 포함
            }
            const end = start + lines[idx].length;

            textarea.focus();
            textarea.setSelectionRange(start, end);

            const ratio = idx / Math.max(1, lines.length - 1);
            const targetScroll = textarea.scrollHeight * ratio - textarea.clientHeight / 2;
            textarea.scrollTop = Math.max(0, targetScroll);

            return idx;  // ✅ 최종 라인 번호 반환
        }


        // 노드 라벨 + (선택) 대략 라인 위치 힌트로 코드 라인 하이라이트
        // -> 찾은 라인 인덱스를 반환 (없으면 -1)
        function highlightCodeForLabel(rawLabel, approxLineHint) {
            const textarea = document.getElementById("src");
            if (!textarea) return -1;

            const code = textarea.value;
            if (!code) return -1;

            const lines = code.split("\n");

            // Mermaid가 한 노드에 여러 줄 텍스트를 넣는 경우 대비:
            //    - if 줄 + 대입문이 같이 들어오면, 보통 "대입문"이 더 짧음
            //    - 그래서 줄바꿈 기준으로 나눠서 "가장 짧은 한 줄"만 선택
            let core = rawLabel || "";
            if (core.indexOf("\n") !== -1) {
                const parts = core.split(/\n/).map(p => p.trim()).filter(Boolean);
                if (parts.length > 0) {
                    core = parts.reduce((a, b) => (a.length <= b.length ? a : b));
                }
            }

            let label = normalizeForMatch(core);
            if (!label) return -1;

            // 너무 길면 앞 부분만 사용 (매칭용)
            if (label.length > 120) {
                label = label.slice(0, 120);
            }

            // 1) 정확히 같은 줄(eqCandidates)과
            // 2) 부분 일치(subCandidates)를 따로 모은다.
            const eqCandidates = [];
            const subCandidates = [];

            for (let i = 0; i < lines.length; i++) {
                const normLine = normalizeForMatch(lines[i]);
                if (!normLine) continue;

                if (normLine === label) {
                    // 🔹 완전 일치 라인
                    eqCandidates.push(i);
                } else {
                    // 🔹 부분 일치 (이건 정확 일치가 하나도 없을 때만 사용할 예정)
                    if (
                        normLine.indexOf(label) !== -1 ||      // 라인 안에 라벨 문자열 포함
                        (label.indexOf(normLine) !== -1 && normLine.length > 5)
                    ) {
                        subCandidates.push(i);
                    }
                }
            }

            let bestLine = -1;
            let candidates = [];

            // 1순위: "정확 일치" 후보가 있으면 그것만 사용
            if (eqCandidates.length > 0) {
                candidates = eqCandidates;
            }
            // 2순위: 정확 일치가 하나도 없을 때만 부분 일치 사용
            else if (subCandidates.length > 0) {
                candidates = subCandidates;
            }

            if (candidates.length > 0) {
                // 2) 노드 Y좌표로부터 추정한 라인 가까운 것 우선 선택
                if (typeof approxLineHint === "number" && !Number.isNaN(approxLineHint)) {
                    let minDist = Infinity;
                    candidates.forEach(idx => {
                        const d = Math.abs(idx - approxLineHint);
                        if (d < minDist) {
                            minDist = d;
                            bestLine = idx;
                        }
                    });
                } else {
                    // 힌트 없으면 첫 번째 후보 사용
                    bestLine = candidates[0];
                }
            } else {
                // 3) 그래도 못 찾으면, 라인별 유사도 기반으로 "가장 비슷한" 한 줄을 찾는다.
                let bestScore = 0;
                let bestIdx = -1;

                for (let i = 0; i < lines.length; i++) {
                    const normLine = normalizeForMatch(lines[i]);
                    if (!normLine) continue;

                    const lenLine = normLine.length;
                    const lenLabel = label.length;
                    let score = 0;

                    if (normLine === label) {
                        score = 1.0;
                    } else if (normLine.indexOf(label) !== -1) {
                        // label 이 라인 안에 포함
                        score = label.length / lenLine;
                    } else if (label.indexOf(normLine) !== -1) {
                        // 반대로 라인이 label 안에 포함
                        score = lenLine / lenLabel;
                    } else {
                        continue;
                    }

                    if (score > bestScore) {
                        bestScore = score;
                        bestIdx = i;
                    }
                }

                if (bestScore > 0) {
                    bestLine = bestIdx;
                }
            }

            if (bestLine < 0 || bestLine >= lines.length) return -1;

            // 선택할 문자열의 시작/끝 인덱스 계산
            let start = 0;
            for (let i = 0; i < bestLine; i++) {
                start += lines[i].length + 1; // '\n' 포함
            }
            const end = start + lines[bestLine].length;

            // 텍스트 영역에 선택/포커스
            textarea.focus();
            textarea.setSelectionRange(start, end);

            // 대략적인 스크롤 위치 조정
            const totalLines = lines.length;
            const ratio = bestLine / Math.max(1, totalLines - 1);
            const targetScroll = textarea.scrollHeight * ratio - textarea.clientHeight / 2;
            textarea.scrollTop = Math.max(0, targetScroll);

            return bestLine;
        }

        // Mermaid 노드에 클릭 핸들러 연결
        function attachNodeClickHandlers() {
            const svg = document.querySelector("#chartInner svg");
            if (!svg) return;

            const nodeLines = window.__nodeLines || {};
            const textarea = document.getElementById("src");

            const nodes = svg.querySelectorAll(".node");
            nodes.forEach(node => {
                node.style.cursor = "pointer";
                node.addEventListener("click", () => {
                    if (!textarea) return;

                    // 추가: 노드 하이라이트는 “내가 클릭한 이 노드”로 고정
                    clearNodeHighlight();
                    node.classList.add("autoflow-selected");
                    scrollNodeIntoCenter(node);

                    // Mermaid가 노드 id를 보통 'flowchart-N1' 같은 형태로 만듦
                    const rawId = node.getAttribute("id") || "";
                    let nodeKey = rawId;
                    const m = rawId.match(/(?:flowchart-)?(N\d+)/);
                    if (m) {
                        nodeKey = m[1];   // N1, N2 ...
                    }

                    // 노드에 표시된 텍스트
                    const rawText = node.textContent || "";
                    let label = rawText.replace(/\s+/g, " ").trim();
                    if (!label) return;

                    const lower = label.toLowerCase();
                    if (lower === "merge") return;
                    if (lower.startsWith("start")) return;
                    if (lower.startsWith("end")) return;

                    // 1) node_lines 라인 번호가 있으면 우선 사용하되,
                    //    내용이 안 맞으면 문자열 매칭으로 다시 찾는 fallback 사용
                    const mapped = nodeLines[nodeKey];
                    if (typeof mapped === "number") {
                        const finalIdx = highlightCodeAtLine(mapped, label);  // 코드 쪽 하이라이트만
                        if (finalIdx < 0) {
                            // 라인 매핑이 애매하면 문자열 기반 fallback
                            highlightCodeForLabel(label, mapped);
                        }
                        return;
                    }

                    // -----------------------------
                    // 2) node_lines 정보가 없으면 문자열 매칭으로 찾기
                    // -----------------------------
                    const bestLine = highlightCodeForLabel(label, null);
                    // 코드만 하이라이트하면 충분, 따로 그래프 노드 선택 다시 안 함
                });
            });
        }

        async function generateFlowchart(auto=false) {
            const src = document.getElementById("src").value;
            const status = document.getElementById("status");
            const chartInner = document.getElementById("chartInner");
            const currentFunc = document.getElementById("currentFunc");

            // 새 코드/재생성 시마다 줌을 100%로 초기화
            diagramZoom = 1.0;
            updateZoomLabel();            

            if (!src.trim()) {
                if (!auto) {
                    status.textContent = "Enter the C code on the left.";
                    status.className = "error";
                } else {
                    status.textContent = "";
                    status.className = "";
                }
                currentFunc.textContent = "";
                chartInner.innerHTML = '<p class="placeholder">When you enter C code on the left, a flowchart is automatically generated on the right.</p>';
                return;
            }

            status.textContent = auto ? "Automatically updating..." : "Creating a flowchart...";
            status.className = "";
            chartInner.innerHTML = "";

            const formData = new FormData();
            formData.append("source_code", src);
            formData.append("branch_shape", currentBranchShape);

            try {
                const res = await fetch("/api/convert_text", {
                    method: "POST",
                    body: formData
                });

                if (!res.ok) {
                    status.textContent = "Server error: " + res.status;
                    status.className = "error";
                    chartInner.innerHTML = '<p class="placeholder">A server error occurred.</p>';
                    currentFunc.textContent = "";
                    return;
                }

                const data = await res.json();
                const mermaidCode = data.mermaid || "";
                const errorMsg = data.error || "";
                const funcName = data.func_name || "";
                const nodeLines = data.node_lines || {};

                // === 노드 개수 계산 ===
                const nodeCount = Object.keys(nodeLines).length;

                // node count 전역 저장(나중에 결제 제한 등에 사용)
                window.__nodeCount = nodeCount;

                // === Automatic analysis → Node: XX 로 변경 ===
                const codeHeader = document.getElementById("codeHeader");
                if (codeHeader) {
                    codeHeader.innerHTML = `
                        <span>mAutoFlow</span>
                        <span style="opacity:0.7;">Nodes: ${nodeCount}</span>
                    `;
                }

                // 노드 -> 라인번호 맵을 전역에 저장 (click 핸들러에서 사용)
                window.__nodeLines = nodeLines;

                if (errorMsg) {
                    status.textContent = "Error: " + errorMsg;
                    status.className = "error";
                    chartInner.innerHTML = '<p class="placeholder" style="color:#b91c1c;">' + errorMsg + '</p>';
                    currentFunc.textContent = "";
                    return;
                }

                if (!mermaidCode.trim()) {
                    status.textContent = "The code is empty. Please check that the function is correct.";
                    status.className = "error";
                    chartInner.innerHTML = '<p class="placeholder">The body of the function could not be found.</p>';
                    currentFunc.textContent = "";
                    return;
                }

                status.textContent = auto ? "Refresh Complete." : "Flowchart creation complete.";
                status.className = "success";
                currentFunc.textContent = funcName ? ("Function: " + funcName + "()") : "";

                chartInner.innerHTML = '<div class="mermaid">' + mermaidCode + '</div>';
                const element = chartInner.querySelector(".mermaid");
                mermaid.init(undefined, element);

                applyDiagramZoom();

                // Mermaid 렌더링 후 노드 클릭 핸들러 연결
                setTimeout(attachNodeClickHandlers, 50);
                
            } catch (err) {
                console.error(err);
                status.textContent = "An error occurred during the request.";
                status.className = "error";
                chartInner.innerHTML = '<p class="placeholder" style="color:#b91c1c;">An error occurred during the request.</p>';
                currentFunc.textContent = "";
            }
        }

        function setupSplitDrag() {
            const main = document.querySelector(".main");
            const leftPane = document.getElementById("leftPane");
            const rightPane = document.getElementById("rightPane");
            const divider = document.getElementById("divider");

            let isDragging = false;

            divider.addEventListener("mousedown", function(e) {
                e.preventDefault();
                isDragging = true;
                document.body.style.cursor = "col-resize";
            });

            document.addEventListener("mousemove", function(e) {
                if (!isDragging) return;
                const rect = main.getBoundingClientRect();
                const totalWidth = rect.width;
                let offsetX = e.clientX - rect.left;
                // 최소/최대 비율 제한 (20% ~ 70%)
                let leftPercent = Math.max(0.2, Math.min(0.7, offsetX / totalWidth));
                let rightPercent = 1 - leftPercent;

                leftPane.style.flex = "0 0 " + (leftPercent * 100).toFixed(1) + "%";
                rightPane.style.flex = "0 0 " + (rightPercent * 100).toFixed(1) + "%";
            });

            document.addEventListener("mouseup", function() {
                if (isDragging) {
                    isDragging = false;
                    document.body.style.cursor = "default";
                }
            });
        }

        document.addEventListener("DOMContentLoaded", function() {
            const src = document.getElementById("src");
            const lineNumbers = document.getElementById("lineNumbers");

            // 라인 번호 업데이트 함수
            function updateLineNumbers() {
                if (!src || !lineNumbers) return;
                const lines = src.value.split("\n").length || 1;
                let html = "";
                for (let i = 1; i <= lines; i++) {
                    html += i + "<br>";
                }
                lineNumbers.innerHTML = html;
            }

            // 이벤트 연결 (입력/스크롤)
            if (src && lineNumbers) {
                src.addEventListener("input", updateLineNumbers);
                src.addEventListener("scroll", () => {
                    lineNumbers.scrollTop = src.scrollTop;  // 스크롤 동기화
                });
                updateLineNumbers(); // 초기 1,2,3,... 표시
            }

            // ----- 초기 테마 로딩 -----
            let savedTheme = "classic";
            try {
                const t = localStorage.getItem("autoflow-theme");
                if (t) savedTheme = t;
            } catch (e) {}
            applyTheme(savedTheme);

            // 라디오 버튼 상태 동기화
            const themeRadios = document.querySelectorAll('input[name="theme"]');
            themeRadios.forEach(r => {
                if (r.value === savedTheme) {
                    r.checked = true;
                }
                r.addEventListener("change", (e) => {
                    if (e.target.checked) {
                        applyTheme(e.target.value);
                        // 테마 바뀌면 플로우차트도 다시 그려주고 싶으면:
                        // generateFlowchart(true);
                    }
                });
            });

            // Branch Shape 초기화
            let savedBranchShape = "rounded";
            try {
                const bs = localStorage.getItem("autoflow-branch-shape");
                if (bs) savedBranchShape = bs;
            } catch (e) {}
            currentBranchShape = savedBranchShape;

            const branchRadios = document.querySelectorAll('input[name="branchShape"]');
            branchRadios.forEach(r => {
                if (r.value === savedBranchShape) {
                    r.checked = true;
                }
                r.addEventListener("change", (e) => {
                    if (e.target.checked) {
                        currentBranchShape = e.target.value;
                        try {
                            localStorage.setItem("autoflow-branch-shape", currentBranchShape);
                        } catch (e2) {}
                        // 필요하면 테마처럼 자동 재생성도 가능:
                        generateFlowchart(true);
                    }
                });
            });

            updateZoomLabel();
            setupSplitDrag();

            // 코드 → 노드 하이라이트 연동
            ["click", "keyup", "mouseup"].forEach(ev => {
                src.addEventListener(ev, updateNodeHighlightFromCaret);
            });            

            // 우측 플로우차트 영역에서 Ctrl+휠로 그림만 줌
            const chartContainer = document.getElementById("chartContainer");
            chartContainer.addEventListener("wheel", function(e) {
                // Ctrl 키가 눌려 있지 않으면 그냥 스크롤
                if (!e.ctrlKey) return;

                // 브라우저의 기본 페이지 줌 막기
                e.preventDefault();

                // deltaY < 0 이면 휠 위로(확대), > 0 이면 아래로(축소)
                if (e.deltaY < 0) {
                    zoomChange(+0.1);
                } else if (e.deltaY > 0) {
                    zoomChange(-0.1);
                }
            }, { passive: false });

            // 🔹 좌클릭 드래그로 패닝
            let isPanning = false;
            let startX = 0;
            let startY = 0;
            let startScrollLeft = 0;
            let startScrollTop = 0;

            chartContainer.addEventListener("mousedown", function(e) {
                if (e.button !== 0) return; // 왼쪽 버튼만
                isPanning = true;
                startX = e.clientX;
                startY = e.clientY;
                startScrollLeft = chartContainer.scrollLeft;
                startScrollTop = chartContainer.scrollTop;
                e.preventDefault(); // 텍스트 선택 방지
            });

            document.addEventListener("mousemove", function(e) {
                if (!isPanning) return;
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;
                chartContainer.scrollLeft = startScrollLeft - dx;
                chartContainer.scrollTop = startScrollTop - dy;
            });

            document.addEventListener("mouseup", function() {
                isPanning = false;
            });            


            // 타이핑 자동 업데이트 (debounce)
            src.addEventListener("input", function() {
                if (typingTimer) clearTimeout(typingTimer);
                typingTimer = setTimeout(function() {
                    generateFlowchart(true);
                }, TYPING_DELAY_MS);
            });
            
            // 코드 클릭/이동 시 → 해당 라인 노드 하이라이트
            src.addEventListener("click", updateNodeHighlightFromCaret);
            src.addEventListener("keyup", updateNodeHighlightFromCaret);
            src.addEventListener("mouseup", updateNodeHighlightFromCaret);    
        });
    </script>
</head>
<body>
    <header>
        <div>
            <h1>mAutoFlow</h1>
            <div class="subtitle">When you enter C code on the left, a flowchart is automatically generated on the right.</div>
        </div>
        <div class="topbar-right">
            <button class="btn-settings" onclick="downloadDiagram()">DOWNLOAD</button>
            <button class="btn-settings" onclick="openSettings()">SETTINGS</button>
            <button id="helpToggleBtn" class="btn-settings" onclick="toggleHelp()">HELP</button>
        </div>
    </header>
    <div class="main">
        <div id="leftPane">
            <div class="pane-header">
                <span class="pane-title">Source Code</span>
            </div>
            <div id="codeContainer">
                <div id="codeHeader">
                    <span>mAutoFlow</span>
                    <span style="opacity:0.7;">Automatic analysis</span>
                </div>
                <div id="codeArea">
                    <div id="lineNumbers"></div>
                    <textarea id="src" spellcheck="false" placeholder="Example:
void main(void)
{
    int x = 0;

    if (x == 0)
    {
        x++;
    }
    else
    {
        x--;
    }
}"></textarea>
                </div>
            </div>
        </div>

        <div id="divider"></div>

        <div id="rightPane">
            <div class="pane-header">
                <span class="pane-title">Flowchart</span>
                <div style="display:flex; align-items:center; gap:6px;">
                    <button class="btn btn-ghost" onclick="zoomChange(-0.1)">−</button>
                    <button class="btn btn-ghost" onclick="zoomReset()">100%</button>
                    <button class="btn btn-ghost" onclick="zoomChange(0.1)">+</button>
                    <span class="zoom-label" id="zoomLabel"></span>
                </div>
            </div>
            <div id="toolbar">
                <button class="btn btn-primary" onclick="generateFlowchart(false)">Regenerate Now</button>
                <span id="currentFunc"></span>
                <span id="status"></span>
            </div>
            <div id="chartContainer">
                <div id="chartInner">
                    <p class="placeholder">
                        When you enter C code on the left, a flowchart is automatically generated on the right.
                    </p>
                </div>
            </div>
        </div>
    </div>
    <!-- SETTINGS 모달: 여기 추가 -->
    <div id="settingsOverlay" class="modal-overlay modal-hidden">
        <div class="modal-panel">
            <div class="modal-header">
                <h2>SETTINGS</h2>
                <button class="modal-close" onclick="closeSettings()">×</button>
            </div>

            <!-- Theme 섹션 -->
            <div class="modal-section">
                <div class="modal-section-title">Theme</div>
                <div class="modal-radio-row">
                    <label>
                        <input type="radio" name="theme" value="classic" checked />
                        Classic (Current style)
                    </label>
                    <label>
                        <input type="radio" name="theme" value="light" />
                        Light
                    </label>
                    <label>
                        <input type="radio" name="theme" value="dark" />
                        Dark
                    </label>
                </div>
            </div>

            <!-- Branch Shape 섹션 추가 -->
            <div class="modal-section">
                <div class="modal-section-title">Branch Shape</div>
                <div class="modal-radio-row">
                    <label>
                        <input type="radio" name="branchShape" value="rounded" checked />
                        Rounded (Stadium / Rounded rectangle)
                    </label>
                    <label>
                        <input type="radio" name="branchShape" value="diamond" />
                        Diamond
                    </label>
                </div>
            </div>

            <div style="text-align:right; margin-top:10px; font-size:12px;">
                <button class="btn btn-ghost" onclick="closeSettings()">Close</button>
            </div>
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.post("/api/convert_text")
async def convert_c_text_to_mermaid(
    source_code: str = Form(...),
    branch_shape: str = Form("rounded"),
):
    try:
        mermaid, func_name, node_lines = generate_mermaid_auto(
            source_code,
            branch_shape=branch_shape
        )
        return JSONResponse(
            {
                "mermaid": mermaid,
                "func_name": func_name,
                "node_lines": node_lines,
            }
        )
    except Exception as e:
        return JSONResponse({"mermaid": "", "func_name": "", "error": str(e)})


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
