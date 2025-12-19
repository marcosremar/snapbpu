"""
Detailed system analysis with comprehensive interactions
Tests all components and records detailed findings
"""
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

DETAILED_REPORT = {
    "timestamp": datetime.now().isoformat(),
    "url": "http://localhost:8000",
    "pages": {},
    "global_issues": [],
    "global_features": [],
    "recommendations": []
}

async def analyze_page_structure(page, page_name):
    """Analyze page structure and components"""
    print(f"\n{'='*60}")
    print(f"ANALISANDO: {page_name.upper()}")
    print('='*60)

    analysis = {
        "page_name": page_name,
        "url": page.url,
        "title": await page.title(),
        "components": {},
        "issues": [],
        "features_working": [],
        "interactive_elements": []
    }

    try:
        # Get page content
        content = await page.content()

        # 1. Navigation Analysis
        print("\n[NAVEGAÇÃO]")
        nav_items = await page.query_selector_all('nav a, header a, [role="navigation"] a')
        nav_list = []
        for item in nav_items:
            try:
                text = await item.text_content()
                href = await item.get_attribute('href')
                if text.strip():
                    nav_list.append({"text": text.strip(), "href": href})
            except:
                pass

        if nav_list:
            analysis["components"]["navigation"] = nav_list
            print(f"✓ {len(nav_list)} itens de navegação encontrados")
            for item in nav_list[:5]:
                print(f"  - {item['text']} → {item.get('href', 'N/A')}")
        else:
            print("✗ Nenhum item de navegação encontrado")
            analysis["issues"].append("Navigation menu not found or not clickable")

        # 2. Form Elements
        print("\n[FORMULÁRIOS]")
        inputs = await page.query_selector_all('input')
        labels = await page.query_selector_all('label')
        buttons = await page.query_selector_all('button')

        form_info = {
            "total_inputs": len(inputs),
            "total_buttons": len(buttons),
            "input_types": []
        }

        input_types = {}
        for inp in inputs[:10]:
            try:
                inp_type = await inp.get_attribute('type')
                placeholder = await inp.get_attribute('placeholder')
                input_types[inp_type] = input_types.get(inp_type, 0) + 1
            except:
                pass

        form_info["input_types"] = list(input_types.keys())
        analysis["components"]["forms"] = form_info

        if len(inputs) > 0:
            print(f"✓ {len(inputs)} campos de entrada encontrados")
            print(f"  Tipos: {', '.join(input_types.keys())}")
        else:
            print("✗ Nenhum campo de entrada encontrado")

        if len(buttons) > 0:
            print(f"✓ {len(buttons)} botões encontrados")
        else:
            print("✗ Nenhum botão encontrado")

        # 3. Data Display
        print("\n[DADOS]")
        tables = await page.query_selector_all('table')
        grids = await page.query_selector_all('[role="grid"]')
        cards = await page.query_selector_all('[class*="card"], [class*="Card"]')
        lists = await page.query_selector_all('ul, ol')

        data_info = {
            "tables": len(tables),
            "grids": len(grids),
            "cards": len(cards),
            "lists": len(lists)
        }

        analysis["components"]["data_display"] = data_info

        if len(tables) > 0:
            print(f"✓ {len(tables)} tabelas encontradas")
        if len(grids) > 0:
            print(f"✓ {len(grids)} grids encontrados")
        if len(cards) > 0:
            print(f"✓ {len(cards)} cards encontrados")
        if len(lists) > 0:
            print(f"✓ {len(lists)} listas encontradas")

        if len(tables) == 0 and len(grids) == 0 and len(cards) == 0 and len(lists) == 0:
            print("✗ Nenhum elemento de dados encontrado")
            analysis["issues"].append("No data display elements found")

        # 4. Interactive Elements
        print("\n[INTERATIVIDADE]")
        selects = await page.query_selector_all('select')
        toggles = await page.query_selector_all('[role="switch"], input[type="checkbox"], input[type="radio"]')
        dropdowns = await page.query_selector_all('[role="button"][aria-haspopup]')
        modals = await page.query_selector_all('[role="dialog"], .modal, [class*="Modal"]')

        interactive_info = {
            "selects": len(selects),
            "toggles": len(toggles),
            "dropdowns": len(dropdowns),
            "modals": len(modals)
        }

        analysis["interactive_elements"] = interactive_info

        if len(selects) > 0:
            print(f"✓ {len(selects)} selects encontrados")
            analysis["features_working"].append("Select dropdowns")

        if len(toggles) > 0:
            print(f"✓ {len(toggles)} switches/toggles encontrados")
            analysis["features_working"].append("Toggle switches")

        if len(dropdowns) > 0:
            print(f"✓ {len(dropdowns)} dropdowns encontrados")

        if len(modals) > 0:
            print(f"✓ {len(modals)} modals encontrados")

        # 5. Visual Elements
        print("\n[VISUAIS]")
        images = await page.query_selector_all('img')
        charts = await page.query_selector_all('canvas, svg, [class*="chart"], [class*="Chart"]')
        badges = await page.query_selector_all('[class*="badge"], [class*="tag"], span[class*="Badge"]')

        visual_info = {
            "images": len(images),
            "charts": len(charts),
            "badges": len(badges)
        }

        analysis["components"]["visuals"] = visual_info

        if len(images) > 0:
            print(f"✓ {len(images)} imagens encontradas")
        if len(charts) > 0:
            print(f"✓ {len(charts)} gráficos encontrados")
            analysis["features_working"].append("Data visualization")
        if len(badges) > 0:
            print(f"✓ {len(badges)} badges encontradas")

        # 6. Test Basic Interactions
        print("\n[TESTES DE INTERAÇÃO]")

        # Try to click buttons
        buttons_on_page = await page.query_selector_all('button:not([disabled])')
        if len(buttons_on_page) > 0:
            try:
                # Get first button text
                btn_text = await buttons_on_page[0].text_content()
                print(f"  Testando clique em botão: '{btn_text.strip()}'...")
                await buttons_on_page[0].click()
                await page.wait_for_timeout(500)
                analysis["features_working"].append("Button clicks responsive")
                print(f"  ✓ Botão clicável")
            except Exception as e:
                analysis["issues"].append(f"Button click failed: {str(e)}")
                print(f"  ✗ Erro ao clicar: {e}")

        # Try to fill inputs
        if len(inputs) > 0 and page_name != "login":
            try:
                await inputs[0].fill("test")
                analysis["features_working"].append("Input fields responsive")
                print(f"  ✓ Campo de entrada funcional")
            except:
                pass

        # 7. Error Messages
        print("\n[VALIDAÇÕES]")
        error_elements = await page.query_selector_all('[role="alert"], .error, .alert, [class*="Error"]')
        if len(error_elements) > 0:
            print(f"⚠ {len(error_elements)} elementos de erro/alerta encontrados")
            for elem in error_elements[:2]:
                try:
                    text = await elem.text_content()
                    if text.strip():
                        print(f"  - {text.strip()[:80]}")
                except:
                    pass

        # 8. Accessibility
        print("\n[ACESSIBILIDADE]")
        aria_labels = await page.query_selector_all('[aria-label]')
        aria_describedby = await page.query_selector_all('[aria-describedby]')
        alt_texts = await page.query_selector_all('img[alt]')

        if len(aria_labels) > 0 or len(alt_texts) > 0:
            print(f"✓ Elementos com acessibilidade: {len(aria_labels)} aria-labels, {len(alt_texts)} alt-texts")
            analysis["features_working"].append("Accessibility attributes")
        else:
            print("⚠ Poucos elementos com atributos de acessibilidade")
            analysis["issues"].append("Missing accessibility attributes")

    except Exception as e:
        analysis["issues"].append(f"Analysis error: {str(e)}")
        print(f"\n✗ Erro durante análise: {e}")

    DETAILED_REPORT["pages"][page_name] = analysis
    return analysis

