"""
Demo Mode Functional Validation
Tests all UI elements, navigation, filters, and API responses without AI analysis
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import requests

BASE_URL = "http://localhost:8000"

class DemoValidator:
    """Functional validation for demo mode"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "passed": 0,
            "failed": 0,
            "screenshots": []
        }
        self.screenshot_dir = Path("/tmp/demo_validation")
        self.screenshot_dir.mkdir(exist_ok=True)

    async def take_screenshot(self, page, name):
        """Capture screenshot"""
        path = self.screenshot_dir / f"{name}.png"
        await page.screenshot(path=str(path))
        self.results["screenshots"].append(str(path))
        return str(path)

    async def wait_for_page(self, page):
        """Wait for page to be ready"""
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(0.5)

    async def dismiss_overlays(self, page):
        """Dismiss any modal overlays"""
        try:
            skip_btn = await page.query_selector('button:has-text("Pular"), button:has-text("Skip")')
            if skip_btn:
                await skip_btn.click()
                await asyncio.sleep(0.3)
        except:
            pass

    def add_result(self, name, passed, details=None, error=None):
        """Add test result"""
        result = {
            "name": name,
            "passed": passed,
            "details": details or {},
            "error": error
        }
        self.results["tests"].append(result)
        if passed:
            self.results["passed"] += 1
            print(f"  ✅ {name}")
        else:
            self.results["failed"] += 1
            print(f"  ❌ {name}: {error or 'Failed'}")

    # =========================================================================
    # TEST: Dashboard Page
    # =========================================================================
    async def test_dashboard(self, page):
        """Test Dashboard page loads correctly"""
        print("\n📊 Testing Dashboard Page...")

        await page.goto(f"{BASE_URL}/demo-app")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)
        await self.take_screenshot(page, "01_dashboard")

        # Check DEMO badge
        demo_badge = await page.query_selector('.demo-badge')
        if not demo_badge:
            demo_badge = await page.query_selector('text=DEMO')
        self.add_result("Dashboard - DEMO badge visible", demo_badge is not None)

        # Check navigation links
        nav_links = await page.query_selector_all('nav a, nav button')
        self.add_result("Dashboard - Navigation links present", len(nav_links) >= 4,
                        {"count": len(nav_links)})

        # Check stats cards
        stats_cards = await page.query_selector_all('[class*="bg-gradient"]')
        self.add_result("Dashboard - Stats cards visible", len(stats_cards) >= 1,
                        {"count": len(stats_cards)})

        # Check deploy wizard
        deploy_section = await page.query_selector('text=/Deploy|Buscar GPU/i')
        self.add_result("Dashboard - Deploy wizard present", deploy_section is not None)

        # Check region buttons
        region_btns = await page.query_selector_all('button:has-text("EUA"), button:has-text("Europa")')
        self.add_result("Dashboard - Region buttons visible", len(region_btns) >= 1,
                        {"count": len(region_btns)})

    # =========================================================================
    # TEST: Machines Page
    # =========================================================================
    async def test_machines_page(self, page):
        """Test Machines page loads and shows demo data"""
        print("\n🖥️  Testing Machines Page...")

        await page.goto(f"{BASE_URL}/demo-app/machines")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)
        await self.take_screenshot(page, "02_machines_all")

        # Check page title (Portuguese: "Minhas Máquinas")
        title = await page.query_selector('h1')
        if not title:
            title = await page.query_selector('h2')
        if not title:
            title = await page.query_selector('text=/Minhas Máquinas|My Machines/i')
        self.add_result("Machines - Page title present", title is not None)

        # Check filter tabs
        filter_tabs = await page.query_selector_all('button:has-text("Todas"), button:has-text("Online"), button:has-text("Offline")')
        self.add_result("Machines - Filter tabs visible", len(filter_tabs) >= 2,
                        {"count": len(filter_tabs)})

        # Check machine cards
        machine_cards = await page.query_selector_all('[class*="rounded-lg"][class*="border"]')
        # Filter to only actual machine cards (not navigation or other elements)
        self.add_result("Machines - Machine cards present", len(machine_cards) >= 1,
                        {"count": len(machine_cards)})

        # Check for GPU names
        gpu_names = await page.query_selector_all('text=/RTX|A100|H100|3090|4090/i')
        self.add_result("Machines - GPU names visible", len(gpu_names) >= 1,
                        {"count": len(gpu_names)})

        # Check status badges
        status_badges = await page.query_selector_all('text=/ONLINE|OFFLINE/i')
        self.add_result("Machines - Status badges visible", len(status_badges) >= 1,
                        {"count": len(status_badges)})

    # =========================================================================
    # TEST: Machines Filters
    # =========================================================================
    async def test_machines_filters(self, page):
        """Test machine filtering works"""
        print("\n🔍 Testing Machine Filters...")

        await page.goto(f"{BASE_URL}/demo-app/machines")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)

        # Click Online filter
        online_btn = await page.query_selector('button:has-text("Online")')
        if online_btn:
            await online_btn.click()
            await asyncio.sleep(0.5)
            await self.take_screenshot(page, "03_machines_online")

            # Check online filter is working by looking at the active button and visible badges
            # Count ONLINE status badges (green badges with ONLINE text)
            online_badges = await page.query_selector_all('[class*="bg-green"]:has-text("ONLINE")')
            if not online_badges:
                online_badges = await page.query_selector_all('span:has-text("ONLINE")')
            # Filter should show only online machines - verify we have online badges and no offline
            offline_text = await page.query_selector('[class*="bg-red"]:has-text("OFFLINE")')
            self.add_result("Filter - Online filter works",
                           len(online_badges) >= 1 and offline_text is None,
                           {"online_badges": len(online_badges), "has_offline": offline_text is not None})
        else:
            self.add_result("Filter - Online filter works", False, error="Button not found")

        # Click Offline filter
        offline_btn = await page.query_selector('button:has-text("Offline")')
        if offline_btn:
            await offline_btn.click()
            await asyncio.sleep(0.5)
            await self.take_screenshot(page, "04_machines_offline")

            # Check offline filter is working - should show offline badges and no online
            offline_badges = await page.query_selector_all('[class*="bg-red"]:has-text("OFFLINE")')
            if not offline_badges:
                offline_badges = await page.query_selector_all('span:has-text("OFFLINE")')
            online_text = await page.query_selector('[class*="bg-green"]:has-text("ONLINE")')
            self.add_result("Filter - Offline filter works",
                           len(offline_badges) >= 1 and online_text is None,
                           {"offline_badges": len(offline_badges), "has_online": online_text is not None})
        else:
            self.add_result("Filter - Offline filter works", False, error="Button not found")

        # Click All filter
        all_btn = await page.query_selector('button:has-text("Todas")')
        if all_btn:
            await all_btn.click()
            await asyncio.sleep(0.5)

            online_badges = await page.query_selector_all('text=/ONLINE/i')
            offline_badges = await page.query_selector_all('text=/OFFLINE/i')
            self.add_result("Filter - All filter shows both",
                           len(online_badges) >= 1 and len(offline_badges) >= 1,
                           {"online": len(online_badges), "offline": len(offline_badges)})

    # =========================================================================
    # TEST: Machine Actions
    # =========================================================================
    async def test_machine_actions(self, page):
        """Test machine action buttons"""
        print("\n⚡ Testing Machine Actions...")

        await page.goto(f"{BASE_URL}/demo-app/machines")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)

        # Check for IDE buttons
        ide_btns = await page.query_selector_all('button:has-text("VS Code"), button:has-text("Cursor"), button:has-text("Windsurf")')
        self.add_result("Actions - IDE buttons present", len(ide_btns) >= 1,
                        {"count": len(ide_btns)})

        # Check for Pause button (for online machines)
        pause_btn = await page.query_selector('button:has-text("Pausar")')
        self.add_result("Actions - Pause button present", pause_btn is not None)

        # Check for CPU migration button
        migrate_btn = await page.query_selector('button:has-text("Migrar"), button:has-text("CPU")')
        self.add_result("Actions - Migrate button present", migrate_btn is not None)

        # Check for snapshot dropdown
        snapshot_btn = await page.query_selector('button:has-text("backup"), select:has-text("backup")')
        self.add_result("Actions - Snapshot option present", snapshot_btn is not None)

        # Test clicking Pause on first online machine
        if pause_btn:
            await pause_btn.click()
            await asyncio.sleep(2)
            await self.take_screenshot(page, "05_after_pause")

            # Check for toast notification
            toast = await page.query_selector('[class*="toast"], [class*="fixed bottom"]')
            self.add_result("Actions - Demo toast appears on action", toast is not None)

    # =========================================================================
    # TEST: Metrics Hub
    # =========================================================================
    async def test_metrics_hub(self, page):
        """Test Metrics Hub page"""
        print("\n📈 Testing Metrics Hub...")

        await page.goto(f"{BASE_URL}/demo-app/metrics-hub")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)
        await self.take_screenshot(page, "06_metrics_hub")

        # Check page title
        title = await page.query_selector('h1:has-text("Métrica"), h2:has-text("Métrica")')
        self.add_result("Metrics - Page title present", title is not None)

        # Check metric cards
        metric_cards = await page.query_selector_all('[class*="rounded"][class*="border"], [class*="card"]')
        self.add_result("Metrics - Metric cards visible", len(metric_cards) >= 3,
                        {"count": len(metric_cards)})

        # Check navigation is active
        active_nav = await page.query_selector('a[class*="active"], nav a[class*="bg-"]')
        self.add_result("Metrics - Active navigation indicator", active_nav is not None)

    # =========================================================================
    # TEST: Settings Page
    # =========================================================================
    async def test_settings(self, page):
        """Test Settings page"""
        print("\n⚙️  Testing Settings Page...")

        await page.goto(f"{BASE_URL}/demo-app/settings")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)
        await self.take_screenshot(page, "07_settings")

        # Check page title (might be h1, h2, or just text)
        title = await page.query_selector('h1')
        if not title:
            title = await page.query_selector('h2')
        if not title:
            title = await page.query_selector('text=/Settings|Configurações/i')
        self.add_result("Settings - Page title present", title is not None)

        # Check for form elements
        inputs = await page.query_selector_all('input, select, textarea')
        self.add_result("Settings - Form inputs present", len(inputs) >= 1,
                        {"count": len(inputs)})

        # Check for save button
        save_btn = await page.query_selector('button:has-text("Salvar"), button:has-text("Save")')
        self.add_result("Settings - Save button present", save_btn is not None)

    # =========================================================================
    # TEST: Navigation Flow
    # =========================================================================
    async def test_navigation(self, page):
        """Test navigation between pages"""
        print("\n🔗 Testing Navigation Flow...")

        pages = [
            ("/demo-app", "Dashboard"),
            ("/demo-app/machines", "Machines"),
            ("/demo-app/metrics-hub", "Metrics"),
            ("/demo-app/settings", "Settings"),
            ("/demo-app/advisor", "AI Advisor"),
            ("/demo-app/savings", "Savings"),
        ]

        for url, name in pages:
            try:
                await page.goto(f"{BASE_URL}{url}")
                await self.wait_for_page(page)

                # Check no 404 error
                error = await page.query_selector('text=/404|Not Found|Error/i')

                # Check demo badge still present
                demo_badge = await page.query_selector('.demo-badge')
                if not demo_badge:
                    demo_badge = await page.query_selector('text=DEMO')

                passed = error is None and demo_badge is not None
                self.add_result(f"Navigation - {name} page loads", passed,
                               {"url": url, "has_demo_badge": demo_badge is not None})
            except Exception as e:
                self.add_result(f"Navigation - {name} page loads", False, error=str(e)[:50])

    # =========================================================================
    # TEST: API Endpoints
    # =========================================================================
    async def test_api_endpoints(self, page):
        """Test API returns demo data"""
        print("\n🔌 Testing API Endpoints...")

        # Test instances API
        try:
            response = await page.evaluate('''async () => {
                const res = await fetch('/api/v1/instances?demo=true');
                return await res.json();
            }''')
            self.add_result("API - Instances endpoint works",
                           response.get("count", 0) > 0,
                           {"count": response.get("count", 0)})
        except Exception as e:
            self.add_result("API - Instances endpoint works", False, error=str(e)[:50])

        # Test offers API
        try:
            response = await page.evaluate('''async () => {
                const res = await fetch('/api/v1/instances/offers?demo=true');
                return await res.json();
            }''')
            self.add_result("API - Offers endpoint works",
                           response.get("count", 0) > 0,
                           {"count": response.get("count", 0)})
        except Exception as e:
            self.add_result("API - Offers endpoint works", False, error=str(e)[:50])

        # Test health endpoint
        try:
            response = await page.evaluate('''async () => {
                const res = await fetch('/health');
                return await res.json();
            }''')
            self.add_result("API - Health endpoint works",
                           response.get("status") == "healthy",
                           {"status": response.get("status")})
        except Exception as e:
            self.add_result("API - Health endpoint works", False, error=str(e)[:50])

    # =========================================================================
    # TEST: Mobile Responsiveness
    # =========================================================================
    async def test_mobile_view(self, context):
        """Test mobile view"""
        print("\n📱 Testing Mobile View...")

        mobile_page = await context.new_page()
        await mobile_page.set_viewport_size({"width": 375, "height": 812})

        await mobile_page.goto(f"{BASE_URL}/demo-app")
        await self.wait_for_page(mobile_page)
        await self.dismiss_overlays(mobile_page)
        await self.take_screenshot(mobile_page, "08_mobile_dashboard")

        # Check hamburger menu or mobile nav
        mobile_menu = await mobile_page.query_selector('button[class*="mobile"], button[aria-label*="menu"]')
        self.add_result("Mobile - Menu toggle present", mobile_menu is not None)

        # Check demo badge still visible
        demo_badge = await mobile_page.query_selector('.demo-badge')
        if not demo_badge:
            demo_badge = await mobile_page.query_selector('text=DEMO')
        self.add_result("Mobile - DEMO badge visible", demo_badge is not None)

        await mobile_page.goto(f"{BASE_URL}/demo-app/machines")
        await self.wait_for_page(mobile_page)
        await self.take_screenshot(mobile_page, "09_mobile_machines")

        # Check machines are visible on mobile
        gpu_names = await mobile_page.query_selector_all('text=/RTX|A100|H100/i')
        self.add_result("Mobile - Machine cards visible", len(gpu_names) >= 1,
                        {"count": len(gpu_names)})

        await mobile_page.close()

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    async def run_all(self):
        """Run all validation tests"""
        print("="*80)
        print("🚀 DEMO MODE FUNCTIONAL VALIDATION")
        print("="*80)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()

            # Run all tests
            await self.test_dashboard(page)
            await self.test_machines_page(page)
            await self.test_machines_filters(page)
            await self.test_machine_actions(page)
            await self.test_metrics_hub(page)
            await self.test_settings(page)
            await self.test_navigation(page)
            await self.test_api_endpoints(page)
            await self.test_mobile_view(context)

            await browser.close()

        # Save results
        self.save_results()
        self.print_summary()

    def save_results(self):
        """Save results to files"""
        # JSON report
        json_path = "/tmp/demo_validation_report.json"
        with open(json_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 JSON Report: {json_path}")

        # Markdown report
        md_path = "/tmp/demo_validation_report.md"
        with open(md_path, "w") as f:
            f.write("# Demo Mode Validation Report\n\n")
            f.write(f"**Timestamp:** {self.results['timestamp']}\n\n")
            f.write(f"## Summary\n\n")
            f.write(f"- **Passed:** {self.results['passed']}\n")
            f.write(f"- **Failed:** {self.results['failed']}\n")
            f.write(f"- **Total:** {len(self.results['tests'])}\n\n")

            f.write("## Test Results\n\n")
            f.write("| Test | Status | Details |\n")
            f.write("|------|--------|--------|\n")
            for test in self.results["tests"]:
                status = "✅" if test["passed"] else "❌"
                details = test.get("error") or str(test.get("details", ""))[:50]
                f.write(f"| {test['name']} | {status} | {details} |\n")

            f.write("\n## Screenshots\n\n")
            for ss in self.results["screenshots"]:
                f.write(f"- {ss}\n")

        print(f"📄 Markdown Report: {md_path}")

    def print_summary(self):
        """Print final summary"""
        print("\n" + "="*80)
        print("📊 FINAL SUMMARY")
        print("="*80)
        total = len(self.results["tests"])
        passed = self.results["passed"]
        failed = self.results["failed"]
        pct = (passed / total * 100) if total > 0 else 0

        print(f"  Total Tests: {total}")
        print(f"  ✅ Passed: {passed} ({pct:.1f}%)")
        print(f"  ❌ Failed: {failed}")
        print(f"  📸 Screenshots: {len(self.results['screenshots'])}")

        if failed > 0:
            print("\n⚠️  Failed Tests:")
            for test in self.results["tests"]:
                if not test["passed"]:
                    print(f"   - {test['name']}: {test.get('error', 'Failed')}")


async def main():
    validator = DemoValidator()
    await validator.run_all()


if __name__ == "__main__":
    asyncio.run(main())
