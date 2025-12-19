# ByteDance UI-TARS 1.5-7b Comprehensive UI Testing

## Overview

This directory contains comprehensive UI testing scripts using **ByteDance UI-TARS 1.5-7b** model with **OpenRouter API** for intelligent visual analysis of the Dumont Cloud system.

## What is UI-TARS?

**UI-TARS** (Understanding User Interface - Towards Assistive Retrieval Systems) is a vision model optimized for understanding and analyzing user interfaces. It can:

- 🎯 Detect UI elements (buttons, forms, tables, etc.)
- 📊 Analyze page layouts and structure
- ✅ Verify functionality through visual analysis
- 🤖 Generate intelligent insights about UX/UI
- 📋 Create detailed reports with recommendations

## Files

### 1. `ui_tars_comprehensive_test.py`
Standalone comprehensive test suite without external API dependency.

**Features:**
- Full page testing (Navigation, Forms, Content, etc.)
- Performance metrics
- Accessibility checks
- Responsive design testing (Desktop, Tablet, Mobile)
- Error handling verification
- Generates JSON and Markdown reports

**Usage:**
```bash
python ui_tars_comprehensive_test.py
```

**Output:**
- `/tmp/ui_tars_test_report.json` - Detailed JSON report
- `/tmp/ui_tars_test_report.md` - Markdown report

### 2. `ui_tars_openrouter.py`
AI-powered testing using ByteDance UI-TARS via OpenRouter API.

**Features:**
- 🤖 AI visual analysis of every page
- Screenshot-based element detection
- Intelligent functionality assessment
- AI-generated insights and recommendations
- Integrates with OpenRouter for API calls

**Setup:**
```bash
# Set your OpenRouter API key
export OPENROUTER_API_KEY="your-api-key-here"

# Or add to ~/.bashrc or ~/.env
echo 'export OPENROUTER_API_KEY="your-key"' >> ~/.bashrc
```

**Usage:**
```bash
python ui_tars_openrouter.py
```

**Output:**
- `/tmp/ui_tars_openrouter_report.json` - AI analysis report
- `/tmp/ui_tars_openrouter_report.md` - Formatted markdown report

## Test Coverage

Both tests cover the following pages:

1. **Login/Landing Page**
   - Demo mode functionality
   - Form elements
   - Call-to-action visibility

2. **Dashboard**
   - Navigation menu
   - Cards and widgets
   - Search/Wizard button
   - Interactive elements

3. **Machines Page**
   - List/table structure
   - Filter functionality
   - Action buttons
   - Status indicators

4. **Metrics Page**
   - Charts and graphs
   - Metric cards
   - Date pickers
   - Data visualization

5. **Navigation Flow**
   - Link functionality
   - Page transitions
   - Menu navigation

6. **Form Interactions**
   - Input fields
   - Button clicks
   - Form submission

## Test Metrics

### Performance Testing
- Page load time
- Network metrics (DNS, TCP, TTFB)
- Render performance

### Functionality Testing
- Navigation links
- Form inputs
- Button interactions
- Page responsiveness

### Accessibility Testing
- ARIA labels
- Alt text for images
- Keyboard navigation
- Screen reader compatibility

### UI Element Detection
- Headings, paragraphs, images
- Forms, inputs, buttons
- Cards, lists, tables
- Navigation elements

## Report Generation

### JSON Report Format
```json
{
  "timestamp": "2025-12-19T...",
  "model": "bytedance/ui-tars-1.5-7b",
  "summary": {
    "total_pages": 4,
    "total_screenshots": 10,
    "ai_insights": 8,
    "issues_found": 2
  },
  "ai_analysis": [...],
  "screenshots": [...],
  "detailed_findings": {
    "ui_elements": [...],
    "functionality_tests": [...],
    "issues": [...]
  }
}
```

### Markdown Report Format
- Executive summary
- Page-by-page analysis
- AI insights
- Functionality test results
- Issues and recommendations

## Running Tests

### Quick Test (No API)
```bash
# Run comprehensive tests without AI
python ui_tars_comprehensive_test.py

# Check results
cat /tmp/ui_tars_test_report.md
```

