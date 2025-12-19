"""
ByteDance UI-TARS 1.5-7b with OpenRouter
Comprehensive UI Testing with Vision AI Analysis
Navigates, captures screenshots, and uses AI to analyze UI elements and functionality
"""

import asyncio
import json
import base64
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import requests
from typing import Optional

# OpenRouter configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "bytedance/ui-tars-1.5-7b"  # UI-TARS model ID

TEST_REPORT = {
    "timestamp": datetime.now().isoformat(),
    "model": MODEL,
    "version": "1.0",
    "site_url": "http://localhost:8000",
    "ai_analysis": [],
    "screenshots": [],
    "pages": [],
    "summary": {
        "total_pages": 0,
        "total_screenshots": 0,
        "ai_insights": 0,
        "issues_found": 0,
        "recommendations": 0
    },
    "detailed_findings": {
        "ui_elements": [],
        "functionality_tests": [],
        "issues": [],
        "opportunities": []
    }
}

class OpenRouterUITARS:
    """UI-TARS with OpenRouter for visual analysis"""

    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Dumont Cloud UI Testing"
        })

    def analyze_screenshot(self, image_base64: str, prompt: str) -> Optional[dict]:
        """
        Send screenshot to UI-TARS via OpenRouter for analysis
        """
        if not self.api_key:
            print("⚠️  OpenRouter API key not configured. Skipping AI analysis.")
            print("   Set OPENROUTER_API_KEY environment variable to enable.")
            return None

        try:
            # Formato correto do OpenRouter para modelos de visão
            payload = {
                "model": MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1024
            }

            response = self.session.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "success",
                    "analysis": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    "model": result.get("model", MODEL),
                    "tokens": result.get("usage", {})
                }
            else:
                print(f"⚠️  API Error: {response.status_code}")
                return {
                    "status": "error",
                    "error": response.text,
                    "code": response.status_code
                }

        except Exception as e:
            print(f"⚠️  Analysis error: {e}")
            return None

    async def take_and_analyze_screenshot(self, page, page_name: str, analysis_prompt: str):
        """Take screenshot and analyze with UI-TARS"""
        try:
            # Take screenshot
            screenshot_path = f"/tmp/ui_tars_{page_name}_{datetime.now().timestamp()}.png"
            await page.screenshot(path=screenshot_path)

            # Read and encode to base64
            with open(screenshot_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode()

            # Store screenshot info
            screenshot_info = {
                "page": page_name,
                "path": screenshot_path,
                "timestamp": datetime.now().isoformat()
            }

            # Analyze with UI-TARS if API key available
            if self.api_key:
                print(f"\n🤖 Analyzing {page_name} with UI-TARS...")
                analysis = self.analyze_screenshot(image_base64, analysis_prompt)

                if analysis and analysis.get("status") == "success":
                    ai_finding = {
                        "page": page_name,
                        "analysis": analysis.get("analysis", ""),
                        "model": analysis.get("model"),
                        "tokens": analysis.get("tokens")
                    }
                    TEST_REPORT["ai_analysis"].append(ai_finding)
                    TEST_REPORT["summary"]["ai_insights"] += 1

                    print(f"✅ Analysis complete")
                    print(f"   {analysis.get('analysis', '')[:200]}...")
                else:
                    print(f"⚠️  Analysis failed")

            screenshot_info["analyzed"] = bool(self.api_key)
            TEST_REPORT["screenshots"].append(screenshot_info)
            TEST_REPORT["summary"]["total_screenshots"] += 1

            return screenshot_path

        except Exception as e:
            print(f"Error in screenshot analysis: {e}")
            return None


class UITARSComprehensiveTest:
    """Comprehensive UI testing with UI-TARS"""

    def __init__(self):
        self.analyzer = OpenRouterUITARS()
        self.start_time = datetime.now()

    async def dismiss_onboarding(self, page):
        """Dismiss onboarding overlay if present"""
        try:
            # Wait a bit for potential overlay to appear
            await page.wait_for_timeout(500)

            # Try multiple methods to close onboarding
            selectors = [
                'text=Pular tudo',
                'text=Skip',
                '.close-btn',
                'button[aria-label="Close"]',
                '.onboarding-overlay button:has-text("X")',
                '.onboarding-modal .close-btn'
            ]

            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.click()
                        print("  ✓ Dismissed onboarding overlay")
                        await page.wait_for_timeout(500)
                        return True
                except:
                    pass

            # Check if overlay exists and click outside to close
            overlay = await page.query_selector('.onboarding-overlay')
            if overlay:
                # Click on the overlay background (not the modal)
                await page.click('.onboarding-overlay', position={"x": 10, "y": 10})
                print("  ✓ Closed overlay by clicking outside")
                await page.wait_for_timeout(500)
                return True

        except Exception as e:
            print(f"  ℹ No onboarding overlay to dismiss: {e}")

        return False

    async def wait_for_page_ready(self, page, timeout=10000):
        """Wait for page to be fully loaded and interactive"""
        try:
            # Wait for network to be idle
            await page.wait_for_load_state('networkidle', timeout=timeout)
            # Wait for DOM to be ready
            await page.wait_for_load_state('domcontentloaded', timeout=timeout)
            # Small additional wait for React/Vue to hydrate
            await page.wait_for_timeout(300)
            return True
        except Exception as e:
            print(f"  ⚠ Page load timeout: {e}")
            return False

    async def safe_click(self, page, selector, retries=3, timeout=5000):
        """Click with retry logic and overlay handling"""
        for attempt in range(retries):
            try:
                # First dismiss any overlays
                await self.dismiss_onboarding(page)

                # Try to click
                element = await page.wait_for_selector(selector, timeout=timeout)
                if element:
                    # Check if element is visible and not obscured
                    is_visible = await element.is_visible()
                    if is_visible:
                        await element.click(timeout=timeout)
                        return True

            except Exception as e:
                if attempt < retries - 1:
                    print(f"  ⚠ Click attempt {attempt + 1} failed, retrying...")
                    await page.wait_for_timeout(500)
                else:
                    print(f"  ✗ Click failed after {retries} attempts: {e}")

        return False

    async def test_login_page(self, page):
        """Test login page elements and functionality"""
        print("\n" + "="*80)
        print("📄 TESTING LOGIN PAGE")
        print("="*80)

        try:
            # Use /demo-app for automatic demo mode
            await page.goto("http://localhost:8000/demo-app")
            await self.wait_for_page_ready(page)

            # Analyze login page
            prompt = """Analyze this login/landing page screenshot and provide:
1. List all visible UI elements (buttons, forms, text, etc.)
2. Identify the main call-to-action
3. Check if the login form is properly visible
4. Note any design or UX issues
5. Rate the overall layout quality (1-10)
Provide a structured analysis."""

            screenshot = await self.analyzer.take_and_analyze_screenshot(
                page,
                "login_page",
                prompt
            )

            # Check for specific elements
            email_input = await page.query_selector('input[type="email"]')
            password_input = await page.query_selector('input[type="password"]')
            login_button = await page.query_selector('button:has-text("Login"), button:has-text("Entrar")')
            demo_button = await page.query_selector('button:has-text("Demo"), a:has-text("Demo")')

            elements_found = []
            if email_input:
                elements_found.append("Email Input")
            if password_input:
                elements_found.append("Password Input")
            if login_button:
                elements_found.append("Login Button")
            if demo_button:
                elements_found.append("Demo Mode")

            TEST_REPORT["detailed_findings"]["ui_elements"].append({
                "page": "Login Page",
                "elements": elements_found,
                "screenshot": screenshot
            })

        except Exception as e:
            print(f"Error: {e}")
            TEST_REPORT["detailed_findings"]["issues"].append(f"Login page test error: {e}")

    async def test_dashboard(self, page):
        """Test dashboard page"""
        print("\n" + "="*80)
        print("📊 TESTING DASHBOARD")
        print("="*80)

        try:
            await page.goto("http://localhost:8000/demo-app")
            await self.wait_for_page_ready(page)
            await self.dismiss_onboarding(page)

            prompt = """Analyze this dashboard screenshot and provide:
1. Identify main sections/cards visible
2. List interactive elements (buttons, dropdowns, etc.)
3. Check the navigation menu
4. Assess data visualization elements
5. Note any responsiveness issues
6. Provide a functionality score (1-10)
Format as structured analysis."""

            screenshot = await self.analyzer.take_and_analyze_screenshot(
                page,
                "dashboard",
                prompt
            )

            # Find dashboard elements
            title = await page.query_selector('h1, h2')
            cards = await page.query_selector_all('[class*="card"], [class*="Card"]')
            menu_items = await page.query_selector_all('nav a, header a')
            search_button = await page.query_selector('button:has-text("Search"), button:has-text("Buscar")')

            TEST_REPORT["detailed_findings"]["ui_elements"].append({
                "page": "Dashboard",
                "elements": {
                    "title": await title.text_content() if title else "No title",
                    "cards": len(cards),
                    "menu_items": len(menu_items),
                    "has_search": search_button is not None
                },
                "screenshot": screenshot
            })

        except Exception as e:
            print(f"Error: {e}")
            TEST_REPORT["detailed_findings"]["issues"].append(f"Dashboard test error: {e}")

    async def test_machines_page(self, page):
        """Test machines page"""
        print("\n" + "="*80)
        print("⚙️  TESTING MACHINES PAGE")
        print("="*80)

        try:
            await page.goto("http://localhost:8000/demo-app/machines")
            await self.wait_for_page_ready(page)
            await self.dismiss_onboarding(page)

            prompt = """Analyze this machines/instances page screenshot and provide:
1. Identify the list/table structure
2. List visible columns/fields
3. Check for action buttons (edit, delete, etc.)
4. Look for filters or search functionality
5. Assess the overall layout
6. Note any missing features or improvements needed
Provide detailed structured feedback."""

            screenshot = await self.analyzer.take_and_analyze_screenshot(
                page,
                "machines_page",
                prompt
            )

            # Check page elements
            machine_list = await page.query_selector('[class*="machine"], [class*="list"]')
            filter_input = await page.query_selector('input[type="text"], [class*="filter"]')
            action_buttons = await page.query_selector_all('button:has-text("Edit"), button:has-text("Delete")')

            TEST_REPORT["detailed_findings"]["ui_elements"].append({
                "page": "Machines",
                "elements": {
                    "has_list": machine_list is not None,
                    "has_filter": filter_input is not None,
                    "action_buttons": len(action_buttons)
                },
                "screenshot": screenshot
            })

        except Exception as e:
            print(f"Error: {e}")
            TEST_REPORT["detailed_findings"]["issues"].append(f"Machines page test error: {e}")

    async def test_metrics_page(self, page):
        """Test metrics page"""
        print("\n" + "="*80)
        print("📈 TESTING METRICS PAGE")
        print("="*80)

        try:
            await page.goto("http://localhost:8000/demo-app/metrics-hub")
            await self.wait_for_page_ready(page)
            await self.dismiss_onboarding(page)

            prompt = """Analyze this metrics/analytics page screenshot and provide:
1. Identify charts and graphs present
2. List metric cards or statistics displayed
3. Check for date range selectors or filters
4. Assess data visualization quality
5. Look for export or download options
6. Rate the page informativeness (1-10)
Give a comprehensive analysis."""

            screenshot = await self.analyzer.take_and_analyze_screenshot(
                page,
                "metrics_page",
                prompt
            )

            # Check metrics elements
            charts = await page.query_selector_all('canvas, svg, [class*="chart"]')
            metric_cards = await page.query_selector_all('[class*="metric"], [class*="stat"]')
            date_picker = await page.query_selector('input[type="date"], [class*="date"]')

            TEST_REPORT["detailed_findings"]["ui_elements"].append({
                "page": "Metrics",
                "elements": {
                    "charts": len(charts),
                    "metric_cards": len(metric_cards),
                    "has_date_picker": date_picker is not None
                },
                "screenshot": screenshot
            })

        except Exception as e:
            print(f"Error: {e}")
            TEST_REPORT["detailed_findings"]["issues"].append(f"Metrics page test error: {e}")

    async def test_navigation_flow(self, page):
        """Test navigation between pages"""
        print("\n" + "="*80)
        print("🔗 TESTING NAVIGATION FLOW")
        print("="*80)

        try:
            # Test navigation from dashboard (using /demo-app)
            await page.goto("http://localhost:8000/demo-app")
            await self.wait_for_page_ready(page)
            await self.dismiss_onboarding(page)

            # Re-fetch nav items after dismissing overlay
            nav_items = await page.query_selector_all('nav a, aside a, [class*="sidebar"] a')

            functionality_test = {
                "name": "Navigation Flow",
                "tests": []
            }

            for i, nav_item in enumerate(nav_items[:5]):  # Test first 5 links
                try:
                    text = await nav_item.text_content()
                    href = await nav_item.get_attribute('href')

                    if not text or not text.strip():
                        continue

                    # Dismiss overlay before each click
                    await self.dismiss_onboarding(page)

                    # Check if element is visible
                    is_visible = await nav_item.is_visible()
                    if not is_visible:
                        print(f"  ⚠ {text.strip()} not visible, skipping")
                        continue

                    await nav_item.click(timeout=5000)
                    await self.wait_for_page_ready(page)

                    functionality_test["tests"].append({
                        "link": text.strip(),
                        "url": href,
                        "status": "clickable"
                    })

                    print(f"  ✓ Navigation to {text.strip()}")

                except Exception as e:
                    error_msg = str(e)[:100]  # Truncate long errors
                    functionality_test["tests"].append({
                        "link": text.strip() if text else "Unknown",
                        "status": "error",
                        "error": error_msg
                    })
                    print(f"  ✗ Error navigating: {error_msg}")

            TEST_REPORT["detailed_findings"]["functionality_tests"].append(functionality_test)

        except Exception as e:
            print(f"Navigation test error: {e}")
            TEST_REPORT["detailed_findings"]["issues"].append(f"Navigation test error: {e}")

    async def test_form_interactions(self, page):
        """Test form interactions"""
        print("\n" + "="*80)
        print("📝 TESTING FORM INTERACTIONS")
        print("="*80)

        try:
            await page.goto("http://localhost:8000/demo-app")
            await self.wait_for_page_ready(page)
            await self.dismiss_onboarding(page)

            inputs = await page.query_selector_all('input:not([type="hidden"]):visible')

            functionality_test = {
                "name": "Form Interactions",
                "tests": []
            }

            if len(inputs) > 0:
                test_input = inputs[0]

                try:
                    # Check if input is visible and interactable
                    is_visible = await test_input.is_visible()
                    if is_visible:
                        await test_input.focus()
                        await test_input.type("test_value")
                        value = await test_input.input_value()

                        functionality_test["tests"].append({
                            "action": "Input typing",
                            "status": "success",
                            "value": value
                        })

                        print(f"  ✓ Input interaction working")
                    else:
                        functionality_test["tests"].append({
                            "action": "Input typing",
                            "status": "skipped",
                            "reason": "Input not visible"
                        })
                        print(f"  ⚠ Input not visible, skipped")

                except Exception as e:
                    functionality_test["tests"].append({
                        "action": "Input typing",
                        "status": "failed",
                        "error": str(e)[:100]
                    })
                    print(f"  ✗ Input error: {str(e)[:50]}")

            # Find visible, enabled buttons that are not inside overlays
            buttons = await page.query_selector_all('button:not([disabled]):not(.close-btn)')

            for btn in buttons[:3]:  # Test first 3 buttons
                try:
                    is_visible = await btn.is_visible()
                    if not is_visible:
                        continue

                    btn_text = await btn.text_content()
                    await btn.click(timeout=3000)

                    functionality_test["tests"].append({
                        "action": f"Button click: {btn_text[:20] if btn_text else 'Unknown'}",
                        "status": "success"
                    })
                    print(f"  ✓ Button '{btn_text[:20] if btn_text else 'btn'}' clicked")
                    break  # One successful click is enough

                except Exception as e:
                    continue  # Try next button

            TEST_REPORT["detailed_findings"]["functionality_tests"].append(functionality_test)

        except Exception as e:
            print(f"Form interaction test error: {e}")
            TEST_REPORT["detailed_findings"]["issues"].append(f"Form test error: {e}")

    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*100)
        print("🚀 ByteDance UI-TARS 1.5-7b with OpenRouter - Comprehensive UI Test Suite")
        print("   Testing: Dumont Cloud")
        print("="*100)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Run all tests
                await self.test_login_page(page)
                await self.test_dashboard(page)
                await self.test_machines_page(page)
                await self.test_metrics_page(page)
                await self.test_navigation_flow(page)
                await self.test_form_interactions(page)

                # Update summary
                TEST_REPORT["summary"]["total_pages"] = len(TEST_REPORT["detailed_findings"]["ui_elements"])
                TEST_REPORT["summary"]["issues_found"] = len(TEST_REPORT["detailed_findings"]["issues"])

                # Save report
                self.save_report()

                # Print summary
                self.print_summary()

            finally:
                await browser.close()

    def save_report(self):
        """Save test report"""
        report_path = "/tmp/ui_tars_openrouter_report.json"

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(TEST_REPORT, f, indent=2, ensure_ascii=False)

        print(f"\n📄 JSON Report saved to: {report_path}")

        # Create markdown report
        markdown_report = self.generate_markdown_report()
        markdown_path = "/tmp/ui_tars_openrouter_report.md"

        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)

        print(f"📄 Markdown Report saved to: {markdown_path}")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*100)
        print("📊 TEST SUMMARY")
        print("="*100)

        summary = TEST_REPORT["summary"]
        print(f"\n✅ Total Pages Tested:        {summary['total_pages']}")
        print(f"📸 Total Screenshots:         {summary['total_screenshots']}")
        print(f"🤖 AI Insights Generated:     {summary['ai_insights']}")
        print(f"🚨 Issues Found:              {summary['issues_found']}")
        print(f"💡 Recommendations:           {summary['recommendations']}")

        if TEST_REPORT["detailed_findings"]["issues"]:
            print(f"\n🔴 Issues Detected:")
            for issue in TEST_REPORT["detailed_findings"]["issues"]:
                print(f"   • {issue}")

    def generate_markdown_report(self) -> str:
        """Generate markdown report"""
        md = "# ByteDance UI-TARS 1.5-7b Analysis Report\n\n"
        md += f"**Model:** {TEST_REPORT['model']}\n"
        md += f"**Timestamp:** {TEST_REPORT['timestamp']}\n"
        md += f"**Site:** {TEST_REPORT['site_url']}\n\n"

        md += "## Executive Summary\n\n"
        summary = TEST_REPORT["summary"]
        md += f"- Pages Tested: {summary['total_pages']}\n"
        md += f"- Screenshots Analyzed: {summary['total_screenshots']}\n"
        md += f"- AI Insights: {summary['ai_insights']}\n"
        md += f"- Issues Found: {summary['issues_found']}\n\n"

        md += "## UI Elements Analysis\n\n"
        for elem in TEST_REPORT["detailed_findings"]["ui_elements"]:
            md += f"### {elem['page']}\n\n"
            if isinstance(elem.get('elements'), dict):
                for key, value in elem['elements'].items():
                    md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
            else:
                for element in elem.get('elements', []):
                    md += f"- {element}\n"
            md += "\n"

        md += "## AI Analysis Results\n\n"
        if TEST_REPORT["ai_analysis"]:
            for analysis in TEST_REPORT["ai_analysis"]:
                md += f"### {analysis['page']}\n\n"
                md += f"{analysis['analysis']}\n\n"
        else:
            md += "_No AI analysis available (API key not configured)_\n\n"

        md += "## Functionality Tests\n\n"
        for func_test in TEST_REPORT["detailed_findings"]["functionality_tests"]:
            md += f"### {func_test['name']}\n\n"
            for test in func_test['tests']:
                status = "✅" if test.get('status') == 'success' or test.get('status') == 'clickable' else "❌"
                md += f"{status} {test}\n"
            md += "\n"

        md += "## Issues & Recommendations\n\n"
        if TEST_REPORT["detailed_findings"]["issues"]:
            md += "### Issues Found\n\n"
            for issue in TEST_REPORT["detailed_findings"]["issues"]:
                md += f"- {issue}\n"
            md += "\n"

        return md


async def main():
    """Main entry point"""
    tester = UITARSComprehensiveTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
