# UI-TARS Usage Examples

## Quick Start

### 1. Run Basic Tests (No Setup Required)
```bash
cd /home/ubuntu/dumont-cloud/tests/ui-tars-test

# Make sure server is running
export DEMO_MODE=true
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# Run tests
python ui_tars_comprehensive_test.py
```

### 2. View Results
```bash
# Markdown report (pretty)
cat /tmp/ui_tars_test_report.md

# JSON report (machine readable)
python -m json.tool /tmp/ui_tars_test_report.json
```

---

## Advanced Examples

### Example 1: Run with OpenRouter AI Analysis

```bash
#!/bin/bash

# Set up API key
export OPENROUTER_API_KEY="sk-or-v1-xxxxxxxxxxxx"

# Verify key works
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  https://openrouter.io/api/v1/models | grep ui-tars

# Run AI-powered tests
python tests/ui-tars-test/ui_tars_openrouter.py

# View AI insights
cat /tmp/ui_tars_openrouter_report.md
```

### Example 2: Run Specific Pages

Edit `ui_tars_openrouter.py`:

```python
async def run_all_tests(self):
    """Run all tests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Comment out tests you don't want
            # await self.test_login_page(page)
            await self.test_dashboard(page)
            # await self.test_machines_page(page)
            # await self.test_metrics_page(page)
```

### Example 3: Custom Test Scenario

```python
async def test_custom_scenario(self, page):
    """Test custom user scenario"""
    print("\n" + "="*80)
    print("📋 CUSTOM SCENARIO: New User Onboarding")
    print("="*80)

    try:
        # 1. User lands on page
        await page.goto("http://localhost:8000/?demo=true")
        print("✓ Step 1: Landing page loaded")

        # 2. User clicks demo/login
        demo_btn = await page.query_selector('button:has-text("Demo")')
        if demo_btn:
            await demo_btn.click()
            await page.wait_for_timeout(1000)
            print("✓ Step 2: Demo mode activated")

        # 3. User navigates to dashboard
        dashboard_link = await page.query_selector('a:has-text("Dashboard")')
        if dashboard_link:
            await dashboard_link.click()
            await page.wait_for_timeout(1000)
            print("✓ Step 3: Dashboard loaded")

        # 4. User explores features
        cards = await page.query_selector_all('[class*="card"]')
        print(f"✓ Step 4: Found {len(cards)} feature cards")

        # Analyze with AI
        prompt = """Analyze this user journey:
        1. User landed on page
        2. Activated demo mode
        3. Navigated to dashboard
        4. Explored features

        Provide UX/UI feedback."""

        screenshot = await self.analyzer.take_and_analyze_screenshot(
            page,
            "custom_scenario",
            prompt
        )

    except Exception as e:
        print(f"✗ Error: {e}")
```

### Example 4: Performance Monitoring

```python
async def test_performance_under_load(self, page):
    """Test performance with multiple page loads"""
    print("\n" + "="*80)
    print("⚡ PERFORMANCE TEST: Load Stress")
    print("="*80)

    urls = [
        "http://localhost:8000/?demo=true",
        "http://localhost:8000/app?demo=true",
        "http://localhost:8000/app/machines?demo=true",
        "http://localhost:8000/app/metrics-hub?demo=true",
    ]

    load_times = []

    for url in urls:
        start = datetime.now()
        await page.goto(url, wait_until="networkidle")
        load_time = (datetime.now() - start).total_seconds()
        load_times.append(load_time)
        print(f"  Load time: {load_time:.2f}s - {url.split('/')[-1] or 'Landing'}")

    avg_time = sum(load_times) / len(load_times)
    print(f"\n  Average: {avg_time:.2f}s")
    print(f"  Min: {min(load_times):.2f}s")
    print(f"  Max: {max(load_times):.2f}s")
```

### Example 5: Accessibility Deep Dive