### Full Test with AI Analysis
```bash
# Set API key first
export OPENROUTER_API_KEY="your-openrouter-api-key"

# Run AI-powered tests
python ui_tars_openrouter.py

# View AI insights
cat /tmp/ui_tars_openrouter_report.md
```

### Test Specific Pages
Edit the test files to uncomment specific test functions:

```python
# In ui_tars_openrouter.py
async def run_all_tests(self):
    # Uncomment only the tests you want to run
    # await self.test_login_page(page)
    # await self.test_dashboard(page)
    await self.test_metrics_page(page)  # Only metrics
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Run UI-TARS Tests
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
  run: |
    python tests/ui-tars-test/ui_tars_openrouter.py

- name: Upload Test Reports
  uses: actions/upload-artifact@v3
  with:
    name: ui-test-reports
    path: /tmp/ui_tars_*_report.*
```

### GitLab CI Example
```yaml
ui-tars-tests:
  stage: test
  script:
    - export OPENROUTER_API_KEY=$OPENROUTER_API_KEY
    - python tests/ui-tars-test/ui_tars_openrouter.py
  artifacts:
    paths:
      - /tmp/ui_tars_*_report.*
```

## Sample Output

### Console Output
```
================================================================================
🚀 ByteDance UI-TARS 1.5-7b with OpenRouter - Comprehensive UI Test Suite
   Testing: Dumont Cloud
================================================================================

📄 TESTING LOGIN PAGE
================================================================================
🤖 Analyzing login_page with UI-TARS...
✅ Analysis complete
   The login page features a clean, minimalist design...

📊 TESTING DASHBOARD
================================================================================
🤖 Analyzing dashboard with UI-TARS...
✅ Analysis complete
   Dashboard contains 23 interactive cards, a navigation menu...

⚙️  TESTING MACHINES PAGE
================================================================================
...

📊 TEST SUMMARY
================================================================================
✅ Total Pages Tested:        4
📸 Total Screenshots:         10
🤖 AI Insights Generated:     8
🚨 Issues Found:              2
💡 Recommendations:           5
```

## Troubleshooting

### OpenRouter API Issues
```bash
# Check API key
echo $OPENROUTER_API_KEY

# Test API connection
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  https://openrouter.io/api/v1/models
```

### Screenshot Issues
- Ensure server is running on `http://localhost:8000`
- Check browser permissions for screenshots
- Verify `/tmp` directory exists and is writable

### Test Timeouts
- Increase timeout values in test files
- Check server response times
- Verify network connectivity

## API Pricing

OpenRouter pricing for ByteDance UI-TARS:
- Input: $X per 1M tokens
- Output: $Y per 1M tokens
- Each screenshot analysis uses ~500-1000 tokens

## Best Practices

1. **Run tests regularly** - Especially before releases
2. **Monitor trends** - Track performance over time
3. **Fix issues promptly** - Address detected problems
4. **Update recommendations** - Implement AI suggestions
5. **Integrate with CI/CD** - Automate testing pipeline

## Advanced Usage

### Custom Analysis Prompts
Edit the `analysis_prompt` in test functions:

```python
prompt = """Custom analysis focused on:
1. Specific feature verification
2. UX patterns
3. Accessibility compliance
4. Performance metrics
"""
```

### Batch Testing
Run multiple test scenarios:

```python
test_scenarios = [
    ("http://localhost:8000/?demo=true", "Landing"),
    ("http://localhost:8000/app?demo=true", "Dashboard"),
    # Add more...
]

for url, name in test_scenarios:
    await test_page(page, url, name)
```

## Resources

- [ByteDance UI-TARS Model](https://github.com/bytedance/ui-tars)
- [OpenRouter API Docs](https://openrouter.io/docs)
- [Playwright Documentation](https://playwright.dev)
- [UI Testing Best Practices](https://www.sauceLabs.com/blog/ui-testing)

## Support

For issues or questions:
1. Check test logs in `/tmp/`
2. Enable verbose mode for debugging
3. Review OpenRouter API status
4. Check server availability

## License

These tests are part of the Dumont Cloud project.

---

**Last Updated:** December 2025
**Version:** 1.0
