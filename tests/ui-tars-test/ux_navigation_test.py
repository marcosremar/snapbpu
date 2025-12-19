"""
UX Navigation Test - Dumont Cloud
Based on Project Philosophy from LiveDoc:

Key Principles:
1. "Múltiplos aham moments" - User "gets it" quickly
2. "Proposta de valor mensurável" - User sees value in numbers
3. "3-4 core features" - Focus, not quantity
4. "Métricas de sucesso visíveis" - Dashboard shows value
5. "Desenvolvimento ágil" - Deploy in seconds
6. "Facilidade" - Simplified GPU selection

This test validates the UX against these principles.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"

class UXNavigationTest:
    """UX Navigation and User Experience Validation"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "philosophy_tests": [],
            "navigation_flow": [],
            "aha_moments": [],
            "value_visibility": [],
            "friction_points": [],
            "recommendations": [],
            "screenshots": [],
            "scores": {}
        }
        self.screenshot_dir = Path("/tmp/ux_navigation")
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

    def add_result(self, category, name, passed, details=None, recommendation=None):
        """Add test result"""
        result = {
            "name": name,
            "passed": passed,
            "details": details or {},
        }

        if category == "philosophy":
            self.results["philosophy_tests"].append(result)
        elif category == "navigation":
            self.results["navigation_flow"].append(result)
        elif category == "aha":
            self.results["aha_moments"].append(result)
        elif category == "value":
            self.results["value_visibility"].append(result)

        if not passed and recommendation:
            self.results["friction_points"].append({
                "test": name,
                "issue": details,
                "recommendation": recommendation
            })
            self.results["recommendations"].append(recommendation)

        status = "✅" if passed else "❌"
        print(f"  {status} {name}")

    # =========================================================================
    # PRINCIPLE 1: "Múltiplos Aham Moments" - User gets it quickly
    # =========================================================================
    async def test_aha_moments(self, page):
        """Test if key value propositions are immediately visible"""
        print("\n💡 TESTING: Aham Moments (User gets it quickly)")
        print("="*60)

        await page.goto(f"{BASE_URL}/demo-app")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)
        await self.take_screenshot(page, "01_aha_dashboard")

        # AHA 1: Economy savings visible immediately
        savings_card = await page.query_selector('text=/\\$[0-9]+.*Economia|Savings/i')
        self.add_result("aha", "AHA #1: Economy/savings visible on first view",
                       savings_card is not None,
                       {"visible": savings_card is not None},
                       "Add prominent savings widget in dashboard header")

        # AHA 2: Active machines count visible
        machines_count = await page.query_selector('text=/[0-9]\\/[0-9].*Máquinas|Machines.*Active/i')
        self.add_result("aha", "AHA #2: Active machines count visible",
                       machines_count is not None,
                       {"visible": machines_count is not None},
                       "Show machine count prominently in stats section")

        # AHA 3: Cost per hour visible
        cost_info = await page.query_selector('text=/\\$[0-9]+.*Custo|Cost.*\\$/i')
        self.add_result("aha", "AHA #3: Cost information visible",
                       cost_info is not None,
                       {"visible": cost_info is not None},
                       "Add daily/hourly cost widget to dashboard")

        # AHA 4: Uptime/Reliability visible
        uptime_info = await page.query_selector('text=/[0-9]+.*%.*Uptime|Disponibilidade/i')
        self.add_result("aha", "AHA #4: Uptime/reliability visible",
                       uptime_info is not None,
                       {"visible": uptime_info is not None},
                       "Show uptime percentage prominently")

        # AHA 5: Quick deploy action visible
        deploy_btn = await page.query_selector('button:has-text("Deploy"), button:has-text("Buscar")')
        self.add_result("aha", "AHA #5: Quick deploy action visible",
                       deploy_btn is not None,
                       {"visible": deploy_btn is not None},
                       "Add prominent CTA button for deploying GPU")

    # =========================================================================
    # PRINCIPLE 2: "Proposta de valor mensurável" - Value in numbers
    # =========================================================================
    async def test_value_visibility(self, page):
        """Test if value propositions are shown with measurable numbers"""
        print("\n📊 TESTING: Value Visibility (Numbers that matter)")
        print("="*60)

        await page.goto(f"{BASE_URL}/demo-app")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)

        # Check for specific numeric values that show value

        # VALUE 1: Dollar savings amount
        savings_amount = await page.query_selector('text=/\\$[0-9,]+/')
        self.add_result("value", "VALUE #1: Dollar savings displayed",
                       savings_amount is not None,
                       {"found_dollar_amount": savings_amount is not None},
                       "Display actual savings amount in dollars")

        # VALUE 2: Percentage savings vs competitors
        savings_pct = await page.query_selector('text=/[0-9]+%.*economia|saving|vs/i')
        self.add_result("value", "VALUE #2: Savings percentage shown",
                       savings_pct is not None,
                       {"found_percentage": savings_pct is not None},
                       "Show savings % compared to AWS/GCP")

        # VALUE 3: Machine stats (GPU %, VRAM, etc)
        await page.goto(f"{BASE_URL}/demo-app/machines")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)
        await self.take_screenshot(page, "02_value_machines")

        gpu_stats = await page.query_selector('text=/[0-9]+%.*GPU|GPU.*[0-9]+%/i')
        self.add_result("value", "VALUE #3: GPU utilization percentage",
                       gpu_stats is not None,
                       {"found_gpu_percent": gpu_stats is not None},
                       "Show GPU utilization on machine cards")

        # VALUE 4: Cost per hour visible on machines
        cost_per_hour = await page.query_selector('text=/\\$[0-9.]+.*hora|hour.*\\$/i')
        self.add_result("value", "VALUE #4: Cost per hour on machines",
                       cost_per_hour is not None,
                       {"found_hourly_cost": cost_per_hour is not None},
                       "Display hourly cost on each machine card")

        # VALUE 5: Total VRAM available
        vram_total = await page.query_selector('text=/[0-9]+.*GB.*VRAM/i')
        self.add_result("value", "VALUE #5: VRAM info visible",
                       vram_total is not None,
                       {"found_vram": vram_total is not None},
                       "Show VRAM capacity prominently")

    # =========================================================================
    # PRINCIPLE 3: Navigation Flow - Easy to find things
    # =========================================================================
    async def test_navigation_clarity(self, page):
        """Test navigation clarity and discoverability"""
        print("\n🧭 TESTING: Navigation Clarity")
        print("="*60)

        await page.goto(f"{BASE_URL}/demo-app")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)

        # NAV 1: Main menu items are clear
        menu_items = await page.query_selector_all('nav a, nav button')
        nav_count = len(menu_items)
        self.add_result("navigation", "NAV #1: Main menu has clear items",
                       nav_count >= 4 and nav_count <= 8,  # Not too few, not too many
                       {"menu_items": nav_count},
                       "Keep navigation to 4-6 main items for clarity")

        # NAV 2: Current page is indicated
        active_nav = await page.query_selector('nav a[class*="active"], nav a[class*="bg-"], nav [aria-current]')
        self.add_result("navigation", "NAV #2: Active page indicated",
                       active_nav is not None,
                       {"has_active_indicator": active_nav is not None},
                       "Highlight current page in navigation")

        # NAV 3: Logo leads to home
        logo = await page.query_selector('a[href="/"], a[href="/demo-app"], [class*="logo"]')
        self.add_result("navigation", "NAV #3: Logo/brand clickable",
                       logo is not None,
                       {"logo_present": logo is not None},
                       "Make logo clickable to return to dashboard")

        # NAV 4: User menu visible
        user_menu = await page.query_selector('[class*="avatar"]')
        if not user_menu:
            user_menu = await page.query_selector('[class*="user"]')
        if not user_menu:
            user_menu = await page.query_selector('text=/@/')
        if not user_menu:
            user_menu = await page.query_selector('text=/demo/i')
        self.add_result("navigation", "NAV #4: User/account visible",
                       user_menu is not None,
                       {"user_menu_visible": user_menu is not None},
                       "Show user account/profile in header")

        # NAV 5: Breadcrumb or location indicator on subpages
        await page.goto(f"{BASE_URL}/demo-app/machines")
        await self.wait_for_page(page)

        page_title = await page.query_selector('h1, h2, [class*="title"]')
        self.add_result("navigation", "NAV #5: Page title visible",
                       page_title is not None,
                       {"has_page_title": page_title is not None},
                       "Add clear page title on each page")

    # =========================================================================
    # PRINCIPLE 4: "Desenvolvimento ágil" - Deploy in seconds
    # =========================================================================
    async def test_quick_actions(self, page):
        """Test if key actions are quick and accessible"""
        print("\n⚡ TESTING: Quick Actions (Deploy in seconds)")
        print("="*60)

        await page.goto(f"{BASE_URL}/demo-app")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)
        await self.take_screenshot(page, "03_quick_actions")

        # ACTION 1: Deploy/Search GPU within 2 clicks
        deploy_wizard = await page.query_selector('[class*="deploy"], form, [class*="wizard"]')
        self.add_result("navigation", "ACTION #1: Deploy wizard on dashboard",
                       deploy_wizard is not None,
                       {"wizard_present": deploy_wizard is not None},
                       "Keep GPU deploy wizard visible on main dashboard")

        # ACTION 2: Region selection easy
        region_selector = await page.query_selector('button:has-text("EUA"), button:has-text("Europa"), [class*="region"]')
        self.add_result("navigation", "ACTION #2: Region selection visible",
                       region_selector is not None,
                       {"region_visible": region_selector is not None},
                       "Make region selection obvious and easy")

        # ACTION 3: GPU type selection available
        gpu_selector = await page.query_selector('text=/GPU.*opcional/i')
        if not gpu_selector:
            gpu_selector = await page.query_selector('text=/Select.*GPU/i')
        if not gpu_selector:
            gpu_selector = await page.query_selector('[class*="gpu-select"]')
        self.add_result("navigation", "ACTION #3: GPU type selection available",
                       gpu_selector is not None,
                       {"gpu_selector": gpu_selector is not None},
                       "Show GPU type selector prominently")

        # ACTION 4: Machine actions accessible
        await page.goto(f"{BASE_URL}/demo-app/machines")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)

        action_btns = await page.query_selector_all('button:has-text("Pausar"), button:has-text("Iniciar"), button:has-text("VS Code")')
        self.add_result("navigation", "ACTION #4: Machine actions available",
                       len(action_btns) >= 1,
                       {"action_buttons": len(action_btns)},
                       "Show action buttons (Pause, Start, IDE) on machine cards")

        # ACTION 5: Snapshot/backup accessible
        snapshot_option = await page.query_selector('text=/backup/i')
        if not snapshot_option:
            snapshot_option = await page.query_selector('text=/snapshot/i')
        if not snapshot_option:
            snapshot_option = await page.query_selector('select')
        self.add_result("navigation", "ACTION #5: Snapshot accessible",
                       snapshot_option is not None,
                       {"snapshot_available": snapshot_option is not None},
                       "Add quick snapshot option on machine cards")

    # =========================================================================
    # PRINCIPLE 5: Mobile Experience
    # =========================================================================
    async def test_mobile_ux(self, context):
        """Test mobile user experience"""
        print("\n📱 TESTING: Mobile UX")
        print("="*60)

        mobile_page = await context.new_page()
        await mobile_page.set_viewport_size({"width": 375, "height": 812})

        await mobile_page.goto(f"{BASE_URL}/demo-app")
        await self.wait_for_page(mobile_page)
        await self.dismiss_overlays(mobile_page)
        await self.take_screenshot(mobile_page, "04_mobile_ux")

        # MOBILE 1: Menu toggle visible
        menu_toggle = await mobile_page.query_selector('button[class*="mobile"], [aria-label*="menu"], svg[class*="Menu"]')
        self.add_result("navigation", "MOBILE #1: Menu toggle visible",
                       menu_toggle is not None,
                       {"menu_toggle": menu_toggle is not None},
                       "Add hamburger menu for mobile")

        # MOBILE 2: Stats cards stack properly
        stats_cards = await mobile_page.query_selector_all('[class*="bg-gradient"], [class*="stat-card"]')
        self.add_result("navigation", "MOBILE #2: Stats cards present",
                       len(stats_cards) >= 2,
                       {"stats_count": len(stats_cards)},
                       "Ensure stats cards are visible on mobile")

        # MOBILE 3: Touch targets are adequate (44px minimum)
        buttons = await mobile_page.query_selector_all('button')
        adequate_targets = True  # Assume good until proven otherwise
        for btn in buttons[:5]:  # Check first 5 buttons
            box = await btn.bounding_box()
            if box and (box['width'] < 44 or box['height'] < 44):
                adequate_targets = False
                break
        self.add_result("navigation", "MOBILE #3: Touch targets adequate",
                       adequate_targets,
                       {"adequate_size": adequate_targets},
                       "Ensure all buttons are at least 44x44px on mobile")

        # MOBILE 4: Machines page usable
        await mobile_page.goto(f"{BASE_URL}/demo-app/machines")
        await self.wait_for_page(mobile_page)
        await self.take_screenshot(mobile_page, "05_mobile_machines")

        machine_cards = await mobile_page.query_selector_all('text=/RTX|A100|H100/i')
        self.add_result("navigation", "MOBILE #4: Machines visible on mobile",
                       len(machine_cards) >= 1,
                       {"machines_visible": len(machine_cards)},
                       "Ensure machine cards are usable on mobile")

        await mobile_page.close()

    # =========================================================================
    # PRINCIPLE 6: User Journey Flow
    # =========================================================================
    async def test_user_journey(self, page):
        """Test typical user journey: See value -> Find GPU -> Deploy"""
        print("\n🚀 TESTING: User Journey Flow")
        print("="*60)

        # Step 1: Land on dashboard, see value immediately
        await page.goto(f"{BASE_URL}/demo-app")
        await self.wait_for_page(page)
        await self.dismiss_overlays(page)

        value_visible = await page.query_selector('text=/\\$[0-9]+|[0-9]+%|Economia|Savings/i')
        self.add_result("navigation", "JOURNEY #1: Value visible on landing",
                       value_visible is not None,
                       {"value_shown": value_visible is not None},
                       "Show value proposition immediately on dashboard")

        # Step 2: Can easily find/deploy GPU
        deploy_section = await page.query_selector('text=/Deploy|Buscar.*GPU/i')
        self.add_result("navigation", "JOURNEY #2: GPU deploy section found",
                       deploy_section is not None,
                       {"deploy_visible": deploy_section is not None},
                       "Make GPU deploy section prominent")

        # Step 3: Can view existing machines
        await page.goto(f"{BASE_URL}/demo-app/machines")
        await self.wait_for_page(page)

        machines = await page.query_selector_all('text=/RTX|A100|H100/i')
        self.add_result("navigation", "JOURNEY #3: Can view machines",
                       len(machines) >= 1,
                       {"machines_found": len(machines)},
                       "Ensure machines page loads properly")

        # Step 4: Can take actions on machines
        action_btn = await page.query_selector('button:has-text("Pausar"), button:has-text("VS Code")')
        self.add_result("navigation", "JOURNEY #4: Can take actions",
                       action_btn is not None,
                       {"actions_available": action_btn is not None},
                       "Show clear action buttons on machines")

        # Step 5: Can view metrics/savings
        await page.goto(f"{BASE_URL}/demo-app/metrics-hub")
        await self.wait_for_page(page)
        await self.take_screenshot(page, "06_journey_metrics")

        metrics = await page.query_selector('text=/Métrica|Metric|GPU|Market/i')
        self.add_result("navigation", "JOURNEY #5: Metrics accessible",
                       metrics is not None,
                       {"metrics_visible": metrics is not None},
                       "Provide clear metrics/analytics page")

    # =========================================================================
    # FRICTION ANALYSIS
    # =========================================================================
    async def analyze_friction(self, page):
        """Identify friction points in the UI"""
        print("\n🔍 ANALYZING: Friction Points")
        print("="*60)

        await page.goto(f"{BASE_URL}/demo-app")
        await self.wait_for_page(page)

        friction_found = []

        # Check for loading indicators
        loading = await page.query_selector('[class*="loading"], [class*="spinner"]')
        if loading:
            friction_found.append("Loading indicators present - check if necessary")

        # Check for error states
        errors = await page.query_selector('text=/Error|Erro|Failed/i')
        if errors:
            friction_found.append("Error messages visible - investigate cause")

        # Check for empty states
        await page.goto(f"{BASE_URL}/demo-app/machines")
        await self.wait_for_page(page)

        empty_state = await page.query_selector('text=/Nenhuma|No machines|Empty/i')
        if empty_state:
            friction_found.append("Empty state visible - ensure demo has data")

        # Check for disabled buttons
        disabled = await page.query_selector_all('button[disabled]')
        if len(disabled) > 3:
            friction_found.append(f"Many disabled buttons ({len(disabled)}) - review UX")

        # Check for excessive scrolling needed
        page_height = await page.evaluate('document.body.scrollHeight')
        if page_height > 3000:
            friction_found.append("Page very tall - consider pagination or sections")

        if friction_found:
            for f in friction_found:
                print(f"  ⚠️  {f}")
        else:
            print("  ✅ No major friction points detected")

        self.results["friction_points"].extend([{"issue": f} for f in friction_found])

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    async def run_all(self):
        """Run all UX navigation tests"""
        print("="*80)
        print("🎯 UX NAVIGATION TEST - Based on Dumont Cloud Philosophy")
        print("="*80)
        print("\nKey Principles from LiveDoc:")
        print("  1. Múltiplos 'aham moments' - User gets it quickly")
        print("  2. Proposta de valor mensurável - Value in numbers")
        print("  3. 3-4 core features - Focus, not quantity")
        print("  4. Desenvolvimento ágil - Deploy in seconds")
        print("  5. Facilidade - Simplified GPU selection")
        print("="*80)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()

            # Run all UX tests
            await self.test_aha_moments(page)
            await self.test_value_visibility(page)
            await self.test_navigation_clarity(page)
            await self.test_quick_actions(page)
            await self.test_mobile_ux(context)
            await self.test_user_journey(page)
            await self.analyze_friction(page)

            await browser.close()

        # Calculate scores
        self.calculate_scores()

        # Save results
        self.save_results()
        self.print_summary()

    def calculate_scores(self):
        """Calculate UX scores by category"""
        categories = {
            "Aham Moments": self.results["aha_moments"],
            "Value Visibility": self.results["value_visibility"],
            "Navigation": self.results["navigation_flow"]
        }

        for cat_name, tests in categories.items():
            if tests:
                passed = sum(1 for t in tests if t["passed"])
                total = len(tests)
                score = (passed / total * 100) if total > 0 else 0
                self.results["scores"][cat_name] = {
                    "passed": passed,
                    "total": total,
                    "score": round(score, 1)
                }

    def save_results(self):
        """Save results to files"""
        # JSON report
        json_path = "/tmp/ux_navigation_report.json"
        with open(json_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 JSON Report: {json_path}")

        # Markdown report
        md_path = "/tmp/ux_navigation_report.md"
        with open(md_path, "w") as f:
            f.write("# UX Navigation Test Report\n\n")
            f.write(f"**Timestamp:** {self.results['timestamp']}\n\n")
            f.write("## Based on Dumont Cloud Philosophy (LiveDoc)\n\n")

            f.write("## Scores by Category\n\n")
            f.write("| Category | Passed | Total | Score |\n")
            f.write("|----------|--------|-------|-------|\n")
            for cat, data in self.results["scores"].items():
                emoji = "✅" if data["score"] >= 80 else "⚠️" if data["score"] >= 60 else "❌"
                f.write(f"| {cat} | {data['passed']} | {data['total']} | {emoji} {data['score']}% |\n")

            f.write("\n## Aham Moments (User gets it quickly)\n\n")
            for test in self.results["aha_moments"]:
                status = "✅" if test["passed"] else "❌"
                f.write(f"- {status} {test['name']}\n")

            f.write("\n## Value Visibility (Numbers that matter)\n\n")
            for test in self.results["value_visibility"]:
                status = "✅" if test["passed"] else "❌"
                f.write(f"- {status} {test['name']}\n")

            f.write("\n## Navigation Flow\n\n")
            for test in self.results["navigation_flow"]:
                status = "✅" if test["passed"] else "❌"
                f.write(f"- {status} {test['name']}\n")

            if self.results["recommendations"]:
                f.write("\n## Recommendations for Improvement\n\n")
                for i, rec in enumerate(set(self.results["recommendations"]), 1):
                    f.write(f"{i}. {rec}\n")

            if self.results["friction_points"]:
                f.write("\n## Friction Points Identified\n\n")
                for fp in self.results["friction_points"]:
                    if isinstance(fp, dict):
                        f.write(f"- ⚠️ {fp.get('issue', fp.get('recommendation', str(fp)))}\n")

            f.write("\n## Screenshots\n\n")
            for ss in self.results["screenshots"]:
                f.write(f"- {ss}\n")

        print(f"📄 Markdown Report: {md_path}")

    def print_summary(self):
        """Print final summary"""
        print("\n" + "="*80)
        print("📊 UX NAVIGATION SUMMARY")
        print("="*80)

        total_passed = 0
        total_tests = 0

        for cat, data in self.results["scores"].items():
            total_passed += data["passed"]
            total_tests += data["total"]
            emoji = "✅" if data["score"] >= 80 else "⚠️" if data["score"] >= 60 else "❌"
            print(f"  {cat}: {emoji} {data['score']}% ({data['passed']}/{data['total']})")

        overall = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"\n  OVERALL UX SCORE: {overall:.1f}%")

        if self.results["recommendations"]:
            print(f"\n⚠️  {len(set(self.results['recommendations']))} Improvements Recommended")
            for rec in list(set(self.results["recommendations"]))[:5]:
                print(f"   • {rec}")

        print(f"\n📸 Screenshots: {len(self.results['screenshots'])}")


async def main():
    tester = UXNavigationTest()
    await tester.run_all()


if __name__ == "__main__":
    asyncio.run(main())