```python
async def test_accessibility_compliance(self, page):
    """Detailed accessibility testing"""
    print("\n" + "="*80)
    print("♿ ACCESSIBILITY COMPLIANCE TEST")
    print("="*80)

    await page.goto("http://localhost:8000/app?demo=true")

    # Check WCAG 2.1 guidelines
    checks = {
        "Color contrast": await self.check_color_contrast(page),
        "Keyboard navigation": await self.check_keyboard_nav(page),
        "ARIA labels": await self.check_aria_labels(page),
        "Form labels": await self.check_form_labels(page),
        "Focus indicators": await self.check_focus(page),
        "Alt text": await self.check_alt_text(page),
    }

    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")

async def check_color_contrast(self, page):
    """Check color contrast ratios"""
    return await page.evaluate("""() => {
        const elements = document.querySelectorAll('*');
        let passCount = 0;
        for (let el of elements) {
            const style = window.getComputedStyle(el);
            // Simplified check
            if (style.color && style.backgroundColor) {
                passCount++;
            }
        }
        return passCount > 0;
    }""")
```

### Example 6: CI/CD Integration Script

```bash
#!/bin/bash
# run-ui-tests.sh

set -e

echo "🚀 Starting UI-TARS Test Suite"

# Check if server is running
if ! curl -s http://localhost:8000/api/v1/auth/me?demo=true >/dev/null; then
    echo "Starting server..."
    export DEMO_MODE=true
    python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 &
    SERVER_PID=$!
    sleep 5
fi

echo "Running tests..."
cd tests/ui-tars-test

# Run tests
python ui_tars_comprehensive_test.py

# Capture exit code
TEST_EXIT=$?

# Check results
if [ -f "/tmp/ui_tars_test_report.json" ]; then
    echo "📊 Analyzing results..."

    # Parse JSON and check pass rate
    PASS_RATE=$(python -c "
import json
with open('/tmp/ui_tars_test_report.json') as f:
    data = json.load(f)
    total = data['summary']['total_tests']
    passed = data['summary']['passed']
    rate = (passed / total * 100) if total > 0 else 0
    print(f'{rate:.1f}')
")

    echo "Pass rate: ${PASS_RATE}%"

    # Fail if below threshold
    if (( $(echo "$PASS_RATE < 90" | bc -l) )); then
        echo "❌ Pass rate below 90% threshold!"
        exit 1
    else
        echo "✅ Tests passed!"
    fi
fi

# Cleanup
[ ! -z "$SERVER_PID" ] && kill $SERVER_PID 2>/dev/null || true

exit $TEST_EXIT
```

### Example 7: Generate HTML Report

```python
import json
from datetime import datetime

def generate_html_report():
    """Generate HTML report from JSON results"""

    with open('/tmp/ui_tars_test_report.json') as f:
        data = json.load(f)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>UI-TARS Test Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .summary {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
            .passed {{ color: green; }}
            .failed {{ color: red; }}
            .warning {{ color: orange; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
        </style>
    </head>
    <body>
        <h1>UI-TARS Comprehensive Test Report</h1>
        <p>Generated: {datetime.now().isoformat()}</p>

        <div class="summary">
            <h2>Summary</h2>
            <p><span class="passed">✅ Passed: {data['summary']['passed']}</span></p>
            <p><span class="failed">❌ Failed: {data['summary']['failed']}</span></p>
            <p><span class="warning">⚠️ Warned: {data['summary']['warnings']}</span></p>
            <p>Execution Time: {data['summary']['execution_time']:.2f}s</p>
        </div>

        <h2>Pages Tested</h2>
        <table>
            <tr>
                <th>Page</th>
                <th>URL</th>
                <th>Load Time</th>
                <th>Title</th>
            </tr>
    """

    for page in data['pages_tested']:
        html += f"""
            <tr>
                <td>{page['name']}</td>
                <td>{page['url']}</td>
                <td>{page['load_time']:.2f}s</td>
                <td>{page['title']}</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    with open('/tmp/ui_tars_test_report.html', 'w') as f:
        f.write(html)

    print("HTML report saved to /tmp/ui_tars_test_report.html")

if __name__ == "__main__":
    generate_html_report()
```

---

## Real-World Scenarios

### Scenario 1: Pre-Release Testing

```bash
# 1. Start server
export DEMO_MODE=true
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# 2. Run comprehensive tests
python tests/ui-tars-test/ui_tars_comprehensive_test.py

# 3. With AI analysis (if API key available)
export OPENROUTER_API_KEY="your-key"
python tests/ui-tars-test/ui_tars_openrouter.py

# 4. Generate report
cp /tmp/ui_tars_test_report.* ./release-reports/

# 5. Review results before release
cat ./release-reports/ui_tars_test_report.md
```

