"""
Debug script to identify specific issues with broken components
Tests with debug output and error logging
"""
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

DEBUG_REPORT = {
    "timestamp": datetime.now().isoformat(),
    "debug_findings": {}
}

async def debug_machines_page(page):
    """Debug why machines page is broken"""
    print("\n" + "="*70)
    print("DEBUGGING: PÁGINA MACHINES")
    print("="*70)

    findings = {
        "page_url": None,
        "page_loaded": False,
        "console_errors": [],
        "network_issues": [],
        "dom_structure": {},
        "api_calls": [],
        "component_status": {}
    }

    try:
        # Set up network listener
        request_log = []
        def log_request(request):
            request_log.append({
                "url": request.url,
                "method": request.method,
                "type": request.resource_type
            })

        def log_response(response):
            if response.status != 200:
                findings["network_issues"].append({
                    "url": response.url,
                    "status": response.status
                })

        page.on("request", log_request)
        page.on("response", log_response)

        # Set up console error listener
        def on_console_message(msg):
            if msg.type in ["error", "warning"]:
                findings["console_errors"].append({
                    "type": msg.type,
                    "text": msg.text
                })
                print(f"🔴 Console {msg.type}: {msg.text[:100]}")

        page.on("console", on_console_message)

        # Navigate with demo mode
        print("\nNavegando para /app/machines...")
        await page.goto("http://localhost:8000/?demo=true")
        await page.wait_for_timeout(1000)

        await page.goto("http://localhost:8000/app/machines")
        await page.wait_for_timeout(3000)  # Wait longer for loading

        findings["page_url"] = page.url
        findings["page_loaded"] = True

        # Check page content
        content = await page.content()
        print(f"✓ Página carregou ({len(content)} bytes)")

        # Check for errors
        if "error" in content.lower() or "erro" in content.lower():
            print("⚠ Mensagens de erro detectadas no HTML")

        # Check specific elements
        print("\n[Elementos do DOM]")

        # Check table/list container
        machine_container = await page.query_selector('[class*="machine"], [class*="Machine"], [class*="list"], [class*="List"], table')
        if machine_container:
            print("✓ Container de máquinas encontrado")
            findings["component_status"]["machine_container"] = "FOUND"
        else:
            print("✗ Container de máquinas NÃO encontrado")
            findings["component_status"]["machine_container"] = "NOT_FOUND"

        # Check loading spinner
        spinner = await page.query_selector('[class*="loading"], [class*="spinner"], [class*="Loading"]')
        if spinner:
            print("⚠ Elemento de carregamento detectado (pode estar carregando)")
            findings["component_status"]["loading_spinner"] = "VISIBLE"

        # Check error message
        error_msg = await page.query_selector('[role="alert"], [class*="error"], [class*="Error"]')
        if error_msg:
            error_text = await error_msg.text_content()
            print(f"🔴 Mensagem de erro encontrada: {error_text.strip()[:100]}")
            findings["component_status"]["error_message"] = error_text.strip()

        # Check for empty state
        empty_state = await page.query_selector('[class*="empty"], [class*="Empty"]')
        if empty_state:
            print("ℹ️ Estado vazio detectado (lista vazia)")
            findings["component_status"]["empty_state"] = "VISIBLE"

        # Try to trigger data loading
        print("\n[Tentando ativar dados]")

        # Look for filter/search to trigger load
        search_input = await page.query_selector('input[type="text"]')
        if search_input:
            print("✓ Input de pesquisa encontrado")
            try:
                await search_input.focus()
                await search_input.type("test")
                await page.wait_for_timeout(1000)
                print("✓ Valor digitado no input")
            except Exception as e:
                print(f"✗ Erro ao interagir com input: {e}")

        # Check for button to load machines
        load_btn = await page.query_selector('button:has-text("Load"), button:has-text("Buscar"), button:has-text("Search")')
        if load_btn:
            print("✓ Botão de busca encontrado")
            try:
                await load_btn.click()
                await page.wait_for_timeout(2000)
                print("✓ Botão clicado")
            except:
                print("✗ Erro ao clicar botão")

        # Check state after interaction
        machine_items = await page.query_selector_all('[class*="machine"], tr')
        print(f"\nApós interação: {len(machine_items)} itens encontrados")

        # Log API calls
        print(f"\n[Requisições de Rede]")
        api_calls = [req for req in request_log if '/api' in req['url']]
        if api_calls:
            print(f"✓ {len(api_calls)} requisições de API detectadas:")
            for call in api_calls[:5]:
                print(f"  - {call['method']} {call['url'].split('/api')[-1][:50]}")
            findings["api_calls"] = api_calls
        else:
            print("✗ Nenhuma requisição de API detectada")

        # Check network issues
        if findings["network_issues"]:
            print(f"\n[Erros de Rede]")
            for issue in findings["network_issues"][:3]:
                print(f"  ✗ {issue['status']} - {issue['url'][:60]}")

    except Exception as e:
        findings["error"] = str(e)
        print(f"\n✗ Erro durante debug: {e}")

    DEBUG_REPORT["debug_findings"]["machines_page"] = findings
    return findings

