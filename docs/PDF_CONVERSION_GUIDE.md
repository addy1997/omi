# Convert Technical Design Document to PDF

## Files Generated

### Primary Documents
- **`TECHNICAL_DESIGN_WITH_DIAGRAMS.html`** ⭐ **← USE THIS ONE FOR PDF**
  - HTML document with all 4 professional SVG diagrams embedded
  - Ready for print-to-PDF conversion
  - Size: 42 KB
  - File: `/mnt/d/dev/addy_wp/omi/TECHNICAL_DESIGN_WITH_DIAGRAMS.html`

### Alternative Formats
- `TECHNICAL_DESIGN.md` — Markdown source (48 KB)
- `TECHNICAL_DESIGN.html` — HTML version without embedded diagrams (31 KB)

### Diagrams (SVG Files)
Located in `/mnt/d/dev/addy_wp/omi/diagrams/`:
1. `01-architecture.svg` — High-level system architecture (7.1 KB)
2. `02-routing.svg` — Task routing decision tree (5.5 KB)
3. `03-agent-lifecycle.svg` — Agent lifecycle state machine (5.2 KB)
4. `04-execution-lifecycle.svg` — Task execution lifecycle (5.7 KB)

---

## How to Convert to PDF

### Option 1: Browser Print-to-PDF (Easiest) ✅

1. **Open the HTML file in your browser:**
   ```bash
   # On Windows
   start /mnt/d/dev/addy_wp/omi/TECHNICAL_DESIGN_WITH_DIAGRAMS.html
   
   # On macOS
   open /mnt/d/dev/addy_wp/omi/TECHNICAL_DESIGN_WITH_DIAGRAMS.html
   
   # On Linux
   firefox /mnt/d/dev/addy_wp/omi/TECHNICAL_DESIGN_WITH_DIAGRAMS.html
   ```

2. **Print to PDF:**
   - Press `Ctrl+P` (Windows/Linux) or `Cmd+P` (macOS)
   - Select "Save as PDF" as the printer
   - Click "Save"
   - Choose: `/mnt/d/dev/addy_wp/omi/TECHNICAL_DESIGN.pdf`

3. **PDF Settings (Recommended):**
   - Margins: Default (0.5 inch)
   - Paper size: A4 or Letter
   - Scale: 100%
   - Background graphics: ✓ Enabled (for diagrams)

---

### Option 2: Command Line (Linux/macOS)

#### Using wkhtmltopdf:
```bash
# Install (if not already)
# macOS: brew install --cask wkhtmltopdf
# Ubuntu: sudo apt-get install wkhtmltopdf
# Windows: Download from https://wkhtmltopdf.org/

wkhtmltopdf /mnt/d/dev/addy_wp/omi/TECHNICAL_DESIGN_WITH_DIAGRAMS.html /mnt/d/dev/addy_wp/omi/TECHNICAL_DESIGN.pdf
```

#### Using Puppeteer (Node.js):
```bash
npm install -g puppeteer-cli

puppeteer print /mnt/d/dev/addy_wp/omi/TECHNICAL_DESIGN_WITH_DIAGRAMS.html /mnt/d/dev/addy_wp/omi/TECHNICAL_DESIGN.pdf
```

---

### Option 3: Online Converters

If you don't have PDF tools installed, use:
- **CloudConvert:** https://cloudconvert.com/html-to-pdf
- **Zamzar:** https://www.zamzar.com/convert/html-to-pdf/
- **Online-Convert:** https://document.online-convert.com/convert-to-pdf

1. Upload `TECHNICAL_DESIGN_WITH_DIAGRAMS.html`
2. Select PDF as output format
3. Download the converted PDF

---

## Document Contents

### Sections (11 major sections)
1. **Executive Summary** — Platform overview
2. **Architectural Principles** — Core principles & trade-offs
3. **System Components** — Detailed component breakdown
4. **API Contracts** — All REST & WebSocket endpoints
5. **Task Routing Flow** — 4-level routing cascade
6. **Task Execution Lifecycle** — 8-step execution process
7. **Architecture Diagrams** — 4 professional SVG diagrams
8. **Security & Compliance** — Auth, network, input validation
9. **Scaling & Deployment** — Single to multi-instance paths
10. **Extension Points** — Customization possibilities
11. **Key Metrics & SLOs** — Performance targets

### Embedded Diagrams

**Figure 1: High-Level System Architecture**
- Shows client layer, platform components, agents
- Illustrates information flow and component relationships

**Figure 2: Task Routing Decision Tree**
- Demonstrates 4-level routing cascade
- Shows decision points and failure paths

**Figure 3: Agent Lifecycle State Machine**
- Agent states: UNREGISTERED → ONLINE → OFFLINE → DEREGISTERED
- Transitions and triggers

**Figure 4: Task Execution Lifecycle**
- 8-step execution process from submission to result storage
- Shows database interactions and success/failure paths

---

## PDF Quality Tips

### For Best Results:
1. **Use Chrome, Firefox, or Edge** — They have the best print-to-PDF engines
2. **Check "Background graphics"** — Required for colored diagrams
3. **Use A4 or Letter size** — Standard dimensions
4. **100% scale** — Ensures readability
5. **Disable headers/footers** — Optional, keeps content clean

### Output Specifications:
- **Format:** PDF/A-1b (archival quality)
- **Font:** Embedded (Segoe UI, Arial)
- **Color:** Full RGB
- **Dimensions:** A4 (210×297 mm) or Letter (8.5×11 in)
- **File size:** ~3-5 MB (compressed SVG diagrams)

---

## Sharing the PDF

Once converted, the PDF can be:
- ✅ Printed directly to physical paper
- ✅ Shared via email (small file size)
- ✅ Uploaded to document repositories (Confluence, SharePoint, etc.)
- ✅ Embedded in presentations
- ✅ Added to project wikis
- ✅ Archived for compliance/records

---

## Troubleshooting

### "Diagrams not showing"
- Make sure "Background graphics" is enabled in print settings
- Check that SVGs are rendering in your browser (open in separate tab)

### "Formatting looks wrong"
- Try a different browser (Chrome is most reliable)
- Adjust margins to 0.5 inch
- Disable headers and footers

### "File is too large"
- Compress the PDF using an online tool (pdf-compress.com)
- Or use quality setting "Low" in wkhtmltopdf

---

## Document Metadata

| Property | Value |
|----------|-------|
| Title | Omi Platform — Technical Design Document |
| Version | 0.1.0 |
| Status | Active Development |
| Date | June 2026 |
| Pages | ~15-20 (varies by margins/scale) |
| Diagrams | 4 professional SVG diagrams |
| Language | English |

---

**Ready to convert?** Open `TECHNICAL_DESIGN_WITH_DIAGRAMS.html` in your browser and print to PDF! 📄