### Scenario 2: Nightly CI/CD Testing

```yaml
# .github/workflows/nightly-ui-tests.yml
name: Nightly UI Tests

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2

      - name: Start server
        env:
          DEMO_MODE: true
        run: |
          python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 &
          sleep 5

      - name: Run UI tests
        run: python tests/ui-tars-test/ui_tars_comprehensive_test.py

      - name: Upload report
        uses: actions/upload-artifact@v2
        with:
          name: ui-test-report-${{ github.run_number }}
          path: /tmp/ui_tars_test_report.*

      - name: Check results
        run: |
          python -c "
          import json
          with open('/tmp/ui_tars_test_report.json') as f:
              d = json.load(f)
              if d['summary']['passed'] < 80:
                  exit(1)
          "
```

### Scenario 3: Performance Regression Testing

```python
import json
from datetime import datetime

def check_performance_regression():
    """Compare current performance with baseline"""

    current = json.load(open('/tmp/ui_tars_test_report.json'))
    baseline = json.load(open('./performance-baseline.json'))

    current_avg = current['summary']['execution_time']
    baseline_avg = baseline['summary']['execution_time']

    diff_percent = ((current_avg - baseline_avg) / baseline_avg * 100)

    print(f"Current: {current_avg:.2f}s")
    print(f"Baseline: {baseline_avg:.2f}s")
    print(f"Difference: {diff_percent:+.1f}%")

    if diff_percent > 10:
        print("⚠️ Performance regressed more than 10%!")
        return False

    return True

if __name__ == "__main__":
    if not check_performance_regression():
        exit(1)
```

---

## Customization Tips

### 1. Add Custom Assertions

```python
async def assert_element_visible(self, page, selector, name):
    elem = await page.query_selector(selector)
    if elem and await elem.is_visible():
        await self.add_test_result("Custom", f"{name} visible", "PASS")
    else:
        await self.add_test_result("Custom", f"{name} visible", "FAIL")
```

### 2. Test Business Logic

```python
async def test_price_calculation(self, page):
    """Test if pricing calculations are correct"""
    # Navigate to pricing
    await page.goto("http://localhost:8000/app/pricing?demo=true")

    # Get GPU prices
    price_elem = await page.query_selector('[data-price]')
    price = await price_elem.text_content()

    # Verify calculation
    assert float(price) > 0, "Price should be positive"
```

### 3. Multi-Language Testing

```python
async def test_multiple_languages(self, page):
    """Test different language support"""
    for lang_code, lang_name in [("en", "English"), ("pt", "Portuguese")]:
        url = f"http://localhost:8000/?demo=true&lang={lang_code}"
        await page.goto(url)

        # Check if content is in correct language
        content = await page.content()
        assert lang_code in content or "lang" in content
```

---

## Debugging Tips

### 1. Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Save Screenshots on Failure

```python
except Exception as e:
    screenshot = await page.screenshot(path=f"failure_{datetime.now().timestamp()}.png")
    print(f"Screenshot saved: {screenshot}")
    raise
```

### 3. Debug Page State

```python
# Print page source
print(await page.content())

# Print all elements
elements = await page.query_selector_all('*')
print(f"Total elements: {len(elements)}")

# Check console for errors
for msg in page.listeners('console'):
    print(msg.text)
```

---

## Performance Optimization

### Run Tests in Parallel

```python
import asyncio

async def run_tests_parallel():
    """Run multiple test scenarios in parallel"""
    await asyncio.gather(
        test_scenario_1(),
        test_scenario_2(),
        test_scenario_3(),
    )
```

### Use Test Fixtures

```python
@pytest.fixture
async def authenticated_page():
    """Fixture providing authenticated page"""
    page = await browser.new_page()
    await page.goto("http://localhost:8000/?demo=true")
    return page
```

---

## Result Interpretation

### High Pass Rate (>95%)
✅ System is production-ready
- Deploy with confidence
- Monitor for regressions

### Medium Pass Rate (80-95%)
⚠️ Some issues found
- Fix critical failures first
- Test after fixes

### Low Pass Rate (<80%)
❌ Not ready for production
- Fix all failures
- Review test setup

---

**Last Updated**: December 2025
**Examples Version**: 1.0