async def debug_navigation_menu(page):
    """Debug why navigation menu is not visible"""
    print("\n" + "="*70)
    print("DEBUGGING: MENU DE NAVEGAÇÃO")
    print("="*70)

    findings = {
        "nav_elements_found": 0,
        "nav_structure": {},
        "issues": []
    }

    try:
        await page.goto("http://localhost:8000/?demo=true")
        await page.wait_for_timeout(1000)
        await page.goto("http://localhost:8000/app")
        await page.wait_for_timeout(2000)

        print("\nBuscando elementos de navegação...")

        # Check for nav tag
        nav = await page.query_selector('nav')
        if nav:
            print("✓ Tag <nav> encontrada")
            findings["nav_structure"]["nav_tag"] = "FOUND"
        else:
            print("✗ Tag <nav> NÃO encontrada")
            findings["nav_structure"]["nav_tag"] = "NOT_FOUND"

        # Check for header
        header = await page.query_selector('header')
        if header:
            print("✓ Tag <header> encontrada")
            findings["nav_structure"]["header_tag"] = "FOUND"
        else:
            print("✗ Tag <header> NÃO encontrada")

        # Check for all links
        links = await page.query_selector_all('a')
        print(f"\n✓ {len(links)} links encontrados no total")

        # Filter visible links
        visible_links = []
        for link in links[:20]:
            try:
                text = await link.text_content()
                href = await link.get_attribute('href')
                if text.strip() and href:
                    visible_links.append({"text": text.strip(), "href": href})
                    print(f"  - {text.strip()[:30]} → {href[:50]}")
            except:
                pass

        findings["visible_links"] = visible_links
        findings["nav_elements_found"] = len(visible_links)

        # Check for specific nav patterns
        print("\nBuscando padrões de navegação específicos...")

        # Look for menu button
        menu_btn = await page.query_selector('button[aria-label*="menu"], button[class*="menu"], button[class*="Menu"]')
        if menu_btn:
            print("✓ Botão de menu encontrado")
        else:
            print("✗ Botão de menu NÃO encontrado")

        # Check if nav is hidden
        nav_hidden = await page.query_selector('nav[style*="display: none"], nav[class*="hidden"]')
        if nav_hidden:
            print("⚠ Navegação pode estar oculta por CSS")
            findings["issues"].append("Navigation hidden by CSS")

        # Check for mobile menu
        mobile_menu = await page.query_selector('[class*="mobile"], [class*="Mobile"]')
        if mobile_menu:
            print("ℹ️ Menu mobile detectado")

    except Exception as e:
        findings["error"] = str(e)
        print(f"✗ Erro: {e}")

    DEBUG_REPORT["debug_findings"]["navigation_menu"] = findings
    return findings