async def test_login_page(page):
    """Test login functionality"""
    print("\n" + "="*60)
    print("TESTANDO PÁGINA DE LOGIN")
    print("="*60)

    analysis = await analyze_page_structure(page, "login")

    # Check if we're on login page
    await page.goto("http://localhost:8000")
    await page.wait_for_timeout(2000)

    # Look for form
    form = await page.query_selector('form')
    if form:
        print("\n✓ Formulário de login encontrado")
    else:
        print("\n✗ Formulário de login NÃO encontrado")
        analysis["issues"].append("Login form not found")

    return analysis

async def test_dashboard_page(page):
    """Test dashboard functionality"""
    print("\n" + "="*60)
    print("TESTANDO DASHBOARD")
    print("="*60)

    # Navigate to dashboard
    await page.goto("http://localhost:8000/dashboard")
    await page.wait_for_timeout(2000)

    analysis = await analyze_page_structure(page, "dashboard")

    # Test speed cards interaction
    cards = await page.query_selector_all('[class*="card"], [class*="Card"], button')
    if len(cards) > 0:
        print("\nTestando cards de velocidade...")
        for i, card in enumerate(cards[:3]):
            try:
                text = await card.text_content()
                if text and any(speed in text.lower() for speed in ['rapido', 'slow', 'medio', 'ultra']):
                    print(f"  Encontrado: {text.strip()[:50]}")
                    analysis["features_working"].append(f"Speed card: {text.strip()}")
            except:
                pass

    return analysis

