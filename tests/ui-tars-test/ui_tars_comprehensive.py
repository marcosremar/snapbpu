"""
UI-TARS Comprehensive Demo Mode Validation
Tests all UI scenarios: filters, actions, navigation, search, and API responses
"""

import asyncio
import json
import base64
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import requests
from typing import Optional, List, Dict

# OpenRouter configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "bytedance/ui-tars-1.5-7b"

# Test scenarios to validate
TEST_SCENARIOS = {
    "dashboard": {
        "url": "/demo-app",
        "checks": [
            "stats_cards_visible",
            "deploy_wizard_visible",
            "navigation_working",
            "demo_badge_visible"
        ]
    },
    "machines_all": {
        "url": "/demo-app/machines",
        "checks": [
            "machine_list_visible",
            "online_machines_count",
            "offline_machines_count",
            "filter_tabs_visible"
        ]
    },
    "machines_online_filter": {
        "url": "/demo-app/machines",
        "action": "click_online_filter",
        "checks": [
            "only_online_machines_visible",
            "correct_count"
        ]
    },
    "machines_offline_filter": {
        "url": "/demo-app/machines",
        "action": "click_offline_filter",
        "checks": [
            "only_offline_machines_visible",
            "correct_count"
        ]
    },
    "machine_actions": {
        "url": "/demo-app/machines",
        "checks": [
            "pause_button_visible",
            "migrate_button_visible",
            "vscode_button_visible",
            "snapshot_menu_visible"
        ]
    },
    "metrics_hub": {
        "url": "/demo-app/metrics-hub",
        "checks": [
            "metric_cards_visible",
            "navigation_working"
        ]
    },
    "settings": {
        "url": "/demo-app/settings",
        "checks": [
            "settings_form_visible",
            "save_button_visible"
        ]
    }
}

COMPREHENSIVE_REPORT = {
    "timestamp": datetime.now().isoformat(),
    "model": MODEL,
    "total_scenarios": len(TEST_SCENARIOS),
    "passed": 0,
    "failed": 0,
    "scenarios": [],
    "issues": [],
    "recommendations": []
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
        """Send screenshot to UI-TARS via OpenRouter for analysis"""
        if not self.api_key:
            print("⚠️  OpenRouter API key not configured.")
            return None

        try:
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
                "temperature": 0.3,
                "max_tokens": 2048
            }

            response = self.session.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "success",
                    "analysis": result["choices"][0]["message"]["content"]
                }
            else:
                return {"status": "error", "error": response.text}

        except Exception as e:
            return {"status": "error", "error": str(e)}


