"""
Comprehensive system validation using Playwright
Navigates through all pages and verifies functionality
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import sys

# Report structure
REPORT = {
    "timestamp": None,
    "url": "http://localhost:8000",
    "pages": {
        "login": {"status": None, "issues": [], "elements": []},
        "dashboard": {"status": None, "issues": [], "elements": []},
        "machines": {"status": None, "issues": [], "elements": []},
        "settings": {"status": None, "issues": [], "elements": []},
        "metrics": {"status": None, "issues": [], "elements": []},
    },
    "issues": [],
    "summary": {
        "total_issues": 0,
        "working": 0,
        "broken": 0,
        "recommendations": []
    }
}

async def take_screenshot(page, name):
    """Take screenshot for debugging"""
    path = f"/tmp/validate_{name}_{asyncio.get_event_loop().time()}.png"
    try:
        await page.screenshot(path=path)
        return path
    except:
        return None

async def validate_login(page):
    """Validate login page and authentication"""
    print("\n[1/5] TESTANDO PÁGINA DE LOGIN...")
    issues = []
    elements = []

    try:
        await page.goto("http://localhost:8000")
        await page.wait_for_timeout(2000)

        # Check for login form elements
        email_input = await page.query_selector('input[type="email"]')
        password_input = await page.query_selector('input[type="password"]')
        login_button = await page.query_selector('button[type="submit"]')

        if email_input:
            elements.append("Email input field")
        else:
            issues.append("Email input field not found")

        if password_input:
            elements.append("Password input field")
        else:
            issues.append("Password input field not found")

        if login_button:
            elements.append("Login button")
        else:
            issues.append("Login button not found")

        # Try to login
        if email_input and password_input and login_button:
            await email_input.fill("test@example.com")
            await password_input.fill("testpassword123")
            await login_button.click()

            # Wait for navigation
            try:
                await page.wait_for_url("**/dashboard**", timeout=5000)
                REPORT["pages"]["login"]["status"] = "PASSED"
                print("✓ Login funcionando")
            except:
                # Check if error message appeared
                error_msg = await page.query_selector('[role="alert"]')
                if error_msg:
                    error_text = await error_msg.text_content()
                    issues.append(f"Login error: {error_text}")
                else:
                    issues.append("Login redirect failed - possible authentication issue")
                REPORT["pages"]["login"]["status"] = "PARTIAL"
                print("⚠ Login com problemas")
        else:
            REPORT["pages"]["login"]["status"] = "BROKEN"
            print("✗ Login form incompleto")

    except Exception as e:
        issues.append(f"Exception: {str(e)}")
        REPORT["pages"]["login"]["status"] = "BROKEN"
        print(f"✗ Erro ao testar login: {e}")

    REPORT["pages"]["login"]["issues"] = issues
    REPORT["pages"]["login"]["elements"] = elements
    return len(issues) == 0

async def validate_dashboard(page):
    """Validate dashboard page"""
    print("\n[2/5] TESTANDO DASHBOARD...")
    issues = []
    elements = []

    try:
        # Navigate directly if login didn't work
        await page.goto("http://localhost:8000/dashboard")
        await page.wait_for_timeout(2000)

        # Check for dashboard elements
        dashboard_title = await page.query_selector('h1, h2')
        if dashboard_title:
            title_text = await dashboard_title.text_content()
            elements.append(f"Page title: {title_text}")
        else:
            issues.append("Dashboard title not found")

        # Check for speed cards
        speed_cards = await page.query_selector_all('[class*="card"], [class*="speed"], button')
        if speed_cards:
            elements.append(f"Found {len(speed_cards)} cards/buttons")

            # Try clicking first card if available
            if len(speed_cards) > 0:
                try:
                    await speed_cards[0].click()
                    await page.wait_for_timeout(1000)
                    elements.append("Successfully clicked speed card")
                except:
                    issues.append("Could not click speed card")
        else:
            issues.append("No dashboard cards found")

        # Check for wizard/search button
        search_button = await page.query_selector('button:has-text("Buscar"), button:has-text("Search")')
        if search_button:
            elements.append("Search/Wizard button found")
        else:
            issues.append("Search/Wizard button not found")

        REPORT["pages"]["dashboard"]["status"] = "PASSED" if len(issues) < 2 else "PARTIAL" if len(issues) < 4 else "BROKEN"
        print(f"{'✓' if len(issues) == 0 else '⚠' if len(issues) < 3 else '✗'} Dashboard: {len(elements)} elementos, {len(issues)} problemas")

    except Exception as e:
        issues.append(f"Exception: {str(e)}")
        REPORT["pages"]["dashboard"]["status"] = "BROKEN"
        print(f"✗ Erro ao testar dashboard: {e}")

    REPORT["pages"]["dashboard"]["issues"] = issues
    REPORT["pages"]["dashboard"]["elements"] = elements
    return len(issues) == 0

async def validate_machines(page):
    """Validate machines page"""
    print("\n[3/5] TESTANDO PÁGINA MACHINES...")
    issues = []
    elements = []

    try:
        await page.goto("http://localhost:8000/machines")
        await page.wait_for_timeout(2000)

        # Check page content
        page_content = await page.content()

        # Check for machine list
        machine_rows = await page.query_selector_all('[role="row"], tr, [class*="machine"]')
        if machine_rows:
            elements.append(f"Found {len(machine_rows)} machine rows/items")
        else:
            issues.append("No machine list found")

        # Check for filter/search
        search_input = await page.query_selector('input[placeholder*="search"], input[placeholder*="Search"]')
        if search_input:
            elements.append("Search input found")
        else:
            issues.append("Search/filter input not found")

        # Check for status indicators
        status_badges = await page.query_selector_all('[class*="badge"], [class*="status"], span[class*="online"], span[class*="offline"]')
        if status_badges:
            elements.append(f"Found {len(status_badges)} status indicators")
        else:
            issues.append("No status indicators found")

        REPORT["pages"]["machines"]["status"] = "PASSED" if len(issues) < 1 else "PARTIAL" if len(issues) < 3 else "BROKEN"
        print(f"{'✓' if len(issues) == 0 else '⚠' if len(issues) < 2 else '✗'} Machines: {len(elements)} elementos, {len(issues)} problemas")

    except Exception as e:
        issues.append(f"Exception: {str(e)}")
        REPORT["pages"]["machines"]["status"] = "BROKEN"
        print(f"✗ Erro ao testar machines: {e}")

    REPORT["pages"]["machines"]["issues"] = issues
    REPORT["pages"]["machines"]["elements"] = elements
    return len(issues) == 0

async def validate_settings(page):
    """Validate settings page"""
    print("\n[4/5] TESTANDO PÁGINA SETTINGS...")
    issues = []
    elements = []

    try:
        await page.goto("http://localhost:8000/settings")
        await page.wait_for_timeout(2000)

        # Check for settings form elements
        inputs = await page.query_selector_all('input, select, textarea')
        if inputs:
            elements.append(f"Found {len(inputs)} form inputs")
        else:
            issues.append("No form inputs found")

        # Check for toggles/switches
        toggles = await page.query_selector_all('[role="switch"], [class*="toggle"], [class*="checkbox"]')
        if toggles:
            elements.append(f"Found {len(toggles)} toggle switches")
        else:
            issues.append("No toggle switches found")

        # Check for save button
        save_button = await page.query_selector('button:has-text("Save"), button:has-text("Salvar")')
        if save_button:
            elements.append("Save button found")
        else:
            issues.append("Save button not found")

        REPORT["pages"]["settings"]["status"] = "PASSED" if len(issues) < 1 else "PARTIAL" if len(issues) < 3 else "BROKEN"
        print(f"{'✓' if len(issues) == 0 else '⚠' if len(issues) < 2 else '✗'} Settings: {len(elements)} elementos, {len(issues)} problemas")

    except Exception as e:
        issues.append(f"Exception: {str(e)}")
        REPORT["pages"]["settings"]["status"] = "BROKEN"
        print(f"✗ Erro ao testar settings: {e}")

    REPORT["pages"]["settings"]["issues"] = issues
    REPORT["pages"]["settings"]["elements"] = elements
    return len(issues) == 0

async def validate_metrics(page):
    """Validate metrics page"""
    print("\n[5/5] TESTANDO PÁGINA MÉTRICAS...")
    issues = []
    elements = []

    try:
        await page.goto("http://localhost:8000/metrics")
        await page.wait_for_timeout(2000)

        # Check for charts/graphs
        charts = await page.query_selector_all('canvas, svg, [class*="chart"], [class*="graph"]')
        if charts:
            elements.append(f"Found {len(charts)} charts/graphs")
        else:
            issues.append("No charts/graphs found")

        # Check for data tables
        tables = await page.query_selector_all('table, [role="grid"]')
        if tables:
            elements.append(f"Found {len(tables)} data tables")
        else:
            issues.append("No data tables found")

        # Check for metrics cards
        metric_cards = await page.query_selector_all('[class*="metric"], [class*="stat"], [class*="card"]')
        if metric_cards:
            elements.append(f"Found {len(metric_cards)} metric cards")
        else:
            issues.append("No metric cards found")

        REPORT["pages"]["metrics"]["status"] = "PASSED" if len(issues) < 1 else "PARTIAL" if len(issues) < 3 else "BROKEN"
        print(f"{'✓' if len(issues) == 0 else '⚠' if len(issues) < 2 else '✗'} Metrics: {len(elements)} elementos, {len(issues)} problemas")

    except Exception as e:
        issues.append(f"Exception: {str(e)}")
        REPORT["pages"]["metrics"]["status"] = "BROKEN"
        print(f"✗ Erro ao testar metrics: {e}")

    REPORT["pages"]["metrics"]["issues"] = issues
    REPORT["pages"]["metrics"]["elements"] = elements
    return len(issues) == 0

async def validate_navigation(page):
    """Validate navigation menu"""
    print("\n[EXTRA] TESTANDO NAVEGAÇÃO...")
    issues = []

    try:
        # Check for nav items
        nav_items = await page.query_selector_all('nav a, [role="navigation"] a, header a')
        if nav_items:
            nav_texts = []
            for item in nav_items[:5]:  # Get first 5
                text = await item.text_content()
                if text.strip():
                    nav_texts.append(text.strip())
            if nav_texts:
                print(f"✓ Menu items encontrados: {', '.join(nav_texts)}")
            else:
                issues.append("Navigation items found but empty")
        else:
            issues.append("No navigation menu found")
    except Exception as e:
        issues.append(f"Exception: {str(e)}")

    return len(issues) == 0

async def run_validation():
    """Run complete validation"""
    print("="*60)
    print("VALIDAÇÃO COMPLETA DO SISTEMA DUMONT CLOUD")
    print("="*60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Run all validations
            await validate_navigation(page)
            await validate_login(page)
            await validate_dashboard(page)
            await validate_machines(page)
            await validate_settings(page)
            await validate_metrics(page)

            # Calculate summary
            for page_name, page_data in REPORT["pages"].items():
                if page_data["status"] == "PASSED":
                    REPORT["summary"]["working"] += 1
                else:
                    REPORT["summary"]["broken"] += 1
                REPORT["summary"]["total_issues"] += len(page_data["issues"])

            # Print summary
            print("\n" + "="*60)
            print("RESUMO DA VALIDAÇÃO")
            print("="*60)
            print(f"Páginas funcionando: {REPORT['summary']['working']}")
            print(f"Páginas com problemas: {REPORT['summary']['broken']}")
            print(f"Total de problemas: {REPORT['summary']['total_issues']}")

            print("\nDETALHES POR PÁGINA:")
            for page_name, page_data in REPORT["pages"].items():
                print(f"\n{page_name.upper()}: {page_data['status']}")
                if page_data["elements"]:
                    print(f"  Elementos: {', '.join(page_data['elements'][:3])}")
                if page_data["issues"]:
                    print(f"  Problemas: {', '.join(page_data['issues'][:3])}")

            # Save detailed report
            report_path = "/tmp/validation_report.json"
            with open(report_path, 'w') as f:
                json.dump(REPORT, f, indent=2)
            print(f"\nRelatório completo salvo em: {report_path}")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_validation())