async def test_machines_page(page):
    """Test machines page"""
    print("\n" + "="*60)
    print("TESTANDO PÁGINA MACHINES")
    print("="*60)

    await page.goto("http://localhost:8000/machines")
    await page.wait_for_timeout(2000)

    analysis = await analyze_page_structure(page, "machines")

    # Check for machine list
    machine_list = await page.query_selector('[class*="machine"], [class*="instance"], [role="list"]')
    if machine_list:
        print("\n✓ Lista de máquinas encontrada")
        analysis["features_working"].append("Machine list")
    else:
        print("\n✗ Lista de máquinas NÃO encontrada")
        analysis["issues"].append("Machine list not found")

    # Check for status indicators
    online_status = await page.query_selector_all('[class*="online"], span:has-text("Online")')
    offline_status = await page.query_selector_all('[class*="offline"], span:has-text("Offline")')

    if len(online_status) > 0 or len(offline_status) > 0:
        print(f"✓ Status de máquinas: {len(online_status)} online, {len(offline_status)} offline")
        analysis["features_working"].append("Machine status indicators")

    return analysis

async def test_settings_page(page):
    """Test settings page"""
    print("\n" + "="*60)
    print("TESTANDO PÁGINA SETTINGS")
    print("="*60)

    await page.goto("http://localhost:8000/settings")
    await page.wait_for_timeout(2000)

    analysis = await analyze_page_structure(page, "settings")

    # Check for settings groups
    sections = await page.query_selector_all('[class*="section"], [class*="Section"], h2, h3')
    if len(sections) > 0:
        print(f"\n✓ {len(sections)} seções de configuração encontradas")
        analysis["features_working"].append("Settings sections")

    return analysis

async def test_metrics_page(page):
    """Test metrics/analytics page"""
    print("\n" + "="*60)
    print("TESTANDO PÁGINA MÉTRICAS")
    print("="*60)

    await page.goto("http://localhost:8000/metrics")
    await page.wait_for_timeout(2000)

    analysis = await analyze_page_structure(page, "metrics")

    # Check for date range picker
    date_picker = await page.query_selector('[class*="date"], input[type="date"], input[class*="Date"]')
    if date_picker:
        print("\n✓ Date picker encontrado")
        analysis["features_working"].append("Date range picker")

    return analysis

async def run_detailed_analysis():
    """Run detailed system analysis"""
    print("\n" + "="*80)
    print("ANÁLISE DETALHADA DO SISTEMA DUMONT CLOUD")
    print("="*80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Test all pages
            await test_login_page(page)
            await test_dashboard_page(page)
            await test_machines_page(page)
            await test_settings_page(page)
            await test_metrics_page(page)

            # Generate summary
            print("\n\n" + "="*80)
            print("RESUMO EXECUTIVO")
            print("="*80)

            total_issues = 0
            total_features = 0
            all_features = set()
            all_issues = []

            for page_name, page_data in DETAILED_REPORT["pages"].items():
                issues = page_data.get("issues", [])
                features = page_data.get("features_working", [])

                total_issues += len(issues)
                total_features += len(features)
                all_features.update(features)
                all_issues.extend(issues)

                status = "✓ OK" if len(issues) == 0 else "⚠ PARCIAL" if len(issues) < 3 else "✗ QUEBRADO"
                print(f"\n{page_name.upper()}: {status}")
                print(f"  Recursos: {', '.join(features[:3]) if features else 'Nenhum'}")
                if issues:
                    print(f"  Problemas: {', '.join(issues[:2])}")

            print("\n\n" + "="*80)
            print("RECURSOS FUNCIONANDO:")
            print("="*80)
            for feature in sorted(all_features):
                print(f"✓ {feature}")

            print("\n" + "="*80)
            print("PROBLEMAS ENCONTRADOS:")
            print("="*80)
            for issue in sorted(set(all_issues)):
                print(f"✗ {issue}")

            # Recommendations
            print("\n" + "="*80)
            print("RECOMENDAÇÕES:")
            print("="*80)

            if "Login form not found" in all_issues:
                DETAILED_REPORT["recommendations"].append("Implementar formulário de login na página raiz")

            if "Machine list not found" in all_issues:
                DETAILED_REPORT["recommendations"].append("Implementar listagem de máquinas na página /machines")

            if "Search/Wizard button not found" in all_issues:
                DETAILED_REPORT["recommendations"].append("Adicionar botão 'Buscar Máquinas' no dashboard")

            if "Missing accessibility attributes" in all_issues:
                DETAILED_REPORT["recommendations"].append("Melhorar acessibilidade com aria-labels e alt-text")

            if DETAILED_REPORT["recommendations"]:
                for i, rec in enumerate(DETAILED_REPORT["recommendations"], 1):
                    print(f"{i}. {rec}")
            else:
                print("Nenhuma recomendação crítica no momento")

            # Save detailed report
            report_path = "/tmp/detailed_analysis_report.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(DETAILED_REPORT, f, indent=2, ensure_ascii=False)

            print(f"\n\nRelatório detalhado salvo em: {report_path}")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_detailed_analysis())
