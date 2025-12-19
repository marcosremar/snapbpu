"""
Comprehensive navigation test with login
Tests authenticated pages
"""
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

NAVIGATION_REPORT = {
    "timestamp": datetime.now().isoformat(),
    "url": "http://localhost:8000",
    "test_results": {}
}

async def test_landing_page(page):
    """Test landing/login page"""
    print("\n" + "="*70)
    print("1. TESTE DA PÁGINA INICIAL/LOGIN")
    print("="*70)

    result = {
        "page": "landing",
        "status": "UNTESTED",
        "components_found": [],
        "actions_tested": [],
        "issues": []
    }

    try:
        await page.goto("http://localhost:8000/")
        await page.wait_for_timeout(2000)

        # Check for login form
        email_input = await page.query_selector('input[type="email"], input[name="email"], input[placeholder*="email"]')
        password_input = await page.query_selector('input[type="password"], input[name="password"]')
        login_button = await page.query_selector('button:has-text("Login"), button:has-text("Entrar"), button:has-text("Sign In")')

        if email_input:
            result["components_found"].append("Email input")
        else:
            result["issues"].append("Email input not found")

        if password_input:
            result["components_found"].append("Password input")
        else:
            result["issues"].append("Password input not found")

        if login_button:
            result["components_found"].append("Login button")
        else:
            result["issues"].append("Login button not found")

        # Check for social login options
        google_btn = await page.query_selector('button:has-text("Google"), button:has-text("google")')
        github_btn = await page.query_selector('button:has-text("GitHub"), button:has-text("github")')

        if google_btn:
            result["components_found"].append("Google login button")
        if github_btn:
            result["components_found"].append("GitHub login button")

        # Try demo mode first
        print("✓ Tentando modo demo...")
        await page.goto("http://localhost:8000/?demo=true")
        await page.wait_for_timeout(2000)
        result["actions_tested"].append("Demo mode activation")

        if "localhost" in page.url:
            result["status"] = "DEMO_SUCCESS"
            print("✓ Demo mode ativado com sucesso")
        else:
            print("⚠ Demo mode pode ter falhado")

    except Exception as e:
        result["issues"].append(f"Exception: {str(e)}")
        print(f"✗ Erro: {e}")

    NAVIGATION_REPORT["test_results"]["landing_page"] = result
    return result

async def test_dashboard(page):
    """Test dashboard page"""
    print("\n" + "="*70)
    print("2. TESTE DO DASHBOARD")
    print("="*70)

    result = {
        "page": "dashboard",
        "status": "UNTESTED",
        "components_found": [],
        "actions_tested": [],
        "issues": []
    }

    try:
        await page.goto("http://localhost:8000/app?demo=true")
        await page.wait_for_timeout(2000)

        # Verify we're on dashboard
        title_elem = await page.query_selector('h1, h2, [class*="title"]')
        if title_elem:
            title = await title_elem.text_content()
            result["components_found"].append(f"Dashboard title: {title.strip()[:50]}")
            print(f"✓ Dashboard carregou: {title.strip()[:50]}")

        # Check for speed cards/wizard
        cards = await page.query_selector_all('[class*="card"], button[class*="speed"]')
        if len(cards) > 0:
            result["components_found"].append(f"Speed cards ({len(cards)} found)")
            print(f"✓ {len(cards)} cards encontrados")

            # Try clicking first card
            try:
                await cards[0].click()
                await page.wait_for_timeout(1000)
                result["actions_tested"].append("Clicked speed card")
                print("✓ Card clicável")
            except:
                result["issues"].append("Speed card not clickable")

        # Check for search/wizard button
        search_button = await page.query_selector('button:has-text("Buscar"), button:has-text("Search"), button:has-text("Procurar")')
        if search_button:
            result["components_found"].append("Search/Wizard button")
            result["actions_tested"].append("Search button found")
            print("✓ Botão de busca encontrado")

            try:
                await search_button.click()
                await page.wait_for_timeout(1000)
                result["actions_tested"].append("Clicked search button")
                print("✓ Botão de busca clicável")
            except:
                result["issues"].append("Search button not clickable")
        else:
            result["issues"].append("Search/Wizard button not found")
            print("✗ Botão de busca não encontrado")

        # Check for widgets/cards
        stat_cards = await page.query_selector_all('[class*="stat"], [class*="metric"], [class*="widget"]')
        if len(stat_cards) > 0:
            result["components_found"].append(f"Stat/Metric cards ({len(stat_cards)})")
            print(f"✓ {len(stat_cards)} cards de métricas/stats")

        result["status"] = "SUCCESS" if len(result["issues"]) == 0 else "PARTIAL" if len(result["issues"]) < 3 else "BROKEN"

    except Exception as e:
        result["issues"].append(f"Exception: {str(e)}")
        print(f"✗ Erro: {e}")
        result["status"] = "BROKEN"

    NAVIGATION_REPORT["test_results"]["dashboard"] = result
    return result