async def debug_dashboard_wizard(page):
    """Debug why search/wizard button is missing"""
    print("\n" + "="*70)
    print("DEBUGGING: BOTÃO DE BUSCA/WIZARD NO DASHBOARD")
    print("="*70)

    findings = {
        "wizard_component_found": False,
        "search_button_found": False,
        "ai_wizard_status": "UNKNOWN",
        "possible_locations": []
    }

    try:
        await page.goto("http://localhost:8000/?demo=true")
        await page.wait_for_timeout(1000)
        await page.goto("http://localhost:8000/app")
        await page.wait_for_timeout(2000)

        print("\nBuscando componente de Wizard/Busca...")

        # Check for wizard component
        wizard = await page.query_selector('[class*="wizard"], [class*="Wizard"], [id*="wizard"]')
        if wizard:
            print("✓ Componente Wizard encontrado")
            findings["wizard_component_found"] = True
        else:
            print("✗ Componente Wizard NÃO encontrado")

        # Check for search button variations
        search_variations = [
            'button:has-text("Buscar")',
            'button:has-text("Search")',
            'button:has-text("Procurar")',
            'button[class*="search"]',
            'button[class*="Search"]',
            'button[id*="wizard"]'
        ]

        found_buttons = []
        for selector in search_variations:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    text = await btn.text_content()
                    found_buttons.append(text.strip())
                    print(f"✓ Encontrado: {text.strip()}")
            except:
                pass

        findings["search_button_found"] = len(found_buttons) > 0
        findings["found_buttons"] = found_buttons

        # Check for button in specific sections
        print("\nBuscando em seções específicas...")

        # Check in hero section
        hero = await page.query_selector('[class*="hero"], [class*="Hero"], section')
        if hero:
            hero_buttons = await hero.query_selector_all('button')
            print(f"ℹ️ Seção hero: {len(hero_buttons)} botões")
            findings["possible_locations"].append({
                "location": "hero_section",
                "buttons": len(hero_buttons)
            })

        # Check in main content
        main = await page.query_selector('main, [role="main"]')
        if main:
            main_buttons = await main.query_selector_all('button')
            print(f"ℹ️ Main content: {len(main_buttons)} botões")
            findings["possible_locations"].append({
                "location": "main_content",
                "buttons": len(main_buttons)
            })

        # Get all buttons and their text
        all_buttons = await page.query_selector_all('button')
        button_texts = []
        for btn in all_buttons[:10]:
            try:
                text = await btn.text_content()
                if text.strip():
                    button_texts.append(text.strip())
            except:
                pass

        print(f"\nTodos os botões encontrados: {button_texts[:10]}")
        findings["all_buttons"] = button_texts

    except Exception as e:
        findings["error"] = str(e)
        print(f"✗ Erro: {e}")

    DEBUG_REPORT["debug_findings"]["dashboard_wizard"] = findings
    return findings

async def run_debug_session():
    """Run debug session"""
    print("\n" + "="*70)
    print("SESSÃO DE DEBUG - IDENTIFICANDO PROBLEMAS ESPECÍFICOS")
    print("="*70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Run debug tests
            await debug_machines_page(page)
            await debug_navigation_menu(page)
            await debug_dashboard_wizard(page)

            # Summary
            print("\n\n" + "="*70)
            print("RESUMO DO DEBUG")
            print("="*70)

            for component, findings in DEBUG_REPORT["debug_findings"].items():
                print(f"\n{component}:")
                if "error" in findings:
                    print(f"  ✗ Erro: {findings['error']}")
                else:
                    for key, value in findings.items():
                        if key != "error":
                            print(f"  - {key}: {value}")

            # Save report
            report_path = "/tmp/debug_report.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(DEBUG_REPORT, f, indent=2, ensure_ascii=False)

            print(f"\n\nRelatório de debug salvo em: {report_path}")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_debug_session())