class ComprehensiveDemoTester:
    """Comprehensive testing of demo mode functionality"""

    def __init__(self):
        self.analyzer = OpenRouterUITARS()
        self.screenshots_dir = Path("/tmp/ui_tars_comprehensive")
        self.screenshots_dir.mkdir(exist_ok=True)

    async def wait_for_page_ready(self, page, timeout=15000):
        """Wait for page to be fully loaded"""
        try:
            await page.wait_for_load_state('networkidle', timeout=timeout)
            await page.wait_for_timeout(500)
            return True
        except:
            return False

    async def dismiss_onboarding(self, page):
        """Dismiss onboarding overlay if present"""
        try:
            selectors = [
                'text=Pular tudo',
                '.close-btn',
                'button:has-text("X")'
            ]
            for selector in selectors:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    await page.wait_for_timeout(500)
                    return True
        except:
            pass
        return False

    async def capture_and_analyze(self, page, scenario_name: str, prompt: str) -> dict:
        """Capture screenshot and analyze with UI-TARS"""
        screenshot_path = self.screenshots_dir / f"{scenario_name}.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)

        with open(screenshot_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode()

        print(f"  🤖 Analyzing {scenario_name}...")
        result = self.analyzer.analyze_screenshot(image_base64, prompt)

        return {
            "scenario": scenario_name,
            "screenshot": str(screenshot_path),
            "analysis": result
        }

    async def test_dashboard(self, page) -> dict:
        """Test Dashboard with stats cards and deploy wizard"""
        print("\n" + "="*80)
        print("📊 SCENARIO: Dashboard Overview")
        print("="*80)

        await page.goto("http://localhost:8000/demo-app")
        await self.wait_for_page_ready(page)
        await self.dismiss_onboarding(page)

        prompt = """Analyze this dashboard screenshot and answer these specific questions:

1. DEMO BADGE: Is there a "DEMO" badge/label visible in the header? (YES/NO)
2. STATS CARDS: Are there stat cards showing metrics like "Máquinas Ativas", "Custo Diário", "Economia", "Uptime"? List what you see.
3. DEPLOY WIZARD: Is there a deploy/create section with GPU options? (YES/NO)
4. REGION SELECTOR: Are there region buttons (EUA, Europa, Ásia, etc.)? (YES/NO)
5. NAVIGATION: List all navigation menu items visible.
6. USER EMAIL: What email is shown for the logged-in user?
7. ISSUES: List any UI issues, broken elements, or missing data.
8. SCORE: Rate the dashboard completeness from 1-10."""

        result = await self.capture_and_analyze(page, "dashboard_overview", prompt)

        # Additional programmatic checks
        checks = {
            "demo_badge": await page.query_selector('.demo-badge') is not None,
            "stats_cards": len(await page.query_selector_all('[class*="StatCard"], [class*="stat"]')) > 0,
            "navigation": len(await page.query_selector_all('nav a')) > 0
        }

        result["programmatic_checks"] = checks
        return result

    async def test_machines_list(self, page) -> dict:
        """Test Machines page with full list"""
        print("\n" + "="*80)
        print("🖥️  SCENARIO: Machines List (All)")
        print("="*80)

        await page.goto("http://localhost:8000/demo-app/machines")
        await self.wait_for_page_ready(page)
        await self.dismiss_onboarding(page)

        prompt = """Analyze this machines/instances page and answer:

1. MACHINE COUNT: How many machines are visible in the list? Count them.
2. ONLINE MACHINES: List the GPU names of machines showing "ONLINE" status.
3. OFFLINE MACHINES: List the GPU names of machines showing "OFFLINE" status.
4. FILTER TABS: Are there filter tabs like "Todas", "Online", "Offline"? What counts do they show?
5. MACHINE DETAILS: For each machine, what information is displayed? (GPU%, VRAM, Temp, Cost, etc.)
6. ACTION BUTTONS: What action buttons are visible? (VS Code, Pause, Migrate, etc.)
7. CPU BACKUP: Do any machines show CPU backup/standby information?
8. PRICING: What prices per hour are shown for each machine?
9. ISSUES: Any missing data, broken UI, or problems?
10. COMPLETENESS SCORE: Rate from 1-10."""

        result = await self.capture_and_analyze(page, "machines_all", prompt)

        # Count machines programmatically
        machine_cards = await page.query_selector_all('[class*="rounded-lg"][class*="border"]')
        online_badges = await page.query_selector_all('text=/ONLINE|Online/i')
        offline_badges = await page.query_selector_all('text=/OFFLINE|Offline/i')

        result["programmatic_checks"] = {
            "machine_cards_count": len(machine_cards),
            "online_count": len(online_badges),
            "offline_count": len(offline_badges)
        }

        return result

    async def test_machines_filter_online(self, page) -> dict:
        """Test Online filter on Machines page"""
        print("\n" + "="*80)
        print("🟢 SCENARIO: Machines Filter - Online Only")
        print("="*80)

        await page.goto("http://localhost:8000/demo-app/machines")
        await self.wait_for_page_ready(page)
        await self.dismiss_onboarding(page)

        # Click Online filter
        try:
            online_btn = await page.query_selector('button:has-text("Online")')
            if online_btn:
                await online_btn.click()
                await page.wait_for_timeout(500)
                print("  ✓ Clicked Online filter")
        except Exception as e:
            print(f"  ✗ Could not click Online filter: {e}")

        prompt = """After clicking the "Online" filter, analyze:

1. FILTER STATE: Which filter tab is now active/selected?
2. VISIBLE MACHINES: How many machines are now visible?
3. ALL ONLINE: Are ALL visible machines showing "ONLINE" status? (YES/NO)
4. OFFLINE HIDDEN: Are there any "OFFLINE" machines visible? (should be NO)
5. COUNT MATCH: Does the number of visible machines match the count shown in the "Online" tab?
6. MACHINE DETAILS: List the GPU names of all visible online machines.
7. FILTER WORKING: Is the filter working correctly? (YES/NO)"""

        result = await self.capture_and_analyze(page, "machines_filter_online", prompt)
        return result

    async def test_machines_filter_offline(self, page) -> dict:
        """Test Offline filter on Machines page"""
        print("\n" + "="*80)
        print("🔴 SCENARIO: Machines Filter - Offline Only")
        print("="*80)

        await page.goto("http://localhost:8000/demo-app/machines")
        await self.wait_for_page_ready(page)
        await self.dismiss_onboarding(page)

        # Click Offline filter
        try:
            offline_btn = await page.query_selector('button:has-text("Offline")')
            if offline_btn:
                await offline_btn.click()
                await page.wait_for_timeout(500)
                print("  ✓ Clicked Offline filter")
        except Exception as e:
            print(f"  ✗ Could not click Offline filter: {e}")

        prompt = """After clicking the "Offline" filter, analyze:

1. FILTER STATE: Which filter tab is now active/selected?
2. VISIBLE MACHINES: How many machines are now visible?
3. ALL OFFLINE: Are ALL visible machines showing "OFFLINE" status? (YES/NO)
4. ONLINE HIDDEN: Are there any "ONLINE" machines visible? (should be NO)
5. START BUTTON: Do offline machines show a "Start/Iniciar" button?
6. MACHINE DETAILS: List the GPU names of all visible offline machines.
7. FILTER WORKING: Is the filter working correctly? (YES/NO)"""

        result = await self.capture_and_analyze(page, "machines_filter_offline", prompt)
        return result

    async def test_machine_actions(self, page) -> dict:
        """Test machine action buttons and menus"""
        print("\n" + "="*80)
        print("⚡ SCENARIO: Machine Actions & Buttons")
        print("="*80)

        await page.goto("http://localhost:8000/demo-app/machines")
        await self.wait_for_page_ready(page)
        await self.dismiss_onboarding(page)

        # Try to open dropdown menu on first machine
        try:
            menu_btn = await page.query_selector('button:has(svg[class*="MoreVertical"]), button:has-text("⋮")')
            if menu_btn:
                await menu_btn.click()
                await page.wait_for_timeout(300)
                print("  ✓ Opened machine menu")
        except:
            print("  ⚠ Could not open menu")

        prompt = """Analyze the machine action buttons and menus:

1. IDE BUTTONS: What IDE/editor buttons are visible? (VS Code, Cursor, Windsurf, etc.)
2. MIGRATE BUTTON: Is there a "Migrar p/ CPU" or migration button? (YES/NO)
3. PAUSE BUTTON: Is there a "Pausar" or pause button for running machines? (YES/NO)
4. START BUTTON: Is there an "Iniciar" or start button for stopped machines? (YES/NO)
5. DROPDOWN MENU: If a dropdown menu is open, what options are shown?
6. SNAPSHOT OPTION: Is there a snapshot/backup option in the menu?
7. DESTROY OPTION: Is there a destroy/delete option?
8. CPU BACKUP INFO: Can you see CPU backup/standby information for any machine?
9. BUTTON STATES: Are buttons properly enabled/disabled based on machine status?"""

        result = await self.capture_and_analyze(page, "machine_actions", prompt)
        return result

    async def test_metrics_hub(self, page) -> dict:
        """Test Metrics Hub page"""
        print("\n" + "="*80)
        print("📈 SCENARIO: Metrics Hub")
        print("="*80)

        await page.goto("http://localhost:8000/demo-app/metrics-hub")
        await self.wait_for_page_ready(page)
        await self.dismiss_onboarding(page)

        prompt = """Analyze this metrics hub page:

1. PAGE TITLE: What is the main title/header of the page?
2. METRIC CARDS: List all metric cards/sections visible (e.g., GPU Market, Provider Ranking, etc.)
3. CARD DESCRIPTIONS: What does each card describe?
4. NAVIGATION: Is the navigation menu working and showing the correct active page?
5. DATA PRESENCE: Is there actual data/content in the cards or are they empty?
6. VISUAL DESIGN: Rate the visual design from 1-10.
7. ISSUES: Any problems or missing elements?"""

        result = await self.capture_and_analyze(page, "metrics_hub", prompt)
        return result

    async def test_settings(self, page) -> dict:
        """Test Settings page"""
        print("\n" + "="*80)
        print("⚙️  SCENARIO: Settings Page")
        print("="*80)

        await page.goto("http://localhost:8000/demo-app/settings")
        await self.wait_for_page_ready(page)
        await self.dismiss_onboarding(page)

        prompt = """Analyze this settings page:

1. SETTINGS SECTIONS: What settings sections/categories are visible?
2. FORM FIELDS: What input fields or toggles are present?
3. API KEYS: Is there a section for API keys configuration?
4. SAVE BUTTON: Is there a save/submit button?
5. CURRENT VALUES: Are there any pre-filled values in the form?
6. DEMO MODE: Does the page work in demo mode or show errors?
7. ISSUES: Any problems or missing elements?"""

        result = await self.capture_and_analyze(page, "settings_page", prompt)
        return result

    async def test_navigation_flow(self, page) -> dict:
        """Test navigation between all pages - using direct navigation"""
        print("\n" + "="*80)
        print("🔗 SCENARIO: Navigation Flow")
        print("="*80)

        nav_results = []
        nav_pages = [
            ("Dashboard", "http://localhost:8000/demo-app"),
            ("Machines", "http://localhost:8000/demo-app/machines"),
            ("Metrics Hub", "http://localhost:8000/demo-app/metrics-hub"),
            ("Settings", "http://localhost:8000/demo-app/settings"),
            ("AI Advisor", "http://localhost:8000/demo-app/advisor"),
            ("Savings", "http://localhost:8000/demo-app/savings")
        ]

        for page_name, url in nav_pages:
            try:
                await page.goto(url)
                await self.wait_for_page_ready(page)
                await self.dismiss_onboarding(page)

                # Check if page loaded correctly (no error)
                error_element = await page.query_selector('text=/Error|404|Not Found/i')
                success = error_element is None

                # Check for demo badge
                demo_badge = await page.query_selector('.demo-badge, text=DEMO')
                has_demo_badge = demo_badge is not None

                nav_results.append({
                    "page": page_name,
                    "url": url,
                    "success": success,
                    "has_demo_badge": has_demo_badge
                })
                print(f"  {'✓' if success else '✗'} {page_name}: {'OK' if success else 'Error'} (Demo badge: {has_demo_badge})")

            except Exception as e:
                nav_results.append({
                    "page": page_name,
                    "url": url,
                    "error": str(e)[:50],
                    "success": False
                })
                print(f"  ✗ {page_name}: Error - {str(e)[:50]}")

        return {
            "scenario": "navigation_flow",
            "results": nav_results,
            "all_passed": all(r.get("success", False) for r in nav_results)
        }

    async def test_api_demo_data(self, page) -> dict:
        """Verify API returns demo data correctly"""
        print("\n" + "="*80)
        print("🔌 SCENARIO: API Demo Data Verification")
        print("="*80)

        results = {}

        # Test instances API
        try:
            response = await page.evaluate('''async () => {
                const res = await fetch('/api/v1/instances?demo=true');
                return await res.json();
            }''')
            results["instances_api"] = {
                "success": True,
                "count": response.get("count", 0),
                "has_data": len(response.get("instances", [])) > 0,
                "sample": response.get("instances", [{}])[0].get("gpu_name", "N/A") if response.get("instances") else "N/A"
            }
            print(f"  ✓ Instances API: {results['instances_api']['count']} machines")
        except Exception as e:
            results["instances_api"] = {"success": False, "error": str(e)}
            print(f"  ✗ Instances API: {e}")

        # Test offers API
        try:
            response = await page.evaluate('''async () => {
                const res = await fetch('/api/v1/instances/offers?demo=true');
                return await res.json();
            }''')
            results["offers_api"] = {
                "success": True,
                "count": response.get("count", 0),
                "has_data": len(response.get("offers", [])) > 0
            }
            print(f"  ✓ Offers API: {results['offers_api']['count']} offers")
        except Exception as e:
            results["offers_api"] = {"success": False, "error": str(e)}
            print(f"  ✗ Offers API: {e}")

        return {
            "scenario": "api_demo_data",
            "results": results
        }

    async def run_all_tests(self):
        """Run all comprehensive tests"""
        print("="*100)
        print("🚀 UI-TARS COMPREHENSIVE DEMO MODE VALIDATION")
        print("   Testing all UI scenarios, filters, actions, and API responses")
        print("="*100)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()

            all_results = []

            # Run all test scenarios
            test_methods = [
                self.test_dashboard,
                self.test_machines_list,
                self.test_machines_filter_online,
                self.test_machines_filter_offline,
                self.test_machine_actions,
                self.test_metrics_hub,
                self.test_settings,
                self.test_navigation_flow,
                self.test_api_demo_data
            ]

            for test_method in test_methods:
                try:
                    result = await test_method(page)
                    all_results.append(result)

                    # Check for issues in analysis
                    if result.get("analysis", {}).get("status") == "success":
                        analysis_text = result["analysis"].get("analysis", "").lower()
                        if "no" in analysis_text and "visible" in analysis_text:
                            COMPREHENSIVE_REPORT["issues"].append(f"{result.get('scenario')}: Possible missing elements")
                        COMPREHENSIVE_REPORT["passed"] += 1
                    else:
                        COMPREHENSIVE_REPORT["failed"] += 1

                except Exception as e:
                    print(f"  ✗ Test failed: {e}")
                    COMPREHENSIVE_REPORT["failed"] += 1

            await browser.close()

            # Generate report
            COMPREHENSIVE_REPORT["scenarios"] = all_results
            COMPREHENSIVE_REPORT["total_scenarios"] = len(all_results)

            # Save reports
            self.save_reports(all_results)

            return all_results

    def save_reports(self, results):
        """Save comprehensive test reports"""
        # JSON report
        json_path = "/tmp/ui_tars_comprehensive_report.json"
        with open(json_path, "w") as f:
            json.dump(COMPREHENSIVE_REPORT, f, indent=2, default=str)
        print(f"\n📄 JSON Report: {json_path}")

        # Markdown report
        md_path = "/tmp/ui_tars_comprehensive_report.md"
        with open(md_path, "w") as f:
            f.write("# UI-TARS Comprehensive Demo Mode Validation Report\n\n")
            f.write(f"**Timestamp:** {COMPREHENSIVE_REPORT['timestamp']}\n")
            f.write(f"**Model:** {COMPREHENSIVE_REPORT['model']}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- **Total Scenarios:** {COMPREHENSIVE_REPORT['total_scenarios']}\n")
            f.write(f"- **Passed:** {COMPREHENSIVE_REPORT['passed']}\n")
            f.write(f"- **Failed:** {COMPREHENSIVE_REPORT['failed']}\n\n")

            f.write("## Test Results\n\n")
            for result in results:
                scenario = result.get("scenario", "Unknown")
                f.write(f"### {scenario}\n\n")

                if "analysis" in result and result["analysis"]:
                    if result["analysis"].get("status") == "success":
                        f.write(result["analysis"].get("analysis", "No analysis") + "\n\n")
                    else:
                        f.write(f"Error: {result['analysis'].get('error', 'Unknown error')}\n\n")

                if "programmatic_checks" in result:
                    f.write("**Programmatic Checks:**\n")
                    for k, v in result["programmatic_checks"].items():
                        f.write(f"- {k}: {v}\n")
                    f.write("\n")

                if "results" in result and isinstance(result["results"], list):
                    f.write("**Results:**\n")
                    for r in result["results"]:
                        if isinstance(r, dict):
                            status = "✅" if r.get("success") else "❌"
                            f.write(f"- {status} {r.get('link', 'Unknown')}\n")
                    f.write("\n")

                f.write("---\n\n")

            if COMPREHENSIVE_REPORT["issues"]:
                f.write("## Issues Found\n\n")
                for issue in COMPREHENSIVE_REPORT["issues"]:
                    f.write(f"- {issue}\n")

        print(f"📄 Markdown Report: {md_path}")


async def main():
    tester = ComprehensiveDemoTester()
    results = await tester.run_all_tests()

    print("\n" + "="*100)
    print("📊 FINAL SUMMARY")
    print("="*100)
    print(f"  Total Scenarios: {COMPREHENSIVE_REPORT['total_scenarios']}")
    print(f"  ✅ Passed: {COMPREHENSIVE_REPORT['passed']}")
    print(f"  ❌ Failed: {COMPREHENSIVE_REPORT['failed']}")

    if COMPREHENSIVE_REPORT["issues"]:
        print(f"\n  ⚠️  Issues Found: {len(COMPREHENSIVE_REPORT['issues'])}")
        for issue in COMPREHENSIVE_REPORT["issues"]:
            print(f"     - {issue}")


if __name__ == "__main__":
    asyncio.run(main())