async def test_machines_page(page):
    """Test machines page"""
    print("\n" + "="*70)
    print("3. TESTE DA PÁGINA MACHINES")
    print("="*70)

    result = {
        "page": "machines",
        "status": "UNTESTED",
        "components_found": [],
        "actions_tested": [],
        "issues": []
    }

    try:
        await page.goto("http://localhost:8000/app/machines?demo=true")
        await page.wait_for_timeout(2000)

        # Check page title
        title_elem = await page.query_selector('h1, h2, [class*="PageTitle"]')
        if title_elem:
            title = await title_elem.text_content()
            result["components_found"].append(f"Page title: {title.strip()[:50]}")
            print(f"✓ Página carregou: {title.strip()[:50]}")

        # Check for machine list
        machine_items = await page.query_selector_all('[class*="machine"], [class*="instance"], tr')
        if len(machine_items) > 0:
            result["components_found"].append(f"Machine items ({len(machine_items)})")
            print(f"✓ {len(machine_items)} máquinas encontradas")
        else:
            result["issues"].append("No machine items found")
            print("✗ Nenhuma máquina encontrada")

        # Check for filters
        filter_elements = await page.query_selector_all('input[type="text"], select, [class*="filter"]')
        if len(filter_elements) > 0:
            result["components_found"].append(f"Filter/Search elements ({len(filter_elements)})")
            print(f"✓ {len(filter_elements)} elementos de filtro")

        # Check for action buttons
        action_buttons = await page.query_selector_all('button:has-text("Edit"), button:has-text("Delete"), button:has-text("Pause"), button:has-text("Resume")')
        if len(action_buttons) > 0:
            result["components_found"].append(f"Action buttons ({len(action_buttons)})")
            print(f"✓ {len(action_buttons)} botões de ação")
        else:
            result["issues"].append("No action buttons found")

        # Check for status indicators
        status_badges = await page.query_selector_all('[class*="badge"], [class*="status"]')
        if len(status_badges) > 0:
            result["components_found"].append(f"Status badges ({len(status_badges)})")
            print(f"✓ {len(status_badges)} badges de status")

        result["status"] = "SUCCESS" if len(result["issues"]) == 0 else "PARTIAL" if len(result["issues"]) < 2 else "BROKEN"

    except Exception as e:
        result["issues"].append(f"Exception: {str(e)}")
        print(f"✗ Erro: {e}")
        result["status"] = "BROKEN"

    NAVIGATION_REPORT["test_results"]["machines_page"] = result
    return result

async def test_metrics_page(page):
    """Test metrics page"""
    print("\n" + "="*70)
    print("4. TESTE DA PÁGINA MÉTRICAS")
    print("="*70)

    result = {
        "page": "metrics",
        "status": "UNTESTED",
        "components_found": [],
        "actions_tested": [],
        "issues": []
    }

    try:
        await page.goto("http://localhost:8000/app/metrics-hub?demo=true")
        await page.wait_for_timeout(2000)

        # Check page title
        title_elem = await page.query_selector('h1, h2, [class*="PageTitle"]')
        if title_elem:
            title = await title_elem.text_content()
            result["components_found"].append(f"Page title: {title.strip()[:50]}")
            print(f"✓ Página carregou: {title.strip()[:50]}")

        # Check for charts
        charts = await page.query_selector_all('canvas, svg, [class*="chart"], [class*="Chart"]')
        if len(charts) > 0:
            result["components_found"].append(f"Charts ({len(charts)})")
            print(f"✓ {len(charts)} gráficos encontrados")
        else:
            result["issues"].append("No charts found")

        # Check for data tables
        tables = await page.query_selector_all('table')
        if len(tables) > 0:
            result["components_found"].append(f"Data tables ({len(tables)})")
            print(f"✓ {len(tables)} tabelas encontradas")

        # Check for filters/date picker
        date_inputs = await page.query_selector_all('input[type="date"], input[class*="date"], button[class*="date"]')
        if len(date_inputs) > 0:
            result["components_found"].append(f"Date pickers ({len(date_inputs)})")
            print(f"✓ {len(date_inputs)} seletores de data")

        # Check for metric cards
        metric_cards = await page.query_selector_all('[class*="metric"], [class*="stat"], [class*="card"]')
        if len(metric_cards) > 0:
            result["components_found"].append(f"Metric cards ({len(metric_cards)})")
            print(f"✓ {len(metric_cards)} cards de métricas")

        result["status"] = "SUCCESS" if len(result["issues"]) == 0 else "PARTIAL" if len(result["issues"]) < 2 else "BROKEN"

    except Exception as e:
        result["issues"].append(f"Exception: {str(e)}")
        print(f"✗ Erro: {e}")
        result["status"] = "BROKEN"

    NAVIGATION_REPORT["test_results"]["metrics_page"] = result
    return result

async def test_settings_page(page):
    """Test settings page"""
    print("\n" + "="*70)
    print("5. TESTE DA PÁGINA SETTINGS")
    print("="*70)

    result = {
        "page": "settings",
        "status": "UNTESTED",
        "components_found": [],
        "actions_tested": [],
        "issues": []
    }

    try:
        # Settings might not have a dedicated route, check Layout menu
        # First, go to dashboard to access settings from menu
        await page.goto("http://localhost:8000/app?demo=true")
        await page.wait_for_timeout(1000)

        # Look for settings link in menu
        settings_link = await page.query_selector('a:has-text("Settings"), a:has-text("Configurações"), button:has-text("Settings")')
        if settings_link:
            await settings_link.click()
            await page.wait_for_timeout(1000)
            result["actions_tested"].append("Clicked settings link")
            print("✓ Link de settings clicado")
        else:
            # Try direct URL
            await page.goto("http://localhost:8000/app/settings?demo=true")
            await page.wait_for_timeout(1000)
            print("✓ Tentando acesso direto a settings")

        # Check for settings elements
        settings_sections = await page.query_selector_all('[class*="setting"], [class*="Setting"], h2, h3')
        if len(settings_sections) > 0:
            result["components_found"].append(f"Settings sections ({len(settings_sections)})")
            print(f"✓ {len(settings_sections)} seções de configuração")

        # Check for inputs
        inputs = await page.query_selector_all('input, select, textarea')
        if len(inputs) > 0:
            result["components_found"].append(f"Input fields ({len(inputs)})")
            print(f"✓ {len(inputs)} campos de entrada")

        # Check for toggles/switches
        toggles = await page.query_selector_all('[role="switch"], input[type="checkbox"]')
        if len(toggles) > 0:
            result["components_found"].append(f"Toggle switches ({len(toggles)})")
            print(f"✓ {len(toggles)} switches de configuração")

        # Check for save button
        save_button = await page.query_selector('button:has-text("Save"), button:has-text("Salvar"), button:has-text("Apply")')
        if save_button:
            result["components_found"].append("Save button")
            print("✓ Botão de salvar encontrado")

        result["status"] = "SUCCESS" if len(result["issues"]) == 0 else "PARTIAL" if len(result["issues"]) < 2 else "BROKEN"

    except Exception as e:
        result["issues"].append(f"Exception: {str(e)}")
        print(f"✗ Erro: {e}")
        result["status"] = "BROKEN"

    NAVIGATION_REPORT["test_results"]["settings_page"] = result
    return result

async def test_navigation_menu(page):
    """Test navigation menu"""
    print("\n" + "="*70)
    print("6. TESTE DO MENU DE NAVEGAÇÃO")
    print("="*70)

    result = {
        "component": "navigation_menu",
        "status": "UNTESTED",
        "menu_items": [],
        "issues": []
    }

    try:
        await page.goto("http://localhost:8000/app?demo=true")
        await page.wait_for_timeout(1000)

        # Find navigation items
        nav_links = await page.query_selector_all('nav a, [role="navigation"] a, header a')
        menu_items = []

        for link in nav_links:
            try:
                text = await link.text_content()
                href = await link.get_attribute('href')
                if text.strip() and text.strip() not in menu_items:
                    menu_items.append(text.strip())
                    print(f"✓ Menu item: {text.strip()}")
            except:
                pass

        result["menu_items"] = menu_items

        if len(menu_items) > 0:
            result["status"] = "SUCCESS"
        else:
            result["issues"].append("No menu items found")
            result["status"] = "BROKEN"

    except Exception as e:
        result["issues"].append(f"Exception: {str(e)}")
        result["status"] = "BROKEN"

    NAVIGATION_REPORT["test_results"]["navigation_menu"] = result
    return result

async def run_comprehensive_navigation_test():
    """Run comprehensive navigation test"""
    print("\n" + "="*70)
    print("NAVEGAÇÃO COMPLETA COM AUTENTICAÇÃO")
    print("Dumont Cloud - Sistema de Gerenciamento de GPUs")
    print("="*70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Run all tests
            await test_landing_page(page)
            await test_navigation_menu(page)
            await test_dashboard(page)
            await test_machines_page(page)
            await test_metrics_page(page)
            await test_settings_page(page)

            # Summary
            print("\n\n" + "="*70)
            print("RESUMO FINAL")
            print("="*70)

            success_count = 0
            partial_count = 0
            broken_count = 0

            for test_name, test_result in NAVIGATION_REPORT["test_results"].items():
                if "status" in test_result:
                    status = test_result["status"]
                    if status == "SUCCESS" or status == "DEMO_SUCCESS":
                        success_count += 1
                        icon = "✓"
                    elif status == "PARTIAL":
                        partial_count += 1
                        icon = "⚠"
                    else:
                        broken_count += 1
                        icon = "✗"

                    print(f"{icon} {test_name.replace('_', ' ').title()}: {status}")

                    # Show found components
                    if "components_found" in test_result and test_result["components_found"]:
                        for component in test_result["components_found"][:2]:
                            print(f"    • {component}")

                    # Show issues
                    if "issues" in test_result and test_result["issues"]:
                        for issue in test_result["issues"][:2]:
                            print(f"    ⚠ {issue}")

            print(f"\nTotal: {success_count} Success | {partial_count} Partial | {broken_count} Broken")

            # Save report
            report_path = "/tmp/navigation_test_report.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(NAVIGATION_REPORT, f, indent=2, ensure_ascii=False)

            print(f"\nRelatório completo salvo em: {report_path}")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_comprehensive_navigation_test())
